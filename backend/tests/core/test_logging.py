"""
Comprehensive tests for app/core/logging.py

Coverage: JSONFormatter, StructuredLogger, setup_logging, get_logger
Tests include: JSON formatting, context management, all log levels, exception handling
"""

import pytest
import logging
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

from app.core.logging import (
    JSONFormatter,
    StructuredLogger,
    setup_logging,
    get_logger,
)


class TestJSONFormatter:
    """Test JSONFormatter class for JSON log formatting."""

    def test_format_basic_log_record(self):
        """Test formatting a basic log record to JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Test message"
        assert parsed["logger"] == "test_logger"
        assert parsed["line"] == 10

    def test_format_includes_timestamp(self):
        """Test that formatted output includes ISO timestamp."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        parsed = json.loads(result)

        assert "timestamp" in parsed
        # Verify it's a valid ISO format
        assert "T" in parsed["timestamp"]

    def test_format_with_exception_info(self):
        """Test formatting with exception information."""
        formatter = JSONFormatter()
        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        result = formatter.format(record)
        parsed = json.loads(result)

        assert "exception" in parsed
        assert parsed["exception"]["type"] == "ValueError"
        assert "Test exception" in parsed["exception"]["message"]
        assert "traceback" in parsed["exception"]

    def test_format_with_extra_fields(self):
        """Test formatting with extra context fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.extra_fields = {"user_id": 123, "request_id": "abc-def"}

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["user_id"] == 123
        assert parsed["request_id"] == "abc-def"

    def test_format_different_log_levels(self):
        """Test formatting with different log levels."""
        formatter = JSONFormatter()
        levels = [
            (logging.DEBUG, "DEBUG"),
            (logging.INFO, "INFO"),
            (logging.WARNING, "WARNING"),
            (logging.ERROR, "ERROR"),
            (logging.CRITICAL, "CRITICAL"),
        ]

        for level, level_name in levels:
            record = logging.LogRecord(
                name="test",
                level=level,
                pathname="test.py",
                lineno=1,
                msg="Test",
                args=(),
                exc_info=None,
            )
            result = formatter.format(record)
            parsed = json.loads(result)
            assert parsed["level"] == level_name

    def test_format_includes_module_and_function(self):
        """Test that module and function names are included."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="app.services.user_service",
            level=logging.INFO,
            pathname="/app/services/user_service.py",
            lineno=42,
            msg="User created",
            args=(),
            exc_info=None,
        )
        record.funcName = "create_user"

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["module"] == "user_service"
        assert parsed["function"] == "create_user"
        assert parsed["line"] == 42


