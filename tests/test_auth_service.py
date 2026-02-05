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


# ==================== Get User by Auth ID Tests ====================

class TestGetUserByAuthId:
    """Tests for get_user_by_auth_id method."""

    @pytest.mark.asyncio
    async def test_get_user_by_auth_id_cache_miss(self, auth_service, mock_supabase_client):
        """Should fetch user from DB on cache miss."""
        from src.services.auth_service import _user_cache

        # Clear cache
        _user_cache.clear()

        mock_user_data = {
            "id": "org-user-1",
            "auth_user_id": "auth-123",
            "tenant_id": "tenant-1",
            "email": "test@example.com",
            "name": "Test User",
            "role": "admin",
            "is_active": True
        }

        # Setup mock chain
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq1 = MagicMock()
        mock_eq2 = MagicMock()
        mock_eq3 = MagicMock()
        mock_single = MagicMock()
        mock_result = MagicMock()
        mock_result.data = mock_user_data

        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.eq.return_value = mock_eq3
        mock_eq3.single.return_value = mock_single
        mock_single.execute.return_value = mock_result

        user = await auth_service.get_user_by_auth_id("auth-123", "tenant-1")

        assert user is not None
        assert user["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_user_by_auth_id_cache_hit(self, auth_service, mock_supabase_client):
        """Should return cached user on cache hit."""
        from src.services.auth_service import _user_cache
        from datetime import datetime

        # Set up cache with valid entry
        cache_key = "tenant-1:auth-123"
        cached_user = {
            "id": "org-user-1",
            "email": "cached@example.com"
        }
        _user_cache[cache_key] = {
            "user": cached_user,
            "expires": datetime.utcnow().timestamp() + 3600  # Future expiry
        }

        user = await auth_service.get_user_by_auth_id("auth-123", "tenant-1")

        # Should return cached user without calling DB
        assert user["email"] == "cached@example.com"
        mock_supabase_client.table.assert_not_called()

        # Clean up
        _user_cache.clear()

    @pytest.mark.asyncio
    async def test_get_user_by_auth_id_expired_cache(self, auth_service, mock_supabase_client):
        """Should refetch user when cache is expired."""
        from src.services.auth_service import _user_cache
        from datetime import datetime

        # Set up expired cache entry
        cache_key = "tenant-1:auth-456"
        _user_cache[cache_key] = {
            "user": {"email": "old@example.com"},
            "expires": datetime.utcnow().timestamp() - 100  # Past expiry
        }

        # Setup mock for fresh fetch
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq1 = MagicMock()
        mock_eq2 = MagicMock()
        mock_eq3 = MagicMock()
        mock_single = MagicMock()
        mock_result = MagicMock()
        mock_result.data = {"email": "fresh@example.com"}

        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.eq.return_value = mock_eq3
        mock_eq3.single.return_value = mock_single
        mock_single.execute.return_value = mock_result

        user = await auth_service.get_user_by_auth_id("auth-456", "tenant-1")

        # Should return fresh data
        assert user["email"] == "fresh@example.com"

        # Clean up
        _user_cache.clear()

    @pytest.mark.asyncio
    async def test_get_user_by_auth_id_not_found(self, auth_service, mock_supabase_client):
        """Should return None when user not found."""
        from src.services.auth_service import _user_cache

        _user_cache.clear()

        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq1 = MagicMock()
        mock_eq2 = MagicMock()
        mock_eq3 = MagicMock()
        mock_single = MagicMock()
        mock_result = MagicMock()
        mock_result.data = None

        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.eq.return_value = mock_eq3
        mock_eq3.single.return_value = mock_single
        mock_single.execute.return_value = mock_result

        user = await auth_service.get_user_by_auth_id("nonexistent", "tenant-1")

        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_auth_id_db_error(self, auth_service, mock_supabase_client):
        """Should return None on database error."""
        from src.services.auth_service import _user_cache

        _user_cache.clear()

        mock_supabase_client.table.side_effect = Exception("Database error")

        user = await auth_service.get_user_by_auth_id("auth-123", "tenant-1")

        assert user is None


# ==================== Create Auth User Tests ====================

class TestCreateAuthUser:
    """Tests for create_auth_user method."""

    @pytest.mark.asyncio
    async def test_create_auth_user_new_user_success(self, auth_service):
        """Should create new user successfully."""
        from src.services.auth_service import get_fresh_admin_client

        with patch('src.services.auth_service.get_fresh_admin_client') as mock_get_admin:
            mock_admin_client = MagicMock()
            mock_get_admin.return_value = mock_admin_client

            # Mock successful auth user creation
            mock_auth_user = MagicMock()
            mock_auth_user.id = "new-auth-123"
            mock_admin_client.auth.admin.create_user.return_value = MagicMock(user=mock_auth_user)

            # Mock checking existing org user (not found)
            mock_existing_result = MagicMock()
            mock_existing_result.data = []
            mock_admin_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_existing_result

            # Mock creating org user
            mock_org_user = {
                "id": "org-user-new",
                "auth_user_id": "new-auth-123",
                "email": "new@example.com",
                "name": "New User",
                "role": "consultant",
                "tenant_id": "tenant-1"
            }
            mock_insert_result = MagicMock()
            mock_insert_result.data = [mock_org_user]
            mock_admin_client.table.return_value.insert.return_value.execute.return_value = mock_insert_result

            success, data = await auth_service.create_auth_user(
                email="new@example.com",
                password="password123",
                name="New User",
                tenant_id="tenant-1"
            )

            assert success is True
            assert "user" in data
            assert data["auth_user_id"] == "new-auth-123"

    @pytest.mark.asyncio
    async def test_create_auth_user_existing_in_tenant(self, auth_service):
        """Should return existing user if already in tenant."""
        with patch('src.services.auth_service.get_fresh_admin_client') as mock_get_admin:
            mock_admin_client = MagicMock()
            mock_get_admin.return_value = mock_admin_client

            # Mock auth user creation
            mock_auth_user = MagicMock()
            mock_auth_user.id = "existing-auth-123"
            mock_admin_client.auth.admin.create_user.return_value = MagicMock(user=mock_auth_user)

            # Mock existing org user found
            mock_existing_user = {
                "id": "org-user-existing",
                "auth_user_id": "existing-auth-123",
                "email": "existing@example.com"
            }
            mock_existing_result = MagicMock()
            mock_existing_result.data = [mock_existing_user]
            mock_admin_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_existing_result

            success, data = await auth_service.create_auth_user(
                email="existing@example.com",
                password="password123",
                name="Existing User",
                tenant_id="tenant-1"
            )

            assert success is True
            assert data.get("already_existed") is True

    @pytest.mark.asyncio
    async def test_create_auth_user_failed(self, auth_service):
        """Should handle auth user creation failure."""
        with patch('src.services.auth_service.get_fresh_admin_client') as mock_get_admin:
            mock_admin_client = MagicMock()
            mock_get_admin.return_value = mock_admin_client

            # Mock auth user creation failure
            mock_admin_client.auth.admin.create_user.return_value = MagicMock(user=None)

            # Mock sign-in also failing
            auth_service.client.auth.sign_in_with_password.side_effect = Exception("Wrong password")

            success, data = await auth_service.create_auth_user(
                email="test@example.com",
                password="password123",
                name="Test User",
                tenant_id="tenant-1"
            )

            assert success is False
            assert "error" in data


# ==================== Update Password Tests ====================

class TestUpdatePassword:
    """Tests for update_password method."""

    @pytest.mark.asyncio
    async def test_update_password_success(self, auth_service, mock_supabase_client):
        """Should update password successfully."""
        mock_supabase_client.auth.set_session.return_value = None
        mock_supabase_client.auth.update_user.return_value = MagicMock()

        success, data = await auth_service.update_password("valid-token", "new-password")

        assert success is True
        assert "message" in data
        assert "updated" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_update_password_auth_error(self, auth_service, mock_supabase_client):
        """Should handle auth API error."""
        from gotrue.errors import AuthApiError

        mock_supabase_client.auth.set_session.return_value = None
        mock_supabase_client.auth.update_user.side_effect = AuthApiError("Invalid token", 401, "bad_jwt")

        success, data = await auth_service.update_password("invalid-token", "new-password")

        assert success is False
        assert "error" in data

    @pytest.mark.asyncio
    async def test_update_password_generic_error(self, auth_service, mock_supabase_client):
        """Should handle generic error."""
        mock_supabase_client.auth.set_session.side_effect = Exception("Connection error")

        success, data = await auth_service.update_password("token", "new-password")

        assert success is False
        assert "error" in data


# ==================== Login Edge Cases Tests ====================

class TestLoginEdgeCases:
    """Additional edge case tests for login."""

    @pytest.mark.asyncio
    async def test_login_tenant_agnostic(self, auth_service, mock_supabase_client):
        """Should login without tenant_id (tenant-agnostic)."""
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

        # Mock org user lookup with limit() for tenant-agnostic login
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq1 = MagicMock()
        mock_eq2 = MagicMock()
        mock_limit = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{
            "id": "org-user-1",
            "email": "test@example.com",
            "name": "Test User",
            "role": "admin",
            "tenant_id": "auto-detected-tenant",
            "is_active": True
        }]

        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.limit.return_value = mock_limit
        mock_limit.execute.return_value = mock_result

        # Mock update
        mock_update = MagicMock()
        mock_update.eq.return_value.execute.return_value = MagicMock()
        mock_table.update.return_value = mock_update

        # Login without tenant_id
        success, data = await auth_service.login("test@example.com", "password")

        assert success is True
        assert data["user"]["tenant_id"] == "auto-detected-tenant"

    @pytest.mark.asyncio
    async def test_login_user_not_in_organization(self, auth_service, mock_supabase_client):
        """Should fail when user exists in auth but not in any organization."""
        # Mock successful auth
        mock_user = MagicMock()
        mock_user.id = "auth-user-123"
        mock_auth_response = MagicMock()
        mock_auth_response.user = mock_user
        mock_supabase_client.auth.sign_in_with_password.return_value = mock_auth_response

        # Mock org user lookup returning empty
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq1 = MagicMock()
        mock_eq2 = MagicMock()
        mock_limit = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []  # No org membership

        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.limit.return_value = mock_limit
        mock_limit.execute.return_value = mock_result

        success, data = await auth_service.login("test@example.com", "password")

        assert success is False
        assert "not found" in data["error"].lower()


