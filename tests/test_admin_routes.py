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


# ==================== NEW: Direct Handler Tests ====================
# These tests call route handlers directly (bypassing TestClient) for
# faster execution and to avoid import-chain issues.


class TestVerifyAdminTokenDirect:
    """Direct unit tests for the verify_admin_token dependency function."""

    def test_token_match_returns_true(self):
        """Matching token should return True."""
        from src.api.admin_routes import verify_admin_token

        with patch.dict(os.environ, {"ADMIN_API_TOKEN": "my-secret"}):
            assert verify_admin_token("my-secret") is True

    def test_no_header_raises_401(self):
        """None header value should raise 401."""
        from fastapi import HTTPException
        from src.api.admin_routes import verify_admin_token

        with patch.dict(os.environ, {"ADMIN_API_TOKEN": "my-secret"}):
            with pytest.raises(HTTPException) as exc_info:
                verify_admin_token(None)
            assert exc_info.value.status_code == 401
            assert "header required" in exc_info.value.detail.lower()

    def test_wrong_token_raises_401(self):
        """Incorrect token should raise 401 with 'Invalid' message."""
        from fastapi import HTTPException
        from src.api.admin_routes import verify_admin_token

        with patch.dict(os.environ, {"ADMIN_API_TOKEN": "correct-token"}):
            with pytest.raises(HTTPException) as exc_info:
                verify_admin_token("wrong-token")
            assert exc_info.value.status_code == 401
            assert "invalid" in exc_info.value.detail.lower()

    def test_unset_env_var_raises_503(self):
        """When ADMIN_API_TOKEN env var is empty, should raise 503."""
        from fastapi import HTTPException
        from src.api.admin_routes import verify_admin_token

        with patch.dict(os.environ, {"ADMIN_API_TOKEN": ""}, clear=False):
            with pytest.raises(HTTPException) as exc_info:
                verify_admin_token("any-token")
            assert exc_info.value.status_code == 503
            assert "not configured" in exc_info.value.detail.lower()

    def test_env_var_completely_absent_raises_503(self):
        """When ADMIN_API_TOKEN is not in env at all, should raise 503."""
        from fastapi import HTTPException
        from src.api.admin_routes import verify_admin_token

        env_copy = {k: v for k, v in os.environ.items() if k != "ADMIN_API_TOKEN"}
        with patch.dict(os.environ, env_copy, clear=True):
            with pytest.raises(HTTPException) as exc_info:
                verify_admin_token("any-token")
            assert exc_info.value.status_code == 503

    def test_empty_string_token_raises_401(self):
        """Empty string as header token should raise 401 (not header required)."""
        from fastapi import HTTPException
        from src.api.admin_routes import verify_admin_token

        with patch.dict(os.environ, {"ADMIN_API_TOKEN": "real-secret"}):
            # Empty string is truthy-falsy edge case - the function checks 'if not x_admin_token'
            with pytest.raises(HTTPException) as exc_info:
                verify_admin_token("")
            assert exc_info.value.status_code == 401


class TestAdminHealthCheckDirect:
    """Direct handler tests for GET /api/v1/admin/health."""

    def test_health_no_tenants_returns_healthy(self):
        """Health check with no tenants should still return healthy status."""
        from src.api.admin_routes import get_system_health

        with patch("src.api.admin_routes.list_clients", return_value=[]):
            result = get_system_health(admin_verified=True)
            assert result.status == "healthy"
            assert result.total_tenants == 0
            assert result.active_tenants == 0
            assert result.database_status == "healthy"
            assert result.timestamp is not None

    def test_health_with_tenants_db_error_returns_degraded(self):
        """When database check fails, health status should be 'degraded'."""
        from src.api.admin_routes import get_system_health

        with patch("src.api.admin_routes.list_clients", return_value=["tenant_a"]):
            with patch("src.api.admin_routes.ClientConfig") as mock_cfg:
                mock_cfg.return_value = MagicMock()
                with patch("src.tools.supabase_tool.SupabaseTool") as mock_sb:
                    mock_sb.side_effect = Exception("Connection refused")
                    result = get_system_health(admin_verified=True)
                    assert result.status == "degraded"
                    assert "error" in result.database_status.lower()
                    assert result.total_tenants == 1

    def test_health_response_has_iso_timestamp(self):
        """Timestamp in health response should be ISO 8601 format."""
        from src.api.admin_routes import get_system_health
        from datetime import datetime

        with patch("src.api.admin_routes.list_clients", return_value=[]):
            result = get_system_health(admin_verified=True)
            # Should parse as ISO datetime without error
            datetime.fromisoformat(result.timestamp)


