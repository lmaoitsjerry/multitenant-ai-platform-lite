"""
Auth Service Unit Tests

Tests for the Supabase authentication service.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import jwt
from datetime import datetime, timedelta


# ==================== Fixtures ====================

@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client."""
    client = MagicMock()
    client.auth = MagicMock()
    client.table = MagicMock(return_value=MagicMock())
    return client


@pytest.fixture
def auth_service(mock_supabase_client):
    """Create an AuthService with mocked client."""
    from src.services.auth_service import AuthService, _auth_client_cache

    # Clear cache
    _auth_client_cache.clear()

    with patch('src.services.auth_service.get_cached_auth_client', return_value=mock_supabase_client):
        with patch.dict('os.environ', {'SUPABASE_JWT_SECRET': 'test-secret'}):
            service = AuthService(
                supabase_url="https://test.supabase.co",
                supabase_key="test-key"
            )
            return service


# ==================== Initialization Tests ====================

class TestAuthServiceInit:
    """Tests for AuthService initialization."""

    def test_init_with_jwt_secret(self, mock_supabase_client):
        """Should enable signature verification when JWT secret is set."""
        from src.services.auth_service import AuthService, _auth_client_cache

        _auth_client_cache.clear()

        with patch('src.services.auth_service.get_cached_auth_client', return_value=mock_supabase_client):
            with patch.dict('os.environ', {'SUPABASE_JWT_SECRET': 'test-secret'}):
                service = AuthService("https://test.supabase.co", "key")

                assert service.verify_jwt_signature is True
                assert service.jwt_secret == 'test-secret'

    def test_init_without_jwt_secret_in_dev(self, mock_supabase_client):
        """Should disable signature verification in dev without JWT secret."""
        from src.services.auth_service import AuthService, _auth_client_cache

        _auth_client_cache.clear()

        with patch('src.services.auth_service.get_cached_auth_client', return_value=mock_supabase_client):
            with patch.dict('os.environ', {'ENVIRONMENT': 'development'}, clear=True):
                service = AuthService("https://test.supabase.co", "key")

                assert service.verify_jwt_signature is False

    def test_init_without_jwt_secret_in_prod_raises(self, mock_supabase_client):
        """Should raise error in production without JWT secret."""
        from src.services.auth_service import AuthService, _auth_client_cache

        _auth_client_cache.clear()

        with patch('src.services.auth_service.get_cached_auth_client', return_value=mock_supabase_client):
            with patch.dict('os.environ', {'ENVIRONMENT': 'production'}, clear=True):
                with pytest.raises(RuntimeError, match="SUPABASE_JWT_SECRET is required"):
                    AuthService("https://test.supabase.co", "key")


# ==================== Client Caching Tests ====================

class TestClientCaching:
    """Tests for Supabase client caching."""

    def test_get_cached_auth_client_returns_same_instance(self):
        """get_cached_auth_client should return cached instance."""
        from src.services.auth_service import get_cached_auth_client, _auth_client_cache

        _auth_client_cache.clear()

        with patch('src.services.auth_service.create_client') as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            client1 = get_cached_auth_client("https://test.supabase.co", "key123")
            client2 = get_cached_auth_client("https://test.supabase.co", "key123")

            assert client1 is client2
            mock_create.assert_called_once()

    def test_get_fresh_admin_client_creates_new_instance(self):
        """get_fresh_admin_client should create new instance each time."""
        from src.services.auth_service import get_fresh_admin_client

        with patch('src.services.auth_service.create_client') as mock_create:
            mock_client1 = MagicMock()
            mock_client2 = MagicMock()
            mock_create.side_effect = [mock_client1, mock_client2]

            client1 = get_fresh_admin_client("https://test.supabase.co", "key")
            client2 = get_fresh_admin_client("https://test.supabase.co", "key")

            assert client1 is not client2
            assert mock_create.call_count == 2


# ==================== JWT Verification Tests ====================