# ==================== JWT Edge Cases Tests ====================

class TestJWTEdgeCases:
    """Additional edge case tests for JWT verification."""

    def test_verify_jwt_wrong_issuer(self, auth_service):
        """Should reject JWT with wrong issuer when signature verification enabled."""
        import time

        payload = {
            "sub": "user-123",
            "exp": int(time.time()) + 3600,
            "iss": "https://wrong.supabase.co/auth/v1",  # Wrong issuer
            "aud": "authenticated"
        }
        token = jwt.encode(payload, "test-secret", algorithm="HS256")

        valid, result = auth_service.verify_jwt(token)

        assert valid is False
        assert "issuer" in result["error"].lower()

    def test_verify_jwt_malformed_token(self, auth_service):
        """Should reject malformed JWT."""
        valid, result = auth_service.verify_jwt("not.a.valid.jwt")

        assert valid is False
        assert "error" in result

    def test_verify_jwt_empty_token(self, auth_service):
        """Should reject empty token."""
        valid, result = auth_service.verify_jwt("")

        assert valid is False
        assert "error" in result


# ==================== Token Refresh Edge Cases ====================

class TestRefreshTokenEdgeCases:
    """Additional edge case tests for token refresh."""

    @pytest.mark.asyncio
    async def test_refresh_token_exception(self, auth_service, mock_supabase_client):
        """Should handle exception during refresh."""
        mock_supabase_client.auth.refresh_session.side_effect = Exception("Network error")

        success, data = await auth_service.refresh_token("token")

        assert success is False
        assert "error" in data


