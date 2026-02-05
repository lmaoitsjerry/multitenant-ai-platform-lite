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

    def test_docs_is_not_public(self):
        """Test that /docs is NOT public (restricted; disabled in production)"""
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/docs') == False

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


# ==================== NEW TESTS: ASGI-level middleware tests ====================
# The AuthMiddleware is a pure ASGI middleware (__call__(scope, receive, send)).
# The tests below exercise the actual ASGI interface directly.


async def _run_middleware(scope, patches=None):
    """
    Helper: run AuthMiddleware.__call__ and capture the response status + body.

    Returns (status_code, body_bytes, scope_after).
    If the inner app is reached, status 200 is returned from the inner app.
    """
    from src.middleware.auth_middleware import AuthMiddleware

    captured = {"status": None, "body": b"", "app_called": False, "scope": scope}

    async def mock_app(sc, recv, snd):
        captured["app_called"] = True
        captured["scope"] = sc
        # Simulate a 200 response from the inner app
        await snd({
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"text/plain")],
        })
        await snd({"type": "http.response.body", "body": b"OK"})

    middleware = AuthMiddleware(app=mock_app)

    response_started = False

    async def send(message):
        nonlocal response_started
        if message["type"] == "http.response.start":
            captured["status"] = message["status"]
            response_started = True
        elif message["type"] == "http.response.body":
            captured["body"] += message.get("body", b"")

    async def receive():
        return {"type": "http.request", "body": b""}

    await middleware(scope, receive, send)
    return captured["status"], captured["body"], captured["scope"], captured["app_called"]


class TestAuthMiddlewareInit:
    """Tests for AuthMiddleware initialization and basic structure."""

    def test_middleware_stores_app_reference(self):
        """AuthMiddleware.__init__ stores the wrapped ASGI app."""
        from src.middleware.auth_middleware import AuthMiddleware
        sentinel = object()
        mw = AuthMiddleware(app=sentinel)
        assert mw.app is sentinel

    def test_middleware_is_callable(self):
        """AuthMiddleware instances are callable (ASGI interface)."""
        from src.middleware.auth_middleware import AuthMiddleware
        mw = AuthMiddleware(app=MagicMock())
        assert callable(mw)

    def test_middleware_has_send_json_method(self):
        """AuthMiddleware exposes _send_json helper."""
        from src.middleware.auth_middleware import AuthMiddleware
        mw = AuthMiddleware(app=MagicMock())
        assert hasattr(mw, '_send_json')


# ==================== Test PUBLIC_PATHS completeness ====================

class TestPublicPathsCompleteness:
    """Verify every entry in PUBLIC_PATHS and PUBLIC_PREFIXES is recognised."""

    def test_root_path_is_public(self):
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/') is True

    def test_health_live_is_public(self):
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/health/live') is True

    def test_metrics_is_public(self):
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/metrics') is True

    def test_password_reset_is_public(self):
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/api/v1/auth/password/reset') is True

    def test_invite_accept_is_public(self):
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/api/v1/auth/invite/accept') is True

    def test_webhooks_prefix_is_public(self):
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/api/v1/webhooks/sendgrid') is True
        assert is_public_path('/webhooks/stripe') is True

    def test_inbound_prefix_is_public(self):
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/api/v1/inbound/email') is True

    def test_quotes_chat_is_public(self):
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/api/v1/quotes/chat') is True

    def test_branding_endpoints_are_public(self):
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/api/v1/branding') is True
        assert is_public_path('/api/v1/branding/presets') is True
        assert is_public_path('/api/v1/branding/fonts') is True

    def test_helpdesk_endpoints_are_public(self):
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/api/v1/helpdesk/faiss-status') is True
        assert is_public_path('/api/v1/helpdesk/test-search') is True
        assert is_public_path('/api/v1/helpdesk/ask') is True
        assert is_public_path('/api/v1/helpdesk/topics') is True
        assert is_public_path('/api/v1/helpdesk/search') is True

    def test_onboarding_prefix_is_public(self):
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/api/v1/onboarding/signup') is True

    def test_public_prefix_is_public(self):
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/api/v1/public/invoice/abc') is True

    def test_rates_prefix_is_public(self):
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/api/v1/rates/search') is True

    def test_travel_prefix_is_public(self):
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/api/v1/travel/flights') is True

    def test_knowledge_global_prefix_is_public(self):
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/api/v1/knowledge/global') is True

    def test_non_public_paths_are_rejected(self):
        """Paths not in PUBLIC_PATHS or PUBLIC_PREFIXES should NOT be public."""
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/api/v1/clients') is False
        assert is_public_path('/api/v1/invoices') is False
        assert is_public_path('/api/v1/notifications') is False
        assert is_public_path('/api/v1/analytics') is False
        assert is_public_path('/api/v1/templates') is False
        assert is_public_path('/api/v1/settings') is False
        assert is_public_path('/api/v1/pipeline') is False

    def test_legacy_webhook_prefix_is_public(self):
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/api/webhooks/sendgrid/inbound') is True