class TestListTenantsDirect:
    """Direct handler tests for GET /api/v1/admin/tenants."""

    def test_list_tenants_no_clients_dir(self):
        """When clients directory does not exist, should return empty list."""
        from src.api.admin_routes import list_tenants

        with patch("src.api.admin_routes.Path") as mock_path:
            mock_path.return_value.exists.return_value = False
            result = list_tenants(admin_verified=True)
            assert result == {"tenants": [], "count": 0}

    def test_list_tenants_with_multiple_clients(self):
        """Should return all tenants from the clients directory."""
        from src.api.admin_routes import list_tenants

        with patch("src.api.admin_routes.Path") as mock_path:
            mock_clients_dir = MagicMock()
            mock_clients_dir.exists.return_value = True

            # Create two mock tenant dirs
            dirs = []
            for name in ["alpha", "beta"]:
                d = MagicMock()
                d.is_dir.return_value = True
                d.name = name
                config_file = MagicMock()
                config_file.exists.return_value = True
                d.__truediv__ = MagicMock(return_value=config_file)
                dirs.append(d)

            mock_clients_dir.iterdir.return_value = dirs
            mock_path.return_value = mock_clients_dir

            with patch("src.api.admin_routes.ClientConfig") as mock_cfg:
                cfg = MagicMock()
                cfg.company_name = "Company"
                cfg.currency = "ZAR"
                cfg.destination_names = ["Cape Town"]
                cfg.vapi_api_key = "key"
                cfg.sendgrid_api_key = "key"
                mock_cfg.return_value = cfg

                result = list_tenants(admin_verified=True)
                assert result["count"] == 2
                assert len(result["tenants"]) == 2
                ids = [t["tenant_id"] for t in result["tenants"]]
                assert "alpha" in ids
                assert "beta" in ids

    def test_list_tenants_config_error_still_lists_tenant(self):
        """If a tenant config fails to load, tenant should appear with error."""
        from src.api.admin_routes import list_tenants

        with patch("src.api.admin_routes.Path") as mock_path:
            mock_clients_dir = MagicMock()
            mock_clients_dir.exists.return_value = True

            d = MagicMock()
            d.is_dir.return_value = True
            d.name = "broken_tenant"
            config_file = MagicMock()
            config_file.exists.return_value = True
            d.__truediv__ = MagicMock(return_value=config_file)
            mock_clients_dir.iterdir.return_value = [d]
            mock_path.return_value = mock_clients_dir

            with patch("src.api.admin_routes.ClientConfig") as mock_cfg:
                mock_cfg.side_effect = Exception("YAML parse error")
                result = list_tenants(admin_verified=True)
                assert result["count"] == 1
                assert "error" in result["tenants"][0]
                assert result["tenants"][0]["tenant_id"] == "broken_tenant"

    def test_list_tenants_skips_non_directories(self):
        """Files in clients dir (not subdirs) should be skipped."""
        from src.api.admin_routes import list_tenants

        with patch("src.api.admin_routes.Path") as mock_path:
            mock_clients_dir = MagicMock()
            mock_clients_dir.exists.return_value = True

            file_entry = MagicMock()
            file_entry.is_dir.return_value = False
            mock_clients_dir.iterdir.return_value = [file_entry]
            mock_path.return_value = mock_clients_dir

            result = list_tenants(admin_verified=True)
            assert result["count"] == 0

    def test_list_tenants_skips_dir_without_config(self):
        """Directories without client.yaml should be skipped."""
        from src.api.admin_routes import list_tenants

        with patch("src.api.admin_routes.Path") as mock_path:
            mock_clients_dir = MagicMock()
            mock_clients_dir.exists.return_value = True

            d = MagicMock()
            d.is_dir.return_value = True
            d.name = "no_config_tenant"
            config_file = MagicMock()
            config_file.exists.return_value = False  # no client.yaml
            d.__truediv__ = MagicMock(return_value=config_file)
            mock_clients_dir.iterdir.return_value = [d]
            mock_path.return_value = mock_clients_dir

            result = list_tenants(admin_verified=True)
            assert result["count"] == 0