# ==================== NEW TESTS: AuthService Initialization ====================

class TestAuthServiceInitExtended:
    """Extended initialization tests for AuthService."""

    def test_init_stores_supabase_url(self, mock_supabase_client):
        """Should store the Supabase URL for issuer validation."""
        from src.services.auth_service import AuthService, _auth_client_cache
        _auth_client_cache.clear()

        with patch('src.services.auth_service.get_cached_auth_client', return_value=mock_supabase_client):
            with patch.dict('os.environ', {'SUPABASE_JWT_SECRET': 'test-secret'}):
                service = AuthService("https://myproject.supabase.co", "my-key")

                assert service.supabase_url == "https://myproject.supabase.co"
                assert service.supabase_key == "my-key"

    def test_init_stores_client_reference(self, mock_supabase_client):
        """Should store the Supabase client from cache."""
        from src.services.auth_service import AuthService, _auth_client_cache
        _auth_client_cache.clear()

        with patch('src.services.auth_service.get_cached_auth_client', return_value=mock_supabase_client):
            with patch.dict('os.environ', {'SUPABASE_JWT_SECRET': 'test-secret'}):
                service = AuthService("https://test.supabase.co", "key")

                assert service.client is mock_supabase_client

    def test_init_prod_environment_variants(self, mock_supabase_client):
        """Should raise RuntimeError for both 'production' and 'prod' environment values."""
        from src.services.auth_service import AuthService, _auth_client_cache

        for env_val in ("production", "prod", "PRODUCTION", "PROD"):
            _auth_client_cache.clear()

            with patch('src.services.auth_service.get_cached_auth_client', return_value=mock_supabase_client):
                with patch.dict('os.environ', {'ENVIRONMENT': env_val}, clear=True):
                    with pytest.raises(RuntimeError):
                        AuthService("https://test.supabase.co", "key")

    def test_init_dev_sets_dummy_secret(self, mock_supabase_client):
        """Should set dummy secret in development when SUPABASE_JWT_SECRET missing."""
        from src.services.auth_service import AuthService, _auth_client_cache
        _auth_client_cache.clear()

        with patch('src.services.auth_service.get_cached_auth_client', return_value=mock_supabase_client):
            with patch.dict('os.environ', {'ENVIRONMENT': 'development'}, clear=True):
                service = AuthService("https://test.supabase.co", "key")

                assert service.jwt_secret == "development-mode-no-verification"
                assert service.verify_jwt_signature is False


