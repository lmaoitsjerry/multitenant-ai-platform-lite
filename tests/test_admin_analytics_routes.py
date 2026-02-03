"""
Admin Analytics Routes Unit Tests

Tests for platform-wide admin analytics API models and functions.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
from fastapi.testclient import TestClient


# ==================== Pydantic Models Tests ====================

class TestPlatformOverviewModel:
    """Tests for PlatformOverview model."""

    def test_default_values(self):
        """PlatformOverview should have sensible defaults."""
        from src.api.admin_analytics_routes import PlatformOverview

        overview = PlatformOverview()

        assert overview.total_tenants == 0
        assert overview.active_tenants == 0
        assert overview.total_quotes == 0
        assert overview.total_revenue == 0

    def test_with_all_fields(self):
        """PlatformOverview should accept all fields."""
        from src.api.admin_analytics_routes import PlatformOverview

        overview = PlatformOverview(
            total_tenants=10,
            active_tenants=8,
            suspended_tenants=1,
            trial_tenants=1,
            total_quotes=500,
            quotes_this_month=50,
            quotes_last_month=45,
            total_invoices=200,
            invoices_paid=180,
            invoices_paid_this_month=20,
            invoices_pending=20,
            total_revenue=50000.0,
            revenue_this_month=5000.0,
            total_users=25,
            total_clients=100,
            total_crm_clients=100,
            tenant_growth_percent=5.5,
            quote_growth_percent=11.1
        )

        assert overview.total_tenants == 10
        assert overview.active_tenants == 8
        assert overview.total_revenue == 50000.0
        assert overview.quote_growth_percent == 11.1

    def test_model_dump(self):
        """PlatformOverview should serialize correctly."""
        from src.api.admin_analytics_routes import PlatformOverview

        overview = PlatformOverview(total_tenants=5, total_quotes=100)
        data = overview.model_dump()

        assert isinstance(data, dict)
        assert data["total_tenants"] == 5
        assert data["total_quotes"] == 100


class TestUsageDataPointModel:
    """Tests for UsageDataPoint model."""

    def test_requires_date(self):
        """UsageDataPoint should require date."""
        from src.api.admin_analytics_routes import UsageDataPoint

        data_point = UsageDataPoint(date="2026-01-15")

        assert data_point.date == "2026-01-15"
        assert data_point.quotes == 0
        assert data_point.invoices == 0
        assert data_point.emails == 0
        assert data_point.logins == 0

    def test_with_all_metrics(self):
        """UsageDataPoint should accept all metrics."""
        from src.api.admin_analytics_routes import UsageDataPoint

        data_point = UsageDataPoint(
            date="2026-01-15",
            quotes=10,
            invoices=5,
            emails=20,
            logins=15
        )

        assert data_point.quotes == 10
        assert data_point.invoices == 5


class TestTopTenantModel:
    """Tests for TopTenant model."""

    def test_required_fields(self):
        """TopTenant should require all fields."""
        from src.api.admin_analytics_routes import TopTenant

        tenant = TopTenant(
            tenant_id="test-tenant",
            company_name="Test Company",
            value=1000.0,
            rank=1
        )

        assert tenant.tenant_id == "test-tenant"
        assert tenant.company_name == "Test Company"
        assert tenant.value == 1000.0
        assert tenant.rank == 1


class TestTenantUsageStatsModel:
    """Tests for TenantUsageStats model."""

    def test_default_values(self):
        """TenantUsageStats should have defaults for counts."""
        from src.api.admin_analytics_routes import TenantUsageStats

        stats = TenantUsageStats(
            tenant_id="test",
            company_name="Test Co"
        )

        assert stats.quotes_count == 0
        assert stats.invoices_count == 0
        assert stats.total_revenue == 0

    def test_with_all_fields(self):
        """TenantUsageStats should accept all fields."""
        from src.api.admin_analytics_routes import TenantUsageStats

        stats = TenantUsageStats(
            tenant_id="test",
            company_name="Test Co",
            quotes_count=50,
            invoices_count=30,
            invoices_paid=25,
            total_revenue=15000.0,
            users_count=5,
            clients_count=20
        )

        assert stats.quotes_count == 50
        assert stats.total_revenue == 15000.0


class TestGrowthMetricsModel:
    """Tests for GrowthMetrics model."""

    def test_default_values(self):
        """GrowthMetrics should have zero defaults."""
        from src.api.admin_analytics_routes import GrowthMetrics

        metrics = GrowthMetrics()

        assert metrics.new_tenants_this_week == 0
        assert metrics.new_tenants_this_month == 0
        assert metrics.growth_rate_percent == 0
        assert metrics.churn_rate_percent == 0

    def test_with_values(self):
        """GrowthMetrics should accept all values."""
        from src.api.admin_analytics_routes import GrowthMetrics

        metrics = GrowthMetrics(
            new_tenants_this_week=2,
            new_tenants_this_month=8,
            new_tenants_last_month=5,
            growth_rate_percent=60.0,
            churn_rate_percent=5.0
        )

        assert metrics.new_tenants_this_month == 8
        assert metrics.growth_rate_percent == 60.0


# ==================== Cache Functions Tests ====================

class TestCacheFunctions:
    """Tests for caching functions."""

    def test_get_cached_returns_none_for_missing_key(self):
        """get_cached should return None for non-existent key."""
        from src.api.admin_analytics_routes import get_cached, _cache

        # Clear cache
        _cache.clear()

        result = get_cached("nonexistent")

        assert result is None

    def test_set_and_get_cached(self):
        """set_cached and get_cached should work together."""
        from src.api.admin_analytics_routes import get_cached, set_cached, _cache

        _cache.clear()

        test_data = {"key": "value", "count": 42}
        set_cached("test_key", test_data)

        result = get_cached("test_key")

        assert result == test_data

    def test_cache_expires(self):
        """Cached items should expire after TTL."""
        from src.api.admin_analytics_routes import get_cached, set_cached, _cache

        _cache.clear()

        # Set with very short TTL
        set_cached("short_ttl", "data", ttl=0)

        # Should be expired immediately
        result = get_cached("short_ttl")

        assert result is None

    def test_cache_respects_ttl(self):
        """Cached items should be available within TTL."""
        from src.api.admin_analytics_routes import get_cached, set_cached, _cache

        _cache.clear()

        # Set with long TTL
        set_cached("long_ttl", "data", ttl=3600)

        result = get_cached("long_ttl")

        assert result == "data"

    def test_expired_cache_is_deleted(self):
        """Expired cache entries should be removed."""
        from src.api.admin_analytics_routes import get_cached, _cache
        from datetime import datetime, timedelta

        _cache.clear()

        # Manually add an expired entry
        _cache["expired"] = {
            "data": "old_data",
            "expires": datetime.now() - timedelta(seconds=10)
        }

        # Get should remove it
        result = get_cached("expired")

        assert result is None
        assert "expired" not in _cache


# ==================== Helper Function Tests ====================

class TestGetSupabaseAdminClient:
    """Tests for get_supabase_admin_client helper."""

    def test_returns_none_without_env_vars(self):
        """Should return None when env vars not set."""
        from src.api.admin_analytics_routes import get_supabase_admin_client

        with patch.dict('os.environ', {}, clear=True):
            result = get_supabase_admin_client()

        assert result is None

    def test_returns_client_with_env_vars(self):
        """Should return client when env vars are set."""
        from src.api.admin_analytics_routes import get_supabase_admin_client

        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_KEY': 'test-key'
        }):
            with patch('supabase.create_client') as mock_create:
                mock_client = MagicMock()
                mock_create.return_value = mock_client

                result = get_supabase_admin_client()

                mock_create.assert_called_once_with(
                    'https://test.supabase.co',
                    'test-key'
                )
                assert result is mock_client


class TestGetAllQuotesStats:
    """Tests for get_all_quotes_stats helper."""

    @pytest.mark.asyncio
    async def test_returns_zeros_without_client(self):
        """Should return zeros when no Supabase client."""
        from src.api.admin_analytics_routes import get_all_quotes_stats

        with patch('src.api.admin_analytics_routes.get_supabase_admin_client') as mock:
            mock.return_value = None

            result = await get_all_quotes_stats()

            assert result == {"total": 0, "this_month": 0, "last_month": 0}

    @pytest.mark.asyncio
    async def test_handles_exception(self):
        """Should handle exceptions gracefully."""
        from src.api.admin_analytics_routes import get_all_quotes_stats

        with patch('src.api.admin_analytics_routes.get_supabase_admin_client') as mock:
            mock_client = MagicMock()
            mock_client.table.side_effect = Exception("DB Error")
            mock.return_value = mock_client

            result = await get_all_quotes_stats()

            assert result == {"total": 0, "this_month": 0, "last_month": 0}


class TestGetAllInvoicesStats:
    """Tests for get_all_invoices_stats helper."""

    @pytest.mark.asyncio
    async def test_returns_zeros_without_client(self):
        """Should return zeros when no Supabase client."""
        from src.api.admin_analytics_routes import get_all_invoices_stats

        with patch('src.api.admin_analytics_routes.get_supabase_admin_client') as mock:
            mock.return_value = None

            result = await get_all_invoices_stats()

            assert result["total"] == 0
            assert result["paid"] == 0
            assert result["total_amount"] == 0


class TestGetUserAndClientCounts:
    """Tests for get_user_and_client_counts helper."""

    @pytest.mark.asyncio
    async def test_returns_zeros_without_client(self):
        """Should return zeros when no Supabase client."""
        from src.api.admin_analytics_routes import get_user_and_client_counts

        with patch('src.api.admin_analytics_routes.get_supabase_admin_client') as mock:
            mock.return_value = None

            result = await get_user_and_client_counts()

            assert result == {"users": 0, "clients": 0}


# ==================== Endpoint Tests ====================

class TestEndpointsAuth:
    """Tests for endpoint authentication."""

    @pytest.fixture
    def test_client(self):
        """Create test client."""
        from main import app
        return TestClient(app)

    def test_overview_requires_admin_token(self, test_client):
        """GET /admin/analytics/overview should require admin token."""
        response = test_client.get("/api/v1/admin/analytics/overview")

        # Should fail without admin token
        assert response.status_code in [401, 403, 503]

    def test_usage_requires_admin_token(self, test_client):
        """GET /admin/analytics/usage should require admin token."""
        response = test_client.get("/api/v1/admin/analytics/usage")

        assert response.status_code in [401, 403, 503]

    def test_top_tenants_requires_admin_token(self, test_client):
        """GET /admin/analytics/tenants/top should require admin token."""
        response = test_client.get("/api/v1/admin/analytics/tenants/top")

        assert response.status_code in [401, 403, 503]

    def test_growth_requires_admin_token(self, test_client):
        """GET /admin/analytics/growth should require admin token."""
        response = test_client.get("/api/v1/admin/analytics/growth")

        assert response.status_code in [401, 403, 503]


class TestEndpointResponses:
    """Tests for endpoint response structure."""

    @pytest.fixture
    def test_client(self):
        """Create test client."""
        from main import app
        return TestClient(app)

    def test_overview_invalid_token_error(self, test_client):
        """Overview with invalid token should return error."""
        response = test_client.get(
            "/api/v1/admin/analytics/overview",
            headers={"X-Admin-Token": "invalid-token"}
        )

        # Should be authentication error (503 when token not configured, 401/403 otherwise)
        assert response.status_code in [401, 403, 503]

    def test_usage_accepts_period_param(self, test_client):
        """Usage endpoint should accept period parameter."""
        response = test_client.get(
            "/api/v1/admin/analytics/usage",
            params={"period": "7d"},
            headers={"X-Admin-Token": "invalid"}
        )

        # Auth should fail before processing, but endpoint exists
        assert response.status_code in [401, 403, 503]

    def test_top_tenants_accepts_metric_param(self, test_client):
        """Top tenants should accept metric parameter."""
        response = test_client.get(
            "/api/v1/admin/analytics/tenants/top",
            params={"metric": "revenue", "limit": 5},
            headers={"X-Admin-Token": "invalid"}
        )

        assert response.status_code in [401, 403, 503]


# ==================== Constants Tests ====================

class TestConstants:
    """Tests for module constants."""

    def test_cache_ttl_defined(self):
        """CACHE_TTL_SECONDS should be defined."""
        from src.api.admin_analytics_routes import CACHE_TTL_SECONDS

        assert isinstance(CACHE_TTL_SECONDS, int)
        assert CACHE_TTL_SECONDS > 0

    def test_cache_ttl_reasonable(self):
        """CACHE_TTL_SECONDS should be a reasonable value."""
        from src.api.admin_analytics_routes import CACHE_TTL_SECONDS

        # Should be between 10 seconds and 10 minutes
        assert 10 <= CACHE_TTL_SECONDS <= 600
