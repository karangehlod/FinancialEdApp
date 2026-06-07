"""
CacheService — application-level caching layer.

Responsibilities:
  - Provide a consistent key-naming convention
  - Define TTL constants per data domain
  - Offer typed cache operations used by domain services
  - Provide cache invalidation helpers that clear all related keys

Design decisions:
  - Keys follow the pattern:  cache:{domain}:{user_id}:{resource}[:{discriminator}]
  - All values are JSON-serialised/deserialised transparently via RedisCache
  - Cache-aside pattern: read from cache → on miss, read from DB → populate cache
  - Invalidation is eager: any mutation clears all keys for that user's domain
"""

import hashlib
import json
import logging
from typing import Any, Callable, Optional, TypeVar

from app.core.providers import CacheProvider

logger = logging.getLogger(__name__)

T = TypeVar("T")

# ---------------------------------------------------------------------------
# TTL constants (seconds)
# ---------------------------------------------------------------------------

class CacheTTL:
    """Time-to-live values per data domain."""
    USER_PROFILE    = 1800   # 30 min — rarely changes
    BUDGET_SUMMARY  = 300    #  5 min — changes on expense create/update
    EXPENSE_LIST    = 120    #  2 min — high write frequency
    EXPENSE_SUMMARY = 300    #  5 min
    GOAL_LIST       = 300    #  5 min
    ANALYTICS       = 600    # 10 min — expensive to recompute
    TOKEN_USER      = 1800   # 30 min — match access token TTL


# ---------------------------------------------------------------------------
# Key builders
# ---------------------------------------------------------------------------

class CacheKey:
    """Centralised, deterministic cache key builders."""

    @staticmethod
    def user_profile(user_id: str) -> str:
        return f"cache:profile:{user_id}"

    @staticmethod
    def expense_list(user_id: str, page: int, limit: int, filters_hash: str) -> str:
        return f"cache:expenses:{user_id}:list:{page}:{limit}:{filters_hash}"

    @staticmethod
    def expense_summary(user_id: str, start_date: str, end_date: str) -> str:
        return f"cache:expenses:{user_id}:summary:{start_date}:{end_date}"

    @staticmethod
    def expense_analytics(user_id: str) -> str:
        return f"cache:expenses:{user_id}:analytics"

    @staticmethod
    def budget_list(user_id: str, month: str) -> str:
        return f"cache:budgets:{user_id}:{month}"

    @staticmethod
    def budget_summary(user_id: str, month: str) -> str:
        return f"cache:budgets:{user_id}:summary:{month}"

    @staticmethod
    def goal_list(user_id: str) -> str:
        return f"cache:goals:{user_id}:list"

    @staticmethod
    def token_user(user_id: str) -> str:
        return f"cache:token_user:{user_id}"

    # --- Invalidation patterns ---

    @staticmethod
    def user_expenses_pattern(user_id: str) -> str:
        return f"cache:expenses:{user_id}:*"

    @staticmethod
    def user_budgets_pattern(user_id: str) -> str:
        return f"cache:budgets:{user_id}:*"

    @staticmethod
    def user_goals_pattern(user_id: str) -> str:
        return f"cache:goals:{user_id}:*"

    @staticmethod
    def user_all_pattern(user_id: str) -> str:
        return f"cache:*:{user_id}:*"

    @staticmethod
    def hash_filters(filters: Any) -> str:
        """Deterministic hash of a filter object for use as a cache key discriminator."""
        try:
            serialized = json.dumps(
                filters if isinstance(filters, dict) else vars(filters),
                sort_keys=True,
                default=str,
            )
            return hashlib.md5(serialized.encode()).hexdigest()[:8]  # noqa: S324
        except Exception:
            return "nf"


# ---------------------------------------------------------------------------
# CacheService
# ---------------------------------------------------------------------------