class TestStructuredLogger:
    """Test StructuredLogger class for contextual logging."""

    def test_initialization(self):
        """Test logger initialization."""
        logger = StructuredLogger("test_logger")
        assert logger.logger.name == "test_logger"
        assert logger._extra_fields == {}

    def test_set_context_single_field(self):
        """Test setting a single context field."""
        logger = StructuredLogger("test")
        logger.set_context(user_id=123)
        assert logger._extra_fields["user_id"] == 123

    def test_set_context_multiple_fields(self):
        """Test setting multiple context fields."""
        logger = StructuredLogger("test")
        logger.set_context(user_id=123, request_id="abc", session="xyz")
        assert logger._extra_fields == {"user_id": 123, "request_id": "abc", "session": "xyz"}

    def test_set_context_overwrites_existing(self):
        """Test that set_context overwrites existing fields."""
        logger = StructuredLogger("test")
        logger.set_context(user_id=123)
        logger.set_context(user_id=456)
        assert logger._extra_fields["user_id"] == 456

    def test_set_context_merges_fields(self):
        """Test that set_context merges new fields with existing ones."""
        logger = StructuredLogger("test")
        logger.set_context(user_id=123)
        logger.set_context(request_id="abc")
        assert logger._extra_fields == {"user_id": 123, "request_id": "abc"}

    def test_clear_context(self):
        """Test clearing all context fields."""
        logger = StructuredLogger("test")
        logger.set_context(user_id=123, request_id="abc")
        logger.clear_context()
        assert logger._extra_fields == {}

    @patch.object(StructuredLogger, "_log")
    def test_debug_logging(self, mock_log):
        """Test debug level logging."""
        logger = StructuredLogger("test")
        logger.debug("Debug message", extra_field="value")
        mock_log.assert_called_once()
        args = mock_log.call_args
        assert args[0][0] == logging.DEBUG
        assert args[0][1] == "Debug message"

    @patch.object(StructuredLogger, "_log")
    def test_info_logging(self, mock_log):
        """Test info level logging."""
        logger = StructuredLogger("test")
        logger.info("Info message", custom="data")
        mock_log.assert_called_once()
        args = mock_log.call_args
        assert args[0][0] == logging.INFO

    @patch.object(StructuredLogger, "_log")
    def test_warning_logging(self, mock_log):
        """Test warning level logging."""
        logger = StructuredLogger("test")
        logger.warning("Warning message")
        mock_log.assert_called_once()
        assert mock_log.call_args[0][0] == logging.WARNING

    @patch.object(StructuredLogger, "_log")
    def test_error_logging(self, mock_log):
        """Test error level logging with exc_info."""
        logger = StructuredLogger("test")
        logger.error("Error message", exc_info=True)
        mock_log.assert_called_once()
        assert mock_log.call_args[0][0] == logging.ERROR

    @patch.object(StructuredLogger, "_log")
    def test_critical_logging(self, mock_log):
        """Test critical level logging with exc_info."""
        logger = StructuredLogger("test")
        logger.critical("Critical message", exc_info=True)
        mock_log.assert_called_once()
        assert mock_log.call_args[0][0] == logging.CRITICAL

    def test_log_internal_copies_context(self):
        """Test that _log creates a copy of context fields."""
        logger = StructuredLogger("test")
        logger.set_context(user_id=123)

        # Mock the logger.handle to inspect the record
        with patch.object(logger.logger, "handle") as mock_handle:
            logger._log(logging.INFO, "Test")
            mock_handle.assert_called_once()
            record = mock_handle.call_args[0][0]
            assert hasattr(record, "extra_fields")
            assert record.extra_fields["user_id"] == 123

    def test_log_merges_extra_fields(self):
        """Test that _log merges extra fields with context."""
        logger = StructuredLogger("test")
        logger.set_context(user_id=123)

        with patch.object(logger.logger, "handle") as mock_handle:
            logger._log(logging.INFO, "Test", extra={"request_id": "abc"})
            record = mock_handle.call_args[0][0]
            assert record.extra_fields["user_id"] == 123
            assert record.extra_fields["request_id"] == "abc"

    def test_log_without_extra_fields(self):
        """Test logging when there are no extra fields."""
        logger = StructuredLogger("test")

        with patch.object(logger.logger, "handle") as mock_handle:
            logger._log(logging.INFO, "Test")
            record = mock_handle.call_args[0][0]
            # extra_fields should not be set if empty
            assert not hasattr(record, "extra_fields")


class TestSetupLogging:
    """Test setup_logging function."""

    def test_setup_logging_default_level(self):
        """Test setting up logging with default INFO level."""
        # Clear existing loggers to ensure clean state
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]
        
        try:
            setup_logging(level=logging.INFO, json_format=False)
            # Verify the root logger level was set
            assert root_logger.level == logging.INFO
        finally:
            # Restore original state
            root_logger.handlers = original_handlers

    def test_setup_logging_removes_existing_handlers(self):
        """Test that setup removes existing handlers."""
        with patch("logging.getLogger") as mock_get:
            mock_root = MagicMock()
            mock_handler1 = MagicMock()
            mock_handler2 = MagicMock()
            mock_root.handlers = [mock_handler1, mock_handler2]
            mock_get.return_value = mock_root

            setup_logging(level=logging.INFO)

            # Verify handlers were removed
            assert mock_root.removeHandler.call_count >= 2

    def test_setup_logging_adds_console_handler(self):
        """Test that console handler is added."""
        with patch("logging.getLogger") as mock_get, patch(
            "logging.StreamHandler"
        ) as mock_stream:
            mock_root = MagicMock()
            mock_root.handlers = []
            mock_get.return_value = mock_root
            mock_handler = MagicMock()
            mock_stream.return_value = mock_handler

            setup_logging(level=logging.DEBUG)

            mock_root.addHandler.assert_called()

    def test_setup_logging_with_json_formatter(self):
        """Test setup with JSON formatter."""
        with patch("logging.getLogger") as mock_get, patch(
            "logging.StreamHandler"
        ) as mock_stream, patch("app.core.logging.JSONFormatter") as mock_json:
            mock_root = MagicMock()
            mock_root.handlers = []
            mock_get.return_value = mock_root
            mock_handler = MagicMock()
            mock_stream.return_value = mock_handler
            mock_formatter = MagicMock()
            mock_json.return_value = mock_formatter

            setup_logging(json_format=True)

            mock_json.assert_called_once()

    def test_setup_logging_with_plain_formatter(self):
        """Test setup with plain text formatter."""
        with patch("logging.getLogger") as mock_get, patch(
            "logging.StreamHandler"
        ), patch("logging.Formatter") as mock_format:
            mock_root = MagicMock()
            mock_root.handlers = []
            mock_get.return_value = mock_root

            setup_logging(json_format=False)

            mock_format.assert_called_once()

    def test_setup_logging_suppresses_noisy_loggers(self):
        """Test that setup suppresses noisy loggers."""
        with patch("logging.getLogger") as mock_get:
            mock_root = MagicMock()
            mock_root.handlers = []
            mock_get.return_value = mock_root

            setup_logging()

            # Check that noisy loggers were accessed
            calls = [str(call) for call in mock_get.call_args_list]
            assert any("sqlalchemy" in str(call) for call in calls)


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_returns_structured_logger(self):
        """Test that get_logger returns a StructuredLogger instance."""
        logger = get_logger("test.module")
        assert isinstance(logger, StructuredLogger)

    def test_get_logger_with_module_name(self):
        """Test getting logger with module name."""
        logger = get_logger("app.services.user")
        assert logger.logger.name == "app.services.user"

    def test_get_logger_different_instances_different_loggers(self):
        """Test that different calls return different logger instances."""
        logger1 = get_logger("test1")
        logger2 = get_logger("test2")
        assert logger1.logger.name != logger2.logger.name

    def test_get_logger_same_name_different_instances(self):
        """Test that same name returns different wrapper instances."""
        logger1 = get_logger("test")
        logger2 = get_logger("test")
        # Should be different wrapper instances
        assert logger1 is not logger2
        # But wrap the same underlying logger
        assert logger1.logger.name == logger2.logger.name


