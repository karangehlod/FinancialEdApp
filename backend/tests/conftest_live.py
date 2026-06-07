"""
Live Integration Test Fixtures
===============================
These fixtures connect to the REAL PostgreSQL + Redis containers
spun up by docker-compose.dev.yml.

Used exclusively by tests/integration/live_* tests.
The conftest.py in the root still uses SQLite in-memory for fast unit tests.

Environment (set in backend/.env):
  AUTH_DB_HOST=localhost  AUTH_DB_PORT=55432  AUTH_DB_NAME=auth_db
  DATA_DB_HOST=localhost  DATA_DB_PORT=55432  DATA_DB_NAME=financial_ed_db
  REDIS_URL=redis://:finedu_redis_password@localhost:56379/0
"""
import uuid
import pytest
import pytest_asyncio
import httpx
from datetime import datetime, timedelta
from decimal import Decimal
from typing import AsyncGenerator

from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from jose import jwt

from app.main import app
from app.config import settings
from app.db.session import AuthBase, DataBase
from app.db.models.auth import User
from app.db.models.data import UserProfile
from app.core.security import hash_password


# ---------------------------------------------------------------------------
# Database engines pointing at the real Docker containers
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def auth_engine_live():
    """Async engine connected to the real auth PostgreSQL container."""
    engine = create_async_engine(
        settings.AUTH_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=5,
    )
    yield engine


@pytest.fixture(scope="session")
def data_engine_live():
    """Async engine connected to the real data PostgreSQL container."""
    engine = create_async_engine(
        settings.DATA_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=5,
    )
    yield engine


@pytest.fixture(scope="session")
def auth_session_factory(auth_engine_live):
    return async_sessionmaker(auth_engine_live, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def data_session_factory(data_engine_live):
    return async_sessionmaker(data_engine_live, class_=AsyncSession, expire_on_commit=False)


# ---------------------------------------------------------------------------
# Per-test isolated sessions with automatic rollback (no data pollution)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def auth_db(auth_session_factory) -> AsyncGenerator[AsyncSession, None]:
    """
    Auth DB session scoped to one test.
    Uses SAVEPOINT so every test starts clean without wiping the schema.
    """
    async with auth_session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest_asyncio.fixture
async def data_db(data_session_factory) -> AsyncGenerator[AsyncSession, None]:
    """Data DB session scoped to one test with rollback isolation."""
    async with data_session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


# ---------------------------------------------------------------------------
# User factory (creates real rows, rolled back after test)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def make_user(auth_db: AsyncSession, data_db: AsyncSession):
    """
    Factory that creates a verified User + matching UserProfile.
    Returns a helper callable: user = await make_user(email, password)
    """
    async def _make(
        email: str = None,
        password: str = "TestPass123!",
        is_verified: bool = True,
        is_active: bool = True,
    ) -> User:
        if email is None:
            email = f"test_{uuid.uuid4().hex[:8]}@example.com"

        user = User(
            id=uuid.uuid4(),
            email=email,
            password_hash=hash_password(password),
            is_active=is_active,
            is_verified=is_verified,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        auth_db.add(user)
        await auth_db.flush()  # get the PK without committing

        # Mirror the profile in the data DB
        profile = UserProfile(
            user_id=user.id,
            name=email.split("@")[0],
            country="IN",
            currency="INR",
            consent_given=True,
            consent_timestamp=datetime.utcnow(),
        )
        data_db.add(profile)
        await data_db.flush()
        return user

    return _make


# ---------------------------------------------------------------------------
# JWT token helpers
# ---------------------------------------------------------------------------

def _mint_token(user_id: uuid.UUID, minutes: int = 60) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(minutes=minutes),
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


@pytest.fixture
def auth_headers_for():
    """Returns a function: headers = auth_headers_for(user)"""
    def _headers(user: User) -> dict:
        return {
            "Authorization": f"Bearer {_mint_token(user.id)}",
            "Content-Type": "application/json",
        }
    return _headers


# ---------------------------------------------------------------------------
# HTTPX async client wired to the live FastAPI app
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def live_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    Async HTTP client that hits the real FastAPI app with real DB + Redis.
    No dependency overrides — everything is real.
    """
    async with httpx.AsyncClient(
        base_url="http://test",
        transport=ASGITransport(app=app),
        timeout=30.0,
    ) as client:
        yield client


@pytest_asyncio.fixture
async def authed_client(make_user, auth_headers_for) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Async client pre-authenticated as a freshly created user."""
    user = await make_user()
    headers = auth_headers_for(user)
    async with httpx.AsyncClient(
        base_url="http://test",
        transport=ASGITransport(app=app),
        headers=headers,
        timeout=30.0,
    ) as client:
        client.user = user  # attach for assertions in tests
        yield client