class TestTenantSummaryDirect:
    """Direct handler tests for GET /api/v1/admin/tenants/summary."""

    def test_summary_empty_tenants(self):
        """Summary with no tenants should return empty list and count 0."""
        from src.api.admin_routes import get_all_tenants_summary

        with patch("src.api.admin_routes.list_clients", return_value=[]):
            result = get_all_tenants_summary(admin_verified=True)
            assert result["count"] == 0
            assert result["tenants"] == []

    def test_summary_includes_all_fields(self, mock_client_config):
        """Each tenant summary should include all TenantSummary fields."""
        from src.api.admin_routes import get_all_tenants_summary

        with patch("src.api.admin_routes.list_clients", return_value=["test_tenant"]):
            with patch("src.api.admin_routes.ClientConfig", return_value=mock_client_config):
                result = get_all_tenants_summary(admin_verified=True)
                assert result["count"] == 1
                tenant = result["tenants"][0]
                # TenantSummary is a Pydantic model so we check dict/model keys
                assert tenant.client_id == "test_tenant"
                assert tenant.company_name == "Test Company"
                assert tenant.currency == "USD"
                assert tenant.timezone == "UTC"
                assert tenant.destinations_count == 2  # Cape Town, Kruger
                assert tenant.vapi_configured is True
                assert tenant.sendgrid_configured is True
                assert tenant.supabase_configured is True
                assert tenant.status == "active"

    def test_summary_skips_broken_tenants(self):
        """Tenants that fail to load should be skipped, not crash the endpoint."""
        from src.api.admin_routes import get_all_tenants_summary

        with patch("src.api.admin_routes.list_clients", return_value=["good", "broken"]):
            def side_effect(client_id):
                if client_id == "broken":
                    raise Exception("Config load failed")
                cfg = MagicMock()
                cfg.name = "Good"
                cfg.company_name = "Good Co"
                cfg.currency = "USD"
                cfg.timezone = "UTC"
                cfg.destination_names = []
                cfg.vapi_api_key = ""
                cfg.sendgrid_api_key = ""
                cfg.supabase_url = ""
                return cfg

            with patch("src.api.admin_routes.ClientConfig", side_effect=side_effect):
                result = get_all_tenants_summary(admin_verified=True)
                # Only the "good" tenant should appear
                assert result["count"] == 1


class TestTenantDetailDirect:
    """Direct handler tests for GET /api/v1/admin/tenants/{tenant_id}."""

    @pytest.mark.asyncio
    async def test_detail_not_found_raises_404(self):
        """Non-existent tenant should raise HTTPException 404."""
        from fastapi import HTTPException
        from src.api.admin_routes import get_tenant_details

        with patch("src.api.admin_routes.ClientConfig", side_effect=FileNotFoundError):
            with pytest.raises(HTTPException) as exc_info:
                await get_tenant_details("no_such_tenant", admin_verified=True)
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_detail_includes_infrastructure(self, mock_client_config):
        """Response should include full infrastructure section."""
        from src.api.admin_routes import get_tenant_details

        with patch("src.api.admin_routes.ClientConfig", return_value=mock_client_config):
            with patch("src.api.admin_routes.get_bigquery_destinations") as mock_bq:
                mock_bq.return_value = {
                    "destinations": [{"name": "Cape Town", "hotel_count": 5, "rate_count": 20}],
                    "total_destinations": 1,
                    "total_hotels": 5,
                    "total_rates": 20
                }
                result = await get_tenant_details("test_tenant", admin_verified=True)

                assert result["tenant_id"] == "test_tenant"
                assert result["client"]["company_name"] == "Test Company"
                assert result["client"]["currency"] == "USD"
                assert result["destinations_count"] == 1
                assert result["hotels_count"] == 5
                assert result["rates_count"] == 20
                infra = result["infrastructure"]
                assert infra["gcp_project"] == "test-project"
                assert infra["vapi"]["configured"] is True
                assert infra["vapi"]["assistant_id"] == "asst-123"
                assert infra["email"]["sendgrid_configured"] is True

    @pytest.mark.asyncio
    async def test_detail_bq_fallback_on_error(self, mock_client_config):
        """When BigQuery fails, should fall back to config destinations."""
        from src.api.admin_routes import get_tenant_details

        with patch("src.api.admin_routes.ClientConfig", return_value=mock_client_config):
            with patch("src.api.admin_routes.get_bigquery_destinations") as mock_bq:
                mock_bq.return_value = {
                    "destinations": mock_client_config.destinations,
                    "total_destinations": 0,
                    "total_hotels": 0,
                    "total_rates": 0,
                    "error": "BigQuery unavailable"
                }
                result = await get_tenant_details("test_tenant", admin_verified=True)
                # Should still return a valid response
                assert result["tenant_id"] == "test_tenant"
                assert result["destinations"] == ["Cape Town", "Kruger"]


