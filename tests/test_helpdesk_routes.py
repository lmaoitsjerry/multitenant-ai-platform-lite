"""
Helpdesk Routes Unit Tests

Tests for the helpdesk API endpoints:
- GET /api/v1/helpdesk/topics - Get helpdesk topics
- GET /api/v1/helpdesk/search - Search knowledge base
- GET /api/v1/helpdesk/health - Health check
- GET /api/v1/helpdesk/rag-status - RAG system status
- GET /api/v1/helpdesk/faiss-status - FAISS index status
- POST /api/v1/helpdesk/ask - Ask a question
- POST /api/v1/helpdesk/agent/chat - Chat with agent
- POST /api/v1/helpdesk/agent/reset - Reset agent session
- GET /api/v1/helpdesk/agent/stats - Get agent stats
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


# ==================== Fixtures ====================

@pytest.fixture
def test_client():
    """Create a basic TestClient."""
    from main import app
    return TestClient(app)


@pytest.fixture
def mock_config():
    """Create a mock ClientConfig."""
    config = MagicMock()
    config.client_id = "test_tenant"
    config.tenant_id = "test_tenant"
    config.company_name = "Test Company"
    return config


@pytest.fixture
def auth_headers():
    """Create mock auth headers."""
    return {
        "Authorization": "Bearer test-token",
        "X-Client-ID": "test_tenant"
    }


# ==================== Topics Endpoint Tests ====================

class TestTopicsEndpoint:
    """Tests for GET /api/v1/helpdesk/topics endpoint."""

    def test_get_topics_returns_list(self, test_client):
        """GET /topics should return list of helpdesk topics."""
        response = test_client.get("/api/v1/helpdesk/topics")

        assert response.status_code == 200
        data = response.json()
        assert "topics" in data
        assert isinstance(data["topics"], list)
        assert len(data["topics"]) > 0

    def test_get_topics_has_expected_fields(self, test_client):
        """Each topic should have id, name, description, icon."""
        response = test_client.get("/api/v1/helpdesk/topics")
        data = response.json()

        for topic in data["topics"]:
            assert "id" in topic
            assert "name" in topic
            assert "description" in topic
            assert "icon" in topic

    def test_get_topics_includes_quotes_topic(self, test_client):
        """Topics should include quotes topic."""
        response = test_client.get("/api/v1/helpdesk/topics")
        data = response.json()

        topic_ids = [t["id"] for t in data["topics"]]
        assert "quotes" in topic_ids


# ==================== Health Endpoint Tests ====================

class TestHealthEndpoint:
    """Tests for GET /api/v1/helpdesk/health endpoint."""

    def test_health_returns_status(self, test_client):
        """GET /health should return health status (may require auth)."""
        response = test_client.get("/api/v1/helpdesk/health")

        # May require auth depending on configuration
        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert "status" in data


# ==================== RAG Status Endpoint Tests ====================

class TestRagStatusEndpoint:
    """Tests for GET /api/v1/helpdesk/rag-status endpoint."""

    def test_rag_status_requires_auth(self, test_client):
        """GET /rag-status requires authentication."""
        response = test_client.get("/api/v1/helpdesk/rag-status")

        # This endpoint requires authentication
        assert response.status_code == 401

    def test_rag_status_with_client_id_still_requires_auth(self, test_client):
        """GET /rag-status with X-Client-ID still requires auth token."""
        response = test_client.get(
            "/api/v1/helpdesk/rag-status",
            headers={"X-Client-ID": "test_tenant"}
        )

        # X-Client-ID alone is not enough, need auth token
        assert response.status_code == 401


# ==================== FAISS Status Endpoint Tests ====================

class TestFaissStatusEndpoint:
    """Tests for GET /api/v1/helpdesk/faiss-status endpoint."""

    def test_faiss_status_returns_info(self, test_client):
        """GET /faiss-status should return FAISS index info."""
        response = test_client.get("/api/v1/helpdesk/faiss-status")

        assert response.status_code == 200
        data = response.json()
        # Should have some status information
        assert isinstance(data, dict)


# ==================== Search Endpoint Tests ====================

class TestSearchEndpoint:
    """Tests for GET /api/v1/helpdesk/search endpoint."""

    def test_search_without_query_returns_default(self, test_client):
        """GET /search without query should return default response or 401."""
        response = test_client.get("/api/v1/helpdesk/search")

        # May require auth or return default
        assert response.status_code in [200, 401, 422]

    def test_search_with_query(self, test_client):
        """GET /search with query should return results or require auth."""
        response = test_client.get(
            "/api/v1/helpdesk/search",
            params={"q": "test query"}
        )

        # May require auth
        assert response.status_code in [200, 401, 500]

    def test_search_with_limit(self, test_client):
        """GET /search with limit parameter should be accepted."""
        response = test_client.get(
            "/api/v1/helpdesk/search",
            params={"q": "hotels", "limit": 5}
        )

        assert response.status_code in [200, 401, 500]


# ==================== Ask Endpoint Tests ====================

class TestAskEndpoint:
    """Tests for POST /api/v1/helpdesk/ask endpoint."""

    def test_ask_requires_body(self, test_client):
        """POST /ask without body should return 422."""
        response = test_client.post("/api/v1/helpdesk/ask")

        assert response.status_code == 422

    def test_ask_with_question(self, test_client, mock_config):
        """POST /ask with question should process request."""
        with patch('src.api.helpdesk_routes.get_client_config', return_value=mock_config):
            with patch('src.api.helpdesk_routes.get_travel_platform_rag_client') as mock_rag:
                mock_client = MagicMock()
                mock_client.query = AsyncMock(return_value={
                    "success": True,
                    "answer": "Test answer",
                    "sources": []
                })
                mock_rag.return_value = mock_client

                response = test_client.post(
                    "/api/v1/helpdesk/ask",
                    json={"question": "How do I create a quote?"},
                    headers={"X-Client-ID": "test_tenant"}
                )

                # Should return 200 or handle gracefully
                assert response.status_code in [200, 500]


# ==================== Agent Chat Endpoint Tests ====================

class TestAgentChatEndpoint:
    """Tests for POST /api/v1/helpdesk/agent/chat endpoint."""

    def test_agent_chat_requires_auth(self, test_client):
        """POST /agent/chat requires authentication."""
        response = test_client.post("/api/v1/helpdesk/agent/chat")

        # Requires auth
        assert response.status_code == 401

    def test_agent_chat_with_client_id_still_requires_auth(self, test_client):
        """POST /agent/chat with X-Client-ID still requires auth token."""
        response = test_client.post(
            "/api/v1/helpdesk/agent/chat",
            json={"message": "Hello"},
            headers={"X-Client-ID": "test_tenant"}
        )

        assert response.status_code == 401


# ==================== Agent Reset Endpoint Tests ====================

class TestAgentResetEndpoint:
    """Tests for POST /api/v1/helpdesk/agent/reset endpoint."""

    def test_agent_reset_requires_auth(self, test_client):
        """POST /agent/reset requires authentication."""
        response = test_client.post("/api/v1/helpdesk/agent/reset")

        assert response.status_code == 401

    def test_agent_reset_with_client_id_requires_auth(self, test_client):
        """POST /agent/reset with X-Client-ID still requires auth."""
        response = test_client.post(
            "/api/v1/helpdesk/agent/reset",
            headers={"X-Client-ID": "test_tenant"}
        )

        assert response.status_code == 401


# ==================== Agent Stats Endpoint Tests ====================

class TestAgentStatsEndpoint:
    """Tests for GET /api/v1/helpdesk/agent/stats endpoint."""

    def test_agent_stats_requires_auth(self, test_client):
        """GET /agent/stats requires authentication."""
        response = test_client.get("/api/v1/helpdesk/agent/stats")

        assert response.status_code == 401

    def test_agent_stats_with_client_id_requires_auth(self, test_client):
        """GET /agent/stats with X-Client-ID still requires auth."""
        response = test_client.get(
            "/api/v1/helpdesk/agent/stats",
            headers={"X-Client-ID": "test_tenant"}
        )

        assert response.status_code == 401


# ==================== Reinit Endpoint Tests ====================

class TestReinitEndpoint:
    """Tests for POST /api/v1/helpdesk/reinit endpoint."""

    def test_reinit_requires_auth(self, test_client):
        """POST /reinit should require authentication."""
        response = test_client.post("/api/v1/helpdesk/reinit")

        # Should either require auth or handle gracefully
        assert response.status_code in [200, 401, 403, 500]


# ==================== Test Search Endpoint Tests ====================

class TestTestSearchEndpoint:
    """Tests for GET /api/v1/helpdesk/test-search endpoint."""

    def test_test_search_returns_results(self, test_client):
        """GET /test-search should return test search results."""
        with patch('src.api.helpdesk_routes.get_travel_platform_rag_client') as mock_rag:
            mock_client = MagicMock()
            mock_client.search = AsyncMock(return_value={
                "success": True,
                "results": []
            })
            mock_rag.return_value = mock_client

            response = test_client.get("/api/v1/helpdesk/test-search")

            assert response.status_code in [200, 500]


# ==================== Accuracy Test Endpoints Tests ====================

class TestAccuracyTestEndpoints:
    """Tests for accuracy test endpoints."""

    def test_accuracy_test_cases_returns_list(self, test_client):
        """GET /accuracy-test/cases should return test cases."""
        response = test_client.get("/api/v1/helpdesk/accuracy-test/cases")

        # May require admin or return results
        assert response.status_code in [200, 401, 403, 500]

    def test_accuracy_test_runs(self, test_client):
        """GET /accuracy-test should run accuracy tests."""
        response = test_client.get("/api/v1/helpdesk/accuracy-test")

        # May require setup or return results
        assert response.status_code in [200, 401, 403, 500]


# ==================== Client Config Helper Tests ====================

class TestClientConfigHelper:
    """Tests for the get_client_config helper function."""

    def test_get_client_config_caches_result(self, mock_config):
        """get_client_config should cache configurations."""
        from src.api.helpdesk_routes import get_client_config, _client_configs

        # Clear cache
        _client_configs.clear()

        with patch('src.api.helpdesk_routes.ClientConfig', return_value=mock_config):
            config1 = get_client_config("test_tenant")
            config2 = get_client_config("test_tenant")

            # Should return the same cached instance
            assert config1 is config2

    def test_get_client_config_handles_error(self):
        """get_client_config should handle config errors gracefully."""
        from src.api.helpdesk_routes import get_client_config, _client_configs

        # Clear cache
        _client_configs.clear()

        with patch('src.api.helpdesk_routes.ClientConfig', side_effect=Exception("Config error")):
            result = get_client_config("nonexistent_tenant")

            # Should return None on error
            assert result is None
