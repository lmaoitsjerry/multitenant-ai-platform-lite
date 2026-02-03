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