# ==================== ASGI-level Token Extraction Tests ====================

class TestTokenExtraction:
    """Tests for Authorization header parsing at the ASGI level."""

    @pytest.mark.asyncio
    async def test_bearer_token_extracted_correctly(self):
        """Valid 'Bearer <token>' is accepted and forwarded to AuthService."""
        from src.middleware.auth_middleware import AuthMiddleware

        with patch('src.middleware.auth_middleware.get_config') as mock_gc, \
             patch('src.middleware.auth_middleware.AuthService') as MockAS:

            mock_gc.return_value = MockConfig('t1')
            inst = MagicMock()
            inst.verify_jwt.return_value = (True, {'sub': 'uid1'})
            inst.get_user_by_auth_id = AsyncMock(return_value=MockUser('t1').data)
            MockAS.return_value = inst

            scope = create_mock_scope('/api/v1/quotes', headers={
                'authorization': 'Bearer my.jwt.token',
                'x-client-id': 't1',
            })
            status, body, scope_out, app_called = await _run_middleware(scope)

            assert app_called is True
            assert status == 200
            inst.verify_jwt.assert_called_once_with('my.jwt.token')

    @pytest.mark.asyncio
    async def test_bearer_prefix_case_insensitive(self):
        """'bearer' (lowercase) should also be accepted."""
        with patch('src.middleware.auth_middleware.get_config') as mock_gc, \
             patch('src.middleware.auth_middleware.AuthService') as MockAS:

            mock_gc.return_value = MockConfig('t1')
            inst = MagicMock()
            inst.verify_jwt.return_value = (True, {'sub': 'uid1'})
            inst.get_user_by_auth_id = AsyncMock(return_value=MockUser('t1').data)
            MockAS.return_value = inst

            scope = create_mock_scope('/api/v1/quotes', headers={
                'authorization': 'bearer my.jwt.token',
                'x-client-id': 't1',
            })
            status, body, scope_out, app_called = await _run_middleware(scope)
            assert app_called is True
            assert status == 200

    @pytest.mark.asyncio
    async def test_missing_bearer_prefix_returns_401(self):
        """'Token xyz' (wrong prefix) is rejected with 401."""
        scope = create_mock_scope('/api/v1/quotes', headers={
            'authorization': 'Token abc.def.ghi',
            'x-client-id': 't1',
        })
        status, body, _, app_called = await _run_middleware(scope)
        assert status == 401
        assert app_called is False
        assert b'Invalid authorization header format' in body

    @pytest.mark.asyncio
    async def test_empty_authorization_header_returns_401(self):
        """Empty Authorization header value is rejected."""
        scope = create_mock_scope('/api/v1/quotes', headers={
            'authorization': '',
            'x-client-id': 't1',
        })
        status, body, _, app_called = await _run_middleware(scope)
        assert status == 401
        assert app_called is False

    @pytest.mark.asyncio
    async def test_bearer_with_no_token_returns_401(self):
        """'Bearer ' with nothing after it (single part) is rejected."""
        scope = create_mock_scope('/api/v1/quotes', headers={
            'authorization': 'Bearer',
            'x-client-id': 't1',
        })
        status, body, _, app_called = await _run_middleware(scope)
        assert status == 401
        assert app_called is False

    @pytest.mark.asyncio
    async def test_bearer_with_extra_parts_returns_401(self):
        """'Bearer tok1 tok2' (three parts) is rejected."""
        scope = create_mock_scope('/api/v1/quotes', headers={
            'authorization': 'Bearer tok1 tok2',
            'x-client-id': 't1',
        })
        status, body, _, app_called = await _run_middleware(scope)
        assert status == 401
        assert app_called is False


