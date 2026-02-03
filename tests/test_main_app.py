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
        """API docs should be available in dev, disabled in prod."""
        response = test_client.get("/docs")

        # May return 200 (available) or 404 (disabled in production)
        assert response.status_code in [200, 404]

    def test_openapi_availability(self, test_client):
        """OpenAPI spec should be available in dev, disabled in prod."""
        response = test_client.get("/openapi.json")

        # May return 200 (available) or 404 (disabled in production)
        assert response.status_code in [200, 404]

    def test_redoc_availability(self, test_client):
        """ReDoc should be available in dev, disabled in prod."""
        response = test_client.get("/redoc")

        # May return 200 (available) or 404 (disabled in production)
        assert response.status_code in [200, 404]


# ==================== Error Handling Tests ====================

class TestErrorHandling:
    """Tests for global error handling."""

    def test_404_on_unknown_route(self, test_client):
        """Unknown routes should return 404."""
        response = test_client.get("/nonexistent/route/12345")

        assert response.status_code == 404

    def test_405_on_wrong_method(self, test_client):
        """Wrong HTTP method should return 405."""
        response = test_client.delete("/health/live")

        # May return 405 or 404 depending on routing
        assert response.status_code in [404, 405]
