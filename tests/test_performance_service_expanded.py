"""
Performance Service Expanded Tests

Comprehensive tests for the PerformanceService class:
- get_consultant_rankings() with data processing
- get_consultant_performance() lookup
- get_performance_summary() aggregation
- Conversion counting logic (paid + departed)
- Period filtering
- Metric sorting

Uses mocked Supabase for isolated unit testing.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

from src.services.performance_service import PerformanceService, ConsultantPerformance


# ==================== Fixtures ====================

@pytest.fixture
def mock_supabase():
    """Create a mock SupabaseTool."""
    mock = MagicMock()
    mock.tenant_id = "test_tenant"
    mock.client = MagicMock()
    return mock


@pytest.fixture
def sample_consultants():
    """Sample consultant users."""
    return [
        {"id": "consultant_1", "name": "Alice Johnson", "email": "alice@example.com", "role": "consultant"},
        {"id": "consultant_2", "name": "Bob Smith", "email": "bob@example.com", "role": "consultant"},
        {"id": "consultant_3", "name": "Carol Davis", "email": "carol@example.com", "role": "consultant"},
        {"id": "admin_1", "name": "Admin User", "email": "admin@example.com", "role": "admin"},  # Not a consultant
    ]


@pytest.fixture
def sample_quotes():
    """Sample quotes data."""
    now = datetime.utcnow()
    past_date = (now - timedelta(days=30)).isoformat()
    future_date = (now + timedelta(days=30)).isoformat()

    return [
        {"quote_id": "QT-001", "consultant_id": "consultant_1", "check_out_date": past_date, "created_at": now.isoformat()},
        {"quote_id": "QT-002", "consultant_id": "consultant_1", "check_out_date": past_date, "created_at": now.isoformat()},
        {"quote_id": "QT-003", "consultant_id": "consultant_1", "check_out_date": future_date, "created_at": now.isoformat()},  # Future
        {"quote_id": "QT-004", "consultant_id": "consultant_2", "check_out_date": past_date, "created_at": now.isoformat()},
        {"quote_id": "QT-005", "consultant_id": "consultant_2", "check_out_date": past_date, "created_at": now.isoformat()},
        {"quote_id": "QT-006", "consultant_id": "consultant_3", "check_out_date": past_date, "created_at": now.isoformat()},
    ]


@pytest.fixture
def sample_invoices():
    """Sample invoices data."""
    return [
        {"quote_id": "QT-001", "status": "paid", "total_amount": 5000, "consultant_id": "consultant_1"},
        {"quote_id": "QT-002", "status": "paid", "total_amount": 7500, "consultant_id": "consultant_1"},
        {"quote_id": "QT-003", "status": "paid", "total_amount": 3000, "consultant_id": "consultant_1"},  # Future checkout
        {"quote_id": "QT-004", "status": "sent", "total_amount": 4000, "consultant_id": "consultant_2"},  # Not paid
        {"quote_id": "QT-005", "status": "paid", "total_amount": 6000, "consultant_id": "consultant_2"},
    ]


# ==================== Initialization Tests ====================

class TestPerformanceServiceInit:
    """Test PerformanceService initialization."""

    def test_service_initialization(self, mock_supabase):
        """Service should initialize with SupabaseTool."""
        service = PerformanceService(mock_supabase)

        assert service.db == mock_supabase
        assert service.tenant_id == "test_tenant"

    def test_valid_periods(self):
        """Valid periods should be defined."""
        assert "week" in PerformanceService.VALID_PERIODS
        assert "month" in PerformanceService.VALID_PERIODS
        assert "quarter" in PerformanceService.VALID_PERIODS
        assert "year" in PerformanceService.VALID_PERIODS
        assert "all" in PerformanceService.VALID_PERIODS

    def test_valid_metrics(self):
        """Valid metrics should be defined."""
        assert "conversions" in PerformanceService.VALID_METRICS
        assert "revenue" in PerformanceService.VALID_METRICS
        assert "quotes" in PerformanceService.VALID_METRICS


# ==================== Period Start Calculation Tests ====================

class TestPeriodStartCalculation:
    """Test _get_period_start calculations."""

    def test_week_start(self, mock_supabase):
        """Week should start on Monday."""
        service = PerformanceService(mock_supabase)
        start = service._get_period_start("week")

        # Should be a Monday (weekday 0)
        assert start.weekday() == 0
        assert start.hour == 0
        assert start.minute == 0

    def test_month_start(self, mock_supabase):
        """Month should start on day 1."""
        service = PerformanceService(mock_supabase)
        start = service._get_period_start("month")

        assert start.day == 1
        assert start.hour == 0
        assert start.minute == 0

    def test_quarter_start(self, mock_supabase):
        """Quarter should start on Q1/Q2/Q3/Q4 month."""
        service = PerformanceService(mock_supabase)
        start = service._get_period_start("quarter")

        assert start.month in [1, 4, 7, 10]
        assert start.day == 1
        assert start.hour == 0

    def test_year_start(self, mock_supabase):
        """Year should start on January 1."""
        service = PerformanceService(mock_supabase)
        start = service._get_period_start("year")

        now = datetime.utcnow()
        assert start.year == now.year
        assert start.month == 1
        assert start.day == 1

    def test_all_time_start(self, mock_supabase):
        """All-time should start from 2020."""
        service = PerformanceService(mock_supabase)
        start = service._get_period_start("all")

        assert start.year == 2020
        assert start.month == 1
        assert start.day == 1


# ==================== Consultant Rankings Tests ====================

class TestConsultantRankings:
    """Test get_consultant_rankings method."""

    def test_rankings_with_no_consultants(self, mock_supabase):
        """Empty consultant list should return empty rankings."""
        mock_supabase.get_organization_users.return_value = []

        service = PerformanceService(mock_supabase)
        rankings = service.get_consultant_rankings()

        assert rankings == []

    def test_rankings_filter_non_consultants(self, mock_supabase, sample_consultants):
        """Only consultants should appear in rankings."""
        mock_supabase.get_organization_users.return_value = sample_consultants
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = Mock(data=[])

        service = PerformanceService(mock_supabase)
        rankings = service.get_consultant_rankings()

        # Admin should not be in rankings
        consultant_ids = [r["consultant_id"] for r in rankings]
        assert "admin_1" not in consultant_ids

    def test_rankings_count_quotes_per_consultant(self, mock_supabase, sample_consultants, sample_quotes):
        """Quote counts should be calculated per consultant."""
        mock_supabase.get_organization_users.return_value = sample_consultants
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = Mock(data=sample_quotes)
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = Mock(data=[])

        service = PerformanceService(mock_supabase)
        rankings = service.get_consultant_rankings()

        # Find Alice (consultant_1) - has 3 quotes
        alice = next(r for r in rankings if r["consultant_id"] == "consultant_1")
        assert alice["quote_count"] == 3

        # Find Bob (consultant_2) - has 2 quotes
        bob = next(r for r in rankings if r["consultant_id"] == "consultant_2")
        assert bob["quote_count"] == 2

    def test_rankings_count_conversions(self, mock_supabase, sample_consultants, sample_quotes, sample_invoices):
        """Conversions should only count paid invoices with past checkout dates."""
        mock_supabase.get_organization_users.return_value = sample_consultants
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = Mock(data=sample_quotes)
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = Mock(data=sample_invoices)

        service = PerformanceService(mock_supabase)
        rankings = service.get_consultant_rankings()

        # Alice has 2 conversions (QT-001, QT-002 paid with past dates)
        # QT-003 is paid but future checkout, should not count
        alice = next(r for r in rankings if r["consultant_id"] == "consultant_1")
        assert alice["conversions"] == 2

        # Bob has 1 conversion (QT-005 paid with past date)
        # QT-004 is not paid
        bob = next(r for r in rankings if r["consultant_id"] == "consultant_2")
        assert bob["conversions"] == 1

    def test_rankings_calculate_revenue(self, mock_supabase, sample_consultants, sample_quotes, sample_invoices):
        """Revenue should sum total_amount from conversions."""
        mock_supabase.get_organization_users.return_value = sample_consultants
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = Mock(data=sample_quotes)
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = Mock(data=sample_invoices)

        service = PerformanceService(mock_supabase)
        rankings = service.get_consultant_rankings()

        # Alice: 5000 + 7500 = 12500 (QT-003 is future, not counted)
        alice = next(r for r in rankings if r["consultant_id"] == "consultant_1")
        assert alice["revenue"] == 12500.0

        # Bob: 6000 (only QT-005 is paid)
        bob = next(r for r in rankings if r["consultant_id"] == "consultant_2")
        assert bob["revenue"] == 6000.0

    def test_rankings_calculate_conversion_rate(self, mock_supabase, sample_consultants, sample_quotes, sample_invoices):
        """Conversion rate should be (conversions / quotes) * 100."""
        mock_supabase.get_organization_users.return_value = sample_consultants
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = Mock(data=sample_quotes)
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = Mock(data=sample_invoices)

        service = PerformanceService(mock_supabase)
        rankings = service.get_consultant_rankings()

        # Alice: 2/3 = 66.7%
        alice = next(r for r in rankings if r["consultant_id"] == "consultant_1")
        assert alice["conversion_rate"] == 66.7

        # Bob: 1/2 = 50%
        bob = next(r for r in rankings if r["consultant_id"] == "consultant_2")
        assert bob["conversion_rate"] == 50.0

    def test_rankings_sort_by_conversions(self, mock_supabase, sample_consultants, sample_quotes, sample_invoices):
        """Default sorting should be by conversions."""
        mock_supabase.get_organization_users.return_value = sample_consultants
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = Mock(data=sample_quotes)
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = Mock(data=sample_invoices)

        service = PerformanceService(mock_supabase)
        rankings = service.get_consultant_rankings(metric="conversions")

        # Alice has most conversions, should be first
        assert rankings[0]["consultant_id"] == "consultant_1"

    def test_rankings_sort_by_revenue(self, mock_supabase, sample_consultants, sample_quotes, sample_invoices):
        """Revenue sorting should work."""
        mock_supabase.get_organization_users.return_value = sample_consultants
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = Mock(data=sample_quotes)
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = Mock(data=sample_invoices)

        service = PerformanceService(mock_supabase)
        rankings = service.get_consultant_rankings(metric="revenue")

        # Alice has most revenue, should be first
        assert rankings[0]["consultant_id"] == "consultant_1"

    def test_rankings_sort_by_quotes(self, mock_supabase, sample_consultants, sample_quotes, sample_invoices):
        """Quote count sorting should work."""
        mock_supabase.get_organization_users.return_value = sample_consultants
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = Mock(data=sample_quotes)
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = Mock(data=sample_invoices)

        service = PerformanceService(mock_supabase)
        rankings = service.get_consultant_rankings(metric="quotes")

        # Alice has most quotes (3), should be first
        assert rankings[0]["consultant_id"] == "consultant_1"

    def test_rankings_assign_rank_numbers(self, mock_supabase, sample_consultants, sample_quotes, sample_invoices):
        """Rankings should have sequential rank numbers."""
        mock_supabase.get_organization_users.return_value = sample_consultants
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = Mock(data=sample_quotes)
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = Mock(data=sample_invoices)

        service = PerformanceService(mock_supabase)
        rankings = service.get_consultant_rankings()

        ranks = [r["rank"] for r in rankings]
        assert ranks == [1, 2, 3]

    def test_rankings_invalid_period_normalized(self, mock_supabase, sample_consultants):
        """Invalid period should be normalized to 'month'."""
        mock_supabase.get_organization_users.return_value = sample_consultants
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = Mock(data=[])

        service = PerformanceService(mock_supabase)
        # Should not raise
        rankings = service.get_consultant_rankings(period="invalid")
        assert isinstance(rankings, list)

    def test_rankings_invalid_metric_normalized(self, mock_supabase, sample_consultants):
        """Invalid metric should be normalized to 'conversions'."""
        mock_supabase.get_organization_users.return_value = sample_consultants
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = Mock(data=[])

        service = PerformanceService(mock_supabase)
        # Should not raise
        rankings = service.get_consultant_rankings(metric="invalid")
        assert isinstance(rankings, list)

    def test_rankings_respect_limit(self, mock_supabase, sample_consultants, sample_quotes, sample_invoices):
        """Rankings should respect limit parameter."""
        mock_supabase.get_organization_users.return_value = sample_consultants
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = Mock(data=sample_quotes)
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = Mock(data=sample_invoices)

        service = PerformanceService(mock_supabase)
        rankings = service.get_consultant_rankings(limit=2)

        assert len(rankings) == 2

    def test_rankings_handle_database_error(self, mock_supabase, sample_consultants):
        """Database errors should return empty list."""
        mock_supabase.get_organization_users.return_value = sample_consultants
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.side_effect = Exception("DB Error")

        service = PerformanceService(mock_supabase)
        rankings = service.get_consultant_rankings()

        assert rankings == []


# ==================== Consultant Performance Tests ====================

class TestConsultantPerformance:
    """Test get_consultant_performance method."""

    def test_get_specific_consultant(self, mock_supabase, sample_consultants, sample_quotes, sample_invoices):
        """Should return specific consultant's performance."""
        mock_supabase.get_organization_users.return_value = sample_consultants
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = Mock(data=sample_quotes)
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = Mock(data=sample_invoices)

        service = PerformanceService(mock_supabase)
        result = service.get_consultant_performance("consultant_2")

        assert result is not None
        assert result["consultant_id"] == "consultant_2"
        assert result["name"] == "Bob Smith"

    def test_get_nonexistent_consultant(self, mock_supabase, sample_consultants, sample_quotes):
        """Should return None for nonexistent consultant."""
        mock_supabase.get_organization_users.return_value = sample_consultants
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = Mock(data=sample_quotes)
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = Mock(data=[])

        service = PerformanceService(mock_supabase)
        result = service.get_consultant_performance("nonexistent")

        assert result is None


