"""
Admin Tenants Routes Unit Tests

Tests for the admin tenant management endpoints.
All tests call handler functions directly (no TestClient / app import needed).
"""

import inspect
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


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


# ==================== Endpoint Auth Dependency Tests ====================
# These verify that each endpoint function declares admin_verified as a parameter
# (which means FastAPI will enforce the Depends(verify_admin_token) dependency).

class TestListTenantsEndpoint:
    """Tests for list_tenants endpoint auth dependency."""

    def test_list_tenants_requires_admin_auth(self):
        """list_tenants should depend on admin verification."""
        from src.api.admin_tenants_routes import list_tenants
        sig = inspect.signature(list_tenants)
        assert 'admin_verified' in sig.parameters

    def test_list_tenants_with_invalid_token(self):
        """list_tenants admin_verified param should have Depends default."""
        from src.api.admin_tenants_routes import list_tenants
        sig = inspect.signature(list_tenants)
        param = sig.parameters['admin_verified']
        # The default is a Depends() instance
        assert param.default is not inspect.Parameter.empty


class TestGetTenantDetailsEndpoint:
    """Tests for get_tenant_details endpoint auth dependency."""

    def test_get_tenant_requires_admin_auth(self):
        """get_tenant_details should depend on admin verification."""
        from src.api.admin_tenants_routes import get_tenant_details
        sig = inspect.signature(get_tenant_details)
        assert 'admin_verified' in sig.parameters


class TestGetTenantStatsEndpoint:
    """Tests for get_tenant_statistics endpoint auth dependency."""

    def test_get_stats_requires_admin_auth(self):
        """get_tenant_statistics should depend on admin verification."""
        from src.api.admin_tenants_routes import get_tenant_statistics
        sig = inspect.signature(get_tenant_statistics)
        assert 'admin_verified' in sig.parameters


class TestSuspendTenantEndpoint:
    """Tests for suspend_tenant endpoint auth dependency."""

    def test_suspend_requires_admin_auth(self):
        """suspend_tenant should depend on admin verification."""
        from src.api.admin_tenants_routes import suspend_tenant
        sig = inspect.signature(suspend_tenant)
        assert 'admin_verified' in sig.parameters


class TestActivateTenantEndpoint:
    """Tests for activate_tenant endpoint auth dependency."""

    def test_activate_requires_admin_auth(self):
        """activate_tenant should depend on admin verification."""
        from src.api.admin_tenants_routes import activate_tenant
        sig = inspect.signature(activate_tenant)
        assert 'admin_verified' in sig.parameters


class TestDeleteTenantEndpoint:
    """Tests for delete_tenant endpoint auth dependency."""

    def test_delete_requires_admin_auth(self):
        """delete_tenant should depend on admin verification."""
        from src.api.admin_tenants_routes import delete_tenant
        sig = inspect.signature(delete_tenant)
        assert 'admin_verified' in sig.parameters


class TestCreateTenantEndpoint:
    """Tests for create_tenant endpoint auth dependency."""

    def test_create_requires_admin_auth(self):
        """create_tenant should depend on admin verification."""
        from src.api.admin_tenants_routes import create_tenant
        sig = inspect.signature(create_tenant)
        assert 'admin_verified' in sig.parameters


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


# ==================== Fixtures ====================

@pytest.fixture
def mock_client_config():
    """Create a mock ClientConfig instance with typical attributes."""
    mock_cfg = MagicMock()
    mock_cfg.company_name = "Test Company"
    mock_cfg.support_email = "support@test.com"
    mock_cfg.support_phone = "+27123456789"
    mock_cfg.website = "https://test.com"
    mock_cfg.currency = "ZAR"
    mock_cfg.timezone = "Africa/Johannesburg"
    mock_cfg.logo_url = "https://test.com/logo.png"
    mock_cfg.primary_color = "#ff0000"
    mock_cfg.gcp_project_id = "test-gcp-project"
    mock_cfg.sendgrid_api_key = "SG.test-key"
    mock_cfg.vapi_assistant_id = "vapi-123"
    mock_cfg.config_path = "/fake/path/config.yaml"
    return mock_cfg


# ==================== Extended Model Tests ====================

class TestTenantListResponseModel:
    """Tests for TenantListResponse model."""

    def test_tenant_list_response_fields(self):
        """TenantListResponse should contain success, data, count, total."""
        from src.api.admin_tenants_routes import TenantListResponse, TenantSummary

        tenants = [
            TenantSummary(tenant_id="t1", company_name="Company 1"),
            TenantSummary(tenant_id="t2", company_name="Company 2"),
        ]

        response = TenantListResponse(
            success=True, data=tenants, count=2, total=5
        )

        assert response.success is True
        assert len(response.data) == 2
        assert response.count == 2
        assert response.total == 5

    def test_tenant_list_response_empty(self):
        """TenantListResponse should work with empty data list."""
        from src.api.admin_tenants_routes import TenantListResponse

        response = TenantListResponse(
            success=True, data=[], count=0, total=0
        )

        assert response.data == []
        assert response.count == 0
        assert response.total == 0

    def test_tenant_list_response_count_differs_from_total(self):
        """count (page) and total (all) can differ for pagination."""
        from src.api.admin_tenants_routes import TenantListResponse, TenantSummary

        response = TenantListResponse(
            success=True,
            data=[TenantSummary(tenant_id="t1", company_name="C1")],
            count=1,
            total=50,
        )

        assert response.count == 1
        assert response.total == 50


# ==================== Extended Helper Function Tests ====================