# ==================== ASGI-level JWT Decoding Tests ====================

class TestJWTDecoding:
    """Test JWT verification outcomes at the ASGI level."""

    @pytest.mark.asyncio
    async def test_expired_token_returns_401_with_message(self):
        """Expired JWT returns 401 and the error from verify_jwt."""
        with patch('src.middleware.auth_middleware.get_config') as mock_gc, \
             patch('src.middleware.auth_middleware.AuthService') as MockAS:

            mock_gc.return_value = MockConfig('t1')
            inst = MagicMock()
            inst.verify_jwt.return_value = (False, {'error': 'Token expired'})
            MockAS.return_value = inst

            scope = create_mock_scope('/api/v1/quotes', headers={
                'authorization': 'Bearer expired.jwt.here',
                'x-client-id': 't1',
            })
            status, body, _, app_called = await _run_middleware(scope)
            assert status == 401
            assert app_called is False
            assert b'Token expired' in body

    @pytest.mark.asyncio
    async def test_invalid_signature_returns_401(self):
        """JWT with invalid signature returns 401."""
        with patch('src.middleware.auth_middleware.get_config') as mock_gc, \
             patch('src.middleware.auth_middleware.AuthService') as MockAS:

            mock_gc.return_value = MockConfig('t1')
            inst = MagicMock()
            inst.verify_jwt.return_value = (False, {'error': 'Invalid signature'})
            MockAS.return_value = inst

            scope = create_mock_scope('/api/v1/quotes', headers={
                'authorization': 'Bearer tampered.jwt.sig',
                'x-client-id': 't1',
            })
            status, body, _, app_called = await _run_middleware(scope)
            assert status == 401
            assert b'Invalid signature' in body

    @pytest.mark.asyncio
    async def test_token_missing_sub_claim_returns_401(self):
        """JWT that decodes but has no 'sub' claim returns 401."""
        with patch('src.middleware.auth_middleware.get_config') as mock_gc, \
             patch('src.middleware.auth_middleware.AuthService') as MockAS:

            mock_gc.return_value = MockConfig('t1')
            inst = MagicMock()
            # Valid JWT but no 'sub' in payload
            inst.verify_jwt.return_value = (True, {'aud': 'authenticated'})
            MockAS.return_value = inst

            scope = create_mock_scope('/api/v1/quotes', headers={
                'authorization': 'Bearer no.sub.jwt',
                'x-client-id': 't1',
            })
            status, body, _, app_called = await _run_middleware(scope)
            assert status == 401
            assert app_called is False
            assert b'Invalid token payload' in body


# ==================== ASGI-level UserContext on scope.state ====================

class TestUserContextOnScope:
    """Verify user context is attached to scope['state'] correctly."""

    @pytest.mark.asyncio
    async def test_user_context_set_on_scope_state(self):
        """After auth, scope['state']['user'] is a UserContext instance."""
        from src.middleware.auth_middleware import UserContext

        with patch('src.middleware.auth_middleware.get_config') as mock_gc, \
             patch('src.middleware.auth_middleware.AuthService') as MockAS:

            mock_gc.return_value = MockConfig('t1')
            inst = MagicMock()
            inst.verify_jwt.return_value = (True, {'sub': 'au1'})
            inst.get_user_by_auth_id = AsyncMock(return_value={
                'id': 'u1', 'email': 'a@t1.com', 'name': 'A',
                'role': 'admin', 'tenant_id': 't1', 'is_active': True,
            })
            MockAS.return_value = inst

            scope = create_mock_scope('/api/v1/quotes', headers={
                'authorization': 'Bearer ok.jwt',
                'x-client-id': 't1',
            })
            status, body, scope_out, app_called = await _run_middleware(scope)
            assert app_called is True
            user = scope_out['state']['user']
            assert isinstance(user, UserContext)
            assert user.user_id == 'u1'
            assert user.auth_user_id == 'au1'
            assert user.email == 'a@t1.com'
            assert user.tenant_id == 't1'
            assert user.role == 'admin'

    @pytest.mark.asyncio
    async def test_public_path_sets_user_to_none(self):
        """Public paths set scope['state']['user'] = None."""
        scope = create_mock_scope('/health', headers={})
        status, body, scope_out, app_called = await _run_middleware(scope)
        assert app_called is True
        assert scope_out['state']['user'] is None