class TestLoggingIntegration:
    """Integration tests for logging system."""

    def test_logging_with_context_and_extra_fields(self):
        """Test logging with both context and extra fields."""
        logger = StructuredLogger("test")
        logger.set_context(user_id=123, session="xyz")

        with patch.object(logger.logger, "handle") as mock_handle:
            logger.info("Action completed", action="login", result="success")
            record = mock_handle.call_args[0][0]
            assert record.extra_fields["user_id"] == 123
            assert record.extra_fields["action"] == "login"

    def test_logging_preserves_context_between_calls(self):
        """Test that context is preserved between log calls."""
        logger = StructuredLogger("test")
        logger.set_context(request_id="abc123")

        with patch.object(logger.logger, "handle") as mock_handle:
            logger.info("First message")
            logger.info("Second message")

        # Both calls should have the context
        for call in mock_handle.call_args_list:
            record = call[0][0]
            assert record.extra_fields["request_id"] == "abc123"

    def test_logging_exception_flow(self):
        """Test logging with exception information in realistic flow."""
        logger = StructuredLogger("test")

        try:
            raise RuntimeError("Test error")
        except RuntimeError:
            logger.error("Operation failed", exc_info=True)


class TestLoggingEdgeCases:
    """Test edge cases and error conditions."""

    def test_logging_with_none_extra_fields(self):
        """Test logging when extra is None."""
        logger = StructuredLogger("test")
        with patch.object(logger.logger, "handle"):
            logger._log(logging.INFO, "Test", extra=None)

    def test_logging_with_empty_string_message(self):
        """Test logging with empty message."""
        logger = StructuredLogger("test")
        logger.info("")

    def test_logging_with_very_long_message(self):
        """Test logging with very long message."""
        logger = StructuredLogger("test")
        long_msg = "x" * 10000
        logger.info(long_msg)

    def test_json_formatter_with_unicode_characters(self):
        """Test JSON formatter with unicode characters."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="测试消息 🚀 Тест",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        parsed = json.loads(result)
        assert "测试消息" in parsed["message"]
        assert "🚀" in parsed["message"]

    def test_structured_logger_context_with_special_values(self):
        """Test context with special values like None, 0, empty string."""
        logger = StructuredLogger("test")
        logger.set_context(none_val=None, zero=0, empty="", false=False)

        with patch.object(logger.logger, "handle") as mock_handle:
            logger.info("Test")
            record = mock_handle.call_args[0][0]
            assert record.extra_fields["none_val"] is None
            assert record.extra_fields["zero"] == 0
            assert record.extra_fields["empty"] == ""
            assert record.extra_fields["false"] is False

    def test_json_formatter_with_large_extra_fields(self):
        """Test JSON formatting with many extra fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        # Add many fields
        record.extra_fields = {f"field_{i}": i for i in range(100)}

        result = formatter.format(record)
        parsed = json.loads(result)
        assert len(parsed) > 100  # At least 100 fields + standard ones
        assert parsed["field_0"] == 0
        assert parsed["field_99"] == 99