# ==================== NEW TESTS: Login Extended ====================

class TestLoginExtended:
    """Extended login tests covering more edge cases."""

    @pytest.mark.asyncio
    async def test_login_auth_api_error(self, auth_service, mock_supabase_client):
        """Should handle AuthApiError during login and return message."""
        from gotrue.errors import AuthApiError

        mock_supabase_client.auth.sign_in_with_password.side_effect = AuthApiError(
            "Invalid login credentials", 400, "invalid_credentials"
        )

        success, data = await auth_service.login("test@example.com", "wrong")

        assert success is False
        assert "error" in data

    @pytest.mark.asyncio
    async def test_login_generic_exception_invalid_credentials_message(self, auth_service, mock_supabase_client):
        """Should return friendly message when generic exception contains 'Invalid login credentials'."""
        mock_supabase_client.auth.sign_in_with_password.side_effect = Exception(
            "Invalid login credentials"
        )

        success, data = await auth_service.login("test@example.com", "bad")

        assert success is False
        assert data["error"] == "Invalid email or password"

    @pytest.mark.asyncio
    async def test_login_generic_exception_unknown_error(self, auth_service, mock_supabase_client):
        """Should propagate unknown error messages."""
        mock_supabase_client.auth.sign_in_with_password.side_effect = Exception(
            "Connection refused"
        )

        success, data = await auth_service.login("test@example.com", "pass")

        assert success is False
        assert "Connection refused" in data["error"]

    @pytest.mark.asyncio
    async def test_login_success_returns_all_user_fields(self, auth_service, mock_supabase_client):
        """Should return all expected user fields on login success."""
        mock_user = MagicMock()
        mock_user.id = "auth-user-999"
        mock_session = MagicMock()
        mock_session.access_token = "at-123"
        mock_session.refresh_token = "rt-123"
        mock_session.expires_at = 9999

        mock_auth_response = MagicMock()
        mock_auth_response.user = mock_user
        mock_auth_response.session = mock_session
        mock_supabase_client.auth.sign_in_with_password.return_value = mock_auth_response

        org_user = {
            "id": "ou-1",
            "email": "admin@company.com",
            "name": "Admin User",
            "role": "admin",
            "tenant_id": "tenant-abc",
            "is_active": True
        }

        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq1 = MagicMock()
        mock_eq2 = MagicMock()
        mock_eq3 = MagicMock()
        mock_single = MagicMock()
        mock_result = MagicMock()
        mock_result.data = org_user

        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.eq.return_value = mock_eq3
        mock_eq3.single.return_value = mock_single
        mock_single.execute.return_value = mock_result

        mock_update = MagicMock()
        mock_update.eq.return_value.execute.return_value = MagicMock()
        mock_table.update.return_value = mock_update

        success, data = await auth_service.login("admin@company.com", "pass123", "tenant-abc")

        assert success is True
        assert data["access_token"] == "at-123"
        assert data["refresh_token"] == "rt-123"
        assert data["expires_at"] == 9999
        user = data["user"]
        assert user["id"] == "ou-1"
        assert user["auth_user_id"] == "auth-user-999"
        assert user["email"] == "admin@company.com"
        assert user["name"] == "Admin User"
        assert user["role"] == "admin"
        assert user["tenant_id"] == "tenant-abc"
        assert user["is_active"] is True

    @pytest.mark.asyncio
    async def test_login_empty_error_message(self, auth_service, mock_supabase_client):
        """Should return fallback message when exception has empty string."""
        mock_supabase_client.auth.sign_in_with_password.side_effect = Exception("")

        success, data = await auth_service.login("test@test.com", "pass")

        assert success is False
        assert data["error"] == "An error occurred during login"