# ==================== Multi-tenant Isolation ====================

class TestMultiTenantIsolation:
    """Tenant isolation enforcement at ASGI level."""

    @pytest.mark.asyncio
    async def test_tenant_mismatch_returns_403(self):
        """X-Client-ID different from user's tenant_id yields 403."""
        with patch('src.middleware.auth_middleware.get_config') as mock_gc, \
             patch('src.middleware.auth_middleware.AuthService') as MockAS:

            mock_gc.return_value = MockConfig('tenant_b')
            inst = MagicMock()
            inst.verify_jwt.return_value = (True, {'sub': 'au1'})
            inst.get_user_by_auth_id = AsyncMock(return_value=MockUser('tenant_a').data)
            MockAS.return_value = inst

            scope = create_mock_scope('/api/v1/quotes', headers={
                'authorization': 'Bearer valid',
                'x-client-id': 'tenant_b',
            })
            status, body, _, app_called = await _run_middleware(scope)
            assert status == 403
            assert app_called is False
            assert b'tenant mismatch' in body or b'Access denied' in body

    @pytest.mark.asyncio
    async def test_no_xclientid_header_skips_mismatch_check(self):
        """Without X-Client-ID, mismatch check is skipped (uses default)."""
        with patch('src.middleware.auth_middleware.get_config') as mock_gc, \
             patch('src.middleware.auth_middleware.AuthService') as MockAS, \
             patch.dict('os.environ', {'CLIENT_ID': 'default_t'}):

            mock_gc.return_value = MockConfig('default_t')
            inst = MagicMock()
            inst.verify_jwt.return_value = (True, {'sub': 'au1'})
            inst.get_user_by_auth_id = AsyncMock(return_value=MockUser('default_t').data)
            MockAS.return_value = inst

            scope = create_mock_scope('/api/v1/quotes', headers={
                'authorization': 'Bearer valid',
            })
            status, body, _, app_called = await _run_middleware(scope)
            assert status == 200
            assert app_called is True

    @pytest.mark.asyncio
    async def test_tenant_id_from_jwt_user_not_from_header(self):
        """The UserContext.tenant_id comes from DB user, not from X-Client-ID header."""
        from src.middleware.auth_middleware import UserContext

        with patch('src.middleware.auth_middleware.get_config') as mock_gc, \
             patch('src.middleware.auth_middleware.AuthService') as MockAS:

            mock_gc.return_value = MockConfig('real_tenant')
            inst = MagicMock()
            inst.verify_jwt.return_value = (True, {'sub': 'au1'})
            inst.get_user_by_auth_id = AsyncMock(return_value={
                'id': 'u1', 'email': 'a@real.com', 'name': 'A',
                'role': 'admin', 'tenant_id': 'real_tenant', 'is_active': True,
            })
            MockAS.return_value = inst

            scope = create_mock_scope('/api/v1/quotes', headers={
                'authorization': 'Bearer valid',
                'x-client-id': 'real_tenant',
            })
            status, body, scope_out, app_called = await _run_middleware(scope)
            assert app_called is True
            user = scope_out['state']['user']
            assert user.tenant_id == 'real_tenant'


# ==================== OPTIONS / CORS Preflight ====================

class TestOptionsPreflightASGI:
    """CORS preflight OPTIONS at the ASGI level."""

    @pytest.mark.asyncio
    async def test_options_request_passes_through(self):
        """OPTIONS request on protected path passes without auth."""
        scope = create_mock_scope('/api/v1/quotes', method='OPTIONS', headers={})
        status, body, scope_out, app_called = await _run_middleware(scope)
        assert app_called is True
        assert scope_out['state']['user'] is None

    @pytest.mark.asyncio
    async def test_options_request_no_auth_header_needed(self):
        """OPTIONS does not need Authorization header."""
        scope = create_mock_scope('/api/v1/invoices', method='OPTIONS', headers={})
        status, body, _, app_called = await _run_middleware(scope)
        assert app_called is True
        assert status == 200


