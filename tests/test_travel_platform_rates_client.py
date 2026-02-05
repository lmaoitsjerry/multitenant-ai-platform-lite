"""
Travel Platform Rates Client Tests

Tests for the TravelPlatformRatesClient:
- Client initialization
- Singleton pattern
- Hotel search functionality
- Circuit breaker integration
- Error handling (timeout, connection errors, HTTP errors)
- Retry logic
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import date, timedelta
import httpx


# ==================== Fixtures ====================

@pytest.fixture(autouse=True)
def reset_client():
    """Reset the singleton client before each test."""
    from src.services.travel_platform_rates_client import reset_travel_platform_rates_client
    reset_travel_platform_rates_client()
    yield
    reset_travel_platform_rates_client()


@pytest.fixture
def mock_circuit_breaker():
    """Create a mock circuit breaker that allows execution."""
    with patch('src.services.travel_platform_rates_client.rates_circuit') as mock_cb:
        mock_cb.can_execute.return_value = True
        mock_cb.record_success = MagicMock()
        mock_cb.record_failure = MagicMock()
        yield mock_cb


@pytest.fixture
def sample_search_response():
    """Sample successful search response."""
    return {
        "destination": "zanzibar",
        "check_in": "2025-03-01",
        "check_out": "2025-03-05",
        "nights": 4,
        "total_hotels": 2,
        "hotels": [
            {
                "name": "Beach Resort",
                "star_rating": 5,
                "total_price": 1500.00,
                "currency": "USD"
            },
            {
                "name": "Ocean View Hotel",
                "star_rating": 4,
                "total_price": 1200.00,
                "currency": "USD"
            }
        ],
        "search_time_seconds": 3.5
    }


# ==================== Initialization Tests ====================

class TestClientInitialization:
    """Tests for client initialization."""

    def test_client_initializes_with_defaults(self):
        """Client should initialize with default values."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        with patch.dict('os.environ', {}, clear=True):
            client = TravelPlatformRatesClient()

            assert client._initialized is True
            assert "zorah-travel-platform" in client.base_url
            assert client.timeout == 120.0

    def test_client_uses_env_vars(self):
        """Client should use environment variables when set."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        with patch.dict('os.environ', {
            'RATES_ENGINE_URL': 'https://custom.api.com',
            'RATES_ENGINE_TIMEOUT': '60'
        }):
            # Reset singleton
            TravelPlatformRatesClient._instance = None
            client = TravelPlatformRatesClient()

            assert client.base_url == 'https://custom.api.com'
            assert client.timeout == 60.0


class TestSingletonPattern:
    """Tests for singleton pattern."""

    def test_singleton_returns_same_instance(self):
        """Multiple instantiations should return the same instance."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client1 = TravelPlatformRatesClient()
        client2 = TravelPlatformRatesClient()

        assert client1 is client2

    def test_get_client_returns_singleton(self):
        """get_travel_platform_rates_client should return singleton."""
        from src.services.travel_platform_rates_client import (
            get_travel_platform_rates_client,
            TravelPlatformRatesClient
        )

        client1 = get_travel_platform_rates_client()
        client2 = get_travel_platform_rates_client()
        client3 = TravelPlatformRatesClient()

        assert client1 is client2
        assert client1 is client3

    def test_reset_clears_singleton(self):
        """reset_travel_platform_rates_client should clear the singleton."""
        from src.services.travel_platform_rates_client import (
            get_travel_platform_rates_client,
            reset_travel_platform_rates_client
        )

        client1 = get_travel_platform_rates_client()
        reset_travel_platform_rates_client()
        client2 = get_travel_platform_rates_client()

        assert client1 is not client2


# ==================== Health Check Tests ====================

