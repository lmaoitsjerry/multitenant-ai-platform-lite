"""
Tests for PerformanceService - Consultant Performance Tracking

Tests cover:
- Period start date calculations
- Consultant rankings
- Individual consultant performance
- Organization performance summary
- Conversion rate calculations
- Edge cases and error handling
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from freezegun import freeze_time

from src.services.performance_service import PerformanceService, ConsultantPerformance


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_supabase_tool():
    """Create a mock SupabaseTool."""
    mock = MagicMock()
    mock.tenant_id = "tenant-123"
    return mock


@pytest.fixture
def performance_service(mock_supabase_tool):
    """Create a PerformanceService instance with mocked dependencies."""
    return PerformanceService(mock_supabase_tool)


@pytest.fixture
def sample_consultants():
    """Sample consultant data."""
    return [
        {"id": "cons-1", "name": "Alice Smith", "email": "alice@example.com", "role": "consultant"},
        {"id": "cons-2", "name": "Bob Jones", "email": "bob@example.com", "role": "consultant"},
        {"id": "cons-3", "name": "Carol White", "email": "carol@example.com", "role": "consultant"},
        {"id": "admin-1", "name": "Admin User", "email": "admin@example.com", "role": "admin"},
    ]


@pytest.fixture
def sample_quotes():
    """Sample quote data."""
    return [
        {"quote_id": "q1", "consultant_id": "cons-1", "check_out_date": "2024-01-15", "created_at": "2024-01-01T10:00:00Z"},
        {"quote_id": "q2", "consultant_id": "cons-1", "check_out_date": "2024-01-20", "created_at": "2024-01-02T10:00:00Z"},
        {"quote_id": "q3", "consultant_id": "cons-2", "check_out_date": "2024-01-18", "created_at": "2024-01-03T10:00:00Z"},
        {"quote_id": "q4", "consultant_id": "cons-2", "check_out_date": "2024-02-10", "created_at": "2024-01-04T10:00:00Z"},
        {"quote_id": "q5", "consultant_id": "cons-3", "check_out_date": "2024-01-25", "created_at": "2024-01-05T10:00:00Z"},
    ]


@pytest.fixture
def sample_invoices():
    """Sample invoice data."""
    return [
        {"quote_id": "q1", "consultant_id": "cons-1", "status": "paid", "total_amount": 5000},
        {"quote_id": "q2", "consultant_id": "cons-1", "status": "paid", "total_amount": 7500},
        {"quote_id": "q3", "consultant_id": "cons-2", "status": "paid", "total_amount": 6000},
        {"quote_id": "q4", "consultant_id": "cons-2", "status": "pending", "total_amount": 8000},
        {"quote_id": "q5", "consultant_id": "cons-3", "status": "draft", "total_amount": 4500},
    ]


# =============================================================================
# ConsultantPerformance Dataclass Tests
# =============================================================================

class TestConsultantPerformanceDataclass:
    """Tests for ConsultantPerformance dataclass."""

    def test_create_consultant_performance(self):
        """ConsultantPerformance can be created with required fields."""
        perf = ConsultantPerformance(
            consultant_id="cons-1",
            name="Alice Smith",
            email="alice@example.com",
            conversions=10,
            revenue=50000.0,
            quote_count=25,
            conversion_rate=40.0
        )

        assert perf.consultant_id == "cons-1"
        assert perf.name == "Alice Smith"
        assert perf.email == "alice@example.com"
        assert perf.conversions == 10
        assert perf.revenue == 50000.0
        assert perf.quote_count == 25
        assert perf.conversion_rate == 40.0
        assert perf.rank == 0  # Default value

    def test_consultant_performance_with_rank(self):
        """ConsultantPerformance can include rank."""
        perf = ConsultantPerformance(
            consultant_id="cons-1",
            name="Alice Smith",
            email="alice@example.com",
            conversions=10,
            revenue=50000.0,
            quote_count=25,
            conversion_rate=40.0,
            rank=1
        )

        assert perf.rank == 1


# =============================================================================
# PerformanceService Initialization Tests
# =============================================================================

class TestPerformanceServiceInit:
    """Tests for PerformanceService initialization."""

    def test_initialization(self, mock_supabase_tool):
        """PerformanceService initializes with supabase tool."""
        service = PerformanceService(mock_supabase_tool)

        assert service.db == mock_supabase_tool
        assert service.tenant_id == "tenant-123"

    def test_valid_periods(self, performance_service):
        """Service has valid periods defined."""
        assert "week" in performance_service.VALID_PERIODS
        assert "month" in performance_service.VALID_PERIODS
        assert "quarter" in performance_service.VALID_PERIODS
        assert "year" in performance_service.VALID_PERIODS
        assert "all" in performance_service.VALID_PERIODS

    def test_valid_metrics(self, performance_service):
        """Service has valid metrics defined."""
        assert "conversions" in performance_service.VALID_METRICS
        assert "revenue" in performance_service.VALID_METRICS
        assert "quotes" in performance_service.VALID_METRICS


# =============================================================================
# Period Start Date Tests
# =============================================================================

class TestGetPeriodStart:
    """Tests for _get_period_start method."""

    @freeze_time("2024-01-17 14:30:00")  # Wednesday
    def test_period_start_week(self, performance_service):
        """Week period starts on Monday."""
        period_start = performance_service._get_period_start("week")

        # Monday of the week containing 2024-01-17 (Wednesday)
        expected = datetime(2024, 1, 15, 0, 0, 0, 0)
        assert period_start == expected

    @freeze_time("2024-01-17 14:30:00")
    def test_period_start_month(self, performance_service):
        """Month period starts on first day of month."""
        period_start = performance_service._get_period_start("month")

        expected = datetime(2024, 1, 1, 0, 0, 0, 0)
        assert period_start == expected

    @freeze_time("2024-05-17 14:30:00")
    def test_period_start_quarter_q2(self, performance_service):
        """Quarter period starts on first day of quarter (Q2)."""
        period_start = performance_service._get_period_start("quarter")

        # Q2 starts April 1
        expected = datetime(2024, 4, 1, 0, 0, 0, 0)
        assert period_start == expected

    @freeze_time("2024-01-17 14:30:00")
    def test_period_start_quarter_q1(self, performance_service):
        """Quarter period starts on first day of quarter (Q1)."""
        period_start = performance_service._get_period_start("quarter")

        # Q1 starts January 1
        expected = datetime(2024, 1, 1, 0, 0, 0, 0)
        assert period_start == expected

    @freeze_time("2024-09-17 14:30:00")
    def test_period_start_quarter_q3(self, performance_service):
        """Quarter period starts on first day of quarter (Q3)."""
        period_start = performance_service._get_period_start("quarter")

        # Q3 starts July 1
        expected = datetime(2024, 7, 1, 0, 0, 0, 0)
        assert period_start == expected

    @freeze_time("2024-11-17 14:30:00")
    def test_period_start_quarter_q4(self, performance_service):
        """Quarter period starts on first day of quarter (Q4)."""
        period_start = performance_service._get_period_start("quarter")

        # Q4 starts October 1
        expected = datetime(2024, 10, 1, 0, 0, 0, 0)
        assert period_start == expected

    @freeze_time("2024-01-17 14:30:00")
    def test_period_start_year(self, performance_service):
        """Year period starts on January 1."""
        period_start = performance_service._get_period_start("year")

        expected = datetime(2024, 1, 1, 0, 0, 0, 0)
        assert period_start == expected

    @freeze_time("2024-01-17 14:30:00")
    def test_period_start_all(self, performance_service):
        """All period starts from 2020-01-01."""
        period_start = performance_service._get_period_start("all")

        expected = datetime(2020, 1, 1)
        assert period_start == expected

    @freeze_time("2024-01-01 00:00:00")  # Monday, start of month/year
    def test_period_start_week_on_monday(self, performance_service):
        """Week period on Monday returns that Monday."""
        period_start = performance_service._get_period_start("week")

        expected = datetime(2024, 1, 1, 0, 0, 0, 0)
        assert period_start == expected


# =============================================================================
# Consultant Rankings Tests
# =============================================================================

class TestGetConsultantRankings:
    """Tests for get_consultant_rankings method."""

    @freeze_time("2024-02-01 12:00:00")
    def test_rankings_with_data(self, performance_service, sample_consultants, sample_quotes, sample_invoices):
        """Rankings returned with proper data."""
        # Setup mocks
        performance_service.db.get_organization_users.return_value = sample_consultants

        quotes_mock = MagicMock()
        quotes_mock.data = sample_quotes
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = quotes_mock

        invoices_mock = MagicMock()
        invoices_mock.data = sample_invoices
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = invoices_mock

        rankings = performance_service.get_consultant_rankings(period="month", metric="conversions")

        assert len(rankings) == 3  # Only consultants, not admin
        # First ranked consultant should have most conversions
        assert rankings[0]["rank"] == 1

    def test_rankings_invalid_period_defaults_to_month(self, performance_service, sample_consultants):
        """Invalid period defaults to month."""
        performance_service.db.get_organization_users.return_value = sample_consultants

        quotes_mock = MagicMock()
        quotes_mock.data = []
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = quotes_mock

        # Should not raise error
        rankings = performance_service.get_consultant_rankings(period="invalid_period")

        assert isinstance(rankings, list)

    def test_rankings_invalid_metric_defaults_to_conversions(self, performance_service, sample_consultants):
        """Invalid metric defaults to conversions."""
        performance_service.db.get_organization_users.return_value = sample_consultants

        quotes_mock = MagicMock()
        quotes_mock.data = []
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = quotes_mock

        # Should not raise error
        rankings = performance_service.get_consultant_rankings(metric="invalid_metric")

        assert isinstance(rankings, list)

    def test_rankings_no_consultants(self, performance_service):
        """Empty list returned when no consultants."""
        performance_service.db.get_organization_users.return_value = []

        rankings = performance_service.get_consultant_rankings()

        assert rankings == []

    def test_rankings_only_admins(self, performance_service):
        """Empty list returned when only admins (no consultants)."""
        performance_service.db.get_organization_users.return_value = [
            {"id": "admin-1", "name": "Admin", "email": "admin@example.com", "role": "admin"}
        ]

        rankings = performance_service.get_consultant_rankings()

        assert rankings == []

    def test_rankings_respects_limit(self, performance_service, sample_consultants):
        """Rankings respects limit parameter."""
        performance_service.db.get_organization_users.return_value = sample_consultants

        quotes_mock = MagicMock()
        quotes_mock.data = []
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = quotes_mock

        rankings = performance_service.get_consultant_rankings(limit=1)

        assert len(rankings) <= 1

    def test_rankings_sort_by_revenue(self, performance_service, sample_consultants):
        """Rankings can be sorted by revenue."""
        performance_service.db.get_organization_users.return_value = sample_consultants

        quotes_mock = MagicMock()
        quotes_mock.data = []
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = quotes_mock

        # Should not raise error
        rankings = performance_service.get_consultant_rankings(metric="revenue")

        assert isinstance(rankings, list)

    def test_rankings_sort_by_quotes(self, performance_service, sample_consultants):
        """Rankings can be sorted by quotes."""
        performance_service.db.get_organization_users.return_value = sample_consultants

        quotes_mock = MagicMock()
        quotes_mock.data = []
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = quotes_mock

        # Should not raise error
        rankings = performance_service.get_consultant_rankings(metric="quotes")

        assert isinstance(rankings, list)

    def test_rankings_exception_returns_empty_list(self, performance_service):
        """Exception during ranking calculation returns empty list."""
        performance_service.db.get_organization_users.side_effect = Exception("DB error")

        rankings = performance_service.get_consultant_rankings()

        assert rankings == []

    def test_rankings_no_quotes(self, performance_service, sample_consultants):
        """Rankings work with zero quotes."""
        performance_service.db.get_organization_users.return_value = sample_consultants

        quotes_mock = MagicMock()
        quotes_mock.data = []
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = quotes_mock

        rankings = performance_service.get_consultant_rankings()

        assert len(rankings) == 3
        for r in rankings:
            assert r["quote_count"] == 0
            assert r["conversions"] == 0
            assert r["conversion_rate"] == 0.0


# =============================================================================
# Individual Consultant Performance Tests
# =============================================================================

class TestGetConsultantPerformance:
    """Tests for get_consultant_performance method."""

    def test_get_specific_consultant(self, performance_service, sample_consultants):
        """Get performance for specific consultant."""
        performance_service.db.get_organization_users.return_value = sample_consultants

        quotes_mock = MagicMock()
        quotes_mock.data = []
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = quotes_mock

        result = performance_service.get_consultant_performance("cons-1")

        assert result is not None
        assert result["consultant_id"] == "cons-1"

    def test_get_nonexistent_consultant(self, performance_service, sample_consultants):
        """Returns None for nonexistent consultant."""
        performance_service.db.get_organization_users.return_value = sample_consultants

        quotes_mock = MagicMock()
        quotes_mock.data = []
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = quotes_mock

        result = performance_service.get_consultant_performance("nonexistent-id")

        assert result is None

    def test_get_consultant_with_period(self, performance_service, sample_consultants):
        """Get performance with specific period."""
        performance_service.db.get_organization_users.return_value = sample_consultants

        quotes_mock = MagicMock()
        quotes_mock.data = []
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = quotes_mock

        result = performance_service.get_consultant_performance("cons-1", period="year")

        assert result is not None


# =============================================================================
# Performance Summary Tests
# =============================================================================

class TestGetPerformanceSummary:
    """Tests for get_performance_summary method."""

    def test_summary_with_data(self, performance_service, sample_consultants):
        """Summary includes all required fields."""
        performance_service.db.get_organization_users.return_value = sample_consultants

        quotes_mock = MagicMock()
        quotes_mock.data = []
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = quotes_mock

        summary = performance_service.get_performance_summary()

        assert "period" in summary
        assert "total_conversions" in summary
        assert "total_revenue" in summary
        assert "total_quotes" in summary
        assert "active_consultants" in summary
        assert "avg_conversion_rate" in summary
        assert "top_performer" in summary

    def test_summary_period_passed_through(self, performance_service, sample_consultants):
        """Summary includes the specified period."""
        performance_service.db.get_organization_users.return_value = sample_consultants

        quotes_mock = MagicMock()
        quotes_mock.data = []
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = quotes_mock

        summary = performance_service.get_performance_summary(period="quarter")

        assert summary["period"] == "quarter"

    def test_summary_no_consultants(self, performance_service):
        """Summary works with no consultants."""
        performance_service.db.get_organization_users.return_value = []

        summary = performance_service.get_performance_summary()

        assert summary["total_conversions"] == 0
        assert summary["total_revenue"] == 0.0
        assert summary["total_quotes"] == 0
        assert summary["active_consultants"] == 0
        assert summary["avg_conversion_rate"] == 0.0
        assert summary["top_performer"] is None

    def test_summary_calculates_totals(self, performance_service, sample_consultants):
        """Summary correctly calculates totals."""
        # Create consultants with known quote counts to verify active_consultants
        performance_service.db.get_organization_users.return_value = sample_consultants

        quotes_mock = MagicMock()
        quotes_mock.data = [
            {"quote_id": "q1", "consultant_id": "cons-1", "check_out_date": "2024-01-15", "created_at": "2024-01-01T10:00:00Z"},
        ]
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = quotes_mock

        invoices_mock = MagicMock()
        invoices_mock.data = []
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = invoices_mock

        summary = performance_service.get_performance_summary()

        # At least one active consultant (cons-1 has a quote)
        assert summary["active_consultants"] >= 1


# =============================================================================
# Conversion Rate Tests
# =============================================================================

class TestConversionRates:
    """Tests for conversion rate calculations."""

    @freeze_time("2024-02-01 12:00:00")
    def test_conversion_rate_calculation(self, performance_service, sample_consultants):
        """Conversion rate calculated correctly."""
        performance_service.db.get_organization_users.return_value = sample_consultants

        # 2 quotes for cons-1
        quotes_mock = MagicMock()
        quotes_mock.data = [
            {"quote_id": "q1", "consultant_id": "cons-1", "check_out_date": "2024-01-15", "created_at": "2024-01-01"},
            {"quote_id": "q2", "consultant_id": "cons-1", "check_out_date": "2024-01-20", "created_at": "2024-01-02"},
        ]
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = quotes_mock

        # 1 paid invoice for cons-1 (50% conversion)
        invoices_mock = MagicMock()
        invoices_mock.data = [
            {"quote_id": "q1", "consultant_id": "cons-1", "status": "paid", "total_amount": 5000},
        ]
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = invoices_mock

        rankings = performance_service.get_consultant_rankings()

        # Find cons-1 in rankings
        cons1 = next((r for r in rankings if r["consultant_id"] == "cons-1"), None)

        assert cons1 is not None
        assert cons1["quote_count"] == 2
        assert cons1["conversions"] == 1
        assert cons1["conversion_rate"] == 50.0

    def test_conversion_rate_zero_quotes(self, performance_service, sample_consultants):
        """Conversion rate is 0 when no quotes."""
        performance_service.db.get_organization_users.return_value = sample_consultants

        quotes_mock = MagicMock()
        quotes_mock.data = []
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = quotes_mock

        rankings = performance_service.get_consultant_rankings()

        for r in rankings:
            assert r["conversion_rate"] == 0.0


# =============================================================================
# Invoice Processing Tests
# =============================================================================

class TestInvoiceProcessing:
    """Tests for invoice processing in rankings."""

    @freeze_time("2024-02-01 12:00:00")
    def test_only_paid_invoices_count(self, performance_service, sample_consultants):
        """Only paid invoices count as conversions."""
        performance_service.db.get_organization_users.return_value = sample_consultants

        quotes_mock = MagicMock()
        quotes_mock.data = [
            {"quote_id": "q1", "consultant_id": "cons-1", "check_out_date": "2024-01-15", "created_at": "2024-01-01"},
            {"quote_id": "q2", "consultant_id": "cons-1", "check_out_date": "2024-01-20", "created_at": "2024-01-02"},
        ]
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = quotes_mock

        # One paid, one pending - only paid should count
        invoices_mock = MagicMock()
        invoices_mock.data = [
            {"quote_id": "q1", "consultant_id": "cons-1", "status": "paid", "total_amount": 5000},
            {"quote_id": "q2", "consultant_id": "cons-1", "status": "pending", "total_amount": 7000},
        ]
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = invoices_mock

        rankings = performance_service.get_consultant_rankings()
        cons1 = next((r for r in rankings if r["consultant_id"] == "cons-1"), None)

        assert cons1 is not None
        assert cons1["conversions"] == 1
        assert cons1["revenue"] == 5000.0

    @freeze_time("2024-01-10 12:00:00")  # Before checkout dates
    def test_future_checkout_not_converted(self, performance_service, sample_consultants):
        """Paid invoices with future checkout dates are not conversions."""
        performance_service.db.get_organization_users.return_value = sample_consultants

        # Quote with checkout in the future
        quotes_mock = MagicMock()
        quotes_mock.data = [
            {"quote_id": "q1", "consultant_id": "cons-1", "check_out_date": "2024-01-20", "created_at": "2024-01-01"},
        ]
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = quotes_mock

        invoices_mock = MagicMock()
        invoices_mock.data = [
            {"quote_id": "q1", "consultant_id": "cons-1", "status": "paid", "total_amount": 5000},
        ]
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = invoices_mock

        rankings = performance_service.get_consultant_rankings()
        cons1 = next((r for r in rankings if r["consultant_id"] == "cons-1"), None)

        assert cons1 is not None
        # Checkout is in the future, so should not count as conversion
        assert cons1["conversions"] == 0

    @freeze_time("2024-02-01 12:00:00")
    def test_invalid_checkout_date_still_counts(self, performance_service, sample_consultants):
        """Paid invoice with invalid checkout date still counts (graceful fallback)."""
        performance_service.db.get_organization_users.return_value = sample_consultants

        quotes_mock = MagicMock()
        quotes_mock.data = [
            {"quote_id": "q1", "consultant_id": "cons-1", "check_out_date": "invalid-date", "created_at": "2024-01-01"},
        ]
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = quotes_mock

        invoices_mock = MagicMock()
        invoices_mock.data = [
            {"quote_id": "q1", "consultant_id": "cons-1", "status": "paid", "total_amount": 5000},
        ]
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = invoices_mock

        rankings = performance_service.get_consultant_rankings()
        cons1 = next((r for r in rankings if r["consultant_id"] == "cons-1"), None)

        assert cons1 is not None
        # Invalid date falls back to counting as conversion
        assert cons1["conversions"] == 1

    @freeze_time("2024-02-01 12:00:00")
    def test_null_total_amount_defaults_to_zero(self, performance_service, sample_consultants):
        """Null total_amount defaults to zero."""
        performance_service.db.get_organization_users.return_value = sample_consultants

        quotes_mock = MagicMock()
        quotes_mock.data = [
            {"quote_id": "q1", "consultant_id": "cons-1", "check_out_date": "2024-01-15", "created_at": "2024-01-01"},
        ]
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = quotes_mock

        invoices_mock = MagicMock()
        invoices_mock.data = [
            {"quote_id": "q1", "consultant_id": "cons-1", "status": "paid", "total_amount": None},
        ]
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = invoices_mock

        rankings = performance_service.get_consultant_rankings()
        cons1 = next((r for r in rankings if r["consultant_id"] == "cons-1"), None)

        assert cons1 is not None
        assert cons1["revenue"] == 0.0


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases."""

    def test_quotes_without_quote_id(self, performance_service, sample_consultants):
        """Quotes without quote_id are skipped."""
        performance_service.db.get_organization_users.return_value = sample_consultants

        quotes_mock = MagicMock()
        quotes_mock.data = [
            {"consultant_id": "cons-1", "check_out_date": "2024-01-15", "created_at": "2024-01-01"},  # No quote_id
        ]
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = quotes_mock

        rankings = performance_service.get_consultant_rankings()

        # Should not crash
        assert isinstance(rankings, list)

    def test_invoice_without_consultant(self, performance_service, sample_consultants):
        """Invoices without consultant_id are handled."""
        performance_service.db.get_organization_users.return_value = sample_consultants

        quotes_mock = MagicMock()
        quotes_mock.data = [
            {"quote_id": "q1", "check_out_date": "2024-01-15", "created_at": "2024-01-01"},  # No consultant_id
        ]
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = quotes_mock

        invoices_mock = MagicMock()
        invoices_mock.data = [
            {"quote_id": "q1", "status": "paid", "total_amount": 5000},  # No consultant_id
        ]
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = invoices_mock

        rankings = performance_service.get_consultant_rankings()

        # Should not crash
        assert isinstance(rankings, list)

    @freeze_time("2024-02-01 12:00:00")
    def test_iso_format_checkout_date_with_z(self, performance_service, sample_consultants):
        """Checkout date with Z suffix is parsed correctly."""
        performance_service.db.get_organization_users.return_value = sample_consultants

        quotes_mock = MagicMock()
        quotes_mock.data = [
            {"quote_id": "q1", "consultant_id": "cons-1", "check_out_date": "2024-01-15T00:00:00Z", "created_at": "2024-01-01"},
        ]
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = quotes_mock

        invoices_mock = MagicMock()
        invoices_mock.data = [
            {"quote_id": "q1", "consultant_id": "cons-1", "status": "paid", "total_amount": 5000},
        ]
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = invoices_mock

        rankings = performance_service.get_consultant_rankings()
        cons1 = next((r for r in rankings if r["consultant_id"] == "cons-1"), None)

        assert cons1 is not None
        assert cons1["conversions"] == 1

    def test_quotes_result_none_data(self, performance_service, sample_consultants):
        """Handle quotes result with None data."""
        performance_service.db.get_organization_users.return_value = sample_consultants

        quotes_mock = MagicMock()
        quotes_mock.data = None
        performance_service.db.client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = quotes_mock

        rankings = performance_service.get_consultant_rankings()

        # Should handle None gracefully (data or [] = [])
        assert isinstance(rankings, list)