# ==================== Websocket / Non-HTTP Handling ====================

class TestNonHTTPScopes:
    """Test middleware behaviour for non-http scope types."""

    @pytest.mark.asyncio
    async def test_websocket_scope_passes_through(self):
        """Websocket scopes are forwarded to the inner app without auth."""
        from src.middleware.auth_middleware import AuthMiddleware

        app_called = False
        async def mock_app(scope, receive, send):
            nonlocal app_called
            app_called = True

        mw = AuthMiddleware(app=mock_app)

        scope = {
            'type': 'websocket',
            'path': '/ws',
            'headers': [],
        }
        async def receive():
            return {}
        async def send(msg):
            pass

        await mw(scope, receive, send)
        assert app_called is True

    @pytest.mark.asyncio
    async def test_lifespan_scope_passes_through(self):
        """Lifespan events are forwarded without auth."""
        from src.middleware.auth_middleware import AuthMiddleware

        app_called = False
        async def mock_app(scope, receive, send):
            nonlocal app_called
            app_called = True

        mw = AuthMiddleware(app=mock_app)

        scope = {'type': 'lifespan'}
        async def receive():
            return {}
        async def send(msg):
            pass

        await mw(scope, receive, send)
        assert app_called is True


# ==================== Edge Cases ====================

class TestEdgeCasesAuth:
    """Edge cases for the auth middleware."""

    @pytest.mark.asyncio
    async def test_scope_without_state_key_gets_state_created(self):
        """If scope has no 'state' key, middleware creates it."""
        with patch('src.middleware.auth_middleware.get_config') as mock_gc, \
             patch('src.middleware.auth_middleware.AuthService') as MockAS:

            mock_gc.return_value = MockConfig('t1')
            inst = MagicMock()
            inst.verify_jwt.return_value = (True, {'sub': 'au1'})
            inst.get_user_by_auth_id = AsyncMock(return_value=MockUser('t1').data)
            MockAS.return_value = inst

            scope = {
                'type': 'http',
                'method': 'GET',
                'path': '/api/v1/quotes',
                'headers': [
                    (b'authorization', b'Bearer valid.jwt'),
                    (b'x-client-id', b't1'),
                ],
                # No 'state' key
            }
            status, body, scope_out, app_called = await _run_middleware(scope)
            assert 'state' in scope_out
            assert app_called is True

    @pytest.mark.asyncio
    async def test_auth_service_exception_returns_500(self):
        """Unhandled exception in AuthService results in 500."""
        with patch('src.middleware.auth_middleware.get_config') as mock_gc, \
             patch('src.middleware.auth_middleware.AuthService') as MockAS:

            mock_gc.return_value = MockConfig('t1')
            MockAS.side_effect = RuntimeError("Supabase connection failed")

            scope = create_mock_scope('/api/v1/quotes', headers={
                'authorization': 'Bearer valid',
                'x-client-id': 't1',
            })
            status, body, _, app_called = await _run_middleware(scope)
            assert status == 500
            assert app_called is False
            assert b'Authentication error' in body

    @pytest.mark.asyncio
    async def test_unknown_client_config_returns_400(self):
        """FileNotFoundError from get_config returns 400."""
        with patch('src.middleware.auth_middleware.get_config') as mock_gc:
            mock_gc.side_effect = FileNotFoundError("No config")

            scope = create_mock_scope('/api/v1/quotes', headers={
                'authorization': 'Bearer valid',
                'x-client-id': 'no_such_tenant',
            })
            status, body, _, app_called = await _run_middleware(scope)
            assert status == 400
            assert app_called is False
            assert b'Unknown client' in body

    @pytest.mark.asyncio
    async def test_deactivated_user_returns_401_with_message(self):
        """Deactivated user gets 401 with 'deactivated' message."""
        with patch('src.middleware.auth_middleware.get_config') as mock_gc, \
             patch('src.middleware.auth_middleware.AuthService') as MockAS:

            mock_gc.return_value = MockConfig('t1')
            inst = MagicMock()
            inst.verify_jwt.return_value = (True, {'sub': 'au1'})
            inst.get_user_by_auth_id = AsyncMock(return_value=MockUser('t1', is_active=False).data)
            MockAS.return_value = inst

            scope = create_mock_scope('/api/v1/quotes', headers={
                'authorization': 'Bearer valid',
                'x-client-id': 't1',
            })
            status, body, _, app_called = await _run_middleware(scope)
            assert status == 401
            assert app_called is False
            assert b'deactivated' in body