class TestIsAvailable:
    """Tests for the is_available method."""

    @pytest.mark.asyncio
    async def test_is_available_healthy(self):
        """Should return True when health check succeeds."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy", "providers": {}}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await client.is_available()

            assert result is True

    @pytest.mark.asyncio
    async def test_is_available_unhealthy(self):
        """Should return False when service is unhealthy."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "unhealthy"}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await client.is_available()

            assert result is False

    @pytest.mark.asyncio
    async def test_is_available_on_error(self):
        """Should return False on connection error."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("Connection refused")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await client.is_available()

            assert result is False
            assert client._last_error is not None

    @pytest.mark.asyncio
    async def test_is_available_on_non_200(self):
        """Should return False on non-200 response."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        mock_response = MagicMock()
        mock_response.status_code = 503

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await client.is_available()

            assert result is False


# ==================== Hotel Search Tests ====================

class TestSearchHotels:
    """Tests for the search_hotels method."""

    @pytest.mark.asyncio
    async def test_search_hotels_success(self, mock_circuit_breaker, sample_search_response):
        """Should return hotels on successful search."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_search_response
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await client.search_hotels(
                destination="zanzibar",
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 5)
            )

            assert result["success"] is True
            assert result["total_hotels"] == 2
            assert len(result["hotels"]) == 2
            mock_circuit_breaker.record_success.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_hotels_circuit_breaker_open(self):
        """Should return error when circuit breaker is open."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        with patch('src.services.travel_platform_rates_client.rates_circuit') as mock_cb:
            mock_cb.can_execute.return_value = False

            result = await client.search_hotels(
                destination="zanzibar",
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 5)
            )

            assert result["success"] is False
            assert "Circuit breaker" in result["error"]

    @pytest.mark.asyncio
    async def test_search_hotels_timeout(self, mock_circuit_breaker):
        """Should handle timeout errors."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("Timeout")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await client.search_hotels(
                destination="zanzibar",
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 5)
            )

            assert result["success"] is False
            assert "timed out" in result["error"]
            mock_circuit_breaker.record_failure.assert_called()

    @pytest.mark.asyncio
    async def test_search_hotels_connection_error(self, mock_circuit_breaker):
        """Should handle connection errors."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await client.search_hotels(
                destination="zanzibar",
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 5)
            )

            assert result["success"] is False
            assert "Connection" in result["error"]
            mock_circuit_breaker.record_failure.assert_called()

    @pytest.mark.asyncio
    async def test_search_hotels_http_error(self, mock_circuit_breaker):
        """Should handle HTTP errors."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.HTTPStatusError(
                "Server Error",
                request=mock_request,
                response=mock_response
            )
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await client.search_hotels(
                destination="zanzibar",
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 5)
            )

            assert result["success"] is False
            assert "HTTP 500" in result["error"]
            mock_circuit_breaker.record_failure.assert_called()

    @pytest.mark.asyncio
    async def test_search_hotels_with_children(self, mock_circuit_breaker, sample_search_response):
        """Should pass children ages in request."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        mock_response = MagicMock()
        mock_response.json.return_value = sample_search_response
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await client.search_hotels(
                destination="zanzibar",
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 5),
                adults=2,
                children_ages=[5, 8],
                max_hotels=20
            )

            assert result["success"] is True
            # Verify the payload included children
            call_args = mock_client.post.call_args
            payload = call_args.kwargs.get('json') or call_args[1].get('json')
            assert payload["rooms"][0]["children_ages"] == [5, 8]


# ==================== Search by Names Tests ====================

class TestSearchHotelsByNames:
    """Tests for the search_hotels_by_names method."""

    @pytest.mark.asyncio
    async def test_search_by_names_success(self):
        """Should return matched hotels on success."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "matched_hotels": [{"name": "Beach Resort", "price": 1500}],
            "unmatched": []
        }
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await client.search_hotels_by_names(
                destination="zanzibar",
                hotel_names=["Beach Resort"],
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 5)
            )

            assert result["success"] is True
            assert "matched_hotels" in result

    @pytest.mark.asyncio
    async def test_search_by_names_timeout(self):
        """Should handle timeout errors."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("Timeout")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await client.search_hotels_by_names(
                destination="zanzibar",
                hotel_names=["Beach Resort"],
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 5)
            )

            assert result["success"] is False
            assert "timed out" in result["error"]

    @pytest.mark.asyncio
    async def test_search_by_names_generic_error(self):
        """Should handle generic errors."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = Exception("Unexpected error")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await client.search_hotels_by_names(
                destination="zanzibar",
                hotel_names=["Beach Resort"],
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 5)
            )

            assert result["success"] is False
            assert "Unexpected error" in result["error"]


# ==================== Status Tests ====================

class TestGetStatus:
    """Tests for the get_status method."""

    def test_get_status_returns_info(self):
        """Should return client status information."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()
        client._last_error = "Test error"

        status = client.get_status()

        assert status["initialized"] is True
        assert "base_url" in status
        assert "timeout" in status
        assert status["last_error"] == "Test error"


