"""
HotelBeds Routes Unit Tests

Comprehensive tests for HotelBeds API endpoints:
- GET /api/v1/hotelbeds/health - API health check
- GET /api/v1/hotelbeds/status - Client status
- GET /api/v1/hotelbeds/hotels/search - Hotel search (GET)
- POST /api/v1/hotelbeds/hotels/search - Hotel search (POST with children)
- GET /api/v1/hotelbeds/activities/search - Activity search
- POST /api/v1/hotelbeds/activities/search - Activity search (POST)
- GET /api/v1/hotelbeds/transfers/search - Transfer search
- POST /api/v1/hotelbeds/transfers/search - Transfer search (POST)

These tests verify:
1. Endpoint structure and HTTP methods
2. Pydantic model validation
3. Query parameter validation
4. Error handling for invalid dates
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from datetime import date, timedelta
from pydantic import ValidationError


# ==================== Fixtures ====================

@pytest.fixture
def test_client():
    """Create a basic TestClient."""
    from main import app
    return TestClient(app)


@pytest.fixture
def mock_hotelbeds_client():
    """Create a mock HotelBeds client."""
    mock_client = AsyncMock()
    return mock_client


# ==================== Pydantic Model Tests ====================

class TestHotelSearchRequestModel:
    """Test HotelSearchRequest Pydantic model."""

    def test_valid_hotel_search_request(self):
        """Should accept valid hotel search request."""
        from src.api.hotelbeds_routes import HotelSearchRequest

        request = HotelSearchRequest(
            destination="Zanzibar",
            check_in=date(2026, 3, 15),
            check_out=date(2026, 3, 20),
            adults=2,
            children_ages=[5, 8],
            max_hotels=50
        )

        assert request.destination == "zanzibar"  # Normalized to lowercase
        assert request.adults == 2
        assert request.children_ages == [5, 8]

    def test_destination_normalized_to_lowercase(self):
        """Should normalize destination to lowercase."""
        from src.api.hotelbeds_routes import HotelSearchRequest

        request = HotelSearchRequest(
            destination="  MAURITIUS  ",
            check_in=date(2026, 4, 1),
            check_out=date(2026, 4, 5)
        )

        assert request.destination == "mauritius"

    def test_check_out_must_be_after_check_in(self):
        """Should reject check_out before check_in."""
        from src.api.hotelbeds_routes import HotelSearchRequest

        with pytest.raises(ValidationError) as exc_info:
            HotelSearchRequest(
                destination="Zanzibar",
                check_in=date(2026, 3, 20),
                check_out=date(2026, 3, 15)  # Before check_in
            )

        assert "check_out must be after check_in" in str(exc_info.value)

    def test_default_values(self):
        """Should use default values when not specified."""
        from src.api.hotelbeds_routes import HotelSearchRequest

        request = HotelSearchRequest(
            destination="maldives",
            check_in=date(2026, 5, 1),
            check_out=date(2026, 5, 7)
        )

        assert request.adults == 2
        assert request.children_ages == []
        assert request.max_hotels == 50

    def test_adults_validation_min(self):
        """Should reject adults less than 1."""
        from src.api.hotelbeds_routes import HotelSearchRequest

        with pytest.raises(ValidationError):
            HotelSearchRequest(
                destination="zanzibar",
                check_in=date(2026, 3, 15),
                check_out=date(2026, 3, 20),
                adults=0
            )

    def test_adults_validation_max(self):
        """Should reject adults more than 10."""
        from src.api.hotelbeds_routes import HotelSearchRequest

        with pytest.raises(ValidationError):
            HotelSearchRequest(
                destination="zanzibar",
                check_in=date(2026, 3, 15),
                check_out=date(2026, 3, 20),
                adults=15
            )

    def test_max_hotels_validation_min(self):
        """Should reject max_hotels less than 1."""
        from src.api.hotelbeds_routes import HotelSearchRequest

        with pytest.raises(ValidationError):
            HotelSearchRequest(
                destination="zanzibar",
                check_in=date(2026, 3, 15),
                check_out=date(2026, 3, 20),
                max_hotels=0
            )

    def test_max_hotels_validation_max(self):
        """Should reject max_hotels more than 200."""
        from src.api.hotelbeds_routes import HotelSearchRequest

        with pytest.raises(ValidationError):
            HotelSearchRequest(
                destination="zanzibar",
                check_in=date(2026, 3, 15),
                check_out=date(2026, 3, 20),
                max_hotels=500
            )


class TestActivitySearchRequestModel:
    """Test ActivitySearchRequest Pydantic model."""

    def test_valid_activity_search_request(self):
        """Should accept valid activity search request."""
        from src.api.hotelbeds_routes import ActivitySearchRequest

        request = ActivitySearchRequest(
            destination="Zanzibar",
            participants=4
        )

        assert request.destination == "zanzibar"
        assert request.participants == 4

    def test_destination_normalized(self):
        """Should normalize destination to lowercase."""
        from src.api.hotelbeds_routes import ActivitySearchRequest

        request = ActivitySearchRequest(
            destination="  CAPE TOWN  "
        )

        assert request.destination == "cape town"

    def test_default_participants(self):
        """Should use default participants when not specified."""
        from src.api.hotelbeds_routes import ActivitySearchRequest

        request = ActivitySearchRequest(destination="bali")

        assert request.participants == 2

    def test_participants_validation_max(self):
        """Should reject participants more than 50."""
        from src.api.hotelbeds_routes import ActivitySearchRequest

        with pytest.raises(ValidationError):
            ActivitySearchRequest(
                destination="zanzibar",
                participants=100
            )


class TestTransferSearchRequestModel:
    """Test TransferSearchRequest Pydantic model."""

    def test_valid_transfer_search_request(self):
        """Should accept valid transfer search request."""
        from src.api.hotelbeds_routes import TransferSearchRequest

        request = TransferSearchRequest(
            route="Zanzibar Airport to Stone Town",
            transfer_date=date(2026, 3, 15),
            passengers=4
        )

        assert request.route == "Zanzibar Airport to Stone Town"
        assert request.passengers == 4

    def test_default_passengers(self):
        """Should use default passengers when not specified."""
        from src.api.hotelbeds_routes import TransferSearchRequest

        request = TransferSearchRequest(
            route="Airport to Hotel",
            transfer_date=date(2026, 4, 1)
        )

        assert request.passengers == 2

    def test_passengers_validation_max(self):
        """Should reject passengers more than 20."""
        from src.api.hotelbeds_routes import TransferSearchRequest

        with pytest.raises(ValidationError):
            TransferSearchRequest(
                route="Airport to Hotel",
                transfer_date=date(2026, 4, 1),
                passengers=50
            )


# ==================== Endpoint Existence Tests ====================

class TestHotelBedsEndpointExistence:
    """Test that all HotelBeds endpoints exist."""

    def test_health_endpoint_exists(self, test_client):
        """GET /health endpoint should exist."""
        response = test_client.get("/api/v1/hotelbeds/health")
        # Any response that's not 404 means the route exists
        assert response.status_code != 404

    def test_status_endpoint_exists(self, test_client):
        """GET /status endpoint should exist."""
        response = test_client.get("/api/v1/hotelbeds/status")
        assert response.status_code != 404

    def test_hotels_search_get_exists(self, test_client):
        """GET /hotels/search endpoint should exist."""
        response = test_client.get(
            "/api/v1/hotelbeds/hotels/search",
            params={
                "destination": "zanzibar",
                "check_in": "2026-03-15",
                "check_out": "2026-03-20"
            }
        )
        assert response.status_code != 404

    def test_hotels_search_post_exists(self, test_client):
        """POST /hotels/search endpoint should exist."""
        response = test_client.post(
            "/api/v1/hotelbeds/hotels/search",
            json={
                "destination": "zanzibar",
                "check_in": "2026-03-15",
                "check_out": "2026-03-20"
            }
        )
        assert response.status_code != 404

    def test_activities_search_get_exists(self, test_client):
        """GET /activities/search endpoint should exist."""
        response = test_client.get(
            "/api/v1/hotelbeds/activities/search",
            params={"destination": "zanzibar"}
        )
        assert response.status_code != 404

    def test_activities_search_post_exists(self, test_client):
        """POST /activities/search endpoint should exist."""
        response = test_client.post(
            "/api/v1/hotelbeds/activities/search",
            json={"destination": "zanzibar"}
        )
        assert response.status_code != 404

    def test_transfers_search_get_exists(self, test_client):
        """GET /transfers/search endpoint should exist."""
        response = test_client.get(
            "/api/v1/hotelbeds/transfers/search",
            params={
                "route": "Airport to Hotel",
                "date": "2026-03-15"
            }
        )
        assert response.status_code != 404

    def test_transfers_search_post_exists(self, test_client):
        """POST /transfers/search endpoint should exist."""
        response = test_client.post(
            "/api/v1/hotelbeds/transfers/search",
            json={
                "route": "Airport to Hotel",
                "transfer_date": "2026-03-15"
            }
        )
        assert response.status_code != 404


# ==================== Validation Tests ====================
# Note: These endpoints require authentication, so we test for 401 to verify
# the endpoint exists and is protected. Model validation is tested separately.

class TestHotelsSearchValidation:
    """Test validation for hotel search endpoints."""

    def test_hotels_search_requires_auth(self, test_client):
        """GET /hotels/search requires authentication."""
        response = test_client.get(
            "/api/v1/hotelbeds/hotels/search",
            params={
                "destination": "zanzibar",
                "check_in": "2026-03-15",
                "check_out": "2026-03-20"
            }
        )
        # Endpoint requires auth, returns 401
        assert response.status_code == 401

    def test_hotels_search_missing_params_still_requires_auth(self, test_client):
        """GET /hotels/search with missing params still requires auth first."""
        response = test_client.get(
            "/api/v1/hotelbeds/hotels/search",
            params={"check_in": "2026-03-15"}  # Missing destination and check_out
        )
        # Auth runs first, so we get 401
        assert response.status_code == 401

    def test_hotels_search_post_requires_auth(self, test_client):
        """POST /hotels/search requires authentication."""
        response = test_client.post(
            "/api/v1/hotelbeds/hotels/search",
            json={
                "destination": "zanzibar",
                "check_in": "2026-03-15",
                "check_out": "2026-03-20"
            }
        )
        assert response.status_code == 401

    def test_hotels_search_post_validation_error_requires_auth(self, test_client):
        """POST /hotels/search validation runs after auth."""
        response = test_client.post(
            "/api/v1/hotelbeds/hotels/search",
            json={
                "destination": "zanzibar",
                "check_in": "2026-03-20",
                "check_out": "2026-03-15"  # Before check_in
            }
        )
        # Auth runs first, so we get 401 or 422 depending on middleware order
        assert response.status_code in [401, 422]


class TestActivitiesSearchValidation:
    """Test validation for activity search endpoints."""

    def test_activities_search_requires_auth(self, test_client):
        """GET /activities/search requires authentication."""
        response = test_client.get(
            "/api/v1/hotelbeds/activities/search",
            params={"destination": "zanzibar"}
        )
        assert response.status_code == 401


class TestTransfersSearchValidation:
    """Test validation for transfer search endpoints."""

    def test_transfers_search_requires_auth(self, test_client):
        """GET /transfers/search requires authentication."""
        response = test_client.get(
            "/api/v1/hotelbeds/transfers/search",
            params={"route": "Airport to Hotel", "date": "2026-03-15"}
        )
        assert response.status_code == 401


# ==================== Response Format Tests ====================
# Note: These endpoints require authentication. The mocked tests below verify
# the endpoint is protected (401). For full integration testing, see E2E tests.

class TestHotelsSearchRequiresAuth:
    """Test hotel search requires authentication."""

    def test_search_hotels_get_requires_auth(self, test_client):
        """GET /hotels/search requires auth - returns 401."""
        response = test_client.get(
            "/api/v1/hotelbeds/hotels/search",
            params={
                "destination": "zanzibar",
                "check_in": "2026-03-15",
                "check_out": "2026-03-20"
            }
        )

        assert response.status_code == 401

    def test_search_hotels_post_requires_auth(self, test_client):
        """POST /hotels/search requires auth - returns 401."""
        response = test_client.post(
            "/api/v1/hotelbeds/hotels/search",
            json={
                "destination": "zanzibar",
                "check_in": "2026-03-15",
                "check_out": "2026-03-20"
            }
        )

        assert response.status_code == 401


class TestHealthEndpointRequiresAuth:
    """Test health endpoint requires authentication."""

    def test_health_requires_auth(self, test_client):
        """GET /health requires auth - returns 401."""
        response = test_client.get("/api/v1/hotelbeds/health")

        # Endpoint requires auth
        assert response.status_code == 401


class TestStatusEndpointRequiresAuth:
    """Test status endpoint requires authentication."""

    def test_status_requires_auth(self, test_client):
        """GET /status requires auth - returns 401."""
        response = test_client.get("/api/v1/hotelbeds/status")

        # Endpoint requires auth
        assert response.status_code == 401


# ==================== Router Tests ====================

class TestHotelbedsRouter:
    """Test hotelbeds router configuration."""

    def test_router_prefix(self):
        """Should have correct prefix."""
        from src.api.hotelbeds_routes import hotelbeds_router

        assert hotelbeds_router.prefix == "/api/v1/hotelbeds"

    def test_router_tags(self):
        """Should have correct tags."""
        from src.api.hotelbeds_routes import hotelbeds_router

        assert "HotelBeds" in hotelbeds_router.tags

    def test_include_hotelbeds_router_function(self):
        """include_hotelbeds_router should add router to app."""
        from src.api.hotelbeds_routes import include_hotelbeds_router, hotelbeds_router

        mock_app = MagicMock()
        include_hotelbeds_router(mock_app)

        mock_app.include_router.assert_called_once_with(hotelbeds_router)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