# ==================== NEW TESTS: JWT Verification Extended ====================

class TestJWTVerificationExtended:
    """Extended JWT verification tests."""

    def test_verify_jwt_valid_with_signature_verification(self, auth_service):
        """Should verify JWT with valid signature when verification is enabled."""
        import time

        payload = {
            "sub": "user-abc",
            "exp": int(time.time()) + 3600,
            "iss": "https://test.supabase.co/auth/v1",
            "aud": "authenticated"
        }
        token = jwt.encode(payload, "test-secret", algorithm="HS256")

        valid, result = auth_service.verify_jwt(token)

        assert valid is True
        assert result["sub"] == "user-abc"

    def test_verify_jwt_correct_issuer_required_with_sig_verification(self, auth_service):
        """Should require matching issuer when signature verification is on."""
        import time

        payload = {
            "sub": "user-1",
            "exp": int(time.time()) + 3600,
            "iss": "https://OTHER.supabase.co/auth/v1",
            "aud": "authenticated"
        }
        token = jwt.encode(payload, "test-secret", algorithm="HS256")

        valid, result = auth_service.verify_jwt(token)

        assert valid is False
        assert "issuer" in result["error"].lower()

    def test_verify_jwt_issuer_not_checked_without_sig_verification(self, auth_service):
        """Should skip issuer check when signature verification is disabled."""
        import time

        auth_service.verify_jwt_signature = False

        payload = {
            "sub": "user-1",
            "exp": int(time.time()) + 3600,
            "iss": "https://ANY.supabase.co/auth/v1"
        }
        token = jwt.encode(payload, "any-key", algorithm="HS256")

        valid, result = auth_service.verify_jwt(token)

        assert valid is True

    def test_verify_jwt_completely_garbage_token(self, auth_service):
        """Should reject completely non-JWT strings."""
        valid, result = auth_service.verify_jwt("this-is-not-a-jwt-at-all")

        assert valid is False
        assert "error" in result

    def test_verify_jwt_audience_mismatch(self, auth_service):
        """Should reject JWT with wrong audience when verification is enabled."""
        import time

        payload = {
            "sub": "user-123",
            "exp": int(time.time()) + 3600,
            "iss": "https://test.supabase.co/auth/v1",
            "aud": "wrong-audience"
        }
        token = jwt.encode(payload, "test-secret", algorithm="HS256")

        valid, result = auth_service.verify_jwt(token)

        assert valid is False
        assert "error" in result

    def test_verify_jwt_returns_full_payload(self, auth_service):
        """Should return the full decoded payload on success."""
        import time

        auth_service.verify_jwt_signature = False

        custom_data = {
            "sub": "user-full",
            "exp": int(time.time()) + 3600,
            "iss": "https://test.supabase.co/auth/v1",
            "role": "authenticated",
            "email": "user@test.com"
        }
        token = jwt.encode(custom_data, "any-key", algorithm="HS256")

        valid, result = auth_service.verify_jwt(token)

        assert valid is True
        assert result["sub"] == "user-full"
        assert result["email"] == "user@test.com"
        assert result["role"] == "authenticated"


