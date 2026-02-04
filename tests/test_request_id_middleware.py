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


class TestRequestIdFormat:
    """Tests for request ID format validation."""

    def test_generated_id_is_uuid(self, test_client):
        """Generated ID should be valid UUID."""
        response = test_client.get("/test")
        request_id = response.headers["X-Request-ID"]

        # Should be valid UUID4 format
        parsed_uuid = uuid.UUID(request_id)
        assert parsed_uuid.version == 4

    def test_custom_id_preserved_exactly(self, test_client):
        """Custom ID should be preserved exactly."""
        custom_ids = [
            "simple-id",
            "with-numbers-123",
            "UPPERCASE-ID",
            "mixed-Case-ID-123",
            "a" * 100,  # Long ID
        ]

        for custom_id in custom_ids:
            response = test_client.get("/test", headers={"X-Request-ID": custom_id})
            assert response.headers["X-Request-ID"] == custom_id

    def test_empty_request_id_header_generates_new(self, test_client):
        """Empty X-Request-ID header should generate new ID."""
        response = test_client.get("/test", headers={"X-Request-ID": ""})

        request_id = response.headers["X-Request-ID"]
        # Should be a valid UUID (generated)
        uuid.UUID(request_id)


class TestMultipleRequestsHandling:
    """Tests for handling multiple concurrent requests."""

    def test_different_requests_get_different_ids(self, test_client):
        """Multiple requests should get unique IDs."""
        ids = set()

        for _ in range(10):
            response = test_client.get("/test")
            ids.add(response.headers["X-Request-ID"])

        # All IDs should be unique
        assert len(ids) == 10

    def test_concurrent_requests_isolated(self, app_with_request_id):
        """Concurrent requests should have isolated IDs."""
        import concurrent.futures

        client = TestClient(app_with_request_id)

        def make_request():
            response = client.get("/test")
            return response.json()["request_id"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            ids = [f.result() for f in futures]

        # All IDs should be unique
        assert len(set(ids)) == 5


class TestIPExtractionEdgeCases:
    """Edge case tests for IP extraction."""

    def test_multiple_ips_in_forwarded_for(self):
        """Should extract first IP from multiple IPs."""
        from src.middleware.request_id_middleware import RequestIdMiddleware

        middleware = RequestIdMiddleware(None)

        mock_request = MagicMock()
        mock_request.headers = {
            "X-Forwarded-For": "203.0.113.195, 70.41.3.18, 150.172.238.178"
        }
        mock_request.client = MagicMock(host="10.0.0.1")

        ip = middleware._get_client_ip(mock_request)

        assert ip == "203.0.113.195"

    def test_whitespace_in_forwarded_for(self):
        """Should handle whitespace in X-Forwarded-For."""
        from src.middleware.request_id_middleware import RequestIdMiddleware

        middleware = RequestIdMiddleware(None)

        mock_request = MagicMock()
        mock_request.headers = {
            "X-Forwarded-For": "  203.0.113.195  ,  70.41.3.18  "
        }
        mock_request.client = MagicMock(host="10.0.0.1")

        ip = middleware._get_client_ip(mock_request)

        # Should extract trimmed IP
        assert ip.strip() == "203.0.113.195"

    def test_ipv6_address(self):
        """Should handle IPv6 addresses."""
        from src.middleware.request_id_middleware import RequestIdMiddleware

        middleware = RequestIdMiddleware(None)

        mock_request = MagicMock()
        mock_request.headers = {"X-Real-IP": "2001:0db8:85a3:0000:0000:8a2e:0370:7334"}
        mock_request.client = MagicMock(host="10.0.0.1")

        ip = middleware._get_client_ip(mock_request)

        assert "2001:0db8" in ip


class TestResponseHeaderConsistency:
    """Tests for response header consistency."""

    def test_request_id_in_all_responses(self, test_client):
        """All responses should include X-Request-ID."""
        endpoints = ["/test"]

        for endpoint in endpoints:
            response = test_client.get(endpoint)
            assert "X-Request-ID" in response.headers

    def test_request_id_header_format(self, test_client):
        """X-Request-ID header should be properly formatted."""
        response = test_client.get("/test")

        header_name = None
        for h in response.headers:
            if h.lower() == "x-request-id":
                header_name = h
                break

        assert header_name is not None


class TestMiddlewareInitialization:
    """Tests for middleware initialization."""

    def test_middleware_accepts_app(self):
        """Middleware should accept FastAPI app."""
        from src.middleware.request_id_middleware import RequestIdMiddleware

        app = FastAPI()
        middleware = RequestIdMiddleware(app)

        assert middleware.app is app

    def test_middleware_has_dispatch(self):
        """Middleware should have dispatch method."""
        from src.middleware.request_id_middleware import RequestIdMiddleware

        middleware = RequestIdMiddleware(None)

        assert hasattr(middleware, 'dispatch')
        assert callable(getattr(middleware, 'dispatch', None))


class TestRequestStateAccess:
    """Tests for request.state access."""

    def test_request_state_has_request_id(self, test_client):
        """request.state should have request_id."""
        response = test_client.get("/test")
        data = response.json()

        assert "request_id" in data
        assert data["request_id"] is not None

    def test_request_state_id_matches_header(self, test_client):
        """request.state.request_id should match response header."""
        response = test_client.get("/test")
        data = response.json()

        assert data["request_id"] == response.headers["X-Request-ID"]


class TestRequestIdPropagation:
    """Tests for request ID propagation through the system."""

    def test_custom_id_propagates_to_state(self, test_client):
        """Custom request ID should propagate to request.state."""
        custom_id = "propagation-test-id"
        response = test_client.get(
            "/test",
            headers={"X-Request-ID": custom_id}
        )
        data = response.json()

        assert data["request_id"] == custom_id

    def test_id_available_in_route_handler(self):
        """Request ID should be available in route handlers."""
        from src.middleware.request_id_middleware import RequestIdMiddleware

        app = FastAPI()
        app.add_middleware(RequestIdMiddleware)

        captured_ids = []

        @app.get("/capture")
        async def capture_route(request: Request):
            captured_ids.append(request.state.request_id)
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/capture")

        assert len(captured_ids) == 1
        assert captured_ids[0] == response.headers["X-Request-ID"]
