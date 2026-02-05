"""
HotelBeds Client Unit Tests

Comprehensive tests for HotelBedsClient service:
- Singleton pattern
- Health check
- Hotel search with mocked httpx
- Activity search with mocked httpx
- Transfer search with mocked httpx
- Error handling (timeout, HTTP errors, circuit breaker)
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import date
import httpx


# ==================== Fixtures ====================

@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton before each test."""
    from src.services.hotelbeds_client import reset_hotelbeds_client
    reset_hotelbeds_client()
    yield
    reset_hotelbeds_client()


@pytest.fixture
def mock_circuit_breaker():
    """Mock circuit breaker that allows execution."""
    with patch('src.services.hotelbeds_client.hotelbeds_circuit') as mock:
        mock.can_execute.return_value = True
        mock.get_status.return_value = {"state": "closed", "failures": 0}
        yield mock


# ==================== Singleton Tests ====================

class TestHotelBedsClientSingleton:
    """Test singleton pattern for HotelBedsClient."""

    def test_singleton_returns_same_instance(self):
        """Should return the same instance on multiple calls."""
        from src.services.hotelbeds_client import HotelBedsClient

        client1 = HotelBedsClient()
        client2 = HotelBedsClient()

        assert client1 is client2

    def test_get_hotelbeds_client_returns_singleton(self):
        """get_hotelbeds_client should return singleton."""
        from src.services.hotelbeds_client import get_hotelbeds_client

        client1 = get_hotelbeds_client()
        client2 = get_hotelbeds_client()

        assert client1 is client2

    def test_reset_hotelbeds_client_clears_singleton(self):
        """reset_hotelbeds_client should clear the singleton."""
        from src.services.hotelbeds_client import (
            get_hotelbeds_client, reset_hotelbeds_client, HotelBedsClient
        )

        client1 = get_hotelbeds_client()
        reset_hotelbeds_client()
        client2 = get_hotelbeds_client()

        assert client1 is not client2


# ==================== Initialization Tests ====================

class TestHotelBedsClientInit:
    """Test HotelBedsClient initialization."""

    def test_default_base_url(self):
        """Should use default base URL when env var not set."""
        from src.services.hotelbeds_client import HotelBedsClient

        with patch.dict('os.environ', {}, clear=True):
            client = HotelBedsClient()
            assert "zorah-travel-platform" in client.base_url

    def test_default_timeout(self):
        """Should use default timeout of 60 seconds."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()
        assert client.timeout == 60.0

    def test_initialized_flag_set(self):
        """Should set _initialized flag."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()
        assert client._initialized is True


# ==================== Health Check Tests ====================

class TestHealthCheck:
    """Test health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Should return success on healthy response."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "healthy",
            "environment": "test"
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.health_check()

        assert result["success"] is True
        assert result["available"] is True
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        """Should return unavailable on non-healthy status."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "degraded",
            "environment": "test"
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.health_check()

        assert result["success"] is True
        assert result["available"] is False

    @pytest.mark.asyncio
    async def test_health_check_http_error(self):
        """Should handle HTTP errors gracefully."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.health_check()

        assert result["success"] is False
        assert result["available"] is False
        assert "HTTP 500" in result["error"]

    @pytest.mark.asyncio
    async def test_health_check_exception(self):
        """Should handle connection errors gracefully."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Connection refused")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.health_check()

        assert result["success"] is False
        assert result["available"] is False
        assert "Connection refused" in result["error"]


# ==================== Hotel Search Tests ====================

