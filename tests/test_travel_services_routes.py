"""
Travel Services Routes Unit Tests

Tests for flights, transfers, and activities API endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


# ==================== Fixtures ====================

@pytest.fixture
def test_client():
    """Create a basic TestClient."""
    from main import app
    return TestClient(app)


# ==================== Model Tests ====================

class TestFlightResult:
    """Tests for FlightResult model."""

    def test_flight_result_required_fields(self):
        """FlightResult should have required fields."""
        from src.api.travel_services_routes import FlightResult

        result = FlightResult(
            destination="zanzibar",
            price_per_person=5000.0
        )

        assert result.destination == "zanzibar"
        assert result.price_per_person == 5000.0
        assert result.currency == "ZAR"

    def test_flight_result_optional_fields(self):
        """FlightResult should have optional fields."""
        from src.api.travel_services_routes import FlightResult

        result = FlightResult(
            destination="mauritius",
            price_per_person=8000.0,
            airline="SAA",
            departure_date="2026-03-15"
        )

        assert result.airline == "SAA"
        assert result.departure_date == "2026-03-15"


class TestFlightSearchResponse:
    """Tests for FlightSearchResponse model."""

    def test_success_response(self):
        """FlightSearchResponse should represent success."""
        from src.api.travel_services_routes import FlightSearchResponse

        response = FlightSearchResponse(
            success=True,
            destination="zanzibar",
            total_flights=5,
            flights=[{"destination": "zanzibar"}]
        )

        assert response.success is True
        assert response.total_flights == 5

    def test_error_response(self):
        """FlightSearchResponse should represent error."""
        from src.api.travel_services_routes import FlightSearchResponse

        response = FlightSearchResponse(
            success=False,
            error="BigQuery not configured"
        )

        assert response.success is False
        assert response.error == "BigQuery not configured"


class TestTransferResult:
    """Tests for TransferResult model."""

    def test_transfer_result_fields(self):
        """TransferResult should have required fields."""
        from src.api.travel_services_routes import TransferResult

        result = TransferResult(
            destination="zanzibar",
            transfers_adult=50.0,
            transfers_child=30.0
        )

        assert result.destination == "zanzibar"
        assert result.transfers_adult == 50.0
        assert result.transfers_child == 30.0


class TestActivityResult:
    """Tests for ActivityResult model."""

    def test_activity_result_required_fields(self):
        """ActivityResult should have required fields."""
        from src.api.travel_services_routes import ActivityResult

        result = ActivityResult(
            activity_id="ACT001",
            name="Spice Tour",
            destination="zanzibar",
            price_adult=45.0
        )

        assert result.activity_id == "ACT001"
        assert result.name == "Spice Tour"
        assert result.price_adult == 45.0

    def test_activity_result_optional_fields(self):
        """ActivityResult should have optional fields."""
        from src.api.travel_services_routes import ActivityResult

        result = ActivityResult(
            activity_id="ACT001",
            name="Spice Tour",
            destination="zanzibar",
            price_adult=45.0,
            price_child=25.0,
            category="Cultural",
            duration="Half Day"
        )

        assert result.price_child == 25.0
        assert result.category == "Cultural"


# ==================== Sample Activities Data Tests ====================

class TestSampleActivities:
    """Tests for SAMPLE_ACTIVITIES data."""

    def test_sample_activities_exists(self):
        """SAMPLE_ACTIVITIES should be defined."""
        from src.api.travel_services_routes import SAMPLE_ACTIVITIES

        assert isinstance(SAMPLE_ACTIVITIES, list)
        assert len(SAMPLE_ACTIVITIES) > 0

    def test_activity_has_required_fields(self):
        """Each activity should have required fields."""
        from src.api.travel_services_routes import SAMPLE_ACTIVITIES

        required_fields = ["activity_id", "name", "destination", "price_adult"]

        for activity in SAMPLE_ACTIVITIES:
            for field in required_fields:
                assert field in activity, f"Activity missing {field}"

    def test_activities_cover_multiple_destinations(self):
        """Activities should cover multiple destinations."""
        from src.api.travel_services_routes import SAMPLE_ACTIVITIES

        destinations = set(a["destination"] for a in SAMPLE_ACTIVITIES)

        assert len(destinations) >= 3  # At least 3 destinations


# ==================== Flights Endpoint Tests ====================

class TestListFlightsEndpoint:
    """Tests for GET /api/v1/travel/flights endpoint."""

    def test_list_flights_endpoint_exists(self, test_client):
        """GET /flights endpoint should exist."""
        response = test_client.get("/api/v1/travel/flights")

        # Should not be 404
        assert response.status_code != 404

    def test_list_flights_with_destination_filter(self, test_client):
        """GET /flights should accept destination filter."""
        # Will return error if BigQuery not configured, but endpoint should work
        response = test_client.get("/api/v1/travel/flights?destination=zanzibar")

        assert response.status_code == 200
        data = response.json()
        assert "success" in data


class TestSearchFlightsEndpoint:
    """Tests for GET /api/v1/travel/flights/search endpoint."""

    def test_search_flights_requires_destination(self, test_client):
        """GET /flights/search should require destination."""
        response = test_client.get("/api/v1/travel/flights/search")

        assert response.status_code == 422

    def test_search_flights_with_destination(self, test_client):
        """GET /flights/search should accept destination."""
        response = test_client.get("/api/v1/travel/flights/search?destination=zanzibar")

        assert response.status_code == 200


# ==================== Transfers Endpoint Tests ====================

class TestListTransfersEndpoint:
    """Tests for GET /api/v1/travel/transfers endpoint."""

    def test_list_transfers_endpoint_exists(self, test_client):
        """GET /transfers endpoint should exist."""
        response = test_client.get("/api/v1/travel/transfers")

        assert response.status_code != 404

    def test_list_transfers_response_format(self, test_client):
        """GET /transfers should return proper format."""
        response = test_client.get("/api/v1/travel/transfers")

        assert response.status_code == 200
        data = response.json()
        assert "success" in data


class TestSearchTransfersEndpoint:
    """Tests for GET /api/v1/travel/transfers/search endpoint."""

    def test_search_transfers_requires_destination(self, test_client):
        """GET /transfers/search should require destination."""
        response = test_client.get("/api/v1/travel/transfers/search")

        assert response.status_code == 422

    def test_search_transfers_with_destination(self, test_client):
        """GET /transfers/search should accept destination."""
        response = test_client.get("/api/v1/travel/transfers/search?destination=zanzibar")

        assert response.status_code == 200


# ==================== Activities Endpoint Tests ====================

class TestListActivitiesEndpoint:
    """Tests for GET /api/v1/travel/activities endpoint."""

    def test_list_activities_returns_data(self, test_client):
        """GET /activities should return activities list."""
        response = test_client.get("/api/v1/travel/activities")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "activities" in data
        assert len(data["activities"]) > 0

    def test_list_activities_filter_by_destination(self, test_client):
        """GET /activities should filter by destination."""
        response = test_client.get("/api/v1/travel/activities?destination=zanzibar")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # All activities should be for zanzibar
        for activity in data["activities"]:
            assert activity["destination"].lower() == "zanzibar"

    def test_list_activities_filter_by_category(self, test_client):
        """GET /activities should filter by category."""
        response = test_client.get("/api/v1/travel/activities?category=Cultural")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # All activities should be Cultural category
        for activity in data["activities"]:
            assert activity["category"].lower() == "cultural"

    def test_list_activities_respects_limit(self, test_client):
        """GET /activities should respect limit parameter."""
        response = test_client.get("/api/v1/travel/activities?limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["activities"]) <= 2


class TestSearchActivitiesEndpoint:
    """Tests for GET /api/v1/travel/activities/search endpoint."""

    def test_search_activities_requires_destination(self, test_client):
        """GET /activities/search should require destination."""
        response = test_client.get("/api/v1/travel/activities/search")

        assert response.status_code == 422

    def test_search_activities_with_destination(self, test_client):
        """GET /activities/search should return activities for destination."""
        response = test_client.get("/api/v1/travel/activities/search?destination=zanzibar")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["destination"] == "zanzibar"

    def test_search_activities_with_query(self, test_client):
        """GET /activities/search should filter by query text."""
        response = test_client.get("/api/v1/travel/activities/search?destination=zanzibar&query=spice")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Should find Spice Tour
        if data["activities"]:
            assert any("spice" in a["name"].lower() for a in data["activities"])


class TestActivityCategoriesEndpoint:
    """Tests for GET /api/v1/travel/activities/categories endpoint."""

    def test_list_categories(self, test_client):
        """GET /activities/categories should return categories."""
        response = test_client.get("/api/v1/travel/activities/categories")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "categories" in data
        assert len(data["categories"]) > 0

    def test_categories_are_unique(self, test_client):
        """Categories should be unique."""
        response = test_client.get("/api/v1/travel/activities/categories")
        data = response.json()

        categories = data["categories"]
        assert len(categories) == len(set(categories))


# ==================== Destinations Endpoint Tests ====================

class TestListDestinationsEndpoint:
    """Tests for GET /api/v1/travel/destinations endpoint."""

    def test_list_destinations(self, test_client):
        """GET /destinations should return destinations list."""
        response = test_client.get("/api/v1/travel/destinations")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "destinations" in data
        assert len(data["destinations"]) > 0

    def test_destination_has_required_fields(self, test_client):
        """Each destination should have required fields."""
        response = test_client.get("/api/v1/travel/destinations")
        data = response.json()

        required_fields = ["code", "name", "country"]

        for dest in data["destinations"]:
            for field in required_fields:
                assert field in dest

    def test_destination_has_service_flags(self, test_client):
        """Each destination should have service availability flags."""
        response = test_client.get("/api/v1/travel/destinations")
        data = response.json()

        service_flags = ["hotels", "activities", "flights", "transfers"]

        for dest in data["destinations"]:
            for flag in service_flags:
                assert flag in dest


# ==================== Dependency Tests ====================

class TestGetClientConfig:
    """Tests for get_client_config dependency."""

    def test_get_client_config_with_header(self):
        """Should use X-Client-ID header when provided."""
        from src.api.travel_services_routes import get_client_config

        with patch('src.api.travel_services_routes.get_config') as mock_get_config:
            mock_config = MagicMock()
            mock_get_config.return_value = mock_config

            result = get_client_config(x_client_id="my-tenant")

            mock_get_config.assert_called_once_with("my-tenant")

    def test_get_client_config_raises_on_error(self):
        """Should raise HTTPException on config error."""
        from src.api.travel_services_routes import get_client_config
        from fastapi import HTTPException

        with patch('src.api.travel_services_routes.get_config', side_effect=Exception("Not found")):
            with pytest.raises(HTTPException) as exc_info:
                get_client_config(x_client_id="unknown")

            assert exc_info.value.status_code == 400


# ==================== Include Router Tests ====================

class TestIncludeTravelRouter:
    """Tests for include_travel_router function."""

    def test_include_travel_router(self):
        """include_travel_router should add router to app."""
        from src.api.travel_services_routes import include_travel_router
        from fastapi import FastAPI

        app = FastAPI()

        include_travel_router(app)

        # Check that routes are included
        routes = [r.path for r in app.routes]
        assert any("/travel" in r for r in routes)


# ====================================================================
# NEW TESTS: Extended model tests
# ====================================================================

class TestFlightResultExtended:
    """Extended tests for FlightResult model."""

    def test_flight_result_currency_default_is_zar(self):
        """FlightResult currency should default to ZAR."""
        from src.api.travel_services_routes import FlightResult

        result = FlightResult(destination="maldives", price_per_person=12000.0)
        assert result.currency == "ZAR"

    def test_flight_result_currency_override(self):
        """FlightResult currency should be overridable."""
        from src.api.travel_services_routes import FlightResult

        result = FlightResult(
            destination="maldives",
            price_per_person=800.0,
            currency="USD"
        )
        assert result.currency == "USD"

    def test_flight_result_all_optional_fields_none_by_default(self):
        """All optional fields on FlightResult should default to None."""
        from src.api.travel_services_routes import FlightResult

        result = FlightResult(destination="kenya", price_per_person=7500.0)

        assert result.departure_date is None
        assert result.return_date is None
        assert result.airline is None

    def test_flight_result_return_date_field(self):
        """FlightResult should accept return_date."""
        from src.api.travel_services_routes import FlightResult

        result = FlightResult(
            destination="zanzibar",
            price_per_person=5000.0,
            departure_date="2026-06-01",
            return_date="2026-06-08"
        )
        assert result.return_date == "2026-06-08"


class TestTransferResultExtended:
    """Extended tests for TransferResult model."""

    def test_transfer_result_currency_default(self):
        """TransferResult currency should default to ZAR."""
        from src.api.travel_services_routes import TransferResult

        result = TransferResult(
            destination="mauritius",
            transfers_adult=60.0,
            transfers_child=35.0
        )
        assert result.currency == "ZAR"

    def test_transfer_result_currency_override(self):
        """TransferResult currency should be overridable."""
        from src.api.travel_services_routes import TransferResult

        result = TransferResult(
            destination="mauritius",
            transfers_adult=60.0,
            transfers_child=35.0,
            currency="EUR"
        )
        assert result.currency == "EUR"

    def test_transfer_result_hotel_name_optional(self):
        """TransferResult hotel_name should be optional."""
        from src.api.travel_services_routes import TransferResult

        result = TransferResult(
            destination="zanzibar",
            transfers_adult=50.0,
            transfers_child=30.0
        )
        assert result.hotel_name is None

    def test_transfer_result_with_hotel_name(self):
        """TransferResult should accept hotel_name."""
        from src.api.travel_services_routes import TransferResult

        result = TransferResult(
            destination="zanzibar",
            transfers_adult=50.0,
            transfers_child=30.0,
            hotel_name="Beach Resort & Spa"
        )
        assert result.hotel_name == "Beach Resort & Spa"


class TestTransferSearchResponseModel:
    """Tests for TransferSearchResponse model."""

    def test_transfer_search_response_success(self):
        """TransferSearchResponse should represent a successful search."""
        from src.api.travel_services_routes import TransferSearchResponse

        response = TransferSearchResponse(
            success=True,
            destination="zanzibar",
            total_transfers=3,
            transfers=[
                {"destination": "zanzibar", "transfers_adult": 50.0},
            ]
        )

        assert response.success is True
        assert response.destination == "zanzibar"
        assert response.total_transfers == 3
        assert len(response.transfers) == 1

    def test_transfer_search_response_error(self):
        """TransferSearchResponse should represent an error."""
        from src.api.travel_services_routes import TransferSearchResponse

        response = TransferSearchResponse(
            success=False,
            error="BigQuery not configured"
        )

        assert response.success is False
        assert response.error == "BigQuery not configured"
        assert response.total_transfers == 0
        assert response.transfers == []

    def test_transfer_search_response_defaults(self):
        """TransferSearchResponse should have sensible defaults."""
        from src.api.travel_services_routes import TransferSearchResponse

        response = TransferSearchResponse(success=True)

        assert response.destination is None
        assert response.total_transfers == 0
        assert response.transfers == []
        assert response.error is None


class TestActivitySearchResponseModel:
    """Tests for ActivitySearchResponse model."""

    def test_activity_search_response_success(self):
        """ActivitySearchResponse should represent a successful search."""
        from src.api.travel_services_routes import ActivitySearchResponse

        response = ActivitySearchResponse(
            success=True,
            destination="mauritius",
            total_activities=4,
            activities=[{"name": "Catamaran Cruise"}]
        )

        assert response.success is True
        assert response.destination == "mauritius"
        assert response.total_activities == 4

    def test_activity_search_response_error(self):
        """ActivitySearchResponse should represent an error."""
        from src.api.travel_services_routes import ActivitySearchResponse

        response = ActivitySearchResponse(
            success=False,
            error="Internal server error"
        )

        assert response.success is False
        assert response.error == "Internal server error"

    def test_activity_search_response_defaults(self):
        """ActivitySearchResponse should have sensible defaults."""
        from src.api.travel_services_routes import ActivitySearchResponse

        response = ActivitySearchResponse(success=True)

        assert response.destination is None
        assert response.total_activities == 0
        assert response.activities == []
        assert response.error is None


# ====================================================================
# NEW TESTS: get_client_config with default client
# ====================================================================

class TestGetClientConfigExtended:
    """Extended tests for get_client_config dependency."""

    def test_get_client_config_default_client_from_env(self):
        """Should use CLIENT_ID env var when no header provided."""
        from src.api.travel_services_routes import get_client_config
        import os

        with patch.dict(os.environ, {'CLIENT_ID': 'env-tenant'}, clear=False):
            with patch('src.api.travel_services_routes.get_config') as mock_get_config:
                mock_config = MagicMock()
                mock_get_config.return_value = mock_config

                result = get_client_config(x_client_id=None)

                mock_get_config.assert_called_once_with("env-tenant")

    def test_get_client_config_default_africastay(self):
        """Should fall back to 'africastay' when no header and no env var."""
        from src.api.travel_services_routes import get_client_config
        import os

        env = {k: v for k, v in os.environ.items() if k != 'CLIENT_ID'}
        with patch.dict(os.environ, env, clear=True):
            with patch('src.api.travel_services_routes.get_config') as mock_get_config:
                mock_config = MagicMock()
                mock_get_config.return_value = mock_config

                result = get_client_config(x_client_id=None)

                mock_get_config.assert_called_once_with("africastay")

    def test_get_client_config_returns_client_config_object(self):
        """Should return whatever get_config returns."""
        from src.api.travel_services_routes import get_client_config

        with patch('src.api.travel_services_routes.get_config') as mock_get_config:
            mock_config = MagicMock()
            mock_config.client_id = "test-tenant"
            mock_get_config.return_value = mock_config

            result = get_client_config(x_client_id="test-tenant")

            assert result is mock_config

    def test_get_client_config_error_message_contains_client_id(self):
        """Error message should contain the client_id for debugging."""
        from src.api.travel_services_routes import get_client_config
        from fastapi import HTTPException

        with patch('src.api.travel_services_routes.get_config', side_effect=Exception("Not found")):
            with pytest.raises(HTTPException) as exc_info:
                get_client_config(x_client_id="bad-tenant")

            assert "bad-tenant" in str(exc_info.value.detail)


# ====================================================================
# NEW TESTS: Flights with mocked BigQuery
# ====================================================================

class TestListFlightsMockedBigQuery:
    """Tests for list_flights with mocked BigQuery."""

    def test_list_flights_bigquery_not_configured(self, test_client):
        """list_flights should return error when BigQuery not configured."""
        with patch('src.tools.bigquery_tool.BigQueryTool', autospec=False) as MockBQ:
            mock_bq = MagicMock()
            mock_bq.client = None
            MockBQ.return_value = mock_bq

            response = test_client.get("/api/v1/travel/flights")
            data = response.json()

            assert response.status_code == 200
            assert data["success"] is False
            assert "BigQuery not configured" in data.get("error", "")

    def test_list_flights_returns_flight_data(self, test_client):
        """list_flights should return structured flight data from BigQuery."""
        from datetime import date as d

        mock_row = MagicMock()
        mock_row.destination = "zanzibar"
        mock_row.departure_date = d(2026, 6, 1)
        mock_row.return_date = d(2026, 6, 8)
        mock_row.price_per_person = 5500.0
        mock_row.airline = "SAA"

        with patch('src.tools.bigquery_tool.BigQueryTool', autospec=False) as MockBQ:
            mock_bq = MagicMock()
            mock_bq.client = MagicMock()
            mock_bq.db = MagicMock()
            mock_bq.db.flight_prices = "proj.dataset.flights"
            mock_bq.client.query.return_value.result.return_value = [mock_row]
            MockBQ.return_value = mock_bq

            response = test_client.get("/api/v1/travel/flights")
            data = response.json()

            assert response.status_code == 200
            assert data["success"] is True
            assert data["total_flights"] == 1
            assert data["flights"][0]["destination"] == "zanzibar"
            assert data["flights"][0]["price_per_person"] == 5500.0
            assert data["flights"][0]["airline"] == "SAA"
            assert data["flights"][0]["currency"] == "ZAR"

    def test_list_flights_empty_result(self, test_client):
        """list_flights should handle empty BigQuery results."""
        with patch('src.tools.bigquery_tool.BigQueryTool', autospec=False) as MockBQ:
            mock_bq = MagicMock()
            mock_bq.client = MagicMock()
            mock_bq.db = MagicMock()
            mock_bq.db.flight_prices = "proj.dataset.flights"
            mock_bq.client.query.return_value.result.return_value = []
            MockBQ.return_value = mock_bq

            response = test_client.get("/api/v1/travel/flights")
            data = response.json()

            assert response.status_code == 200
            assert data["success"] is True
            assert data["total_flights"] == 0
            assert data["flights"] == []

    def test_list_flights_bigquery_error(self, test_client):
        """list_flights should handle BigQuery errors gracefully."""
        with patch('src.tools.bigquery_tool.BigQueryTool', autospec=False) as MockBQ:
            mock_bq = MagicMock()
            mock_bq.client = MagicMock()
            mock_bq.db = MagicMock()
            mock_bq.db.flight_prices = "proj.dataset.flights"
            mock_bq.client.query.side_effect = Exception("BigQuery timeout")
            MockBQ.return_value = mock_bq

            response = test_client.get("/api/v1/travel/flights")
            data = response.json()

            assert response.status_code == 200
            assert data["success"] is False
            assert "BigQuery timeout" in data["error"]


# ====================================================================
# NEW TESTS: Search flights with mocked BigQuery
# ====================================================================

class TestSearchFlightsMockedBigQuery:
    """Tests for search_flights with mocked BigQuery."""

    def test_search_flights_returns_data(self, test_client):
        """search_flights should return flights for a given destination."""
        from datetime import date as d

        mock_row = MagicMock()
        mock_row.destination = "mauritius"
        mock_row.departure_date = d(2026, 7, 10)
        mock_row.return_date = d(2026, 7, 17)
        mock_row.price_per_person = 8200.0
        mock_row.airline = "Air Mauritius"

        with patch('src.tools.bigquery_tool.BigQueryTool', autospec=False) as MockBQ:
            mock_bq = MagicMock()
            mock_bq.client = MagicMock()
            mock_bq.db = MagicMock()
            mock_bq.db.flight_prices = "proj.dataset.flights"
            mock_bq.client.query.return_value.result.return_value = [mock_row]
            MockBQ.return_value = mock_bq

            response = test_client.get("/api/v1/travel/flights/search?destination=mauritius")
            data = response.json()

            assert response.status_code == 200
            assert data["success"] is True
            assert data["destination"] == "mauritius"
            assert data["total_flights"] == 1
            assert data["flights"][0]["airline"] == "Air Mauritius"

    def test_search_flights_bigquery_not_configured(self, test_client):
        """search_flights should return error when BigQuery not configured."""
        with patch('src.tools.bigquery_tool.BigQueryTool', autospec=False) as MockBQ:
            mock_bq = MagicMock()
            mock_bq.client = None
            MockBQ.return_value = mock_bq

            response = test_client.get("/api/v1/travel/flights/search?destination=zanzibar")
            data = response.json()

            assert response.status_code == 200
            assert data["success"] is False
            assert data["destination"] == "zanzibar"

    def test_search_flights_empty_results(self, test_client):
        """search_flights should handle no matching flights."""
        with patch('src.tools.bigquery_tool.BigQueryTool', autospec=False) as MockBQ:
            mock_bq = MagicMock()
            mock_bq.client = MagicMock()
            mock_bq.db = MagicMock()
            mock_bq.db.flight_prices = "proj.dataset.flights"
            mock_bq.client.query.return_value.result.return_value = []
            MockBQ.return_value = mock_bq

            response = test_client.get("/api/v1/travel/flights/search?destination=nowhere")
            data = response.json()

            assert data["success"] is True
            assert data["total_flights"] == 0

    def test_search_flights_handles_null_fields(self, test_client):
        """search_flights should handle null optional fields in rows."""
        mock_row = MagicMock()
        mock_row.destination = "zanzibar"
        mock_row.departure_date = None
        mock_row.return_date = None
        mock_row.price_per_person = None
        mock_row.airline = None

        with patch('src.tools.bigquery_tool.BigQueryTool', autospec=False) as MockBQ:
            mock_bq = MagicMock()
            mock_bq.client = MagicMock()
            mock_bq.db = MagicMock()
            mock_bq.db.flight_prices = "proj.dataset.flights"
            mock_bq.client.query.return_value.result.return_value = [mock_row]
            MockBQ.return_value = mock_bq

            response = test_client.get("/api/v1/travel/flights/search?destination=zanzibar")
            data = response.json()

            assert data["success"] is True
            assert data["flights"][0]["departure_date"] is None
            assert data["flights"][0]["price_per_person"] == 0


# ====================================================================
# NEW TESTS: Transfers with mocked BigQuery
# ====================================================================

class TestListTransfersMockedBigQuery:
    """Tests for list_transfers with mocked BigQuery."""

    def test_list_transfers_returns_data(self, test_client):
        """list_transfers should return transfer pricing data."""
        mock_row = MagicMock()
        mock_row.destination = "zanzibar"
        mock_row.hotel_name = "Zuri Zanzibar"
        mock_row.transfers_adult = 55.0
        mock_row.transfers_child = 30.0

        with patch('src.tools.bigquery_tool.BigQueryTool', autospec=False) as MockBQ:
            mock_bq = MagicMock()
            mock_bq.client = MagicMock()
            mock_bq.db = MagicMock()
            mock_bq.db.hotel_rates = "proj.dataset.hotel_rates"
            mock_bq.client.query.return_value.result.return_value = [mock_row]
            MockBQ.return_value = mock_bq

            response = test_client.get("/api/v1/travel/transfers")
            data = response.json()

            assert response.status_code == 200
            assert data["success"] is True
            assert data["total_transfers"] == 1
            assert data["transfers"][0]["destination"] == "zanzibar"
            assert data["transfers"][0]["hotel_name"] == "Zuri Zanzibar"
            assert data["transfers"][0]["transfers_adult"] == 55.0

    def test_list_transfers_bigquery_not_configured(self, test_client):
        """list_transfers should return error when BigQuery not configured."""
        with patch('src.tools.bigquery_tool.BigQueryTool', autospec=False) as MockBQ:
            mock_bq = MagicMock()
            mock_bq.client = None
            MockBQ.return_value = mock_bq

            response = test_client.get("/api/v1/travel/transfers")
            data = response.json()

            assert data["success"] is False
            assert "BigQuery not configured" in data["error"]

    def test_list_transfers_empty_results(self, test_client):
        """list_transfers should handle empty BigQuery results."""
        with patch('src.tools.bigquery_tool.BigQueryTool', autospec=False) as MockBQ:
            mock_bq = MagicMock()
            mock_bq.client = MagicMock()
            mock_bq.db = MagicMock()
            mock_bq.db.hotel_rates = "proj.dataset.hotel_rates"
            mock_bq.client.query.return_value.result.return_value = []
            MockBQ.return_value = mock_bq

            response = test_client.get("/api/v1/travel/transfers")
            data = response.json()

            assert data["success"] is True
            assert data["total_transfers"] == 0
            assert data["transfers"] == []

    def test_list_transfers_bigquery_error(self, test_client):
        """list_transfers should handle BigQuery errors gracefully."""
        with patch('src.tools.bigquery_tool.BigQueryTool', autospec=False) as MockBQ:
            mock_bq = MagicMock()
            mock_bq.client = MagicMock()
            mock_bq.db = MagicMock()
            mock_bq.db.hotel_rates = "proj.dataset.hotel_rates"
            mock_bq.client.query.side_effect = Exception("Query failed")
            MockBQ.return_value = mock_bq

            response = test_client.get("/api/v1/travel/transfers")
            data = response.json()

            assert data["success"] is False
            assert "Query failed" in data["error"]


# ====================================================================
# NEW TESTS: Search transfers with mocked BigQuery
# ====================================================================

class TestSearchTransfersMockedBigQuery:
    """Tests for search_transfers with mocked BigQuery."""

    def test_search_transfers_returns_data(self, test_client):
        """search_transfers should return transfers for destination."""
        mock_row = MagicMock()
        mock_row.destination = "mauritius"
        mock_row.hotel_name = "LUX* Belle Mare"
        mock_row.transfers_adult = 75.0
        mock_row.transfers_child = 45.0

        with patch('src.tools.bigquery_tool.BigQueryTool', autospec=False) as MockBQ:
            mock_bq = MagicMock()
            mock_bq.client = MagicMock()
            mock_bq.db = MagicMock()
            mock_bq.db.hotel_rates = "proj.dataset.hotel_rates"
            mock_bq.client.query.return_value.result.return_value = [mock_row]
            MockBQ.return_value = mock_bq

            response = test_client.get("/api/v1/travel/transfers/search?destination=mauritius")
            data = response.json()

            assert data["success"] is True
            assert data["destination"] == "mauritius"
            assert data["transfers"][0]["hotel_name"] == "LUX* Belle Mare"

    def test_search_transfers_with_null_child_price(self, test_client):
        """search_transfers should handle null transfers_child."""
        mock_row = MagicMock()
        mock_row.destination = "zanzibar"
        mock_row.hotel_name = "Test Hotel"
        mock_row.transfers_adult = 50.0
        mock_row.transfers_child = None

        with patch('src.tools.bigquery_tool.BigQueryTool', autospec=False) as MockBQ:
            mock_bq = MagicMock()
            mock_bq.client = MagicMock()
            mock_bq.db = MagicMock()
            mock_bq.db.hotel_rates = "proj.dataset.hotel_rates"
            mock_bq.client.query.return_value.result.return_value = [mock_row]
            MockBQ.return_value = mock_bq

            response = test_client.get("/api/v1/travel/transfers/search?destination=zanzibar")
            data = response.json()

            assert data["success"] is True
            assert data["transfers"][0]["transfers_child"] == 0


# ====================================================================
# NEW TESTS: Activities offset pagination / max_price
# ====================================================================

class TestActivitiesOffsetPagination:
    """Tests for activities endpoint with offset pagination via limit."""

    def test_activities_limit_1_returns_single(self, test_client):
        """Activities with limit=1 should return exactly 1 activity."""
        response = test_client.get("/api/v1/travel/activities?limit=1")
        data = response.json()

        assert data["success"] is True
        assert len(data["activities"]) == 1

    def test_activities_default_limit_returns_all(self, test_client):
        """Activities without limit should return all (up to default 50)."""
        from src.api.travel_services_routes import SAMPLE_ACTIVITIES

        response = test_client.get("/api/v1/travel/activities")
        data = response.json()

        assert data["success"] is True
        assert data["total_activities"] == len(SAMPLE_ACTIVITIES)

    def test_activities_limit_exceeds_data(self, test_client):
        """Activities with limit > total should return all available."""
        from src.api.travel_services_routes import SAMPLE_ACTIVITIES

        response = test_client.get("/api/v1/travel/activities?limit=200")
        data = response.json()

        assert data["success"] is True
        assert data["total_activities"] == len(SAMPLE_ACTIVITIES)

    def test_activities_combined_destination_and_limit(self, test_client):
        """Activities filtered by destination and limited should work together."""
        response = test_client.get("/api/v1/travel/activities?destination=zanzibar&limit=2")
        data = response.json()

        assert data["success"] is True
        assert len(data["activities"]) <= 2
        for activity in data["activities"]:
            assert activity["destination"] == "zanzibar"


class TestActivitiesSearchMaxPrice:
    """Tests for activities search with various filters."""

    def test_search_activities_category_filter(self, test_client):
        """search_activities should filter by category."""
        response = test_client.get("/api/v1/travel/activities/search?destination=zanzibar&category=Cultural")
        data = response.json()

        assert data["success"] is True
        for activity in data["activities"]:
            assert activity["category"].lower() == "cultural"

    def test_search_activities_query_in_description(self, test_client):
        """search_activities should search in description too."""
        response = test_client.get("/api/v1/travel/activities/search?destination=zanzibar&query=dolphin")
        data = response.json()

        assert data["success"] is True
        if data["activities"]:
            for activity in data["activities"]:
                name_desc = (activity["name"] + " " + (activity.get("description") or "")).lower()
                assert "dolphin" in name_desc

    def test_search_activities_no_match(self, test_client):
        """search_activities should return empty for non-matching query."""
        response = test_client.get("/api/v1/travel/activities/search?destination=zanzibar&query=xyznonexistent")
        data = response.json()

        assert data["success"] is True
        assert data["total_activities"] == 0
        assert data["activities"] == []

    def test_search_activities_case_insensitive_destination(self, test_client):
        """search_activities should be case-insensitive for destination."""
        response_lower = test_client.get("/api/v1/travel/activities/search?destination=zanzibar")
        response_upper = test_client.get("/api/v1/travel/activities/search?destination=ZANZIBAR")
        response_mixed = test_client.get("/api/v1/travel/activities/search?destination=Zanzibar")

        data_lower = response_lower.json()
        data_upper = response_upper.json()
        data_mixed = response_mixed.json()

        assert data_lower["total_activities"] == data_upper["total_activities"]
        assert data_lower["total_activities"] == data_mixed["total_activities"]


# ====================================================================
# NEW TESTS: SAMPLE_ACTIVITIES specific destination counts
# ====================================================================

class TestSampleActivitiesDestinationCounts:
    """Tests for SAMPLE_ACTIVITIES destination-specific counts."""

    def test_zanzibar_has_five_activities(self):
        """Zanzibar should have 5 activities in sample data."""
        from src.api.travel_services_routes import SAMPLE_ACTIVITIES

        zanzibar = [a for a in SAMPLE_ACTIVITIES if a["destination"] == "zanzibar"]
        assert len(zanzibar) == 5

    def test_mauritius_has_four_activities(self):
        """Mauritius should have 4 activities in sample data."""
        from src.api.travel_services_routes import SAMPLE_ACTIVITIES

        mauritius = [a for a in SAMPLE_ACTIVITIES if a["destination"] == "mauritius"]
        assert len(mauritius) == 4

    def test_maldives_has_three_activities(self):
        """Maldives should have 3 activities in sample data."""
        from src.api.travel_services_routes import SAMPLE_ACTIVITIES

        maldives = [a for a in SAMPLE_ACTIVITIES if a["destination"] == "maldives"]
        assert len(maldives) == 3

    def test_kenya_has_two_activities(self):
        """Kenya should have 2 activities in sample data."""
        from src.api.travel_services_routes import SAMPLE_ACTIVITIES

        kenya = [a for a in SAMPLE_ACTIVITIES if a["destination"] == "kenya"]
        assert len(kenya) == 2

    def test_victoria_falls_has_three_activities(self):
        """Victoria Falls should have 3 activities in sample data."""
        from src.api.travel_services_routes import SAMPLE_ACTIVITIES

        vf = [a for a in SAMPLE_ACTIVITIES if a["destination"] == "victoria-falls"]
        assert len(vf) == 3

    def test_total_sample_activities_count(self):
        """Total SAMPLE_ACTIVITIES count should be 17."""
        from src.api.travel_services_routes import SAMPLE_ACTIVITIES

        assert len(SAMPLE_ACTIVITIES) == 17

    def test_all_activity_ids_unique(self):
        """All activity_ids should be unique."""
        from src.api.travel_services_routes import SAMPLE_ACTIVITIES

        ids = [a["activity_id"] for a in SAMPLE_ACTIVITIES]
        assert len(ids) == len(set(ids))

    def test_bungee_jump_has_no_child_price(self):
        """Bungee Jump (ACT017) should have no child price."""
        from src.api.travel_services_routes import SAMPLE_ACTIVITIES

        bungee = next(a for a in SAMPLE_ACTIVITIES if a["activity_id"] == "ACT017")
        assert bungee["price_child"] is None

    def test_activities_all_have_currency(self):
        """All activities should have a currency field."""
        from src.api.travel_services_routes import SAMPLE_ACTIVITIES

        for activity in SAMPLE_ACTIVITIES:
            assert "currency" in activity
            assert activity["currency"] == "USD"

    def test_activities_categories_include_expected(self):
        """Activities should include expected categories."""
        from src.api.travel_services_routes import SAMPLE_ACTIVITIES

        categories = set(a.get("category") for a in SAMPLE_ACTIVITIES if a.get("category"))

        assert "Cultural" in categories
        assert "Water Sports" in categories
        assert "Nature" in categories
        assert "Safari" in categories


# ====================================================================
# NEW TESTS: FlightSearchResponse defaults
# ====================================================================

class TestFlightSearchResponseDefaults:
    """Tests for FlightSearchResponse model defaults."""

    def test_flight_search_response_defaults(self):
        """FlightSearchResponse should have sensible defaults."""
        from src.api.travel_services_routes import FlightSearchResponse

        response = FlightSearchResponse(success=True)

        assert response.destination is None
        assert response.total_flights == 0
        assert response.flights == []
        assert response.error is None

    def test_flight_search_response_with_multiple_flights(self):
        """FlightSearchResponse should handle multiple flights."""
        from src.api.travel_services_routes import FlightSearchResponse

        flights = [
            {"destination": "zanzibar", "price_per_person": 5000},
            {"destination": "zanzibar", "price_per_person": 5500},
            {"destination": "zanzibar", "price_per_person": 6000},
        ]
        response = FlightSearchResponse(
            success=True,
            destination="zanzibar",
            total_flights=3,
            flights=flights
        )

        assert response.total_flights == 3
        assert len(response.flights) == 3


# ====================================================================
# NEW TESTS: ActivityResult extended
# ====================================================================

class TestActivityResultExtended:
    """Extended tests for ActivityResult model."""

    def test_activity_result_all_optional_none_by_default(self):
        """All optional fields on ActivityResult should default to None."""
        from src.api.travel_services_routes import ActivityResult

        result = ActivityResult(
            activity_id="ACT999",
            name="Test Activity",
            destination="test",
            price_adult=10.0
        )

        assert result.description is None
        assert result.duration is None
        assert result.price_child is None
        assert result.category is None
        assert result.image_url is None

    def test_activity_result_currency_default(self):
        """ActivityResult currency should default to ZAR."""
        from src.api.travel_services_routes import ActivityResult

        result = ActivityResult(
            activity_id="ACT999",
            name="Test",
            destination="test",
            price_adult=10.0
        )
        assert result.currency == "ZAR"

    def test_activity_result_full_fields(self):
        """ActivityResult should accept all fields."""
        from src.api.travel_services_routes import ActivityResult

        result = ActivityResult(
            activity_id="ACT100",
            name="Full Activity",
            destination="zanzibar",
            description="A great activity",
            duration="Full Day",
            price_adult=100.0,
            price_child=50.0,
            currency="USD",
            category="Adventure",
            image_url="https://example.com/img.jpg"
        )

        assert result.activity_id == "ACT100"
        assert result.description == "A great activity"
        assert result.duration == "Full Day"
        assert result.price_child == 50.0
        assert result.currency == "USD"
        assert result.category == "Adventure"
        assert result.image_url == "https://example.com/img.jpg"
