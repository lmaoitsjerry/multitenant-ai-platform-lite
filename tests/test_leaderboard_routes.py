"""
Leaderboard Routes Unit Tests

Comprehensive tests for leaderboard API endpoints:
- GET /api/v1/leaderboard/rankings
- GET /api/v1/leaderboard/me
- GET /api/v1/leaderboard/summary
- GET /api/v1/leaderboard/consultant/{consultant_id}

Uses FastAPI TestClient with mocked dependencies.
These tests verify:
1. Authentication requirements
2. Pydantic model validation
3. PerformanceService unit tests
4. Dependency function behavior
5. Route registration
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import os


# ==================== Fixtures ====================

@pytest.fixture
def test_client():
    """Create a TestClient."""
    from main import app
    return TestClient(app)


@pytest.fixture
def mock_supabase_tool():
    """Create a mock SupabaseTool."""
    mock = MagicMock()
    mock.client = MagicMock()
    mock.tenant_id = "test_tenant"
    mock.get_organization_users.return_value = [
        {"id": "user_1", "name": "Alice", "email": "alice@example.com", "role": "consultant"},
        {"id": "user_2", "name": "Bob", "email": "bob@example.com", "role": "consultant"},
    ]
    return mock


@pytest.fixture
def sample_rankings():
    """Sample ranking data for tests."""
    return [
        {
            "rank": 1,
            "consultant_id": "user_1",
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "conversions": 15,
            "revenue": 75000.0,
            "quote_count": 20,
            "conversion_rate": 75.0
        },
        {
            "rank": 2,
            "consultant_id": "user_2",
            "name": "Bob Smith",
            "email": "bob@example.com",
            "conversions": 12,
            "revenue": 60000.0,
            "quote_count": 18,
            "conversion_rate": 66.7
        },
        {
            "rank": 3,
            "consultant_id": "user_123",
            "name": "Test User",
            "email": "user@example.com",
            "conversions": 10,
            "revenue": 50000.0,
            "quote_count": 15,
            "conversion_rate": 66.7
        }
    ]


@pytest.fixture
def sample_summary():
    """Sample summary data for tests."""
    return {
        "period": "month",
        "total_conversions": 37,
        "total_revenue": 185000.0,
        "total_quotes": 53,
        "active_consultants": 3,
        "avg_conversion_rate": 69.8,
        "top_performer": {
            "rank": 1,
            "consultant_id": "user_1",
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "conversions": 15,
            "revenue": 75000.0,
            "quote_count": 20,
            "conversion_rate": 75.0
        }
    }


# ==================== Authentication Tests ====================

class TestLeaderboardAuth:
    """Test authentication requirements for leaderboard endpoints."""

    def test_rankings_requires_auth(self, test_client):
        """GET /rankings should require authentication."""
        response = test_client.get("/api/v1/leaderboard/rankings")
        assert response.status_code == 401

    def test_me_requires_auth(self, test_client):
        """GET /me should require authentication."""
        response = test_client.get("/api/v1/leaderboard/me")
        assert response.status_code == 401

    def test_summary_requires_auth(self, test_client):
        """GET /summary should require authentication."""
        response = test_client.get("/api/v1/leaderboard/summary")
        assert response.status_code == 401

    def test_consultant_requires_auth(self, test_client):
        """GET /consultant/{id} should require authentication."""
        response = test_client.get("/api/v1/leaderboard/consultant/user_123")
        assert response.status_code == 401

    def test_rankings_with_query_params_requires_auth(self, test_client):
        """GET /rankings with query params still requires auth."""
        response = test_client.get("/api/v1/leaderboard/rankings?period=month&metric=revenue&limit=10")
        assert response.status_code == 401

    def test_me_with_period_requires_auth(self, test_client):
        """GET /me with period still requires auth."""
        response = test_client.get("/api/v1/leaderboard/me?period=year")
        assert response.status_code == 401


# ==================== Route Registration Tests ====================

class TestRouteRegistration:
    """Test that leaderboard routes module structure is correct."""

    def test_leaderboard_router_prefix(self):
        """Verify leaderboard router has correct prefix."""
        from src.api.leaderboard_routes import leaderboard_router

        assert leaderboard_router.prefix == "/api/v1/leaderboard"
        assert "Leaderboard" in leaderboard_router.tags

    def test_leaderboard_router_has_routes(self):
        """Verify leaderboard router has expected routes."""
        from src.api.leaderboard_routes import leaderboard_router

        route_paths = [r.path for r in leaderboard_router.routes]

        # Paths include the prefix
        assert "/api/v1/leaderboard/rankings" in route_paths
        assert "/api/v1/leaderboard/me" in route_paths
        assert "/api/v1/leaderboard/summary" in route_paths
        assert "/api/v1/leaderboard/consultant/{consultant_id}" in route_paths

    def test_leaderboard_router_route_count(self):
        """Verify leaderboard router has correct number of routes."""
        from src.api.leaderboard_routes import leaderboard_router

        # Should have 4 routes: rankings, me, summary, consultant/{id}
        assert len(leaderboard_router.routes) == 4


# ==================== Pydantic Models Tests ====================

class TestPydanticModels:
    """Test Pydantic model validation."""

    def test_consultant_ranking_response_structure(self):
        """Test ConsultantRankingResponse model."""
        from src.api.leaderboard_routes import ConsultantRankingResponse

        data = {
            "rank": 1,
            "consultant_id": "user_1",
            "name": "Alice",
            "email": "alice@example.com",
            "conversions": 10,
            "revenue": 50000.0,
            "quote_count": 15,
            "conversion_rate": 66.7
        }

        model = ConsultantRankingResponse(**data)
        assert model.rank == 1
        assert model.consultant_id == "user_1"
        assert model.revenue == 50000.0
        assert model.conversion_rate == 66.7

    def test_consultant_ranking_response_all_fields(self):
        """Test all fields in ConsultantRankingResponse."""
        from src.api.leaderboard_routes import ConsultantRankingResponse

        model = ConsultantRankingResponse(
            rank=5,
            consultant_id="abc123",
            name="John Doe",
            email="john@test.com",
            conversions=8,
            revenue=40000.0,
            quote_count=12,
            conversion_rate=66.6
        )

        assert model.rank == 5
        assert model.consultant_id == "abc123"
        assert model.name == "John Doe"
        assert model.email == "john@test.com"
        assert model.conversions == 8
        assert model.revenue == 40000.0
        assert model.quote_count == 12
        assert model.conversion_rate == 66.6

    def test_leaderboard_response_structure(self):
        """Test LeaderboardResponse model."""
        from src.api.leaderboard_routes import LeaderboardResponse, ConsultantRankingResponse

        ranking = ConsultantRankingResponse(
            rank=1,
            consultant_id="user_1",
            name="Alice",
            email="alice@example.com",
            conversions=10,
            revenue=50000.0,
            quote_count=15,
            conversion_rate=66.7
        )

        model = LeaderboardResponse(
            success=True,
            period="month",
            metric="conversions",
            rankings=[ranking],
            total_consultants=1
        )

        assert model.success is True
        assert model.period == "month"
        assert model.metric == "conversions"
        assert len(model.rankings) == 1
        assert model.total_consultants == 1

    def test_leaderboard_response_empty_rankings(self):
        """Test LeaderboardResponse with empty rankings."""
        from src.api.leaderboard_routes import LeaderboardResponse

        model = LeaderboardResponse(
            success=True,
            period="week",
            metric="revenue",
            rankings=[],
            total_consultants=0
        )

        assert model.rankings == []
        assert model.total_consultants == 0

    def test_my_performance_response_structure(self):
        """Test MyPerformanceResponse model."""
        from src.api.leaderboard_routes import MyPerformanceResponse

        model = MyPerformanceResponse(
            success=True,
            period="month",
            rank=3,
            name="Test User",
            conversions=10,
            revenue=50000.0,
            quote_count=15,
            conversion_rate=66.7,
            total_consultants=10
        )

        assert model.rank == 3
        assert model.total_consultants == 10
        assert model.name == "Test User"

    def test_my_performance_response_not_ranked(self):
        """Test MyPerformanceResponse for user not in rankings."""
        from src.api.leaderboard_routes import MyPerformanceResponse

        model = MyPerformanceResponse(
            success=True,
            period="month",
            rank=0,
            name="New User",
            conversions=0,
            revenue=0.0,
            quote_count=0,
            conversion_rate=0.0,
            total_consultants=5
        )

        assert model.rank == 0
        assert model.conversions == 0

    def test_performance_summary_response_structure(self):
        """Test PerformanceSummaryResponse model."""
        from src.api.leaderboard_routes import PerformanceSummaryResponse

        model = PerformanceSummaryResponse(
            success=True,
            period="month",
            total_conversions=37,
            total_revenue=185000.0,
            total_quotes=53,
            active_consultants=3,
            avg_conversion_rate=69.8,
            top_performer=None
        )

        assert model.total_conversions == 37
        assert model.top_performer is None

    def test_performance_summary_with_top_performer(self, sample_rankings):
        """Test PerformanceSummaryResponse with top performer."""
        from src.api.leaderboard_routes import PerformanceSummaryResponse, ConsultantRankingResponse

        top_performer = ConsultantRankingResponse(**sample_rankings[0])

        model = PerformanceSummaryResponse(
            success=True,
            period="quarter",
            total_conversions=100,
            total_revenue=500000.0,
            total_quotes=150,
            active_consultants=5,
            avg_conversion_rate=66.7,
            top_performer=top_performer
        )

        assert model.top_performer is not None
        assert model.top_performer.name == "Alice Johnson"
        assert model.top_performer.rank == 1


# ==================== PerformanceService Tests ====================

class TestPerformanceService:
    """Test PerformanceService class directly."""

    def test_service_initialization(self, mock_supabase_tool):
        """Test PerformanceService initializes correctly."""
        from src.services.performance_service import PerformanceService

        service = PerformanceService(mock_supabase_tool)

        assert service.db == mock_supabase_tool
        assert service.tenant_id == "test_tenant"

    def test_valid_periods(self):
        """Test valid periods list."""
        from src.services.performance_service import PerformanceService

        assert "week" in PerformanceService.VALID_PERIODS
        assert "month" in PerformanceService.VALID_PERIODS
        assert "quarter" in PerformanceService.VALID_PERIODS
        assert "year" in PerformanceService.VALID_PERIODS
        assert "all" in PerformanceService.VALID_PERIODS

    def test_valid_metrics(self):
        """Test valid metrics list."""
        from src.services.performance_service import PerformanceService

        assert "conversions" in PerformanceService.VALID_METRICS
        assert "revenue" in PerformanceService.VALID_METRICS
        assert "quotes" in PerformanceService.VALID_METRICS

    def test_get_period_start_week(self, mock_supabase_tool):
        """Test _get_period_start for week."""
        from src.services.performance_service import PerformanceService

        service = PerformanceService(mock_supabase_tool)
        start = service._get_period_start("week")

        now = datetime.utcnow()
        days_since_monday = now.weekday()
        expected = (now - timedelta(days=days_since_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        assert start.date() == expected.date()

    def test_get_period_start_month(self, mock_supabase_tool):
        """Test _get_period_start for month."""
        from src.services.performance_service import PerformanceService

        service = PerformanceService(mock_supabase_tool)
        start = service._get_period_start("month")

        assert start.day == 1
        assert start.hour == 0

    def test_get_period_start_quarter(self, mock_supabase_tool):
        """Test _get_period_start for quarter."""
        from src.services.performance_service import PerformanceService

        service = PerformanceService(mock_supabase_tool)
        start = service._get_period_start("quarter")

        # Should be first month of current quarter
        assert start.month in [1, 4, 7, 10]
        assert start.day == 1

    def test_get_period_start_year(self, mock_supabase_tool):
        """Test _get_period_start for year."""
        from src.services.performance_service import PerformanceService

        service = PerformanceService(mock_supabase_tool)
        start = service._get_period_start("year")

        now = datetime.utcnow()
        assert start.year == now.year
        assert start.month == 1
        assert start.day == 1

    def test_get_period_start_all(self, mock_supabase_tool):
        """Test _get_period_start for all."""
        from src.services.performance_service import PerformanceService

        service = PerformanceService(mock_supabase_tool)
        start = service._get_period_start("all")

        assert start.year == 2020
        assert start.month == 1
        assert start.day == 1

    def test_get_consultant_rankings_no_consultants(self, mock_supabase_tool):
        """Test get_consultant_rankings with no consultants."""
        from src.services.performance_service import PerformanceService

        mock_supabase_tool.get_organization_users.return_value = []

        service = PerformanceService(mock_supabase_tool)
        rankings = service.get_consultant_rankings()

        assert rankings == []

    def test_get_consultant_rankings_invalid_period(self, mock_supabase_tool):
        """Test get_consultant_rankings normalizes invalid period."""
        from src.services.performance_service import PerformanceService

        mock_supabase_tool.get_organization_users.return_value = []

        service = PerformanceService(mock_supabase_tool)
        # Should not raise - normalizes to "month"
        rankings = service.get_consultant_rankings(period="invalid")

        assert rankings == []

    def test_get_consultant_rankings_invalid_metric(self, mock_supabase_tool):
        """Test get_consultant_rankings normalizes invalid metric."""
        from src.services.performance_service import PerformanceService

        mock_supabase_tool.get_organization_users.return_value = []

        service = PerformanceService(mock_supabase_tool)
        # Should not raise - normalizes to "conversions"
        rankings = service.get_consultant_rankings(metric="invalid")

        assert rankings == []

    def test_get_consultant_performance_not_found(self, mock_supabase_tool):
        """Test get_consultant_performance for non-existent consultant."""
        from src.services.performance_service import PerformanceService

        mock_supabase_tool.get_organization_users.return_value = []

        service = PerformanceService(mock_supabase_tool)
        result = service.get_consultant_performance("nonexistent_user")

        assert result is None

    def test_get_performance_summary_empty(self, mock_supabase_tool):
        """Test get_performance_summary with no data."""
        from src.services.performance_service import PerformanceService

        mock_supabase_tool.get_organization_users.return_value = []

        service = PerformanceService(mock_supabase_tool)
        summary = service.get_performance_summary()

        assert summary["total_conversions"] == 0
        assert summary["total_revenue"] == 0
        assert summary["total_quotes"] == 0
        assert summary["active_consultants"] == 0
        assert summary["top_performer"] is None


# ==================== Dependency Function Tests ====================

class TestDependencyFunctions:
    """Test route dependency functions."""

    def test_get_supabase_tool_unknown_client(self):
        """Test get_supabase_tool raises 400 for unknown client."""
        from src.api.leaderboard_routes import get_supabase_tool
        from fastapi import HTTPException

        with patch("src.api.leaderboard_routes.get_config") as mock_get_config:
            mock_get_config.side_effect = FileNotFoundError("Unknown client")

            with pytest.raises(HTTPException) as exc_info:
                get_supabase_tool("unknown_client")

            assert exc_info.value.status_code == 400
            assert "Unknown client" in exc_info.value.detail

    def test_get_supabase_tool_default_client(self):
        """Test get_supabase_tool uses default when header is None."""
        from src.api.leaderboard_routes import get_supabase_tool

        with patch("src.api.leaderboard_routes.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_get_config.return_value = mock_config

            with patch("src.api.leaderboard_routes.SupabaseTool") as mock_supabase:
                with patch.dict(os.environ, {"CLIENT_ID": "default_tenant"}):
                    get_supabase_tool(None)
                    mock_get_config.assert_called_with("default_tenant")

    def test_get_supabase_tool_with_header(self):
        """Test get_supabase_tool uses header client ID."""
        from src.api.leaderboard_routes import get_supabase_tool

        with patch("src.api.leaderboard_routes.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_get_config.return_value = mock_config

            with patch("src.api.leaderboard_routes.SupabaseTool") as mock_supabase:
                mock_supabase.return_value = MagicMock()
                get_supabase_tool("header_tenant")
                mock_get_config.assert_called_with("header_tenant")

    def test_get_performance_service(self):
        """Test get_performance_service dependency."""
        from src.api.leaderboard_routes import get_performance_service
        from src.services.performance_service import PerformanceService

        mock_db = MagicMock()
        mock_db.tenant_id = "test"

        service = get_performance_service(mock_db)

        assert isinstance(service, PerformanceService)
        assert service.db == mock_db


# ==================== ConsultantPerformance Dataclass Tests ====================

class TestConsultantPerformanceDataclass:
    """Test ConsultantPerformance dataclass."""

    def test_consultant_performance_creation(self):
        """Test creating ConsultantPerformance."""
        from src.services.performance_service import ConsultantPerformance

        perf = ConsultantPerformance(
            consultant_id="user_1",
            name="Alice",
            email="alice@example.com",
            conversions=10,
            revenue=50000.0,
            quote_count=15,
            conversion_rate=66.7,
            rank=1
        )

        assert perf.consultant_id == "user_1"
        assert perf.name == "Alice"
        assert perf.rank == 1

    def test_consultant_performance_default_rank(self):
        """Test ConsultantPerformance default rank."""
        from src.services.performance_service import ConsultantPerformance

        perf = ConsultantPerformance(
            consultant_id="user_1",
            name="Alice",
            email="alice@example.com",
            conversions=10,
            revenue=50000.0,
            quote_count=15,
            conversion_rate=66.7
        )

        assert perf.rank == 0


# ==================== HTTP Method Tests ====================

class TestHTTPMethods:
    """Test that endpoints only accept correct HTTP methods."""

    def test_rankings_only_get(self, test_client):
        """Rankings endpoint only accepts GET."""
        # POST should fail
        response = test_client.post("/api/v1/leaderboard/rankings")
        assert response.status_code in [405, 401]  # Method not allowed or auth error

    def test_me_only_get(self, test_client):
        """Me endpoint only accepts GET."""
        response = test_client.put("/api/v1/leaderboard/me")
        assert response.status_code in [405, 401]

    def test_summary_only_get(self, test_client):
        """Summary endpoint only accepts GET."""
        response = test_client.delete("/api/v1/leaderboard/summary")
        assert response.status_code in [405, 401]


# ==================== Query Parameter Tests ====================

class TestQueryParameters:
    """Test query parameter validation."""

    def test_rankings_period_param_accepted(self, test_client):
        """Test rankings accepts period query param."""
        # Request should fail auth but not validation
        for period in ["week", "month", "quarter", "year", "all"]:
            response = test_client.get(f"/api/v1/leaderboard/rankings?period={period}")
            # 401 means auth failed, not validation
            assert response.status_code == 401

    def test_rankings_metric_param_accepted(self, test_client):
        """Test rankings accepts metric query param."""
        for metric in ["conversions", "revenue", "quotes"]:
            response = test_client.get(f"/api/v1/leaderboard/rankings?metric={metric}")
            assert response.status_code == 401

    def test_rankings_limit_param_accepted(self, test_client):
        """Test rankings accepts limit query param."""
        response = test_client.get("/api/v1/leaderboard/rankings?limit=10")
        assert response.status_code == 401

    def test_rankings_all_params_combined(self, test_client):
        """Test rankings accepts all params combined."""
        response = test_client.get(
            "/api/v1/leaderboard/rankings?period=quarter&metric=revenue&limit=25"
        )
        assert response.status_code == 401


# ==================== Endpoint Unit Tests ====================

class TestGetRankingsEndpoint:
    """Unit tests for get_rankings endpoint handler."""

    @pytest.mark.asyncio
    async def test_get_rankings_returns_rankings(self, sample_rankings):
        """get_rankings should return consultant rankings."""
        from src.api.leaderboard_routes import get_rankings
        from src.middleware.auth_middleware import UserContext
        from fastapi import Request

        mock_user = MagicMock(spec=UserContext)
        mock_user.user_id = "user_123"

        mock_service = MagicMock()
        mock_service.get_consultant_rankings.return_value = sample_rankings

        mock_request = MagicMock(spec=Request)

        result = await get_rankings(
            request=mock_request,
            period="month",
            metric="conversions",
            limit=50,
            user=mock_user,
            performance_service=mock_service
        )

        assert result.success is True
        assert result.period == "month"
        assert result.metric == "conversions"
        assert len(result.rankings) == 3
        assert result.total_consultants == 3

    @pytest.mark.asyncio
    async def test_get_rankings_normalizes_invalid_period(self, sample_rankings):
        """get_rankings should normalize invalid period to 'month'."""
        from src.api.leaderboard_routes import get_rankings
        from src.middleware.auth_middleware import UserContext
        from fastapi import Request

        mock_user = MagicMock(spec=UserContext)
        mock_service = MagicMock()
        mock_service.get_consultant_rankings.return_value = sample_rankings
        mock_request = MagicMock(spec=Request)

        result = await get_rankings(
            request=mock_request,
            period="invalid_period",
            metric="conversions",
            limit=50,
            user=mock_user,
            performance_service=mock_service
        )

        assert result.period == "month"

    @pytest.mark.asyncio
    async def test_get_rankings_normalizes_invalid_metric(self, sample_rankings):
        """get_rankings should normalize invalid metric to 'conversions'."""
        from src.api.leaderboard_routes import get_rankings
        from src.middleware.auth_middleware import UserContext
        from fastapi import Request

        mock_user = MagicMock(spec=UserContext)
        mock_service = MagicMock()
        mock_service.get_consultant_rankings.return_value = sample_rankings
        mock_request = MagicMock(spec=Request)

        result = await get_rankings(
            request=mock_request,
            period="month",
            metric="invalid_metric",
            limit=50,
            user=mock_user,
            performance_service=mock_service
        )

        assert result.metric == "conversions"

    @pytest.mark.asyncio
    async def test_get_rankings_handles_service_error(self):
        """get_rankings should raise 500 on service error."""
        from src.api.leaderboard_routes import get_rankings
        from src.middleware.auth_middleware import UserContext
        from fastapi import Request, HTTPException

        mock_user = MagicMock(spec=UserContext)
        mock_service = MagicMock()
        mock_service.get_consultant_rankings.side_effect = Exception("Service error")
        mock_request = MagicMock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await get_rankings(
                request=mock_request,
                period="month",
                metric="conversions",
                limit=50,
                user=mock_user,
                performance_service=mock_service
            )

        assert exc_info.value.status_code == 500


class TestGetMyPerformanceEndpoint:
    """Unit tests for get_my_performance endpoint handler."""

    @pytest.mark.asyncio
    async def test_get_my_performance_user_in_rankings(self, sample_rankings):
        """get_my_performance should return user's performance."""
        from src.api.leaderboard_routes import get_my_performance
        from src.middleware.auth_middleware import UserContext
        from fastapi import Request

        mock_user = MagicMock(spec=UserContext)
        mock_user.user_id = "user_123"  # Matches sample_rankings[2]
        mock_user.name = "Test User"

        mock_service = MagicMock()
        mock_service.get_consultant_rankings.return_value = sample_rankings
        mock_request = MagicMock(spec=Request)

        result = await get_my_performance(
            request=mock_request,
            period="month",
            user=mock_user,
            performance_service=mock_service
        )

        assert result.success is True
        assert result.rank == 3
        assert result.conversions == 10
        assert result.total_consultants == 3

    @pytest.mark.asyncio
    async def test_get_my_performance_user_not_in_rankings(self, sample_rankings):
        """get_my_performance should return zero rank for unranked user."""
        from src.api.leaderboard_routes import get_my_performance
        from src.middleware.auth_middleware import UserContext
        from fastapi import Request

        mock_user = MagicMock(spec=UserContext)
        mock_user.user_id = "nonexistent_user"
        mock_user.name = "New User"

        mock_service = MagicMock()
        mock_service.get_consultant_rankings.return_value = sample_rankings
        mock_request = MagicMock(spec=Request)

        result = await get_my_performance(
            request=mock_request,
            period="month",
            user=mock_user,
            performance_service=mock_service
        )

        assert result.success is True
        assert result.rank == 0
        assert result.conversions == 0
        assert result.name == "New User"

    @pytest.mark.asyncio
    async def test_get_my_performance_handles_error(self):
        """get_my_performance should raise 500 on error."""
        from src.api.leaderboard_routes import get_my_performance
        from src.middleware.auth_middleware import UserContext
        from fastapi import Request, HTTPException

        mock_user = MagicMock(spec=UserContext)
        mock_service = MagicMock()
        mock_service.get_consultant_rankings.side_effect = Exception("Error")
        mock_request = MagicMock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await get_my_performance(
                request=mock_request,
                period="month",
                user=mock_user,
                performance_service=mock_service
            )

        assert exc_info.value.status_code == 500