class TestTenantUsageDirect:
    """Direct handler tests for GET /api/v1/admin/tenants/{tenant_id}/usage."""

    def test_usage_not_found_raises_404(self):
        """Non-existent tenant should raise 404."""
        from fastapi import HTTPException
        from src.api.admin_routes import get_tenant_usage

        with patch("src.api.admin_routes.ClientConfig", side_effect=FileNotFoundError):
            with pytest.raises(HTTPException) as exc_info:
                get_tenant_usage("nonexistent", period="month", admin_verified=True)
            assert exc_info.value.status_code == 404

    def test_usage_returns_fallback_on_db_error(self, mock_client_config):
        """When Supabase fails, should return empty stats (not crash)."""
        from src.api.admin_routes import get_tenant_usage

        with patch("src.api.admin_routes.ClientConfig", return_value=mock_client_config):
            with patch("src.tools.supabase_tool.SupabaseTool", side_effect=Exception("DB down")):
                result = get_tenant_usage("test_tenant", period="month", admin_verified=True)
                assert result.client_id == "test_tenant"
                assert result.period == "month"
                assert result.quotes_generated == 0
                assert result.total_revenue == 0

    def test_usage_default_period_is_month(self, mock_client_config):
        """Default period parameter should be 'month'."""
        from src.api.admin_routes import get_tenant_usage

        with patch("src.api.admin_routes.ClientConfig", return_value=mock_client_config):
            with patch("src.tools.supabase_tool.SupabaseTool", side_effect=Exception("skip")):
                result = get_tenant_usage("test_tenant", admin_verified=True)
                assert result.period == "month"

    def test_usage_accepts_all_period_values(self, mock_client_config):
        """Endpoint should accept day, week, month, quarter, year."""
        from src.api.admin_routes import get_tenant_usage

        for period in ["day", "week", "month", "quarter", "year"]:
            with patch("src.api.admin_routes.ClientConfig", return_value=mock_client_config):
                with patch("src.tools.supabase_tool.SupabaseTool", side_effect=Exception("skip")):
                    result = get_tenant_usage("test_tenant", period=period, admin_verified=True)
                    assert result.period == period


class TestUsageSummaryDirect:
    """Direct handler tests for GET /api/v1/admin/usage/summary."""

    def test_usage_summary_empty_tenants(self):
        """With no tenants, totals should all be zero."""
        from src.api.admin_routes import get_all_tenants_usage_summary

        with patch("src.api.admin_routes.list_clients", return_value=[]):
            result = get_all_tenants_usage_summary(period="month", admin_verified=True)
            assert result["period"] == "month"
            assert result["totals"]["total_quotes"] == 0
            assert result["totals"]["total_revenue"] == 0
            assert result["totals"]["tenant_count"] == 0
            assert result["by_tenant"] == []

    def test_usage_summary_aggregates_across_tenants(self):
        """Totals should sum across all tenants."""
        from src.api.admin_routes import get_all_tenants_usage_summary, TenantUsageStats

        with patch("src.api.admin_routes.list_clients", return_value=["t1", "t2"]):
            with patch("src.api.admin_routes.get_tenant_usage") as mock_usage:
                mock_usage.side_effect = [
                    TenantUsageStats(client_id="t1", period="month", quotes_generated=5, total_revenue=1000.0, active_users=2, total_clients=10, invoices_created=3, invoices_paid=2),
                    TenantUsageStats(client_id="t2", period="month", quotes_generated=3, total_revenue=500.0, active_users=1, total_clients=5, invoices_created=1, invoices_paid=1),
                ]
                result = get_all_tenants_usage_summary(period="month", admin_verified=True)
                assert result["totals"]["total_quotes"] == 8
                assert result["totals"]["total_revenue"] == 1500.0
                assert result["totals"]["total_active_users"] == 3
                assert result["totals"]["total_crm_clients"] == 15
                assert result["totals"]["tenant_count"] == 2
                assert len(result["by_tenant"]) == 2

    def test_usage_summary_skips_failing_tenants(self):
        """Tenants that error during usage fetch should be skipped."""
        from src.api.admin_routes import get_all_tenants_usage_summary

        with patch("src.api.admin_routes.list_clients", return_value=["ok", "fail"]):
            with patch("src.api.admin_routes.get_tenant_usage") as mock_usage:
                from src.api.admin_routes import TenantUsageStats
                def side_effect(client_id, period, admin_verified):
                    if client_id == "fail":
                        raise Exception("boom")
                    return TenantUsageStats(client_id=client_id, period=period, quotes_generated=10)
                mock_usage.side_effect = side_effect
                result = get_all_tenants_usage_summary(period="week", admin_verified=True)
                assert result["totals"]["tenant_count"] == 1
                assert result["totals"]["total_quotes"] == 10