class TestSearchHotels:
    """Test search_hotels method."""

    @pytest.mark.asyncio
    async def test_search_hotels_success(self, mock_circuit_breaker):
        """Should return hotels on successful search."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hotels": [{"name": "Test Hotel", "price": 100}],
            "count": 1,
            "destination": "zanzibar"
        }
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.search_hotels(
                destination="zanzibar",
                check_in=date(2026, 3, 15),
                check_out=date(2026, 3, 20),
                adults=2
            )

        assert result["success"] is True
        assert result["source"] == "hotelbeds"
        assert len(result["hotels"]) == 1
        mock_circuit_breaker.record_success.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_hotels_with_children(self, mock_circuit_breaker):
        """Should use POST when children_ages provided."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"hotels": [], "count": 0}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await client.search_hotels(
                destination="zanzibar",
                check_in=date(2026, 3, 15),
                check_out=date(2026, 3, 20),
                adults=2,
                children_ages=[5, 8]
            )

        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_hotels_circuit_breaker_open(self, mock_circuit_breaker):
        """Should return error when circuit breaker is open."""
        from src.services.hotelbeds_client import HotelBedsClient

        mock_circuit_breaker.can_execute.return_value = False

        client = HotelBedsClient()

        result = await client.search_hotels(
            destination="zanzibar",
            check_in=date(2026, 3, 15),
            check_out=date(2026, 3, 20)
        )

        assert result["success"] is False
        assert "Circuit breaker" in result["error"]

    @pytest.mark.asyncio
    async def test_search_hotels_timeout(self, mock_circuit_breaker):
        """Should handle timeout errors."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("Timeout")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.search_hotels(
                destination="zanzibar",
                check_in=date(2026, 3, 15),
                check_out=date(2026, 3, 20)
            )

        assert result["success"] is False
        assert "timed out" in result["error"]
        mock_circuit_breaker.record_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_hotels_http_error(self, mock_circuit_breaker):
        """Should handle HTTP status errors."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.HTTPStatusError(
                "Server Error",
                request=MagicMock(),
                response=mock_response
            )
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.search_hotels(
                destination="zanzibar",
                check_in=date(2026, 3, 15),
                check_out=date(2026, 3, 20)
            )

        assert result["success"] is False
        assert "HTTP 500" in result["error"]
        mock_circuit_breaker.record_failure.assert_called_once()


# ==================== Activity Search Tests ====================

class TestSearchActivities:
    """Test search_activities method."""

    @pytest.mark.asyncio
    async def test_search_activities_success(self, mock_circuit_breaker):
        """Should return activities on successful search."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "activities": [{"name": "Safari Tour", "price": 200}],
            "count": 1
        }
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.search_activities(
                destination="zanzibar",
                participants=4
            )

        assert result["success"] is True
        assert result["source"] == "hotelbeds"
        assert len(result["activities"]) == 1

    @pytest.mark.asyncio
    async def test_search_activities_circuit_breaker_open(self, mock_circuit_breaker):
        """Should return error when circuit breaker is open."""
        from src.services.hotelbeds_client import HotelBedsClient

        mock_circuit_breaker.can_execute.return_value = False

        client = HotelBedsClient()

        result = await client.search_activities(
            destination="zanzibar",
            participants=2
        )

        assert result["success"] is False
        assert "Circuit breaker" in result["error"]


# ==================== Transfer Search Tests ====================

class TestSearchTransfers:
    """Test search_transfers method."""

    @pytest.mark.asyncio
    async def test_search_transfers_success(self, mock_circuit_breaker):
        """Should return transfers on successful search."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "transfers": [{"vehicle": "Sedan", "price": 50}],
            "count": 1
        }
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.search_transfers(
                route="Airport to Hotel",
                transfer_date=date(2026, 3, 15),
                passengers=3
            )

        assert result["success"] is True
        assert result["source"] == "hotelbeds"
        assert len(result["transfers"]) == 1

    @pytest.mark.asyncio
    async def test_search_transfers_circuit_breaker_open(self, mock_circuit_breaker):
        """Should return error when circuit breaker is open."""
        from src.services.hotelbeds_client import HotelBedsClient

        mock_circuit_breaker.can_execute.return_value = False

        client = HotelBedsClient()

        result = await client.search_transfers(
            route="Airport to Hotel",
            transfer_date=date(2026, 3, 15),
            passengers=2
        )

        assert result["success"] is False
        assert "Circuit breaker" in result["error"]


