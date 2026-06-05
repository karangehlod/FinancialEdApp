import os
import asyncio
import pytest
from types import SimpleNamespace
from datetime import datetime, timedelta
from jose import jwt

from app.config import settings
from app.core.cache_service import CacheKey
from app.main import app as app_module
from app.dependencies import get_current_user
from app.db.models.auth import User

from fastapi.security import HTTPAuthorizationCredentials


pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(os.getenv('TEST_REAL_REDIS', '0') not in ('1', 'true', 'True') or not getattr(settings, 'REDIS_URL', None), reason="Requires real Redis (TEST_REAL_REDIS=1 and REDIS_URL)")
async def test_token_user_cache_avoids_db_lookup_and_respects_ttl(monkeypatch):
    """Integration test asserting token->user cache is used and TTL is aligned with access token expiry."""
    # Create a Redis client and ensure app.state.cache points to it
    from redis import asyncio as aioredis
    from app.core.provider_implementations import RedisCache

    redis_client = aioredis.from_url(settings.REDIS_URL, encoding='utf-8', decode_responses=True)
    await redis_client.ping()
    redis_cache = RedisCache(redis_client)

    # Attach to app state for dependencies
    app_module.state.cache = redis_cache

    # Create a sample user and token
    user_id = "550e8400-e29b-41d4-a716-446655440000"
    user = User.__new__(User)
    user.id = user_id
    user.email = "cachetest@example.com"
    user.is_active = True
    user.is_verified = True

    # Create access token with expiry equal to settings.ACCESS_TOKEN_EXPIRE_MINUTES
    expires = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = jwt.encode({"sub": user_id, "exp": expires, "type": "access"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    # Populate cache as AuthService would do
    cache_key = CacheKey.token_user(user_id)
    await redis_cache.set(cache_key, {"id": user_id, "email": user.email, "is_active": True, "is_verified": True}, ttl=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)

    # Prepare credentials and fake request
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    fake_request = SimpleNamespace(app=app_module)

    # Monkeypatch UserRepository so we can detect DB access
    call_count = {"count": 0}

    class DummyRepo:
        def __init__(self, db):
            pass
        async def get_user_by_id(self, uid):
            call_count['count'] += 1
            # Return a user object as usual
            return user

    monkeypatch.setattr('app.dependencies.UserRepository', DummyRepo)

    # Call get_current_user - should hit cache and NOT call DB
    result = await get_current_user(fake_request, credentials=creds, db=None)
    assert result.email == user.email
    assert call_count['count'] == 0

    # Check TTL on Redis key is roughly settings.ACCESS_TOKEN_EXPIRE_MINUTES*60
    ttl = await redis_client.ttl(cache_key)
    assert ttl <= settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert ttl > 0

    # Evict cache and call again - should trigger DB lookup
    await redis_client.delete(cache_key)
    result2 = await get_current_user(fake_request, credentials=creds, db=None)
    assert call_count['count'] == 1

    # Cleanup
    await redis_client.close()
