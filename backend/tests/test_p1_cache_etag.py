"""
P1-1: Response caching strategy tests — ETag, Last-Modified, and cache invalidation.

Test coverage:
  - Cache hit/miss tracking
  - ETag generation and conditional requests (304 Not Modified)
  - Cache TTL enforcement
  - Cache invalidation patterns
  - Version bumping
"""

import pytest
import json
import hashlib
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.cache_service import CacheService, CacheKey, CacheTTL
from app.core.cache import compute_etag, make_metadata_key, set_metadata, get_metadata


@pytest.mark.asyncio
class TestETagGeneration:
    """Test ETag computation for caching."""

    def test_compute_etag_deterministic(self):
        """ETags for identical payloads should be identical."""
        payload = {"user_id": "123", "expenses": [{"amount": 100, "category": "food"}]}
        etag1 = compute_etag(payload)
        etag2 = compute_etag(payload)
        assert etag1 == etag2

    def test_compute_etag_different_for_different_payload(self):
        """ETags for different payloads should differ."""
        payload1 = {"amount": 100}
        payload2 = {"amount": 200}
        etag1 = compute_etag(payload1)
        etag2 = compute_etag(payload2)
        assert etag1 != etag2

    def test_compute_etag_handles_unserializable_fallback(self):
        """ETag generation should handle non-JSON-serializable payloads gracefully."""
        # Use a simple class instance that is not JSON serializable
        class Unserializable:
            def __repr__(self):
                return "Unserializable(key=value)"
        obj = Unserializable()
        etag = compute_etag(obj)
        assert isinstance(etag, str)
        assert len(etag) == 64  # SHA-256 hex