# ==================== NEW TESTS: Refresh Token Extended ====================

class TestRefreshTokenExtended:
    """Extended refresh token tests."""

    @pytest.mark.asyncio
    async def test_refresh_token_auth_api_error(self, auth_service, mock_supabase_client):
        """Should handle AuthApiError during refresh."""
        from gotrue.errors import AuthApiError

        mock_supabase_client.auth.refresh_session.side_effect = AuthApiError(
            "Refresh token expired", 401, "bad_jwt"
        )

        success, data = await auth_service.refresh_token("expired-refresh-token")

        assert success is False
        assert data["error"] == "Failed to refresh token"

    @pytest.mark.asyncio
    async def test_refresh_token_returns_new_tokens(self, auth_service, mock_supabase_client):
        """Should return all three token fields on success."""
        mock_session = MagicMock()
        mock_session.access_token = "new-at"
        mock_session.refresh_token = "new-rt"
        mock_session.expires_at = 12345

        mock_response = MagicMock()
        mock_response.session = mock_session
        mock_supabase_client.auth.refresh_session.return_value = mock_response

        success, data = await auth_service.refresh_token("old-rt")

        assert success is True
        assert data["access_token"] == "new-at"
        assert data["refresh_token"] == "new-rt"
        assert data["expires_at"] == 12345


# ==================== NEW TESTS: Password Reset Extended ====================

class TestPasswordResetExtended:
    """Extended password reset tests."""

    @pytest.mark.asyncio
    async def test_request_password_reset_always_returns_success(self, auth_service, mock_supabase_client):
        """Should always return success for security (no email enumeration)."""
        # Even on error, it returns success
        mock_supabase_client.auth.reset_password_email.side_effect = Exception("SMTP error")

        success, data = await auth_service.request_password_reset("any@email.com")

        assert success is True
        # Message should be vague about account existence
        assert "if an account exists" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_request_password_reset_success_message(self, auth_service, mock_supabase_client):
        """Should return direct success message on successful send."""
        mock_supabase_client.auth.reset_password_email.return_value = None

        success, data = await auth_service.request_password_reset("valid@example.com")

        assert success is True
        assert "password reset" in data["message"].lower()


# ==================== NEW TESTS: Update Password Extended ====================

class TestUpdatePasswordExtended:
    """Extended update password tests."""

    @pytest.mark.asyncio
    async def test_update_password_calls_set_session(self, auth_service, mock_supabase_client):
        """Should set session with access token before updating password."""
        mock_supabase_client.auth.set_session.return_value = None
        mock_supabase_client.auth.update_user.return_value = MagicMock()

        await auth_service.update_password("my-access-token", "new-password-123")

        mock_supabase_client.auth.set_session.assert_called_once_with("my-access-token", "")

    @pytest.mark.asyncio
    async def test_update_password_passes_new_password(self, auth_service, mock_supabase_client):
        """Should pass new password to update_user call."""
        mock_supabase_client.auth.set_session.return_value = None
        mock_supabase_client.auth.update_user.return_value = MagicMock()

        await auth_service.update_password("token", "super-secure-pw")

        mock_supabase_client.auth.update_user.assert_called_once_with({"password": "super-secure-pw"})


# ==================== NEW TESTS: Get User by Auth ID Extended ====================

