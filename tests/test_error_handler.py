"""
Error Handler Unit Tests

Tests for secure error response generation.
"""

import pytest
import logging
from unittest.mock import MagicMock, patch
from fastapi import HTTPException


class TestSafeErrorResponse:
    """Tests for safe_error_response function."""

    def test_returns_http_exception(self):
        """safe_error_response should return HTTPException."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = Exception("Internal details")

        result = safe_error_response(500, "processing", exc, mock_logger)

        assert isinstance(result, HTTPException)
        assert result.status_code == 500

    def test_logs_full_error_details(self):
        """safe_error_response should log full exception details."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = Exception("Internal details here")

        safe_error_response(500, "processing", exc, mock_logger)

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "processing failed" in call_args[0][0]
        assert "Internal details here" in call_args[0][0]
        assert call_args[1]["exc_info"] is True

    def test_server_error_generic_message(self):
        """5xx errors should return generic message."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = Exception("SQL injection detected in query")

        result = safe_error_response(500, "processing request", exc, mock_logger)

        # Should NOT contain internal details
        assert "SQL injection" not in result.detail
        assert "internal error" in result.detail.lower()
        assert "processing request" in result.detail.lower()

    def test_server_error_503(self):
        """503 errors should return generic message."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = Exception("Database connection refused")

        result = safe_error_response(503, "connecting to database", exc, mock_logger)

        assert result.status_code == 503
        assert "Database connection" not in result.detail
        assert "internal error" in result.detail.lower()

    def test_client_error_different_message(self):
        """4xx errors should have different message format."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = ValueError("Invalid email format")

        result = safe_error_response(400, "validating input", exc, mock_logger)

        assert result.status_code == 400
        # Client errors can be more specific
        assert "check your request" in result.detail.lower()
        # But still shouldn't expose internals
        assert "Invalid email format" not in result.detail

    def test_client_error_404(self):
        """404 errors should return client-facing message."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = Exception("User with id abc123 not found")

        result = safe_error_response(404, "finding user", exc, mock_logger)

        assert result.status_code == 404
        assert "abc123" not in result.detail


class TestLogAndRaise:
    """Tests for log_and_raise function."""

    def test_raises_http_exception(self):
        """log_and_raise should raise HTTPException."""
        from src.utils.error_handler import log_and_raise

        mock_logger = MagicMock()
        exc = Exception("Test error")

        with pytest.raises(HTTPException) as exc_info:
            log_and_raise(500, "testing", exc, mock_logger)

        assert exc_info.value.status_code == 500

    def test_logs_before_raising(self):
        """log_and_raise should log before raising."""
        from src.utils.error_handler import log_and_raise

        mock_logger = MagicMock()
        exc = Exception("Test error")

        try:
            log_and_raise(500, "testing", exc, mock_logger)
        except HTTPException:
            pass

        mock_logger.error.assert_called_once()

    def test_raises_with_sanitized_message(self):
        """log_and_raise should raise with sanitized message."""
        from src.utils.error_handler import log_and_raise

        mock_logger = MagicMock()
        exc = Exception("Secret password: abc123")

        with pytest.raises(HTTPException) as exc_info:
            log_and_raise(500, "authenticating", exc, mock_logger)

        assert "abc123" not in exc_info.value.detail
        assert "password" not in exc_info.value.detail.lower()


class TestErrorHandlerIntegration:
    """Integration tests for error handling."""

    def test_typical_try_except_pattern(self):
        """Test typical usage in a route handler."""
        from src.utils.error_handler import log_and_raise

        logger = logging.getLogger("test")

        def mock_route_handler():
            try:
                # Simulate database error
                raise ConnectionError("Connection to postgres:5432 refused")
            except Exception as e:
                log_and_raise(500, "fetching data", e, logger)

        with pytest.raises(HTTPException) as exc_info:
            mock_route_handler()

        assert exc_info.value.status_code == 500
        # Connection details should not be exposed
        assert "postgres:5432" not in exc_info.value.detail
        assert "Connection" not in exc_info.value.detail

    def test_error_messages_by_status_code(self):
        """Test that error messages vary by status code appropriately."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = Exception("test")

        # Server errors
        result_500 = safe_error_response(500, "op", exc, mock_logger)
        result_502 = safe_error_response(502, "op", exc, mock_logger)
        result_503 = safe_error_response(503, "op", exc, mock_logger)

        assert "internal error" in result_500.detail.lower()
        assert "internal error" in result_502.detail.lower()
        assert "internal error" in result_503.detail.lower()

        # Client errors
        result_400 = safe_error_response(400, "op", exc, mock_logger)
        result_404 = safe_error_response(404, "op", exc, mock_logger)
        result_422 = safe_error_response(422, "op", exc, mock_logger)

        assert "check your request" in result_400.detail.lower()
        assert "check your request" in result_404.detail.lower()
        assert "check your request" in result_422.detail.lower()


class TestSensitiveDataProtection:
    """Tests for sensitive data protection in error responses."""

    def test_hides_database_connection_strings(self):
        """Should not expose database connection strings."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = Exception("postgresql://user:password@localhost:5432/db")

        result = safe_error_response(500, "connecting", exc, mock_logger)

        assert "password" not in result.detail.lower()
        assert "postgresql" not in result.detail.lower()
        assert "localhost:5432" not in result.detail

    def test_hides_api_keys(self):
        """Should not expose API keys in error messages."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = Exception("API key invalid: sk_live_abc123xyz789")

        result = safe_error_response(500, "authenticating", exc, mock_logger)

        assert "sk_live_abc123xyz789" not in result.detail
        assert "sk_live" not in result.detail

    def test_hides_jwt_tokens(self):
        """Should not expose JWT tokens in error messages."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        exc = Exception(f"Token validation failed: {token}")

        result = safe_error_response(401, "validating token", exc, mock_logger)

        assert token not in result.detail
        assert "eyJ" not in result.detail

    def test_hides_file_paths(self):
        """Should not expose full file paths."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = Exception("File not found: /home/app/secrets/config.json")

        result = safe_error_response(500, "loading config", exc, mock_logger)

        assert "/home/app/secrets" not in result.detail
        assert "config.json" not in result.detail

    def test_hides_ip_addresses(self):
        """Should not expose internal IP addresses."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = Exception("Connection refused to 192.168.1.100:5432")

        result = safe_error_response(500, "connecting", exc, mock_logger)

        assert "192.168.1.100" not in result.detail


