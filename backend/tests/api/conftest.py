"""
Shared fixtures for tests/api/ — provides a TestClient with:
  • A properly-signed JWT (so auth middleware returns 401, not a crash)
  • get_current_user overridden with a mock user (for authenticated calls)
  • Lightweight in-memory DB + mock-Redis overrides
"""
import uuid
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.config import settings
from app.db.session import get_auth_db, get_data_db, AuthBase, DataBase
from app.dependencies import get_current_user, get_redis_cache
from app.db.models.auth import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_test_token(user_id: str) -> str:
    """Return a valid, properly-signed JWT for *user_id*."""
    expires = datetime.utcnow() + timedelta(hours=1)
    return jwt.encode(
        {"sub": user_id, "exp": expires, "type": "access"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def _make_mock_cache():
    """Return a lightweight async-mock cache provider."""
    cache = MagicMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    cache.delete = AsyncMock(return_value=True)
    cache.exists = AsyncMock(return_value=0)
    return cache


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def api_user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture(scope="function")
def api_user(api_user_id: uuid.UUID):
    """Lightweight mock User object used to override get_current_user."""
    user = MagicMock(spec=User)
    user.id = api_user_id
    user.email = "apitest@example.com"
    user.is_active = True
    user.is_verified = True
    user.created_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    return user


@pytest.fixture(scope="function")
def api_token(api_user_id: uuid.UUID) -> str:
    return _make_test_token(str(api_user_id))


@pytest.fixture(scope="function")
async def _api_auth_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(AuthBase.metadata.create_all)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(AuthBase.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="function")
async def _api_data_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(DataBase.metadata.create_all)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(DataBase.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="function")
def client(api_user, api_token, _api_auth_db, _api_data_db):
    """
    TestClient with:
    - get_current_user → api_user (bypasses JWT DB lookup entirely)
    - get_auth_db / get_data_db → in-memory SQLite
    - get_redis_cache → mock (no Redis required)
    - Authorization header pre-set with a valid JWT
    """
    mock_cache = _make_mock_cache()

    async def _override_current_user():
        return api_user

    async def _override_auth_db():
        yield _api_auth_db

    async def _override_data_db():
        yield _api_data_db

    app.dependency_overrides[get_current_user] = _override_current_user
    app.dependency_overrides[get_auth_db] = _override_auth_db
    app.dependency_overrides[get_data_db] = _override_data_db
    app.dependency_overrides[get_redis_cache] = lambda: mock_cache

    test_client = TestClient(app, raise_server_exceptions=False)
    test_client.headers.update({
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    })

    yield test_client

    for dep in [get_current_user, get_auth_db, get_data_db, get_redis_cache]:
        app.dependency_overrides.pop(dep, None)
