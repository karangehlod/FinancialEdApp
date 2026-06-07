"""
Database session management with production-grade connection pooling.

Pool sizing rationale (per worker process):
  - pool_size=20: base connections kept alive
  - max_overflow=40: burst connections allowed
  - pool_timeout=30: wait up to 30s for a connection before raising
  - pool_recycle=1800: recycle connections every 30 min (prevents stale TCP)
  - pool_pre_ping=True: validate connection before checkout (catches DB restarts)

PgBouncer (transaction mode) compatibility:
  - statement_cache_size=0: disable asyncpg prepared statements
    (required in transaction-mode pooling — prepared statements are session-scoped)
  - PgBouncer sits between the app and PostgreSQL, multiplexing many app
    connections onto a small number of real DB connections.

For 1M+ users use PgBouncer in transaction mode in front of PostgreSQL
to manage the total connection count at the infrastructure level.
See: backend/k8s/06-pgbouncer.yaml
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import event

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PgBouncer detection — from settings (env var: PGBOUNCER_MODE=true)
# ---------------------------------------------------------------------------
_PGBOUNCER_MODE = settings.PGBOUNCER_MODE

# asyncpg connect_args — disable prepared statements in PgBouncer transaction mode
_ASYNCPG_CONNECT_ARGS: dict = {}
if _PGBOUNCER_MODE:
    _ASYNCPG_CONNECT_ARGS = {"statement_cache_size": 0}
    logger.info("PgBouncer transaction mode: asyncpg prepared statements DISABLED")

# ---------------------------------------------------------------------------
# Pool configuration — all values from settings (tunable via env vars)
# ---------------------------------------------------------------------------
_POOL_CONFIG = {
    "echo": False,
    "pool_pre_ping": settings.DB_POOL_PRE_PING,
    "pool_size": settings.DB_POOL_SIZE,
    "max_overflow": settings.DB_MAX_OVERFLOW,
    "pool_timeout": settings.DB_POOL_TIMEOUT,
    "pool_recycle": settings.DB_POOL_RECYCLE,
    "connect_args": _ASYNCPG_CONNECT_ARGS,
}

# ---------------------------------------------------------------------------
# Auth Database Engine  (users, refresh_tokens)
# ---------------------------------------------------------------------------
auth_engine = create_async_engine(
    settings.AUTH_DATABASE_URL,
    **_POOL_CONFIG,
)

# ---------------------------------------------------------------------------
# Data Database Engine  (expenses, budgets, goals, loans, notifications…)
# ---------------------------------------------------------------------------
data_engine = create_async_engine(
    settings.DATA_DATABASE_URL,
    **_POOL_CONFIG,
)

# ---------------------------------------------------------------------------
# Pool event listeners — emit Prometheus metrics on pool events
# ---------------------------------------------------------------------------
def _register_pool_events(engine, pool_name: str) -> None:
    """Register SQLAlchemy connection-pool event listeners for observability."""
    try:
        from app.core.metrics import DB_POOL_SIZE, DB_POOL_CHECKEDOUT

        @event.listens_for(engine.sync_engine, "connect")
        def on_connect(dbapi_conn, connection_record):  # noqa: ARG001
            DB_POOL_SIZE.labels(pool_name=pool_name).inc()
            logger.debug("DB pool connection established", extra={"pool": pool_name})

        @event.listens_for(engine.sync_engine, "checkout")
        def on_checkout(dbapi_conn, connection_record, connection_proxy):  # noqa: ARG001
            DB_POOL_CHECKEDOUT.labels(pool_name=pool_name).inc()

        @event.listens_for(engine.sync_engine, "checkin")
        def on_checkin(dbapi_conn, connection_record):  # noqa: ARG001
            DB_POOL_CHECKEDOUT.labels(pool_name=pool_name).dec()

        @event.listens_for(engine.sync_engine, "close")
        def on_close(dbapi_conn, connection_record):  # noqa: ARG001
            DB_POOL_SIZE.labels(pool_name=pool_name).dec()

    except Exception as exc:  # pragma: no cover
        # Metrics are optional — never block engine creation
        logger.warning("Could not register pool event listeners: %s", exc)


_register_pool_events(auth_engine, "auth_db")
_register_pool_events(data_engine, "data_db")

# ---------------------------------------------------------------------------
# Session factories
# ---------------------------------------------------------------------------
AuthSessionLocal = async_sessionmaker(
    auth_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

DataSessionLocal = async_sessionmaker(
    data_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# ---------------------------------------------------------------------------
# Declarative bases (one per database)
# ---------------------------------------------------------------------------
AuthBase = declarative_base()
DataBase = declarative_base()


# ---------------------------------------------------------------------------
# FastAPI dependency helpers
# ---------------------------------------------------------------------------

async def get_auth_db() -> AsyncSession:
    """
    Yield an auth-DB session with autobegin.

    The session uses SQLAlchemy's default autobegin, meaning a transaction
    is started lazily on first use. Services are responsible for calling
    commit() / rollback() as needed.  On exception the session is rolled
    back; the session is always closed on exit.
    """
    async with AuthSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_data_db() -> AsyncSession:
    """
    Yield a data-DB session with autobegin.

    The session uses SQLAlchemy's default autobegin, meaning a transaction
    is started lazily on first use. Services are responsible for calling
    commit() / rollback() as needed.  On exception the session is rolled
    back; the session is always closed on exit.
    """
    async with DataSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Engine disposal (called during application shutdown)
# ---------------------------------------------------------------------------

async def dispose_engines() -> None:
    """Gracefully close all connection pools — call during app shutdown."""
    await auth_engine.dispose()
    await data_engine.dispose()
    logger.info("Database connection pools disposed.")