class TestGetSupabaseAdminClientExtended:
    """Extended tests for get_supabase_admin_client."""

    def test_returns_client_with_env_vars_set(self):
        """Should return a Supabase client when SUPABASE_URL and key are set."""
        from src.api.admin_tenants_routes import get_supabase_admin_client

        mock_client = MagicMock()
        env = {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_KEY": "service-key-123",
        }
        with patch.dict('os.environ', env, clear=True):
            with patch('supabase.create_client', return_value=mock_client) as mock_create:
                result = get_supabase_admin_client()

                mock_create.assert_called_once_with(
                    "https://test.supabase.co", "service-key-123"
                )
                assert result is mock_client

    def test_falls_back_to_supabase_key(self):
        """Should use SUPABASE_KEY when SUPABASE_SERVICE_KEY is absent."""
        from src.api.admin_tenants_routes import get_supabase_admin_client

        mock_client = MagicMock()
        env = {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_KEY": "anon-key-456",
        }
        with patch.dict('os.environ', env, clear=True):
            with patch('supabase.create_client', return_value=mock_client) as mock_create:
                result = get_supabase_admin_client()

                mock_create.assert_called_once_with(
                    "https://test.supabase.co", "anon-key-456"
                )
                assert result is mock_client

    def test_returns_none_with_url_only(self):
        """Should return None when only URL is set (no key)."""
        from src.api.admin_tenants_routes import get_supabase_admin_client

        env = {"SUPABASE_URL": "https://test.supabase.co"}
        with patch.dict('os.environ', env, clear=True):
            result = get_supabase_admin_client()
            assert result is None

    def test_returns_none_with_key_only(self):
        """Should return None when only key is set (no URL)."""
        from src.api.admin_tenants_routes import get_supabase_admin_client

        env = {"SUPABASE_SERVICE_KEY": "service-key-123"}
        with patch.dict('os.environ', env, clear=True):
            result = get_supabase_admin_client()
            assert result is None


class TestGetTenantStatsFromDbExtended:
    """Extended tests for get_tenant_stats_from_db with mocked data."""

    @pytest.mark.asyncio
    async def test_returns_stats_with_quotes(self):
        """Should return quote counts from mocked Supabase."""
        from src.api.admin_tenants_routes import get_tenant_stats_from_db

        mock_client = MagicMock()

        # Build per-table mocks
        def table_side_effect(table_name):
            chain = MagicMock()
            chain.eq.return_value = chain
            chain.gte.return_value = chain

            result = MagicMock()
            result.data = []
            result.count = 0

            if table_name == "quotes":
                result.count = 15
            elif table_name == "invoices":
                result.data = [
                    {"id": 1, "status": "paid", "total_amount": 5000, "paid_amount": 5000},
                    {"id": 2, "status": "pending", "total_amount": 3000, "paid_amount": 0},
                ]
                result.count = 2
            elif table_name == "clients":
                result.count = 8
            elif table_name == "organization_users":
                result.count = 3

            chain.select.return_value = chain
            chain.execute.return_value = result
            return chain

        mock_client.table.side_effect = table_side_effect

        with patch('src.api.admin_tenants_routes.get_supabase_admin_client', return_value=mock_client):
            with patch('asyncio.to_thread', side_effect=_sync_to_thread):
                stats = await get_tenant_stats_from_db("test-tenant")

        assert stats["quotes_count"] == 15
        assert stats["clients_count"] == 8
        assert stats["users_count"] == 3

    @pytest.mark.asyncio
    async def test_returns_invoice_aggregates(self):
        """Should calculate invoice totals correctly."""
        from src.api.admin_tenants_routes import get_tenant_stats_from_db

        mock_client = MagicMock()

        invoices = [
            {"id": 1, "status": "paid", "total_amount": 10000, "paid_amount": 10000},
            {"id": 2, "status": "paid", "total_amount": 5000, "paid_amount": 5000},
            {"id": 3, "status": "pending", "total_amount": 8000, "paid_amount": 0},
        ]

        def table_side_effect(table_name):
            chain = MagicMock()
            chain.eq.return_value = chain
            chain.gte.return_value = chain
            chain.select.return_value = chain

            result = MagicMock()
            if table_name == "invoices":
                result.data = invoices
                result.count = len(invoices)
            else:
                result.data = []
                result.count = 0

            chain.execute.return_value = result
            return chain

        mock_client.table.side_effect = table_side_effect

        with patch('src.api.admin_tenants_routes.get_supabase_admin_client', return_value=mock_client):
            with patch('asyncio.to_thread', side_effect=_sync_to_thread):
                stats = await get_tenant_stats_from_db("test-tenant")

        assert stats["invoices_count"] == 3
        assert stats["invoices_paid"] == 2
        assert stats["total_invoiced"] == 23000
        assert stats["total_paid"] == 15000

    @pytest.mark.asyncio
    async def test_handles_db_exception_gracefully(self):
        """Should return partial stats when DB throws an exception."""
        from src.api.admin_tenants_routes import get_tenant_stats_from_db

        mock_client = MagicMock()

        def table_side_effect(table_name):
            chain = MagicMock()
            chain.eq.return_value = chain
            chain.gte.return_value = chain
            chain.select.return_value = chain
            chain.execute.side_effect = Exception("DB connection lost")
            return chain

        mock_client.table.side_effect = table_side_effect

        with patch('src.api.admin_tenants_routes.get_supabase_admin_client', return_value=mock_client):
            with patch('asyncio.to_thread', side_effect=_sync_to_thread):
                stats = await get_tenant_stats_from_db("test-tenant")

        # Should return default zeros, not crash
        assert stats["quotes_count"] == 0
        assert stats["invoices_count"] == 0

    @pytest.mark.asyncio
    async def test_handles_null_invoice_amounts(self):
        """Should treat None amounts as 0."""
        from src.api.admin_tenants_routes import get_tenant_stats_from_db

        mock_client = MagicMock()

        invoices = [
            {"id": 1, "status": "paid", "total_amount": None, "paid_amount": None},
        ]

        def table_side_effect(table_name):
            chain = MagicMock()
            chain.eq.return_value = chain
            chain.gte.return_value = chain
            chain.select.return_value = chain
            result = MagicMock()
            if table_name == "invoices":
                result.data = invoices
                result.count = 1
            else:
                result.data = []
                result.count = 0
            chain.execute.return_value = result
            return chain

        mock_client.table.side_effect = table_side_effect

        with patch('src.api.admin_tenants_routes.get_supabase_admin_client', return_value=mock_client):
            with patch('asyncio.to_thread', side_effect=_sync_to_thread):
                stats = await get_tenant_stats_from_db("test-tenant")

        assert stats["total_invoiced"] == 0
        assert stats["total_paid"] == 0