class TestGetPerformanceSummaryEndpoint:
    """Unit tests for get_performance_summary endpoint handler."""

    @pytest.mark.asyncio
    async def test_get_summary_returns_summary(self, sample_summary):
        """get_performance_summary should return organization summary."""
        from src.api.leaderboard_routes import get_performance_summary
        from src.middleware.auth_middleware import UserContext
        from fastapi import Request

        mock_user = MagicMock(spec=UserContext)
        mock_service = MagicMock()
        mock_service.get_performance_summary.return_value = sample_summary
        mock_request = MagicMock(spec=Request)

        result = await get_performance_summary(
            request=mock_request,
            period="month",
            user=mock_user,
            performance_service=mock_service
        )

        assert result.success is True
        assert result.total_conversions == 37
        assert result.total_revenue == 185000.0
        assert result.active_consultants == 3
        assert result.top_performer is not None
        assert result.top_performer.name == "Alice Johnson"

    @pytest.mark.asyncio
    async def test_get_summary_without_top_performer(self):
        """get_performance_summary handles no top performer."""
        from src.api.leaderboard_routes import get_performance_summary
        from src.middleware.auth_middleware import UserContext
        from fastapi import Request

        mock_user = MagicMock(spec=UserContext)
        mock_service = MagicMock()
        mock_service.get_performance_summary.return_value = {
            "period": "month",
            "total_conversions": 0,
            "total_revenue": 0.0,
            "total_quotes": 0,
            "active_consultants": 0,
            "avg_conversion_rate": 0.0,
            "top_performer": None
        }
        mock_request = MagicMock(spec=Request)

        result = await get_performance_summary(
            request=mock_request,
            period="month",
            user=mock_user,
            performance_service=mock_service
        )

        assert result.success is True
        assert result.top_performer is None

    @pytest.mark.asyncio
    async def test_get_summary_handles_error(self):
        """get_performance_summary should raise 500 on error."""
        from src.api.leaderboard_routes import get_performance_summary
        from src.middleware.auth_middleware import UserContext
        from fastapi import Request, HTTPException

        mock_user = MagicMock(spec=UserContext)
        mock_service = MagicMock()
        mock_service.get_performance_summary.side_effect = Exception("Error")
        mock_request = MagicMock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await get_performance_summary(
                request=mock_request,
                period="month",
                user=mock_user,
                performance_service=mock_service
            )

        assert exc_info.value.status_code == 500