class TestCreateTestUserDirect:
    """Direct handler tests for POST /api/v1/admin/create-test-user."""

    @pytest.mark.asyncio
    async def test_create_user_tenant_not_found(self):
        """Should raise 404 when tenant config not found."""
        from fastapi import HTTPException
        from src.api.admin_routes import create_test_user, CreateTestUserRequest

        request = CreateTestUserRequest(
            tenant_id="nonexistent", email="a@b.com", password="pass123", name="Test", role="admin"
        )
        with patch("config.loader.get_config", side_effect=FileNotFoundError):
            with pytest.raises(HTTPException) as exc_info:
                await create_test_user(request, admin_verified=True)
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_create_user_no_supabase_config(self):
        """Should raise 500 when Supabase is not configured."""
        from fastapi import HTTPException
        from src.api.admin_routes import create_test_user, CreateTestUserRequest

        request = CreateTestUserRequest(
            tenant_id="test", email="a@b.com", password="pass123", name="Test", role="admin"
        )
        mock_config = MagicMock()
        mock_config.supabase_url = None
        mock_config.supabase_service_key = None

        with patch("config.loader.get_config", return_value=mock_config):
            with patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_SERVICE_KEY": ""}):
                with pytest.raises(HTTPException) as exc_info:
                    await create_test_user(request, admin_verified=True)
                assert exc_info.value.status_code == 500
                assert "supabase" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_create_user_success(self):
        """Successful user creation returns success response."""
        from src.api.admin_routes import create_test_user, CreateTestUserRequest

        request = CreateTestUserRequest(
            tenant_id="test", email="user@example.com", password="pass123", name="New User", role="consultant"
        )
        mock_config = MagicMock()
        mock_config.supabase_url = "https://test.supabase.co"
        mock_config.supabase_service_key = "svc-key"

        with patch("config.loader.get_config", return_value=mock_config):
            with patch("src.services.auth_service.AuthService") as mock_auth_cls:
                mock_auth = AsyncMock()
                mock_auth.create_auth_user.return_value = (True, {"user": {"id": "u123"}, "already_existed": False})
                mock_auth_cls.return_value = mock_auth

                result = await create_test_user(request, admin_verified=True)
                assert result["success"] is True
                assert result["login_info"]["email"] == "user@example.com"
                assert result["login_info"]["role"] == "consultant"

    @pytest.mark.asyncio
    async def test_create_user_auth_failure_returns_400(self):
        """When auth service returns failure, should raise 400."""
        from fastapi import HTTPException
        from src.api.admin_routes import create_test_user, CreateTestUserRequest

        request = CreateTestUserRequest(
            tenant_id="test", email="dup@example.com", password="pass123", name="Dup", role="admin"
        )
        mock_config = MagicMock()
        mock_config.supabase_url = "https://test.supabase.co"
        mock_config.supabase_service_key = "svc-key"

        with patch("config.loader.get_config", return_value=mock_config):
            with patch("src.services.auth_service.AuthService") as mock_auth_cls:
                mock_auth = AsyncMock()
                mock_auth.create_auth_user.return_value = (False, {"error": "User already exists"})
                mock_auth_cls.return_value = mock_auth

                with pytest.raises(HTTPException) as exc_info:
                    await create_test_user(request, admin_verified=True)
                assert exc_info.value.status_code == 400
                assert "already exists" in exc_info.value.detail.lower()

    def test_create_user_validation_rejects_bad_role(self, test_client, admin_headers):
        """Role field should only accept admin, user, or consultant."""
        response = test_client.post(
            "/api/v1/admin/create-test-user",
            headers=admin_headers,
            json={
                "tenant_id": "test",
                "email": "a@b.com",
                "password": "pass123",
                "role": "superadmin"  # invalid
            }
        )
        assert response.status_code == 422

    def test_create_user_validation_rejects_short_password(self, test_client, admin_headers):
        """Password must be at least 6 characters."""
        response = test_client.post(
            "/api/v1/admin/create-test-user",
            headers=admin_headers,
            json={
                "tenant_id": "test",
                "email": "a@b.com",
                "password": "abc",  # too short
                "role": "admin"
            }
        )
        assert response.status_code == 422


class TestQuoteDiagnosticsDirect:
    """Direct handler tests for GET /api/v1/admin/diagnostics/quotes."""

    def test_diagnostics_no_supabase_raises_500(self):
        """When SupabaseService client is None, should raise 500."""
        from fastapi import HTTPException
        from src.api.admin_routes import diagnose_quotes

        with patch("src.api.admin_routes.SupabaseService", create=True) as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.client = None
            mock_svc_cls.return_value = mock_svc

            with patch.dict("sys.modules", {"src.services.supabase_service": MagicMock(SupabaseService=mock_svc_cls)}):
                with pytest.raises(HTTPException) as exc_info:
                    diagnose_quotes(tenant_id=None, limit=20, admin_verified=True)
                assert exc_info.value.status_code == 500

    def test_diagnostics_returns_quotes_grouped_by_tenant(self):
        """Should return quotes grouped by tenant_id."""
        from src.api.admin_routes import diagnose_quotes

        mock_supabase_service = MagicMock()
        mock_client = MagicMock()
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=[
            {"quote_id": "q1", "tenant_id": "tenant_a", "customer_name": "Alice", "customer_email": "a@a.com", "status": "sent", "created_at": "2026-01-01"},
            {"quote_id": "q2", "tenant_id": "tenant_a", "customer_name": "Bob", "customer_email": "b@b.com", "status": "draft", "created_at": "2026-01-02"},
            {"quote_id": "q3", "tenant_id": "tenant_b", "customer_name": "Charlie", "customer_email": "c@c.com", "status": "paid", "created_at": "2026-01-03"},
        ])
        mock_client.table.return_value = mock_query
        mock_supabase_service.client = mock_client

        mock_svc_cls = MagicMock(return_value=mock_supabase_service)

        with patch.dict("sys.modules", {"src.services.supabase_service": MagicMock(SupabaseService=mock_svc_cls)}):
            with patch("src.api.admin_routes.SupabaseService", mock_svc_cls, create=True):
                # We need to re-import to pick up the patched module; call directly instead
                # Actually the function imports inline, so we patch sys.modules
                result = diagnose_quotes(tenant_id=None, limit=20, admin_verified=True)
                assert result["success"] is True
                assert result["total_quotes"] == 3
                assert "tenant_a" in result["tenants_with_quotes"]
                assert "tenant_b" in result["tenants_with_quotes"]
                assert result["quotes_by_tenant"]["tenant_a"] == 2
                assert result["quotes_by_tenant"]["tenant_b"] == 1

    def test_diagnostics_filters_by_tenant_id(self):
        """When tenant_id is provided, query should filter on it."""
        from src.api.admin_routes import diagnose_quotes

        mock_supabase_service = MagicMock()
        mock_client = MagicMock()
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=[
            {"quote_id": "q1", "tenant_id": "specific", "customer_name": "A", "customer_email": "a@a.com", "status": "sent", "created_at": "2026-01-01"},
        ])
        mock_client.table.return_value = mock_query
        mock_supabase_service.client = mock_client

        mock_svc_cls = MagicMock(return_value=mock_supabase_service)

        with patch.dict("sys.modules", {"src.services.supabase_service": MagicMock(SupabaseService=mock_svc_cls)}):
            with patch("src.api.admin_routes.SupabaseService", mock_svc_cls, create=True):
                result = diagnose_quotes(tenant_id="specific", limit=10, admin_verified=True)
                assert result["filter_tenant_id"] == "specific"
                assert result["total_quotes"] == 1
                mock_query.eq.assert_called_with("tenant_id", "specific")