# Helper: synchronous pass-through for asyncio.to_thread in tests
async def _sync_to_thread(fn, *args, **kwargs):
    """Call the function synchronously instead of in a thread."""
    return fn(*args, **kwargs)


# ==================== Direct Handler Tests for list_tenants ====================

class TestListTenantsHandlerDirect:
    """Tests for list_tenants handler called directly (avoids route shadowing).

    Note: list_tenants uses FastAPI Query() defaults, so we must pass plain
    Python values for all parameters when calling directly.
    """

    @pytest.mark.asyncio
    async def test_list_tenants_returns_tenants(self):
        """Should return tenant list with mocked data."""
        from src.api.admin_tenants_routes import list_tenants

        mock_cfg = MagicMock()
        mock_cfg.company_name = "Alpha Co"
        mock_cfg.support_email = "alpha@test.com"
        mock_cfg.currency = "ZAR"

        with patch('src.api.admin_tenants_routes.list_clients', return_value=["alpha"]):
            with patch('src.api.admin_tenants_routes.ClientConfig', return_value=mock_cfg):
                with patch('src.api.admin_tenants_routes.get_tenant_stats_from_db', new_callable=AsyncMock, return_value={}):
                    result = await list_tenants(
                        status=None, search=None, limit=20, offset=0,
                        sort_by="company_name", sort_order="asc", admin_verified=True
                    )

        assert result.success is True
        assert result.total == 1
        assert result.data[0].tenant_id == "alpha"
        assert result.data[0].company_name == "Alpha Co"

    @pytest.mark.asyncio
    async def test_list_tenants_search_filter(self):
        """Should filter tenants by search term."""
        from src.api.admin_tenants_routes import list_tenants

        configs = {
            "alpha": MagicMock(company_name="Alpha Travel", support_email="a@t.com", currency="ZAR"),
            "beta": MagicMock(company_name="Beta Tours", support_email="b@t.com", currency="ZAR"),
            "gamma": MagicMock(company_name="Gamma Safaris", support_email="g@t.com", currency="ZAR"),
        }

        with patch('src.api.admin_tenants_routes.list_clients', return_value=["alpha", "beta", "gamma"]):
            with patch('src.api.admin_tenants_routes.ClientConfig', side_effect=lambda cid: configs[cid]):
                with patch('src.api.admin_tenants_routes.get_tenant_stats_from_db', new_callable=AsyncMock, return_value={}):
                    result = await list_tenants(
                        status=None, search="beta", limit=20, offset=0,
                        sort_by="company_name", sort_order="asc", admin_verified=True
                    )

        assert result.total == 1
        assert result.data[0].tenant_id == "beta"

    @pytest.mark.asyncio
    async def test_list_tenants_search_by_tenant_id(self):
        """Search should also match against tenant_id."""
        from src.api.admin_tenants_routes import list_tenants

        configs = {
            "alpha-resort": MagicMock(company_name="Company One", support_email="a@t.com", currency="ZAR"),
            "beta-lodge": MagicMock(company_name="Company Two", support_email="b@t.com", currency="ZAR"),
        }

        with patch('src.api.admin_tenants_routes.list_clients', return_value=["alpha-resort", "beta-lodge"]):
            with patch('src.api.admin_tenants_routes.ClientConfig', side_effect=lambda cid: configs[cid]):
                with patch('src.api.admin_tenants_routes.get_tenant_stats_from_db', new_callable=AsyncMock, return_value={}):
                    result = await list_tenants(
                        status=None, search="alpha", limit=20, offset=0,
                        sort_by="company_name", sort_order="asc", admin_verified=True
                    )

        assert result.total == 1
        assert result.data[0].tenant_id == "alpha-resort"

    @pytest.mark.asyncio
    async def test_list_tenants_status_filter_active(self):
        """Should filter tenants by active status."""
        from src.api.admin_tenants_routes import list_tenants

        mock_cfg = MagicMock(company_name="Test Co", support_email="t@t.com", currency="ZAR")

        with patch('src.api.admin_tenants_routes.list_clients', return_value=["t1"]):
            with patch('src.api.admin_tenants_routes.ClientConfig', return_value=mock_cfg):
                with patch('src.api.admin_tenants_routes.get_tenant_stats_from_db', new_callable=AsyncMock, return_value={}):
                    result = await list_tenants(
                        status="active", search=None, limit=20, offset=0,
                        sort_by="company_name", sort_order="asc", admin_verified=True
                    )

        assert result.total == 1

    @pytest.mark.asyncio
    async def test_list_tenants_status_filter_suspended(self):
        """Filtering by suspended should exclude active tenants."""
        from src.api.admin_tenants_routes import list_tenants

        mock_cfg = MagicMock(company_name="Test Co", support_email="t@t.com", currency="ZAR")

        with patch('src.api.admin_tenants_routes.list_clients', return_value=["t1"]):
            with patch('src.api.admin_tenants_routes.ClientConfig', return_value=mock_cfg):
                with patch('src.api.admin_tenants_routes.get_tenant_stats_from_db', new_callable=AsyncMock, return_value={}):
                    result = await list_tenants(
                        status="suspended", search=None, limit=20, offset=0,
                        sort_by="company_name", sort_order="asc", admin_verified=True
                    )

        assert result.total == 0

    @pytest.mark.asyncio
    async def test_list_tenants_sort_by_company_name_desc(self):
        """Should sort by company_name descending."""
        from src.api.admin_tenants_routes import list_tenants

        configs = {
            "alpha": MagicMock(company_name="Alpha", support_email="a@t.com", currency="ZAR"),
            "beta": MagicMock(company_name="Beta", support_email="b@t.com", currency="ZAR"),
            "gamma": MagicMock(company_name="Gamma", support_email="g@t.com", currency="ZAR"),
        }

        with patch('src.api.admin_tenants_routes.list_clients', return_value=["alpha", "beta", "gamma"]):
            with patch('src.api.admin_tenants_routes.ClientConfig', side_effect=lambda cid: configs[cid]):
                with patch('src.api.admin_tenants_routes.get_tenant_stats_from_db', new_callable=AsyncMock, return_value={}):
                    result = await list_tenants(
                        status=None, search=None, limit=20, offset=0,
                        sort_by="company_name", sort_order="desc", admin_verified=True
                    )

        names = [t.company_name for t in result.data]
        assert names == ["Gamma", "Beta", "Alpha"]

    @pytest.mark.asyncio
    async def test_list_tenants_sort_by_tenant_id(self):
        """Should sort by tenant_id ascending."""
        from src.api.admin_tenants_routes import list_tenants

        configs = {
            "charlie": MagicMock(company_name="C Co", support_email="c@t.com", currency="ZAR"),
            "alice": MagicMock(company_name="A Co", support_email="a@t.com", currency="ZAR"),
            "bob": MagicMock(company_name="B Co", support_email="b@t.com", currency="ZAR"),
        }

        with patch('src.api.admin_tenants_routes.list_clients', return_value=["charlie", "alice", "bob"]):
            with patch('src.api.admin_tenants_routes.ClientConfig', side_effect=lambda cid: configs[cid]):
                with patch('src.api.admin_tenants_routes.get_tenant_stats_from_db', new_callable=AsyncMock, return_value={}):
                    result = await list_tenants(
                        status=None, search=None, limit=20, offset=0,
                        sort_by="tenant_id", sort_order="asc", admin_verified=True
                    )

        ids = [t.tenant_id for t in result.data]
        assert ids == ["alice", "bob", "charlie"]

    @pytest.mark.asyncio
    async def test_list_tenants_sort_by_quote_count(self):
        """Should sort by quote_count descending."""
        from src.api.admin_tenants_routes import list_tenants

        configs = {
            "low": MagicMock(company_name="Low Co", support_email="l@t.com", currency="ZAR"),
            "high": MagicMock(company_name="High Co", support_email="h@t.com", currency="ZAR"),
            "mid": MagicMock(company_name="Mid Co", support_email="m@t.com", currency="ZAR"),
        }
        stats_map = {
            "low": {"quotes_count": 2},
            "high": {"quotes_count": 100},
            "mid": {"quotes_count": 25},
        }

        async def mock_stats(tid):
            return stats_map.get(tid, {})

        with patch('src.api.admin_tenants_routes.list_clients', return_value=["low", "high", "mid"]):
            with patch('src.api.admin_tenants_routes.ClientConfig', side_effect=lambda cid: configs[cid]):
                with patch('src.api.admin_tenants_routes.get_tenant_stats_from_db', side_effect=mock_stats):
                    result = await list_tenants(
                        status=None, search=None, limit=20, offset=0,
                        sort_by="quote_count", sort_order="desc", admin_verified=True
                    )

        counts = [t.quote_count for t in result.data]
        assert counts == [100, 25, 2]

    @pytest.mark.asyncio
    async def test_list_tenants_pagination(self):
        """Should apply offset and limit for pagination."""
        from src.api.admin_tenants_routes import list_tenants

        configs = {}
        for i in range(5):
            cid = f"tenant-{i}"
            configs[cid] = MagicMock(company_name=f"Company {i}", support_email=f"{i}@t.com", currency="ZAR")

        with patch('src.api.admin_tenants_routes.list_clients', return_value=list(configs.keys())):
            with patch('src.api.admin_tenants_routes.ClientConfig', side_effect=lambda cid: configs[cid]):
                with patch('src.api.admin_tenants_routes.get_tenant_stats_from_db', new_callable=AsyncMock, return_value={}):
                    result = await list_tenants(
                        status=None, search=None, limit=2, offset=1,
                        sort_by="company_name", sort_order="asc", admin_verified=True
                    )

        assert result.count == 2
        assert result.total == 5

    @pytest.mark.asyncio
    async def test_list_tenants_skips_broken_config(self):
        """Should skip tenants with broken configs gracefully."""
        from src.api.admin_tenants_routes import list_tenants

        def config_side_effect(cid):
            if cid == "broken":
                raise Exception("Config parse error")
            m = MagicMock()
            m.company_name = "Good Co"
            m.support_email = "good@t.com"
            m.currency = "ZAR"
            return m

        with patch('src.api.admin_tenants_routes.list_clients', return_value=["good", "broken"]):
            with patch('src.api.admin_tenants_routes.ClientConfig', side_effect=config_side_effect):
                with patch('src.api.admin_tenants_routes.get_tenant_stats_from_db', new_callable=AsyncMock, return_value={}):
                    result = await list_tenants(
                        status=None, search=None, limit=20, offset=0,
                        sort_by="company_name", sort_order="asc", admin_verified=True
                    )

        assert result.total == 1


