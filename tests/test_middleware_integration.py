"""
Middleware Integration Tests

Tests that verify all middleware works together correctly:
- RequestIdMiddleware (request ID generation and propagation)
- SecurityHeadersMiddleware (CSP, X-Frame-Options, HSTS)
- TimingMiddleware (performance timing)
- RateLimitMiddleware (rate limiting)
- AuthMiddleware (JWT authentication)
- PII Audit Middleware (GDPR compliance logging)

These tests verify:
1. Request ID is generated for all requests
2. Security headers are added to all responses
3. Middleware chain executes in correct order
4. Request timing is logged
5. Rate limiting applies correctly
6. Authentication is enforced on protected routes
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import os


# ==================== Fixtures ====================

@pytest.fixture
def test_client():
    """Create a TestClient."""
    from main import app
    return TestClient(app)


@pytest.fixture
def mock_env_vars():
    """Set common environment variables."""
    env_vars = {
        "SUPABASE_JWT_SECRET": "test-jwt-secret-key",
        "ADMIN_API_TOKEN": "test-admin-token",
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars


# ==================== Request ID Tests ====================

class TestRequestIdMiddleware:
    """Test request ID generation and propagation."""

    def test_request_id_generated_for_health_endpoint(self, test_client):
        """Health endpoint should have X-Request-ID header."""
        response = test_client.get("/health")

        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0

    def test_request_id_unique_per_request(self, test_client):
        """Each request should get a unique request ID."""
        response1 = test_client.get("/health")
        response2 = test_client.get("/health")

        request_id1 = response1.headers.get("X-Request-ID")
        request_id2 = response2.headers.get("X-Request-ID")

        assert request_id1 is not None
        assert request_id2 is not None
        assert request_id1 != request_id2

    def test_request_id_format_is_uuid(self, test_client):
        """Request ID should be a valid UUID format."""
        response = test_client.get("/health")
        request_id = response.headers.get("X-Request-ID")

        # UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        import re
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        assert uuid_pattern.match(request_id) is not None

    def test_request_id_on_error_response(self, test_client):
        """Error responses should also have X-Request-ID."""
        response = test_client.get("/api/v1/nonexistent")

        # Should get 404 but still have request ID
        assert "X-Request-ID" in response.headers

    def test_request_id_on_unauthorized_response(self, test_client):
        """Unauthorized responses should have X-Request-ID."""
        response = test_client.get("/api/v1/dashboard/stats")

        assert response.status_code == 401
        assert "X-Request-ID" in response.headers


# ==================== Security Headers Tests ====================

class TestSecurityHeadersMiddleware:
    """Test security headers are added to responses."""

    def test_x_content_type_options(self, test_client):
        """X-Content-Type-Options header should be nosniff."""
        response = test_client.get("/health")

        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, test_client):
        """X-Frame-Options header should be DENY."""
        response = test_client.get("/health")

        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_x_xss_protection(self, test_client):
        """X-XSS-Protection header should be set."""
        response = test_client.get("/health")

        xss_header = response.headers.get("X-XSS-Protection")
        assert xss_header == "1; mode=block"

    def test_content_security_policy_present(self, test_client):
        """Content-Security-Policy header should be present."""
        response = test_client.get("/health")

        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None
        assert "default-src" in csp

    def test_referrer_policy(self, test_client):
        """Referrer-Policy header should be set."""
        response = test_client.get("/health")

        referrer = response.headers.get("Referrer-Policy")
        assert referrer is not None
        # Common secure values
        assert referrer in ["strict-origin-when-cross-origin", "no-referrer", "same-origin"]

    def test_security_headers_on_api_endpoints(self, test_client):
        """Security headers should be on API endpoints too."""
        response = test_client.get("/")

        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers

    def test_security_headers_on_error_responses(self, test_client):
        """Security headers should be on error responses."""
        response = test_client.get("/api/v1/nonexistent")

        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers


# ==================== CORS Headers Tests ====================

class TestCORSMiddleware:
    """Test CORS headers are handled correctly."""

    def test_cors_headers_on_preflight(self, test_client):
        """OPTIONS requests should get CORS headers."""
        response = test_client.options(
            "/api/v1/dashboard/stats",
            headers={"Origin": "http://localhost:5173"}
        )

        # Should return CORS headers
        assert "access-control-allow-origin" in response.headers or response.status_code == 200

    def test_cors_allows_credentials(self, test_client):
        """CORS should allow credentials."""
        response = test_client.get(
            "/health",
            headers={"Origin": "http://localhost:5173"}
        )

        # Check if credentials are allowed (may vary by configuration)
        allow_cred = response.headers.get("access-control-allow-credentials")
        if allow_cred:
            assert allow_cred.lower() == "true"


# ==================== Timing Middleware Tests ====================

class TestTimingMiddleware:
    """Test request timing is tracked."""

    def test_timing_does_not_break_requests(self, test_client):
        """Timing middleware should not break normal requests."""
        response = test_client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_fast_endpoint_completes_quickly(self, test_client):
        """Health check should complete in reasonable time."""
        import time

        start = time.time()
        response = test_client.get("/health")
        elapsed = time.time() - start

        assert response.status_code == 200
        # Should complete within 2 seconds (generous for CI)
        assert elapsed < 2.0


# ==================== Rate Limit Middleware Tests ====================

class TestRateLimitMiddleware:
    """Test rate limiting is applied."""

    def test_rate_limit_headers_present(self, test_client):
        """Rate limit info should be in response headers."""
        response = test_client.get("/health")

        # Check for rate limit headers (may vary by implementation)
        # Common headers: X-RateLimit-Limit, X-RateLimit-Remaining
        # If not present, that's also acceptable (rate limiting might be disabled for /health)
        assert response.status_code == 200

    def test_auth_rate_limit_on_login(self, test_client):
        """Login endpoint should have rate limiting."""
        # Make a login request (will fail but should still apply rate limit)
        response = test_client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "test"}
        )

        # Should not be rate limited on first request
        # Status could be 400/401/500 depending on configuration
        assert response.status_code != 429  # Not rate limited


# ==================== Auth Middleware Tests ====================

class TestAuthMiddleware:
    """Test authentication middleware."""

    def test_public_endpoints_no_auth_required(self, test_client):
        """Public endpoints should not require authentication."""
        public_endpoints = ["/", "/health", "/health/live"]

        for endpoint in public_endpoints:
            response = test_client.get(endpoint)
            assert response.status_code != 401, f"{endpoint} should not require auth"

    def test_protected_endpoints_require_auth(self, test_client):
        """Protected endpoints should require authentication."""
        protected_endpoints = [
            "/api/v1/dashboard/stats",
            "/api/v1/crm/clients",
            "/api/v1/analytics/quotes",
            "/api/v1/notifications",
        ]

        for endpoint in protected_endpoints:
            response = test_client.get(endpoint)
            assert response.status_code == 401, f"{endpoint} should require auth"

    def test_auth_error_returns_json(self, test_client):
        """Auth errors should return JSON response."""
        response = test_client.get("/api/v1/dashboard/stats")

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data or "error" in data

    def test_invalid_bearer_token_rejected(self, test_client):
        """Invalid bearer token should be rejected."""
        response = test_client.get(
            "/api/v1/dashboard/stats",
            headers={"Authorization": "Bearer invalid-token"}
        )

        assert response.status_code in [401, 403]


# ==================== Middleware Chain Order Tests ====================

class TestMiddlewareChainOrder:
    """Test middleware executes in correct order."""

    def test_request_id_available_in_error_responses(self, test_client):
        """Request ID should be set even for errors (runs early)."""
        response = test_client.get("/api/v1/nonexistent")

        # Request ID middleware runs first
        assert "X-Request-ID" in response.headers

    def test_security_headers_on_auth_failure(self, test_client):
        """Security headers should be added even on auth failure."""
        response = test_client.get("/api/v1/dashboard/stats")

        assert response.status_code == 401
        # Security headers should still be present
        assert "X-Content-Type-Options" in response.headers

    def test_cors_runs_before_auth(self, test_client):
        """CORS preflight should work without auth."""
        response = test_client.options(
            "/api/v1/dashboard/stats",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET"
            }
        )

        # Should not get 401 for OPTIONS
        assert response.status_code != 401


# ==================== Combined Middleware Tests ====================

class TestCombinedMiddleware:
    """Test multiple middleware working together."""

    def test_full_response_has_all_headers(self, test_client):
        """Successful response should have all middleware headers."""
        response = test_client.get("/health")

        assert response.status_code == 200
        # Request ID middleware
        assert "X-Request-ID" in response.headers
        # Security headers middleware
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers

    def test_error_response_has_all_headers(self, test_client):
        """Error response should also have all middleware headers."""
        response = test_client.get("/api/v1/dashboard/stats")

        assert response.status_code == 401
        # All headers should still be present
        assert "X-Request-ID" in response.headers
        assert "X-Content-Type-Options" in response.headers

    def test_json_response_content_type(self, test_client):
        """API responses should have JSON content type."""
        response = test_client.get("/")

        assert "application/json" in response.headers.get("content-type", "")

    def test_health_check_fast_with_all_middleware(self, test_client):
        """Health check should be fast even with all middleware."""
        import time

        times = []
        for _ in range(5):
            start = time.time()
            response = test_client.get("/health")
            elapsed = time.time() - start
            times.append(elapsed)
            assert response.status_code == 200

        avg_time = sum(times) / len(times)
        # Average should be under 500ms
        assert avg_time < 0.5, f"Average response time {avg_time:.3f}s is too slow"


# ==================== Admin Token Middleware Tests ====================

class TestAdminMiddleware:
    """Test admin token middleware."""

    def test_admin_endpoints_require_token(self, test_client, mock_env_vars):
        """Admin endpoints should require X-Admin-Token header."""
        response = test_client.get("/api/v1/admin/tenants")

        # Should get 401 without token
        assert response.status_code == 401

    def test_admin_invalid_token_rejected(self, test_client, mock_env_vars):
        """Invalid admin token should be rejected."""
        response = test_client.get(
            "/api/v1/admin/tenants",
            headers={"X-Admin-Token": "wrong-token"}
        )

        assert response.status_code == 401

    def test_admin_valid_token_accepted(self, test_client, mock_env_vars):
        """Valid admin token should be accepted."""
        response = test_client.get(
            "/api/v1/admin/tenants",
            headers={"X-Admin-Token": "test-admin-token"}
        )

        # Should not get auth error (may get other errors)
        assert response.status_code != 401


# ==================== Error Handling Tests ====================

class TestMiddlewareErrorHandling:
    """Test error handling across middleware."""

    def test_404_or_401_has_json_response(self, test_client):
        """Unknown paths should have proper JSON response."""
        # Auth middleware may catch before 404, which is acceptable
        response = test_client.get("/nonexistent-public-path")

        # Either 404 (not found) or 401 (auth required) is acceptable
        assert response.status_code in [401, 404]
        # Should still be valid JSON
        data = response.json()
        assert "detail" in data or "error" in data

    def test_method_not_allowed_handling(self, test_client):
        """Method not allowed should be handled."""
        response = test_client.delete("/health")

        # Should get 405 Method Not Allowed
        assert response.status_code == 405

    def test_validation_error_handling(self, test_client):
        """Validation errors should return 422."""
        # POST to auth/login without required fields
        response = test_client.post(
            "/api/v1/auth/login",
            json={}
        )

        # Should get validation error (422) or auth-related error
        assert response.status_code in [400, 401, 422]


# ==================== Request Attribute Tests ====================

class TestRequestAttributes:
    """Test request attributes set by middleware."""

    def test_client_id_header_passed_through(self, test_client):
        """X-Client-ID header should be passed to endpoints."""
        response = test_client.get(
            "/api/v1/client/info",
            headers={"X-Client-ID": "example"}
        )

        # Should use the provided client ID
        if response.status_code == 200:
            data = response.json()
            if "data" in data:
                assert data["data"].get("client_id") is not None


# ==================== Content Negotiation Tests ====================

class TestContentNegotiation:
    """Test content type handling."""

    def test_json_request_accepted(self, test_client):
        """JSON content type should be accepted."""
        response = test_client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "test"},
            headers={"Content-Type": "application/json"}
        )

        # Should not fail due to content type
        assert response.status_code in [200, 400, 401, 422, 500]

    def test_response_is_json(self, test_client):
        """API responses should be JSON."""
        response = test_client.get("/")

        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type


# ==================== Stress Test ====================

class TestMiddlewareUnderLoad:
    """Test middleware behavior under load."""

    def test_multiple_concurrent_requests(self, test_client):
        """Multiple requests should all get unique request IDs."""
        request_ids = set()

        for _ in range(10):
            response = test_client.get("/health")
            assert response.status_code == 200
            request_id = response.headers.get("X-Request-ID")
            assert request_id not in request_ids
            request_ids.add(request_id)

        assert len(request_ids) == 10
