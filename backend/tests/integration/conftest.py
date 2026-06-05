"""
Shared fixtures for integration (BDD) tests.

Sets up in-memory SQLite databases and Redis mocks so tests run without
a live PostgreSQL or Redis instance.
"""
import pytest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import AuthBase, DataBase, get_auth_db, get_data_db
from app.dependencies import get_redis_cache


# ---------------------------------------------------------------------------
# Shared SQLite engine helper
# ---------------------------------------------------------------------------

def _make_sqlite_engines():
    """Create fresh in-memory SQLite async engines for auth and data DBs."""
    auth_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    data_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    return auth_engine, data_engine


# ---------------------------------------------------------------------------
# pytest fixture: patched_client
# Provides a TestClient wired to SQLite + mocked Redis for BDD tests.
# ---------------------------------------------------------------------------

@pytest.fixture
def patched_client():
    """
    TestClient with:
      - In-memory SQLite databases for auth and data (no real Postgres needed)
      - Mocked Redis client and rate limiter (no real Redis needed)
    """
    import asyncio

    auth_engine, data_engine = _make_sqlite_engines()

    # Set up schemas synchronously via a new event loop
    loop = asyncio.new_event_loop()

    async def _create_schemas():
        async with auth_engine.begin() as conn:
            await conn.run_sync(AuthBase.metadata.create_all)
        async with data_engine.begin() as conn:
            await conn.run_sync(DataBase.metadata.create_all)

    loop.run_until_complete(_create_schemas())

    AuthSession = async_sessionmaker(auth_engine, class_=AsyncSession, expire_on_commit=False)
    DataSession = async_sessionmaker(data_engine, class_=AsyncSession, expire_on_commit=False)

    mock_redis = AsyncMock()
    mock_redis.evalsha = AsyncMock(return_value=[1, 1])
    mock_redis.eval = AsyncMock(return_value=[1, 1])
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=1)
    mock_redis.zremrangebyscore = AsyncMock()
    mock_redis.zcard = AsyncMock(return_value=0)
    mock_redis.zadd = AsyncMock()
    mock_redis.expire = AsyncMock()
    mock_redis.aclose = AsyncMock()

    mock_limiter = AsyncMock()
    mock_limiter.check_and_increment = AsyncMock(return_value=(True, 1))

    async def override_get_auth_db():
        async with AuthSession() as session:
            yield session

    async def override_get_data_db():
        async with DataSession() as session:
            yield session

    app.dependency_overrides[get_auth_db] = override_get_auth_db
    app.dependency_overrides[get_data_db] = override_get_data_db
    app.dependency_overrides[get_redis_cache] = lambda: None

    with patch("redis.asyncio.from_url", return_value=mock_redis):
        with patch("app.startup_checks.perform_startup_checks", return_value=True):
            with TestClient(app) as client:
                client._mock_redis = mock_redis
                client._mock_limiter = mock_limiter
                yield client

    # Teardown
    app.dependency_overrides.pop(get_auth_db, None)
    app.dependency_overrides.pop(get_data_db, None)
    app.dependency_overrides.pop(get_redis_cache, None)

    async def _drop_schemas():
        async with auth_engine.begin() as conn:
            await conn.run_sync(AuthBase.metadata.drop_all)
        async with data_engine.begin() as conn:
            await conn.run_sync(DataBase.metadata.drop_all)
        await auth_engine.dispose()
        await data_engine.dispose()

    loop.run_until_complete(_drop_schemas())
    loop.close()