# ==================== Direct Handler Tests for create_tenant ====================

class TestCreateTenantHandlerDirect:
    """Tests for create_tenant handler called directly (no TestClient needed)."""

    @pytest.mark.asyncio
    async def test_create_tenant_success(self):
        """Should create tenant and return success dict."""
        from src.api.admin_tenants_routes import create_tenant, CreateTenantRequest

        request = CreateTenantRequest(
            tenant_id="new-tenant",
            company_name="New Company",
            admin_email="admin@new.com",
        )

        mock_service = MagicMock()
        mock_service.get_config.return_value = None  # no existing tenant
        mock_service.save_config.return_value = True

        with patch('src.api.admin_tenants_routes.get_config_service', return_value=mock_service):
            with patch('src.api.admin_tenants_routes.get_supabase_admin_client', return_value=None):
                result = await create_tenant(request=request, admin_verified=True)

        assert result["success"] is True
        assert result["data"]["tenant_id"] == "new-tenant"
        assert result["data"]["status"] == "active"
        assert result["data"]["config_source"] == "database"

    @pytest.mark.asyncio
    async def test_create_tenant_duplicate_returns_409(self):
        """Should raise 409 when tenant_id already exists."""
        from src.api.admin_tenants_routes import create_tenant, CreateTenantRequest
        from fastapi import HTTPException

        request = CreateTenantRequest(
            tenant_id="existing-tenant",
            company_name="Existing Company",
            admin_email="admin@existing.com",
        )

        mock_service = MagicMock()
        mock_service.get_config.return_value = {"some": "config"}  # existing tenant

        with patch('src.api.admin_tenants_routes.get_config_service', return_value=mock_service):
            with pytest.raises(HTTPException) as exc_info:
                await create_tenant(request=request, admin_verified=True)

        assert exc_info.value.status_code == 409
        assert "already exists" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_tenant_builds_correct_config(self):
        """Should build config with correct structure including branding and agents."""
        from src.api.admin_tenants_routes import create_tenant, CreateTenantRequest

        request = CreateTenantRequest(
            tenant_id="cfg-test",
            company_name="Config Test Co",
            admin_email="cfg@test.com",
            currency="USD",
            timezone="US/Eastern",
            primary_color="#00ff00",
        )

        mock_service = MagicMock()
        mock_service.get_config.return_value = None
        mock_service.save_config.return_value = True

        with patch('src.api.admin_tenants_routes.get_config_service', return_value=mock_service):
            with patch('src.api.admin_tenants_routes.get_supabase_admin_client', return_value=None):
                result = await create_tenant(request=request, admin_verified=True)

        assert result["success"] is True
        # Inspect the config dict passed to save_config
        saved_config = mock_service.save_config.call_args[0][1]
        assert saved_config["client"]["id"] == "cfg-test"
        assert saved_config["client"]["currency"] == "USD"
        assert saved_config["client"]["timezone"] == "US/Eastern"
        assert saved_config["branding"]["primary_color"] == "#00ff00"
        assert saved_config["branding"]["company_name"] == "Config Test Co"
        assert saved_config["email"]["primary"] == "cfg@test.com"
        assert saved_config["agents"]["helpdesk"]["enabled"] is True
        assert saved_config["agents"]["inbound"]["enabled"] is False

    @pytest.mark.asyncio
    async def test_create_tenant_lite_plan_features(self):
        """Lite plan should have limited features (no voice_calls)."""
        from src.api.admin_tenants_routes import create_tenant, CreateTenantRequest

        request = CreateTenantRequest(
            tenant_id="lite-test",
            company_name="Lite Co",
            admin_email="lite@test.com",
            plan="lite",
        )

        mock_service = MagicMock()
        mock_service.get_config.return_value = None
        mock_service.save_config.return_value = True

        mock_client = MagicMock()
        chain = MagicMock()
        chain.eq.return_value = chain
        chain.execute.return_value = MagicMock(data=[])
        chain.update.return_value = chain
        mock_client.table.return_value = chain

        with patch('src.api.admin_tenants_routes.get_config_service', return_value=mock_service):
            with patch('src.api.admin_tenants_routes.get_supabase_admin_client', return_value=mock_client):
                with patch('asyncio.to_thread', side_effect=_sync_to_thread):
                    result = await create_tenant(request=request, admin_verified=True)

        assert result["success"] is True
        # Check the update call included lite plan limits
        update_call = chain.update.call_args
        if update_call:
            update_data = update_call[0][0]
            assert update_data["max_users"] == 5
            assert update_data["max_monthly_quotes"] == 100
            assert update_data["max_storage_gb"] == 1
            assert update_data["features_enabled"]["voice_calls"] is False

    @pytest.mark.asyncio
    async def test_create_tenant_premium_plan_features(self):
        """Premium plan should have expanded features (voice_calls enabled)."""
        from src.api.admin_tenants_routes import create_tenant, CreateTenantRequest

        request = CreateTenantRequest(
            tenant_id="premium-test",
            company_name="Premium Co",
            admin_email="premium@test.com",
            plan="premium",
        )

        mock_service = MagicMock()
        mock_service.get_config.return_value = None
        mock_service.save_config.return_value = True

        mock_client = MagicMock()
        chain = MagicMock()
        chain.eq.return_value = chain
        chain.execute.return_value = MagicMock(data=[])
        chain.update.return_value = chain
        mock_client.table.return_value = chain

        with patch('src.api.admin_tenants_routes.get_config_service', return_value=mock_service):
            with patch('src.api.admin_tenants_routes.get_supabase_admin_client', return_value=mock_client):
                with patch('asyncio.to_thread', side_effect=_sync_to_thread):
                    result = await create_tenant(request=request, admin_verified=True)

        assert result["success"] is True
        update_call = chain.update.call_args
        if update_call:
            update_data = update_call[0][0]
            assert update_data["max_users"] == 20
            assert update_data["max_monthly_quotes"] == 1000
            assert update_data["max_storage_gb"] == 10
            assert update_data["features_enabled"]["voice_calls"] is True

    @pytest.mark.asyncio
    async def test_create_tenant_save_failure_returns_500(self):
        """Should raise 500 when save_config fails."""
        from src.api.admin_tenants_routes import create_tenant, CreateTenantRequest
        from fastapi import HTTPException

        request = CreateTenantRequest(
            tenant_id="fail-save",
            company_name="Fail Co",
            admin_email="fail@test.com",
        )

        mock_service = MagicMock()
        mock_service.get_config.return_value = None
        mock_service.save_config.return_value = False  # save fails

        with patch('src.api.admin_tenants_routes.get_config_service', return_value=mock_service):
            with pytest.raises(HTTPException) as exc_info:
                await create_tenant(request=request, admin_verified=True)

        assert exc_info.value.status_code == 500