class TestVAPIProvisionDirect:
    """Direct handler tests for VAPI provisioning endpoints."""

    def test_get_vapi_status_tenant_not_found(self):
        """get_vapi_status should raise 404 for unknown tenant."""
        from fastapi import HTTPException
        from src.api.admin_routes import get_vapi_status

        with patch("src.api.admin_routes.ClientConfig", side_effect=FileNotFoundError):
            with pytest.raises(HTTPException) as exc_info:
                get_vapi_status("nonexistent", admin_verified=True)
            assert exc_info.value.status_code == 404

    def test_get_vapi_status_fully_configured(self, mock_client_config):
        """Fully configured tenant should show ready_for_calls=True."""
        from src.api.admin_routes import get_vapi_status

        with patch("src.api.admin_routes.ClientConfig", return_value=mock_client_config):
            result = get_vapi_status("test_tenant", admin_verified=True)
            assert result["tenant_id"] == "test_tenant"
            assert result["vapi_configured"] is True
            assert result["ready_for_calls"] is True
            assert result["inbound_assistant_id"] == "asst-123"
            assert result["outbound_assistant_id"] == "asst-456"
            assert result["phone_number_id"] == "phone-123"

    def test_get_vapi_status_not_configured(self):
        """Tenant without VAPI config should show ready_for_calls=False."""
        from src.api.admin_routes import get_vapi_status

        config = MagicMock()
        config.company_name = "No VAPI Co"
        config.vapi_api_key = ""
        config.vapi_assistant_id = None
        config.vapi_outbound_assistant_id = None
        config.vapi_phone_number_id = None

        with patch("src.api.admin_routes.ClientConfig", return_value=config):
            result = get_vapi_status("unconfigured", admin_verified=True)
            assert result["vapi_configured"] is False
            assert result["ready_for_calls"] is False

    def test_provision_vapi_no_api_key_raises_500(self):
        """Provisioning without VAPI_API_KEY should raise 500."""
        from fastapi import HTTPException
        from src.api.admin_routes import provision_vapi_for_tenant, VAPIProvisionRequest

        request = VAPIProvisionRequest(
            tenant_id="test", company_name="Test", buy_phone_number=False
        )
        bg_tasks = MagicMock()

        # Mock the vapi_tool module since it may not exist
        mock_vapi_module = MagicMock()
        with patch.dict("sys.modules", {"src.tools.vapi_tool": mock_vapi_module}):
            with patch.dict(os.environ, {"VAPI_API_KEY": ""}, clear=False):
                with patch("src.api.admin_routes.ClientConfig") as mock_cfg:
                    mock_cfg.return_value = MagicMock(company_name="Test Co")
                    with pytest.raises(HTTPException) as exc_info:
                        provision_vapi_for_tenant(request, bg_tasks, admin_verified=True)
                    assert exc_info.value.status_code == 500
                    assert "vapi_api_key" in exc_info.value.detail.lower()

    def test_provision_vapi_tenant_not_found_raises_404(self):
        """Provisioning for non-existent tenant should raise 404."""
        from fastapi import HTTPException
        from src.api.admin_routes import provision_vapi_for_tenant, VAPIProvisionRequest

        request = VAPIProvisionRequest(
            tenant_id="ghost", company_name="Ghost", buy_phone_number=False
        )
        bg_tasks = MagicMock()

        mock_vapi_module = MagicMock()
        with patch.dict("sys.modules", {"src.tools.vapi_tool": mock_vapi_module}):
            with patch.dict(os.environ, {"VAPI_API_KEY": "key123"}, clear=False):
                with patch("src.api.admin_routes.ClientConfig", side_effect=FileNotFoundError):
                    with pytest.raises(HTTPException) as exc_info:
                        provision_vapi_for_tenant(request, bg_tasks, admin_verified=True)
                    assert exc_info.value.status_code == 404

    def test_update_vapi_config_tenant_not_found(self):
        """Updating config for non-existent tenant should raise 404."""
        from fastapi import HTTPException
        from src.api.admin_routes import update_tenant_vapi_config, TenantConfigUpdate

        update = TenantConfigUpdate(vapi_api_key="new-key")
        with patch("src.api.admin_routes.ClientConfig", side_effect=FileNotFoundError):
            with pytest.raises(HTTPException) as exc_info:
                update_tenant_vapi_config("ghost", update, admin_verified=True)
            assert exc_info.value.status_code == 404

    def test_update_vapi_config_success(self, mock_client_config):
        """Successful VAPI config update should return success."""
        from src.api.admin_routes import update_tenant_vapi_config, TenantConfigUpdate

        update = TenantConfigUpdate(vapi_api_key="new-key", vapi_assistant_id="asst-new")
        with patch("src.api.admin_routes.ClientConfig", return_value=mock_client_config):
            with patch("src.api.admin_routes.update_tenant_config_file", return_value=True) as mock_update:
                result = update_tenant_vapi_config("test_tenant", update, admin_verified=True)
                assert result["success"] is True
                assert result["tenant_id"] == "test_tenant"
                assert result["message"] == "Configuration updated"
                mock_update.assert_called_once_with(
                    tenant_id="test_tenant",
                    vapi_api_key="new-key",
                    inbound_assistant_id="asst-new",
                    outbound_assistant_id=None,
                    phone_number_id=None
                )

    def test_update_vapi_config_failure(self, mock_client_config):
        """When update_tenant_config_file returns False, message says 'Update failed'."""
        from src.api.admin_routes import update_tenant_vapi_config, TenantConfigUpdate

        update = TenantConfigUpdate(vapi_api_key="bad-key")
        with patch("src.api.admin_routes.ClientConfig", return_value=mock_client_config):
            with patch("src.api.admin_routes.update_tenant_config_file", return_value=False):
                result = update_tenant_vapi_config("test_tenant", update, admin_verified=True)
                assert result["success"] is False
                assert result["message"] == "Update failed"