class TestJWTVerification:
    """Tests for JWT token verification."""

    def test_verify_valid_jwt(self, auth_service):
        """Should verify valid JWT (without signature verification)."""
        import time

        # Test with signature verification disabled for simplicity
        auth_service.verify_jwt_signature = False

        # Use time.time() for accurate expiration (not datetime.utcnow().timestamp())
        exp_time = int(time.time()) + 3600  # 1 hour from now
        payload = {
            "sub": "user-123",
            "exp": exp_time,
            "iss": "https://test.supabase.co/auth/v1"
        }
        token = jwt.encode(payload, "any-secret", algorithm="HS256")

        valid, result = auth_service.verify_jwt(token)

        assert valid is True
        assert result["sub"] == "user-123"

    def test_verify_expired_jwt(self, auth_service):
        """Should reject expired JWT."""
        import time

        payload = {
            "sub": "user-123",
            "exp": int(time.time()) - 3600,  # 1 hour ago
            "iss": "https://test.supabase.co/auth/v1",
            "aud": "authenticated"
        }
        token = jwt.encode(payload, "test-secret", algorithm="HS256")

        valid, result = auth_service.verify_jwt(token)

        assert valid is False
        assert "expired" in result["error"].lower()

    def test_verify_jwt_missing_subject(self, auth_service):
        """Should reject JWT without subject claim."""
        import time

        # Disable signature verification for this test
        auth_service.verify_jwt_signature = False

        exp_time = int(time.time()) + 3600  # 1 hour from now
        payload = {
            "exp": exp_time,
            "iss": "https://test.supabase.co/auth/v1"
        }
        token = jwt.encode(payload, "any-secret", algorithm="HS256")

        valid, result = auth_service.verify_jwt(token)

        assert valid is False
        assert "missing subject" in result["error"].lower()

    def test_verify_jwt_missing_expiration(self, auth_service):
        """Should reject JWT without expiration claim."""
        # Disable signature verification for this test
        auth_service.verify_jwt_signature = False

        payload = {
            "sub": "user-123",
            "iss": "https://test.supabase.co/auth/v1"
        }
        # Create token without exp
        token = jwt.encode(payload, "any-secret", algorithm="HS256")

        # jwt.decode will fail during decode because verify_exp is True
        # and exp claim is missing - this is caught as an invalid token
        valid, result = auth_service.verify_jwt(token)

        assert valid is False
        # jwt raises InvalidClaimError for missing exp, which we catch as invalid token
        assert "error" in result

    def test_verify_jwt_invalid_signature(self, auth_service):
        """Should reject JWT with invalid signature."""
        import time

        payload = {
            "sub": "user-123",
            "exp": int(time.time()) + 3600,  # 1 hour from now
            "iss": "https://test.supabase.co/auth/v1",
            "aud": "authenticated"
        }
        # Sign with different key
        token = jwt.encode(payload, "wrong-secret", algorithm="HS256")

        valid, result = auth_service.verify_jwt(token)

        assert valid is False
        assert "signature" in result["error"].lower()


# ==================== Login Tests ====================