# ==================== Utility Method Tests ====================

class TestUtilityMethods:
    """Test utility methods."""

    def test_error_response_structure(self):
        """_error_response should return proper structure."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()
        result = client._error_response("Test error")

        assert result["success"] is False
        assert result["error"] == "Test error"
        assert result["hotels"] == []
        assert result["activities"] == []
        assert result["transfers"] == []
        assert result["count"] == 0

    def test_get_status(self, mock_circuit_breaker):
        """get_status should return client status."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()
        status = client.get_status()

        assert status["initialized"] is True
        assert "base_url" in status
        assert "timeout" in status
        assert "circuit_breaker" in status


# ==================== NEW TESTS: Initialization Edge Cases ====================

class TestHotelBedsClientInitEdgeCases:
    """Extended initialization tests for HotelBedsClient."""

    def test_custom_base_url_from_env(self):
        """Should use HOTELBEDS_API_URL env var when set."""
        from src.services.hotelbeds_client import HotelBedsClient

        with patch.dict('os.environ', {"HOTELBEDS_API_URL": "https://custom-api.example.com"}):
            client = HotelBedsClient()
            assert client.base_url == "https://custom-api.example.com"

    def test_custom_timeout_from_env(self):
        """Should use HOTELBEDS_API_TIMEOUT env var when set."""
        from src.services.hotelbeds_client import HotelBedsClient

        with patch.dict('os.environ', {"HOTELBEDS_API_TIMEOUT": "120"}):
            client = HotelBedsClient()
            assert client.timeout == 120.0

    def test_last_error_initially_none(self):
        """_last_error should be None after initialization."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()
        assert client._last_error is None

    def test_singleton_only_initializes_once(self):
        """__init__ should only run initialization logic once."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()
        original_url = client.base_url

        # Modify the URL to verify __init__ doesn't reset it
        client.base_url = "http://modified-url.com"

        # Creating another instance should NOT re-initialize
        client2 = HotelBedsClient()
        assert client2.base_url == "http://modified-url.com"

    def test_timeout_is_float_type(self):
        """Timeout should be stored as float even from string env var."""
        from src.services.hotelbeds_client import HotelBedsClient

        with patch.dict('os.environ', {"HOTELBEDS_API_TIMEOUT": "30"}):
            client = HotelBedsClient()
            assert isinstance(client.timeout, float)


# ==================== NEW TESTS: Health Check Edge Cases ====================

