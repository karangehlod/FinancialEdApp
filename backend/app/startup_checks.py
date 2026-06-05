"""Startup health checks for database and Redis connectivity."""
import asyncio
import sys
from sqlalchemy import text
from redis import asyncio as aioredis
import logging

from app.db.session import auth_engine, data_engine
from app.config import settings

logger = logging.getLogger(__name__)


async def check_database_connectivity() -> bool:
    """
    Check if databases are available and accessible.
    
    Returns:
        bool: True if both databases are accessible, False otherwise
    """
    try:
        # Check auth database
        async with auth_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✓ Auth database connection successful")
        
        # Check data database
        async with data_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✓ Data database connection successful")
        
        return True
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        return False


async def check_redis_connectivity() -> bool:
    """
    Check if Redis is available and accessible.
    
    Returns:
        bool: True if Redis is accessible, False otherwise
    """
    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        await redis_client.ping()
        await redis_client.close()
        logger.info("✓ Redis connection successful")
        return True
    except Exception as e:
        logger.error(f"✗ Redis connection failed: {e}")
        return False


async def verify_database_schema() -> bool:
    """
    Verify that required database tables exist.
    Does NOT create tables - only checks for their existence.
    
    Returns:
        bool: True if tables exist, False otherwise
    """
    required_auth_tables = ['users']
    required_data_tables = ['expenses', 'budgets', 'loans', 'goals', 'notifications']
    
    try:
        # Check auth tables
        async with auth_engine.connect() as conn:
            for table in required_auth_tables:
                result = await conn.execute(
                    text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')")
                )
                exists = result.scalar()
                if not exists:
                    logger.warning(f"✗ Required table '{table}' not found in auth database")
                    return False
        
        # Check data tables
        async with data_engine.connect() as conn:
            for table in required_data_tables:
                result = await conn.execute(
                    text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')")
                )
                exists = result.scalar()
                if not exists:
                    logger.warning(f"✗ Required table '{table}' not found in data database")
                    return False
        
        logger.info("✓ All required database tables exist")
        return True
    except Exception as e:
        logger.error(f"✗ Database schema verification failed: {e}")
        return False


async def perform_startup_checks(verify_schema: bool = False) -> bool:
    """
    Perform all startup checks.
    
    Args:
        verify_schema: If True, also verify that database schema exists
    
    Returns:
        bool: True if all checks pass, False otherwise
    """
    logger.info("=" * 60)
    logger.info("Starting application startup checks...")
    logger.info("=" * 60)
    
    # Check database connectivity
    db_ok = await check_database_connectivity()
    if not db_ok:
        logger.error("Database is not available. Please ensure database services are running.")
        return False
    
    # Check Redis connectivity
    redis_ok = await check_redis_connectivity()
    if not redis_ok:
        logger.error("Redis is not available. Please ensure Redis service is running.")
        return False
    
    # Optionally verify schema
    if verify_schema:
        schema_ok = await verify_database_schema()
        if not schema_ok:
            logger.error("Database schema is incomplete. Please run database initialization scripts.")
            return False
    
    logger.info("=" * 60)
    logger.info("✓ All startup checks passed successfully")
    logger.info("=" * 60)
    return True


async def graceful_exit(message: str, exit_code: int = 1):
    """
    Exit gracefully with a message.
    
    Args:
        message: Exit message to log
        exit_code: Exit code (default: 1)
    """
    logger.error(message)
    logger.info("Exiting application...")
    sys.exit(exit_code)


async def main():
    """Run startup checks independently."""
    success = await perform_startup_checks(verify_schema=True)
    if success:
        print("All checks passed!")
        sys.exit(0)
    else:
        print("Some checks failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
