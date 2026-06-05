"""Comprehensive tests for cache_service.py — CacheKey, CacheTTL, CacheService, NullCacheService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.cache_service import CacheKey, CacheTTL, CacheService, NullCacheService


# ============================================================================
# CacheKey builder tests
# ============================================================================

class TestCacheKey:
    """Test all CacheKey static methods."""

    def test_user_profile(self):
        assert CacheKey.user_profile("u1") == "cache:profile:u1"

    def test_expense_list(self):
        assert CacheKey.expense_list("u1", 0, 50, "abc") == "cache:expenses:u1:list:0:50:abc"

    def test_expense_summary(self):
        assert CacheKey.expense_summary("u1", "2024-01", "2024-12") == "cache:expenses:u1:summary:2024-01:2024-12"

    def test_expense_analytics(self):
        assert CacheKey.expense_analytics("u1") == "cache:expenses:u1:analytics"

    def test_budget_list(self):
        assert CacheKey.budget_list("u1", "2024-01") == "cache:budgets:u1:2024-01"

    def test_budget_summary(self):
        assert CacheKey.budget_summary("u1", "2024-01") == "cache:budgets:u1:summary:2024-01"

    def test_goal_list(self):
        assert CacheKey.goal_list("u1") == "cache:goals:u1:list"

    def test_token_user(self):
        assert CacheKey.token_user("u1") == "cache:token_user:u1"

    def test_user_expenses_pattern(self):
        assert CacheKey.user_expenses_pattern("u1") == "cache:expenses:u1:*"

    def test_user_budgets_pattern(self):
        assert CacheKey.user_budgets_pattern("u1") == "cache:budgets:u1:*"

    def test_user_goals_pattern(self):
        assert CacheKey.user_goals_pattern("u1") == "cache:goals:u1:*"

    def test_user_all_pattern(self):
        assert CacheKey.user_all_pattern("u1") == "cache:*:u1:*"

    def test_hash_filters_dict(self):
        h = CacheKey.hash_filters({"a": 1, "b": 2})
        assert isinstance(h, str) and len(h) == 8

    def test_hash_filters_object(self):
        obj = MagicMock()
        obj.__dict__ = {"x": 10}
        h = CacheKey.hash_filters(obj)
        assert isinstance(h, str)

    def test_hash_filters_fallback(self):
        """When serialisation fails, return 'nf'."""
        h = CacheKey.hash_filters(object())  # can't json-serialise
        assert h == "nf"


# ============================================================================
# CacheTTL constants
# ============================================================================

class TestCacheTTL:
    def test_ttl_constants_exist(self):
        assert CacheTTL.USER_PROFILE == 1800
        assert CacheTTL.BUDGET_SUMMARY == 300
        assert CacheTTL.EXPENSE_LIST == 120
        assert CacheTTL.EXPENSE_SUMMARY == 300
        assert CacheTTL.GOAL_LIST == 300
        assert CacheTTL.ANALYTICS == 600
        assert CacheTTL.TOKEN_USER == 1800


# ============================================================================
# CacheService — enabled (with provider)
# ============================================================================

class TestCacheServiceEnabled:
    """Tests for CacheService with a real (mocked) CacheProvider."""

    @pytest.fixture
    def mock_provider(self):
        p = AsyncMock()
        p.get = AsyncMock(return_value=None)
        p.set = AsyncMock(return_value=True)
        p.delete = AsyncMock(return_value=True)
        p.clear_pattern = AsyncMock(return_value=5)
        return p

    @pytest.fixture
    def cache(self, mock_provider):
        return CacheService(mock_provider)

    @pytest.mark.asyncio
    async def test_get_returns_value(self, cache, mock_provider):
        mock_provider.get.return_value = {"foo": 1}
        result = await cache.get("key")
        assert result == {"foo": 1}

    @pytest.mark.asyncio
    async def test_get_cache_miss(self, cache, mock_provider):
        mock_provider.get.return_value = None
        result = await cache.get("key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_stores_value(self, cache, mock_provider):
        result = await cache.set("key", "value", ttl=60)
        assert result is True
        mock_provider.set.assert_called_once_with("key", "value", ttl=60)

    @pytest.mark.asyncio
    async def test_delete_key(self, cache, mock_provider):
        result = await cache.delete("key")
        assert result is True
        mock_provider.delete.assert_called_once_with("key")

    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, cache, mock_provider):
        count = await cache.invalidate_pattern("cache:expenses:u1:*")
        assert count == 5

    @pytest.mark.asyncio
    async def test_get_or_set_cache_hit(self, cache, mock_provider):
        mock_provider.get.return_value = {"cached": True}
        loader = AsyncMock()

        result = await cache.get_or_set("key", loader, ttl=60)

        assert result == {"cached": True}
        loader.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_set_cache_miss_async_loader(self, cache, mock_provider):
        mock_provider.get.return_value = None
        loader = AsyncMock(return_value={"fresh": True})

        result = await cache.get_or_set("key", loader, ttl=60)

        assert result == {"fresh": True}
        mock_provider.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_set_cache_miss_sync_loader(self, cache, mock_provider):
        mock_provider.get.return_value = None

        def sync_loader():
            return [1, 2, 3]

        result = await cache.get_or_set("key", sync_loader, ttl=60)
        assert result == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_get_or_set_with_serializer(self, cache, mock_provider):
        mock_provider.get.return_value = None
        loader = AsyncMock(return_value={"id": 1})
        serializer = lambda x: {"serialized": True}

        result = await cache.get_or_set("key", loader, ttl=60, serializer=serializer)

        assert result == {"id": 1}  # raw loader result returned
        # But serialized version stored
        mock_provider.set.assert_called_once_with("key", {"serialized": True}, ttl=60)

    @pytest.mark.asyncio
    async def test_get_or_set_none_result_not_cached(self, cache, mock_provider):
        mock_provider.get.return_value = None
        loader = AsyncMock(return_value=None)

        result = await cache.get_or_set("key", loader, ttl=60)

        assert result is None
        mock_provider.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalidate_user_expenses(self, cache, mock_provider):
        await cache.invalidate_user_expenses("u1")
        mock_provider.clear_pattern.assert_called_once_with("cache:expenses:u1:*")

    @pytest.mark.asyncio
    async def test_invalidate_user_budgets(self, cache, mock_provider):
        await cache.invalidate_user_budgets("u1")
        mock_provider.clear_pattern.assert_called_once_with("cache:budgets:u1:*")

    @pytest.mark.asyncio
    async def test_invalidate_user_goals(self, cache, mock_provider):
        await cache.invalidate_user_goals("u1")
        mock_provider.clear_pattern.assert_called_once_with("cache:goals:u1:*")

    @pytest.mark.asyncio
    async def test_invalidate_all_user_data(self, cache, mock_provider):
        await cache.invalidate_all_user_data("u1")
        assert mock_provider.clear_pattern.call_count == 1
        assert mock_provider.delete.call_count == 2


# ============================================================================
# CacheService — disabled (no provider)
# ============================================================================

class TestCacheServiceDisabled:
    """Tests for CacheService when cache is None (passthrough mode)."""

    @pytest.fixture
    def cache(self):
        return CacheService(None)

    @pytest.mark.asyncio
    async def test_get_returns_none(self, cache):
        assert await cache.get("key") is None

    @pytest.mark.asyncio
    async def test_set_returns_false(self, cache):
        assert await cache.set("key", "v", ttl=60) is False

    @pytest.mark.asyncio
    async def test_delete_returns_false(self, cache):
        assert await cache.delete("key") is False

    @pytest.mark.asyncio
    async def test_invalidate_pattern_returns_zero(self, cache):
        assert await cache.invalidate_pattern("*") == 0


# ============================================================================
# NullCacheService
# ============================================================================

class TestNullCacheService:
    @pytest.mark.asyncio
    async def test_get_or_set_calls_async_loader(self):
        svc = NullCacheService()
        loader = AsyncMock(return_value=42)
        result = await svc.get_or_set("k", loader, ttl=60)
        assert result == 42

    @pytest.mark.asyncio
    async def test_get_or_set_calls_sync_loader(self):
        svc = NullCacheService()
        result = await svc.get_or_set("k", lambda: 99, ttl=60)
        assert result == 99
