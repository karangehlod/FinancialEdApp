"""
Structured logging configuration for the application.
Uses Python's logging module with JSON formatting for structured logs.
"""

import logging
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict
from pathlib import Path

# Ensure logs directory exists
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class StructuredLogger:
    """Wrapper around Python logger for structured logging with extra context."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._extra_fields: Dict[str, Any] = {}

    def set_context(self, **kwargs) -> None:
        """Set context fields that will be included in all log messages."""
        self._extra_fields.update(kwargs)

    def clear_context(self) -> None:
        """Clear all context fields."""
        self._extra_fields.clear()

    def _log(
        self,
        level: int,
        message: str,
        exc_info: bool = False,
        extra: Dict[str, Any] | None = None,
    ) -> None:
        """Internal logging method with context support."""
        log_extra = self._extra_fields.copy()
        if extra:
            log_extra.update(extra)

        record = self.logger.makeRecord(
            name=self.logger.name,
            level=level,
            fn=self.logger.name,
            lno=0,
            msg=message,
            args=(),
            exc_info=None,
        )

        if log_extra:
            record.extra_fields = log_extra

        if exc_info:
            import sys

            record.exc_info = sys.exc_info()

        self.logger.handle(record)

    def debug(self, message: str, *args, **kwargs) -> None:
        """Log debug level message. Supports %-style positional args."""
        if args:
            message = message % args
        self._log(logging.DEBUG, message, extra=kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        """Log info level message. Supports %-style positional args."""
        if args:
            message = message % args
        self._log(logging.INFO, message, extra=kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        """Log warning level message. Supports %-style positional args."""
        if args:
            message = message % args
        self._log(logging.WARNING, message, extra=kwargs)

    def error(self, message: str, *args, exc_info: bool = False, **kwargs) -> None:
        """Log error level message. Supports %-style positional args."""
        if args:
            message = message % args
        self._log(logging.ERROR, message, exc_info=exc_info, extra=kwargs)

    def critical(self, message: str, *args, exc_info: bool = False, **kwargs) -> None:
        """Log critical level message. Supports %-style positional args."""
        if args:
            message = message % args
        self._log(logging.CRITICAL, message, exc_info=exc_info, extra=kwargs)


def setup_logging(level: int = logging.INFO, json_format: bool = True) -> None:
    """
    Configure application logging.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to use JSON formatting (True) or plain text (False)
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatters
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler(LOGS_DIR / "app.log")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Error file handler
    error_handler = logging.FileHandler(LOGS_DIR / "error.log")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    # Suppress noisy loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name)