# ==================== Error Response Tests ====================

class TestErrorResponse:
    """Tests for the _error_response helper."""

    def test_error_response_structure(self):
        """Error response should have correct structure."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        response = client._error_response("Test error")

        assert response["success"] is False
        assert response["hotels"] == []
        assert response["total_hotels"] == 0
        assert response["error"] == "Test error"


# ==================== NEW TESTS: Date Handling ====================

class TestDateHandling:
    """Tests for date serialization and night calculation."""

    @pytest.mark.asyncio
    async def test_dates_serialized_as_iso_format(self, mock_circuit_breaker, sample_search_response):
        """Check-in and check-out dates should be serialized in ISO format."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        mock_response = MagicMock()
        mock_response.json.return_value = sample_search_response
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await client.search_hotels(
                destination="mauritius",
                check_in=date(2025, 6, 15),
                check_out=date(2025, 6, 20)
            )

            call_args = mock_client.post.call_args
            payload = call_args.kwargs.get('json') or call_args[1].get('json')
            assert payload["check_in"] == "2025-06-15"
            assert payload["check_out"] == "2025-06-20"

    @pytest.mark.asyncio
    async def test_nights_calculated_from_response(self, mock_circuit_breaker):
        """Nights should come from response or be calculated from dates."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        response_data = {
            "destination": "zanzibar",
            "check_in": "2025-03-01",
            "check_out": "2025-03-08",
            "nights": 7,
            "total_hotels": 1,
            "hotels": [{"name": "Test Hotel"}],
            "search_time_seconds": 2.0
        }

        mock_response = MagicMock()
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await client.search_hotels(
                destination="zanzibar",
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 8)
            )

            assert result["nights"] == 7

    @pytest.mark.asyncio
    async def test_nights_fallback_calculates_from_dates(self, mock_circuit_breaker):
        """When response omits 'nights', should calculate from check_in/check_out."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        # Response without 'nights' field
        response_data = {
            "destination": "zanzibar",
            "total_hotels": 0,
            "hotels": [],
            "search_time_seconds": 1.0
        }

        mock_response = MagicMock()
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await client.search_hotels(
                destination="zanzibar",
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 4)
            )

            assert result["nights"] == 3


# ==================== NEW TESTS: Destination Handling ====================

class TestDestinationHandling:
    """Tests for destination name normalization."""

    @pytest.mark.asyncio
    async def test_destination_lowercased_in_payload(self, mock_circuit_breaker, sample_search_response):
        """Destination should be lowercased in the API payload."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        mock_response = MagicMock()
        mock_response.json.return_value = sample_search_response
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await client.search_hotels(
                destination="MAURITIUS",
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 5)
            )

            call_args = mock_client.post.call_args
            payload = call_args.kwargs.get('json') or call_args[1].get('json')
            assert payload["destination"] == "mauritius"

    @pytest.mark.asyncio
    async def test_destination_mixed_case_lowercased(self, mock_circuit_breaker, sample_search_response):
        """Mixed case destination should be lowercased."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        mock_response = MagicMock()
        mock_response.json.return_value = sample_search_response
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await client.search_hotels(
                destination="Zanzibar",
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 5)
            )

            call_args = mock_client.post.call_args
            payload = call_args.kwargs.get('json') or call_args[1].get('json')
            assert payload["destination"] == "zanzibar"


# ==================== NEW TESTS: Hotel Search Response Structure ====================

