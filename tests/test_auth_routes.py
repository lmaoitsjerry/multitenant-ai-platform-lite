"""
Auth Routes Unit Tests

Tests for authentication API endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient


# ==================== Fixtures ====================

@pytest.fixture
def test_client():
    """Create a basic TestClient."""
    from main import app
    return TestClient(app)


@pytest.fixture
def mock_auth_service():
    """Create a mock AuthService."""
    service = MagicMock()
    service.login = AsyncMock()
    service.logout = AsyncMock()
    service.refresh_token = AsyncMock()
    service.verify_jwt = MagicMock()
    service.request_password_reset = AsyncMock()
    service.update_password = AsyncMock()
    service.get_user_by_auth_id = AsyncMock()
    service.create_auth_user = AsyncMock()
    return service


# ==================== Model Tests ====================

class TestLoginRequest:
    """Tests for LoginRequest model."""

    def test_login_request_with_email_password(self):
        """LoginRequest should accept email and password."""
        from src.api.auth_routes import LoginRequest

        request = LoginRequest(
            email="test@example.com",
            password="secretpass"
        )

        assert request.email == "test@example.com"
        assert request.password == "secretpass"
        assert request.tenant_id is None

    def test_login_request_with_tenant_id(self):
        """LoginRequest should accept optional tenant_id."""
        from src.api.auth_routes import LoginRequest

        request = LoginRequest(
            email="test@example.com",
            password="pass",
            tenant_id="my-tenant"
        )

        assert request.tenant_id == "my-tenant"

    def test_login_request_validates_email(self):
        """LoginRequest should validate email format."""
        from src.api.auth_routes import LoginRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            LoginRequest(
                email="not-an-email",
                password="pass"
            )


class TestLoginResponse:
    """Tests for LoginResponse model."""

    def test_login_response_success(self):
        """LoginResponse should represent successful login."""
        from src.api.auth_routes import LoginResponse

        response = LoginResponse(
            success=True,
            access_token="token123",
            refresh_token="refresh456",
            expires_at=3600,
            user={"id": "1", "email": "test@example.com"}
        )

        assert response.success is True
        assert response.access_token == "token123"
        assert response.error is None

    def test_login_response_failure(self):
        """LoginResponse should represent failed login."""
        from src.api.auth_routes import LoginResponse

        response = LoginResponse(
            success=False,
            error="Invalid credentials"
        )

        assert response.success is False
        assert response.error == "Invalid credentials"
        assert response.access_token is None


class TestRefreshRequest:
    """Tests for RefreshRequest model."""

    def test_refresh_request_requires_token(self):
        """RefreshRequest should require refresh_token."""
        from src.api.auth_routes import RefreshRequest

        request = RefreshRequest(refresh_token="refresh-token-value")

        assert request.refresh_token == "refresh-token-value"


class TestPasswordResetRequest:
    """Tests for PasswordResetRequest model."""

    def test_password_reset_validates_email(self):
        """PasswordResetRequest should validate email."""
        from src.api.auth_routes import PasswordResetRequest
        from pydantic import ValidationError

        request = PasswordResetRequest(email="valid@example.com")
        assert request.email == "valid@example.com"

        with pytest.raises(ValidationError):
            PasswordResetRequest(email="invalid")


class TestProfileUpdateRequest:
    """Tests for ProfileUpdateRequest model."""

    def test_profile_update_all_optional(self):
        """ProfileUpdateRequest should have optional fields."""
        from src.api.auth_routes import ProfileUpdateRequest

        request = ProfileUpdateRequest()

        assert request.name is None
        assert request.phone is None

    def test_profile_update_with_values(self):
        """ProfileUpdateRequest should accept values."""
        from src.api.auth_routes import ProfileUpdateRequest

        request = ProfileUpdateRequest(
            name="John Doe",
            phone="+1234567890"
        )

        assert request.name == "John Doe"
        assert request.phone == "+1234567890"


# ==================== Dependency Tests ====================

class TestGetAuthService:
    """Tests for get_auth_service dependency."""

    def test_get_auth_service_with_header(self):
        """Should use X-Client-ID header when provided."""
        from src.api.auth_routes import get_auth_service

        with patch('src.api.auth_routes.get_config') as mock_get_config:
            mock_config = MagicMock()
            mock_config.supabase_url = "https://test.supabase.co"
            mock_config.supabase_service_key = "test-key"
            mock_get_config.return_value = mock_config

            with patch('src.api.auth_routes.AuthService') as mock_auth:
                get_auth_service(x_client_id="my-tenant")

                mock_get_config.assert_called_once_with("my-tenant")

    def test_get_auth_service_raises_on_invalid_client(self):
        """Should raise HTTPException for unknown client."""
        from src.api.auth_routes import get_auth_service

        with patch('src.api.auth_routes.get_config', side_effect=FileNotFoundError()):
            with pytest.raises(HTTPException) as exc_info:
                get_auth_service(x_client_id="unknown-client")

            assert exc_info.value.status_code == 400


class TestGetPlatformAuthService:
    """Tests for get_platform_auth_service dependency."""

    def test_get_platform_auth_service_with_env(self):
        """Should use environment variables."""
        from src.api.auth_routes import get_platform_auth_service

        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://platform.supabase.co',
            'SUPABASE_SERVICE_KEY': 'service-key'
        }):
            with patch('src.api.auth_routes.AuthService') as mock_auth:
                get_platform_auth_service()

                mock_auth.assert_called_once_with(
                    supabase_url='https://platform.supabase.co',
                    supabase_key='service-key'
                )

    def test_get_platform_auth_service_raises_without_env(self):
        """Should raise HTTPException when env not configured."""
        from src.api.auth_routes import get_platform_auth_service

        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(HTTPException) as exc_info:
                get_platform_auth_service()

            assert exc_info.value.status_code == 500


class TestGetTenantId:
    """Tests for get_tenant_id dependency."""

    def test_get_tenant_id_from_header(self):
        """Should use header value when provided."""
        from src.api.auth_routes import get_tenant_id

        result = get_tenant_id(x_client_id="header-tenant")

        assert result == "header-tenant"

    def test_get_tenant_id_from_env(self):
        """Should fall back to env var."""
        from src.api.auth_routes import get_tenant_id

        with patch.dict('os.environ', {'CLIENT_ID': 'env-tenant'}):
            result = get_tenant_id(x_client_id=None)

            assert result == "env-tenant"

    def test_get_tenant_id_default(self):
        """Should use default when no header or env."""
        from src.api.auth_routes import get_tenant_id

        with patch.dict('os.environ', {}, clear=True):
            result = get_tenant_id(x_client_id=None)

            assert result == "africastay"


# ==================== Endpoint Tests ====================

class TestLoginEndpoint:
    """Tests for POST /api/v1/auth/login endpoint."""

    def test_login_without_body(self, test_client):
        """POST /login without body should return 422."""
        response = test_client.post("/api/v1/auth/login")

        assert response.status_code == 422

    def test_login_validates_email(self, test_client):
        """POST /login should validate email format."""
        response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "not-an-email",
                "password": "password"
            }
        )

        assert response.status_code == 422


class TestLogoutEndpoint:
    """Tests for POST /api/v1/auth/logout endpoint."""

    def test_logout_endpoint_exists(self, test_client):
        """POST /logout endpoint should exist."""
        # Will fail auth but endpoint should exist
        response = test_client.post("/api/v1/auth/logout")

        # Should be auth error, not 404
        assert response.status_code != 404


class TestRefreshEndpoint:
    """Tests for POST /api/v1/auth/refresh endpoint."""

    def test_refresh_requires_body(self, test_client):
        """POST /refresh without body should fail (auth or validation)."""
        response = test_client.post("/api/v1/auth/refresh")

        # Could be 401 (auth required before body parsed) or 422 (validation)
        assert response.status_code in [401, 422]


class TestMeEndpoint:
    """Tests for GET /api/v1/auth/me endpoint."""

    def test_me_requires_auth(self, test_client):
        """GET /me should require authorization header."""
        response = test_client.get("/api/v1/auth/me")

        assert response.status_code == 401
        assert "Authorization" in response.json()["detail"]

    def test_me_validates_bearer_format(self, test_client):
        """GET /me should validate Bearer token format."""
        response = test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "InvalidFormat"}
        )

        assert response.status_code == 401


class TestPasswordResetEndpoint:
    """Tests for POST /api/v1/auth/password/reset endpoint."""

    def test_password_reset_requires_email(self, test_client):
        """POST /password/reset should require email."""
        response = test_client.post("/api/v1/auth/password/reset")

        assert response.status_code == 422


class TestPasswordChangeEndpoint:
    """Tests for POST /api/v1/auth/password/change endpoint."""

    def test_password_change_requires_auth(self, test_client):
        """POST /password/change should require auth."""
        response = test_client.post(
            "/api/v1/auth/password/change",
            json={"new_password": "newpass123"}
        )

        assert response.status_code == 401


class TestProfileUpdateEndpoint:
    """Tests for PATCH /api/v1/auth/profile endpoint."""

    def test_profile_update_requires_auth(self, test_client):
        """PATCH /profile should require auth."""
        response = test_client.patch(
            "/api/v1/auth/profile",
            json={"name": "New Name"}
        )

        assert response.status_code == 401


class TestAcceptInviteEndpoint:
    """Tests for POST /api/v1/auth/invite/accept endpoint."""

    def test_accept_invite_requires_token(self, test_client):
        """POST /invite/accept should require token."""
        response = test_client.post(
            "/api/v1/auth/invite/accept",
            json={"password": "newpass"}
        )

        # Missing token query param
        assert response.status_code == 422


# ==================== Helper Tests ====================

class TestGetAuthLimiter:
    """Tests for get_auth_limiter function."""

    def test_get_auth_limiter_returns_limiter(self):
        """get_auth_limiter should return limiter instance."""
        from src.api.auth_routes import get_auth_limiter

        limiter = get_auth_limiter()

        assert limiter is not None
