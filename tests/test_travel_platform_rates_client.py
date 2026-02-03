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
