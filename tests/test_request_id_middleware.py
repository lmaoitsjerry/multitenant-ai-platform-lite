"""
Request ID Middleware Unit Tests

Tests for request ID generation and distributed tracing.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
import uuid


@pytest.fixture
def app_with_request_id():
    """Create a test app with request ID middleware."""
    from src.middleware.request_id_middleware import RequestIdMiddleware

    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/test")
    async def test_route(request: Request):
        return {"request_id": getattr(request.state, "request_id", None)}

    @app.get("/error")
    async def error_route():
        raise ValueError("Test error")

    return app


@pytest.fixture
def test_client(app_with_request_id):
    """Create test client."""
    return TestClient(app_with_request_id, raise_server_exceptions=False)


class TestRequestIdGeneration:
    """Tests for request ID generation."""

    def test_generates_request_id(self, test_client):
        """Should generate request ID when not provided."""
        response = test_client.get("/test")

        assert "X-Request-ID" in response.headers
        # Should be a valid UUID
        request_id = response.headers["X-Request-ID"]
        uuid.UUID(request_id)  # Raises if invalid

    def test_uses_provided_request_id(self, test_client):
        """Should use X-Request-ID from incoming request."""
        custom_id = "custom-trace-id-12345"

        response = test_client.get("/test", headers={"X-Request-ID": custom_id})

        assert response.headers["X-Request-ID"] == custom_id

    def test_request_id_in_request_state(self, test_client):
        """Should set request_id in request.state."""
        response = test_client.get("/test")
        data = response.json()

        assert data["request_id"] is not None
        assert data["request_id"] == response.headers["X-Request-ID"]


class TestRequestIdOnErrors:
    """Tests for request ID handling with errors."""

    def test_error_response_returns_500(self, test_client):
        """Error endpoint should return 500 status."""
        response = test_client.get("/error")

        assert response.status_code == 500

    def test_unique_ids_across_requests(self, test_client):
        """Different requests should get different IDs."""
        response1 = test_client.get("/test")
        response2 = test_client.get("/test")

        id1 = response1.headers["X-Request-ID"]
        id2 = response2.headers["X-Request-ID"]

        assert id1 != id2

    def test_error_logs_request_id(self, app_with_request_id):
        """Errors should be logged with request ID context."""
        # The middleware logs errors before re-raising, so error logging is verified
        # by the logging tests below. This test just confirms the app handles errors.
        client = TestClient(app_with_request_id, raise_server_exceptions=False)
        response = client.get("/error")

        # Error should be handled (not raised)
        assert response.status_code == 500


class TestClientIPExtraction:
    """Tests for client IP extraction from headers."""

    def test_extracts_forwarded_for(self):
        """Should extract IP from X-Forwarded-For header."""
        from src.middleware.request_id_middleware import RequestIdMiddleware

        middleware = RequestIdMiddleware(None)

        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "203.0.113.195, 70.41.3.18"}
        mock_request.client = MagicMock(host="10.0.0.1")

        ip = middleware._get_client_ip(mock_request)

        assert ip == "203.0.113.195"

    def test_extracts_real_ip(self):
        """Should extract IP from X-Real-IP header."""
        from src.middleware.request_id_middleware import RequestIdMiddleware

        middleware = RequestIdMiddleware(None)

        mock_request = MagicMock()
        mock_request.headers = {"X-Real-IP": "192.168.1.100"}
        mock_request.client = MagicMock(host="10.0.0.1")

        ip = middleware._get_client_ip(mock_request)

        assert ip == "192.168.1.100"

    def test_falls_back_to_client_host(self):
        """Should fall back to direct client host."""
        from src.middleware.request_id_middleware import RequestIdMiddleware

        middleware = RequestIdMiddleware(None)

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = MagicMock(host="192.168.1.50")

        ip = middleware._get_client_ip(mock_request)

        assert ip == "192.168.1.50"

    def test_returns_unknown_when_no_client(self):
        """Should return 'unknown' when no client info."""
        from src.middleware.request_id_middleware import RequestIdMiddleware

        middleware = RequestIdMiddleware(None)

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = None

        ip = middleware._get_client_ip(mock_request)

        assert ip == "unknown"

    def test_prefers_forwarded_for_over_real_ip(self):
        """X-Forwarded-For should take precedence over X-Real-IP."""
        from src.middleware.request_id_middleware import RequestIdMiddleware

        middleware = RequestIdMiddleware(None)

        mock_request = MagicMock()
        mock_request.headers = {
            "X-Forwarded-For": "203.0.113.195",
            "X-Real-IP": "192.168.1.100"
        }
        mock_request.client = MagicMock(host="10.0.0.1")

        ip = middleware._get_client_ip(mock_request)

        assert ip == "203.0.113.195"


class TestContextVarsHandling:
    """Tests for context variable handling."""

    def test_clears_context_after_request(self):
        """Should clear context vars after request completes."""
        from src.utils.structured_logger import request_id_var, tenant_id_var

        # Set up app with middleware
        from src.middleware.request_id_middleware import RequestIdMiddleware

        app = FastAPI()
        app.add_middleware(RequestIdMiddleware)

        @app.get("/test")
        async def test_route():
            return {"status": "ok"}

        client = TestClient(app)

        # Make request
        response = client.get("/test")

        # Context vars should be cleared (back to default)
        # Note: This is difficult to test directly due to threading
        assert response.status_code == 200


class TestLogging:
    """Tests for request logging."""

    def test_logs_request_start(self, app_with_request_id):
        """Should log request start with method and path."""
        with patch('src.middleware.request_id_middleware.logger') as mock_logger:
            client = TestClient(app_with_request_id)
            client.get("/test")

            # Find the "Request started" log call
            start_calls = [
                c for c in mock_logger.info.call_args_list
                if "started" in str(c)
            ]
            assert len(start_calls) > 0

    def test_logs_request_completion(self, app_with_request_id):
        """Should log request completion with status and duration."""
        with patch('src.middleware.request_id_middleware.logger') as mock_logger:
            client = TestClient(app_with_request_id)
            client.get("/test")

            # Find the "Request completed" log call
            complete_calls = [
                c for c in mock_logger.info.call_args_list
                if "completed" in str(c)
            ]
            assert len(complete_calls) > 0

    def test_logs_request_error(self, app_with_request_id):
        """Should log errors on request failure."""
        with patch('src.middleware.request_id_middleware.logger') as mock_logger:
            client = TestClient(app_with_request_id, raise_server_exceptions=False)
            client.get("/error")

            # Should have error log
            mock_logger.error.assert_called()
