"""
Rate limiting implementation using Redis sliding window algorithm.

Design:
  - Algorithm: Sliding window via Redis sorted sets + atomic Lua script
  - Key namespacing:
      Authenticated:   rate_limit:user:{user_id}:{endpoint_group}
      Unauthenticated: rate_limit:ip:{client_ip}:{endpoint_group}
  - Fail-open on Redis errors (availability > strictness)
  - Per-route limits via RateLimitConfig
  - Exposes X-RateLimit-{Limit,Remaining,Reset} on every response
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lua script for atomic sliding-window increment
# Returns [allowed (1|0), current_count]
# ---------------------------------------------------------------------------
_SLIDING_WINDOW_LUA = """
local key        = KEYS[1]
local now        = tonumber(ARGV[1])
local window     = tonumber(ARGV[2])
local limit      = tonumber(ARGV[3])
local window_start = now - window

-- Remove expired entries
redis.call('ZREMRANGEBYSCORE', key, 0, window_start)

-- Count current entries
local count = redis.call('ZCARD', key)

if count < limit then
    -- Atomically add this request
    redis.call('ZADD', key, now, now .. ':' .. math.random(1, 1000000))
    redis.call('EXPIRE', key, math.ceil(window))
    return {1, count + 1}
else
    return {0, count}