class TestHealthCheckEdgeCases:
    """Extended health check tests."""

    @pytest.mark.asyncio
    async def test_health_check_stores_last_error(self):
        """Should store the last error when health check fails."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Network unreachable")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.health_check()

        assert client._last_error == "Network unreachable"

    @pytest.mark.asyncio
    async def test_health_check_timeout_exception(self):
        """Should handle httpx.TimeoutException in health check."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("Health check timed out")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.health_check()

        assert result["success"] is False
        assert result["available"] is False
        assert "timed out" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_health_check_non_200_status(self):
        """Should handle non-200 status like 503 Service Unavailable."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.status_code = 503

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.health_check()

        assert result["success"] is False
        assert "HTTP 503" in result["error"]

    @pytest.mark.asyncio
    async def test_health_check_uses_correct_url(self):
        """Should call the correct health endpoint URL."""
        from src.services.hotelbeds_client import HotelBedsClient

        with patch.dict('os.environ', {"HOTELBEDS_API_URL": "https://api.test.com"}):
            client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await client.health_check()

        mock_client.get.assert_called_once_with(
            "https://api.test.com/api/v1/hotelbeds/health",
            timeout=10.0
        )


# ==================== NEW TESTS: Hotel Search Request Building ====================

class TestSearchHotelsRequestBuilding:
    """Tests for how search_hotels builds and sends requests."""

    @pytest.mark.asyncio
    async def test_search_hotels_sends_correct_params(self, mock_circuit_breaker):
        """Should send destination, dates, adults, max_hotels as query params."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.json.return_value = {"hotels": [], "count": 0}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await client.search_hotels(
                destination="Mauritius",
                check_in=date(2026, 6, 1),
                check_out=date(2026, 6, 10),
                adults=3,
                max_hotels=25
            )

        call_args = mock_client.get.call_args
        params = call_args.kwargs.get("params", call_args[1].get("params"))
        assert params["destination"] == "mauritius"  # lowercased
        assert params["check_in"] == "2026-06-01"
        assert params["check_out"] == "2026-06-10"
        assert params["adults"] == 3
        assert params["max_hotels"] == 25

    @pytest.mark.asyncio
    async def test_search_hotels_post_includes_children_ages(self, mock_circuit_breaker):
        """POST request should include children_ages in JSON body."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.json.return_value = {"hotels": [], "count": 0}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await client.search_hotels(
                destination="zanzibar",
                check_in=date(2026, 3, 15),
                check_out=date(2026, 3, 20),
                adults=2,
                children_ages=[3, 7, 12]
            )

        call_args = mock_client.post.call_args
        json_body = call_args.kwargs.get("json", call_args[1].get("json"))
        assert json_body["children_ages"] == [3, 7, 12]
        assert json_body["destination"] == "zanzibar"

    @pytest.mark.asyncio
    async def test_search_hotels_uses_get_without_children(self, mock_circuit_breaker):
        """Should use GET when no children_ages provided."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.json.return_value = {"hotels": [], "count": 0}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await client.search_hotels(
                destination="zanzibar",
                check_in=date(2026, 3, 15),
                check_out=date(2026, 3, 20)
            )

        mock_client.get.assert_called_once()
        mock_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_hotels_default_adults_is_two(self, mock_circuit_breaker):
        """Default adults parameter should be 2."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.json.return_value = {"hotels": [], "count": 0}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await client.search_hotels(
                destination="zanzibar",
                check_in=date(2026, 3, 15),
                check_out=date(2026, 3, 20)
            )

        call_args = mock_client.get.call_args
        params = call_args.kwargs.get("params", call_args[1].get("params"))
        assert params["adults"] == 2


# ==================== NEW TESTS: Hotel Search Response Parsing ====================

class TestSearchHotelsResponseParsing:
    """Tests for how search_hotels parses response data."""

    @pytest.mark.asyncio
    async def test_success_response_includes_source_field(self, mock_circuit_breaker):
        """Successful response should include source='hotelbeds'."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "hotels": [{"id": 1, "name": "Beach Resort"}],
            "count": 1,
            "destination": "zanzibar"
        }
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.search_hotels(
                destination="zanzibar",
                check_in=date(2026, 3, 15),
                check_out=date(2026, 3, 20)
            )

        assert result["success"] is True
        assert result["source"] == "hotelbeds"
        assert result["count"] == 1
        assert result["destination"] == "zanzibar"

    @pytest.mark.asyncio
    async def test_empty_hotels_result(self, mock_circuit_breaker):
        """Should handle empty hotel results gracefully."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.json.return_value = {"hotels": [], "count": 0}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.search_hotels(
                destination="unknown_place",
                check_in=date(2026, 3, 15),
                check_out=date(2026, 3, 20)
            )

        assert result["success"] is True
        assert result["hotels"] == []
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_multiple_hotels_in_response(self, mock_circuit_breaker):
        """Should return all hotels from API response."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        hotels_data = [
            {"id": i, "name": f"Hotel {i}", "price": 100 + i * 50}
            for i in range(5)
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "hotels": hotels_data,
            "count": 5,
            "destination": "mauritius"
        }
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.search_hotels(
                destination="mauritius",
                check_in=date(2026, 6, 1),
                check_out=date(2026, 6, 7)
            )

        assert result["success"] is True
        assert len(result["hotels"]) == 5
        assert result["hotels"][0]["name"] == "Hotel 0"
        assert result["hotels"][4]["price"] == 300