class TestSearchResponseStructure:
    """Tests for the structure of successful search responses."""

    @pytest.mark.asyncio
    async def test_success_response_has_all_required_fields(self, mock_circuit_breaker, sample_search_response):
        """Successful response should have all required fields."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        mock_response = MagicMock()
        mock_response.json.return_value = sample_search_response
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await client.search_hotels(
                destination="zanzibar",
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 5)
            )

            assert "success" in result
            assert "destination" in result
            assert "check_in" in result
            assert "check_out" in result
            assert "nights" in result
            assert "total_hotels" in result
            assert "hotels" in result
            assert "search_time_seconds" in result

    @pytest.mark.asyncio
    async def test_search_time_preserved(self, mock_circuit_breaker, sample_search_response):
        """search_time_seconds should be preserved from response."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        mock_response = MagicMock()
        mock_response.json.return_value = sample_search_response
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await client.search_hotels(
                destination="zanzibar",
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 5)
            )

            assert result["search_time_seconds"] == 3.5

    @pytest.mark.asyncio
    async def test_hotel_count_from_total_hotels_field(self, mock_circuit_breaker):
        """total_hotels should come from response's total_hotels field."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        response_data = {
            "destination": "mauritius",
            "total_hotels": 25,
            "hotels": [{"name": f"Hotel {i}"} for i in range(10)],  # Only 10 returned
            "search_time_seconds": 5.0
        }

        mock_response = MagicMock()
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await client.search_hotels(
                destination="mauritius",
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 5)
            )

            # total_hotels from response, not len(hotels)
            assert result["total_hotels"] == 25


# ==================== NEW TESTS: Payload Construction ====================

class TestPayloadConstruction:
    """Tests for correct payload construction."""

    @pytest.mark.asyncio
    async def test_rooms_array_structure(self, mock_circuit_breaker, sample_search_response):
        """Payload should have rooms array with adults and children_ages."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        mock_response = MagicMock()
        mock_response.json.return_value = sample_search_response
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await client.search_hotels(
                destination="zanzibar",
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 5),
                adults=3
            )

            call_args = mock_client.post.call_args
            payload = call_args.kwargs.get('json') or call_args[1].get('json')

            assert "rooms" in payload
            assert len(payload["rooms"]) == 1
            assert payload["rooms"][0]["adults"] == 3
            assert payload["rooms"][0]["children_ages"] == []

    @pytest.mark.asyncio
    async def test_max_hotels_sent_in_payload(self, mock_circuit_breaker, sample_search_response):
        """max_hotels should be included in the payload."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        mock_response = MagicMock()
        mock_response.json.return_value = sample_search_response
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await client.search_hotels(
                destination="zanzibar",
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 5),
                max_hotels=10
            )

            call_args = mock_client.post.call_args
            payload = call_args.kwargs.get('json') or call_args[1].get('json')
            assert payload["max_hotels"] == 10

    @pytest.mark.asyncio
    async def test_default_max_hotels_is_50(self, mock_circuit_breaker, sample_search_response):
        """Default max_hotels should be 50."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        mock_response = MagicMock()
        mock_response.json.return_value = sample_search_response
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await client.search_hotels(
                destination="zanzibar",
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 5)
            )

            call_args = mock_client.post.call_args
            payload = call_args.kwargs.get('json') or call_args[1].get('json')
            assert payload["max_hotels"] == 50

    @pytest.mark.asyncio
    async def test_correct_api_endpoint_used(self, mock_circuit_breaker, sample_search_response):
        """Should call /api/v1/availability/search endpoint."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        mock_response = MagicMock()
        mock_response.json.return_value = sample_search_response
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await client.search_hotels(
                destination="zanzibar",
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 5)
            )

            call_url = mock_client.post.call_args[0][0]
            assert '/api/v1/availability/search' in call_url


# ==================== NEW TESTS: Circuit Breaker Integration ====================

class TestCircuitBreakerIntegration:
    """Tests for circuit breaker behavior with the rates client."""

    @pytest.mark.asyncio
    async def test_success_records_on_circuit_breaker(self, mock_circuit_breaker, sample_search_response):
        """Successful search should record success on circuit breaker."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        mock_response = MagicMock()
        mock_response.json.return_value = sample_search_response
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await client.search_hotels(
                destination="zanzibar",
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 5)
            )

        mock_circuit_breaker.record_success.assert_called_once()

    @pytest.mark.asyncio
    async def test_timeout_records_failure_on_circuit_breaker(self, mock_circuit_breaker):
        """Timeout should record failure on circuit breaker."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("Timeout")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await client.search_hotels(
                destination="zanzibar",
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 5)
            )

        mock_circuit_breaker.record_failure.assert_called()

    @pytest.mark.asyncio
    async def test_last_error_set_on_timeout(self, mock_circuit_breaker):
        """_last_error should be set after a timeout."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("Timeout")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await client.search_hotels(
                destination="zanzibar",
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 5)
            )

        assert client._last_error is not None
        assert "timed out" in client._last_error.lower()


