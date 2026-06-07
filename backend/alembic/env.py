"""Alembic environment configuration for async SQLAlchemy."""
import asyncio
from logging.config import fileConfig
import sys
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Add parent directory to path so `app` package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import models so Alembic auto-detects schema changes
from app.db.session import AuthBase, DataBase  # noqa: E402
from app.db.models.auth import User, RefreshToken  # noqa: E402, F401
from app.db.models.data import (  # noqa: E402, F401
    UserProfile, Expense, Budget, UserFinancialProfile, BudgetAlert,
    Loan, LoanPayment, Goal, RecurringExpense, IncomeSource, Notification,
)
from app.config import settings  # noqa: E402

# Alembic Config object — provides access to alembic.ini values
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Combine both bases so a single Alembic run covers both schemas.
# We use the DATA database as the primary migration target; auth tables
# are managed separately via the auth migration env if needed.
target_metadata = DataBase.metadata


def get_url() -> str:
    """
    Return the database URL for migrations.

    Uses DATA_DATABASE_URL (the financial-data database).
    Auth-DB migrations should be run against AUTH_DATABASE_URL in a
    separate Alembic environment if schema drift is needed there.
    """
    return settings.DATA_DATABASE_URL  # ← Fixed: was settings.get_database_url()


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection required)."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations against an active connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with an async engine."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # No pooling during migrations
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migration mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
