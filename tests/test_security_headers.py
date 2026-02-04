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


class TestPermissionsPolicy:
    """Tests for Permissions-Policy header."""

    def test_geolocation_disabled(self, test_client):
        """Geolocation should be disabled."""
        response = test_client.get("/test")

        policy = response.headers.get("Permissions-Policy", "")
        assert "geolocation=()" in policy

    def test_camera_disabled(self, test_client):
        """Camera should be disabled."""
        response = test_client.get("/test")

        policy = response.headers.get("Permissions-Policy", "")
        assert "camera=()" in policy

    def test_microphone_disabled(self, test_client):
        """Microphone should be disabled."""
        response = test_client.get("/test")

        policy = response.headers.get("Permissions-Policy", "")
        assert "microphone=()" in policy


class TestCSPDirectives:
    """Tests for Content-Security-Policy directives."""

    def test_csp_default_src(self, test_client):
        """CSP should have default-src directive."""
        response = test_client.get("/test")

        csp = response.headers.get("Content-Security-Policy", "")
        assert "default-src" in csp

    def test_csp_frame_ancestors(self, test_client):
        """CSP should have frame-ancestors directive."""
        response = test_client.get("/test")

        csp = response.headers.get("Content-Security-Policy", "")
        assert "frame-ancestors" in csp

    def test_csp_base_uri(self, test_client):
        """CSP should have base-uri directive."""
        response = test_client.get("/test")

        csp = response.headers.get("Content-Security-Policy", "")
        assert "base-uri" in csp


class TestSecurityHeadersOnDifferentMethods:
    """Tests for security headers on different HTTP methods."""

    @pytest.fixture
    def full_app(self):
        """Create app with multiple endpoints."""
        from src.middleware.security_headers import SecurityHeadersMiddleware

        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/test")
        async def get_route():
            return {"method": "GET"}

        @app.post("/test")
        async def post_route():
            return {"method": "POST"}

        @app.put("/test")
        async def put_route():
            return {"method": "PUT"}

        @app.delete("/test")
        async def delete_route():
            return {"method": "DELETE"}

        return app

    @pytest.fixture
    def full_client(self, full_app):
        """Create test client."""
        return TestClient(full_app)

    def test_headers_on_get(self, full_client):
        """GET should have security headers."""
        response = full_client.get("/test")

        assert response.headers["X-Frame-Options"] == "DENY"

    def test_headers_on_post(self, full_client):
        """POST should have security headers."""
        response = full_client.post("/test")

        assert response.headers["X-Frame-Options"] == "DENY"

    def test_headers_on_put(self, full_client):
        """PUT should have security headers."""
        response = full_client.put("/test")

        assert response.headers["X-Frame-Options"] == "DENY"

    def test_headers_on_delete(self, full_client):
        """DELETE should have security headers."""
        response = full_client.delete("/test")

        assert response.headers["X-Frame-Options"] == "DENY"


class TestSecurityHeadersEdgeCases:
    """Edge case tests for security headers."""

    def test_headers_on_empty_response(self):
        """Headers should be set on empty responses."""
        from src.middleware.security_headers import SecurityHeadersMiddleware
        from fastapi.responses import Response

        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/empty")
        async def empty_route():
            return Response(status_code=204)

        client = TestClient(app)
        response = client.get("/empty")

        assert response.status_code == 204
        assert response.headers["X-Frame-Options"] == "DENY"

    def test_headers_on_redirect(self):
        """Headers should be set on redirects."""
        from src.middleware.security_headers import SecurityHeadersMiddleware
        from fastapi.responses import RedirectResponse

        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/redirect")
        async def redirect_route():
            return RedirectResponse(url="/test")

        @app.get("/test")
        async def test_route():
            return {"status": "ok"}

        client = TestClient(app, follow_redirects=False)
        response = client.get("/redirect")

        assert response.status_code == 307
        assert response.headers["X-Frame-Options"] == "DENY"

    def test_headers_on_large_response(self):
        """Headers should be set on large responses."""
        from src.middleware.security_headers import SecurityHeadersMiddleware

        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/large")
        async def large_route():
            return {"data": "x" * 10000}

        client = TestClient(app)
        response = client.get("/large")

        assert response.status_code == 200
        assert response.headers["X-Frame-Options"] == "DENY"


class TestXFrameOptionsValues:
    """Tests for X-Frame-Options header values."""

    def test_x_frame_options_is_deny(self, test_client):
        """X-Frame-Options should be DENY."""
        response = test_client.get("/test")

        assert response.headers["X-Frame-Options"] == "DENY"

    def test_x_frame_options_not_sameorigin(self, test_client):
        """X-Frame-Options should not be SAMEORIGIN."""
        response = test_client.get("/test")

        assert response.headers["X-Frame-Options"] != "SAMEORIGIN"


class TestXContentTypeOptions:
    """Tests for X-Content-Type-Options header."""

    def test_value_is_nosniff(self, test_client):
        """X-Content-Type-Options should be nosniff."""
        response = test_client.get("/test")

        assert response.headers["X-Content-Type-Options"] == "nosniff"


class TestXXSSProtection:
    """Tests for X-XSS-Protection header."""

    def test_xss_protection_enabled(self, test_client):
        """X-XSS-Protection should enable protection."""
        response = test_client.get("/test")

        header = response.headers["X-XSS-Protection"]
        assert header.startswith("1")

    def test_xss_protection_mode_block(self, test_client):
        """X-XSS-Protection should use mode=block."""
        response = test_client.get("/test")

        header = response.headers["X-XSS-Protection"]
        assert "mode=block" in header


class TestReferrerPolicy:
    """Tests for Referrer-Policy header."""

    def test_referrer_policy_value(self, test_client):
        """Referrer-Policy should be strict-origin-when-cross-origin."""
        response = test_client.get("/test")

        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_referrer_policy_not_no_referrer(self, test_client):
        """Referrer-Policy should not be no-referrer (too strict for some use cases)."""
        response = test_client.get("/test")

        assert response.headers["Referrer-Policy"] != "no-referrer"