# ==================== NEW TESTS: Activity Search Edge Cases ====================

class TestSearchActivitiesEdgeCases:
    """Extended tests for search_activities method."""

    @pytest.mark.asyncio
    async def test_search_activities_default_participants(self, mock_circuit_breaker):
        """Default participants should be 2."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.json.return_value = {"activities": [], "count": 0}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await client.search_activities(destination="zanzibar")

        call_args = mock_client.get.call_args
        params = call_args.kwargs.get("params", call_args[1].get("params"))
        assert params["participants"] == 2

    @pytest.mark.asyncio
    async def test_search_activities_lowercases_destination(self, mock_circuit_breaker):
        """Should lowercase destination in request params."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.json.return_value = {"activities": [], "count": 0}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await client.search_activities(destination="MAURITIUS", participants=4)

        call_args = mock_client.get.call_args
        params = call_args.kwargs.get("params", call_args[1].get("params"))
        assert params["destination"] == "mauritius"

    @pytest.mark.asyncio
    async def test_search_activities_timeout(self, mock_circuit_breaker):
        """Should handle timeout during activity search."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("Activity search timed out")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.search_activities(destination="zanzibar")

        assert result["success"] is False
        assert "timed out" in result["error"]
        mock_circuit_breaker.record_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_activities_http_error(self, mock_circuit_breaker):
        """Should handle HTTP status errors during activity search."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.HTTPStatusError(
                "Rate limited",
                request=MagicMock(),
                response=mock_response
            )
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.search_activities(destination="zanzibar")

        assert result["success"] is False
        assert "HTTP 429" in result["error"]
        mock_circuit_breaker.record_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_activities_generic_exception(self, mock_circuit_breaker):
        """Should handle generic exceptions during activity search."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = RuntimeError("Unexpected error")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.search_activities(destination="zanzibar")

        assert result["success"] is False
        assert "Unexpected error" in result["error"]
        mock_circuit_breaker.record_failure.assert_called_once()


# ==================== NEW TESTS: Transfer Search Edge Cases ====================

class TestSearchTransfersEdgeCases:
    """Extended tests for search_transfers method."""

    @pytest.mark.asyncio
    async def test_search_transfers_default_passengers(self, mock_circuit_breaker):
        """Default passengers should be 2."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.json.return_value = {"transfers": [], "count": 0}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await client.search_transfers(
                route="Airport to Hotel",
                transfer_date=date(2026, 3, 15)
            )

        call_args = mock_client.get.call_args
        params = call_args.kwargs.get("params", call_args[1].get("params"))
        assert params["passengers"] == 2

    @pytest.mark.asyncio
    async def test_search_transfers_sends_correct_params(self, mock_circuit_breaker):
        """Should send route, date, and passengers as query params."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.json.return_value = {"transfers": [], "count": 0}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await client.search_transfers(
                route="Zanzibar Airport to Stone Town",
                transfer_date=date(2026, 7, 20),
                passengers=5
            )

        call_args = mock_client.get.call_args
        params = call_args.kwargs.get("params", call_args[1].get("params"))
        assert params["route"] == "Zanzibar Airport to Stone Town"
        assert params["date"] == "2026-07-20"
        assert params["passengers"] == 5

    @pytest.mark.asyncio
    async def test_search_transfers_timeout(self, mock_circuit_breaker):
        """Should handle timeout during transfer search."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("Transfer search timed out")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.search_transfers(
                route="Airport to Hotel",
                transfer_date=date(2026, 3, 15)
            )

        assert result["success"] is False
        assert "timed out" in result["error"]
        mock_circuit_breaker.record_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_transfers_http_error(self, mock_circuit_breaker):
        """Should handle HTTP status errors during transfer search."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request: invalid route"

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.HTTPStatusError(
                "Bad Request",
                request=MagicMock(),
                response=mock_response
            )
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.search_transfers(
                route="Invalid",
                transfer_date=date(2026, 3, 15)
            )

        assert result["success"] is False
        assert "HTTP 400" in result["error"]

    @pytest.mark.asyncio
    async def test_search_transfers_generic_exception(self, mock_circuit_breaker):
        """Should handle generic exceptions during transfer search."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = ValueError("Bad data")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.search_transfers(
                route="Airport",
                transfer_date=date(2026, 3, 15)
            )

        assert result["success"] is False
        assert "Bad data" in result["error"]