# ==================== NEW TESTS: Search by Names Details ====================

class TestSearchByNamesDetails:
    """Detailed tests for search_hotels_by_names method."""

    @pytest.mark.asyncio
    async def test_search_by_names_sends_hotel_names(self):
        """Should include hotel_names in the request payload."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"matched_hotels": [], "unmatched": []}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await client.search_hotels_by_names(
                destination="mauritius",
                hotel_names=["Solana Beach", "Constance Belle Mare"],
                check_in=date(2025, 6, 1),
                check_out=date(2025, 6, 5)
            )

            call_args = mock_client.post.call_args
            payload = call_args.kwargs.get('json') or call_args[1].get('json')
            assert payload["hotel_names"] == ["Solana Beach", "Constance Belle Mare"]
            assert payload["destination"] == "mauritius"

    @pytest.mark.asyncio
    async def test_search_by_names_uses_correct_endpoint(self):
        """Should call /api/v1/availability/search-by-names."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"matched_hotels": []}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await client.search_hotels_by_names(
                destination="zanzibar",
                hotel_names=["Resort A"],
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 5)
            )

            call_url = mock_client.post.call_args[0][0]
            assert '/api/v1/availability/search-by-names' in call_url

    @pytest.mark.asyncio
    async def test_search_by_names_children_ages_default_empty(self):
        """children_ages should default to empty list."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"matched_hotels": []}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await client.search_hotels_by_names(
                destination="zanzibar",
                hotel_names=["Resort A"],
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 5)
            )

            call_args = mock_client.post.call_args
            payload = call_args.kwargs.get('json') or call_args[1].get('json')
            assert payload["children_ages"] == []

    @pytest.mark.asyncio
    async def test_search_by_names_sets_last_error_on_failure(self):
        """_last_error should be set after search_by_names failure."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = Exception("Something broke")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await client.search_hotels_by_names(
                destination="zanzibar",
                hotel_names=["Resort A"],
                check_in=date(2025, 3, 1),
                check_out=date(2025, 3, 5)
            )

        assert result["success"] is False
        assert client._last_error == "Something broke"


# ==================== NEW TESTS: Health Check Endpoint ====================

class TestHealthCheckEndpoint:
    """Additional tests for health check endpoint details."""

    @pytest.mark.asyncio
    async def test_health_check_uses_correct_url(self):
        """Health check should call /api/v1/travel-services/health."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        with patch.dict('os.environ', {'RATES_ENGINE_URL': 'https://my-api.com'}):
            TravelPlatformRatesClient._instance = None
            client = TravelPlatformRatesClient()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await client.is_available()

            call_url = mock_client.get.call_args[0][0]
            assert call_url == 'https://my-api.com/api/v1/travel-services/health'

    @pytest.mark.asyncio
    async def test_health_check_uses_10s_timeout(self):
        """Health check should use 10 second timeout regardless of client timeout."""
        from src.services.travel_platform_rates_client import TravelPlatformRatesClient

        client = TravelPlatformRatesClient()
        assert client.timeout == 120.0  # client timeout is much larger

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await client.is_available()

            call_kwargs = mock_client.get.call_args
            assert call_kwargs.kwargs.get('timeout') == 10.0 or call_kwargs[1].get('timeout') == 10.0
