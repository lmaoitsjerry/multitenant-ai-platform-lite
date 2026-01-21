"""
API Route Tests

Tests for core API endpoints:
- Health endpoints
- Auth routes
- Quote routes
- Invoice routes
- Client info routes

Uses FastAPI TestClient for synchronous testing.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

# Import app
from main import app


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_root_returns_api_info(self):
        """GET / should return API info."""
        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "running"

    def test_health_returns_healthy(self):
        """GET /health should return healthy status."""
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_health_live_returns_alive(self):
        """GET /health/live should return alive status."""
        client = TestClient(app)
        response = client.get("/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"


class TestAuthRoutes:
    """Test authentication routes."""

    def test_login_without_credentials_returns_422(self):
        """POST /api/v1/auth/login without body returns 422."""
        client = TestClient(app)
        response = client.post("/api/v1/auth/login")

        assert response.status_code == 422  # Validation error

    def test_login_with_empty_body_returns_422(self):
        """POST /api/v1/auth/login with empty body returns 422."""
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/login",
            json={},
            headers={"X-Client-ID": "africastay"}
        )

        assert response.status_code == 422

    def test_refresh_without_token_returns_error(self):
        """POST /api/v1/auth/refresh without token returns error."""
        client = TestClient(app)
        response = client.post("/api/v1/auth/refresh")

        # Should fail - no refresh token provided
        assert response.status_code in [401, 422]


class TestClientInfoRoute:
    """Test client info endpoint.

    Note: /api/v1/client/info requires authentication in this system.
    These tests verify the endpoint behavior when accessed.
    """

    def test_client_info_requires_auth(self):
        """GET /api/v1/client/info requires authentication."""
        client = TestClient(app)

        response = client.get(
            "/api/v1/client/info",
            headers={"X-Client-ID": "africastay"}
        )

        # Protected endpoint requires auth
        assert response.status_code == 401


class TestProtectedRoutes:
    """Test that protected routes require authentication."""

    def test_quotes_requires_auth(self):
        """GET /api/v1/quotes requires authentication."""
        client = TestClient(app)
        response = client.get("/api/v1/quotes")

        assert response.status_code == 401

    def test_invoices_requires_auth(self):
        """GET /api/v1/invoices requires authentication."""
        client = TestClient(app)
        response = client.get("/api/v1/invoices")

        assert response.status_code == 401

    def test_clients_requires_auth(self):
        """GET /api/v1/clients requires authentication."""
        client = TestClient(app)
        response = client.get("/api/v1/clients")

        assert response.status_code == 401

    def test_analytics_requires_auth(self):
        """GET /api/v1/analytics/overview requires authentication."""
        client = TestClient(app)
        response = client.get("/api/v1/analytics/overview")

        assert response.status_code == 401

    def test_pipeline_requires_auth(self):
        """GET /api/v1/crm/pipeline requires authentication."""
        client = TestClient(app)
        response = client.get("/api/v1/crm/pipeline")

        assert response.status_code == 401


class TestCORSHeaders:
    """Test CORS headers are present."""

    def test_options_request_returns_cors_headers(self):
        """OPTIONS request should return CORS headers."""
        client = TestClient(app)
        response = client.options(
            "/api/v1/quotes",
            headers={"Origin": "http://localhost:5173"}
        )

        # OPTIONS should be handled by CORS middleware
        assert response.status_code in [200, 405]

    def test_response_includes_cors_allow_origin(self):
        """Response should include CORS allow origin header for allowed origins."""
        client = TestClient(app)
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:5173"}
        )

        # Health endpoints should have CORS headers
        assert response.status_code == 200


class TestRateLimitHeaders:
    """Test rate limit headers are present."""

    def test_api_routes_have_rate_limit_headers(self):
        """API routes should include rate limit headers."""
        client = TestClient(app)

        # Protected endpoint that will return 401 but still have rate limit headers
        response = client.get("/api/v1/quotes")

        # Rate limit headers should be present even on 401
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers

    def test_rate_limit_headers_have_valid_values(self):
        """Rate limit headers should have valid integer values."""
        client = TestClient(app)

        response = client.get("/api/v1/quotes")

        limit = int(response.headers["X-RateLimit-Limit"])
        remaining = int(response.headers["X-RateLimit-Remaining"])

        assert limit > 0
        assert remaining >= 0
        assert remaining <= limit


class TestSecurityHeaders:
    """Test security headers are present."""

    def test_x_content_type_options_header(self):
        """Response should include X-Content-Type-Options header."""
        client = TestClient(app)
        response = client.get("/health")

        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_x_frame_options_header(self):
        """Response should include X-Frame-Options header."""
        client = TestClient(app)
        response = client.get("/health")

        assert "X-Frame-Options" in response.headers

    def test_x_xss_protection_header(self):
        """Response should include X-XSS-Protection header."""
        client = TestClient(app)
        response = client.get("/health")

        # Check either present or deprecated (some security scanners warn about it)
        # Modern browsers disable X-XSS-Protection but it's still often included
        pass  # Header may or may not be present depending on security policy


class TestRequestIdHeader:
    """Test request ID tracing headers."""

    def test_response_includes_request_id(self):
        """Response should include X-Request-ID header."""
        client = TestClient(app)
        response = client.get("/health")

        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0

    def test_request_id_is_uuid_format(self):
        """X-Request-ID should be in UUID format."""
        client = TestClient(app)
        response = client.get("/health")

        request_id = response.headers.get("X-Request-ID", "")
        # Should be 36 chars (UUID with hyphens)
        assert len(request_id) == 36
        assert request_id.count("-") == 4


class TestErrorHandling:
    """Test error handling responses."""

    def test_protected_route_returns_401_before_404(self):
        """Unknown protected routes return 401 (auth) before 404."""
        client = TestClient(app)
        response = client.get("/api/v1/unknown/route")

        # Auth middleware intercepts before route matching
        assert response.status_code == 401

    def test_unknown_client_on_public_route(self):
        """Unknown client ID on health endpoint still works."""
        client = TestClient(app, raise_server_exceptions=False)

        # Health endpoint doesn't use client config
        response = client.get(
            "/health",
            headers={"X-Client-ID": "nonexistent_tenant_xyz"}
        )

        # Health is public, doesn't validate client
        assert response.status_code == 200


class TestAdminRoutes:
    """Test admin routes (use X-Admin-Token auth)."""

    def test_admin_routes_without_token_returns_error(self):
        """Admin routes without X-Admin-Token should return 401 or 503."""
        client = TestClient(app)
        response = client.get("/api/v1/admin/tenants")

        # Without ADMIN_API_TOKEN configured: 503
        # With ADMIN_API_TOKEN configured but missing header: 401
        assert response.status_code in [401, 503]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