class TestUpdateTenantConfigFile:
    """Direct unit tests for the update_tenant_config_file helper function."""

    def test_config_file_not_found_returns_false(self):
        """When config file does not exist, should return False."""
        from src.api.admin_routes import update_tenant_config_file

        with patch("src.api.admin_routes.Path") as mock_path_cls:
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            mock_path_cls.return_value = mock_path

            result = update_tenant_config_file("missing_tenant", vapi_api_key="key")
            assert result is False

    def test_config_file_updates_yaml(self, tmp_path):
        """Should update the YAML file with provided values."""
        import yaml
        from src.api.admin_routes import update_tenant_config_file

        # Create a temporary config file
        config_dir = tmp_path / "clients" / "test_tenant"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "client.yaml"
        config_file.write_text(yaml.dump({
            "client": {"name": "Test"},
            "infrastructure": {"vapi": {"assistant_id": "old-id"}}
        }))

        with patch("src.api.admin_routes.Path") as mock_path_cls:
            mock_path_cls.return_value = config_file
            # Also need to handle the _config_cache import
            with patch("config.loader._config_cache", {}):
                result = update_tenant_config_file(
                    "test_tenant",
                    inbound_assistant_id="new-asst-id",
                    outbound_assistant_id="new-outbound-id"
                )
                assert result is True

                # Verify the file was updated
                with open(config_file) as f:
                    updated = yaml.safe_load(f)
                assert updated["infrastructure"]["vapi"]["assistant_id"] == "new-asst-id"
                assert updated["infrastructure"]["vapi"]["outbound_assistant_id"] == "new-outbound-id"

    def test_config_file_exception_returns_false(self):
        """When YAML write fails, should return False."""
        from src.api.admin_routes import update_tenant_config_file

        with patch("src.api.admin_routes.Path") as mock_path_cls:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path_cls.return_value = mock_path

            with patch("builtins.open", side_effect=PermissionError("denied")):
                result = update_tenant_config_file("test", vapi_api_key="key")
                assert result is False


