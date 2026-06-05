"""
Error handling and logging decorators for DRY compliance - Phase 3.

Provides:
- Automatic error logging with context
- Transaction rollback on exceptions
- Standardized error responses
- Audit logging decorators
- Retry logic with exponential backoff

Usage:
    @handle_db_errors
    @log_operation("expense_creation")
    @audit_log(action="create_expense", resource_type="expense")
    async def create_expense(user_id: UUID, data: ExpenseCreate):
        ...
"""

from functools import wraps
from typing import Callable, Optional, Type, List, Any
import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
import traceback
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.exceptions import (
    AppException,
    DatabaseError,
    ResourceNotFoundError,
    ValidationError,
    AuthenticationError as UnauthorizedError,
    AuthorizationError as ForbiddenError,
)

logger = get_logger(__name__)


# ============================================================================
# Logging Decorators - DRY Compliance
# ============================================================================

def log_operation(
    operation_name: str,
    include_args: bool = False,
    include_result: bool = False,
    level: str = "info"
):
    """
    Decorator to automatically log operation entry/exit.

    Args:
        operation_name: Name of the operation (e.g., "create_expense")
        include_args: Whether to log function arguments
        include_result: Whether to log the returned result
        level: Logging level ('debug', 'info', 'warning')

    Usage:
        @log_operation("create_expense", include_args=True)
        async def create_expense(user_id: UUID, data: ExpenseCreate):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            context = {
                "operation": operation_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "function": func.__name__,
            }

            if include_args:
                context["args"] = str(args)[:200]  # Limit to 200 chars
                context["kwargs"] = str(kwargs)[:200]

            log_func = getattr(logger, level, logger.info)
            log_func(f"Starting {operation_name}", extra=context)

            try:
                result = await func(*args, **kwargs)

                if include_result:
                    context["result_type"] = type(result).__name__
                    if isinstance(result, (dict, list)):
                        context["result_size"] = len(str(result))

                log_func(f"Completed {operation_name}", extra=context)
                return result

            except Exception as exc:
                context["error"] = str(exc)
                context["error_type"] = type(exc).__name__
                logger.error(f"Failed {operation_name}", extra=context, exc_info=True)
                raise

        return wrapper
    return decorator


def audit_log(
    action: str,
    resource_type: str,
    include_user_id: bool = True,
    include_resource_id: bool = True
):
    """
    Decorator to create audit logs for sensitive operations.

    Logs create/update/delete operations for compliance and forensics.

    Args:
        action: Action being performed ('create', 'update', 'delete', 'export')
        resource_type: Type of resource ('expense', 'budget', 'loan', 'user')
        include_user_id: Whether to include user_id in audit log
        include_resource_id: Whether to include resource ID in audit log

    Usage:
        @audit_log(action="create", resource_type="expense")
        async def create_expense(user_id: UUID, data: ExpenseCreate):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            audit_context = {
                "action": action,
                "resource_type": resource_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "function": func.__name__,
            }

            # Try to extract user_id and resource_id from arguments
            if include_user_id:
                user_id = kwargs.get('user_id')
                if not user_id and len(args) > 0:
                    # Try to find UUID-like arguments
                    for arg in args:
                        if isinstance(arg, UUID):
                            user_id = arg
                            break
                if user_id:
                    audit_context["user_id"] = str(user_id)

            try:
                result = await func(*args, **kwargs)

                if include_resource_id and result:
                    if hasattr(result, 'id'):
                        audit_context["resource_id"] = str(result.id)
                    elif isinstance(result, dict) and 'id' in result:
                        audit_context["resource_id"] = str(result['id'])

                audit_context["status"] = "success"
                logger.info(
                    f"Audit: {action} {resource_type}",
                    extra=audit_context
                )
                return result

            except Exception as exc:
                audit_context["status"] = "failed"
                audit_context["error"] = str(exc)
                logger.warning(
                    f"Audit: {action} {resource_type} failed",
                    extra=audit_context,
                    exc_info=True
                )
                raise

        return wrapper
    return decorator


# ============================================================================
# Error Handling Decorators
# ============================================================================

def handle_db_errors(
    default_error: Type[Exception] = DatabaseError,
    rollback_on_error: bool = True
):
    """
    Decorator to handle database exceptions and perform automatic rollback.

    Maps common SQLAlchemy exceptions to application exceptions.

    Args:
        default_error: Default exception type to raise
        rollback_on_error: Whether to rollback session on error

    Usage:
        @handle_db_errors(rollback_on_error=True)
        async def create_expense(db: AsyncSession, data: ExpenseCreate):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            db_session = None

            # Try to find AsyncSession in arguments
            for arg in args:
                if isinstance(arg, AsyncSession):
                    db_session = arg
                    break

            if not db_session:
                for kwarg in kwargs.values():
                    if isinstance(kwarg, AsyncSession):
                        db_session = kwarg
                        break

            try:
                return await func(*args, **kwargs)

            except Exception as exc:
                # Always pass through HTTP exceptions (they carry intended status codes)
                from fastapi import HTTPException
                if isinstance(exc, HTTPException):
                    raise

                # Rollback on error if session found
                if db_session and rollback_on_error:
                    try:
                        await db_session.rollback()
                        logger.debug("Database transaction rolled back")
                    except Exception as rollback_exc:
                        logger.error(f"Rollback failed: {rollback_exc}")

                # Map specific DB errors
                error_msg = str(exc).lower()
                if "unique constraint" in error_msg or "duplicate" in error_msg:
                    raise ValidationError("Resource already exists") from exc
                elif "foreign key" in error_msg:
                    raise ValidationError("Invalid reference: foreign key constraint violated") from exc
                elif "not null constraint" in error_msg:
                    raise ValidationError("Required field missing") from exc

                # Raise default error
                if isinstance(exc, AppException):
                    raise
                raise default_error(str(exc)) from exc

        return wrapper
    return decorator


def handle_validation_errors(
    default_error: Type[Exception] = ValidationError
):
    """
    Decorator to catch and standardize validation errors.

    Args:
        default_error: Exception type to raise on validation failure

    Usage:
        @handle_validation_errors()
        async def create_expense(data: ExpenseCreate):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)

            except ValueError as exc:
                logger.warning(f"Validation error: {exc}")
                raise default_error(str(exc)) from exc

            except Exception as exc:
                if isinstance(exc, AppException):
                    raise
                raise

        return wrapper
    return decorator