class TestGetUserByAuthIdExtended:
    """Extended get_user_by_auth_id tests."""

    @pytest.mark.asyncio
    async def test_get_user_by_auth_id_caches_result(self, auth_service, mock_supabase_client):
        """Should cache the fetched user for subsequent calls."""
        from src.services.auth_service import _user_cache
        _user_cache.clear()

        mock_user_data = {
            "id": "org-1",
            "auth_user_id": "auth-cache-test",
            "tenant_id": "t-1",
            "email": "cache@test.com",
            "is_active": True
        }

        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq1 = MagicMock()
        mock_eq2 = MagicMock()
        mock_eq3 = MagicMock()
        mock_single = MagicMock()
        mock_result = MagicMock()
        mock_result.data = mock_user_data

        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.eq.return_value = mock_eq3
        mock_eq3.single.return_value = mock_single
        mock_single.execute.return_value = mock_result

        # First call - fetches from DB
        user1 = await auth_service.get_user_by_auth_id("auth-cache-test", "t-1")
        assert user1["email"] == "cache@test.com"

        # Verify it's in the cache now
        cache_key = "t-1:auth-cache-test"
        assert cache_key in _user_cache
        assert _user_cache[cache_key]["user"]["email"] == "cache@test.com"

        _user_cache.clear()

    @pytest.mark.asyncio
    async def test_get_user_by_auth_id_none_result_not_cached(self, auth_service, mock_supabase_client):
        """Should not cache when user data is None."""
        from src.services.auth_service import _user_cache
        _user_cache.clear()

        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq1 = MagicMock()
        mock_eq2 = MagicMock()
        mock_eq3 = MagicMock()
        mock_single = MagicMock()
        mock_result = MagicMock()
        mock_result.data = None

        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.eq.return_value = mock_eq3
        mock_eq3.single.return_value = mock_single
        mock_single.execute.return_value = mock_result

        user = await auth_service.get_user_by_auth_id("nonexistent", "t-1")
        assert user is None

        cache_key = "t-1:nonexistent"
        assert cache_key not in _user_cache

        _user_cache.clear()


# ==================== NEW TESTS: Create Auth User Extended ====================

class TestCreateAuthUserExtended:
    """Extended create_auth_user tests."""

    @pytest.mark.asyncio
    async def test_create_auth_user_existing_user_different_password(self, auth_service):
        """Should return error when email exists with different password."""
        from gotrue.errors import AuthApiError

        with patch('src.services.auth_service.get_fresh_admin_client') as mock_get_admin:
            mock_admin_client = MagicMock()
            mock_get_admin.return_value = mock_admin_client

            # Auth creation fails (user exists)
            mock_admin_client.auth.admin.create_user.side_effect = AuthApiError(
                "User already registered", 422, "user_already_exists"
            )

            # Sign in with provided password also fails (wrong password)
            auth_service.client.auth.sign_in_with_password.side_effect = Exception(
                "Invalid login credentials"
            )

            success, data = await auth_service.create_auth_user(
                email="existing@example.com",
                password="wrong-password",
                name="Test",
                tenant_id="tenant-1"
            )

            assert success is False
            assert "already registered" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_create_auth_user_org_insert_failure(self, auth_service):
        """Should return error when organization user insert fails."""
        with patch('src.services.auth_service.get_fresh_admin_client') as mock_get_admin:
            mock_admin_client = MagicMock()
            mock_get_admin.return_value = mock_admin_client

            # Auth user creation succeeds
            mock_auth_user = MagicMock()
            mock_auth_user.id = "new-auth-456"
            mock_admin_client.auth.admin.create_user.return_value = MagicMock(user=mock_auth_user)

            # No existing org user
            mock_existing_result = MagicMock()
            mock_existing_result.data = []
            mock_admin_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_existing_result

            # Org user insert returns no data
            mock_insert_result = MagicMock()
            mock_insert_result.data = None
            mock_admin_client.table.return_value.insert.return_value.execute.return_value = mock_insert_result

            success, data = await auth_service.create_auth_user(
                email="new@test.com",
                password="pw123",
                name="New",
                tenant_id="t-1"
            )

            assert success is False
            assert "failed to create" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_create_auth_user_org_insert_exception(self, auth_service):
        """Should handle exception during organization user insert."""
        with patch('src.services.auth_service.get_fresh_admin_client') as mock_get_admin:
            mock_admin_client = MagicMock()
            mock_get_admin.return_value = mock_admin_client

            # Auth user creation succeeds
            mock_auth_user = MagicMock()
            mock_auth_user.id = "auth-789"
            mock_admin_client.auth.admin.create_user.return_value = MagicMock(user=mock_auth_user)

            # No existing org user
            mock_existing_result = MagicMock()
            mock_existing_result.data = []
            mock_admin_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_existing_result

            # Org user insert throws exception
            mock_admin_client.table.return_value.insert.return_value.execute.side_effect = Exception(
                "Unique constraint violation"
            )

            success, data = await auth_service.create_auth_user(
                email="dup@test.com",
                password="pw",
                name="Dup",
                tenant_id="t-1"
            )

            assert success is False
            assert "error" in data

    @pytest.mark.asyncio
    async def test_create_auth_user_with_role_and_invited_by(self, auth_service):
        """Should pass role and invited_by to org user record."""
        with patch('src.services.auth_service.get_fresh_admin_client') as mock_get_admin:
            mock_admin_client = MagicMock()
            mock_get_admin.return_value = mock_admin_client

            mock_auth_user = MagicMock()
            mock_auth_user.id = "auth-role-test"
            mock_admin_client.auth.admin.create_user.return_value = MagicMock(user=mock_auth_user)

            mock_existing_result = MagicMock()
            mock_existing_result.data = []
            mock_admin_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_existing_result

            mock_org_user = {
                "id": "ou-role",
                "auth_user_id": "auth-role-test",
                "email": "admin@test.com",
                "name": "Admin",
                "role": "admin",
                "tenant_id": "t-1"
            }
            mock_insert_result = MagicMock()
            mock_insert_result.data = [mock_org_user]
            mock_admin_client.table.return_value.insert.return_value.execute.return_value = mock_insert_result

            success, data = await auth_service.create_auth_user(
                email="admin@test.com",
                password="pw",
                name="Admin",
                tenant_id="t-1",
                role="admin",
                invited_by="inviter-id-123"
            )

            assert success is True
            # Verify the insert was called with role and invited_by
            insert_call = mock_admin_client.table.return_value.insert.call_args[0][0]
            assert insert_call["role"] == "admin"
            assert insert_call["invited_by"] == "inviter-id-123"

    @pytest.mark.asyncio
    async def test_create_auth_user_no_auth_user_id(self, auth_service):
        """Should return error when auth user creation returns None user."""
        with patch('src.services.auth_service.get_fresh_admin_client') as mock_get_admin:
            mock_admin_client = MagicMock()
            mock_get_admin.return_value = mock_admin_client

            # Auth creation returns user=None
            mock_admin_client.auth.admin.create_user.return_value = MagicMock(user=None)

            # Sign-in attempt also fails
            auth_service.client.auth.sign_in_with_password.side_effect = Exception("Fail")

            success, data = await auth_service.create_auth_user(
                email="nobody@test.com",
                password="pw",
                name="Nobody",
                tenant_id="t-1"
            )

            assert success is False
            assert "error" in data