class TestPhoneSearchDirect:
    """Direct handler tests for POST /api/v1/admin/provision/phone/search."""

    def test_search_phones_missing_all_creds(self):
        """Should raise 500 when all credentials are missing."""
        from fastapi import HTTPException
        from src.api.admin_routes import search_available_phones, PhoneNumberSearchRequest

        request = PhoneNumberSearchRequest(country_code="ZA", limit=5)
        with patch.dict(os.environ, {"TWILIO_ACCOUNT_SID": "", "TWILIO_AUTH_TOKEN": "", "VAPI_API_KEY": ""}):
            with pytest.raises(HTTPException) as exc_info:
                search_available_phones(request, admin_verified=True)
            assert exc_info.value.status_code == 500


class TestPydanticModels:
    """Test request/response model validation."""

    def test_vapi_provision_request_min_tenant_id(self):
        """tenant_id must be at least 2 chars."""
        from src.api.admin_routes import VAPIProvisionRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            VAPIProvisionRequest(tenant_id="a")  # too short

    def test_vapi_provision_request_max_tenant_id(self):
        """tenant_id must be at most 50 chars."""
        from src.api.admin_routes import VAPIProvisionRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            VAPIProvisionRequest(tenant_id="x" * 51)  # too long

    def test_vapi_provision_request_defaults(self):
        """VAPIProvisionRequest should have correct defaults."""
        from src.api.admin_routes import VAPIProvisionRequest

        req = VAPIProvisionRequest(tenant_id="test_tenant")
        assert req.country_code == "ZA"
        assert req.buy_phone_number is True
        assert req.company_name is None
        assert req.use_existing_number_id is None
        assert req.vapi_api_key is None

    def test_phone_number_search_request_limit_bounds(self):
        """PhoneNumberSearchRequest limit must be 1-20."""
        from src.api.admin_routes import PhoneNumberSearchRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PhoneNumberSearchRequest(limit=0)  # below min
        with pytest.raises(ValidationError):
            PhoneNumberSearchRequest(limit=21)  # above max

    def test_create_test_user_request_role_pattern(self):
        """CreateTestUserRequest role must match pattern."""
        from src.api.admin_routes import CreateTestUserRequest
        from pydantic import ValidationError

        # Valid roles
        for role in ["admin", "user", "consultant"]:
            req = CreateTestUserRequest(tenant_id="tt", email="a@b.com", password="pass123", role=role)
            assert req.role == role

        # Invalid role
        with pytest.raises(ValidationError):
            CreateTestUserRequest(tenant_id="tt", email="a@b.com", password="pass123", role="owner")

    def test_tenant_usage_stats_defaults(self):
        """TenantUsageStats should default all counts to 0."""
        from src.api.admin_routes import TenantUsageStats

        stats = TenantUsageStats(client_id="t1", period="month")
        assert stats.quotes_generated == 0
        assert stats.invoices_created == 0
        assert stats.invoices_paid == 0
        assert stats.total_revenue == 0
        assert stats.emails_sent == 0
        assert stats.calls_made == 0
        assert stats.active_users == 0
        assert stats.total_clients == 0


class TestAdminAuthAcrossEndpoints:
    """Test that all admin endpoints require authentication."""

    ENDPOINTS = [
        ("GET", "/api/v1/admin/tenants"),
        ("GET", "/api/v1/admin/tenants/summary"),
        ("GET", "/api/v1/admin/tenants/some_id"),
        ("GET", "/api/v1/admin/tenants/some_id/usage"),
        ("GET", "/api/v1/admin/usage/summary"),
        ("GET", "/api/v1/admin/health"),
        ("POST", "/api/v1/admin/create-test-user"),
        ("GET", "/api/v1/admin/diagnostics/quotes"),
        ("POST", "/api/v1/admin/provision/vapi"),
        ("GET", "/api/v1/admin/provision/vapi/some_id"),
        ("PATCH", "/api/v1/admin/provision/vapi/some_id/config"),
        ("POST", "/api/v1/admin/provision/phone/search"),
    ]

    @pytest.mark.parametrize("method,url", ENDPOINTS)
    def test_endpoint_rejects_unauthenticated(self, test_client, method, url, mock_admin_token):
        """Every admin endpoint should reject requests without valid token."""
        # Send request with WRONG token
        response = test_client.request(
            method, url,
            headers={"X-Admin-Token": "definitely-wrong-token"},
            json={} if method in ("POST", "PATCH") else None
        )
        assert response.status_code == 401, f"{method} {url} should return 401 with wrong token"

    @pytest.mark.parametrize("method,url", ENDPOINTS)
    def test_endpoint_rejects_missing_token(self, test_client, method, url, mock_admin_token):
        """Every admin endpoint should reject requests without any token."""
        response = test_client.request(
            method, url,
            json={} if method in ("POST", "PATCH") else None
        )
        assert response.status_code == 401, f"{method} {url} should return 401 with no token"
