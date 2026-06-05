"""
Exception handling middleware for the application.
Converts exceptions to proper HTTP responses with error codes.
"""

from typing import Callable
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Handle application exceptions.

    Returns JSON response with error code, message, and details.
    """
    # Handle both string and enum error codes
    error_code = exc.error_code.value if hasattr(exc.error_code, 'value') else str(exc.error_code)
    
    logger.error(
        f"Application exception occurred",
        error_code=error_code,
        status_code=exc.status_code,
        path=str(request.url),
        exc_info=True,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": error_code,
                "message": exc.message,
                "details": exc.details,
            },
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Returns JSON response with validation error details.
    """
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "field": ".".join(str(x) for x in error["loc"][1:]),
                "message": error["msg"],
                "type": error["type"],
            }
        )

    logger.warning(
        f"Validation error",
        error_count=len(errors),
        path=str(request.url),
        errors=errors,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VAL_001",
                "message": "Validation failed",
                "details": {"validation_errors": errors},
            },
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions.

    Returns generic error response.
    """
    logger.critical(
        f"Unexpected error occurred",
        path=str(request.url),
        exc_info=True,
    )

    # Don't expose internal error details in production
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "SRV_001",
                "message": "An unexpected error occurred",
                "details": {"request_id": str(request.headers.get("x-request-id", "N/A"))},
            },
        },
    )
