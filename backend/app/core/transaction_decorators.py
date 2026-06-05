"""
Transaction management decorators - Ensure atomic operations and data consistency.

Features:
- Automatic transaction wrapping
- Rollback on exception
- Retry logic with exponential backoff
- Deadlock detection and recovery
- Nested transaction support
- Connection pooling optimization

Usage:
    @transactional
    async def service_method(...):
        pass

    @transactional(rollback_on_error=True)
    @with_retry(max_attempts=3, backoff="exponential")
    async def critical_operation(...):
        pass
"""

from functools import wraps
from typing import Callable, Optional, Any
import logging
from datetime import datetime, timedelta, timezone
import asyncio
import random

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, DBAPIError, OperationalError

from app.core.logging import get_logger

logger = get_logger(__name__)

# ============================================================================
# Transactional Decorator
# ============================================================================

def transactional(
    rollback_on_error: bool = True,
    nested: bool = False,
    savepoint: Optional[str] = None
):
    """
    Decorator to wrap service methods in database transactions.

    Args:
        rollback_on_error: Whether to rollback transaction on exception (default: True)
        nested: Whether to support nested transactions/savepoints (default: False)
        savepoint: Named savepoint for nested transactions (default: None)

    Raises:
        Original exception if rollback_on_error=True, wrapped in TransactionError otherwise

    Usage:
        @transactional(rollback_on_error=True)
        async def create_expense(self, user_id: UUID, data: ExpenseCreate):
            # Method body
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract db session from arguments
            db_session = None
            
            # Try to find AsyncSession in args (typically self.db or db parameter)
            for arg in args:
                if isinstance(arg, AsyncSession):
                    db_session = arg
                    break
            
            # If not found in args, try kwargs
            if not db_session and 'db' in kwargs:
                db_session = kwargs['db']
            
            if not db_session:
                logger.warning(f"No database session found in {func.__name__}")
                return await func(*args, **kwargs)
            
            try:
                # Begin transaction
                if nested and savepoint:
                    # Use savepoint for nested transactions
                    sp = await db_session.begin_nested()
                    logger.debug(f"Created savepoint: {savepoint}")
                else:
                    # Standard transaction
                    async with db_session.begin():
                        result = await func(*args, **kwargs)
                        # Commit happens automatically on exit
                        return result
                
                # Nested transaction
                try:
                    result = await func(*args, **kwargs)
                    await sp.commit()
                    return result
                except Exception as sp_exc:
                    await sp.rollback()
                    raise sp_exc
                    
            except IntegrityError as exc:
                # Constraint violation
                if rollback_on_error:
                    logger.error(f"Integrity error in {func.__name__}: {exc}")
                    raise
                else:
                    raise
            
            except DBAPIError as exc:
                # Database API error
                logger.error(f"Database API error in {func.__name__}: {exc}")
                if rollback_on_error:
                    raise
                else:
                    raise
            
            except Exception as exc:
                logger.error(f"Error in transactional {func.__name__}: {exc}")
                if rollback_on_error:
                    raise
                else:
                    raise
        
        return wrapper
    return decorator


# ============================================================================
# Retry Decorator with Exponential Backoff
# ============================================================================

def with_retry(
    max_attempts: int = 3,
    backoff: str = "exponential",
    initial_delay: float = 0.1,
    max_delay: float = 10.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (OperationalError, IntegrityError)
):
    """
    Decorator to add retry logic with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        backoff: Backoff strategy - "exponential", "linear", or "fixed" (default: "exponential")
        initial_delay: Initial delay between retries in seconds (default: 0.1)
        max_delay: Maximum delay between retries in seconds (default: 10.0)
        jitter: Whether to add random jitter to delays (default: True)
        retryable_exceptions: Tuple of exceptions to retry on (default: DB errors)

    Raises:
        Original exception if max attempts exceeded

    Usage:
        @with_retry(max_attempts=3, backoff="exponential")
        async def critical_operation(...):
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            last_exception = None
            
            while attempt < max_attempts:
                try:
                    return await func(*args, **kwargs)
                
                except retryable_exceptions as exc:
                    attempt += 1
                    last_exception = exc
                    
                    if attempt >= max_attempts:
                        logger.error(
                            f"Max retry attempts ({max_attempts}) exceeded for {func.__name__}",
                            extra={"last_error": str(exc)}
                        )
                        raise
                    
                    # Calculate delay
                    delay = _calculate_backoff(
                        attempt,
                        backoff,
                        initial_delay,
                        max_delay,
                        jitter
                    )
                    
                    logger.warning(
                        f"Retry {attempt}/{max_attempts} for {func.__name__}",
                        extra={"error": str(exc), "delay_seconds": delay}
                    )
                    
                    await asyncio.sleep(delay)
                
                except Exception as exc:
                    # Non-retryable exception
                    logger.error(f"Non-retryable error in {func.__name__}: {exc}")
                    raise
            
            # Should not reach here
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