class TestGetConsultantPerformanceEndpoint:
    """Unit tests for get_consultant_performance endpoint handler."""

    @pytest.mark.asyncio
    async def test_get_consultant_performance_found(self, sample_rankings):
        """get_consultant_performance should return consultant data."""
        from src.api.leaderboard_routes import get_consultant_performance
        from src.middleware.auth_middleware import UserContext
        from fastapi import Request

        mock_user = MagicMock(spec=UserContext)
        mock_service = MagicMock()
        mock_service.get_consultant_performance.return_value = sample_rankings[0]
        mock_request = MagicMock(spec=Request)

        result = await get_consultant_performance(
            consultant_id="user_1",
            request=mock_request,
            period="month",
            user=mock_user,
            performance_service=mock_service
        )

        assert result["success"] is True
        assert result["consultant"].consultant_id == "user_1"
        assert result["consultant"].rank == 1

    @pytest.mark.asyncio
    async def test_get_consultant_performance_not_found(self):
        """get_consultant_performance should raise 404 when not found."""
        from src.api.leaderboard_routes import get_consultant_performance
        from src.middleware.auth_middleware import UserContext
        from fastapi import Request, HTTPException

        mock_user = MagicMock(spec=UserContext)
        mock_service = MagicMock()
        mock_service.get_consultant_performance.return_value = None
        mock_request = MagicMock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await get_consultant_performance(
                consultant_id="nonexistent",
                request=mock_request,
                period="month",
                user=mock_user,
                performance_service=mock_service
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_consultant_performance_handles_error(self):
        """get_consultant_performance should raise 500 on error."""
        from src.api.leaderboard_routes import get_consultant_performance
        from src.middleware.auth_middleware import UserContext
        from fastapi import Request, HTTPException

        mock_user = MagicMock(spec=UserContext)
        mock_service = MagicMock()
        mock_service.get_consultant_performance.side_effect = Exception("Error")
        mock_request = MagicMock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await get_consultant_performance(
                consultant_id="user_1",
                request=mock_request,
                period="month",
                user=mock_user,
                performance_service=mock_service
            )

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_get_consultant_performance_normalizes_period(self, sample_rankings):
        """get_consultant_performance should normalize invalid period."""
        from src.api.leaderboard_routes import get_consultant_performance
        from src.middleware.auth_middleware import UserContext
        from fastapi import Request

        mock_user = MagicMock(spec=UserContext)
        mock_service = MagicMock()
        mock_service.get_consultant_performance.return_value = sample_rankings[0]
        mock_request = MagicMock(spec=Request)

        result = await get_consultant_performance(
            consultant_id="user_1",
            request=mock_request,
            period="invalid",
            user=mock_user,
            performance_service=mock_service
        )

        assert result["period"] == "month"
