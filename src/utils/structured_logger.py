"""
Structured JSON logging with request ID tracing.

This module provides:
- JSON-formatted log output for machine parsing (Cloud Logging, Datadog, etc.)
- Request ID propagation via contextvars (thread-safe, works with async)
- Automatic request_id injection into every log entry
- Exception formatting with tracebacks

Usage:
    from src.utils.structured_logger import setup_structured_logging, get_logger, set_request_id

    setup_structured_logging()
    set_request_id("abc-123")
    logger = get_logger(__name__)
    logger.info("Processing request", extra={"user_id": 42})
"""

import logging
import json
import sys
import os
from datetime import datetime, timezone
from contextvars import ContextVar
from typing import Optional, Any, Dict


# Context variables for async-safe request tracing (thread-safe, async-safe)
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
tenant_id_var: ContextVar[Optional[str]] = ContextVar('tenant_id', default=None)


def set_request_id(request_id: str) -> None:
    """Set request ID for current context."""
    request_id_var.set(request_id)


def get_request_id() -> Optional[str]:
    """Get request ID for current context."""
    return request_id_var.get()


def clear_request_id() -> None:
    """Clear request ID for current context."""
    request_id_var.set(None)


def set_tenant_id(tenant_id: str) -> None:
    """Set tenant ID for current context."""
    tenant_id_var.set(tenant_id)


def get_tenant_id() -> Optional[str]:
    """Get tenant ID for current context."""
    return tenant_id_var.get()


def clear_tenant_id() -> None:
    """Clear tenant ID for current context."""
    tenant_id_var.set(None)


class JSONFormatter(logging.Formatter):
    """JSON log formatter with request_id injection.

    Formats log records as JSON with consistent structure:
    {
        "timestamp": "2024-01-21T15:30:00.123456Z",
        "level": "INFO",
        "logger": "module.name",
        "message": "Log message",
        "request_id": "abc-123",
        "service": "multi-tenant-ai-platform",
        ...extra fields...
    }
    """

    def __init__(self, service_name: str = "multi-tenant-ai-platform"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string.

        Args:
            record: The log record to format

        Returns:
            JSON-formatted string
        """
        # Build base log data
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id(),
            "tenant_id": get_tenant_id(),
            "service": self.service_name,
        }

        # Add source location for debugging
        log_data["source"] = {
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # Add any extra fields passed via extra={} parameter
        # Standard LogRecord attributes to exclude
        standard_attrs = {
            'name', 'msg', 'args', 'created', 'filename', 'funcName',
            'levelname', 'levelno', 'lineno', 'module', 'msecs',
            'pathname', 'process', 'processName', 'relativeCreated',
            'stack_info', 'exc_info', 'exc_text', 'thread', 'threadName',
            'message', 'taskName'
        }

        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith('_'):
                # Ensure value is JSON serializable
                try:
                    json.dumps(value)
                    extra_fields[key] = value
                except (TypeError, ValueError):
                    extra_fields[key] = str(value)

        if extra_fields:
            log_data["extra"] = extra_fields

        return json.dumps(log_data, default=str)


class PlainFormatter(logging.Formatter):
    """Plain text formatter with request_id for development.

    Format: timestamp - logger - level - [request_id] message
    """

    def format(self, record: logging.LogRecord) -> str:
        request_id = get_request_id()
        request_id_str = f"[{request_id}] " if request_id else ""

        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

        base_message = f"{timestamp} - {record.name} - {record.levelname} - {request_id_str}{record.getMessage()}"

        if record.exc_info:
            base_message += "\n" + self.formatException(record.exc_info)

        return base_message


def setup_structured_logging(
    level: str = "INFO",
    json_output: bool = True,
    service_name: str = "multi-tenant-ai-platform"
) -> None:
    """Configure structured JSON logging for the application.

    This should be called once at application startup, before any logging
    statements are executed.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: If True, output JSON format. If False, use plain text (for development)
        service_name: Service name to include in log entries
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to prevent duplicate logs
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create handler with appropriate formatter
    handler = logging.StreamHandler(sys.stdout)

    if json_output:
        handler.setFormatter(JSONFormatter(service_name=service_name))
    else:
        handler.setFormatter(PlainFormatter())

    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        A configured Logger instance
    """
    return logging.getLogger(name)


class StructuredLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that automatically includes request_id and extra context.

    Usage:
        base_logger = get_logger(__name__)
        logger = StructuredLoggerAdapter(base_logger, {"tenant_id": "africastay"})
        logger.info("Processing request")  # Includes tenant_id automatically
    """

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Add extra context to log kwargs.

        Args:
            msg: The log message
            kwargs: Keyword arguments passed to the logging call

        Returns:
            Tuple of (message, updated_kwargs)
        """
        extra = kwargs.get('extra', {})

        # Add adapter's extra context
        extra.update(self.extra)

        # Always include current request_id
        extra['request_id'] = get_request_id()

        kwargs['extra'] = extra
        return msg, kwargs


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **context: Any
) -> None:
    """Log a message with additional context fields.

    Convenience function for logging with extra context fields.

    Args:
        logger: The logger to use
        level: Log level (e.g., logging.INFO)
        message: The log message
        **context: Additional fields to include in the log entry

    Example:
        log_with_context(logger, logging.INFO, "User created",
                        user_id=123, tenant_id="africastay")
    """
    logger.log(level, message, extra=context)