# ==================== UserContext Unit Tests ====================

class TestUserContextUnit:
    """Unit tests for the UserContext dataclass-like object."""

    def test_to_dict_returns_all_fields(self):
        from src.middleware.auth_middleware import UserContext
        uc = UserContext(
            user_id='u1', auth_user_id='au1', email='a@b.com',
            name='Alice', role='admin', tenant_id='t1', is_active=True,
        )
        d = uc.to_dict()
        assert d == {
            'user_id': 'u1', 'auth_user_id': 'au1', 'email': 'a@b.com',
            'name': 'Alice', 'role': 'admin', 'tenant_id': 't1', 'is_active': True,
        }

    def test_is_admin_property(self):
        from src.middleware.auth_middleware import UserContext
        admin = UserContext('u', 'a', 'e', 'n', 'admin', 't')
        assert admin.is_admin is True
        assert admin.is_consultant is False

    def test_is_consultant_property(self):
        from src.middleware.auth_middleware import UserContext
        con = UserContext('u', 'a', 'e', 'n', 'consultant', 't')
        assert con.is_consultant is True
        assert con.is_admin is False

    def test_default_is_active_true(self):
        from src.middleware.auth_middleware import UserContext
        uc = UserContext('u', 'a', 'e', 'n', 'admin', 't')
        assert uc.is_active is True

    def test_is_active_false(self):
        from src.middleware.auth_middleware import UserContext
        uc = UserContext('u', 'a', 'e', 'n', 'admin', 't', is_active=False)
        assert uc.is_active is False

    def test_unknown_role_not_admin_not_consultant(self):
        from src.middleware.auth_middleware import UserContext
        uc = UserContext('u', 'a', 'e', 'n', 'viewer', 't')
        assert uc.is_admin is False
        assert uc.is_consultant is False


# ==================== Dependency Function Tests ====================

class TestDependencyFunctions:
    """Tests for FastAPI dependency functions."""

    def test_get_current_user_raises_when_no_user(self):
        """get_current_user raises 401 when request.state.user is None."""
        from src.middleware.auth_middleware import get_current_user
        from fastapi import HTTPException

        request = MagicMock()
        request.state = MagicMock(spec=[])  # no 'user' attribute
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(request)
        assert exc_info.value.status_code == 401

    def test_get_current_user_returns_user_context(self):
        """get_current_user returns the user when present."""
        from src.middleware.auth_middleware import get_current_user, UserContext
        uc = UserContext('u', 'a', 'e', 'n', 'admin', 't')
        request = MagicMock()
        request.state.user = uc
        result = get_current_user(request)
        assert result is uc

    def test_get_current_user_optional_returns_none(self):
        """get_current_user_optional returns None when no user."""
        from src.middleware.auth_middleware import get_current_user_optional
        request = MagicMock()
        request.state = MagicMock(spec=[])
        result = get_current_user_optional(request)
        assert result is None

    def test_get_current_user_optional_returns_user(self):
        """get_current_user_optional returns user when present."""
        from src.middleware.auth_middleware import get_current_user_optional, UserContext
        uc = UserContext('u', 'a', 'e', 'n', 'admin', 't')
        request = MagicMock()
        request.state.user = uc
        result = get_current_user_optional(request)
        assert result is uc

    def test_require_admin_raises_403_for_non_admin(self):
        """require_admin raises 403 for non-admin user."""
        from src.middleware.auth_middleware import require_admin, UserContext
        from fastapi import HTTPException
        uc = UserContext('u', 'a', 'e', 'n', 'consultant', 't')
        request = MagicMock()
        request.state.user = uc
        with pytest.raises(HTTPException) as exc_info:
            require_admin(request)
        assert exc_info.value.status_code == 403

    def test_require_admin_returns_admin_user(self):
        """require_admin returns user for admin role."""
        from src.middleware.auth_middleware import require_admin, UserContext
        uc = UserContext('u', 'a', 'e', 'n', 'admin', 't')
        request = MagicMock()
        request.state.user = uc
        result = require_admin(request)
        assert result is uc