end
"""


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class RateLimiter(ABC):
    """Abstract base class for rate limiting strategies."""

    @abstractmethod
    async def check_and_increment(
        self,
        identifier: str,
        limit: int,
        window: int,
    ) -> Tuple[bool, int]:
        """
        Atomically check the limit and increment the counter.

        Args:
            identifier: Unique key (user_id, IP, etc.)
            limit:      Maximum requests allowed in the window
            window:     Time window in seconds

        Returns:
            (allowed: bool, current_count: int)
        """

    @abstractmethod
    async def get_remaining(self, identifier: str, limit: int, window: int) -> int:
        """Return the number of remaining requests in the current window."""

    @abstractmethod
    async def reset(self, identifier: str) -> bool:
        """Reset the counter for an identifier (e.g., on logout)."""


# ---------------------------------------------------------------------------
# Redis sliding-window implementation
# ---------------------------------------------------------------------------

class RedisRateLimiter(RateLimiter):
    """
    Redis-based sliding window rate limiter using an atomic Lua script.

    The Lua script guarantees that the ZCARD + ZADD sequence is atomic,
    eliminating the race condition present in naive get/set implementations.
    """

    KEY_PREFIX = "rate_limit"

    def __init__(self, redis_client) -> None:
        self._redis = redis_client
        self._script = None  # Registered Lua script handle

    async def _get_script(self):
        """Lazily register the Lua script with Redis (cached after first call)."""
        if self._script is None:
            self._script = self._redis.register_script(_SLIDING_WINDOW_LUA)
        return self._script

    def _build_key(self, identifier: str) -> str:
        return f"{self.KEY_PREFIX}:{identifier}"

    async def check_and_increment(
        self,
        identifier: str,
        limit: int,
        window: int,
    ) -> Tuple[bool, int]:
        """Atomically check + increment using the Lua script."""
        try:
            script = await self._get_script()
            key = self._build_key(identifier)
            now = time.time()
            result = await script(keys=[key], args=[now, window, limit])
            allowed = bool(result[0])
            count = int(result[1])
            return allowed, count
        except Exception as exc:
            logger.error("Rate limiter Redis error (failing open): %s", exc)
            # Fail open — prefer availability over strict enforcement
            return True, 0

    async def get_remaining(self, identifier: str, limit: int, window: int) -> int:
        """Return remaining requests without incrementing."""
        try:
            key = self._build_key(identifier)
            now = time.time()
            window_start = now - window
            await self._redis.zremrangebyscore(key, 0, window_start)
            count = await self._redis.zcard(key)
            return max(0, limit - count)
        except Exception as exc:
            logger.error("Rate limiter get_remaining error: %s", exc)
            return limit

    async def reset(self, identifier: str) -> bool:
        """Delete all rate-limit keys for an identifier."""
        try:
            key = self._build_key(identifier)
            await self._redis.delete(key)
            return True
        except Exception as exc:
            logger.error("Rate limiter reset error: %s", exc)
            return False


# ---------------------------------------------------------------------------
# Route-level configuration
# ---------------------------------------------------------------------------

@dataclass
class RouteRateLimit:
    """Rate limit rule for a specific route/group."""
    limit: int          # Max requests allowed
    window: int         # Time window in seconds
    group: str = ""     # Endpoint group label for key namespacing


@dataclass
class RateLimitConfig:
    """
    Centralised rate-limit rules per endpoint group.

    All limits are read from app settings so they can be changed via
    environment variables without rebuilding the image.

    Rules are matched by prefix; the most specific prefix wins.
    """

    rules: Dict[str, RouteRateLimit] = field(default_factory=dict)

    def __post_init__(self):
        """Populate rules from settings after dataclass init."""
        from app.config import settings
        self.rules = {
            "/api/v1/auth/login":           RouteRateLimit(limit=settings.RATE_LIMIT_LOGIN_LIMIT,
                                                           window=settings.RATE_LIMIT_LOGIN_WINDOW,
                                                           group="auth_login"),
            "/api/v1/auth/register":        RouteRateLimit(limit=settings.RATE_LIMIT_REGISTER_LIMIT,
                                                           window=settings.RATE_LIMIT_REGISTER_WINDOW,
                                                           group="auth_register"),
            "/api/v1/auth/forgot-password": RouteRateLimit(limit=settings.RATE_LIMIT_FORGOT_PASSWORD_LIMIT,
                                                           window=settings.RATE_LIMIT_FORGOT_PASSWORD_WINDOW,
                                                           group="auth_forgot"),
            "/api/v1/auth/refresh":         RouteRateLimit(limit=settings.RATE_LIMIT_REFRESH_LIMIT,
                                                           window=settings.RATE_LIMIT_REFRESH_WINDOW,
                                                           group="auth_refresh"),
            "/api/v1/auth/oauth":           RouteRateLimit(limit=settings.RATE_LIMIT_OAUTH_LIMIT,
                                                           window=settings.RATE_LIMIT_OAUTH_WINDOW,
                                                           group="auth_oauth"),
            "/api/v1/exports":              RouteRateLimit(limit=settings.RATE_LIMIT_EXPORTS_LIMIT,
                                                           window=settings.RATE_LIMIT_EXPORTS_WINDOW,
                                                           group="exports"),
            "/api/v1/expenses/analytics":   RouteRateLimit(limit=settings.RATE_LIMIT_ANALYTICS_LIMIT,
                                                           window=settings.RATE_LIMIT_ANALYTICS_WINDOW,
                                                           group="analytics"),
            "/api/v1/expenses/trends":      RouteRateLimit(limit=settings.RATE_LIMIT_ANALYTICS_LIMIT,
                                                           window=settings.RATE_LIMIT_ANALYTICS_WINDOW,
                                                           group="analytics"),
            "default_authenticated":        RouteRateLimit(limit=settings.RATE_LIMIT_DEFAULT_AUTH_LIMIT,
                                                           window=settings.RATE_LIMIT_DEFAULT_AUTH_WINDOW,
                                                           group="api"),
            "default_unauthenticated":      RouteRateLimit(limit=settings.RATE_LIMIT_DEFAULT_UNAUTH_LIMIT,
                                                           window=settings.RATE_LIMIT_DEFAULT_UNAUTH_WINDOW,
                                                           group="public"),
        }

    def get_rule(self, path: str, authenticated: bool = True) -> RouteRateLimit:
        """Return the most-specific matching rule for a path."""
        for rule_path in sorted(self.rules, key=len, reverse=True):
            if rule_path.startswith("default_"):
                continue
            if path.startswith(rule_path):
                return self.rules[rule_path]
        default_key = "default_authenticated" if authenticated else "default_unauthenticated"
        return self.rules[default_key]


# Singleton configuration instance — created once, reads from settings at import time
rate_limit_config = RateLimitConfig()