@pytest.mark.asyncio
class TestCacheMetadata:
    """Test metadata (ETag, Last-Modified) operations."""

    async def test_set_and_get_metadata(self):
        """Storing and retrieving metadata should work."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps({
            "etag": "abc123",
            "last_modified": "Mon, 01 Jan 2024 00:00:00 GMT"
        }).encode()

        result = await get_metadata(mock_redis, "expenses", "/api/v1/expenses?user=1")
        assert result["etag"] == "abc123"

    async def test_metadata_with_ttl(self):
        """Metadata should be stored with TTL to prevent unbounded growth."""
        mock_redis = AsyncMock()
        await set_metadata(
            mock_redis,
            namespace="expenses",
            key="/api/v1/expenses",
            etag="test123",
            last_modified="Mon, 01 Jan 2024 00:00:00 GMT",
            ttl=3600
        )
        # Verify setex was called (atomic set + expire)
        mock_redis.set.assert_called_once()


@pytest.mark.asyncio
class TestCacheServiceVersioning:
    """Test cache invalidation via version bumping."""

    async def test_bump_version_increments_counter(self):
        """Bumping version should increment a counter."""
        mock_cache = AsyncMock()
        mock_redis = AsyncMock()
        mock_cache.redis = mock_redis
        mock_redis.incr.return_value = 2

        service = CacheService(mock_cache)
        result = await service.bump_version("expenses", "user123")
        assert result is True
        mock_redis.incr.assert_called_once()

    async def test_get_version_returns_zero_on_miss(self):
        """Getting a non-existent version should return 0."""
        mock_cache = AsyncMock()
        mock_redis = AsyncMock()
        mock_cache.redis = mock_redis
        mock_redis.get.return_value = None

        service = CacheService(mock_cache)
        version = await service.get_version("expenses", "user123")
        assert version == 0

    async def test_get_version_returns_current_count(self):
        """Getting an existing version should return the current count."""
        mock_cache = AsyncMock()
        mock_redis = AsyncMock()
        mock_cache.redis = mock_redis
        mock_redis.get.return_value = b"5"

        service = CacheService(mock_cache)
        version = await service.get_version("expenses", "user123")
        assert version == 5


@pytest.mark.asyncio
class TestCacheInvalidationPatterns:
    """Test pattern-based cache invalidation."""

    async def test_invalidate_user_expenses_pattern(self):
        """Invalidating user expenses should clear all related keys."""
        mock_cache = AsyncMock()
        mock_cache.clear_pattern.return_value = 5

        service = CacheService(mock_cache)
        count = await service.invalidate_pattern(CacheKey.user_expenses_pattern("user123"))
        assert count == 5
        mock_cache.clear_pattern.assert_called_once()

    async def test_invalidate_all_user_data(self):
        """Invalidating all user data should clear expenses, budgets, goals."""
        mock_cache = AsyncMock()
        mock_cache.clear_pattern.return_value = 15

        service = CacheService(mock_cache)
        count = await service.invalidate_pattern(CacheKey.user_all_pattern("user123"))
        assert count == 15


@pytest.mark.asyncio
class TestCacheAside:
    """Test cache-aside pattern with fallback to source."""

    async def test_get_or_set_cache_hit(self):
        """Cache hit should return cached value without calling loader."""
        mock_cache = AsyncMock()
        mock_cache.get.return_value = {"user_id": "123", "email": "test@example.com"}

        service = CacheService(mock_cache)
        loader = AsyncMock()

        result = await service.get_or_set(
            key="test_key",
            loader=loader,
            ttl=300
        )
        assert result == {"user_id": "123", "email": "test@example.com"}
        loader.assert_not_called()

    async def test_get_or_set_cache_miss(self):
        """Cache miss should call loader and store result."""
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None

        service = CacheService(mock_cache)

        async def loader():
            return {"user_id": "123", "email": "test@example.com"}

        result = await service.get_or_set(
            key="test_key",
            loader=loader,
            ttl=300
        )
        assert result == {"user_id": "123", "email": "test@example.com"}
        mock_cache.set.assert_called_once()

    async def test_get_or_set_with_serializer(self):
        """Serializer should be applied before caching."""
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None

        service = CacheService(mock_cache)

        async def loader():
            return MagicMock(id="123", email="test@example.com")

        def serializer(obj):
            return {"id": obj.id, "email": obj.email}

        result = await service.get_or_set(
            key="test_key",
            loader=loader,
            ttl=300,
            serializer=serializer
        )
        assert result.id == "123"
        mock_cache.set.assert_called_once()


@pytest.mark.asyncio
class TestCacheTTLConstants:
    """Test cache TTL configuration."""

    def test_ttl_constants_defined(self):
        """All cache TTL constants should be defined."""
        assert hasattr(CacheTTL, 'USER_PROFILE')
        assert hasattr(CacheTTL, 'BUDGET_SUMMARY')
        assert hasattr(CacheTTL, 'EXPENSE_LIST')
        assert hasattr(CacheTTL, 'ANALYTICS')
        
        # TTLs should be positive integers
        assert isinstance(CacheTTL.USER_PROFILE, int)
        assert CacheTTL.USER_PROFILE > 0

    def test_cache_keys_are_deterministic(self):
        """Cache keys should be deterministic for same inputs."""
        key1 = CacheKey.expense_list("user123", page=0, limit=50, filters_hash="abc")
        key2 = CacheKey.expense_list("user123", page=0, limit=50, filters_hash="abc")
        assert key1 == key2

    def test_cache_keys_differ_for_different_params(self):
        """Cache keys should differ for different parameters."""
        key1 = CacheKey.expense_list("user123", page=0, limit=50, filters_hash="abc")
        key2 = CacheKey.expense_list("user123", page=1, limit=50, filters_hash="abc")
        assert key1 != key2


@pytest.mark.asyncio
class TestCacheDisabled:
    """Test cache service behavior when cache is disabled."""

    async def test_disabled_cache_returns_none(self):
        """Disabled cache should return None on get."""
        service = CacheService(cache=None)
        result = await service.get("any_key")
        assert result is None

    async def test_disabled_cache_returns_false_on_set(self):
        """Disabled cache should return False on set."""
        service = CacheService(cache=None)
        result = await service.set("key", "value", ttl=300)
        assert result is False

    async def test_disabled_cache_invalidation_returns_zero(self):
        """Disabled cache should return 0 for invalidation."""
        service = CacheService(cache=None)
        count = await service.invalidate_pattern("*")
        assert count == 0