class TestLogin:
    """Tests for login functionality."""

    @pytest.mark.asyncio
    async def test_login_success(self, auth_service, mock_supabase_client):
        """Should login successfully with valid credentials."""
        # Mock auth response
        mock_user = MagicMock()
        mock_user.id = "auth-user-123"
        mock_session = MagicMock()
        mock_session.access_token = "access-token"
        mock_session.refresh_token = "refresh-token"
        mock_session.expires_at = 3600

        mock_auth_response = MagicMock()
        mock_auth_response.user = mock_user
        mock_auth_response.session = mock_session

        mock_supabase_client.auth.sign_in_with_password.return_value = mock_auth_response

        # Mock org user lookup
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq1 = MagicMock()
        mock_eq2 = MagicMock()
        mock_eq3 = MagicMock()
        mock_single = MagicMock()
        mock_result = MagicMock()
        mock_result.data = {
            "id": "org-user-1",
            "email": "test@example.com",
            "name": "Test User",
            "role": "admin",
            "tenant_id": "tenant-1",
            "is_active": True
        }

        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.eq.return_value = mock_eq3
        mock_eq3.single.return_value = mock_single
        mock_single.execute.return_value = mock_result

        # Mock update
        mock_update = MagicMock()
        mock_update.eq.return_value.execute.return_value = MagicMock()
        mock_table.update.return_value = mock_update

        success, data = await auth_service.login("test@example.com", "password", "tenant-1")

        assert success is True
        assert "access_token" in data
        assert "user" in data

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, auth_service, mock_supabase_client):
        """Should fail with invalid credentials."""
        mock_auth_response = MagicMock()
        mock_auth_response.user = None
        mock_supabase_client.auth.sign_in_with_password.return_value = mock_auth_response

        success, data = await auth_service.login("test@example.com", "wrong-password")

        assert success is False
        assert "error" in data


# ==================== Logout Tests ====================

class TestLogout:
    """Tests for logout functionality."""

    @pytest.mark.asyncio
    async def test_logout_success(self, auth_service, mock_supabase_client):
        """Should logout successfully."""
        mock_supabase_client.auth.sign_out.return_value = None

        result = await auth_service.logout()

        assert result is True
        mock_supabase_client.auth.sign_out.assert_called_once()

    @pytest.mark.asyncio
    async def test_logout_handles_error(self, auth_service, mock_supabase_client):
        """Should handle logout errors gracefully."""
        mock_supabase_client.auth.sign_out.side_effect = Exception("Sign out failed")

        result = await auth_service.logout()

        assert result is False


# ==================== Refresh Token Tests ====================

class TestRefreshToken:
    """Tests for token refresh functionality."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, auth_service, mock_supabase_client):
        """Should refresh token successfully."""
        mock_session = MagicMock()
        mock_session.access_token = "new-access-token"
        mock_session.refresh_token = "new-refresh-token"
        mock_session.expires_at = 7200

        mock_response = MagicMock()
        mock_response.session = mock_session
        mock_supabase_client.auth.refresh_session.return_value = mock_response

        success, data = await auth_service.refresh_token("old-refresh-token")

        assert success is True
        assert data["access_token"] == "new-access-token"

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, auth_service, mock_supabase_client):
        """Should fail with invalid refresh token."""
        mock_response = MagicMock()
        mock_response.session = None
        mock_supabase_client.auth.refresh_session.return_value = mock_response

        success, data = await auth_service.refresh_token("invalid-token")

        assert success is False
        assert "error" in data


# ==================== Password Reset Tests ====================

class TestPasswordReset:
    """Tests for password reset functionality."""

    @pytest.mark.asyncio
    async def test_request_password_reset(self, auth_service, mock_supabase_client):
        """Should send password reset email."""
        mock_supabase_client.auth.reset_password_email.return_value = None

        success, data = await auth_service.request_password_reset("test@example.com")

        assert success is True
        assert "message" in data

    @pytest.mark.asyncio
    async def test_request_password_reset_handles_error(self, auth_service, mock_supabase_client):
        """Should not reveal if email exists on error."""
        mock_supabase_client.auth.reset_password_email.side_effect = Exception("Error")

        success, data = await auth_service.request_password_reset("nonexistent@example.com")

        # Always returns success to not reveal if email exists
        assert success is True


# ==================== User Cache Tests ====================

class TestUserCache:
    """Tests for user caching functionality."""

    def test_user_cache_ttl_constant(self):
        """User cache TTL should be defined."""
        from src.services.auth_service import _USER_CACHE_TTL

        assert _USER_CACHE_TTL == 60  # 60 seconds

    def test_user_cache_is_dict(self):
        """User cache should be a dictionary."""
        from src.services.auth_service import _user_cache

        assert isinstance(_user_cache, dict)