# ==================== Performance Summary Tests ====================

class TestPerformanceSummary:
    """Test get_performance_summary method."""

    def test_summary_totals(self, mock_supabase, sample_consultants, sample_quotes, sample_invoices):
        """Summary should have correct totals."""
        mock_supabase.get_organization_users.return_value = sample_consultants
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = Mock(data=sample_quotes)
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = Mock(data=sample_invoices)

        service = PerformanceService(mock_supabase)
        summary = service.get_performance_summary()

        # Alice: 2 conversions, Bob: 1, Carol: 0 = 3 total
        assert summary["total_conversions"] == 3

        # Alice: 12500, Bob: 6000 = 18500 total
        assert summary["total_revenue"] == 18500.0

        # 6 total quotes
        assert summary["total_quotes"] == 6

    def test_summary_active_consultants(self, mock_supabase, sample_consultants, sample_quotes, sample_invoices):
        """Active consultants should only count those with quotes."""
        mock_supabase.get_organization_users.return_value = sample_consultants
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = Mock(data=sample_quotes)
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = Mock(data=sample_invoices)

        service = PerformanceService(mock_supabase)
        summary = service.get_performance_summary()

        # All 3 consultants have quotes
        assert summary["active_consultants"] == 3

    def test_summary_conversion_rate(self, mock_supabase, sample_consultants, sample_quotes, sample_invoices):
        """Average conversion rate should be calculated correctly."""
        mock_supabase.get_organization_users.return_value = sample_consultants
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = Mock(data=sample_quotes)
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = Mock(data=sample_invoices)

        service = PerformanceService(mock_supabase)
        summary = service.get_performance_summary()

        # 3 conversions / 6 quotes = 50%
        assert summary["avg_conversion_rate"] == 50.0

    def test_summary_top_performer(self, mock_supabase, sample_consultants, sample_quotes, sample_invoices):
        """Top performer should be included."""
        mock_supabase.get_organization_users.return_value = sample_consultants
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = Mock(data=sample_quotes)
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = Mock(data=sample_invoices)

        service = PerformanceService(mock_supabase)
        summary = service.get_performance_summary()

        assert summary["top_performer"] is not None
        assert summary["top_performer"]["consultant_id"] == "consultant_1"

    def test_summary_no_data(self, mock_supabase):
        """Summary with no data should have zeros."""
        mock_supabase.get_organization_users.return_value = []

        service = PerformanceService(mock_supabase)
        summary = service.get_performance_summary()

        assert summary["total_conversions"] == 0
        assert summary["total_revenue"] == 0
        assert summary["total_quotes"] == 0
        assert summary["active_consultants"] == 0
        assert summary["top_performer"] is None

    def test_summary_includes_period(self, mock_supabase):
        """Summary should include the period."""
        mock_supabase.get_organization_users.return_value = []

        service = PerformanceService(mock_supabase)
        summary = service.get_performance_summary(period="quarter")

        assert summary["period"] == "quarter"


