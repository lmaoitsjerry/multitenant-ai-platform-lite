"""
Travel Platform RAG Client Tests

Tests for the Travel Platform RAG API client.
"""

import pytest
from unittest.mock import patch, MagicMock
import requests


# ==================== Fixtures ====================

@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton before each test."""
    from src.services.travel_platform_rag_client import reset_travel_platform_rag_client
    reset_travel_platform_rag_client()
    yield
    reset_travel_platform_rag_client()


@pytest.fixture
def mock_env():
    """Mock environment variables."""
    with patch.dict('os.environ', {
        'TRAVEL_PLATFORM_URL': 'http://test-platform.local',
        'TRAVEL_PLATFORM_API_KEY': 'test-api-key',
        'TRAVEL_PLATFORM_TENANT': 'test-tenant',
        'TRAVEL_PLATFORM_TIMEOUT': '15'
    }):
        yield


# ==================== Initialization Tests ====================

class TestClientInitialization:
    """Tests for client initialization."""

    def test_client_is_singleton(self, mock_env):
        """Client should follow singleton pattern."""
        from src.services.travel_platform_rag_client import TravelPlatformRAGClient

        client1 = TravelPlatformRAGClient()
        client2 = TravelPlatformRAGClient()

        assert client1 is client2

    def test_get_client_returns_singleton(self, mock_env):
        """get_travel_platform_rag_client should return singleton."""
        from src.services.travel_platform_rag_client import get_travel_platform_rag_client

        client1 = get_travel_platform_rag_client()
        client2 = get_travel_platform_rag_client()

        assert client1 is client2

    def test_client_reads_env_vars(self, mock_env):
        """Client should read configuration from environment."""
        from src.services.travel_platform_rag_client import TravelPlatformRAGClient

        client = TravelPlatformRAGClient()

        assert client.base_url == 'http://test-platform.local'
        assert client.api_key == 'test-api-key'
        assert client.tenant_slug == 'test-tenant'
        assert client.timeout == 15

    def test_client_has_default_values(self):
        """Client should have sensible defaults."""
        from src.services.travel_platform_rag_client import TravelPlatformRAGClient

        with patch.dict('os.environ', {}, clear=True):
            client = TravelPlatformRAGClient()

            assert client.base_url == 'http://localhost:8000'
            assert client.tenant_slug == 'itc'
            assert client.timeout == 30

    def test_client_sets_auth_header(self, mock_env):
        """Client should set Authorization header with API key."""
        from src.services.travel_platform_rag_client import TravelPlatformRAGClient

        client = TravelPlatformRAGClient()

        assert 'Authorization' in client.session.headers
        assert client.session.headers['Authorization'] == 'Bearer test-api-key'

    def test_client_marks_as_initialized(self, mock_env):
        """Client should mark itself as initialized."""
        from src.services.travel_platform_rag_client import TravelPlatformRAGClient

        client = TravelPlatformRAGClient()

        assert client._initialized is True


# ==================== Is Available Tests ====================

class TestIsAvailable:
    """Tests for the is_available method."""

    def test_returns_true_when_healthy(self, mock_env):
        """Should return True when health check succeeds."""
        from src.services.travel_platform_rag_client import TravelPlatformRAGClient

        client = TravelPlatformRAGClient()

        with patch.object(requests, 'get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                'status': 'healthy',
                'database': 'connected',
                'warmed_up': True
            }

            assert client.is_available() is True

    def test_returns_true_when_degraded(self, mock_env):
        """Should return True when status is degraded (still usable)."""
        from src.services.travel_platform_rag_client import TravelPlatformRAGClient

        client = TravelPlatformRAGClient()

        with patch.object(requests, 'get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {'status': 'degraded'}

            assert client.is_available() is True

    def test_returns_false_on_non_200(self, mock_env):
        """Should return False on non-200 response."""
        from src.services.travel_platform_rag_client import TravelPlatformRAGClient

        client = TravelPlatformRAGClient()

        with patch.object(requests, 'get') as mock_get:
            mock_get.return_value.status_code = 503

            assert client.is_available() is False

    def test_returns_false_on_unhealthy_status(self, mock_env):
        """Should return False when status is not healthy/degraded."""
        from src.services.travel_platform_rag_client import TravelPlatformRAGClient

        client = TravelPlatformRAGClient()

        with patch.object(requests, 'get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {'status': 'unhealthy'}

            assert client.is_available() is False

    def test_returns_false_on_exception(self, mock_env):
        """Should return False on connection error."""
        from src.services.travel_platform_rag_client import TravelPlatformRAGClient

        client = TravelPlatformRAGClient()

        with patch.object(requests, 'get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError()

            assert client.is_available() is False


# ==================== Search Tests ====================

def _reset_circuit_breaker(cb):
    """Helper to reset a circuit breaker to closed state."""
    cb.failures = 0
    cb.state = "closed"
    cb.last_failure_time = 0


class TestSearch:
    """Tests for the search method."""

    def test_search_returns_success_response(self, mock_env):
        """Search should return success response on valid request."""
        from src.services.travel_platform_rag_client import TravelPlatformRAGClient
        from src.utils.circuit_breaker import rag_circuit

        # Reset circuit breaker
        _reset_circuit_breaker(rag_circuit)

        client = TravelPlatformRAGClient()

        with patch.object(client.session, 'post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.raise_for_status = MagicMock()
            mock_post.return_value.json.return_value = {
                'answer': 'Test answer',
                'citations': [{'source': 'doc1'}],
                'confidence': 0.95,
                'latency_ms': 150,
                'query_id': 'q-123'
            }

            result = client.search('How do I create a quote?')

            assert result['success'] is True
            assert result['answer'] == 'Test answer'
            assert result['confidence'] == 0.95
            assert len(result['citations']) == 1

    def test_search_uses_correct_endpoint(self, mock_env):
        """Search should call correct endpoint."""
        from src.services.travel_platform_rag_client import TravelPlatformRAGClient
        from src.utils.circuit_breaker import rag_circuit

        _reset_circuit_breaker(rag_circuit)

        client = TravelPlatformRAGClient()

        with patch.object(client.session, 'post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.raise_for_status = MagicMock()
            mock_post.return_value.json.return_value = {'answer': ''}

            client.search('test query')

            mock_post.assert_called_once()
            call_url = mock_post.call_args[0][0]
            assert '/api/v1/rag/search' in call_url

    def test_search_sends_correct_payload(self, mock_env):
        """Search should send correct payload."""
        from src.services.travel_platform_rag_client import TravelPlatformRAGClient
        from src.utils.circuit_breaker import rag_circuit

        _reset_circuit_breaker(rag_circuit)

        client = TravelPlatformRAGClient()

        with patch.object(client.session, 'post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.raise_for_status = MagicMock()
            mock_post.return_value.json.return_value = {'answer': ''}

            client.search('my query', top_k=10, include_shared=False)

            call_kwargs = mock_post.call_args[1]
            payload = call_kwargs['json']
            assert payload['query'] == 'my query'
            assert payload['top_k'] == 10
            assert payload['include_shared'] is False

    def test_search_returns_error_on_timeout(self, mock_env):
        """Search should return error response on timeout."""
        from src.services.travel_platform_rag_client import TravelPlatformRAGClient
        from src.utils.circuit_breaker import rag_circuit

        _reset_circuit_breaker(rag_circuit)

        client = TravelPlatformRAGClient()

        with patch.object(client.session, 'post') as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout()

            result = client.search('test')

            assert result['success'] is False
            assert 'error' in result
            assert 'timed out' in result['error'].lower()

    def test_search_returns_error_on_connection_error(self, mock_env):
        """Search should return error response on connection error."""
        from src.services.travel_platform_rag_client import TravelPlatformRAGClient
        from src.utils.circuit_breaker import rag_circuit

        _reset_circuit_breaker(rag_circuit)

        client = TravelPlatformRAGClient()

        with patch.object(client.session, 'post') as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

            result = client.search('test')

            assert result['success'] is False
            assert 'error' in result

    def test_search_returns_error_on_http_error(self, mock_env):
        """Search should return error response on HTTP error."""
        from src.services.travel_platform_rag_client import TravelPlatformRAGClient
        from src.utils.circuit_breaker import rag_circuit

        _reset_circuit_breaker(rag_circuit)

        client = TravelPlatformRAGClient()

        with patch.object(client.session, 'post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = 'Internal Server Error'
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
            mock_post.return_value = mock_response

            result = client.search('test')

            assert result['success'] is False
            assert 'error' in result

    def test_search_skips_when_circuit_open(self, mock_env):
        """Search should skip when circuit breaker is open."""
        from src.services.travel_platform_rag_client import TravelPlatformRAGClient
        from src.utils.circuit_breaker import rag_circuit

        # Reset first then force circuit breaker open
        _reset_circuit_breaker(rag_circuit)
        for _ in range(rag_circuit.failure_threshold + 1):
            rag_circuit.record_failure()

        client = TravelPlatformRAGClient()

        result = client.search('test')

        assert result['success'] is False
        assert 'circuit breaker' in result['error'].lower()


# ==================== Get Status Tests ====================

class TestGetStatus:
    """Tests for the get_status method."""

    def test_get_status_returns_dict(self, mock_env):
        """get_status should return status dictionary."""
        from src.services.travel_platform_rag_client import TravelPlatformRAGClient

        client = TravelPlatformRAGClient()

        with patch.object(client, 'is_available', return_value=True):
            status = client.get_status()

        assert isinstance(status, dict)
        assert 'initialized' in status
        assert 'available' in status
        assert 'base_url' in status
        assert 'tenant' in status
        assert 'timeout' in status

    def test_get_status_reflects_availability(self, mock_env):
        """get_status should reflect actual availability."""
        from src.services.travel_platform_rag_client import TravelPlatformRAGClient

        client = TravelPlatformRAGClient()

        with patch.object(client, 'is_available', return_value=False):
            status = client.get_status()
            assert status['available'] is False

        with patch.object(client, 'is_available', return_value=True):
            status = client.get_status()
            assert status['available'] is True


# ==================== Error Response Tests ====================

class TestErrorResponse:
    """Tests for the _error_response method."""

    def test_error_response_structure(self, mock_env):
        """Error response should have correct structure."""
        from src.services.travel_platform_rag_client import TravelPlatformRAGClient

        client = TravelPlatformRAGClient()

        result = client._error_response("Test error message")

        assert result['success'] is False
        assert result['answer'] == ''
        assert result['citations'] == []
        assert result['confidence'] == 0.0
        assert result['latency_ms'] == 0
        assert result['error'] == "Test error message"


# ==================== Reset Tests ====================

class TestReset:
    """Tests for resetting the singleton."""

    def test_reset_clears_singleton(self, mock_env):
        """reset_travel_platform_rag_client should clear singleton."""
        from src.services.travel_platform_rag_client import (
            TravelPlatformRAGClient,
            get_travel_platform_rag_client,
            reset_travel_platform_rag_client
        )

        client1 = get_travel_platform_rag_client()
        client1_id = id(client1)

        reset_travel_platform_rag_client()

        client2 = get_travel_platform_rag_client()
        client2_id = id(client2)

        # Should be different instances
        assert client1_id != client2_id