class TestExceptionTypeHandling:
    """Tests for handling different exception types."""

    def test_handles_value_error(self):
        """Should handle ValueError."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = ValueError("Invalid value")

        result = safe_error_response(400, "validating", exc, mock_logger)

        assert result.status_code == 400

    def test_handles_type_error(self):
        """Should handle TypeError."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = TypeError("Expected str, got int")

        result = safe_error_response(400, "processing", exc, mock_logger)

        assert result.status_code == 400

    def test_handles_key_error(self):
        """Should handle KeyError."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = KeyError("missing_key")

        result = safe_error_response(400, "accessing data", exc, mock_logger)

        assert result.status_code == 400

    def test_handles_connection_error(self):
        """Should handle ConnectionError."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = ConnectionError("Connection refused")

        result = safe_error_response(503, "connecting", exc, mock_logger)

        assert result.status_code == 503

    def test_handles_timeout_error(self):
        """Should handle TimeoutError."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = TimeoutError("Request timed out after 30s")

        result = safe_error_response(504, "requesting", exc, mock_logger)

        assert result.status_code == 504

    def test_handles_runtime_error(self):
        """Should handle RuntimeError."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = RuntimeError("Unexpected state")

        result = safe_error_response(500, "processing", exc, mock_logger)

        assert result.status_code == 500


class TestOperationDescriptions:
    """Tests for operation description in error messages."""

    def test_operation_description_included(self):
        """Operation description should be in error message."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = Exception("test")

        result = safe_error_response(500, "generating quote", exc, mock_logger)

        assert "generating quote" in result.detail.lower()

    def test_various_operations(self):
        """Should handle various operation descriptions."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = Exception("test")

        operations = [
            "fetching user",
            "creating order",
            "updating profile",
            "deleting record",
            "sending email",
        ]

        for op in operations:
            result = safe_error_response(500, op, exc, mock_logger)
            assert op in result.detail.lower()


class TestLoggerIntegration:
    """Tests for logger integration."""

    def test_uses_provided_logger(self):
        """Should use the provided logger instance."""
        from src.utils.error_handler import safe_error_response

        logger1 = MagicMock()
        logger2 = MagicMock()
        exc = Exception("test")

        safe_error_response(500, "op", exc, logger1)
        safe_error_response(500, "op", exc, logger2)

        logger1.error.assert_called_once()
        logger2.error.assert_called_once()

    def test_logs_with_exc_info(self):
        """Should log with exc_info for stack traces."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = Exception("test")

        safe_error_response(500, "op", exc, mock_logger)

        call_kwargs = mock_logger.error.call_args[1]
        assert call_kwargs.get("exc_info") is True

    def test_log_message_contains_operation(self):
        """Log message should contain operation description."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = Exception("test")

        safe_error_response(500, "processing payment", exc, mock_logger)

        log_message = mock_logger.error.call_args[0][0]
        assert "processing payment" in log_message.lower()

    def test_log_message_contains_exception_details(self):
        """Log message should contain exception details."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = ValueError("Invalid input value")

        safe_error_response(400, "validating", exc, mock_logger)

        log_message = mock_logger.error.call_args[0][0]
        assert "Invalid input value" in log_message


class TestEdgeCases:
    """Edge case tests for error handler."""

    def test_empty_operation_description(self):
        """Should handle empty operation description."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = Exception("test")

        result = safe_error_response(500, "", exc, mock_logger)

        assert result.status_code == 500

    def test_exception_with_empty_message(self):
        """Should handle exception with empty message."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = Exception("")

        result = safe_error_response(500, "operation", exc, mock_logger)

        assert result.status_code == 500

    def test_exception_with_none_args(self):
        """Should handle exception with None args."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = Exception(None)

        result = safe_error_response(500, "operation", exc, mock_logger)

        assert result.status_code == 500

    def test_unicode_in_exception_message(self):
        """Should handle Unicode in exception message."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        exc = Exception("Error with Unicode: test")

        result = safe_error_response(500, "operation", exc, mock_logger)

        assert result.status_code == 500

    def test_very_long_exception_message(self):
        """Should handle very long exception messages."""
        from src.utils.error_handler import safe_error_response

        mock_logger = MagicMock()
        long_message = "x" * 10000
        exc = Exception(long_message)

        result = safe_error_response(500, "operation", exc, mock_logger)

        # Should not include the full long message
        assert len(result.detail) < 10000
