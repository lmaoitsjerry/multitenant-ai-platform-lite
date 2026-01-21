"""
Unit Tests for Auth Middleware

Tests for the AuthMiddleware class, specifically:
1. X-Client-ID header validation against JWT user's tenant
2. Tenant spoofing rejection (header != user's tenant)
3. Normal flow when header matches or is absent
4. Public path bypass
5. Missing/invalid auth handling

These tests verify SEC-02 security fix for tenant isolation.
Implements tests for Plan 09-01 tenant spoofing prevention.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class MockUser:
    """Mock user from database"""
    def __init__(self, tenant_id='tenant_a', user_id='user_123', is_active=True, role='admin'):
        self.data = {
            'id': user_id,
            'email': f'{user_id}@{tenant_id}.com',
            'name': 'Test User',
            'role': role,
            'tenant_id': tenant_id,
            'is_active': is_active
        }

    def to_dict(self):
        return self.data


class MockConfig:
    """Mock ClientConfig"""
    def __init__(self, tenant_id='tenant_a'):
        self.client_id = tenant_id
        self.supabase_url = 'https://test.supabase.co'
        self.supabase_service_key = 'test-service-key'


def create_mock_scope(path, method='GET', headers=None):
    """Create a mock ASGI scope for testing"""
    header_list = []
    if headers:
        for key, value in headers.items():
            header_list.append((key.lower().encode(), value.encode()))

    return {
        'type': 'http',
        'method': method,
        'path': path,
        'query_string': b'',
        'root_path': '',
        'headers': header_list,
        'server': ('localhost', 8000),
    }


# ==================== Test Public Path Detection ====================

class TestPublicPathDetection:
    """Test the is_public_path function"""

    def test_health_endpoint_is_public(self):
        """Test that /health endpoint is public"""
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/health') == True

    def test_health_ready_is_public(self):
        """Test that /health/ready is public"""
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/health/ready') == True

    def test_docs_is_public(self):
        """Test that /docs is public"""
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/docs') == True

    def test_auth_login_is_public(self):
        """Test that login endpoint is public"""
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/api/v1/auth/login') == True

    def test_admin_routes_are_public(self):
        """
        Test that /api/v1/admin/* routes are public (use X-Admin-Token auth)
        These routes bypass JWT auth and use their own token-based auth.
        """
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/api/v1/admin/tenants') == True
        assert is_public_path('/api/v1/admin/analytics/overview') == True

    def test_protected_routes_are_not_public(self):
        """Test that protected API routes are not public"""
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/api/v1/quotes') == False
        assert is_public_path('/api/v1/invoices') == False
        assert is_public_path('/api/v1/clients') == False


# ==================== Test Tenant Spoofing Rejection ====================

class TestTenantSpoofingRejection:
    """
    Test that tenant spoofing attempts are rejected.

    These are the core SEC-02 security tests. They verify that a user
    cannot access another tenant's data by sending a spoofed X-Client-ID header.
    """

    @pytest.mark.asyncio
    async def test_mismatched_tenant_header_returns_403(self):
        """
        Test: User from tenant_a sends X-Client-ID: tenant_b
        Expected: 403 Forbidden with "tenant mismatch" message

        This is the core SEC-02 security test. A valid user authenticates
        but attempts to access another tenant by spoofing the header.
        """
        from src.middleware.auth_middleware import AuthMiddleware
        from starlette.requests import Request
        from starlette.responses import Response

        # Create middleware with mock app
        middleware = AuthMiddleware(app=MagicMock())

        # Mock the external dependencies
        with patch('src.middleware.auth_middleware.get_config') as mock_get_config, \
             patch('src.middleware.auth_middleware.AuthService') as MockAuthService:

            # Setup config - use tenant_b since that's what header says
            mock_get_config.return_value = MockConfig('tenant_b')

            # Setup auth service
            mock_auth_instance = MagicMock()
            mock_auth_instance.verify_jwt.return_value = (True, {'sub': 'auth_user_123'})
            # User actually belongs to tenant_a
            mock_auth_instance.get_user_by_auth_id = AsyncMock(return_value=MockUser('tenant_a').data)
            MockAuthService.return_value = mock_auth_instance

            # Create request with SPOOFED header
            scope = create_mock_scope(
                '/api/v1/quotes',
                headers={
                    'authorization': 'Bearer valid.jwt.token',
                    'x-client-id': 'tenant_b',  # SPOOFED - user is actually in tenant_a
                }
            )

            # Need to add receive and send for Request
            async def receive():
                return {'type': 'http.request', 'body': b''}

            request = Request(scope, receive)

            async def call_next(req):
                return Response(content='OK', status_code=200)

            response = await middleware.dispatch(request, call_next)

            # Should be 403 Forbidden due to tenant mismatch
            assert response.status_code == 403, f"Expected 403, got {response.status_code}"

            # Verify response body mentions the issue
            body = response.body.decode() if hasattr(response, 'body') else ''
            assert 'tenant' in body.lower() or 'mismatch' in body.lower() or 'denied' in body.lower()

    @pytest.mark.asyncio
    async def test_matching_tenant_header_succeeds(self):
        """
        Test: User from tenant_a sends X-Client-ID: tenant_a
        Expected: Request proceeds normally with 200

        Valid case - user's tenant matches the header.
        """
        from src.middleware.auth_middleware import AuthMiddleware
        from starlette.requests import Request
        from starlette.responses import Response

        middleware = AuthMiddleware(app=MagicMock())

        with patch('src.middleware.auth_middleware.get_config') as mock_get_config, \
             patch('src.middleware.auth_middleware.AuthService') as MockAuthService:

            mock_get_config.return_value = MockConfig('tenant_a')

            mock_auth_instance = MagicMock()
            mock_auth_instance.verify_jwt.return_value = (True, {'sub': 'auth_user_123'})
            # User belongs to tenant_a - MATCHES header
            mock_auth_instance.get_user_by_auth_id = AsyncMock(return_value=MockUser('tenant_a').data)
            MockAuthService.return_value = mock_auth_instance

            scope = create_mock_scope(
                '/api/v1/quotes',
                headers={
                    'authorization': 'Bearer valid.jwt.token',
                    'x-client-id': 'tenant_a',  # Matches user's actual tenant
                }
            )

            async def receive():
                return {'type': 'http.request', 'body': b''}

            request = Request(scope, receive)

            call_next_called = False
            async def call_next(req):
                nonlocal call_next_called
                call_next_called = True
                # Verify user context was set
                assert hasattr(req.state, 'user')
                assert req.state.user.tenant_id == 'tenant_a'
                return Response(content='OK', status_code=200)

            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 200
            assert call_next_called, "call_next should have been called for valid request"

    @pytest.mark.asyncio
    async def test_no_tenant_header_uses_default(self):
        """
        Test: User sends request without X-Client-ID header
        Expected: Uses default tenant (africastay or from ENV), request proceeds

        When no header is provided, the system uses the default tenant.
        """
        from src.middleware.auth_middleware import AuthMiddleware
        from starlette.requests import Request
        from starlette.responses import Response

        middleware = AuthMiddleware(app=MagicMock())

        with patch('src.middleware.auth_middleware.get_config') as mock_get_config, \
             patch('src.middleware.auth_middleware.AuthService') as MockAuthService, \
             patch.dict('os.environ', {'CLIENT_ID': 'africastay'}):

            mock_get_config.return_value = MockConfig('africastay')

            mock_auth_instance = MagicMock()
            mock_auth_instance.verify_jwt.return_value = (True, {'sub': 'auth_user_123'})
            mock_auth_instance.get_user_by_auth_id = AsyncMock(return_value=MockUser('africastay').data)
            MockAuthService.return_value = mock_auth_instance

            scope = create_mock_scope(
                '/api/v1/quotes',
                headers={
                    'authorization': 'Bearer valid.jwt.token',
                    # NO x-client-id header
                }
            )

            async def receive():
                return {'type': 'http.request', 'body': b''}

            request = Request(scope, receive)

            async def call_next(req):
                return Response(content='OK', status_code=200)

            response = await middleware.dispatch(request, call_next)

            # Should succeed since no header means no mismatch validation
            assert response.status_code == 200


# ==================== Test Public Path Bypass ====================

class TestPublicPathBypass:
    """Test that public paths bypass auth"""

    @pytest.mark.asyncio
    async def test_health_endpoint_skips_auth(self):
        """
        Test: Request to /health endpoint without auth
        Expected: Auth middleware skips validation, request proceeds
        """
        from src.middleware.auth_middleware import AuthMiddleware
        from starlette.requests import Request
        from starlette.responses import Response

        middleware = AuthMiddleware(app=MagicMock())

        scope = create_mock_scope('/health', headers={})

        async def receive():
            return {'type': 'http.request', 'body': b''}

        request = Request(scope, receive)

        call_next_called = False
        async def call_next(req):
            nonlocal call_next_called
            call_next_called = True
            # User should be None for public paths
            assert req.state.user is None
            return Response(content='OK', status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200
        assert call_next_called

    @pytest.mark.asyncio
    async def test_options_preflight_skips_auth(self):
        """
        Test: OPTIONS preflight request (CORS)
        Expected: Auth middleware skips validation
        """
        from src.middleware.auth_middleware import AuthMiddleware
        from starlette.requests import Request
        from starlette.responses import Response

        middleware = AuthMiddleware(app=MagicMock())

        scope = create_mock_scope('/api/v1/quotes', method='OPTIONS', headers={})

        async def receive():
            return {'type': 'http.request', 'body': b''}

        request = Request(scope, receive)

        async def call_next(req):
            assert req.state.user is None
            return Response(content='', status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200


# ==================== Test Missing/Invalid Auth ====================

class TestMissingInvalidAuth:
    """Test requests with missing or invalid authentication"""

    @pytest.mark.asyncio
    async def test_missing_auth_header_returns_401(self):
        """
        Test: Protected path without Authorization header
        Expected: 401 Unauthorized
        """
        from src.middleware.auth_middleware import AuthMiddleware
        from starlette.requests import Request
        from starlette.responses import Response

        middleware = AuthMiddleware(app=MagicMock())

        scope = create_mock_scope(
            '/api/v1/quotes',  # Protected path
            headers={
                'x-client-id': 'tenant_a',
                # NO authorization header
            }
        )

        async def receive():
            return {'type': 'http.request', 'body': b''}

        request = Request(scope, receive)

        async def call_next(req):
            return Response(content='OK', status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_bearer_format_returns_401(self):
        """
        Test: Authorization header with invalid format
        Expected: 401 Unauthorized
        """
        from src.middleware.auth_middleware import AuthMiddleware
        from starlette.requests import Request
        from starlette.responses import Response

        middleware = AuthMiddleware(app=MagicMock())

        scope = create_mock_scope(
            '/api/v1/quotes',
            headers={
                'authorization': 'InvalidFormat token123',  # Not "Bearer xxx"
                'x-client-id': 'tenant_a',
            }
        )

        async def receive():
            return {'type': 'http.request', 'body': b''}

        request = Request(scope, receive)

        async def call_next(req):
            return Response(content='OK', status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_jwt_returns_401(self):
        """
        Test: Protected path with invalid/expired JWT
        Expected: 401 Unauthorized
        """
        from src.middleware.auth_middleware import AuthMiddleware
        from starlette.requests import Request
        from starlette.responses import Response

        middleware = AuthMiddleware(app=MagicMock())

        with patch('src.middleware.auth_middleware.get_config') as mock_get_config, \
             patch('src.middleware.auth_middleware.AuthService') as MockAuthService:

            mock_get_config.return_value = MockConfig('tenant_a')

            mock_auth_instance = MagicMock()
            # JWT verification FAILS
            mock_auth_instance.verify_jwt.return_value = (False, {'error': 'Token expired'})
            MockAuthService.return_value = mock_auth_instance

            scope = create_mock_scope(
                '/api/v1/quotes',
                headers={
                    'authorization': 'Bearer expired.jwt.token',
                    'x-client-id': 'tenant_a',
                }
            )

            async def receive():
                return {'type': 'http.request', 'body': b''}

            request = Request(scope, receive)

            async def call_next(req):
                return Response(content='OK', status_code=200)

            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_user_not_found_returns_401(self):
        """
        Test: Valid JWT but user not found in database
        Expected: 401 Unauthorized
        """
        from src.middleware.auth_middleware import AuthMiddleware
        from starlette.requests import Request
        from starlette.responses import Response

        middleware = AuthMiddleware(app=MagicMock())

        with patch('src.middleware.auth_middleware.get_config') as mock_get_config, \
             patch('src.middleware.auth_middleware.AuthService') as MockAuthService:

            mock_get_config.return_value = MockConfig('tenant_a')

            mock_auth_instance = MagicMock()
            mock_auth_instance.verify_jwt.return_value = (True, {'sub': 'auth_user_123'})
            # User NOT FOUND
            mock_auth_instance.get_user_by_auth_id = AsyncMock(return_value=None)
            MockAuthService.return_value = mock_auth_instance

            scope = create_mock_scope(
                '/api/v1/quotes',
                headers={
                    'authorization': 'Bearer valid.jwt.token',
                    'x-client-id': 'tenant_a',
                }
            )

            async def receive():
                return {'type': 'http.request', 'body': b''}

            request = Request(scope, receive)

            async def call_next(req):
                return Response(content='OK', status_code=200)

            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_deactivated_user_returns_401(self):
        """
        Test: Valid JWT but user is deactivated
        Expected: 401 Unauthorized
        """
        from src.middleware.auth_middleware import AuthMiddleware
        from starlette.requests import Request
        from starlette.responses import Response

        middleware = AuthMiddleware(app=MagicMock())

        with patch('src.middleware.auth_middleware.get_config') as mock_get_config, \
             patch('src.middleware.auth_middleware.AuthService') as MockAuthService:

            mock_get_config.return_value = MockConfig('tenant_a')

            mock_auth_instance = MagicMock()
            mock_auth_instance.verify_jwt.return_value = (True, {'sub': 'auth_user_123'})
            # User is DEACTIVATED
            mock_auth_instance.get_user_by_auth_id = AsyncMock(
                return_value=MockUser('tenant_a', is_active=False).data
            )
            MockAuthService.return_value = mock_auth_instance

            scope = create_mock_scope(
                '/api/v1/quotes',
                headers={
                    'authorization': 'Bearer valid.jwt.token',
                    'x-client-id': 'tenant_a',
                }
            )

            async def receive():
                return {'type': 'http.request', 'body': b''}

            request = Request(scope, receive)

            async def call_next(req):
                return Response(content='OK', status_code=200)

            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 401


# ==================== Test UserContext Population ====================

class TestUserContextPopulation:
    """Test that UserContext is correctly populated"""

    @pytest.mark.asyncio
    async def test_user_context_has_correct_fields(self):
        """
        Test: Valid authenticated request
        Expected: UserContext has correct tenant_id, role, email, etc.
        """
        from src.middleware.auth_middleware import AuthMiddleware, UserContext
        from starlette.requests import Request
        from starlette.responses import Response

        middleware = AuthMiddleware(app=MagicMock())

        user_data = {
            'id': 'user_123',
            'email': 'admin@tenant_a.com',
            'name': 'Admin User',
            'role': 'admin',
            'tenant_id': 'tenant_a',
            'is_active': True
        }

        with patch('src.middleware.auth_middleware.get_config') as mock_get_config, \
             patch('src.middleware.auth_middleware.AuthService') as MockAuthService:

            mock_get_config.return_value = MockConfig('tenant_a')

            mock_auth_instance = MagicMock()
            mock_auth_instance.verify_jwt.return_value = (True, {'sub': 'auth_user_123'})
            mock_auth_instance.get_user_by_auth_id = AsyncMock(return_value=user_data)
            MockAuthService.return_value = mock_auth_instance

            scope = create_mock_scope(
                '/api/v1/quotes',
                headers={
                    'authorization': 'Bearer valid.jwt.token',
                    'x-client-id': 'tenant_a',
                }
            )

            async def receive():
                return {'type': 'http.request', 'body': b''}

            request = Request(scope, receive)

            captured_user = None
            async def call_next(req):
                nonlocal captured_user
                captured_user = req.state.user
                return Response(content='OK', status_code=200)

            await middleware.dispatch(request, call_next)

            assert captured_user is not None
            assert isinstance(captured_user, UserContext)
            assert captured_user.tenant_id == 'tenant_a'
            assert captured_user.role == 'admin'
            assert captured_user.email == 'admin@tenant_a.com'
            assert captured_user.name == 'Admin User'
            assert captured_user.user_id == 'user_123'
            assert captured_user.is_admin == True
            assert captured_user.is_active == True

    @pytest.mark.asyncio
    async def test_consultant_user_is_not_admin(self):
        """
        Test: Consultant user authenticated
        Expected: is_admin returns False
        """
        from src.middleware.auth_middleware import AuthMiddleware, UserContext
        from starlette.requests import Request
        from starlette.responses import Response

        middleware = AuthMiddleware(app=MagicMock())

        with patch('src.middleware.auth_middleware.get_config') as mock_get_config, \
             patch('src.middleware.auth_middleware.AuthService') as MockAuthService:

            mock_get_config.return_value = MockConfig('tenant_a')

            mock_auth_instance = MagicMock()
            mock_auth_instance.verify_jwt.return_value = (True, {'sub': 'auth_user_456'})
            mock_auth_instance.get_user_by_auth_id = AsyncMock(
                return_value=MockUser('tenant_a', role='consultant').data
            )
            MockAuthService.return_value = mock_auth_instance

            scope = create_mock_scope(
                '/api/v1/quotes',
                headers={
                    'authorization': 'Bearer valid.jwt.token',
                    'x-client-id': 'tenant_a',
                }
            )

            async def receive():
                return {'type': 'http.request', 'body': b''}

            request = Request(scope, receive)

            captured_user = None
            async def call_next(req):
                nonlocal captured_user
                captured_user = req.state.user
                return Response(content='OK', status_code=200)

            await middleware.dispatch(request, call_next)

            assert captured_user is not None
            assert captured_user.role == 'consultant'
            assert captured_user.is_admin == False
            assert captured_user.is_consultant == True


# ==================== Test Unknown Tenant ====================

class TestUnknownTenant:
    """Test handling of unknown/invalid tenant IDs"""

    @pytest.mark.asyncio
    async def test_unknown_tenant_returns_400(self):
        """
        Test: Request with unknown tenant ID in X-Client-ID
        Expected: 400 Bad Request with "Unknown client" message
        """
        from src.middleware.auth_middleware import AuthMiddleware
        from starlette.requests import Request
        from starlette.responses import Response

        middleware = AuthMiddleware(app=MagicMock())

        with patch('src.middleware.auth_middleware.get_config') as mock_get_config:
            # Simulate config not found
            mock_get_config.side_effect = FileNotFoundError("Client not found")

            scope = create_mock_scope(
                '/api/v1/quotes',
                headers={
                    'authorization': 'Bearer valid.jwt.token',
                    'x-client-id': 'unknown_tenant_xyz',
                }
            )

            async def receive():
                return {'type': 'http.request', 'body': b''}

            request = Request(scope, receive)

            async def call_next(req):
                return Response(content='OK', status_code=200)

            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 400
            body = response.body.decode() if hasattr(response, 'body') else ''
            assert 'unknown' in body.lower() or 'client' in body.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
