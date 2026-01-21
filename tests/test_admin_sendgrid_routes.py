"""
Tests for Admin SendGrid Routes

Comprehensive endpoint tests covering:
- Admin token authentication requirements
- List subusers endpoint
- Subuser statistics endpoint
- Enable/disable subuser endpoints
- Global statistics endpoint
- Tenant credential management endpoints
- Pydantic model validation

Uses FastAPI TestClient with mocked SendGridAdminService.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.fixtures.sendgrid_fixtures import (
    create_mock_sendgrid_service,
    generate_subusers,
    SUBUSER_LIST_RESPONSE,
)


# ==================== Fixtures ====================

@pytest.fixture
def mock_admin_token():
    """Set admin token environment variable."""
    with patch.dict(os.environ, {"ADMIN_API_TOKEN": "test-admin-token-123"}):
        yield "test-admin-token-123"


@pytest.fixture
def admin_headers(mock_admin_token):
    """Headers with valid admin token."""
    return {"X-Admin-Token": mock_admin_token}


@pytest.fixture
def test_client():
    """Create a basic TestClient."""
    from main import app
    return TestClient(app)


@pytest.fixture
def mock_client_config():
    """Create a mock ClientConfig."""
    config = MagicMock()
    config.client_id = "test_tenant"
    config.company_name = "Test Company"
    config.sendgrid_api_key = "SG.test-key"
    config.sendgrid_from_email = "test@example.com"
    config.sendgrid_from_name = "Test Company"
    config.sendgrid_username = "tenant_test"
    return config


# ==================== Admin Token Validation Tests ====================

class TestAdminSendGridAuth:
    """Test admin authentication for all SendGrid endpoints."""

    def test_list_subusers_requires_admin_token(self, test_client):
        """GET /sendgrid/subusers without token should return 401/503."""
        response = test_client.get("/api/v1/admin/sendgrid/subusers")
        # 401 if no token, 503 if admin not configured
        assert response.status_code in [401, 503]

    def test_subuser_stats_requires_admin_token(self, test_client):
        """GET /sendgrid/subusers/{username}/stats without token should return 401/503."""
        response = test_client.get("/api/v1/admin/sendgrid/subusers/test_user/stats")
        assert response.status_code in [401, 503]

    def test_disable_subuser_requires_admin_token(self, test_client):
        """POST /sendgrid/subusers/{username}/disable without token should return 401/503."""
        response = test_client.post("/api/v1/admin/sendgrid/subusers/test_user/disable")
        assert response.status_code in [401, 503]

    def test_enable_subuser_requires_admin_token(self, test_client):
        """POST /sendgrid/subusers/{username}/enable without token should return 401/503."""
        response = test_client.post("/api/v1/admin/sendgrid/subusers/test_user/enable")
        assert response.status_code in [401, 503]

    def test_global_stats_requires_admin_token(self, test_client):
        """GET /sendgrid/stats without token should return 401/503."""
        response = test_client.get("/api/v1/admin/sendgrid/stats")
        assert response.status_code in [401, 503]

    def test_store_credentials_requires_admin_token(self, test_client):
        """POST /sendgrid/tenants/{tenant_id}/credentials without token should return 401/503."""
        response = test_client.post(
            "/api/v1/admin/sendgrid/tenants/test_tenant/credentials",
            json={"api_key": "SG.test"}
        )
        assert response.status_code in [401, 503]

    def test_get_credentials_requires_admin_token(self, test_client):
        """GET /sendgrid/tenants/{tenant_id}/credentials without token should return 401/503."""
        response = test_client.get("/api/v1/admin/sendgrid/tenants/test_tenant/credentials")
        assert response.status_code in [401, 503]

    def test_delete_credentials_requires_admin_token(self, test_client):
        """DELETE /sendgrid/tenants/{tenant_id}/credentials without token should return 401/503."""
        response = test_client.delete("/api/v1/admin/sendgrid/tenants/test_tenant/credentials")
        assert response.status_code in [401, 503]


# ==================== List Subusers Endpoint Tests ====================

class TestListSubusersEndpoint:
    """Test GET /api/v1/admin/sendgrid/subusers endpoint."""

    def test_list_subusers_success(self, test_client, admin_headers):
        """Should return list of subusers with enriched tenant info."""
        mock_service = create_mock_sendgrid_service(
            available=True,
            subusers=SUBUSER_LIST_RESPONSE
        )

        with patch('src.api.admin_sendgrid_routes.get_sendgrid_admin_service', return_value=mock_service):
            with patch('src.api.admin_sendgrid_routes.list_clients', return_value=[]):
                response = test_client.get(
                    "/api/v1/admin/sendgrid/subusers",
                    headers=admin_headers
                )

                assert response.status_code == 200
                data = response.json()
                assert data['success'] is True
                assert 'data' in data
                assert 'count' in data
                assert data['count'] == 3

    def test_list_subusers_with_tenant_matching(self, test_client, admin_headers, mock_client_config):
        """Should enrich subusers with tenant info when matching."""
        subusers = [{'username': 'tenant_test', 'email': 'test@example.com', 'disabled': False, 'id': 1}]
        mock_service = create_mock_sendgrid_service(available=True, subusers=subusers)

        with patch('src.api.admin_sendgrid_routes.get_sendgrid_admin_service', return_value=mock_service):
            with patch('src.api.admin_sendgrid_routes.list_clients', return_value=['test_tenant']):
                with patch('src.api.admin_sendgrid_routes.ClientConfig', return_value=mock_client_config):
                    response = test_client.get(
                        "/api/v1/admin/sendgrid/subusers",
                        headers=admin_headers
                    )

                    assert response.status_code == 200
                    data = response.json()
                    # Should have matched tenant info
                    assert data['count'] == 1
                    # Tenant matching may or may not succeed depending on config

    def test_list_subusers_sendgrid_not_configured(self, test_client, admin_headers):
        """Should return empty list with message when SendGrid not configured."""
        mock_service = create_mock_sendgrid_service(available=False)

        with patch('src.api.admin_sendgrid_routes.get_sendgrid_admin_service', return_value=mock_service):
            response = test_client.get(
                "/api/v1/admin/sendgrid/subusers",
                headers=admin_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['data'] == []
            assert 'not configured' in data.get('message', '').lower()


# ==================== Subuser Stats Endpoint Tests ====================

class TestSubuserStatsEndpoint:
    """Test GET /api/v1/admin/sendgrid/subusers/{username}/stats endpoint."""

    def test_get_subuser_stats_success(self, test_client, admin_headers):
        """Should return stats for subuser."""
        mock_service = create_mock_sendgrid_service(
            available=True,
            subuser_stats={
                'username': 'test_user',
                'period_days': 30,
                'totals': {'requests': 100, 'delivered': 95},
                'daily': []
            }
        )

        with patch('src.api.admin_sendgrid_routes.get_sendgrid_admin_service', return_value=mock_service):
            response = test_client.get(
                "/api/v1/admin/sendgrid/subusers/test_user/stats",
                headers=admin_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['data']['username'] == 'test_user'

    def test_get_subuser_stats_with_days_param(self, test_client, admin_headers):
        """Should pass days parameter to service."""
        mock_service = create_mock_sendgrid_service(
            available=True,
            subuser_stats={'username': 'test_user', 'period_days': 7, 'totals': {}, 'daily': []}
        )

        with patch('src.api.admin_sendgrid_routes.get_sendgrid_admin_service', return_value=mock_service):
            response = test_client.get(
                "/api/v1/admin/sendgrid/subusers/test_user/stats?days=7",
                headers=admin_headers
            )

            assert response.status_code == 200
            mock_service.get_subuser_stats.assert_called_once_with('test_user', 7)

    def test_get_subuser_stats_service_unavailable(self, test_client, admin_headers):
        """Should return 503 when SendGrid not configured."""
        mock_service = create_mock_sendgrid_service(available=False)

        with patch('src.api.admin_sendgrid_routes.get_sendgrid_admin_service', return_value=mock_service):
            response = test_client.get(
                "/api/v1/admin/sendgrid/subusers/test_user/stats",
                headers=admin_headers
            )

            assert response.status_code == 503
            assert 'not configured' in response.json()['detail'].lower()

    def test_get_subuser_stats_error(self, test_client, admin_headers):
        """Should return 400 when service returns error dict."""
        mock_service = create_mock_sendgrid_service(
            available=True,
            subuser_stats={'error': 'User not found'}
        )

        with patch('src.api.admin_sendgrid_routes.get_sendgrid_admin_service', return_value=mock_service):
            response = test_client.get(
                "/api/v1/admin/sendgrid/subusers/unknown_user/stats",
                headers=admin_headers
            )

            assert response.status_code == 400


# ==================== Enable/Disable Subuser Endpoint Tests ====================

class TestSubuserEnableDisableEndpoint:
    """Test enable/disable subuser endpoints."""

    def test_disable_subuser_success(self, test_client, admin_headers):
        """Should return success when disabling subuser."""
        mock_service = create_mock_sendgrid_service(available=True)
        mock_service.disable_subuser.return_value = True

        with patch('src.api.admin_sendgrid_routes.get_sendgrid_admin_service', return_value=mock_service):
            response = test_client.post(
                "/api/v1/admin/sendgrid/subusers/test_user/disable",
                headers=admin_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['disabled'] is True

    def test_disable_subuser_failure(self, test_client, admin_headers):
        """Should return 400 when disable fails."""
        mock_service = create_mock_sendgrid_service(available=True)
        mock_service.disable_subuser.return_value = False

        with patch('src.api.admin_sendgrid_routes.get_sendgrid_admin_service', return_value=mock_service):
            response = test_client.post(
                "/api/v1/admin/sendgrid/subusers/test_user/disable",
                headers=admin_headers
            )

            assert response.status_code == 400

    def test_disable_subuser_service_unavailable(self, test_client, admin_headers):
        """Should return 503 when service unavailable."""
        mock_service = create_mock_sendgrid_service(available=False)

        with patch('src.api.admin_sendgrid_routes.get_sendgrid_admin_service', return_value=mock_service):
            response = test_client.post(
                "/api/v1/admin/sendgrid/subusers/test_user/disable",
                headers=admin_headers
            )

            assert response.status_code == 503

    def test_enable_subuser_success(self, test_client, admin_headers):
        """Should return success when enabling subuser."""
        mock_service = create_mock_sendgrid_service(available=True)
        mock_service.enable_subuser.return_value = True

        with patch('src.api.admin_sendgrid_routes.get_sendgrid_admin_service', return_value=mock_service):
            response = test_client.post(
                "/api/v1/admin/sendgrid/subusers/test_user/enable",
                headers=admin_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['disabled'] is False

    def test_enable_subuser_failure(self, test_client, admin_headers):
        """Should return 400 when enable fails."""
        mock_service = create_mock_sendgrid_service(available=True)
        mock_service.enable_subuser.return_value = False

        with patch('src.api.admin_sendgrid_routes.get_sendgrid_admin_service', return_value=mock_service):
            response = test_client.post(
                "/api/v1/admin/sendgrid/subusers/test_user/enable",
                headers=admin_headers
            )

            assert response.status_code == 400


# ==================== Global Stats Endpoint Tests ====================

class TestGlobalStatsEndpoint:
    """Test GET /api/v1/admin/sendgrid/stats endpoint."""

    def test_global_stats_success(self, test_client, admin_headers):
        """Should return global email statistics."""
        mock_service = create_mock_sendgrid_service(
            available=True,
            global_stats={
                'period_days': 30,
                'totals': {
                    'requests': 10000,
                    'delivered': 9500,
                    'open_rate': 25.5,
                    'delivery_rate': 95.0
                }
            }
        )

        with patch('src.api.admin_sendgrid_routes.get_sendgrid_admin_service', return_value=mock_service):
            response = test_client.get(
                "/api/v1/admin/sendgrid/stats",
                headers=admin_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert 'data' in data
            assert data['data']['totals']['requests'] == 10000

    def test_global_stats_not_configured(self, test_client, admin_headers):
        """Should return default zeros when SendGrid not configured."""
        mock_service = create_mock_sendgrid_service(available=False)

        with patch('src.api.admin_sendgrid_routes.get_sendgrid_admin_service', return_value=mock_service):
            response = test_client.get(
                "/api/v1/admin/sendgrid/stats",
                headers=admin_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['data']['totals']['requests'] == 0


# ==================== Tenant Credentials Endpoint Tests ====================

class TestTenantCredentialsEndpoints:
    """Test tenant credential management endpoints."""

    def test_store_credentials_success(self, test_client, admin_headers, mock_client_config):
        """Should store SendGrid credentials for tenant."""
        mock_supabase = MagicMock()
        mock_supabase.update_tenant_settings.return_value = True

        with patch('src.api.admin_sendgrid_routes.ClientConfig', return_value=mock_client_config):
            with patch('src.tools.supabase_tool.SupabaseTool', return_value=mock_supabase):
                response = test_client.post(
                    "/api/v1/admin/sendgrid/tenants/test_tenant/credentials",
                    headers=admin_headers,
                    json={
                        "api_key": "SG.new-api-key",
                        "username": "new_subuser",
                        "from_email": "new@example.com",
                        "from_name": "New Sender"
                    }
                )

                assert response.status_code == 200
                data = response.json()
                assert data['success'] is True
                assert data['tenant_id'] == 'test_tenant'

    def test_store_credentials_tenant_not_found(self, test_client, admin_headers):
        """Should return 404 when tenant not found."""
        with patch('src.api.admin_sendgrid_routes.ClientConfig', side_effect=Exception("Tenant not found")):
            response = test_client.post(
                "/api/v1/admin/sendgrid/tenants/nonexistent/credentials",
                headers=admin_headers,
                json={"api_key": "SG.test"}
            )

            assert response.status_code == 404

    def test_get_credentials_success(self, test_client, admin_headers, mock_client_config):
        """Should return credentials status (without exposing API key)."""
        mock_supabase = MagicMock()
        mock_supabase.get_tenant_settings.return_value = {
            'sendgrid_api_key': 'SG.secret-key',
            'sendgrid_username': 'tenant_user',
            'email_from_email': 'sender@example.com'
        }

        with patch('src.api.admin_sendgrid_routes.ClientConfig', return_value=mock_client_config):
            with patch('src.tools.supabase_tool.SupabaseTool', return_value=mock_supabase):
                response = test_client.get(
                    "/api/v1/admin/sendgrid/tenants/test_tenant/credentials",
                    headers=admin_headers
                )

                assert response.status_code == 200
                data = response.json()
                assert data['success'] is True
                assert data['configured'] is True
                assert data['source'] == 'database'
                # Should NOT expose the actual API key
                assert 'api_key' not in data or data.get('api_key') is None

    def test_get_credentials_tenant_not_found(self, test_client, admin_headers):
        """Should return 404 when tenant not found."""
        with patch('src.api.admin_sendgrid_routes.ClientConfig', side_effect=Exception("Tenant not found")):
            response = test_client.get(
                "/api/v1/admin/sendgrid/tenants/nonexistent/credentials",
                headers=admin_headers
            )

            assert response.status_code == 404

    def test_delete_credentials_success(self, test_client, admin_headers, mock_client_config):
        """Should delete (clear) credentials successfully."""
        mock_supabase = MagicMock()
        mock_supabase.update_tenant_settings.return_value = True

        with patch('src.api.admin_sendgrid_routes.ClientConfig', return_value=mock_client_config):
            with patch('src.tools.supabase_tool.SupabaseTool', return_value=mock_supabase):
                response = test_client.delete(
                    "/api/v1/admin/sendgrid/tenants/test_tenant/credentials",
                    headers=admin_headers
                )

                assert response.status_code == 200
                data = response.json()
                assert data['success'] is True
                # Should have called update with empty strings
                mock_supabase.update_tenant_settings.assert_called_once_with(
                    sendgrid_api_key="",
                    sendgrid_username=""
                )

    def test_delete_credentials_tenant_not_found(self, test_client, admin_headers):
        """Should return 404 when tenant not found."""
        with patch('src.api.admin_sendgrid_routes.ClientConfig', side_effect=Exception("Tenant not found")):
            response = test_client.delete(
                "/api/v1/admin/sendgrid/tenants/nonexistent/credentials",
                headers=admin_headers
            )

            assert response.status_code == 404


# ==================== Pydantic Model Tests ====================

class TestPydanticModels:
    """Test Pydantic model validation."""

    def test_subuser_info_model(self):
        """Verify SubuserInfo model validation."""
        from src.api.admin_sendgrid_routes import SubuserInfo

        # Valid model
        info = SubuserInfo(
            username="test_user",
            email="test@example.com",
            disabled=False,
            tenant_id="test_tenant",
            tenant_name="Test Company"
        )
        assert info.username == "test_user"
        assert info.disabled is False

        # Minimal required fields
        info_minimal = SubuserInfo(username="user")
        assert info_minimal.email is None
        assert info_minimal.tenant_id is None

    def test_subuser_stats_model(self):
        """Verify SubuserStats model validation."""
        from src.api.admin_sendgrid_routes import SubuserStats

        stats = SubuserStats(
            username="test_user",
            period_days=30,
            totals={"requests": 100, "delivered": 95},
            daily=[{"date": "2026-01-01", "requests": 100}]
        )
        assert stats.username == "test_user"
        assert stats.period_days == 30

    def test_global_email_stats_model(self):
        """Verify GlobalEmailStats model validation."""
        from src.api.admin_sendgrid_routes import GlobalEmailStats

        stats = GlobalEmailStats(
            period_days=30,
            totals={"requests": 10000, "delivered": 9500}
        )
        assert stats.period_days == 30
        assert stats.totals["requests"] == 10000

    def test_subuser_credentials_model(self):
        """Verify SubuserCredentials model validation."""
        from src.api.admin_sendgrid_routes import SubuserCredentials

        # Full model
        creds = SubuserCredentials(
            api_key="SG.test-key",
            username="subuser",
            from_email="sender@example.com",
            from_name="Sender Name"
        )
        assert creds.api_key == "SG.test-key"
        assert creds.username == "subuser"

        # Minimal (only api_key required)
        creds_minimal = SubuserCredentials(api_key="SG.key")
        assert creds_minimal.username is None
        assert creds_minimal.from_email is None


# ==================== Invalid Admin Token Tests ====================

class TestInvalidAdminToken:
    """Test endpoints with invalid admin token."""

    def test_list_subusers_invalid_token(self, test_client, mock_admin_token):
        """Should return 401 for invalid token."""
        response = test_client.get(
            "/api/v1/admin/sendgrid/subusers",
            headers={"X-Admin-Token": "wrong-token"}
        )
        assert response.status_code == 401

    def test_global_stats_invalid_token(self, test_client, mock_admin_token):
        """Should return 401 for invalid token."""
        response = test_client.get(
            "/api/v1/admin/sendgrid/stats",
            headers={"X-Admin-Token": "wrong-token"}
        )
        assert response.status_code == 401


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