# ==================== NEW TESTS: Client Caching Extended ====================

class TestClientCachingExtended:
    """Extended client caching tests."""

    def test_different_keys_get_different_clients(self):
        """Should cache separately for different API keys."""
        from src.services.auth_service import get_cached_auth_client, _auth_client_cache
        _auth_client_cache.clear()

        with patch('src.services.auth_service.create_client') as mock_create:
            mock_client_a = MagicMock()
            mock_client_b = MagicMock()
            mock_create.side_effect = [mock_client_a, mock_client_b]

            client_a = get_cached_auth_client("https://test.supabase.co", "anon-key-12345")
            client_b = get_cached_auth_client("https://test.supabase.co", "service-key-999")

            assert client_a is not client_b
            assert mock_create.call_count == 2

        _auth_client_cache.clear()

    def test_cache_key_uses_url_prefix_and_key_suffix(self):
        """Should use URL prefix and key suffix as cache key."""
        from src.services.auth_service import get_cached_auth_client, _auth_client_cache
        _auth_client_cache.clear()

        with patch('src.services.auth_service.create_client') as mock_create:
            mock_create.return_value = MagicMock()

            get_cached_auth_client("https://test.supabase.co", "key-abcdefghij")

            # Cache key format: first 30 chars of URL + ":" + last 10 chars of key
            expected_key = "https://test.supabase.co:abcdefghij"
            assert expected_key in _auth_client_cache

        _auth_client_cache.clear()

    def test_cache_handles_empty_key(self):
        """Should handle empty key string without crashing."""
        from src.services.auth_service import get_cached_auth_client, _auth_client_cache
        _auth_client_cache.clear()

        with patch('src.services.auth_service.create_client') as mock_create:
            mock_create.return_value = MagicMock()

            # Should not raise even with empty key
            client = get_cached_auth_client("https://test.supabase.co", "")

            assert client is not None

        _auth_client_cache.clear()
