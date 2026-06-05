import asyncio
import pytest
from types import SimpleNamespace

from app.main import lifespan, app
from app.core.provider_implementations import RedisCache
from app.core.cache_service import NullCacheService


@pytest.mark.asyncio
async def test_app_state_cache_with_redis(monkeypatch):
    """When REDIS_URL is reachable, app.state.cache should be a RedisCache or wrapped CacheService."""
    # Create a fake redis client with minimal interface
    class DummyRedis:
        async def ping(self):
            return True
        async def get(self, k):
            return None
        async def set(self, k, v, *a, **kw):
            return True
        async def setex(self, k, ttl, v):
            return True
        async def delete(self, *keys):
            return len(keys)
        async def incr(self, k):
            return 1
        async def exists(self, k):
            return 0
        async def aclose(self):
            pass
        # For pubsub manager compatibility
        def pubsub(self, **kw):
            from unittest.mock import AsyncMock, MagicMock
            ps = MagicMock()
            ps.subscribe = AsyncMock()
            ps.unsubscribe = AsyncMock()
            ps.aclose = AsyncMock()
            ps.listen = AsyncMock(return_value=aiter([]))
            return ps
        async def publish(self, channel, message):
            return 0
    dummy = DummyRedis()

    # Monkeypatch redis.asyncio.from_url to return dummy client synchronously
    # (the real redis.asyncio.from_url is NOT a coroutine — it returns a client directly)
    def fake_from_url(url, **kwargs):
        return dummy

    monkeypatch.setattr('redis.asyncio.from_url', fake_from_url, raising=False)

    # Run lifespan to initialise app.state
    async with lifespan(app):
        cache = getattr(app.state, 'cache', None)
        assert cache is not None
        # RedisCache type or a CacheService wrapping it
        from app.core.provider_implementations import RedisCache
        assert isinstance(cache, RedisCache) or hasattr(cache, '_cache')


@pytest.mark.asyncio
async def test_app_state_cache_without_redis(monkeypatch):
    """When REDIS_URL is not reachable, app.state.cache should be a NullCacheService."""
    # Monkeypatch redis.asyncio.from_url to return a client that fails ping
    class FailRedis:
        async def ping(self):
            raise RuntimeError('redis down')
        async def aclose(self):
            pass

    def fake_from_url(url, **kwargs):
        return FailRedis()

    monkeypatch.setattr('redis.asyncio.from_url', fake_from_url, raising=False)

    async with lifespan(app):
        cache = getattr(app.state, 'cache', None)
        assert cache is not None
        # Should be the NullCacheService instance
        from app.core.cache_service import NullCacheService
        assert isinstance(cache, NullCacheService) or isinstance(getattr(app.state, 'cache_service', None), NullCacheService)
