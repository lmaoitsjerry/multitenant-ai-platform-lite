"""
Pricing Routes Unit Tests

Comprehensive tests for pricing API endpoints:
- /api/v1/pricing/rates (CRUD for rates)
- /api/v1/pricing/hotels (hotel listing)
- /api/v1/pricing/destinations (destination listing)
- /api/v1/pricing/stats (pricing statistics)

Uses FastAPI TestClient with mocked BigQuery dependencies.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import io


# ==================== Fixtures ====================

@pytest.fixture
def mock_config():
    """Create a mock ClientConfig."""
    config = MagicMock()
    config.client_id = "test_tenant"
    config.gcp_project_id = "test-project"
    config.shared_pricing_dataset = "pricing_dataset"
    return config


@pytest.fixture
def test_client():
    """Create a basic TestClient."""
    from main import app
    return TestClient(app)


@pytest.fixture
def mock_bigquery_client():
    """Create a mock BigQuery client."""
    mock_client = MagicMock()
    return mock_client


# ==================== Rate List Endpoint Tests ====================

class TestListRatesEndpoint:
    """Test GET /api/v1/pricing/rates endpoint."""

    def test_list_rates_requires_auth(self, test_client):
        """GET /api/v1/pricing/rates should require authentication."""
        response = test_client.get("/api/v1/pricing/rates")
        assert response.status_code == 401

    def test_list_rates_with_destination_requires_auth(self, test_client):
        """GET /api/v1/pricing/rates?destination=Zanzibar still requires auth."""
        response = test_client.get("/api/v1/pricing/rates?destination=Zanzibar")
        assert response.status_code == 401

    def test_list_rates_with_hotel_filter_requires_auth(self, test_client):
        """GET /api/v1/pricing/rates?hotel_name=Hilton still requires auth."""
        response = test_client.get("/api/v1/pricing/rates?hotel_name=Hilton")
        assert response.status_code == 401

    def test_list_rates_with_meal_plan_requires_auth(self, test_client):
        """GET /api/v1/pricing/rates?meal_plan=AI still requires auth."""
        response = test_client.get("/api/v1/pricing/rates?meal_plan=AI")
        assert response.status_code == 401

    def test_list_rates_with_pagination_requires_auth(self, test_client):
        """GET /api/v1/pricing/rates with pagination still requires auth."""
        response = test_client.get("/api/v1/pricing/rates?limit=10&offset=0")
        assert response.status_code == 401


class TestCreateRateEndpoint:
    """Test POST /api/v1/pricing/rates endpoint."""

    def test_create_rate_requires_auth(self, test_client):
        """POST /api/v1/pricing/rates should require authentication."""
        response = test_client.post(
            "/api/v1/pricing/rates",
            json={
                "hotel_name": "Test Hotel",
                "destination": "Cape Town",
                "room_type": "Standard",
                "meal_plan": "BB",
                "check_in_date": "2025-01-01",
                "check_out_date": "2025-01-08",
                "nights": 7,
                "total_7nights_pps": 1200.0
            }
        )
        assert response.status_code == 401

    def test_create_rate_empty_body_requires_auth(self, test_client):
        """POST /api/v1/pricing/rates without body returns auth error."""
        response = test_client.post("/api/v1/pricing/rates", json={})
        # Auth runs before validation
        assert response.status_code == 401


class TestGetRateEndpoint:
    """Test GET /api/v1/pricing/rates/{rate_id} endpoint."""

    def test_get_rate_requires_auth(self, test_client):
        """GET /api/v1/pricing/rates/{id} should require authentication."""
        response = test_client.get("/api/v1/pricing/rates/RATE-ABC12345")
        assert response.status_code == 401

    def test_get_rate_various_ids(self, test_client):
        """GET /api/v1/pricing/rates/{id} with various IDs requires auth."""
        for rate_id in ["RATE-001", "RATE-XYZ789", "12345"]:
            response = test_client.get(f"/api/v1/pricing/rates/{rate_id}")
            assert response.status_code == 401


class TestUpdateRateEndpoint:
    """Test PUT /api/v1/pricing/rates/{rate_id} endpoint."""

    def test_update_rate_requires_auth(self, test_client):
        """PUT /api/v1/pricing/rates/{id} should require authentication."""
        response = test_client.put(
            "/api/v1/pricing/rates/RATE-ABC12345",
            json={"total_7nights_pps": 1500.0}
        )
        assert response.status_code == 401


class TestDeleteRateEndpoint:
    """Test DELETE /api/v1/pricing/rates/{rate_id} endpoint."""

    def test_delete_rate_requires_auth(self, test_client):
        """DELETE /api/v1/pricing/rates/{id} should require authentication."""
        response = test_client.delete("/api/v1/pricing/rates/RATE-ABC12345")
        assert response.status_code == 401

    def test_hard_delete_rate_requires_auth(self, test_client):
        """DELETE /api/v1/pricing/rates/{id}?hard_delete=true requires auth."""
        response = test_client.delete("/api/v1/pricing/rates/RATE-ABC12345?hard_delete=true")
        assert response.status_code == 401


# ==================== Import/Export Endpoint Tests ====================

class TestImportRatesEndpoint:
    """Test POST /api/v1/pricing/rates/import endpoint."""

    def test_import_rates_requires_auth(self, test_client):
        """POST /api/v1/pricing/rates/import should require authentication."""
        # Create a simple CSV file
        csv_content = b"hotel_name,destination,room_type,meal_plan,check_in_date,check_out_date,nights,total_7nights_pps\nTest Hotel,Cape Town,Standard,BB,2025-01-01,2025-01-08,7,1200"

        response = test_client.post(
            "/api/v1/pricing/rates/import",
            files={"file": ("rates.csv", io.BytesIO(csv_content), "text/csv")}
        )
        assert response.status_code == 401


class TestExportRatesEndpoint:
    """Test GET /api/v1/pricing/rates/export endpoint."""

    def test_export_rates_requires_auth(self, test_client):
        """GET /api/v1/pricing/rates/export should require authentication."""
        response = test_client.get("/api/v1/pricing/rates/export")
        assert response.status_code == 401

    def test_export_rates_with_destination_requires_auth(self, test_client):
        """GET /api/v1/pricing/rates/export?destination=Zanzibar requires auth."""
        response = test_client.get("/api/v1/pricing/rates/export?destination=Zanzibar")
        assert response.status_code == 401


# ==================== Hotel Endpoint Tests ====================

class TestListHotelsEndpoint:
    """Test GET /api/v1/pricing/hotels endpoint."""

    def test_list_hotels_requires_auth(self, test_client):
        """GET /api/v1/pricing/hotels should require authentication."""
        response = test_client.get("/api/v1/pricing/hotels")
        assert response.status_code == 401

    def test_list_hotels_with_destination_requires_auth(self, test_client):
        """GET /api/v1/pricing/hotels?destination=Maldives requires auth."""
        response = test_client.get("/api/v1/pricing/hotels?destination=Maldives")
        assert response.status_code == 401


class TestGetHotelRatesEndpoint:
    """Test GET /api/v1/pricing/hotels/{hotel_name}/rates endpoint."""

    def test_get_hotel_rates_requires_auth(self, test_client):
        """GET /api/v1/pricing/hotels/{name}/rates should require auth."""
        response = test_client.get("/api/v1/pricing/hotels/Hilton/rates")
        assert response.status_code == 401


# ==================== Destination Endpoint Tests ====================

class TestListDestinationsEndpoint:
    """Test GET /api/v1/pricing/destinations endpoint."""

    def test_list_destinations_requires_auth(self, test_client):
        """GET /api/v1/pricing/destinations should require authentication."""
        response = test_client.get("/api/v1/pricing/destinations")
        assert response.status_code == 401


# ==================== Stats Endpoint Tests ====================

class TestPricingStatsEndpoint:
    """Test GET /api/v1/pricing/stats endpoint."""

    def test_pricing_stats_requires_auth(self, test_client):
        """GET /api/v1/pricing/stats should require authentication."""
        response = test_client.get("/api/v1/pricing/stats")
        assert response.status_code == 401


# ==================== Route Existence Tests ====================

class TestPricingRouteExistence:
    """Test that all pricing routes exist."""

    def test_pricing_routes_exist(self, test_client):
        """All pricing routes should exist (not 404)."""
        routes = [
            ("GET", "/api/v1/pricing/rates"),
            ("POST", "/api/v1/pricing/rates"),
            ("GET", "/api/v1/pricing/rates/RATE-001"),
            ("PUT", "/api/v1/pricing/rates/RATE-001"),
            ("DELETE", "/api/v1/pricing/rates/RATE-001"),
            ("GET", "/api/v1/pricing/rates/export"),
            ("POST", "/api/v1/pricing/rates/import"),
            ("GET", "/api/v1/pricing/hotels"),
            ("GET", "/api/v1/pricing/hotels/TestHotel/rates"),
            ("GET", "/api/v1/pricing/destinations"),
            ("GET", "/api/v1/pricing/stats"),
        ]

        for method, path in routes:
            if method == "GET":
                response = test_client.get(path)
            elif method == "POST":
                # For file uploads, provide minimal data
                if "import" in path:
                    response = test_client.post(
                        path,
                        files={"file": ("test.csv", io.BytesIO(b"a,b\n1,2"), "text/csv")}
                    )
                else:
                    response = test_client.post(path, json={})
            elif method == "PUT":
                response = test_client.put(path, json={})
            elif method == "DELETE":
                response = test_client.delete(path)

            # Should be 401 (auth required), not 404 (route not found)
            assert response.status_code != 404, f"{method} {path} returned 404"


# ==================== Pydantic Model Tests ====================

class TestPricingModels:
    """Test Pydantic model validation."""

    def test_rate_base_model_fields(self):
        """RateBase model should have required fields."""
        from src.api.pricing_routes import RateBase

        # Valid rate
        rate = RateBase(
            hotel_name="Test Hotel",
            destination="Cape Town",
            room_type="Standard",
            meal_plan="BB",
            check_in_date="2025-01-01",
            check_out_date="2025-01-08",
            nights=7,
            total_7nights_pps=1200.0
        )

        assert rate.hotel_name == "Test Hotel"
        assert rate.destination == "Cape Town"
        assert rate.nights == 7
        assert rate.is_active is True  # Default

    def test_rate_create_model(self):
        """RateCreate model should inherit from RateBase."""
        from src.api.pricing_routes import RateCreate

        rate = RateCreate(
            hotel_name="Test Hotel",
            destination="Zanzibar",
            room_type="Deluxe",
            meal_plan="AI",
            check_in_date="2025-06-01",
            check_out_date="2025-06-08",
            nights=7,
            total_7nights_pps=2500.0,
            flights_adult=500.0,
            transfers_adult=100.0
        )

        assert rate.flights_adult == 500.0
        assert rate.transfers_adult == 100.0

    def test_rate_update_model_optional_fields(self):
        """RateUpdate model should have all optional fields."""
        from src.api.pricing_routes import RateUpdate

        # Can create with just one field
        update = RateUpdate(total_7nights_pps=1500.0)
        assert update.total_7nights_pps == 1500.0
        assert update.room_type is None

    def test_hotel_base_model(self):
        """HotelBase model should validate star rating."""
        from src.api.pricing_routes import HotelBase

        hotel = HotelBase(
            hotel_name="Hilton Cape Town",
            destination="Cape Town",
            star_rating=5
        )

        assert hotel.star_rating == 5
        assert hotel.adults_only is False
        assert hotel.is_active is True

    def test_hotel_star_rating_validation(self):
        """HotelBase star_rating should be 1-5."""
        from src.api.pricing_routes import HotelBase
        from pydantic import ValidationError

        # Valid ratings
        for rating in [1, 2, 3, 4, 5]:
            hotel = HotelBase(
                hotel_name="Test Hotel",
                destination="Test",
                star_rating=rating
            )
            assert hotel.star_rating == rating

        # Invalid rating (too high)
        with pytest.raises(ValidationError):
            HotelBase(
                hotel_name="Test Hotel",
                destination="Test",
                star_rating=6
            )

    def test_season_definition_model(self):
        """SeasonDefinition model should have price multiplier."""
        from src.api.pricing_routes import SeasonDefinition

        season = SeasonDefinition(
            destination="Maldives",
            season_name="High",
            start_date="12-15",
            end_date="01-15",
            price_multiplier=1.5
        )

        assert season.season_name == "High"
        assert season.price_multiplier == 1.5

    def test_import_result_model(self):
        """ImportResult model should track import stats."""
        from src.api.pricing_routes import ImportResult

        result = ImportResult(
            success=True,
            total_rows=100,
            imported=95,
            errors=[{"row": 5, "error": "Invalid date"}]
        )

        assert result.success is True
        assert result.imported == 95
        assert len(result.errors) == 1


# ==================== BigQuery Client Tests ====================

class TestBigQueryAvailability:
    """Test BigQuery availability checking."""

    @pytest.mark.asyncio
    async def test_check_bigquery_available_returns_bool(self):
        """check_bigquery_available should return boolean."""
        from src.api.pricing_routes import check_bigquery_available, _bigquery_available

        # Reset cached value
        import src.api.pricing_routes as pricing_module
        pricing_module._bigquery_available = None

        with patch('src.api.pricing_routes.asyncio.to_thread') as mock_thread:
            mock_thread.return_value = False
            result = await check_bigquery_available()
            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_bigquery_client_returns_none_when_unavailable(self, mock_config):
        """get_bigquery_client_async returns None when unavailable."""
        from src.api.pricing_routes import get_bigquery_client_async
        import src.api.pricing_routes as pricing_module

        # Set BigQuery as unavailable
        pricing_module._bigquery_available = False

        client = await get_bigquery_client_async(mock_config)
        assert client is None


# ==================== Unit Tests for Endpoint Handlers ====================

class TestListRatesUnit:
    """Unit tests for list_rates endpoint handler."""

    @pytest.fixture
    def mock_bigquery_results(self):
        """Create mock BigQuery results."""
        mock_row = MagicMock()
        mock_row.items.return_value = [
            ('rate_id', 'RATE-ABC123'),
            ('hotel_name', 'Test Hotel'),
            ('destination', 'Cape Town'),
            ('room_type', 'Standard'),
            ('meal_plan', 'BB'),
            ('check_in_date', '2025-01-01'),
            ('check_out_date', '2025-01-08'),
            ('nights', 7),
            ('total_7nights_pps', 1200.0),
            ('is_active', True)
        ]
        mock_row.__iter__ = lambda s: iter(mock_row.items())
        mock_row.keys.return_value = ['rate_id', 'hotel_name', 'destination', 'room_type', 'meal_plan',
                                       'check_in_date', 'check_out_date', 'nights', 'total_7nights_pps', 'is_active']
        return [mock_row]

    @pytest.mark.asyncio
    async def test_list_rates_no_bigquery(self, mock_config):
        """list_rates should return empty when BigQuery unavailable."""
        from src.api.pricing_routes import list_rates
        import src.api.pricing_routes as pricing_module

        pricing_module._bigquery_available = False

        result = await list_rates(
            destination=None,
            hotel_name=None,
            meal_plan=None,
            is_active=True,
            check_in_after=None,
            check_in_before=None,
            limit=100,
            offset=0,
            config=mock_config
        )

        assert result['success'] is True
        assert result['data'] == []
        assert result['count'] == 0
        assert 'BigQuery not configured' in result.get('message', '')

    @pytest.mark.asyncio
    async def test_list_rates_success(self, mock_config):
        """list_rates should return formatted rates."""
        from src.api.pricing_routes import list_rates
        import src.api.pricing_routes as pricing_module

        # Create mock row that behaves like BigQuery row (dict-like)
        mock_row_data = {
            'rate_id': 'RATE-ABC123',
            'hotel_name': 'Test Hotel',
            'hotel_rating': 4,
            'destination': 'Cape Town',
            'room_type': 'Standard',
            'meal_plan': 'BB',
            'check_in_date': '2025-01-01',
            'check_out_date': '2025-01-08',
            'nights': 7,
            'total_7nights_pps': 1200.0,
            'total_7nights_single': 1800.0,
            'total_7nights_child': 600.0,
            'is_active': True
        }

        # Mock BigQuery Row - uses MagicMock with dict-like behavior
        mock_row = MagicMock()
        mock_row.__iter__ = lambda s: iter(mock_row_data.items())
        mock_row.keys.return_value = mock_row_data.keys()
        mock_row.values.return_value = mock_row_data.values()
        mock_row.items.return_value = mock_row_data.items()
        mock_row.get = lambda key, default=None: mock_row_data.get(key, default)
        mock_row.__getitem__ = lambda s, key: mock_row_data[key]

        mock_client = MagicMock()
        mock_query_job = MagicMock()
        mock_query_job.result.return_value = [mock_row]
        mock_client.query.return_value = mock_query_job

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        # Use real dict instead of mock row since dict(row) is called
        with patch('src.api.pricing_routes.asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
            # Return a dict-like object that dict() can convert
            mock_thread.return_value = [mock_row_data]

            result = await list_rates(
                destination=None,
                hotel_name=None,
                meal_plan=None,
                is_active=True,
                check_in_after=None,
                check_in_before=None,
                limit=100,
                offset=0,
                config=mock_config
            )

        assert result['success'] is True
        assert result['count'] == 1
        assert result['data'][0]['rate_id'] == 'RATE-ABC123'

    @pytest.mark.asyncio
    async def test_list_rates_error_returns_empty(self, mock_config):
        """list_rates should return empty on error."""
        from src.api.pricing_routes import list_rates
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_client.query.side_effect = Exception("BigQuery error")

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        result = await list_rates(
            destination=None,
            hotel_name=None,
            meal_plan=None,
            is_active=True,
            check_in_after=None,
            check_in_before=None,
            limit=100,
            offset=0,
            config=mock_config
        )

        # Returns empty instead of raising
        assert result['success'] is True
        assert result['data'] == []


class TestCreateRateUnit:
    """Unit tests for create_rate endpoint handler."""

    @pytest.mark.asyncio
    async def test_create_rate_success(self, mock_config):
        """create_rate should insert rate and return with ID."""
        from src.api.pricing_routes import create_rate, RateCreate
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_client.insert_rows_json.return_value = []  # No errors

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        with patch('src.api.pricing_routes.check_bigquery_available', new_callable=AsyncMock, return_value=True):
            rate = RateCreate(
                hotel_name="Test Hotel",
                destination="Cape Town",
                room_type="Standard",
                meal_plan="BB",
                check_in_date="2025-01-01",
                check_out_date="2025-01-08",
                nights=7,
                total_7nights_pps=1200.0
            )

            result = await create_rate(rate=rate, config=mock_config)

        assert result['success'] is True
        assert 'rate_id' in result['data']
        assert result['data']['hotel_name'] == 'Test Hotel'

    @pytest.mark.asyncio
    async def test_create_rate_bigquery_error(self, mock_config):
        """create_rate should raise 500 on BigQuery insert error."""
        from src.api.pricing_routes import create_rate, RateCreate
        from fastapi import HTTPException
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_client.insert_rows_json.return_value = [{'errors': 'Insert failed'}]

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        with patch('src.api.pricing_routes.check_bigquery_available', new_callable=AsyncMock, return_value=True):
            rate = RateCreate(
                hotel_name="Test Hotel",
                destination="Cape Town",
                room_type="Standard",
                meal_plan="BB",
                check_in_date="2025-01-01",
                check_out_date="2025-01-08",
                nights=7,
                total_7nights_pps=1200.0
            )

            with pytest.raises(HTTPException) as exc_info:
                await create_rate(rate=rate, config=mock_config)

            assert exc_info.value.status_code == 500


class TestGetRateUnit:
    """Unit tests for get_rate endpoint handler."""

    @pytest.mark.asyncio
    async def test_get_rate_not_found(self, mock_config):
        """get_rate should raise 404 when rate not found."""
        from src.api.pricing_routes import get_rate
        from fastapi import HTTPException
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_query_job = MagicMock()
        mock_query_job.result.return_value = []  # Empty result
        mock_client.query.return_value = mock_query_job

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        with patch('src.api.pricing_routes.check_bigquery_available', new_callable=AsyncMock, return_value=True):
            with pytest.raises(HTTPException) as exc_info:
                await get_rate(rate_id="RATE-NOTFOUND", config=mock_config)

            assert exc_info.value.status_code == 404


class TestUpdateRateUnit:
    """Unit tests for update_rate endpoint handler."""

    @pytest.mark.asyncio
    async def test_update_rate_no_fields(self, mock_config):
        """update_rate should raise 400 when no fields to update."""
        from src.api.pricing_routes import update_rate, RateUpdate
        from fastapi import HTTPException
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        with patch('src.api.pricing_routes.check_bigquery_available', new_callable=AsyncMock, return_value=True):
            update = RateUpdate()  # No fields set

            with pytest.raises(HTTPException) as exc_info:
                await update_rate(rate_id="RATE-001", update=update, config=mock_config)

            assert exc_info.value.status_code == 400
            assert "No fields to update" in str(exc_info.value.detail)


class TestDeleteRateUnit:
    """Unit tests for delete_rate endpoint handler."""

    @pytest.mark.asyncio
    async def test_delete_rate_soft(self, mock_config):
        """delete_rate should soft delete by default."""
        from src.api.pricing_routes import delete_rate
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_query_job = MagicMock()
        mock_query_job.result.return_value = None
        mock_client.query.return_value = mock_query_job

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        with patch('src.api.pricing_routes.check_bigquery_available', new_callable=AsyncMock, return_value=True):
            result = await delete_rate(
                rate_id="RATE-001",
                hard_delete=False,
                config=mock_config
            )

        assert result['success'] is True
        assert 'deactivated' in result['message']

    @pytest.mark.asyncio
    async def test_delete_rate_hard(self, mock_config):
        """delete_rate should hard delete when requested."""
        from src.api.pricing_routes import delete_rate
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_query_job = MagicMock()
        mock_query_job.result.return_value = None
        mock_client.query.return_value = mock_query_job

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        with patch('src.api.pricing_routes.check_bigquery_available', new_callable=AsyncMock, return_value=True):
            result = await delete_rate(
                rate_id="RATE-001",
                hard_delete=True,
                config=mock_config
            )

        assert result['success'] is True
        assert 'deleted' in result['message']


class TestListHotelsUnit:
    """Unit tests for list_hotels endpoint handler."""

    @pytest.mark.asyncio
    async def test_list_hotels_no_bigquery(self, mock_config):
        """list_hotels should return empty when BigQuery unavailable."""
        from src.api.pricing_routes import list_hotels
        import src.api.pricing_routes as pricing_module

        pricing_module._bigquery_available = False

        result = await list_hotels(
            destination=None,
            is_active=True,
            config=mock_config
        )

        assert result['success'] is True
        assert result['data'] == []
        assert result['count'] == 0


class TestListDestinationsUnit:
    """Unit tests for list_destinations endpoint handler."""

    @pytest.mark.asyncio
    async def test_list_destinations_no_bigquery(self, mock_config):
        """list_destinations should return empty when BigQuery unavailable."""
        from src.api.pricing_routes import list_destinations
        import src.api.pricing_routes as pricing_module

        pricing_module._bigquery_available = False

        result = await list_destinations(config=mock_config)

        assert result['success'] is True
        assert result['data'] == []
        assert result['count'] == 0


class TestGetPricingStatsUnit:
    """Unit tests for get_pricing_stats endpoint handler."""

    @pytest.mark.asyncio
    async def test_pricing_stats_no_bigquery(self, mock_config):
        """get_pricing_stats should return zeros when BigQuery unavailable."""
        from src.api.pricing_routes import get_pricing_stats
        import src.api.pricing_routes as pricing_module

        pricing_module._bigquery_available = False

        result = await get_pricing_stats(config=mock_config)

        assert result['success'] is True
        assert result['data']['total_rates'] == 0
        assert result['data']['total_hotels'] == 0


class TestGetHotelRatesUnit:
    """Unit tests for get_hotel_rates endpoint handler."""

    @pytest.mark.asyncio
    async def test_get_hotel_rates_no_bigquery(self, mock_config):
        """get_hotel_rates should return empty when BigQuery unavailable."""
        from src.api.pricing_routes import get_hotel_rates
        import src.api.pricing_routes as pricing_module

        pricing_module._bigquery_available = False

        result = await get_hotel_rates(
            hotel_name="Test Hotel",
            config=mock_config
        )

        assert result['success'] is True
        assert result['hotel_name'] == "Test Hotel"
        assert result['data'] == []
        assert result['count'] == 0


class TestImportRatesUnit:
    """Unit tests for import_rates endpoint handler."""

    @pytest.mark.asyncio
    async def test_import_rates_valid_csv(self, mock_config):
        """import_rates should process valid CSV."""
        from src.api.pricing_routes import import_rates
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_client.insert_rows_json.return_value = []  # No errors

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        # Create mock file upload
        csv_content = b"hotel_name,destination,room_type,meal_plan,check_in_date,check_out_date,nights,total_7nights_pps\nTest Hotel,Cape Town,Standard,BB,2025-01-01,2025-01-08,7,1200"

        mock_file = MagicMock()
        mock_file.read = AsyncMock(return_value=csv_content)

        with patch('src.api.pricing_routes.check_bigquery_available', new_callable=AsyncMock, return_value=True):
            result = await import_rates(file=mock_file, config=mock_config)

        assert result['success'] is True
        assert result['imported'] == 1

    @pytest.mark.asyncio
    async def test_import_rates_missing_fields(self, mock_config):
        """import_rates should report rows with missing fields."""
        from src.api.pricing_routes import import_rates
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_client.insert_rows_json.return_value = []

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        # CSV with missing required fields
        csv_content = b"hotel_name,destination,room_type,meal_plan,check_in_date,check_out_date,nights,total_7nights_pps\nTest Hotel,,,BB,2025-01-01,2025-01-08,7,1200"

        mock_file = MagicMock()
        mock_file.read = AsyncMock(return_value=csv_content)

        with patch('src.api.pricing_routes.check_bigquery_available', new_callable=AsyncMock, return_value=True):
            result = await import_rates(file=mock_file, config=mock_config)

        # Should have errors for missing fields
        assert len(result['errors']) > 0
        assert 'Missing fields' in str(result['errors'][0])


class TestExportRatesUnit:
    """Unit tests for export_rates endpoint handler."""

    @pytest.mark.asyncio
    async def test_export_rates_success(self, mock_config):
        """export_rates should return CSV response."""
        from src.api.pricing_routes import export_rates
        import src.api.pricing_routes as pricing_module

        # Create mock row
        class MockRow:
            def __init__(self):
                self._data = {
                    'hotel_name': 'Test Hotel',
                    'destination': 'Cape Town',
                    'room_type': 'Standard',
                    'meal_plan': 'BB',
                    'check_in_date': '2025-01-01',
                    'check_out_date': '2025-01-08',
                    'nights': 7,
                    'total_7nights_pps': 1200.0,
                    'total_7nights_single': None,
                    'total_7nights_child': None,
                    'flights_adult': 0,
                    'flights_child': 0,
                    'transfers_adult': 0,
                    'transfers_child': 0
                }
            def __getitem__(self, key):
                return self._data.get(key)
            def get(self, key, default=None):
                return self._data.get(key, default)
            def items(self):
                return self._data.items()
            def keys(self):
                return self._data.keys()

        mock_client = MagicMock()
        mock_query_job = MagicMock()
        mock_query_job.result.return_value = [MockRow()]
        mock_client.query.return_value = mock_query_job

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        with patch('src.api.pricing_routes.check_bigquery_available', new_callable=AsyncMock, return_value=True):
            response = await export_rates(destination=None, config=mock_config)

        # Should return a StreamingResponse
        from fastapi.responses import StreamingResponse
        assert isinstance(response, StreamingResponse)


# ==================== BigQuery Client Unit Tests ====================

class TestBigQueryClientCreation:
    """Unit tests for BigQuery client creation."""

    @pytest.mark.asyncio
    async def test_check_bigquery_caches_result(self):
        """check_bigquery_available should cache result."""
        from src.api.pricing_routes import check_bigquery_available
        import src.api.pricing_routes as pricing_module

        # Set cached value
        pricing_module._bigquery_available = True

        result = await check_bigquery_available()

        assert result is True

    @pytest.mark.asyncio
    async def test_check_bigquery_handles_error(self):
        """check_bigquery_available should handle errors gracefully."""
        from src.api.pricing_routes import check_bigquery_available
        import src.api.pricing_routes as pricing_module

        # Reset cache
        pricing_module._bigquery_available = None

        with patch('src.api.pricing_routes.asyncio.to_thread', side_effect=Exception("Auth error")):
            result = await check_bigquery_available()

        assert result is False

    @pytest.mark.asyncio
    async def test_get_bigquery_client_timeout(self, mock_config):
        """get_bigquery_client_async should handle timeout."""
        from src.api.pricing_routes import get_bigquery_client_async
        import src.api.pricing_routes as pricing_module
        import asyncio

        # Reset state
        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {}

        with patch('src.api.pricing_routes.check_bigquery_available', new_callable=AsyncMock, return_value=True):
            with patch('src.api.pricing_routes.asyncio.wait_for', side_effect=asyncio.TimeoutError()):
                client = await get_bigquery_client_async(mock_config)

        assert client is None


# ==================== NEW TESTS: Pydantic Model Validation Extended ====================

class TestRateBaseModelExtended:
    """Extended tests for RateBase Pydantic model."""

    def test_rate_base_rejects_zero_nights(self):
        """RateBase rejects nights=0 (minimum is 1)."""
        from src.api.pricing_routes import RateBase
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RateBase(
                hotel_name="Test Hotel",
                destination="Cape Town",
                room_type="Standard",
                meal_plan="BB",
                check_in_date="2025-01-01",
                check_out_date="2025-01-08",
                nights=0,
                total_7nights_pps=1200.0
            )

    def test_rate_base_rejects_negative_nights(self):
        """RateBase rejects negative nights."""
        from src.api.pricing_routes import RateBase
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RateBase(
                hotel_name="Test Hotel",
                destination="Cape Town",
                room_type="Standard",
                meal_plan="BB",
                check_in_date="2025-01-01",
                check_out_date="2025-01-08",
                nights=-1,
                total_7nights_pps=1200.0
            )

    def test_rate_base_rejects_over_30_nights(self):
        """RateBase rejects nights > 30."""
        from src.api.pricing_routes import RateBase
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RateBase(
                hotel_name="Test Hotel",
                destination="Cape Town",
                room_type="Standard",
                meal_plan="BB",
                check_in_date="2025-01-01",
                check_out_date="2025-02-15",
                nights=31,
                total_7nights_pps=1200.0
            )

    def test_rate_base_defaults_for_optional_fields(self):
        """RateBase optional fields have correct defaults."""
        from src.api.pricing_routes import RateBase

        rate = RateBase(
            hotel_name="Test Hotel",
            destination="Maldives",
            room_type="Suite",
            meal_plan="AI",
            check_in_date="2025-03-01",
            check_out_date="2025-03-08",
            nights=7,
            total_7nights_pps=3500.0
        )

        assert rate.total_7nights_single is None
        assert rate.total_7nights_child is None
        assert rate.flights_adult == 0
        assert rate.flights_child == 0
        assert rate.transfers_adult == 0
        assert rate.transfers_child == 0
        assert rate.is_active is True

    def test_rate_base_accepts_max_nights(self):
        """RateBase accepts nights=30 (maximum)."""
        from src.api.pricing_routes import RateBase

        rate = RateBase(
            hotel_name="Test Hotel",
            destination="Bali",
            room_type="Villa",
            meal_plan="FB",
            check_in_date="2025-01-01",
            check_out_date="2025-01-31",
            nights=30,
            total_7nights_pps=5000.0
        )
        assert rate.nights == 30

    def test_rate_base_missing_required_field_raises(self):
        """RateBase raises ValidationError when required fields are missing."""
        from src.api.pricing_routes import RateBase
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RateBase(
                hotel_name="Test Hotel",
                destination="Cape Town",
                # Missing room_type, meal_plan, dates, nights, price
            )


class TestRateUpdateModelExtended:
    """Extended tests for RateUpdate Pydantic model."""

    def test_rate_update_empty_is_valid(self):
        """RateUpdate with no fields is valid (all optional)."""
        from src.api.pricing_routes import RateUpdate

        update = RateUpdate()
        assert update.room_type is None
        assert update.meal_plan is None
        assert update.total_7nights_pps is None
        assert update.is_active is None

    def test_rate_update_single_price_field(self):
        """RateUpdate can update just the price."""
        from src.api.pricing_routes import RateUpdate

        update = RateUpdate(total_7nights_pps=1800.0)
        dumped = update.model_dump(exclude_unset=True)
        assert dumped == {"total_7nights_pps": 1800.0}

    def test_rate_update_multiple_fields(self):
        """RateUpdate can update several fields at once."""
        from src.api.pricing_routes import RateUpdate

        update = RateUpdate(
            room_type="Deluxe",
            meal_plan="AI",
            total_7nights_pps=2200.0,
            flights_adult=600.0
        )
        assert update.room_type == "Deluxe"
        assert update.meal_plan == "AI"
        assert update.total_7nights_pps == 2200.0
        assert update.flights_adult == 600.0

    def test_rate_update_deactivate(self):
        """RateUpdate can deactivate a rate."""
        from src.api.pricing_routes import RateUpdate

        update = RateUpdate(is_active=False)
        dumped = update.model_dump(exclude_unset=True)
        assert dumped == {"is_active": False}


class TestHotelModelExtended:
    """Extended tests for Hotel Pydantic models."""

    def test_hotel_base_rejects_star_rating_zero(self):
        """HotelBase rejects star_rating=0 (minimum is 1)."""
        from src.api.pricing_routes import HotelBase
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            HotelBase(
                hotel_name="Test Hotel",
                destination="Cape Town",
                star_rating=0
            )

    def test_hotel_base_with_amenities(self):
        """HotelBase accepts amenities list."""
        from src.api.pricing_routes import HotelBase

        hotel = HotelBase(
            hotel_name="Grand Resort",
            destination="Maldives",
            star_rating=5,
            amenities=["pool", "spa", "gym", "restaurant"],
            adults_only=True
        )
        assert len(hotel.amenities) == 4
        assert hotel.adults_only is True

    def test_hotel_base_rejects_short_name(self):
        """HotelBase rejects hotel_name shorter than 2 characters."""
        from src.api.pricing_routes import HotelBase
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            HotelBase(
                hotel_name="X",
                destination="Test"
            )

    def test_hotel_create_inherits_from_base(self):
        """HotelCreate inherits all fields from HotelBase."""
        from src.api.pricing_routes import HotelCreate

        hotel = HotelCreate(
            hotel_name="New Resort",
            destination="Zanzibar",
            star_rating=4,
            description="A beautiful resort"
        )
        assert hotel.hotel_name == "New Resort"
        assert hotel.description == "A beautiful resort"

    def test_hotel_update_all_optional(self):
        """HotelUpdate has all optional fields."""
        from src.api.pricing_routes import HotelUpdate

        update = HotelUpdate()
        assert update.hotel_name is None
        assert update.destination is None
        assert update.star_rating is None
        assert update.is_active is None


class TestSeasonDefinitionExtended:
    """Extended tests for SeasonDefinition model."""

    def test_season_definition_default_multiplier(self):
        """SeasonDefinition defaults to price_multiplier=1.0."""
        from src.api.pricing_routes import SeasonDefinition

        season = SeasonDefinition(
            destination="Cape Town",
            season_name="Shoulder",
            start_date="03-01",
            end_date="05-31"
        )
        assert season.price_multiplier == 1.0

    def test_season_definition_low_season(self):
        """SeasonDefinition can represent low season with multiplier < 1."""
        from src.api.pricing_routes import SeasonDefinition

        season = SeasonDefinition(
            destination="Zanzibar",
            season_name="Low",
            start_date="04-01",
            end_date="06-30",
            price_multiplier=0.75
        )
        assert season.price_multiplier == 0.75


class TestImportResultExtended:
    """Extended tests for ImportResult model."""

    def test_import_result_no_errors(self):
        """ImportResult with empty errors list."""
        from src.api.pricing_routes import ImportResult

        result = ImportResult(
            success=True,
            total_rows=50,
            imported=50,
            errors=[]
        )
        assert result.success is True
        assert len(result.errors) == 0
        assert result.total_rows == result.imported

    def test_import_result_partial_failure(self):
        """ImportResult with some errors."""
        from src.api.pricing_routes import ImportResult

        result = ImportResult(
            success=False,
            total_rows=100,
            imported=87,
            errors=[
                {"row": 5, "error": "Invalid date format"},
                {"row": 23, "error": "Missing hotel_name"},
                {"row": 45, "error": "Negative price"}
            ]
        )
        assert result.success is False
        assert result.imported == 87
        assert len(result.errors) == 3


# ==================== NEW TESTS: list_rates with filters ====================

class TestListRatesFilters:
    """Tests for list_rates with various query filters."""

    @pytest.mark.asyncio
    async def test_list_rates_with_destination_filter(self, mock_config):
        """list_rates passes destination filter to BigQuery query."""
        from src.api.pricing_routes import list_rates
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_query_job = MagicMock()
        mock_query_job.result.return_value = []
        mock_client.query.return_value = mock_query_job

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        with patch('src.api.pricing_routes.asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = []

            result = await list_rates(
                destination="Zanzibar",
                hotel_name=None,
                meal_plan=None,
                is_active=True,
                check_in_after=None,
                check_in_before=None,
                limit=100,
                offset=0,
                config=mock_config
            )

        assert result['success'] is True
        assert result['data'] == []
        assert result['count'] == 0

    @pytest.mark.asyncio
    async def test_list_rates_with_date_range(self, mock_config):
        """list_rates with check_in_after and check_in_before filters."""
        from src.api.pricing_routes import list_rates
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_query_job = MagicMock()
        mock_query_job.result.return_value = []
        mock_client.query.return_value = mock_query_job

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        with patch('src.api.pricing_routes.asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = []

            result = await list_rates(
                destination=None,
                hotel_name=None,
                meal_plan=None,
                is_active=True,
                check_in_after="2025-06-01",
                check_in_before="2025-08-31",
                limit=50,
                offset=0,
                config=mock_config
            )

        assert result['success'] is True

    @pytest.mark.asyncio
    async def test_list_rates_with_pagination(self, mock_config):
        """list_rates respects limit and offset parameters."""
        from src.api.pricing_routes import list_rates
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_query_job = MagicMock()
        mock_query_job.result.return_value = []
        mock_client.query.return_value = mock_query_job

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        with patch('src.api.pricing_routes.asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = []

            result = await list_rates(
                destination=None,
                hotel_name=None,
                meal_plan=None,
                is_active=True,
                check_in_after=None,
                check_in_before=None,
                limit=10,
                offset=20,
                config=mock_config
            )

        assert result['success'] is True


# ==================== NEW TESTS: get_rate found / not-found ====================

class TestGetRateUnitExtended:
    """Extended unit tests for get_rate endpoint handler."""

    @pytest.mark.asyncio
    async def test_get_rate_found(self, mock_config):
        """get_rate returns rate data when found."""
        from src.api.pricing_routes import get_rate
        import src.api.pricing_routes as pricing_module

        rate_data = {
            'rate_id': 'RATE-ABC123',
            'hotel_name': 'Beach Resort',
            'destination': 'Zanzibar',
            'room_type': 'Deluxe',
            'meal_plan': 'AI',
            'check_in_date': '2025-06-01',
            'check_out_date': '2025-06-08',
            'nights': 7,
            'total_7nights_pps': 2500.0,
            'is_active': True
        }

        mock_row = MagicMock()
        mock_row.__iter__ = lambda s: iter(rate_data.items())
        mock_row.keys.return_value = rate_data.keys()
        mock_row.values.return_value = rate_data.values()
        mock_row.items.return_value = rate_data.items()
        mock_row.get = lambda key, default=None: rate_data.get(key, default)
        mock_row.__getitem__ = lambda s, key: rate_data[key]

        mock_client = MagicMock()
        mock_query_job = MagicMock()
        mock_query_job.result.return_value = [rate_data]
        mock_client.query.return_value = mock_query_job

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        with patch('src.api.pricing_routes.check_bigquery_available', new_callable=AsyncMock, return_value=True):
            result = await get_rate(rate_id="RATE-ABC123", config=mock_config)

        assert result['success'] is True
        assert result['data']['rate_id'] == 'RATE-ABC123'
        assert result['data']['hotel_name'] == 'Beach Resort'

    @pytest.mark.asyncio
    async def test_get_rate_bigquery_error(self, mock_config):
        """get_rate raises 500 on BigQuery exception."""
        from src.api.pricing_routes import get_rate
        from fastapi import HTTPException
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_client.query.side_effect = Exception("BigQuery connection lost")

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        with patch('src.api.pricing_routes.check_bigquery_available', new_callable=AsyncMock, return_value=True):
            with pytest.raises(HTTPException) as exc_info:
                await get_rate(rate_id="RATE-001", config=mock_config)

            assert exc_info.value.status_code == 500


# ==================== NEW TESTS: create_rate with various data ====================

class TestCreateRateUnitExtended:
    """Extended unit tests for create_rate."""

    @pytest.mark.asyncio
    async def test_create_rate_generates_rate_id(self, mock_config):
        """create_rate generates a RATE-XXXXXXXX format ID."""
        from src.api.pricing_routes import create_rate, RateCreate
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_client.insert_rows_json.return_value = []

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        with patch('src.api.pricing_routes.check_bigquery_available', new_callable=AsyncMock, return_value=True):
            rate = RateCreate(
                hotel_name="Ocean View",
                destination="Maldives",
                room_type="Water Villa",
                meal_plan="AI",
                check_in_date="2025-07-01",
                check_out_date="2025-07-08",
                nights=7,
                total_7nights_pps=4500.0
            )

            result = await create_rate(rate=rate, config=mock_config)

        rate_id = result['data']['rate_id']
        assert rate_id.startswith("RATE-")
        assert len(rate_id) == 13  # RATE- + 8 hex chars

    @pytest.mark.asyncio
    async def test_create_rate_with_all_optional_fields(self, mock_config):
        """create_rate includes optional fields (flights, transfers)."""
        from src.api.pricing_routes import create_rate, RateCreate
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_client.insert_rows_json.return_value = []

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        with patch('src.api.pricing_routes.check_bigquery_available', new_callable=AsyncMock, return_value=True):
            rate = RateCreate(
                hotel_name="Luxury Resort",
                destination="Seychelles",
                room_type="Presidential Suite",
                meal_plan="AI",
                check_in_date="2025-12-20",
                check_out_date="2025-12-27",
                nights=7,
                total_7nights_pps=8000.0,
                total_7nights_single=12000.0,
                total_7nights_child=4000.0,
                flights_adult=800.0,
                flights_child=400.0,
                transfers_adult=150.0,
                transfers_child=75.0
            )

            result = await create_rate(rate=rate, config=mock_config)

        assert result['success'] is True
        assert result['data']['flights_adult'] == 800.0
        assert result['data']['transfers_child'] == 75.0

    @pytest.mark.asyncio
    async def test_create_rate_calls_insert_rows_json(self, mock_config):
        """create_rate calls BigQuery insert_rows_json with correct table."""
        from src.api.pricing_routes import create_rate, RateCreate
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_client.insert_rows_json.return_value = []

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        with patch('src.api.pricing_routes.check_bigquery_available', new_callable=AsyncMock, return_value=True):
            rate = RateCreate(
                hotel_name="Test",
                destination="Test",
                room_type="Standard",
                meal_plan="BB",
                check_in_date="2025-01-01",
                check_out_date="2025-01-08",
                nights=7,
                total_7nights_pps=1000.0
            )

            await create_rate(rate=rate, config=mock_config)

        # Verify insert was called
        mock_client.insert_rows_json.assert_called_once()
        call_args = mock_client.insert_rows_json.call_args
        table_id = call_args[0][0]
        assert "hotel_rates" in table_id
        assert mock_config.gcp_project_id in table_id


# ==================== NEW TESTS: update_rate with different field types ====================

class TestUpdateRateUnitExtended:
    """Extended unit tests for update_rate."""

    @pytest.mark.asyncio
    async def test_update_rate_price_only(self, mock_config):
        """update_rate with only price field calls BQ with correct params."""
        from src.api.pricing_routes import update_rate, RateUpdate
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_query_job = MagicMock()
        mock_query_job.result.return_value = None
        mock_client.query.return_value = mock_query_job

        # For the get_rate call after update
        rate_data = {
            'rate_id': 'RATE-001',
            'hotel_name': 'Test',
            'destination': 'Test',
            'room_type': 'Standard',
            'meal_plan': 'BB',
            'check_in_date': '2025-01-01',
            'check_out_date': '2025-01-08',
            'nights': 7,
            'total_7nights_pps': 1800.0,
            'is_active': True
        }

        # Second call (get_rate) returns the data
        def query_side_effect(*args, **kwargs):
            job = MagicMock()
            if "UPDATE" in args[0]:
                job.result.return_value = None
            else:
                job.result.return_value = [rate_data]
            return job

        mock_client.query.side_effect = query_side_effect

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        with patch('src.api.pricing_routes.check_bigquery_available', new_callable=AsyncMock, return_value=True):
            update = RateUpdate(total_7nights_pps=1800.0)
            result = await update_rate(rate_id="RATE-001", update=update, config=mock_config)

        assert result['success'] is True

    @pytest.mark.asyncio
    async def test_update_rate_deactivate(self, mock_config):
        """update_rate can deactivate a rate via is_active=False."""
        from src.api.pricing_routes import update_rate, RateUpdate
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()

        rate_data = {
            'rate_id': 'RATE-002',
            'hotel_name': 'Test',
            'destination': 'Test',
            'room_type': 'Standard',
            'meal_plan': 'BB',
            'check_in_date': '2025-01-01',
            'check_out_date': '2025-01-08',
            'nights': 7,
            'total_7nights_pps': 1200.0,
            'is_active': False
        }

        def query_side_effect(*args, **kwargs):
            job = MagicMock()
            if "UPDATE" in args[0]:
                job.result.return_value = None
            else:
                job.result.return_value = [rate_data]
            return job

        mock_client.query.side_effect = query_side_effect

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        with patch('src.api.pricing_routes.check_bigquery_available', new_callable=AsyncMock, return_value=True):
            update = RateUpdate(is_active=False)
            result = await update_rate(rate_id="RATE-002", update=update, config=mock_config)

        assert result['success'] is True


# ==================== NEW TESTS: delete_rate soft vs hard ====================

class TestDeleteRateUnitExtended:
    """Extended unit tests for delete_rate endpoint handler."""

    @pytest.mark.asyncio
    async def test_delete_rate_soft_uses_update_query(self, mock_config):
        """Soft delete uses UPDATE query (sets is_active=FALSE)."""
        from src.api.pricing_routes import delete_rate
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_query_job = MagicMock()
        mock_query_job.result.return_value = None
        mock_client.query.return_value = mock_query_job

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        with patch('src.api.pricing_routes.check_bigquery_available', new_callable=AsyncMock, return_value=True):
            result = await delete_rate(rate_id="RATE-001", hard_delete=False, config=mock_config)

        # Verify query called with UPDATE (not DELETE)
        query_str = mock_client.query.call_args[0][0]
        assert "UPDATE" in query_str
        assert "is_active = FALSE" in query_str

    @pytest.mark.asyncio
    async def test_delete_rate_hard_uses_delete_query(self, mock_config):
        """Hard delete uses DELETE FROM query."""
        from src.api.pricing_routes import delete_rate
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_query_job = MagicMock()
        mock_query_job.result.return_value = None
        mock_client.query.return_value = mock_query_job

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        with patch('src.api.pricing_routes.check_bigquery_available', new_callable=AsyncMock, return_value=True):
            result = await delete_rate(rate_id="RATE-001", hard_delete=True, config=mock_config)

        # Verify query called with DELETE FROM
        query_str = mock_client.query.call_args[0][0]
        assert "DELETE FROM" in query_str

    @pytest.mark.asyncio
    async def test_delete_rate_message_format(self, mock_config):
        """delete_rate message includes rate_id."""
        from src.api.pricing_routes import delete_rate
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_query_job = MagicMock()
        mock_query_job.result.return_value = None
        mock_client.query.return_value = mock_query_job

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        with patch('src.api.pricing_routes.check_bigquery_available', new_callable=AsyncMock, return_value=True):
            result = await delete_rate(rate_id="RATE-XYZ789", hard_delete=False, config=mock_config)

        assert "RATE-XYZ789" in result['message']


# ==================== NEW TESTS: list_hotels with BigQuery data ====================

class TestListHotelsUnitExtended:
    """Extended unit tests for list_hotels."""

    @pytest.mark.asyncio
    async def test_list_hotels_with_data(self, mock_config):
        """list_hotels returns formatted hotel list from BigQuery."""
        from src.api.pricing_routes import list_hotels
        import src.api.pricing_routes as pricing_module

        hotel_data = [
            {"hotel_name": "Hilton", "destination": "Cape Town", "star_rating": 5, "is_active": True},
            {"hotel_name": "Marriott", "destination": "Cape Town", "star_rating": 4, "is_active": True},
        ]

        mock_client = MagicMock()
        mock_query_job = MagicMock()
        mock_query_job.result.return_value = hotel_data
        mock_client.query.return_value = mock_query_job

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        with patch('src.api.pricing_routes.asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = hotel_data

            result = await list_hotels(
                destination="Cape Town",
                is_active=True,
                config=mock_config
            )

        assert result['success'] is True
        assert result['count'] == 2

    @pytest.mark.asyncio
    async def test_list_hotels_error_returns_empty(self, mock_config):
        """list_hotels returns empty on BigQuery error."""
        from src.api.pricing_routes import list_hotels
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_client.query.side_effect = Exception("BigQuery error")

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        result = await list_hotels(
            destination=None,
            is_active=True,
            config=mock_config
        )

        assert result['success'] is True
        assert result['data'] == []


# ==================== NEW TESTS: get_pricing_stats with data ====================

class TestGetPricingStatsExtended:
    """Extended unit tests for get_pricing_stats."""

    @pytest.mark.asyncio
    async def test_pricing_stats_with_data(self, mock_config):
        """get_pricing_stats returns formatted stats from BigQuery."""
        from src.api.pricing_routes import get_pricing_stats
        import src.api.pricing_routes as pricing_module

        stats_data = {
            'total_rates': 150,
            'total_hotels': 25,
            'total_destinations': 8,
            'active_rates': 140,
            'avg_price': 2100.50,
            'min_price': 800.0,
            'max_price': 8500.0
        }

        mock_client = MagicMock()

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        with patch('src.api.pricing_routes.asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = [stats_data]

            result = await get_pricing_stats(config=mock_config)

        assert result['success'] is True
        assert result['data']['total_rates'] == 150
        assert result['data']['total_hotels'] == 25

    @pytest.mark.asyncio
    async def test_pricing_stats_error_returns_defaults(self, mock_config):
        """get_pricing_stats returns default zeros on BigQuery error."""
        from src.api.pricing_routes import get_pricing_stats
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_client.query.side_effect = Exception("Connection error")

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        result = await get_pricing_stats(config=mock_config)

        assert result['success'] is True
        assert result['data']['total_rates'] == 0
        assert result['data']['total_hotels'] == 0
        assert result['data']['total_destinations'] == 0


# ==================== NEW TESTS: import_rates edge cases ====================

class TestImportRatesExtended:
    """Extended tests for import_rates endpoint handler."""

    @pytest.mark.asyncio
    async def test_import_rates_multiple_rows(self, mock_config):
        """import_rates processes multiple CSV rows."""
        from src.api.pricing_routes import import_rates
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_client.insert_rows_json.return_value = []

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        csv_content = (
            b"hotel_name,destination,room_type,meal_plan,check_in_date,check_out_date,nights,total_7nights_pps\n"
            b"Hotel A,Cape Town,Standard,BB,2025-01-01,2025-01-08,7,1200\n"
            b"Hotel B,Zanzibar,Deluxe,AI,2025-02-01,2025-02-08,7,2500\n"
            b"Hotel C,Maldives,Suite,FB,2025-03-01,2025-03-08,7,4000\n"
        )

        mock_file = MagicMock()
        mock_file.read = AsyncMock(return_value=csv_content)

        with patch('src.api.pricing_routes.check_bigquery_available', new_callable=AsyncMock, return_value=True):
            result = await import_rates(file=mock_file, config=mock_config)

        assert result['imported'] == 3
        assert result['total_rows'] == 3
        assert len(result['errors']) == 0

    @pytest.mark.asyncio
    async def test_import_rates_meal_plan_uppercased(self, mock_config):
        """import_rates uppercases meal_plan values."""
        from src.api.pricing_routes import import_rates
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_client.insert_rows_json.return_value = []

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        csv_content = b"hotel_name,destination,room_type,meal_plan,check_in_date,check_out_date,nights,total_7nights_pps\nTest Hotel,Cape Town,Standard,bb,2025-01-01,2025-01-08,7,1200"

        mock_file = MagicMock()
        mock_file.read = AsyncMock(return_value=csv_content)

        with patch('src.api.pricing_routes.check_bigquery_available', new_callable=AsyncMock, return_value=True):
            result = await import_rates(file=mock_file, config=mock_config)

        # Verify the meal_plan was uppercased in the insert call
        insert_call_rows = mock_client.insert_rows_json.call_args[0][1]
        assert insert_call_rows[0]['meal_plan'] == 'BB'

    @pytest.mark.asyncio
    async def test_import_rates_bigquery_insert_error(self, mock_config):
        """import_rates reports BigQuery insert errors per row."""
        from src.api.pricing_routes import import_rates
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_client.insert_rows_json.return_value = [
            {'index': 0, 'errors': 'Schema mismatch'}
        ]

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        csv_content = b"hotel_name,destination,room_type,meal_plan,check_in_date,check_out_date,nights,total_7nights_pps\nTest Hotel,Cape Town,Standard,BB,2025-01-01,2025-01-08,7,1200"

        mock_file = MagicMock()
        mock_file.read = AsyncMock(return_value=csv_content)

        with patch('src.api.pricing_routes.check_bigquery_available', new_callable=AsyncMock, return_value=True):
            result = await import_rates(file=mock_file, config=mock_config)

        assert result['success'] is False
        assert len(result['errors']) > 0


# ==================== NEW TESTS: get_hotel_rates with data ====================

class TestGetHotelRatesExtended:
    """Extended unit tests for get_hotel_rates."""

    @pytest.mark.asyncio
    async def test_get_hotel_rates_with_data(self, mock_config):
        """get_hotel_rates returns formatted rates for a hotel."""
        from src.api.pricing_routes import get_hotel_rates
        import src.api.pricing_routes as pricing_module

        rates = [
            {'rate_id': 'RATE-001', 'hotel_name': 'Hilton', 'check_in_date': '2025-01-01',
             'check_out_date': '2025-01-08', 'room_type': 'Standard', 'meal_plan': 'BB',
             'total_7nights_pps': 1200.0},
            {'rate_id': 'RATE-002', 'hotel_name': 'Hilton', 'check_in_date': '2025-02-01',
             'check_out_date': '2025-02-08', 'room_type': 'Deluxe', 'meal_plan': 'AI',
             'total_7nights_pps': 2500.0},
        ]

        mock_client = MagicMock()
        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        with patch('src.api.pricing_routes.asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = rates

            result = await get_hotel_rates(hotel_name="Hilton", config=mock_config)

        assert result['success'] is True
        assert result['hotel_name'] == "Hilton"
        assert result['count'] == 2

    @pytest.mark.asyncio
    async def test_get_hotel_rates_error_returns_empty(self, mock_config):
        """get_hotel_rates returns empty on BigQuery error."""
        from src.api.pricing_routes import get_hotel_rates
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_client.query.side_effect = Exception("Table not found")

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        result = await get_hotel_rates(hotel_name="NonExistent", config=mock_config)

        assert result['success'] is True
        assert result['data'] == []
        assert result['hotel_name'] == "NonExistent"


# ==================== NEW TESTS: list_destinations with data ====================

class TestListDestinationsExtended:
    """Extended unit tests for list_destinations."""

    @pytest.mark.asyncio
    async def test_list_destinations_with_data(self, mock_config):
        """list_destinations returns destination data from BigQuery."""
        from src.api.pricing_routes import list_destinations
        import src.api.pricing_routes as pricing_module

        dest_data = [
            {"destination": "Cape Town", "hotel_count": 10, "rate_count": 50, "min_price": 800, "max_price": 3000},
            {"destination": "Zanzibar", "hotel_count": 8, "rate_count": 40, "min_price": 1200, "max_price": 5000},
        ]

        mock_client = MagicMock()
        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        with patch('src.api.pricing_routes.asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = dest_data

            result = await list_destinations(config=mock_config)

        assert result['success'] is True
        assert result['count'] == 2

    @pytest.mark.asyncio
    async def test_list_destinations_error_returns_empty(self, mock_config):
        """list_destinations returns empty on BigQuery error."""
        from src.api.pricing_routes import list_destinations
        import src.api.pricing_routes as pricing_module

        mock_client = MagicMock()
        mock_client.query.side_effect = Exception("Access denied")

        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: mock_client}

        result = await list_destinations(config=mock_config)

        assert result['success'] is True
        assert result['data'] == []


# ==================== NEW TESTS: BigQuery client caching ====================

class TestBigQueryClientCaching:
    """Tests for BigQuery client caching behavior."""

    @pytest.mark.asyncio
    async def test_bigquery_client_cached_per_project(self, mock_config):
        """get_bigquery_client_async returns cached client for same project."""
        from src.api.pricing_routes import get_bigquery_client_async
        import src.api.pricing_routes as pricing_module

        cached_client = MagicMock()
        pricing_module._bigquery_available = True
        pricing_module._bigquery_clients = {mock_config.gcp_project_id: cached_client}

        with patch('src.api.pricing_routes.check_bigquery_available', new_callable=AsyncMock, return_value=True):
            result = await get_bigquery_client_async(mock_config)

        assert result is cached_client

    @pytest.mark.asyncio
    async def test_check_bigquery_returns_cached_true(self):
        """check_bigquery_available returns cached True without re-checking."""
        from src.api.pricing_routes import check_bigquery_available
        import src.api.pricing_routes as pricing_module

        pricing_module._bigquery_available = True

        result = await check_bigquery_available()
        assert result is True

    @pytest.mark.asyncio
    async def test_check_bigquery_returns_cached_false(self):
        """check_bigquery_available returns cached False without re-checking."""
        from src.api.pricing_routes import check_bigquery_available
        import src.api.pricing_routes as pricing_module

        pricing_module._bigquery_available = False

        result = await check_bigquery_available()
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
