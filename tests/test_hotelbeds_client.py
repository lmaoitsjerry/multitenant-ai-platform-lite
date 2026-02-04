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
