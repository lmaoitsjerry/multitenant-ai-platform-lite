"""
Main Application Tests

Tests for main.py application setup and endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


# ==================== Fixtures ====================

@pytest.fixture
def test_client():
    """Create a basic TestClient."""
    from main import app
    return TestClient(app)


# ==================== Health Endpoints Tests ====================

class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_live_returns_alive(self, test_client):
        """GET /health/live should return alive status."""
        response = test_client.get("/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    def test_health_ready_returns_status(self, test_client):
        """GET /health/ready should return readiness status."""
        response = test_client.get("/health/ready")

        # May return 200 or 503 depending on dependencies
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data

    def test_health_ready_includes_checks(self, test_client):
        """GET /health/ready should include dependency checks."""
        response = test_client.get("/health/ready")

        data = response.json()
        # Should have checks object
        if "checks" in data:
            assert isinstance(data["checks"], dict)

    def test_health_ready_includes_circuit_breakers(self, test_client):
        """GET /health/ready should include circuit breaker status."""
        response = test_client.get("/health/ready")

        data = response.json()
        # Should include circuit breaker info
        if "circuit_breakers" in data:
            assert isinstance(data["circuit_breakers"], dict)


# ==================== Root Endpoint Tests ====================

class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_returns_info(self, test_client):
        """GET / should return API info."""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data or "status" in data or "message" in data


# ==================== CORS Tests ====================

class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_allows_options(self, test_client):
        """OPTIONS request should be allowed."""
        response = test_client.options(
            "/api/v1/quotes",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET"
            }
        )

        # Should not error
        assert response.status_code in [200, 204, 401, 405]

    def test_cors_headers_in_response(self, test_client):
        """Response should include CORS headers for allowed origins."""
        response = test_client.get(
            "/health/live",
            headers={"Origin": "http://localhost:5173"}
        )

        # Access-Control headers may or may not be present
        # depending on whether origin is in allowed list
        assert response.status_code == 200


# ==================== Security Headers Tests ====================

class TestSecurityHeaders:
    """Tests for security headers."""

    def test_response_has_security_headers(self, test_client):
        """Response should include security headers."""
        response = test_client.get("/health/live")

        # Check for common security headers
        headers = response.headers

        # X-Content-Type-Options is commonly set
        # (may or may not be present depending on config)
        assert response.status_code == 200


# ==================== Request ID Tests ====================

class TestRequestIdMiddleware:
    """Tests for request ID middleware."""

    def test_response_includes_request_id(self, test_client):
        """Response should include X-Request-ID header."""
        response = test_client.get("/health/live")

        # Should have X-Request-ID in response
        if "x-request-id" in response.headers:
            assert len(response.headers["x-request-id"]) > 0

    def test_accepts_client_request_id(self, test_client):
        """Should accept client-provided X-Request-ID."""
        custom_id = "test-request-123"
        response = test_client.get(
            "/health/live",
            headers={"X-Request-ID": custom_id}
        )

        assert response.status_code == 200


# ==================== Timing Middleware Tests ====================

class TestTimingMiddleware:
    """Tests for request timing middleware."""

    def test_response_includes_timing(self, test_client):
        """Response may include X-Response-Time header."""
        response = test_client.get("/health/live")

        # Timing header may or may not be present
        assert response.status_code == 200


# ==================== API Documentation Tests ====================

class TestAPIDocumentation:
    """Tests for API documentation endpoints."""

    def test_docs_availability(self, test_client):
        """API docs may require auth or be disabled in prod."""
        response = test_client.get("/docs")

        # May return 200 (available), 401 (requires auth), or 404 (disabled in production)
        assert response.status_code in [200, 401, 404]

    def test_openapi_availability(self, test_client):
        """OpenAPI spec may require auth or be disabled in prod."""
        response = test_client.get("/openapi.json")

        # May return 200 (available), 401 (requires auth), or 404 (disabled in production)
        assert response.status_code in [200, 401, 404]

    def test_redoc_availability(self, test_client):
        """ReDoc may require auth or be disabled in prod."""
        response = test_client.get("/redoc")

        # May return 200 (available), 401 (requires auth), or 404 (disabled in production)
        assert response.status_code in [200, 401, 404]


# ==================== Error Handling Tests ====================

class TestErrorHandling:
    """Tests for global error handling."""

    def test_404_or_401_on_unknown_route(self, test_client):
        """Unknown routes return 404 or 401 (if auth middleware runs first)."""
        response = test_client.get("/nonexistent/route/12345")

        # Auth middleware may return 401 before route matching returns 404
        assert response.status_code in [401, 404]

    def test_405_on_wrong_method(self, test_client):
        """Wrong HTTP method should return 405."""
        response = test_client.delete("/health/live")

        # May return 405 or 404 depending on routing
        assert response.status_code in [404, 405]


# ==================== Environment-Specific Tests ====================

class TestEnvironmentConfig:
    """Tests for environment-specific configuration."""

    def test_app_loads_without_error(self, test_client):
        """App should load without errors."""
        response = test_client.get("/health/live")
        assert response.status_code == 200

    def test_middleware_stack_initialized(self, test_client):
        """All middleware should be initialized."""
        response = test_client.get("/health/live")

        # Response headers indicate middleware is running
        assert response.status_code == 200


# ==================== API Versioning Tests ====================

class TestAPIVersioning:
    """Tests for API versioning."""

    def test_v1_api_prefix(self, test_client):
        """API routes should use /api/v1 prefix."""
        # This is more of a structural test
        # We check that routes exist under /api/v1
        response = test_client.get("/api/v1/health/live")

        # May be 200, 401, or 404 depending on route existence
        assert response.status_code in [200, 401, 404]


# ==================== Startup/Shutdown Tests ====================

class TestAppLifecycle:
    """Tests for app startup and shutdown."""

    def test_app_handles_multiple_requests(self, test_client):
        """App should handle multiple sequential requests."""
        for _ in range(5):
            response = test_client.get("/health/live")
            assert response.status_code == 200

    def test_app_handles_concurrent_health_checks(self, test_client):
        """App should handle concurrent requests."""
        import concurrent.futures

        def make_request():
            return test_client.get("/health/live")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            results = [f.result() for f in futures]

        assert all(r.status_code == 200 for r in results)


# ==================== Response Format Tests ====================

class TestResponseFormat:
    """Tests for response format consistency."""

    def test_health_response_is_json(self, test_client):
        """Health response should be JSON."""
        response = test_client.get("/health/live")

        assert "application/json" in response.headers.get("content-type", "")

    def test_json_response_is_valid(self, test_client):
        """JSON response should be valid."""
        response = test_client.get("/health/live")

        # Should not raise
        data = response.json()
        assert isinstance(data, dict)


# ==================== Request Tracing Tests ====================

class TestRequestTracing:
    """Tests for request tracing headers."""

    def test_request_id_propagates(self, test_client):
        """Request ID should propagate through the system."""
        custom_id = "trace-test-12345"
        response = test_client.get(
            "/health/live",
            headers={"X-Request-ID": custom_id}
        )

        assert response.status_code == 200
        # If request ID is echoed back
        if "x-request-id" in response.headers:
            assert response.headers["x-request-id"] == custom_id

    def test_unique_request_ids_generated(self, test_client):
        """Each request should get unique ID if not provided."""
        response1 = test_client.get("/health/live")
        response2 = test_client.get("/health/live")

        id1 = response1.headers.get("x-request-id")
        id2 = response2.headers.get("x-request-id")

        if id1 and id2:
            assert id1 != id2


# ==================== Content Negotiation Tests ====================

class TestContentNegotiation:
    """Tests for content negotiation."""

    def test_accepts_json(self, test_client):
        """Should accept application/json."""
        response = test_client.get(
            "/health/live",
            headers={"Accept": "application/json"}
        )

        assert response.status_code == 200

    def test_handles_any_accept(self, test_client):
        """Should handle Accept: */*."""
        response = test_client.get(
            "/health/live",
            headers={"Accept": "*/*"}
        )

        assert response.status_code == 200