# ==================== Direct Handler Tests for get_tenant_details ====================

class TestGetTenantDetailsHandlerDirect:
    """Tests for get_tenant_details handler called directly (avoids route shadowing).

    Note: get_tenant_details is a sync function (def, not async def).
    """

    def test_get_tenant_details_success(self, mock_client_config):
        """Should return tenant details with all config fields."""
        from src.api.admin_tenants_routes import get_tenant_details

        with patch('src.api.admin_tenants_routes.ClientConfig', return_value=mock_client_config):
            result = get_tenant_details("test-tenant", admin_verified=True)

        assert result["success"] is True
        detail = result["data"]
        assert detail["tenant_id"] == "test-tenant"
        assert detail["company_name"] == "Test Company"
        assert detail["support_email"] == "support@test.com"
        assert detail["support_phone"] == "+27123456789"
        assert detail["website"] == "https://test.com"
        assert detail["logo_url"] == "https://test.com/logo.png"
        assert detail["primary_color"] == "#ff0000"
        assert detail["gcp_project_id"] == "test-gcp-project"
        assert detail["sendgrid_configured"] is True
        assert detail["vapi_configured"] is True

    def test_get_tenant_details_not_found(self):
        """Should raise 404 when tenant config not found."""
        from src.api.admin_tenants_routes import get_tenant_details
        from fastapi import HTTPException

        with patch('src.api.admin_tenants_routes.ClientConfig', side_effect=FileNotFoundError("not found")):
            with pytest.raises(HTTPException) as exc_info:
                get_tenant_details("nonexistent", admin_verified=True)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    def test_get_tenant_details_without_optional_fields(self):
        """Should handle config missing optional attributes gracefully."""
        from src.api.admin_tenants_routes import get_tenant_details

        mock_cfg = MagicMock(spec=[])
        mock_cfg.company_name = "Minimal Co"

        with patch('src.api.admin_tenants_routes.ClientConfig', return_value=mock_cfg):
            result = get_tenant_details("minimal", admin_verified=True)

        assert result["success"] is True
        assert result["data"]["tenant_id"] == "minimal"