# ==================== Dataclass Tests ====================

class TestConsultantPerformanceDataclass:
    """Test ConsultantPerformance dataclass."""

    def test_create_performance_record(self):
        """Should create performance record."""
        perf = ConsultantPerformance(
            consultant_id="user_1",
            name="Test User",
            email="test@example.com",
            conversions=5,
            revenue=25000.0,
            quote_count=10,
            conversion_rate=50.0,
            rank=1
        )

        assert perf.consultant_id == "user_1"
        assert perf.conversions == 5
        assert perf.revenue == 25000.0
        assert perf.rank == 1

    def test_default_rank(self):
        """Default rank should be 0."""
        perf = ConsultantPerformance(
            consultant_id="user_1",
            name="Test",
            email="test@example.com",
            conversions=0,
            revenue=0.0,
            quote_count=0,
            conversion_rate=0.0
        )

        assert perf.rank == 0


# ==================== Edge Case Tests ====================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_null_total_amount(self, mock_supabase, sample_consultants, sample_quotes):
        """Null total_amount should be treated as 0."""
        mock_supabase.get_organization_users.return_value = sample_consultants
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = Mock(data=sample_quotes)

        invoices = [{"quote_id": "QT-001", "status": "paid", "total_amount": None, "consultant_id": "consultant_1"}]
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = Mock(data=invoices)

        service = PerformanceService(mock_supabase)
        rankings = service.get_consultant_rankings()

        alice = next(r for r in rankings if r["consultant_id"] == "consultant_1")
        assert alice["revenue"] == 0.0

    def test_invalid_checkout_date_format(self, mock_supabase, sample_consultants):
        """Invalid checkout date should still count conversion."""
        mock_supabase.get_organization_users.return_value = sample_consultants

        quotes = [{"quote_id": "QT-001", "consultant_id": "consultant_1", "check_out_date": "invalid-date", "created_at": datetime.utcnow().isoformat()}]
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = Mock(data=quotes)

        invoices = [{"quote_id": "QT-001", "status": "paid", "total_amount": 1000, "consultant_id": "consultant_1"}]
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = Mock(data=invoices)

        service = PerformanceService(mock_supabase)
        rankings = service.get_consultant_rankings()

        alice = next(r for r in rankings if r["consultant_id"] == "consultant_1")
        # Should still count as conversion with the revenue
        assert alice["conversions"] == 1
        assert alice["revenue"] == 1000.0

    def test_no_quotes_in_period(self, mock_supabase, sample_consultants):
        """No quotes in period should show zero stats."""
        mock_supabase.get_organization_users.return_value = sample_consultants
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = Mock(data=[])

        service = PerformanceService(mock_supabase)
        rankings = service.get_consultant_rankings()

        # All consultants should have 0 stats
        for consultant in rankings:
            assert consultant["quote_count"] == 0
            assert consultant["conversions"] == 0
            assert consultant["revenue"] == 0.0
