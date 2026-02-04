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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