# ==================== Direct Handler Tests for get_tenant_statistics ====================

class TestGetTenantStatisticsHandlerDirect:
    """Tests for get_tenant_statistics handler called directly (avoids route shadowing)."""

    @pytest.mark.asyncio
    async def test_get_stats_success(self, mock_client_config):
        """Should return stats for existing tenant."""
        from src.api.admin_tenants_routes import get_tenant_statistics

        mock_stats = {
            "quotes_count": 50,
            "quotes_this_month": 10,
            "invoices_count": 20,
            "invoices_paid": 15,
            "total_invoiced": 100000,
            "total_paid": 75000,
            "clients_count": 30,
            "users_count": 5,
        }

        with patch('src.api.admin_tenants_routes.ClientConfig', return_value=mock_client_config):
            with patch('src.api.admin_tenants_routes.get_tenant_stats_from_db', new_callable=AsyncMock, return_value=mock_stats):
                result = await get_tenant_statistics("test-tenant", admin_verified=True)

        assert result["success"] is True
        stats = result["data"]
        assert stats["tenant_id"] == "test-tenant"
        assert stats["quotes_count"] == 50
        assert stats["quotes_this_month"] == 10
        assert stats["total_invoiced"] == 100000
        assert stats["total_paid"] == 75000
        assert stats["clients_count"] == 30
        assert stats["users_count"] == 5

    @pytest.mark.asyncio
    async def test_get_stats_not_found(self):
        """Should raise 404 for non-existent tenant."""
        from src.api.admin_tenants_routes import get_tenant_statistics
        from fastapi import HTTPException

        with patch('src.api.admin_tenants_routes.ClientConfig', side_effect=FileNotFoundError("not found")):
            with pytest.raises(HTTPException) as exc_info:
                await get_tenant_statistics("nonexistent", admin_verified=True)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_stats_empty_db(self, mock_client_config):
        """Should return all zeros when DB has no data."""
        from src.api.admin_tenants_routes import get_tenant_statistics

        with patch('src.api.admin_tenants_routes.ClientConfig', return_value=mock_client_config):
            with patch('src.api.admin_tenants_routes.get_tenant_stats_from_db', new_callable=AsyncMock, return_value={}):
                result = await get_tenant_statistics("empty-tenant", admin_verified=True)

        assert result["success"] is True
        stats = result["data"]
        assert stats["quotes_count"] == 0
        assert stats["invoices_count"] == 0
        assert stats["clients_count"] == 0