# ==================== Decorator Tests ====================

class TestDecorators:
    """Tests for require_auth and require_role decorators."""

    @pytest.mark.asyncio
    async def test_require_auth_decorator_allows_authenticated(self):
        """require_auth passes when request.state.user is set."""
        from src.middleware.auth_middleware import require_auth, UserContext

        @require_auth
        async def handler(request):
            return "ok"

        uc = UserContext('u', 'a', 'e', 'n', 'admin', 't')
        request = MagicMock()
        request.state.user = uc
        result = await handler(request=request)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_require_auth_decorator_rejects_unauthenticated(self):
        """require_auth raises 401 when no user on request."""
        from src.middleware.auth_middleware import require_auth
        from fastapi import HTTPException

        @require_auth
        async def handler(request):
            return "ok"

        request = MagicMock()
        request.state = MagicMock(spec=[])  # no user attribute
        with pytest.raises(HTTPException) as exc_info:
            await handler(request=request)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_require_role_decorator_allows_matching_role(self):
        """require_role('admin') passes for admin user."""
        from src.middleware.auth_middleware import require_role, UserContext

        @require_role('admin')
        async def handler(request):
            return "admin_ok"

        uc = UserContext('u', 'a', 'e', 'n', 'admin', 't')
        request = MagicMock()
        request.state.user = uc
        result = await handler(request=request)
        assert result == "admin_ok"

    @pytest.mark.asyncio
    async def test_require_role_decorator_rejects_wrong_role(self):
        """require_role('admin') rejects consultant user with 403."""
        from src.middleware.auth_middleware import require_role, UserContext
        from fastapi import HTTPException

        @require_role('admin')
        async def handler(request):
            return "admin_ok"

        uc = UserContext('u', 'a', 'e', 'n', 'consultant', 't')
        request = MagicMock()
        request.state.user = uc
        with pytest.raises(HTTPException) as exc_info:
            await handler(request=request)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_role_decorator_rejects_no_user(self):
        """require_role raises 401 when no user at all."""
        from src.middleware.auth_middleware import require_role
        from fastapi import HTTPException

        @require_role('admin')
        async def handler(request):
            return "ok"

        request = MagicMock()
        request.state = MagicMock(spec=[])
        with pytest.raises(HTTPException) as exc_info:
            await handler(request=request)
        assert exc_info.value.status_code == 401


# ==================== _send_json Tests ====================

class TestSendJson:
    """Test the _send_json helper method."""

    @pytest.mark.asyncio
    async def test_send_json_sends_correct_status(self):
        """_send_json sends correct HTTP status code."""
        from src.middleware.auth_middleware import AuthMiddleware
        import json

        mw = AuthMiddleware(app=MagicMock())
        messages = []
        async def send(msg):
            messages.append(msg)

        await mw._send_json(send, 422, {"detail": "Validation error"})

        assert messages[0]["type"] == "http.response.start"
        assert messages[0]["status"] == 422
        assert messages[1]["type"] == "http.response.body"
        body = json.loads(messages[1]["body"])
        assert body["detail"] == "Validation error"

    @pytest.mark.asyncio
    async def test_send_json_sets_content_type_json(self):
        """_send_json sets content-type to application/json."""
        from src.middleware.auth_middleware import AuthMiddleware

        mw = AuthMiddleware(app=MagicMock())
        messages = []
        async def send(msg):
            messages.append(msg)

        await mw._send_json(send, 200, {"ok": True})

        headers = dict(messages[0]["headers"])
        assert headers[b"content-type"] == b"application/json"

    @pytest.mark.asyncio
    async def test_send_json_sets_content_length(self):
        """_send_json sets correct content-length header."""
        from src.middleware.auth_middleware import AuthMiddleware
        import json

        mw = AuthMiddleware(app=MagicMock())
        messages = []
        async def send(msg):
            messages.append(msg)

        payload = {"detail": "test"}
        await mw._send_json(send, 200, payload)

        headers = dict(messages[0]["headers"])
        expected_len = len(json.dumps(payload).encode())
        assert headers[b"content-length"] == str(expected_len).encode()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
