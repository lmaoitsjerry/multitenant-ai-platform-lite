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