class CacheService:
    """
    Application-level caching service.

    Wraps a ``CacheProvider`` and exposes domain-aware cache operations.
    All services should depend on this class rather than using
    ``CacheProvider`` directly.

    Usage (cache-aside):
        result = await cache_service.get_or_set(
            key=CacheKey.goal_list(str(user_id)),
            ttl=CacheTTL.GOAL_LIST,
            loader=lambda: goal_repo.get_all(user_id),
        )
    """

    def __init__(self, cache: Optional[CacheProvider]) -> None:
        """
        Args:
            cache: A ``CacheProvider`` implementation (e.g. ``RedisCache``).
                   If ``None``, the service operates in passthrough mode
                   (no caching — useful for tests).
        """
        self._cache = cache
        self._enabled = cache is not None

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a cached value. Returns None on miss or if disabled."""
        if not self._enabled:
            return None
        return await self._cache.get(key)

    async def set(self, key: str, value: Any, ttl: int) -> bool:
        """Store a value with a mandatory TTL (no unbounded caching)."""
        if not self._enabled:
            return False
        return await self._cache.set(key, value, ttl=ttl)

    async def delete(self, key: str) -> bool:
        """Delete a single cache key."""
        if not self._enabled:
            return False
        return await self._cache.delete(key)

    async def invalidate_pattern(self, pattern: str) -> int:
        """Delete all keys matching a glob pattern."""
        if not self._enabled:
            return 0
        count = await self._cache.clear_pattern(pattern)
        if count:
            logger.debug("Cache invalidated %d keys for pattern '%s'", count, pattern)
        return count

    async def bump_version(self, namespace: str, user_id: str) -> bool:
        """Increment a lightweight version counter used for ETag invalidation."""
        if not self._enabled or not getattr(self._cache, "redis", None):
            return False

        version_key = f"cache_version:{namespace}:{user_id}"
        await self._cache.redis.incr(version_key)
        return True

    async def get_version(self, namespace: str, user_id: str) -> int:
        """Return the current version counter for a namespace/user pair."""
        if not self._enabled or not getattr(self._cache, "redis", None):
            return 0

        version_key = f"cache_version:{namespace}:{user_id}"
        value = await self._cache.redis.get(version_key)
        if value is None:
            return 0

        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    # ------------------------------------------------------------------
    # Cache-aside helper
    # ------------------------------------------------------------------

    async def get_or_set(
        self,
        key: str,
        loader: Callable,
        ttl: int,
        serializer: Optional[Callable] = None,
    ) -> Any:
        """
        Cache-aside pattern.

        1. Try the cache.
        2. On miss, call ``loader()`` to fetch from the source of truth.
        3. Store the result with ``ttl``.
        4. Return the result.

        Args:
            key:        Cache key.
            loader:     Async (or sync) callable that fetches the data.
            ttl:        TTL in seconds for the cached value.
            serializer: Optional function applied to the loader result
                        before caching (e.g. converting SQLAlchemy models
                        to dicts).  The raw loader result is always returned.
        """
        cached = await self.get(key)
        if cached is not None:
            logger.debug("Cache HIT: %s", key)
            try:
                from app.core.metrics import CACHE_HIT
                CACHE_HIT.labels(cache_type="redis").inc()
            except Exception:
                pass
            return cached

        logger.debug("Cache MISS: %s", key)
        try:
            from app.core.metrics import CACHE_MISS
            CACHE_MISS.labels(cache_type="redis").inc()
        except Exception:
            pass

        import asyncio
        if asyncio.iscoroutinefunction(loader):
            result = await loader()
        else:
            result = loader()

        if result is not None:
            to_store = serializer(result) if serializer else result
            await self.set(key, to_store, ttl=ttl)

        return result

    # ------------------------------------------------------------------
    # Domain-specific invalidation helpers
    # ------------------------------------------------------------------

    async def invalidate_user_expenses(self, user_id: str) -> None:
        """Invalidate all expense caches for a user."""
        await self.invalidate_pattern(CacheKey.user_expenses_pattern(user_id))

    async def invalidate_user_budgets(self, user_id: str) -> None:
        """Invalidate all budget caches for a user."""
        await self.invalidate_pattern(CacheKey.user_budgets_pattern(user_id))

    async def invalidate_user_goals(self, user_id: str) -> None:
        """Invalidate all goal caches for a user."""
        await self.invalidate_pattern(CacheKey.user_goals_pattern(user_id))

    async def invalidate_all_user_data(self, user_id: str) -> None:
        """Invalidate ALL cached data for a user (use on account changes)."""
        await self.invalidate_pattern(CacheKey.user_all_pattern(user_id))
        await self.delete(CacheKey.user_profile(user_id))
        await self.delete(CacheKey.token_user(user_id))


# ---------------------------------------------------------------------------
# Null cache — drop-in replacement when Redis is unavailable
# ---------------------------------------------------------------------------

class NullCacheService(CacheService):
    """
    No-op cache service for use when Redis is unavailable or in unit tests.

    All operations succeed silently without touching any external system.
    """

    def __init__(self) -> None:
        super().__init__(cache=None)

    async def get_or_set(self, key: str, loader: Callable, ttl: int, serializer=None) -> Any:
        import asyncio
        if asyncio.iscoroutinefunction(loader):
            return await loader()
        return loader()
