"""
Auto-skip live tests when required infrastructure (PostgreSQL/Redis) is unavailable.

Live tests require the Docker containers from docker-compose.dev.yml to be running.
Start them with: docker compose -f docker-compose.dev.yml up -d
"""
import socket
import uuid
import pytest
import pytest_asyncio
import httpx
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from jose import jwt

from app.main import app
from app.config import settings
from app.db.models.auth import User
from app.db.models.data import UserProfile
from app.core.security_compat import hash_password


def _port_is_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Return True if a TCP connection can be established."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError, socket.timeout):
        return False


def _check_infrastructure() -> str | None:
    """Return a skip reason string if any required service is unreachable, else None."""
    checks = [
        (getattr(settings, "AUTH_DB_HOST", "localhost"),
         int(getattr(settings, "AUTH_DB_PORT", 55432)),
         "Auth PostgreSQL"),
        (getattr(settings, "DATA_DB_HOST", "localhost"),
         int(getattr(settings, "DATA_DB_PORT", 55433)),
         "Data PostgreSQL"),
    ]
    for host, port, name in checks:
        if not _port_is_open(host, port):
            return (
                f"{name} ({host}:{port}) is not reachable. "
                "Start containers with: docker compose -f docker-compose.dev.yml up -d"
            )
    return None


# Cache the result so the port check runs at most once per session
_skip_reason = _check_infrastructure()


def pytest_collection_modifyitems(config, items):
    """Skip every test in the live/ directory when infrastructure is absent."""
    if _skip_reason is None:
        return
    skip_marker = pytest.mark.skip(reason=_skip_reason)
    for item in items:
        if "/live/" in str(item.fspath):
            item.add_marker(skip_marker)


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
    async with auth_session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest_asyncio.fixture
async def data_db(data_session_factory) -> AsyncGenerator[AsyncSession, None]:
    async with data_session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


# ---------------------------------------------------------------------------
# User factory
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def make_user(auth_db: AsyncSession, data_db: AsyncSession):
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
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        auth_db.add(user)
        await auth_db.flush()

        profile = UserProfile(
            user_id=user.id,
            name=email.split("@")[0],
            country="IN",
            currency="INR",
            consent_given=True,
            consent_timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
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
        "exp": datetime.now(timezone.utc) + timedelta(minutes=minutes),
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


@pytest.fixture
def auth_headers_for():
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
    async with httpx.AsyncClient(
        base_url="http://test",
        transport=ASGITransport(app=app),
        timeout=30.0,
    ) as client:
        yield client


@pytest_asyncio.fixture
async def authed_client(make_user, auth_headers_for) -> AsyncGenerator[httpx.AsyncClient, None]:
    user = await make_user()
    headers = auth_headers_for(user)
    async with httpx.AsyncClient(
        base_url="http://test",
        transport=ASGITransport(app=app),
        headers=headers,
        timeout=30.0,
    ) as client:
        client.user = user
        yield client
