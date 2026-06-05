"""
Comprehensive tests for app/core/error_handlers.py

Coverage: app_exception_handler, validation_exception_handler, general_exception_handler
Tests include: All exception types, error responses, logging, status codes
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError, field_validator
from pydantic import BaseModel

from app.core.error_handlers import (
    app_exception_handler,
    validation_exception_handler,
    general_exception_handler,
)
from app.core.exceptions import (
    AppException,
    ValidationError as AppValidationError,
    AuthenticationError,
    ErrorCode,
)


class TestAppExceptionHandler:
    """Test app_exception_handler function."""

    @pytest.mark.asyncio
    async def test_handles_app_exception(self):
        """Test handling a basic AppException."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = "http://example.com/api/test"

        exc = AppException(
            message="Test error",
            error_code=ErrorCode.VAL_INVALID_INPUT,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

        with patch("app.core.error_handlers.logger"):
            response = await app_exception_handler(mock_request, exc)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.media_type == "application/json"

    @pytest.mark.asyncio
    async def test_exception_handler_response_structure(self):
        """Test that exception handler returns correct response structure."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = "http://example.com/api/test"

        exc = AppException(
            message="Test error",
            error_code=ErrorCode.BDG_NOT_FOUND,
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"field": "value"},
        )

        with patch("app.core.error_handlers.logger"):
            response = await app_exception_handler(mock_request, exc)

        body = response.body.decode()
        import json

        data = json.loads(body)
        assert data["success"] is False
        assert data["error"]["code"] == ErrorCode.BDG_NOT_FOUND.value
        assert data["error"]["message"] == "Test error"
        assert data["error"]["details"]["field"] == "value"

    @pytest.mark.asyncio
    async def test_exception_handler_logs_error(self):
        """Test that exception handler logs the error."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = "http://example.com/api/test"

        exc = AppException(
            message="Test error",
            error_code=ErrorCode.EXP_NOT_FOUND,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

        with patch("app.core.error_handlers.logger") as mock_logger:
            await app_exception_handler(mock_request, exc)
            mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_authentication_error(self):
        """Test handling AuthenticationError (subclass of AppException)."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = "http://example.com/api/test"

        exc = AuthenticationError(message="Invalid credentials")

        with patch("app.core.error_handlers.logger"):
            response = await app_exception_handler(mock_request, exc)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_handles_exception_with_none_details(self):
        """Test handling exception when details is None."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = "http://example.com/api/test"

        exc = AppException(
            message="Error",
            error_code=ErrorCode.VAL_INVALID_INPUT,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=None,
        )

        with patch("app.core.error_handlers.logger"):
            response = await app_exception_handler(mock_request, exc)

        import json

        body = json.loads(response.body.decode())
        assert body["error"]["details"] is None or body["error"]["details"] == {}

    @pytest.mark.asyncio
    async def test_exception_handler_with_500_error(self):
        """Test handling a 500 internal server error."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = "http://example.com/api/test"

        exc = AppException(
            message="Internal server error",
            error_code=ErrorCode.VAL_INVALID_INPUT,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

        with patch("app.core.error_handlers.logger"):
            response = await app_exception_handler(mock_request, exc)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_exception_handler_with_403_forbidden(self):
        """Test handling a 403 forbidden error."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = "http://example.com/api/test"

        exc = AppException(
            message="Access denied",
            error_code=ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS,
            status_code=status.HTTP_403_FORBIDDEN,
        )

        with patch("app.core.error_handlers.logger"):
            response = await app_exception_handler(mock_request, exc)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_exception_handler_preserves_error_code(self):
        """Test that error code is preserved in response."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = "http://example.com/api/test"

        error_code = ErrorCode.LN_INVALID_RATE
        exc = AppException(
            message="Test",
            error_code=error_code,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

        with patch("app.core.error_handlers.logger"):
            response = await app_exception_handler(mock_request, exc)

        import json

        body = json.loads(response.body.decode())
        assert body["error"]["code"] == error_code.value


class TestValidationExceptionHandler:
    """Test validation_exception_handler function."""

    @pytest.mark.asyncio
    async def test_handles_validation_error_mock(self):
        """Test handling a validation error with mocked error list."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = "http://example.com/api/test"

        # Create a mock RequestValidationError with errors() method
        exc = MagicMock(spec=RequestValidationError)
        exc.errors.return_value = [
            {
                "type": "value_error",
                "loc": ("body", "email"),
                "msg": "Invalid email format",
            }
        ]

        with patch("app.core.error_handlers.logger"):
            response = await validation_exception_handler(mock_request, exc)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_validation_handler_response_structure_mock(self):
        """Test validation handler response structure with mock."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = "http://example.com/api/test"

        exc = MagicMock(spec=RequestValidationError)
        exc.errors.return_value = [
            {
                "type": "value_error",
                "loc": ("body", "email"),
                "msg": "Invalid email",
            }
        ]

        with patch("app.core.error_handlers.logger"):
            response = await validation_exception_handler(mock_request, exc)

        import json

        body = json.loads(response.body.decode())
        assert body["success"] is False
        assert body["error"]["code"] == "VAL_001"
        assert body["error"]["message"] == "Validation failed"
        assert "validation_errors" in body["error"]["details"]

    @pytest.mark.asyncio
    async def test_validation_handler_formats_errors_mock(self):
        """Test that validation errors are properly formatted."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = "http://example.com/api/test"

        exc = MagicMock(spec=RequestValidationError)
        exc.errors.return_value = [
            {
                "type": "value_error",
                "loc": ("body", "email"),
                "msg": "Invalid format",
            },
            {
                "type": "missing",
                "loc": ("body", "password"),
                "msg": "Field required",
            },
        ]

        with patch("app.core.error_handlers.logger"):
            response = await validation_exception_handler(mock_request, exc)

        import json

        body = json.loads(response.body.decode())
        errors = body["error"]["details"]["validation_errors"]
        assert len(errors) == 2
        assert errors[0]["field"] == "email"
        assert errors[1]["field"] == "password"

    @pytest.mark.asyncio
    async def test_validation_handler_includes_error_type_mock(self):
        """Test that validation error type is included."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = "http://example.com/api/test"

        exc = MagicMock(spec=RequestValidationError)
        exc.errors.return_value = [
            {
                "type": "string_type",
                "loc": ("body", "age"),
                "msg": "Input should be a valid integer",
            }
        ]

        with patch("app.core.error_handlers.logger"):
            response = await validation_exception_handler(mock_request, exc)

        import json

        body = json.loads(response.body.decode())
        errors = body["error"]["details"]["validation_errors"]
        assert errors[0]["type"] == "string_type"

    @pytest.mark.asyncio
    async def test_validation_handler_logs_warning_mock(self):
        """Test that validation handler logs a warning."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = "http://example.com/api/test"

        exc = MagicMock(spec=RequestValidationError)
        exc.errors.return_value = [
            {
                "type": "value_error",
                "loc": ("body", "field"),
                "msg": "Invalid",
            }
        ]

        with patch("app.core.error_handlers.logger") as mock_logger:
            await validation_exception_handler(mock_request, exc)
            mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_validation_handler_with_nested_fields_mock(self):
        """Test validation handler with nested field paths."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = "http://example.com/api/test"

        exc = MagicMock(spec=RequestValidationError)
        exc.errors.return_value = [
            {
                "type": "value_error",
                "loc": ("body", "user", "address", "zipcode"),
                "msg": "Invalid zipcode",
            }
        ]

        with patch("app.core.error_handlers.logger"):
            response = await validation_exception_handler(mock_request, exc)

        import json

        body = json.loads(response.body.decode())
        errors = body["error"]["details"]["validation_errors"]
        assert "user.address.zipcode" in errors[0]["field"]

    @pytest.mark.asyncio
    async def test_validation_handler_with_multiple_errors_mock(self):
        """Test validation handler with multiple validation errors."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = "http://example.com/api/test"

        exc = MagicMock(spec=RequestValidationError)
        exc.errors.return_value = [
            {
                "type": "value_error",
                "loc": ("body", "email"),
                "msg": "Invalid",
            },
            {
                "type": "value_error",
                "loc": ("body", "phone"),
                "msg": "Invalid",
            },
            {
                "type": "value_error",
                "loc": ("body", "age"),
                "msg": "Must be positive",
            },
        ]

        with patch("app.core.error_handlers.logger"):
            response = await validation_exception_handler(mock_request, exc)

        import json

        body = json.loads(response.body.decode())
        errors = body["error"]["details"]["validation_errors"]
        assert len(errors) == 3


class TestGeneralExceptionHandler:
    """Test general_exception_handler function."""

    @pytest.mark.asyncio
    async def test_handles_generic_exception(self):
        """Test handling a generic Exception."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = "http://example.com/api/test"
        mock_request.headers = {}

        exc = RuntimeError("Unexpected error")

        with patch("app.core.error_handlers.logger"):
            response = await general_exception_handler(mock_request, exc)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_generic_handler_response_structure(self):
        """Test generic handler response structure."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = "http://example.com/api/test"
        mock_request.headers = {}

        exc = Exception("Generic error")

        with patch("app.core.error_handlers.logger"):
            response = await general_exception_handler(mock_request, exc)

        import json

        body = json.loads(response.body.decode())
        assert body["success"] is False
        assert body["error"]["code"] == "SRV_001"
        assert body["error"]["message"] == "An unexpected error occurred"

    @pytest.mark.asyncio
    async def test_generic_handler_does_not_expose_details(self):
        """Test that generic handler doesn't expose internal error details."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = "http://example.com/api/test"
        mock_request.headers = {}

        exc = Exception("Sensitive database error")

        with patch("app.core.error_handlers.logger"):
            response = await general_exception_handler(mock_request, exc)

        import json

        body = json.loads(response.body.decode())
        # Error message should not contain the actual error
        assert "Sensitive database" not in body["error"]["message"]

    @pytest.mark.asyncio
    async def test_generic_handler_logs_critical(self):
        """Test that generic handler logs as critical."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = "http://example.com/api/test"
        mock_request.headers = {}

        exc = Exception("Error")

        with patch("app.core.error_handlers.logger") as mock_logger:
            await general_exception_handler(mock_request, exc)
            mock_logger.critical.assert_called_once()

    @pytest.mark.asyncio
    async def test_generic_handler_includes_request_id(self):
        """Test that handler includes request ID in response."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = "http://example.com/api/test"
        mock_request.headers = {"x-request-id": "req-123-abc"}

        exc = Exception("Error")

        with patch("app.core.error_handlers.logger"):
            response = await general_exception_handler(mock_request, exc)

        import json

        body = json.loads(response.body.decode())
        assert body["error"]["details"]["request_id"] == "req-123-abc"

    @pytest.mark.asyncio
    async def test_generic_handler_missing_request_id_uses_default(self):
        """Test that handler uses N/A when request ID is missing."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = "http://example.com/api/test"
        mock_request.headers = {}

        exc = Exception("Error")

        with patch("app.core.error_handlers.logger"):
            response = await general_exception_handler(mock_request, exc)

        import json

        body = json.loads(response.body.decode())
        assert body["error"]["details"]["request_id"] == "N/A"

    @pytest.mark.asyncio
    async def test_handles_various_exception_types(self):
        """Test handling various exception types."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = "http://example.com/api/test"
        mock_request.headers = {}

        exceptions = [
            ValueError("Invalid value"),
            TypeError("Wrong type"),
            KeyError("Missing key"),
            RuntimeError("Runtime error"),
            OSError("OS error"),
        ]

        with patch("app.core.error_handlers.logger"):
            for exc in exceptions:
                response = await general_exception_handler(mock_request, exc)
                assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestErrorHandlersIntegration:
    """Integration tests for error handlers."""

    @pytest.mark.asyncio
    async def test_exception_handler_status_codes(self):
        """Test various status codes in exception handler."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = "http://example.com/api/test"

        status_codes = [
            (status.HTTP_400_BAD_REQUEST, "Bad request", ErrorCode.VAL_INVALID_INPUT),
            (status.HTTP_401_UNAUTHORIZED, "Unauthorized", ErrorCode.AUTH_INVALID_CREDENTIALS),
            (status.HTTP_403_FORBIDDEN, "Forbidden", ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS),
            (status.HTTP_404_NOT_FOUND, "Not found", ErrorCode.USER_NOT_FOUND),
            (status.HTTP_500_INTERNAL_SERVER_ERROR, "Server error", ErrorCode.VAL_INVALID_INPUT),
        ]

        with patch("app.core.error_handlers.logger"):
            for code, message, error_code in status_codes:
                exc = AppException(
                    message=message, error_code=error_code, status_code=code
                )
                response = await app_exception_handler(mock_request, exc)
                assert response.status_code == code

    @pytest.mark.asyncio
    async def test_validation_error_count_logging_mock(self):
        """Test that validation handler logs error count."""
        mock_request = MagicMock(spec=Request)
        mock_request.url = "http://example.com/api/test"

        exc = MagicMock(spec=RequestValidationError)
        exc.errors.return_value = [
            {
                "type": "value_error",
                "loc": ("body", f"field_{i}"),
                "msg": f"Error {i}",
            }
            for i in range(5)
        ]

        with patch("app.core.error_handlers.logger") as mock_logger:
            await validation_exception_handler(mock_request, exc)
            # Verify that error_count was logged
            call_args = mock_logger.warning.call_args
            assert "error_count" in call_args[1] or "5" in str(call_args)
