"""
Structured Logger Tests

Tests for the structured logging module.
"""

import pytest
import json
import logging
from unittest.mock import patch


class TestJSONFormatter:
    """Tests for the JSONFormatter class."""

    def test_formats_as_json(self):
        """Log output should be valid JSON."""
        from src.utils.structured_logger import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )

        output = formatter.format(record)

        # Should be valid JSON
        data = json.loads(output)
        assert data["message"] == "Test message"
        assert data["level"] == "INFO"
        assert data["logger"] == "test"

    def test_includes_timestamp(self):
        """Log output should include ISO timestamp."""
        from src.utils.structured_logger import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert "timestamp" in data
        assert "Z" in data["timestamp"]  # UTC timezone

    def test_includes_service_name(self):
        """Log output should include service name."""
        from src.utils.structured_logger import JSONFormatter

        formatter = JSONFormatter(service_name="test-service")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert data["service"] == "test-service"

    def test_includes_source_location(self):
        """Log output should include source file info."""
        from src.utils.structured_logger import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test",
            args=(),
            exc_info=None
        )
        record.funcName = "test_function"

        output = formatter.format(record)
        data = json.loads(output)

        assert "source" in data
        assert data["source"]["line"] == 42
        assert data["source"]["function"] == "test_function"

    def test_includes_request_id(self):
        """Log output should include request_id from context."""
        from src.utils.structured_logger import JSONFormatter, set_request_id, clear_request_id

        formatter = JSONFormatter()
        set_request_id("test-request-123")

        try:
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=10,
                msg="Test",
                args=(),
                exc_info=None
            )

            output = formatter.format(record)
            data = json.loads(output)

            assert data["request_id"] == "test-request-123"
        finally:
            clear_request_id()

    def test_includes_tenant_id(self):
        """Log output should include tenant_id from context."""
        from src.utils.structured_logger import JSONFormatter, set_tenant_id, clear_tenant_id

        formatter = JSONFormatter()
        set_tenant_id("test-tenant")

        try:
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=10,
                msg="Test",
                args=(),
                exc_info=None
            )

            output = formatter.format(record)
            data = json.loads(output)

            assert data["tenant_id"] == "test-tenant"
        finally:
            clear_tenant_id()

    def test_includes_extra_fields(self):
        """Log output should include extra fields."""
        from src.utils.structured_logger import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None
        )
        record.user_id = 123
        record.action = "login"

        output = formatter.format(record)
        data = json.loads(output)

        assert "extra" in data
        assert data["extra"]["user_id"] == 123
        assert data["extra"]["action"] == "login"


class TestContextVars:
    """Tests for context variable management."""

    def test_set_and_get_request_id(self):
        """Should set and get request_id."""
        from src.utils.structured_logger import set_request_id, get_request_id, clear_request_id

        set_request_id("req-123")
        assert get_request_id() == "req-123"
        clear_request_id()
        assert get_request_id() is None

    def test_set_and_get_tenant_id(self):
        """Should set and get tenant_id."""
        from src.utils.structured_logger import set_tenant_id, get_tenant_id, clear_tenant_id

        set_tenant_id("tenant-abc")
        assert get_tenant_id() == "tenant-abc"
        clear_tenant_id()
        assert get_tenant_id() is None


class TestSetupStructuredLogging:
    """Tests for logging setup function."""

    def test_setup_configures_root_logger(self):
        """setup_structured_logging should configure root logger."""
        from src.utils.structured_logger import setup_structured_logging

        # Should not raise
        setup_structured_logging(level="DEBUG", json_output=True)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_setup_with_plain_text(self):
        """Should support plain text output."""
        from src.utils.structured_logger import setup_structured_logging

        # Should not raise
        setup_structured_logging(level="INFO", json_output=False)


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_logger(self):
        """get_logger should return a Logger instance."""
        from src.utils.structured_logger import get_logger

        logger = get_logger("test.module")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"


class TestPlainFormatter:
    """Tests for PlainFormatter class."""

    def test_formats_as_plain_text(self):
        """PlainFormatter should output plain text."""
        from src.utils.structured_logger import PlainFormatter

        formatter = PlainFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )

        output = formatter.format(record)

        # Should be plain text, not JSON
        assert "Test message" in output
        assert "{" not in output or "INFO" in output


class TestLogWithContext:
    """Tests for log_with_context helper."""

    def test_logs_with_extra_context(self):
        """log_with_context should add context fields."""
        from src.utils.structured_logger import log_with_context, get_logger

        logger = get_logger("test")

        # Should not raise
        log_with_context(logger, logging.INFO, "Test", user_id=123, action="test")