# ==================== NEW TESTS: Error Response Structure ====================

class TestErrorResponseStructure:
    """Extended tests for _error_response utility method."""

    def test_error_response_with_long_error_message(self):
        """Should handle very long error messages."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()
        long_error = "E" * 5000
        result = client._error_response(long_error)

        assert result["success"] is False
        assert result["error"] == long_error
        assert result["count"] == 0

    def test_error_response_with_special_characters(self):
        """Should handle error messages with special characters."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()
        result = client._error_response("Error: <html>Server error & more</html>")

        assert result["success"] is False
        assert "<html>" in result["error"]

    def test_error_response_all_arrays_empty(self):
        """All array fields in error response should be empty lists."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()
        result = client._error_response("test")

        assert result["hotels"] == []
        assert result["activities"] == []
        assert result["transfers"] == []


# ==================== NEW TESTS: Get Status Extended ====================

class TestGetStatusExtended:
    """Extended tests for get_status method."""

    def test_status_includes_last_error_after_failure(self, mock_circuit_breaker):
        """Should include last error in status after a failure."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()
        client._last_error = "Previous timeout error"

        status = client.get_status()

        assert status["last_error"] == "Previous timeout error"

    def test_status_last_error_none_initially(self, mock_circuit_breaker):
        """Should have last_error as None when no errors occurred."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()
        status = client.get_status()

        assert status["last_error"] is None

    def test_status_reflects_custom_timeout(self, mock_circuit_breaker):
        """Status should reflect custom timeout setting."""
        from src.services.hotelbeds_client import HotelBedsClient

        with patch.dict('os.environ', {"HOTELBEDS_API_TIMEOUT": "90"}):
            client = HotelBedsClient()

        status = client.get_status()
        assert status["timeout"] == 90.0

    def test_status_includes_circuit_breaker_info(self, mock_circuit_breaker):
        """Status should include circuit breaker state information."""
        from src.services.hotelbeds_client import HotelBedsClient

        mock_circuit_breaker.get_status.return_value = {
            "name": "hotelbeds",
            "state": "closed",
            "failures": 2,
            "threshold": 3
        }

        client = HotelBedsClient()
        status = client.get_status()

        cb_status = status["circuit_breaker"]
        assert cb_status["name"] == "hotelbeds"
        assert cb_status["state"] == "closed"
        assert cb_status["failures"] == 2


# ==================== NEW TESTS: Circuit Breaker Integration ====================

class TestCircuitBreakerIntegration:
    """Tests for circuit breaker recording across all search methods."""

    @pytest.mark.asyncio
    async def test_hotel_search_records_success_on_circuit(self, mock_circuit_breaker):
        """Successful hotel search should record success on circuit breaker."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.json.return_value = {"hotels": [], "count": 0}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await client.search_hotels("zanzibar", date(2026, 3, 15), date(2026, 3, 20))

        mock_circuit_breaker.record_success.assert_called_once()
        mock_circuit_breaker.record_failure.assert_not_called()

    @pytest.mark.asyncio
    async def test_activity_search_records_success_on_circuit(self, mock_circuit_breaker):
        """Successful activity search should record success on circuit breaker."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.json.return_value = {"activities": [], "count": 0}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await client.search_activities("zanzibar")

        mock_circuit_breaker.record_success.assert_called_once()

    @pytest.mark.asyncio
    async def test_transfer_search_records_success_on_circuit(self, mock_circuit_breaker):
        """Successful transfer search should record success on circuit breaker."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.json.return_value = {"transfers": [], "count": 0}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await client.search_transfers("Airport to Hotel", date(2026, 3, 15))

        mock_circuit_breaker.record_success.assert_called_once()

    @pytest.mark.asyncio
    async def test_hotel_search_exception_records_failure(self, mock_circuit_breaker):
        """Generic exception in hotel search should record failure on circuit breaker."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = ConnectionError("Connection lost")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await client.search_hotels("zanzibar", date(2026, 3, 15), date(2026, 3, 20))

        mock_circuit_breaker.record_failure.assert_called_once()
        mock_circuit_breaker.record_success.assert_not_called()


# ==================== NEW TESTS: Singleton Accessor and Reset ====================

class TestSingletonAccessorAndReset:
    """Extended tests for get_hotelbeds_client and reset_hotelbeds_client."""

    def test_get_hotelbeds_client_creates_instance(self):
        """get_hotelbeds_client should create a new instance if none exists."""
        from src.services.hotelbeds_client import get_hotelbeds_client, HotelBedsClient

        client = get_hotelbeds_client()
        assert isinstance(client, HotelBedsClient)

    def test_reset_clears_class_instance(self):
        """reset_hotelbeds_client should clear HotelBedsClient._instance."""
        from src.services.hotelbeds_client import (
            get_hotelbeds_client, reset_hotelbeds_client, HotelBedsClient
        )

        get_hotelbeds_client()
        assert HotelBedsClient._instance is not None

        reset_hotelbeds_client()
        assert HotelBedsClient._instance is None

    def test_reset_allows_reinitialization_with_new_env(self):
        """After reset, new instance should pick up changed env vars."""
        from src.services.hotelbeds_client import (
            get_hotelbeds_client, reset_hotelbeds_client
        )

        with patch.dict('os.environ', {"HOTELBEDS_API_URL": "http://old-url.com"}):
            client1 = get_hotelbeds_client()
            url1 = client1.base_url

        reset_hotelbeds_client()

        with patch.dict('os.environ', {"HOTELBEDS_API_URL": "http://new-url.com"}):
            client2 = get_hotelbeds_client()
            url2 = client2.base_url

        assert url1 == "http://old-url.com"
        assert url2 == "http://new-url.com"


# ==================== NEW TESTS: Last Error Tracking ====================

class TestLastErrorTracking:
    """Tests for _last_error tracking across different failure modes."""

    @pytest.mark.asyncio
    async def test_timeout_sets_last_error(self, mock_circuit_breaker):
        """Timeout should update _last_error with timeout message."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()
        assert client._last_error is None

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("Timed out")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await client.search_hotels("zanzibar", date(2026, 3, 15), date(2026, 3, 20))

        assert client._last_error is not None
        assert "timed out" in client._last_error.lower()

    @pytest.mark.asyncio
    async def test_http_error_sets_last_error(self, mock_circuit_breaker):
        """HTTP error should update _last_error with status code."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        mock_response = MagicMock()
        mock_response.status_code = 502
        mock_response.text = "Bad Gateway"

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.HTTPStatusError(
                "Bad Gateway",
                request=MagicMock(),
                response=mock_response
            )
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await client.search_hotels("zanzibar", date(2026, 3, 15), date(2026, 3, 20))

        assert "HTTP 502" in client._last_error

    @pytest.mark.asyncio
    async def test_generic_exception_sets_last_error(self, mock_circuit_breaker):
        """Generic exception should update _last_error."""
        from src.services.hotelbeds_client import HotelBedsClient

        client = HotelBedsClient()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = RuntimeError("Something went wrong")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await client.search_hotels("zanzibar", date(2026, 3, 15), date(2026, 3, 20))

        assert client._last_error == "Something went wrong"
