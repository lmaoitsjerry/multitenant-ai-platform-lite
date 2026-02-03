"""
Admin Tenants Routes Unit Tests

Tests for the admin tenant management endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


# ==================== Fixtures ====================

@pytest.fixture
def test_client():
    """Create a basic TestClient."""
    from main import app
    return TestClient(app)


@pytest.fixture
def admin_headers():
    """Create mock admin auth headers."""
    return {"X-Admin-Token": "test-admin-token"}


# ==================== Model Tests ====================

class TestTenantSummaryModel:
    """Tests for TenantSummary model."""

    def test_tenant_summary_required_fields(self):
        """TenantSummary should have required fields."""
        from src.api.admin_tenants_routes import TenantSummary

        summary = TenantSummary(
            tenant_id="test-tenant",
            company_name="Test Company"
        )

        assert summary.tenant_id == "test-tenant"
        assert summary.company_name == "Test Company"

    def test_tenant_summary_defaults(self):
        """TenantSummary should have sensible defaults."""
        from src.api.admin_tenants_routes import TenantSummary

        summary = TenantSummary(
            tenant_id="test",
            company_name="Test"
        )

        assert summary.status == "active"
        assert summary.currency == "ZAR"
        assert summary.quote_count == 0
        assert summary.invoice_count == 0


class TestTenantDetailModel:
    """Tests for TenantDetail model."""

    def test_tenant_detail_required_fields(self):
        """TenantDetail should have required fields."""
        from src.api.admin_tenants_routes import TenantDetail

        detail = TenantDetail(
            tenant_id="test-tenant",
            company_name="Test Company"
        )

        assert detail.tenant_id == "test-tenant"
        assert detail.company_name == "Test Company"

    def test_tenant_detail_defaults(self):
        """TenantDetail should have sensible defaults."""
        from src.api.admin_tenants_routes import TenantDetail

        detail = TenantDetail(
            tenant_id="test",
            company_name="Test"
        )

        assert detail.currency == "ZAR"
        assert detail.timezone == "Africa/Johannesburg"
        assert detail.status == "active"
        assert detail.sendgrid_configured is False
        assert detail.vapi_configured is False


class TestTenantStatsModel:
    """Tests for TenantStats model."""

    def test_tenant_stats_all_zero_defaults(self):
        """TenantStats should default all counts to zero."""
        from src.api.admin_tenants_routes import TenantStats

        stats = TenantStats(tenant_id="test")

        assert stats.quotes_count == 0
        assert stats.quotes_this_month == 0
        assert stats.invoices_count == 0
        assert stats.invoices_paid == 0
        assert stats.total_invoiced == 0
        assert stats.total_paid == 0
        assert stats.clients_count == 0
        assert stats.users_count == 0


class TestCreateTenantRequest:
    """Tests for CreateTenantRequest model."""

    def test_create_request_defaults(self):
        """CreateTenantRequest should have sensible defaults."""
        from src.api.admin_tenants_routes import CreateTenantRequest

        request = CreateTenantRequest(
            tenant_id="new-tenant",
            company_name="New Company",
            admin_email="admin@example.com"
        )

        assert request.timezone == "Africa/Johannesburg"
        assert request.currency == "ZAR"
        assert request.plan == "lite"
        assert request.primary_color == "#1a73e8"

    def test_create_request_validates_tenant_id_format(self):
        """CreateTenantRequest should validate tenant_id format."""
        from src.api.admin_tenants_routes import CreateTenantRequest
        from pydantic import ValidationError

        # Valid tenant IDs
        valid_ids = ["test-tenant", "my_tenant", "tenant123", "a-b-c"]
        for tid in valid_ids:
            request = CreateTenantRequest(
                tenant_id=tid,
                company_name="Test",
                admin_email="test@example.com"
            )
            assert request.tenant_id == tid

        # Invalid tenant IDs
        with pytest.raises(ValidationError):
            CreateTenantRequest(
                tenant_id="UPPERCASE",  # Must be lowercase
                company_name="Test",
                admin_email="test@example.com"
            )


class TestSuspendRequest:
    """Tests for SuspendRequest model."""

    def test_suspend_request_requires_reason(self):
        """SuspendRequest should require a reason."""
        from src.api.admin_tenants_routes import SuspendRequest
        from pydantic import ValidationError

        # Valid reason
        request = SuspendRequest(reason="Non-payment of invoices")
        assert request.reason == "Non-payment of invoices"

        # Too short reason
        with pytest.raises(ValidationError):
            SuspendRequest(reason="bad")  # Less than 5 chars


# ==================== Endpoint Tests ====================

class TestListTenantsEndpoint:
    """Tests for GET /api/v1/admin/tenants endpoint."""

    def test_list_tenants_requires_admin_auth(self, test_client):
        """GET /admin/tenants should require admin token."""
        response = test_client.get("/api/v1/admin/tenants")

        # 503 when ADMIN_API_TOKEN not configured, 401/403 when configured but wrong token
        assert response.status_code in [401, 403, 503]

    def test_list_tenants_with_invalid_token(self, test_client):
        """GET /admin/tenants should reject invalid token."""
        response = test_client.get(
            "/api/v1/admin/tenants",
            headers={"X-Admin-Token": "invalid-token"}
        )

        # 503 when not configured, 401/403 when configured with wrong token
        assert response.status_code in [401, 403, 503]


class TestGetTenantDetailsEndpoint:
    """Tests for GET /api/v1/admin/tenants/{tenant_id} endpoint."""

    def test_get_tenant_requires_admin_auth(self, test_client):
        """GET /admin/tenants/{id} should require admin token."""
        response = test_client.get("/api/v1/admin/tenants/example")

        assert response.status_code in [401, 403, 503]


class TestGetTenantStatsEndpoint:
    """Tests for GET /api/v1/admin/tenants/{tenant_id}/stats endpoint."""

    def test_get_stats_requires_admin_auth(self, test_client):
        """GET /admin/tenants/{id}/stats should require admin token."""
        response = test_client.get("/api/v1/admin/tenants/example/stats")

        assert response.status_code in [401, 403, 503]


class TestSuspendTenantEndpoint:
    """Tests for POST /api/v1/admin/tenants/{tenant_id}/suspend endpoint."""

    def test_suspend_requires_admin_auth(self, test_client):
        """POST /admin/tenants/{id}/suspend should require admin token."""
        response = test_client.post(
            "/api/v1/admin/tenants/example/suspend",
            json={"reason": "Testing suspension"}
        )

        assert response.status_code in [401, 403, 503]


class TestActivateTenantEndpoint:
    """Tests for POST /api/v1/admin/tenants/{tenant_id}/activate endpoint."""

    def test_activate_requires_admin_auth(self, test_client):
        """POST /admin/tenants/{id}/activate should require admin token."""
        response = test_client.post("/api/v1/admin/tenants/example/activate")

        assert response.status_code in [401, 403, 503]


class TestDeleteTenantEndpoint:
    """Tests for DELETE /api/v1/admin/tenants/{tenant_id} endpoint."""

    def test_delete_requires_admin_auth(self, test_client):
        """DELETE /admin/tenants/{id} should require admin token."""
        response = test_client.delete("/api/v1/admin/tenants/example?confirm=true")

        assert response.status_code in [401, 403, 503]


class TestCreateTenantEndpoint:
    """Tests for POST /api/v1/admin/tenants endpoint."""

    def test_create_requires_admin_auth(self, test_client):
        """POST /admin/tenants should require admin token."""
        response = test_client.post(
            "/api/v1/admin/tenants",
            json={
                "tenant_id": "new-tenant",
                "company_name": "New Company",
                "admin_email": "admin@example.com"
            }
        )

        assert response.status_code in [401, 403, 503]


# ==================== Helper Function Tests ====================

class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_supabase_admin_client_returns_none_without_env(self):
        """Should return None when env vars not set."""
        from src.api.admin_tenants_routes import get_supabase_admin_client

        with patch.dict('os.environ', {}, clear=True):
            client = get_supabase_admin_client()
            assert client is None

    @pytest.mark.asyncio
    async def test_get_tenant_stats_returns_empty_without_client(self):
        """Should return empty stats when no Supabase client."""
        from src.api.admin_tenants_routes import get_tenant_stats_from_db

        with patch('src.api.admin_tenants_routes.get_supabase_admin_client', return_value=None):
            stats = await get_tenant_stats_from_db("test-tenant")
            assert stats == {}
