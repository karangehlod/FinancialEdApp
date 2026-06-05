import asyncio
import pytest
from datetime import datetime, timedelta, timezone

from app.core.rate_limiting import RedisRateLimiter
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.services.auth_service import AuthService
from app.core.provider_implementations import JWTTokenProvider, BcryptPasswordHasher

# These tests are integration-style and expect a running Redis & test DB.
# They are intended as verification scripts — run them during CI or locally
# with docker-compose that brings up test Postgres + Redis.

pytestmark = pytest.mark.skip(reason="Requires live Redis and test DB — run with docker-compose")

@pytest.mark.asyncio
async def test_rate_limiter_increment(redis_client):
    limiter = RedisRateLimiter(redis_client)
    identifier = f"test:{datetime.utcnow().timestamp()}"

    allowed, count = await limiter.check_and_increment(identifier, limit=2, window=5)
    assert allowed

    allowed, count = await limiter.check_and_increment(identifier, limit=2, window=5)
    assert allowed

    allowed, count = await limiter.check_and_increment(identifier, limit=2, window=5)
    assert not allowed

@pytest.mark.asyncio
async def test_refresh_token_rotation(auth_db_session, user_factory):
    # Setup repositories and providers
    refresh_repo = RefreshTokenRepository(auth_db_session)
    pwd = BcryptPasswordHasher(rounds=4)
    jwt = JWTTokenProvider(secret_key='test-secret', algorithm='HS256', access_token_expire_minutes=30, refresh_token_expire_days=7)

    user = await user_factory()

    # Issue initial refresh token
    refresh_token = jwt.create_refresh_token(data={"sub": str(user.id), "type": "refresh"})
    token_hash = jwt._external_hash_func(refresh_token) if hasattr(jwt, '_external_hash_func') else None
    assert token_hash is not None

    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7)
    created = await refresh_repo.create(user_id=user.id, token_hash=token_hash, expires_at=expires_at, auto_commit=True)
    assert created is not None

    # Rotate
    new_refresh = jwt.create_refresh_token(data={"sub": str(user.id), "type": "refresh"})
    new_hash = jwt._external_hash_func(new_refresh)
    new_expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7)

    await refresh_repo.rotate(old_token_hash=token_hash, new_user_id=user.id, new_token_hash=new_hash, new_expires_at=new_expires)

    # Old token should be revoked
    old = await refresh_repo.get_valid(token_hash)
    assert old is None

    # New token should be present
    new_rec = await refresh_repo.get_valid(new_hash)
    assert new_rec is not None