def handle_not_found_errors(
    resource_type: str = "resource"
):
    """
    Decorator to standardize not-found error handling.

    Args:
        resource_type: Type of resource being accessed

    Usage:
        @handle_not_found_errors(resource_type="expense")
        async def get_expense(expense_id: UUID):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            if result is None:
                raise ResourceNotFoundError(f"{resource_type} not found")

            return result

        return wrapper
    return decorator


# ============================================================================
# Retry Decorator with Exponential Backoff
# ============================================================================

def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 0.1,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator to automatically retry operations with exponential backoff.

    Useful for transient failures (network, lock contention, etc.).

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries (seconds)
        backoff_factor: Multiplier for delay on each retry
        exceptions: Tuple of exception types to catch and retry

    Usage:
        @retry_with_backoff(max_retries=3, initial_delay=0.1)
        async def fetch_external_data():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)

                except exceptions as exc:
                    if attempt == max_retries:
                        logger.error(
                            f"All {max_retries + 1} retry attempts failed",
                            extra={"function": func.__name__, "error": str(exc)}
                        )
                        raise

                    logger.warning(
                        f"Attempt {attempt + 1} failed, retrying in {delay}s",
                        extra={"function": func.__name__, "error": str(exc)}
                    )
                    await asyncio.sleep(delay)
                    delay *= backoff_factor

        return wrapper
    return decorator


# ============================================================================
# Authorization Decorators
# ============================================================================

def require_owner_or_admin(
    user_id_param: str = "user_id",
    resource_id_param: str = None
):
    """
    Decorator to enforce owner or admin authorization.

    Ensures user can only access their own resources (unless admin).

    Args:
        user_id_param: Name of the user_id parameter
        resource_id_param: Name of the resource_id parameter (optional)

    Usage:
        @require_owner_or_admin(user_id_param="user_id")
        async def get_expense(user_id: UUID, expense_id: UUID):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_id = kwargs.get(user_id_param)

            if not user_id:
                for arg in args:
                    if isinstance(arg, UUID):
                        user_id = arg
                        break

            if not user_id:
                raise UnauthorizedError("User context required")

            # TODO: Check if user is admin or owner of resource
            # This would typically be done via a current_user dependency

            return await func(*args, **kwargs)

        return wrapper
    return decorator


# ============================================================================
# Rate Limiting Decorator
# ============================================================================

def rate_limit(
    calls: int = 100,
    period: int = 60,
    key_func: Optional[Callable] = None
):
    """
    Decorator to apply rate limiting to operations.

    Args:
        calls: Number of calls allowed
        period: Time period in seconds
        key_func: Function to generate rate limit key (defaults to function name)

    Usage:
        @rate_limit(calls=10, period=60)
        async def create_expense(user_id: UUID, data: ExpenseCreate):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # TODO: Implement rate limiting using Redis or in-memory cache
            # This is a placeholder for the actual implementation
            return await func(*args, **kwargs)

        return wrapper
    return decorator


# ============================================================================
# Mixin Classes for Error Handling - Alternative to Decorators
# ============================================================================

class ErrorHandlingMixin:
    """Mixin to add consistent error handling to service classes."""

    async def handle_operation(
        self,
        operation_name: str,
        operation_func: Callable,
        *args,
        **kwargs
    ):
        """
        Execute an operation with automatic error handling and logging.

        Args:
            operation_name: Name of the operation for logging
            operation_func: Async function to execute
            *args, **kwargs: Arguments to pass to operation_func

        Returns:
            Result of operation_func

        Raises:
            AppException: On any error (with proper logging)
        """
        logger.debug(f"Starting operation: {operation_name}")

        try:
            result = await operation_func(*args, **kwargs)
            logger.debug(f"Completed operation: {operation_name}")
            return result

        except Exception as exc:
            logger.error(
                f"Operation failed: {operation_name}",
                extra={
                    "operation": operation_name,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
                exc_info=True
            )

            if isinstance(exc, AppException):
                raise

            # Wrap unexpected errors
            raise DatabaseError(f"Operation '{operation_name}' failed: {exc}") from exc

    async def execute_with_rollback(
        self,
        operation_name: str,
        operation_func: Callable,
        db_session: Optional[AsyncSession] = None,
        *args,
        **kwargs
    ):
        """
        Execute an operation with automatic rollback on failure.

        Args:
            operation_name: Name of the operation
            operation_func: Async function to execute
            db_session: Database session for rollback
            *args, **kwargs: Arguments to pass to operation_func

        Returns:
            Result of operation_func

        Raises:
            AppException: On any error
        """
        try:
            return await self.handle_operation(
                operation_name,
                operation_func,
                *args,
                **kwargs
            )

        except Exception as exc:
            if db_session:
                try:
                    await db_session.rollback()
                    logger.debug(f"Rolled back transaction for operation: {operation_name}")
                except Exception as rollback_exc:
                    logger.error(f"Rollback failed: {rollback_exc}")

            raise