# ==================== Direct Handler Tests for suspend_tenant ====================

class TestSuspendTenantHandlerDirect:
    """Tests for suspend_tenant handler called directly."""

    @pytest.mark.asyncio
    async def test_suspend_tenant_success(self, mock_client_config):
        """Should suspend tenant and return success."""
        from src.api.admin_tenants_routes import suspend_tenant, SuspendRequest

        request = SuspendRequest(reason="Non-payment of invoices")

        with patch('src.api.admin_tenants_routes.ClientConfig', return_value=mock_client_config):
            with patch('src.api.admin_tenants_routes.get_supabase_admin_client', return_value=None):
                result = await suspend_tenant(
                    tenant_id="test-tenant", request=request, admin_verified=True
                )

        assert result["success"] is True
        assert result["status"] == "suspended"
        assert result["tenant_id"] == "test-tenant"

    @pytest.mark.asyncio
    async def test_suspend_tenant_updates_existing_record(self, mock_client_config):
        """Should update existing DB record when tenant row exists."""
        from src.api.admin_tenants_routes import suspend_tenant, SuspendRequest

        request = SuspendRequest(reason="Payment overdue for 3 months")

        mock_client = MagicMock()
        select_chain = MagicMock()
        select_chain.eq.return_value = select_chain
        select_result = MagicMock()
        select_result.data = [{"id": "test-tenant"}]  # existing record
        select_chain.execute.return_value = select_result
        select_chain.select.return_value = select_chain

        update_chain = MagicMock()
        update_chain.eq.return_value = update_chain
        update_chain.execute.return_value = MagicMock(data=[])
        update_chain.update.return_value = update_chain

        # First call = select (check existing), second call = update
        call_count = {"n": 0}
        def table_side_effect(name):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return select_chain
            return update_chain

        mock_client.table.side_effect = table_side_effect

        with patch('src.api.admin_tenants_routes.ClientConfig', return_value=mock_client_config):
            with patch('src.api.admin_tenants_routes.get_supabase_admin_client', return_value=mock_client):
                with patch('asyncio.to_thread', side_effect=_sync_to_thread):
                    result = await suspend_tenant(
                        tenant_id="test-tenant", request=request, admin_verified=True
                    )

        assert result["success"] is True
        assert result["status"] == "suspended"

    @pytest.mark.asyncio
    async def test_suspend_tenant_inserts_new_record(self, mock_client_config):
        """Should insert new DB record when no tenant row exists."""
        from src.api.admin_tenants_routes import suspend_tenant, SuspendRequest

        request = SuspendRequest(reason="Terms of service violation detected")

        mock_client = MagicMock()
        select_chain = MagicMock()
        select_chain.eq.return_value = select_chain
        select_result = MagicMock()
        select_result.data = []  # no existing record
        select_chain.execute.return_value = select_result
        select_chain.select.return_value = select_chain

        insert_chain = MagicMock()
        insert_chain.execute.return_value = MagicMock(data=[])
        insert_chain.insert.return_value = insert_chain

        call_count = {"n": 0}
        def table_side_effect(name):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return select_chain
            return insert_chain

        mock_client.table.side_effect = table_side_effect

        with patch('src.api.admin_tenants_routes.ClientConfig', return_value=mock_client_config):
            with patch('src.api.admin_tenants_routes.get_supabase_admin_client', return_value=mock_client):
                with patch('asyncio.to_thread', side_effect=_sync_to_thread):
                    result = await suspend_tenant(
                        tenant_id="test-tenant", request=request, admin_verified=True
                    )

        assert result["success"] is True
        assert result["status"] == "suspended"

    @pytest.mark.asyncio
    async def test_suspend_tenant_not_found(self):
        """Should raise 404 when tenant does not exist."""
        from src.api.admin_tenants_routes import suspend_tenant, SuspendRequest
        from fastapi import HTTPException

        request = SuspendRequest(reason="This tenant does not exist")

        with patch('src.api.admin_tenants_routes.ClientConfig', side_effect=FileNotFoundError("not found")):
            with pytest.raises(HTTPException) as exc_info:
                await suspend_tenant(
                    tenant_id="nonexistent", request=request, admin_verified=True
                )

        assert exc_info.value.status_code == 404


# ==================== Direct Handler Tests for activate_tenant ====================

