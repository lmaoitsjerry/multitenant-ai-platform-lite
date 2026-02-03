"""
Rates Routes Unit Tests

Tests for the rates API endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import date
from fastapi.testclient import TestClient


# ==================== Fixtures ====================

@pytest.fixture
def test_client():
    """Create a basic TestClient."""
    from main import app
    return TestClient(app)


# ==================== Destinations Endpoint Tests ====================

class TestDestinationsEndpoint:
    """Tests for GET /api/v1/rates/destinations endpoint."""

    def test_destinations_returns_list(self, test_client):
        """GET /destinations should return list of destinations."""
        response = test_client.get("/api/v1/rates/destinations")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "destinations" in data
        assert isinstance(data["destinations"], list)
        assert data["count"] == len(data["destinations"])

    def test_destinations_have_required_fields(self, test_client):
        """Each destination should have code, name, country."""
        response = test_client.get("/api/v1/rates/destinations")
        data = response.json()

        for dest in data["destinations"]:
            assert "code" in dest
            assert "name" in dest
            assert "country" in dest

    def test_destinations_include_zanzibar(self, test_client):
        """Destinations should include Zanzibar."""
        response = test_client.get("/api/v1/rates/destinations")
        data = response.json()

        codes = [d["code"] for d in data["destinations"]]
        assert "zanzibar" in codes


# ==================== Health Endpoint Tests ====================

class TestRatesHealthEndpoint:
    """Tests for GET /api/v1/rates/health endpoint."""

    def test_health_returns_status(self, test_client):
        """GET /health should return health status."""
        with patch('src.api.rates_routes.get_travel_platform_rates_client') as mock_client:
            mock_instance = MagicMock()
            mock_instance.is_available = AsyncMock(return_value=True)
            mock_instance.get_status.return_value = {"initialized": True}
            mock_client.return_value = mock_instance

            response = test_client.get("/api/v1/rates/health")

            assert response.status_code == 200
            data = response.json()
            assert "success" in data
            assert "available" in data

    def test_health_handles_exception(self, test_client):
        """GET /health should handle exceptions gracefully."""
        with patch('src.api.rates_routes.get_travel_platform_rates_client') as mock_client:
            mock_client.side_effect = Exception("Connection failed")

            response = test_client.get("/api/v1/rates/health")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert data["available"] is False


# ==================== Hotel Search Endpoint Tests ====================

class TestHotelSearchEndpoint:
    """Tests for POST /api/v1/rates/hotels/search endpoint."""

    def test_search_requires_body(self, test_client):
        """POST /hotels/search without body should return 422."""
        response = test_client.post("/api/v1/rates/hotels/search")

        assert response.status_code == 422

    def test_search_validates_dates(self, test_client):
        """POST /hotels/search should validate check_out > check_in."""
        response = test_client.post(
            "/api/v1/rates/hotels/search",
            json={
                "destination": "zanzibar",
                "check_in": "2026-03-20",
                "check_out": "2026-03-15",  # Before check_in
                "adults": 2
            }
        )

        assert response.status_code == 422

    def test_search_with_valid_request(self, test_client):
        """POST /hotels/search should process valid request."""
        with patch('src.api.rates_routes.get_travel_platform_rates_client') as mock_client:
            mock_instance = MagicMock()
            mock_instance.search_hotels = AsyncMock(return_value={
                "success": True,
                "destination": "zanzibar",
                "check_in": "2026-03-15",
                "check_out": "2026-03-20",
                "nights": 5,
                "total_hotels": 10,
                "hotels": [{"hotel_name": "Test Hotel"}],
                "search_time_seconds": 2.5
            })
            mock_client.return_value = mock_instance

            response = test_client.post(
                "/api/v1/rates/hotels/search",
                json={
                    "destination": "zanzibar",
                    "check_in": "2026-03-15",
                    "check_out": "2026-03-20",
                    "adults": 2
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_search_handles_exception(self, test_client):
        """POST /hotels/search should handle exceptions."""
        with patch('src.api.rates_routes.get_travel_platform_rates_client') as mock_client:
            mock_instance = MagicMock()
            mock_instance.search_hotels = AsyncMock(side_effect=Exception("Search failed"))
            mock_client.return_value = mock_instance

            response = test_client.post(
                "/api/v1/rates/hotels/search",
                json={
                    "destination": "zanzibar",
                    "check_in": "2026-03-15",
                    "check_out": "2026-03-20",
                    "adults": 2
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "error" in data


# ==================== Hotel Search By Names Endpoint Tests ====================

class TestHotelSearchByNamesEndpoint:
    """Tests for POST /api/v1/rates/hotels/search-by-names endpoint."""

    def test_search_by_names_requires_body(self, test_client):
        """POST /hotels/search-by-names without body should return 422."""
        response = test_client.post("/api/v1/rates/hotels/search-by-names")

        assert response.status_code == 422

    def test_search_by_names_requires_hotel_names(self, test_client):
        """POST /hotels/search-by-names requires hotel_names."""
        response = test_client.post(
            "/api/v1/rates/hotels/search-by-names",
            json={
                "destination": "zanzibar",
                "check_in": "2026-03-15",
                "check_out": "2026-03-20"
            }
        )

        assert response.status_code == 422

    def test_search_by_names_with_valid_request(self, test_client):
        """POST /hotels/search-by-names should process valid request."""
        with patch('src.api.rates_routes.get_travel_platform_rates_client') as mock_client:
            mock_instance = MagicMock()
            mock_instance.search_hotels_by_names = AsyncMock(return_value={
                "success": True,
                "hotels": [{"hotel_name": "Specific Hotel"}],
                "unmatched_hotels": []
            })
            mock_client.return_value = mock_instance

            response = test_client.post(
                "/api/v1/rates/hotels/search-by-names",
                json={
                    "destination": "zanzibar",
                    "hotel_names": ["Specific Hotel"],
                    "check_in": "2026-03-15",
                    "check_out": "2026-03-20"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_search_by_names_handles_exception(self, test_client):
        """POST /hotels/search-by-names should handle exceptions."""
        with patch('src.api.rates_routes.get_travel_platform_rates_client') as mock_client:
            mock_instance = MagicMock()
            mock_instance.search_hotels_by_names = AsyncMock(side_effect=Exception("Lookup failed"))
            mock_client.return_value = mock_instance

            response = test_client.post(
                "/api/v1/rates/hotels/search-by-names",
                json={
                    "destination": "zanzibar",
                    "hotel_names": ["Test Hotel"],
                    "check_in": "2026-03-15",
                    "check_out": "2026-03-20"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "error" in data


# ==================== Pydantic Model Tests ====================

class TestHotelSearchRequest:
    """Tests for HotelSearchRequest model."""

    def test_destination_normalization(self):
        """Destination should be normalized to lowercase."""
        from src.api.rates_routes import HotelSearchRequest

        request = HotelSearchRequest(
            destination="  ZANZIBAR  ",
            check_in=date(2026, 3, 15),
            check_out=date(2026, 3, 20)
        )

        assert request.destination == "zanzibar"

    def test_default_adults(self):
        """Adults should default to 2."""
        from src.api.rates_routes import HotelSearchRequest

        request = HotelSearchRequest(
            destination="zanzibar",
            check_in=date(2026, 3, 15),
            check_out=date(2026, 3, 20)
        )

        assert request.adults == 2

    def test_default_children_ages(self):
        """Children ages should default to empty list."""
        from src.api.rates_routes import HotelSearchRequest

        request = HotelSearchRequest(
            destination="zanzibar",
            check_in=date(2026, 3, 15),
            check_out=date(2026, 3, 20)
        )

        assert request.children_ages == []

    def test_default_max_hotels(self):
        """Max hotels should default to 50."""
        from src.api.rates_routes import HotelSearchRequest

        request = HotelSearchRequest(
            destination="zanzibar",
            check_in=date(2026, 3, 15),
            check_out=date(2026, 3, 20)
        )

        assert request.max_hotels == 50


class TestHotelSearchResponse:
    """Tests for HotelSearchResponse model."""

    def test_success_response(self):
        """Should create success response."""
        from src.api.rates_routes import HotelSearchResponse

        response = HotelSearchResponse(
            success=True,
            destination="zanzibar",
            total_hotels=5,
            hotels=[{"name": "Test"}]
        )

        assert response.success is True
        assert response.total_hotels == 5

    def test_error_response(self):
        """Should create error response."""
        from src.api.rates_routes import HotelSearchResponse

        response = HotelSearchResponse(
            success=False,
            total_hotels=0,
            hotels=[],
            error="Search failed"
        )

        assert response.success is False
        assert response.error == "Search failed"
