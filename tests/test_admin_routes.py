"""
Admin Routes Unit Tests

Comprehensive tests for admin API endpoints:
- GET /api/v1/admin/tenants
- GET /api/v1/admin/tenants/summary
- GET /api/v1/admin/tenants/{tenant_id}
- GET /api/v1/admin/tenants/{tenant_id}/usage
- GET /api/v1/admin/usage/summary
- GET /api/v1/admin/health
- POST /api/v1/admin/create-test-user
- GET /api/v1/admin/diagnostics/quotes
- POST /api/v1/admin/provision/vapi
- GET /api/v1/admin/provision/vapi/{tenant_id}
- PATCH /api/v1/admin/provision/vapi/{tenant_id}/config

Uses FastAPI TestClient with mocked dependencies.
These tests verify:
1. Admin token validation (503 when unconfigured, 401 when missing/invalid)
2. Endpoint structure and HTTP methods
3. Request validation
4. Response formats
5. Error handling
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import os


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
    config.name = "Test Tenant"
    config.short_name = "test"
    config.company_name = "Test Company"
    config.currency = "USD"
    config.timezone = "UTC"
    config.destinations = ["Cape Town", "Kruger"]
    config.destination_names = ["Cape Town", "Kruger"]
    config.consultants = []
    config.gcp_project_id = "test-project"
    config.gcp_region = "us-central1"
    config.dataset_name = "test_dataset"
    config.supabase_url = "https://test.supabase.co"
    config.supabase_service_key = "test-service-key"
    config.vapi_api_key = "test-vapi-key"
    config.vapi_assistant_id = "asst-123"
    config.vapi_outbound_assistant_id = "asst-456"
    config.vapi_phone_number_id = "phone-123"
    config.sendgrid_api_key = "SG.test-key"
    config.sendgrid_from_email = "test@example.com"
    config.primary_email = "support@example.com"
    return config


# ==================== Admin Token Validation Tests ====================

class TestAdminTokenValidation:
    """Test admin token authentication."""

    def test_admin_endpoint_without_token_configured_returns_503(self, test_client):
        """When ADMIN_API_TOKEN is not set, should return 503."""
        # Ensure no admin token is set
        with patch.dict(os.environ, {"ADMIN_API_TOKEN": ""}, clear=False):
            response = test_client.get(
                "/api/v1/admin/tenants",
                headers={"X-Admin-Token": "any-token"}
            )
            assert response.status_code == 503
            assert "not configured" in response.json()["detail"].lower()

    def test_admin_endpoint_without_header_returns_401(self, test_client, mock_admin_token):
        """When X-Admin-Token header is missing, should return 401."""
        response = test_client.get("/api/v1/admin/tenants")
        assert response.status_code == 401
        assert "header required" in response.json()["detail"].lower()

    def test_admin_endpoint_with_invalid_token_returns_401(self, test_client, mock_admin_token):
        """When X-Admin-Token header has wrong value, should return 401."""
        response = test_client.get(
            "/api/v1/admin/tenants",
            headers={"X-Admin-Token": "wrong-token"}
        )
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()


# ==================== List Tenants Tests ====================

class TestListTenantsEndpoint:
    """Test GET /api/v1/admin/tenants endpoint."""

    def test_list_tenants_returns_list(self, test_client, admin_headers):
        """GET /tenants should return tenant list."""
        response = test_client.get("/api/v1/admin/tenants", headers=admin_headers)
        # Should succeed if clients dir exists, may be empty
        assert response.status_code == 200
        data = response.json()
        assert "tenants" in data
        assert "count" in data
        assert isinstance(data["tenants"], list)

    def test_list_tenants_response_structure(self, test_client, admin_headers):
        """Each tenant in response should have expected fields."""
        with patch("src.api.admin_routes.Path") as mock_path:
            mock_clients = MagicMock()
            mock_clients.exists.return_value = True
            mock_client_dir = MagicMock()
            mock_client_dir.is_dir.return_value = True
            mock_client_dir.name = "test_tenant"
            mock_config_file = MagicMock()
            mock_config_file.exists.return_value = True
            mock_client_dir.__truediv__ = MagicMock(return_value=mock_config_file)
            mock_clients.iterdir.return_value = [mock_client_dir]
            mock_path.return_value = mock_clients

            with patch("src.api.admin_routes.ClientConfig") as mock_config_class:
                mock_config = MagicMock()
                mock_config.company_name = "Test Company"
                mock_config.currency = "USD"
                mock_config.destination_names = ["Cape Town"]
                mock_config.vapi_api_key = "key"
                mock_config.sendgrid_api_key = "key"
                mock_config_class.return_value = mock_config

                response = test_client.get("/api/v1/admin/tenants", headers=admin_headers)
                assert response.status_code == 200


# ==================== Tenant Summary Tests ====================

class TestTenantsSummaryEndpoint:
    """Test GET /api/v1/admin/tenants/summary endpoint."""

    def test_get_tenants_summary(self, test_client, admin_headers):
        """GET /tenants/summary should return summary list."""
        with patch("src.api.admin_routes.list_clients") as mock_list:
            mock_list.return_value = []  # No tenants
            response = test_client.get("/api/v1/admin/tenants/summary", headers=admin_headers)
            assert response.status_code == 200
            data = response.json()
            assert "tenants" in data
            assert "count" in data

    def test_get_tenants_summary_with_tenants(self, test_client, admin_headers, mock_client_config):
        """Summary should include tenant details."""
        with patch("src.api.admin_routes.list_clients") as mock_list:
            mock_list.return_value = ["test_tenant"]
            with patch("src.api.admin_routes.ClientConfig") as mock_config_class:
                mock_config_class.return_value = mock_client_config

                response = test_client.get("/api/v1/admin/tenants/summary", headers=admin_headers)
                assert response.status_code == 200
                data = response.json()
                assert data["count"] >= 0


# ==================== Tenant Detail Tests ====================

class TestTenantDetailEndpoint:
    """Test GET /api/v1/admin/tenants/{tenant_id} endpoint."""

    def test_get_tenant_details_not_found(self, test_client, admin_headers):
        """GET /tenants/{id} should return 404 for non-existent tenant."""
        with patch("src.api.admin_routes.ClientConfig") as mock_config_class:
            mock_config_class.side_effect = FileNotFoundError("Tenant not found")

            response = test_client.get(
                "/api/v1/admin/tenants/nonexistent",
                headers=admin_headers
            )
            assert response.status_code == 404

    def test_get_tenant_details_success(self, test_client, admin_headers, mock_client_config):
        """GET /tenants/{id} should return tenant config details."""
        with patch("src.api.admin_routes.ClientConfig") as mock_config_class:
            mock_config_class.return_value = mock_client_config
            with patch("src.api.admin_routes.get_bigquery_destinations") as mock_bq:
                mock_bq.return_value = {
                    "destinations": [],
                    "total_destinations": 0,
                    "total_hotels": 0,
                    "total_rates": 0
                }

                response = test_client.get(
                    "/api/v1/admin/tenants/test_tenant",
                    headers=admin_headers
                )
                assert response.status_code == 200
                data = response.json()
                assert "tenant_id" in data
                assert "client" in data
                assert "infrastructure" in data


# ==================== Tenant Usage Tests ====================

class TestTenantUsageEndpoint:
    """Test GET /api/v1/admin/tenants/{tenant_id}/usage endpoint."""

    def test_get_tenant_usage_not_found(self, test_client, admin_headers):
        """GET /tenants/{id}/usage should return 404 for non-existent tenant."""
        with patch("src.api.admin_routes.ClientConfig") as mock_config_class:
            mock_config_class.side_effect = FileNotFoundError("Tenant not found")

            response = test_client.get(
                "/api/v1/admin/tenants/nonexistent/usage",
                headers=admin_headers
            )
            assert response.status_code == 404

    def test_get_tenant_usage_success(self, test_client, admin_headers, mock_client_config):
        """GET /tenants/{id}/usage should return usage statistics."""
        with patch("src.api.admin_routes.ClientConfig") as mock_config_class:
            mock_config_class.return_value = mock_client_config
            # SupabaseTool is imported inline, so we patch it at the module level
            with patch("src.tools.supabase_tool.SupabaseTool") as mock_supabase:
                mock_client = MagicMock()
                # Mock chainable queries
                mock_table = MagicMock()
                mock_table.select.return_value = mock_table
                mock_table.gte.return_value = mock_table
                mock_table.eq.return_value = mock_table
                mock_result = MagicMock()
                mock_result.count = 10
                mock_result.data = []
                mock_table.execute.return_value = mock_result
                mock_client.table.return_value = mock_table
                mock_supabase.return_value.client = mock_client

                response = test_client.get(
                    "/api/v1/admin/tenants/test_tenant/usage?period=month",
                    headers=admin_headers
                )
                # Endpoint returns stats even on error (fallback to empty stats)
                assert response.status_code == 200
                data = response.json()
                assert "client_id" in data
                assert "period" in data


# ==================== Usage Summary Tests ====================

class TestUsageSummaryEndpoint:
    """Test GET /api/v1/admin/usage/summary endpoint."""

    def test_get_usage_summary(self, test_client, admin_headers):
        """GET /usage/summary should return aggregated usage."""
        with patch("src.api.admin_routes.list_clients") as mock_list:
            mock_list.return_value = []  # No tenants

            response = test_client.get(
                "/api/v1/admin/usage/summary?period=month",
                headers=admin_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert "period" in data
            assert "totals" in data
            assert "by_tenant" in data


# ==================== Health Endpoint Tests ====================

class TestHealthEndpoint:
    """Test GET /api/v1/admin/health endpoint."""

    def test_get_health_status(self, test_client, admin_headers):
        """GET /health should return system health."""
        with patch("src.api.admin_routes.list_clients") as mock_list:
            mock_list.return_value = []  # No tenants

            response = test_client.get("/api/v1/admin/health", headers=admin_headers)
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "total_tenants" in data
            assert "database_status" in data
            assert "timestamp" in data


# ==================== Create Test User Tests ====================

class TestCreateTestUserEndpoint:
    """Test POST /api/v1/admin/create-test-user endpoint."""

    def test_create_test_user_missing_tenant(self, test_client, admin_headers):
        """POST /create-test-user should return 404 for unknown tenant."""
        # get_config is imported from config.loader, so patch at import location
        with patch("config.loader.get_config") as mock_get_config:
            mock_get_config.side_effect = FileNotFoundError("Tenant not found")

            response = test_client.post(
                "/api/v1/admin/create-test-user",
                headers=admin_headers,
                json={
                    "tenant_id": "nonexistent",
                    "email": "test@example.com",
                    "password": "password123",
                    "name": "Test User",
                    "role": "admin"
                }
            )
            assert response.status_code == 404

    def test_create_test_user_validation(self, test_client, admin_headers):
        """POST /create-test-user should validate request body."""
        response = test_client.post(
            "/api/v1/admin/create-test-user",
            headers=admin_headers,
            json={}  # Missing required fields
        )
        assert response.status_code == 422  # Validation error


# ==================== Diagnostics Tests ====================

class TestDiagnosticsEndpoint:
    """Test GET /api/v1/admin/diagnostics/quotes endpoint."""

    @pytest.mark.skip(reason="SupabaseService module may not exist in current codebase")
    def test_get_diagnostics_quotes_without_supabase(self, test_client, admin_headers):
        """GET /diagnostics/quotes should return 500 when Supabase not configured."""
        # When SupabaseService().client is None, endpoint returns 500
        response = test_client.get(
            "/api/v1/admin/diagnostics/quotes",
            headers=admin_headers
        )
        # Without Supabase configured, we expect either 500 or success with empty data
        # The endpoint handles missing service gracefully
        assert response.status_code in [200, 500]

    @pytest.mark.skip(reason="SupabaseService module may not exist in current codebase")
    def test_get_diagnostics_quotes_accepts_tenant_filter(self, test_client, admin_headers):
        """GET /diagnostics/quotes should accept tenant_id query param."""
        response = test_client.get(
            "/api/v1/admin/diagnostics/quotes?tenant_id=test&limit=5",
            headers=admin_headers
        )
        # May fail due to missing Supabase but request format is valid
        assert response.status_code in [200, 500]

    def test_diagnostics_quotes_requires_admin_auth(self, test_client):
        """GET /diagnostics/quotes should require admin token."""
        response = test_client.get("/api/v1/admin/diagnostics/quotes")
        # 401 if no token, 503 if admin not configured
        assert response.status_code in [401, 503]


# ==================== VAPI Provisioning Tests ====================

class TestVAPIProvisioningEndpoints:
    """Test VAPI provisioning endpoints."""

    def test_get_vapi_status_not_found(self, test_client, admin_headers):
        """GET /provision/vapi/{id} should return 404 for unknown tenant."""
        with patch("src.api.admin_routes.ClientConfig") as mock_config_class:
            mock_config_class.side_effect = FileNotFoundError("Tenant not found")

            response = test_client.get(
                "/api/v1/admin/provision/vapi/nonexistent",
                headers=admin_headers
            )
            assert response.status_code == 404

    def test_get_vapi_status_success(self, test_client, admin_headers, mock_client_config):
        """GET /provision/vapi/{id} should return VAPI config."""
        with patch("src.api.admin_routes.ClientConfig") as mock_config_class:
            mock_config_class.return_value = mock_client_config

            response = test_client.get(
                "/api/v1/admin/provision/vapi/test_tenant",
                headers=admin_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert "tenant_id" in data
            assert "vapi_configured" in data
            assert "ready_for_calls" in data

    def test_provision_vapi_validation(self, test_client, admin_headers):
        """POST /provision/vapi should validate request body."""
        response = test_client.post(
            "/api/v1/admin/provision/vapi",
            headers=admin_headers,
            json={}  # Missing required tenant_id
        )
        # Should fail validation (422) or tenant not found (404)
        assert response.status_code in [404, 422]

    @pytest.mark.skip(reason="VAPIProvisioner module not present in current codebase")
    def test_provision_vapi_tenant_not_found(self, test_client, admin_headers):
        """POST /provision/vapi should return 404 for unknown tenant."""
        with patch("src.api.admin_routes.ClientConfig") as mock_config_class:
            mock_config_class.side_effect = FileNotFoundError("Tenant not found")

            response = test_client.post(
                "/api/v1/admin/provision/vapi",
                headers=admin_headers,
                json={
                    "tenant_id": "nonexistent_tenant_xyz",
                    "company_name": "Test",
                    "country_code": "ZA",
                    "buy_phone_number": False
                }
            )
            # Should return 404 for tenant not found
            assert response.status_code == 404

    def test_provision_vapi_requires_admin_auth(self, test_client):
        """POST /provision/vapi should require admin token."""
        response = test_client.post(
            "/api/v1/admin/provision/vapi",
            json={"tenant_id": "test", "company_name": "Test"}
        )
        # 401 if no token, 503 if admin not configured
        assert response.status_code in [401, 503]

    def test_update_vapi_config_not_found(self, test_client, admin_headers):
        """PATCH /provision/vapi/{id}/config should return 404 for unknown tenant."""
        with patch("src.api.admin_routes.ClientConfig") as mock_config_class:
            mock_config_class.side_effect = FileNotFoundError("Tenant not found")

            response = test_client.patch(
                "/api/v1/admin/provision/vapi/nonexistent/config",
                headers=admin_headers,
                json={"vapi_api_key": "new-key"}
            )
            assert response.status_code == 404


# ==================== Phone Search Tests ====================

class TestPhoneSearchEndpoint:
    """Test POST /api/v1/admin/provision/phone/search endpoint."""

    def test_search_phones_missing_credentials(self, test_client, admin_headers):
        """POST /provision/phone/search should fail without credentials."""
        with patch.dict(os.environ, {
            "TWILIO_ACCOUNT_SID": "",
            "TWILIO_AUTH_TOKEN": "",
            "VAPI_API_KEY": ""
        }, clear=False):
            response = test_client.post(
                "/api/v1/admin/provision/phone/search",
                headers=admin_headers,
                json={"country_code": "ZA", "limit": 5}
            )
            assert response.status_code == 500
            assert "credentials not configured" in response.json()["detail"].lower()


# ==================== Admin Token Timing Safety Tests ====================

class TestAdminTokenTimingSafety:
    """Tests for timing-safe admin token verification."""

    def test_admin_token_uses_constant_time_comparison(self):
        """Verify that hmac.compare_digest is used for token comparison."""
        import inspect
        from src.api.admin_routes import verify_admin_token

        # Get the source code of the function
        source = inspect.getsource(verify_admin_token)

        # Verify it uses hmac.compare_digest
        assert 'hmac.compare_digest' in source, \
            "verify_admin_token must use hmac.compare_digest for constant-time comparison"

    def test_admin_token_rejects_wrong_token_with_401(self):
        """Verify wrong tokens are still rejected."""
        from fastapi import HTTPException
        import pytest
        from src.api.admin_routes import verify_admin_token

        with patch.dict(os.environ, {'ADMIN_API_TOKEN': 'correct-secret-token'}):
            with pytest.raises(HTTPException) as exc_info:
                verify_admin_token('wrong-token')

            assert exc_info.value.status_code == 401
            assert 'Invalid admin token' in exc_info.value.detail

    def test_admin_token_accepts_correct_token(self):
        """Verify correct tokens are accepted."""
        from src.api.admin_routes import verify_admin_token

        with patch.dict(os.environ, {'ADMIN_API_TOKEN': 'correct-secret-token'}):
            result = verify_admin_token('correct-secret-token')
            assert result is True

    def test_admin_token_handles_unicode(self):
        """Verify token comparison works with unicode characters."""
        from src.api.admin_routes import verify_admin_token

        unicode_token = 'secret-token-with-unicode-\u00e9\u00e8\u00ea'

        with patch.dict(os.environ, {'ADMIN_API_TOKEN': unicode_token}):
            result = verify_admin_token(unicode_token)
            assert result is True

    def test_admin_token_no_vulnerable_comparison_in_source(self):
        """Ensure direct string comparison operators are not used for token check."""
        import inspect
        from src.api.admin_routes import verify_admin_token

        source = inspect.getsource(verify_admin_token)

        # The token comparison should NOT use != or == directly on the tokens
        # We check that the pattern "x_admin_token != admin_token" is NOT present
        assert 'x_admin_token != admin_token' not in source, \
            "Direct string comparison (!=) should not be used for token comparison"
        assert 'x_admin_token == admin_token' not in source, \
            "Direct string comparison (==) should not be used for token comparison"