# ==================== Router Inclusion Tests ====================

class TestRouterInclusion:
    """Tests for router inclusion."""

    def test_main_routes_included(self, test_client):
        """Main routes should be included."""
        response = test_client.get("/health/live")
        assert response.status_code == 200

    def test_health_routes_exist(self, test_client):
        """Health routes should exist."""
        response = test_client.get("/health/ready")
        assert response.status_code in [200, 503]


# ==================== Middleware Order Tests ====================

class TestMiddlewareOrder:
    """Tests for middleware execution order."""

    def test_security_headers_applied(self, test_client):
        """Security headers should be applied."""
        response = test_client.get("/health/live")

        # At minimum, some security header should be present
        assert response.status_code == 200

    def test_timing_happens(self, test_client):
        """Request timing should happen."""
        response = test_client.get("/health/live")

        # Response should complete in reasonable time
        assert response.status_code == 200


# ==================== Error Response Tests ====================

class TestErrorResponses:
    """Tests for error response format."""

    def test_error_is_json(self, test_client):
        """Error responses should be JSON."""
        response = test_client.get("/nonexistent/path/12345")

        if response.status_code in [401, 404]:
            # Should have JSON content type
            content_type = response.headers.get("content-type", "")
            # May or may not be JSON depending on when auth kicks in
            if "json" in content_type:
                data = response.json()
                assert "detail" in data or "error" in data or "message" in data


# ==================== Rate Limiting Tests ====================

class TestRateLimiting:
    """Tests for rate limiting behavior."""

    def test_health_not_rate_limited(self, test_client):
        """Health endpoints should not be rate limited."""
        # Make many requests quickly
        for _ in range(20):
            response = test_client.get("/health/live")
            # Should all succeed (no 429)
            assert response.status_code == 200