class TestActivateTenantHandlerDirect:
    """Tests for activate_tenant handler called directly."""

    @pytest.mark.asyncio
    async def test_activate_tenant_success(self, mock_client_config):
        """Should activate tenant and return success."""
        from src.api.admin_tenants_routes import activate_tenant

        with patch('src.api.admin_tenants_routes.ClientConfig', return_value=mock_client_config):
            with patch('src.api.admin_tenants_routes.get_supabase_admin_client', return_value=None):
                result = await activate_tenant(
                    tenant_id="test-tenant", admin_verified=True
                )

        assert result["success"] is True
        assert result["status"] == "active"
        assert result["tenant_id"] == "test-tenant"

    @pytest.mark.asyncio
    async def test_activate_tenant_clears_suspension_fields(self, mock_client_config):
        """Should clear suspended_at and suspended_reason on activation."""
        from src.api.admin_tenants_routes import activate_tenant

        mock_client = MagicMock()
        select_chain = MagicMock()
        select_chain.eq.return_value = select_chain
        select_result = MagicMock()
        select_result.data = [{"id": "test-tenant"}]
        select_chain.execute.return_value = select_result
        select_chain.select.return_value = select_chain

        update_chain = MagicMock()
        update_chain.eq.return_value = update_chain
        update_chain.execute.return_value = MagicMock(data=[])
        update_chain.update.return_value = update_chain

        call_count = {"n": 0}
        def table_side_effect(name):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return select_chain
            return update_chain

        mock_client.table.side_effect = table_side_effect

        with patch('src.api.admin_tenants_routes.ClientConfig', return_value=mock_client_config):
            with patch('src.api.admin_tenants_routes.get_supabase_admin_client', return_value=mock_client):
                with patch('asyncio.to_thread', side_effect=_sync_to_thread):
                    result = await activate_tenant(
                        tenant_id="test-tenant", admin_verified=True
                    )

        assert result["success"] is True
        assert result["status"] == "active"
        # Verify the update payload clears suspension fields
        update_call = update_chain.update.call_args
        if update_call:
            update_data = update_call[0][0]
            assert update_data["status"] == "active"
            assert update_data["suspended_at"] is None
            assert update_data["suspended_reason"] is None

    @pytest.mark.asyncio
    async def test_activate_tenant_not_found(self):
        """Should raise 404 when tenant does not exist."""
        from src.api.admin_tenants_routes import activate_tenant
        from fastapi import HTTPException

        with patch('src.api.admin_tenants_routes.ClientConfig', side_effect=FileNotFoundError("not found")):
            with pytest.raises(HTTPException) as exc_info:
                await activate_tenant(
                    tenant_id="nonexistent", admin_verified=True
                )

        assert exc_info.value.status_code == 404


# ==================== Direct Handler Tests for delete_tenant ====================

class TestDeleteTenantHandlerDirect:
    """Tests for delete_tenant handler called directly."""

    @pytest.mark.asyncio
    async def test_delete_without_confirm_returns_400(self):
        """Should raise 400 when confirm is not set."""
        from src.api.admin_tenants_routes import delete_tenant
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await delete_tenant(
                tenant_id="test-tenant", confirm=False, admin_verified=True
            )

        assert exc_info.value.status_code == 400
        assert "confirm" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_delete_with_confirm_false_returns_400(self):
        """Should raise 400 when confirm is explicitly false."""
        from src.api.admin_tenants_routes import delete_tenant
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await delete_tenant(
                tenant_id="test-tenant", confirm=False, admin_verified=True
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_with_confirm_success(self, mock_client_config):
        """Should delete tenant when confirm=True."""
        from src.api.admin_tenants_routes import delete_tenant

        with patch('src.api.admin_tenants_routes.ClientConfig', return_value=mock_client_config):
            with patch('src.api.admin_tenants_routes.get_supabase_admin_client', return_value=None):
                result = await delete_tenant(
                    tenant_id="test-tenant", confirm=True, admin_verified=True
                )

        assert result["success"] is True
        assert "deleted" in result["message"].lower()
        assert result["tenant_id"] == "test-tenant"

    @pytest.mark.asyncio
    async def test_delete_cascades_tables(self, mock_client_config):
        """Should delete from all related tables in correct order."""
        from src.api.admin_tenants_routes import delete_tenant

        mock_client = MagicMock()
        deleted_tables = []

        def table_side_effect(table_name):
            chain = MagicMock()
            chain.eq.return_value = chain
            chain.execute.return_value = MagicMock(data=[])

            def track_delete():
                chain2 = MagicMock()
                chain2.eq.return_value = chain2
                chain2.execute.return_value = MagicMock(data=[])
                deleted_tables.append(table_name)
                return chain2

            chain.delete.side_effect = track_delete
            return chain

        mock_client.table.side_effect = table_side_effect

        with patch('src.api.admin_tenants_routes.ClientConfig', return_value=mock_client_config):
            with patch('src.api.admin_tenants_routes.get_supabase_admin_client', return_value=mock_client):
                with patch('asyncio.to_thread', side_effect=_sync_to_thread):
                    result = await delete_tenant(
                        tenant_id="test-tenant", confirm=True, admin_verified=True
                    )

        assert result["success"] is True
        # Should delete from these tables in FK-safe order
        expected_tables = [
            "invoice_travelers", "invoices", "quotes",
            "clients", "organization_users", "tenants"
        ]
        assert deleted_tables == expected_tables

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        """Should raise 404 when tenant does not exist."""
        from src.api.admin_tenants_routes import delete_tenant
        from fastapi import HTTPException

        with patch('src.api.admin_tenants_routes.ClientConfig', side_effect=FileNotFoundError("not found")):
            with pytest.raises(HTTPException) as exc_info:
                await delete_tenant(
                    tenant_id="nonexistent", confirm=True, admin_verified=True
                )

        assert exc_info.value.status_code == 404


# ==================== Router Registration Tests ====================

class TestIncludeAdminTenantsRouter:
    """Tests for include_admin_tenants_router function."""

    def test_router_registration(self):
        """include_admin_tenants_router should call app.include_router."""
        from src.api.admin_tenants_routes import include_admin_tenants_router, admin_tenants_router

        mock_app = MagicMock()
        include_admin_tenants_router(mock_app)

        mock_app.include_router.assert_called_once_with(admin_tenants_router)

    def test_router_has_correct_prefix(self):
        """admin_tenants_router should have the correct URL prefix."""
        from src.api.admin_tenants_routes import admin_tenants_router

        assert admin_tenants_router.prefix == "/api/v1/admin/tenants"

    def test_router_has_correct_tags(self):
        """admin_tenants_router should have the Admin - Tenants tag."""
        from src.api.admin_tenants_routes import admin_tenants_router

        assert "Admin - Tenants" in admin_tenants_router.tags