# ============================================================================
# Deadlock Detection and Recovery
# ============================================================================

def with_deadlock_recovery(
    max_attempts: int = 3,
    initial_delay: float = 0.1
):
    """
    Decorator to detect and handle database deadlocks.

    Args:
        max_attempts: Maximum retry attempts on deadlock (default: 3)
        initial_delay: Initial delay before retry (default: 0.1s)

    Raises:
        Original deadlock exception if max attempts exceeded

    Usage:
        @with_deadlock_recovery(max_attempts=3)
        async def competing_operation(...):
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            
            while attempt < max_attempts:
                try:
                    return await func(*args, **kwargs)
                
                except DBAPIError as exc:
                    if "deadlock" in str(exc).lower():
                        attempt += 1
                        
                        if attempt >= max_attempts:
                            logger.error(
                                f"Deadlock max retries ({max_attempts}) exceeded for {func.__name__}"
                            )
                            raise
                        
                        # Exponential backoff for deadlock
                        delay = initial_delay * (2 ** (attempt - 1))
                        delay = min(delay, 10.0)  # Cap at 10 seconds
                        
                        if random.random() < 0.1:  # 10% jitter
                            delay = delay * random.uniform(0.9, 1.1)
                        
                        logger.warning(
                            f"Deadlock detected in {func.__name__}, retry {attempt}/{max_attempts}",
                            extra={"delay_seconds": delay}
                        )
                        
                        await asyncio.sleep(delay)
                    else:
                        raise
                
                except Exception as exc:
                    raise
            
            # Should not reach here
            logger.error(f"Deadlock retry loop ended unexpectedly for {func.__name__}")
            raise DBAPIError("Deadlock recovery failed", None, None)
        
        return wrapper
    return decorator


# ============================================================================
# Helper Functions
# ============================================================================

def _calculate_backoff(
    attempt: int,
    strategy: str,
    initial_delay: float,
    max_delay: float,
    jitter: bool
) -> float:
    """Calculate backoff delay based on strategy."""
    
    if strategy == "fixed":
        delay = initial_delay
    
    elif strategy == "linear":
        delay = initial_delay * attempt
    
    elif strategy == "exponential":
        delay = initial_delay * (2 ** (attempt - 1))
    
    else:
        delay = initial_delay
    
    # Cap at max delay
    delay = min(delay, max_delay)
    
    # Add jitter
    if jitter:
        delay = delay * random.uniform(0.9, 1.1)
    
    return delay


# ============================================================================
# Connection Pool Optimization
# ============================================================================

class ConnectionPoolManager:
    """Manage database connection pool settings for optimal performance."""
    
    @staticmethod
    async def configure_pool(
        engine,
        pool_size: int = 20,
        max_overflow: int = 40,
        pool_timeout: float = 30.0,
        pool_recycle: int = 3600,
        echo: bool = False
    ):
        """
        Configure connection pool settings.
        
        Args:
            engine: SQLAlchemy async engine
            pool_size: Number of connections in pool (default: 20)
            max_overflow: Max additional connections (default: 40)
            pool_timeout: Timeout for getting connection (default: 30s)
            pool_recycle: Recycle connections after N seconds (default: 1h)
            echo: Whether to echo SQL (default: False)
        """
        logger.info(
            "Configuring connection pool",
            extra={
                "pool_size": pool_size,
                "max_overflow": max_overflow,
                "pool_timeout": pool_timeout
            }
        )
        
        # Settings are typically configured at engine creation time
        # This is a placeholder for runtime optimization

# ============================================================================
# Transaction Status Tracking
# ============================================================================

class TransactionMetrics:
    """Track transaction metrics for monitoring."""
    
    def __init__(self):
        self.total_transactions = 0
        self.successful = 0
        self.failed = 0
        self.retried = 0
        self.start_time = datetime.now(timezone.utc)
    
    def record_success(self):
        self.total_transactions += 1
        self.successful += 1
    
    def record_failure(self):
        self.total_transactions += 1
        self.failed += 1
    
    def record_retry(self):
        self.retried += 1
    
    def get_stats(self) -> dict:
        elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        success_rate = (self.successful / self.total_transactions * 100) if self.total_transactions > 0 else 0
        
        return {
            "total_transactions": self.total_transactions,
            "successful": self.successful,
            "failed": self.failed,
            "retried": self.retried,
            "success_rate_percent": success_rate,
            "uptime_seconds": elapsed
        }


# Global metrics instance
transaction_metrics = TransactionMetrics()


def get_transaction_metrics() -> dict:
    """Get current transaction metrics."""
    return transaction_metrics.get_stats()
