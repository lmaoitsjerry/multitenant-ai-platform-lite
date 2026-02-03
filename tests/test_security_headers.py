"""
Security Headers Middleware Unit Tests

Tests for the security headers middleware.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def app_with_security_headers():
    """Create a test app with security headers middleware."""
    from src.middleware.security_headers import SecurityHeadersMiddleware

    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/test")
    async def test_route():
        return {"message": "test"}

    return app


@pytest.fixture
def test_client(app_with_security_headers):
    """Create test client."""
    return TestClient(app_with_security_headers)


class TestSecurityHeaders:
    """Tests for security headers being set correctly."""

    def test_x_frame_options_header(self, test_client):
        """Should set X-Frame-Options to DENY."""
        response = test_client.get("/test")

        assert response.headers["X-Frame-Options"] == "DENY"

    def test_x_content_type_options_header(self, test_client):
        """Should set X-Content-Type-Options to nosniff."""
        response = test_client.get("/test")

        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_x_xss_protection_header(self, test_client):
        """Should set X-XSS-Protection."""
        response = test_client.get("/test")

        assert response.headers["X-XSS-Protection"] == "1; mode=block"

    def test_content_security_policy_header(self, test_client):
        """Should set Content-Security-Policy."""
        response = test_client.get("/test")

        assert "Content-Security-Policy" in response.headers
        # Default CSP should be restrictive
        assert "default-src 'none'" in response.headers["Content-Security-Policy"]

    def test_referrer_policy_header(self, test_client):
        """Should set Referrer-Policy."""
        response = test_client.get("/test")

        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_permissions_policy_header(self, test_client):
        """Should set Permissions-Policy."""
        response = test_client.get("/test")

        assert "Permissions-Policy" in response.headers
        assert "geolocation=()" in response.headers["Permissions-Policy"]
        assert "camera=()" in response.headers["Permissions-Policy"]
        assert "microphone=()" in response.headers["Permissions-Policy"]


class TestHSTSHeader:
    """Tests for Strict-Transport-Security header."""

    def test_no_hsts_in_development(self):
        """Should NOT set HSTS in development environment."""
        from src.middleware.security_headers import SecurityHeadersMiddleware

        with patch.dict("os.environ", {"ENVIRONMENT": "development"}):
            app = FastAPI()
            app.add_middleware(SecurityHeadersMiddleware)

            @app.get("/test")
            async def test_route():
                return {"message": "test"}

            client = TestClient(app)
            response = client.get("/test")

            assert "Strict-Transport-Security" not in response.headers

    def test_hsts_in_production(self):
        """Should set HSTS in production environment."""
        from src.middleware.security_headers import SecurityHeadersMiddleware

        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            app = FastAPI()
            app.add_middleware(SecurityHeadersMiddleware)

            @app.get("/test")
            async def test_route():
                return {"message": "test"}

            client = TestClient(app)
            response = client.get("/test")

            assert "Strict-Transport-Security" in response.headers
            assert "max-age=31536000" in response.headers["Strict-Transport-Security"]
            assert "includeSubDomains" in response.headers["Strict-Transport-Security"]


class TestCustomCSP:
    """Tests for custom Content-Security-Policy."""

    def test_custom_csp_from_env(self):
        """Should use custom CSP from environment variable."""
        from src.middleware.security_headers import SecurityHeadersMiddleware

        custom_csp = "default-src 'self'; script-src 'self'"

        with patch.dict("os.environ", {"SECURITY_CSP": custom_csp}):
            app = FastAPI()
            app.add_middleware(SecurityHeadersMiddleware)

            @app.get("/test")
            async def test_route():
                return {"message": "test"}

            client = TestClient(app)
            response = client.get("/test")

            assert response.headers["Content-Security-Policy"] == custom_csp


class TestSecurityHeadersWithErrors:
    """Tests for security headers with error responses."""

    def test_headers_on_error_response(self):
        """Security headers should be set even on error responses."""
        from src.middleware.security_headers import SecurityHeadersMiddleware
        from fastapi import HTTPException

        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/error")
        async def error_route():
            raise HTTPException(status_code=400, detail="Bad request")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/error")

        assert response.status_code == 400
        # Security headers should still be present
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-Content-Type-Options"] == "nosniff"


class TestSecurityHeadersConstants:
    """Tests for security headers middleware constants."""

    def test_default_csp_constant(self):
        """DEFAULT_CSP should be restrictive."""
        from src.middleware.security_headers import SecurityHeadersMiddleware

        csp = SecurityHeadersMiddleware.DEFAULT_CSP

        assert "default-src 'none'" in csp
        assert "frame-ancestors 'none'" in csp
