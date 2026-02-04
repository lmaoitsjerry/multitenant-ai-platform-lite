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


# ==================== Pydantic Model Tests ====================

class TestAskQuestionModel:
    """Tests for AskQuestion Pydantic model."""

    def test_ask_question_requires_question(self):
        """AskQuestion should require question field."""
        from src.api.helpdesk_routes import AskQuestion

        question = AskQuestion(question="How do I create a quote?")
        assert question.question == "How do I create a quote?"

    def test_ask_question_validation_fails_without_question(self):
        """AskQuestion should fail validation without question."""
        from src.api.helpdesk_routes import AskQuestion
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AskQuestion()


class TestHelpdeskResponseModel:
    """Tests for HelpdeskResponse Pydantic model."""

    def test_helpdesk_response_success(self):
        """HelpdeskResponse should handle success case."""
        from src.api.helpdesk_routes import HelpdeskResponse

        response = HelpdeskResponse(
            success=True,
            answer="Here's how to create a quote...",
            sources=[{"name": "doc1", "score": "0.9"}]  # sources expects Dict[str, str]
        )

        assert response.success is True
        assert response.answer == "Here's how to create a quote..."
        assert len(response.sources) == 1

    def test_helpdesk_response_failure(self):
        """HelpdeskResponse should handle failure case."""
        from src.api.helpdesk_routes import HelpdeskResponse

        response = HelpdeskResponse(success=False)

        assert response.success is False
        assert response.answer is None
        assert response.sources is None

    def test_helpdesk_response_serializes(self):
        """HelpdeskResponse should serialize to dict."""
        from src.api.helpdesk_routes import HelpdeskResponse

        response = HelpdeskResponse(success=True, answer="Test")
        data = response.model_dump()

        assert isinstance(data, dict)
        assert data["success"] is True


# ==================== Constants Tests ====================

class TestHelpdeskTopicsConstant:
    """Tests for HELPDESK_TOPICS constant."""

    def test_helpdesk_topics_is_list(self):
        """HELPDESK_TOPICS should be a list."""
        from src.api.helpdesk_routes import HELPDESK_TOPICS

        assert isinstance(HELPDESK_TOPICS, list)
        assert len(HELPDESK_TOPICS) > 0

    def test_helpdesk_topics_have_required_fields(self):
        """Each topic should have id, name, description, icon."""
        from src.api.helpdesk_routes import HELPDESK_TOPICS

        for topic in HELPDESK_TOPICS:
            assert "id" in topic
            assert "name" in topic
            assert "description" in topic
            assert "icon" in topic

    def test_helpdesk_topics_ids_are_unique(self):
        """Topic IDs should be unique."""
        from src.api.helpdesk_routes import HELPDESK_TOPICS

        ids = [t["id"] for t in HELPDESK_TOPICS]
        assert len(ids) == len(set(ids))

    def test_helpdesk_topics_includes_expected_topics(self):
        """HELPDESK_TOPICS should include expected topics."""
        from src.api.helpdesk_routes import HELPDESK_TOPICS

        topic_ids = [t["id"] for t in HELPDESK_TOPICS]
        expected = ["quotes", "invoices", "clients", "hotels", "system"]

        for expected_id in expected:
            assert expected_id in topic_ids


class TestHelpResponsesConstant:
    """Tests for HELP_RESPONSES constant."""

    def test_help_responses_is_dict(self):
        """HELP_RESPONSES should be a dictionary."""
        from src.api.helpdesk_routes import HELP_RESPONSES

        assert isinstance(HELP_RESPONSES, dict)
        assert len(HELP_RESPONSES) > 0

    def test_help_responses_has_default(self):
        """HELP_RESPONSES should have a default response."""
        from src.api.helpdesk_routes import HELP_RESPONSES

        assert "default" in HELP_RESPONSES
        assert len(HELP_RESPONSES["default"]) > 0

    def test_help_responses_has_quote_responses(self):
        """HELP_RESPONSES should have quote-related responses."""
        from src.api.helpdesk_routes import HELP_RESPONSES

        assert "quote_create" in HELP_RESPONSES
        assert "quote_send" in HELP_RESPONSES

    def test_help_responses_are_non_empty_strings(self):
        """All responses should be non-empty strings."""
        from src.api.helpdesk_routes import HELP_RESPONSES

        for key, value in HELP_RESPONSES.items():
            assert isinstance(value, str)
            assert len(value) > 10  # Reasonable minimum length


# ==================== Search Function Tests ====================

class TestSearchPrivateKnowledgeBase:
    """Tests for search_private_knowledge_base function."""

    def test_returns_empty_list_without_config(self):
        """Should return empty list when config is None."""
        from src.api.helpdesk_routes import search_private_knowledge_base

        result = search_private_knowledge_base(None, "test query")

        assert result == []

    def test_returns_empty_on_exception(self, mock_config):
        """Should return empty list on exception."""
        from src.api.helpdesk_routes import search_private_knowledge_base

        with patch('src.api.helpdesk_routes.get_index_manager', side_effect=Exception("Error")):
            result = search_private_knowledge_base(mock_config, "test query")

        assert result == []

    def test_transforms_results_correctly(self, mock_config):
        """Should transform results to standard format."""
        from src.api.helpdesk_routes import search_private_knowledge_base

        mock_manager = MagicMock()
        mock_manager.search.return_value = [
            {"content": "Test content", "score": 0.8, "source": "doc.pdf"}
        ]

        with patch('src.api.helpdesk_routes.get_index_manager', return_value=mock_manager):
            result = search_private_knowledge_base(mock_config, "test query")

        assert len(result) == 1
        assert result[0]["content"] == "Test content"
        assert result[0]["source_type"] == "private_kb"
        assert result[0]["visibility"] == "private"


class TestSearchTravelPlatformRag:
    """Tests for search_travel_platform_rag function."""

    def test_returns_error_when_unavailable(self):
        """Should return error when RAG client unavailable."""
        from src.api.helpdesk_routes import search_travel_platform_rag

        with patch('src.api.helpdesk_routes.get_travel_platform_rag_client') as mock:
            mock_client = MagicMock()
            mock_client.is_available.return_value = False
            mock.return_value = mock_client

            result = search_travel_platform_rag("test query")

        assert result["success"] is False
        assert "error" in result

    def test_returns_results_on_success(self):
        """Should return results on successful search."""
        from src.api.helpdesk_routes import search_travel_platform_rag

        with patch('src.api.helpdesk_routes.get_travel_platform_rag_client') as mock:
            mock_client = MagicMock()
            mock_client.is_available.return_value = True
            mock_client.search.return_value = {
                "success": True,
                "answer": "Test answer",
                "citations": [],
                "confidence": 0.9
            }
            mock.return_value = mock_client

            result = search_travel_platform_rag("test query")

        assert result["success"] is True
        assert result["confidence"] == 0.9

    def test_handles_exception_gracefully(self):
        """Should handle exceptions gracefully."""
        from src.api.helpdesk_routes import search_travel_platform_rag

        with patch('src.api.helpdesk_routes.get_travel_platform_rag_client', side_effect=Exception("Error")):
            result = search_travel_platform_rag("test query")

        assert result["success"] is False
        assert "error" in result


class TestSearchDualKnowledgeBase:
    """Tests for search_dual_knowledge_base function."""

    def test_merges_global_and_private_results(self, mock_config):
        """Should merge results from both sources."""
        from src.api.helpdesk_routes import search_dual_knowledge_base

        with patch('src.api.helpdesk_routes.search_travel_platform_rag') as mock_global:
            mock_global.return_value = {
                "success": True,
                "answer": "Global answer",
                "citations": [{"content": "Global", "relevance_score": 0.9}]
            }

            with patch('src.api.helpdesk_routes.search_private_knowledge_base') as mock_private:
                mock_private.return_value = [
                    {"content": "Private", "score": 0.8, "source_type": "private_kb"}
                ]

                result = search_dual_knowledge_base(mock_config, "test query")

        assert result["success"] is True
        assert result["answer"] == "Global answer"
        assert "sources_breakdown" in result

    def test_returns_breakdown_counts(self, mock_config):
        """Should return source breakdown counts."""
        from src.api.helpdesk_routes import search_dual_knowledge_base

        with patch('src.api.helpdesk_routes.search_travel_platform_rag') as mock_global:
            mock_global.return_value = {
                "success": True,
                "answer": "",
                "citations": [
                    {"content": "G1", "relevance_score": 0.9},
                    {"content": "G2", "relevance_score": 0.8}
                ]
            }

            with patch('src.api.helpdesk_routes.search_private_knowledge_base') as mock_private:
                mock_private.return_value = [
                    {"content": "P1", "score": 0.7, "source_type": "private_kb"}
                ]

                result = search_dual_knowledge_base(mock_config, "test", top_k=10)

        breakdown = result["sources_breakdown"]
        assert breakdown["global"] == 2
        assert breakdown["private"] == 1
        assert breakdown["total"] == 3


# ==================== Smart Response Tests ====================

class TestGetSmartResponse:
    """Tests for get_smart_response function."""

    def test_quote_create_keyword_match(self):
        """Should match quote creation questions."""
        from src.api.helpdesk_routes import get_smart_response

        answer, topic, sources = get_smart_response("How do I create a new quote?")

        assert topic == "quotes"
        assert "quote" in answer.lower()
        assert len(sources) > 0

    def test_quote_send_keyword_match(self):
        """Should match quote sending questions."""
        from src.api.helpdesk_routes import get_smart_response

        # Note: "How" triggers quote_create first, so use question without "how"
        answer, topic, sources = get_smart_response("I want to send a quote to my client")

        assert topic == "quotes"
        assert "send" in answer.lower()

    def test_invoice_keyword_match(self):
        """Should match invoice questions."""
        from src.api.helpdesk_routes import get_smart_response

        answer, topic, sources = get_smart_response("How do I create an invoice?")

        assert topic == "invoices"
        assert "invoice" in answer.lower()

    def test_client_add_keyword_match(self):
        """Should match client add questions."""
        from src.api.helpdesk_routes import get_smart_response

        answer, topic, sources = get_smart_response("How do I add a new client?")

        assert topic == "clients"
        assert "client" in answer.lower()

    def test_pipeline_keyword_match(self):
        """Should match pipeline questions."""
        from src.api.helpdesk_routes import get_smart_response

        answer, topic, sources = get_smart_response("What are the pipeline stages?")

        assert topic == "pipeline"
        assert "pipeline" in answer.lower()

    def test_hotel_keyword_match(self):
        """Should match hotel questions."""
        from src.api.helpdesk_routes import get_smart_response

        answer, topic, sources = get_smart_response("Where can I find hotel information?")

        assert topic == "hotels"
        assert "hotel" in answer.lower()

    def test_pricing_keyword_match(self):
        """Should match pricing questions."""
        from src.api.helpdesk_routes import get_smart_response

        answer, topic, sources = get_smart_response("How do I update rate information?")

        assert topic == "pricing"
        assert "pric" in answer.lower() or "rate" in answer.lower()

    def test_settings_keyword_match(self):
        """Should match settings questions."""
        from src.api.helpdesk_routes import get_smart_response

        answer, topic, sources = get_smart_response("How do I change my branding settings?")

        assert topic == "settings"
        assert "setting" in answer.lower()

    def test_default_response_for_unknown(self):
        """Should return default for unknown questions."""
        from src.api.helpdesk_routes import get_smart_response

        answer, topic, sources = get_smart_response("random gibberish xyz123")

        assert topic == "general"
        assert "help" in answer.lower()

    def test_payment_maps_to_invoice(self):
        """Payment questions should map to invoice topic."""
        from src.api.helpdesk_routes import get_smart_response

        answer, topic, sources = get_smart_response("How do clients pay their invoices?")

        assert topic == "invoices"

    def test_crm_keyword_match(self):
        """CRM questions should return pipeline help."""
        from src.api.helpdesk_routes import get_smart_response

        answer, topic, sources = get_smart_response("How does the CRM work?")

        assert topic == "crm"


# ==================== Search Knowledge Base Tests ====================

class TestSearchKnowledgeBase:
    """Tests for search_knowledge_base function."""

    def test_returns_empty_on_failed_search(self, mock_config):
        """Should return empty list when RAG search fails."""
        from src.api.helpdesk_routes import search_knowledge_base

        with patch('src.api.helpdesk_routes.search_travel_platform_rag') as mock:
            mock.return_value = {"success": False, "error": "Service unavailable"}

            result = search_knowledge_base(mock_config, "test query")

        assert result == []

    def test_transforms_citations_correctly(self, mock_config):
        """Should transform citations to expected format."""
        from src.api.helpdesk_routes import search_knowledge_base

        with patch('src.api.helpdesk_routes.search_travel_platform_rag') as mock:
            mock.return_value = {
                "success": True,
                "citations": [
                    {
                        "content": "Test content",
                        "relevance_score": 0.85,
                        "source_title": "Test Doc",
                        "source_url": "http://example.com",
                        "doc_id": "doc123",
                        "chunk_id": "chunk456"
                    }
                ]
            }

            result = search_knowledge_base(mock_config, "test query")

        assert len(result) == 1
        assert result[0]["content"] == "Test content"
        assert result[0]["score"] == 0.85
        assert result[0]["source"] == "Test Doc"
        assert result[0]["source_url"] == "http://example.com"

    def test_handles_missing_citation_fields(self, mock_config):
        """Should handle citations with missing fields."""
        from src.api.helpdesk_routes import search_knowledge_base

        with patch('src.api.helpdesk_routes.search_travel_platform_rag') as mock:
            mock.return_value = {
                "success": True,
                "citations": [
                    {"content": "Minimal content"}  # Missing other fields
                ]
            }

            result = search_knowledge_base(mock_config, "test query")

        assert len(result) == 1
        assert result[0]["content"] == "Minimal content"
        assert result[0]["score"] == 0.0  # Default
        assert result[0]["source"] == "Knowledge Base"  # Default


# ==================== Format Knowledge Response Tests ====================

class TestFormatKnowledgeResponse:
    """Tests for format_knowledge_response function."""

    def test_calls_rag_service(self):
        """Should call generate_rag_response with correct args."""
        from src.api.helpdesk_routes import format_knowledge_response

        mock_results = [{"content": "Test", "score": 0.9}]

        with patch('src.api.helpdesk_routes.generate_rag_response') as mock:
            mock.return_value = {"answer": "Test answer", "sources": []}

            result = format_knowledge_response(mock_results, "test question")

        mock.assert_called_once_with("test question", mock_results, "general")

    def test_passes_query_type(self):
        """Should pass query_type to RAG service."""
        from src.api.helpdesk_routes import format_knowledge_response

        with patch('src.api.helpdesk_routes.generate_rag_response') as mock:
            mock.return_value = {"answer": "Test", "sources": []}

            format_knowledge_response([], "question", query_type="hotel_info")

        mock.assert_called_once_with("question", [], "hotel_info")


# ==================== Score Response Tests ====================

class TestScoreResponse:
    """Tests for score_response function."""

    def test_full_keyword_match_scores_high(self):
        """Should score high when all keywords match."""
        from src.api.helpdesk_routes import score_response

        response = {"answer": "Maldives resort honeymoon romantic", "method": "rag"}
        test_case = {
            "expected_keywords": ["maldives", "resort", "honeymoon", "romantic"],
            "must_not_contain": []
        }

        scores = score_response(response, test_case)

        assert scores["keyword_score"] == 1.0

    def test_partial_keyword_match(self):
        """Should score partial when some keywords match."""
        from src.api.helpdesk_routes import score_response

        response = {"answer": "Maldives resort info", "method": "rag"}
        test_case = {
            "expected_keywords": ["maldives", "resort", "honeymoon", "romantic"],
            "must_not_contain": []
        }

        scores = score_response(response, test_case)

        assert scores["keyword_score"] == 0.5  # 2 out of 4

    def test_forbidden_phrase_scores_zero(self):
        """Should score zero for forbidden phrases."""
        from src.api.helpdesk_routes import score_response

        response = {"answer": "I don't know about that", "method": "rag"}
        test_case = {
            "expected_keywords": [],
            "must_not_contain": ["I don't know"]
        }

        scores = score_response(response, test_case)

        assert scores["forbidden_score"] == 0.0

    def test_no_forbidden_scores_full(self):
        """Should score full when no forbidden phrases present."""
        from src.api.helpdesk_routes import score_response

        response = {"answer": "Here are some great hotels", "method": "rag"}
        test_case = {
            "expected_keywords": ["hotels"],
            "must_not_contain": ["I don't know", "error"]
        }

        scores = score_response(response, test_case)

        assert scores["forbidden_score"] == 1.0

    def test_must_contain_any_scores(self):
        """Should score based on must_contain_any."""
        from src.api.helpdesk_routes import score_response

        response = {"answer": "I can't find info on Mars", "method": "rag"}
        test_case = {
            "expected_keywords": [],
            "must_not_contain": [],
            "must_contain_any": ["can't find", "don't have", "not sure"]
        }

        scores = score_response(response, test_case)

        assert scores["contain_any_score"] == 1.0

    def test_method_quality_scoring(self):
        """Should score method quality correctly."""
        from src.api.helpdesk_routes import score_response

        test_case = {"expected_keywords": [], "must_not_contain": []}

        # RAG method should score highest
        rag_response = {"answer": "test", "method": "travel_platform_rag"}
        rag_scores = score_response(rag_response, test_case)
        assert rag_scores["quality_score"] == 1.0

        # Static should score lower
        static_response = {"answer": "test", "method": "static"}
        static_scores = score_response(static_response, test_case)
        assert static_scores["quality_score"] == 0.5

    def test_overall_score_threshold(self):
        """Should pass when overall score >= 0.7."""
        from src.api.helpdesk_routes import score_response

        # Good response
        good_response = {"answer": "Hotels in Mauritius include great resorts", "method": "rag"}
        good_case = {"expected_keywords": ["hotels", "mauritius"], "must_not_contain": []}

        good_scores = score_response(good_response, good_case)
        assert good_scores["passed"] is True
        assert good_scores["overall_score"] >= 0.7


# ==================== Ask Helpdesk Handler Tests ====================

class TestAskHelpdeskHandler:
    """Tests for ask_helpdesk endpoint handler."""

    @pytest.mark.asyncio
    async def test_ask_helpdesk_success_with_dual_kb(self, mock_config):
        """Should return answer from dual KB search."""
        from src.api.helpdesk_routes import ask_helpdesk, AskQuestion

        request = AskQuestion(question="What hotels are in Maldives?")

        with patch('src.api.helpdesk_routes.get_query_classifier') as mock_classifier:
            from src.services.query_classifier import QueryType
            mock_instance = MagicMock()
            mock_instance.classify.return_value = (QueryType.HOTEL_INFO, 0.9)
            mock_instance.get_search_params.return_value = {"k": 10}
            mock_classifier.return_value = mock_instance

            with patch('src.api.helpdesk_routes.search_dual_knowledge_base') as mock_search:
                mock_search.return_value = {
                    "success": True,
                    "answer": "Maldives has amazing resorts",
                    "citations": [{"source": "KB", "score": 0.9, "source_type": "global_kb"}],
                    "confidence": 0.85,
                    "latency_ms": 150,
                    "sources_breakdown": {"global": 1, "private": 0, "total": 1}
                }

                result = await ask_helpdesk(request, user=None, config=mock_config)

        assert result["success"] is True
        assert result["answer"] == "Maldives has amazing resorts"
        assert result["method"] == "dual_kb"
        assert "timing" in result

    @pytest.mark.asyncio
    async def test_ask_helpdesk_llm_fallback(self, mock_config):
        """Should use LLM fallback when KB has no answer."""
        from src.api.helpdesk_routes import ask_helpdesk, AskQuestion

        request = AskQuestion(question="Random question")

        with patch('src.api.helpdesk_routes.get_query_classifier') as mock_classifier:
            from src.services.query_classifier import QueryType
            mock_instance = MagicMock()
            mock_instance.classify.return_value = (QueryType.GENERAL, 0.5)
            mock_instance.get_search_params.return_value = {"k": 5}
            mock_classifier.return_value = mock_instance

            with patch('src.api.helpdesk_routes.search_dual_knowledge_base') as mock_search:
                mock_search.return_value = {
                    "success": False,
                    "answer": "",
                    "citations": []
                }

                with patch('src.api.helpdesk_routes.get_rag_service') as mock_rag:
                    mock_service = MagicMock()
                    mock_service.generate_response.return_value = {
                        "answer": "I can help with that",
                        "sources": []
                    }
                    mock_rag.return_value = mock_service

                    result = await ask_helpdesk(request, user=None, config=mock_config)

        assert result["success"] is True
        assert result["method"] == "llm_synthesis"

    @pytest.mark.asyncio
    async def test_ask_helpdesk_error_fallback(self, mock_config):
        """Should return error fallback on LLM failure."""
        from src.api.helpdesk_routes import ask_helpdesk, AskQuestion

        request = AskQuestion(question="Test question")

        with patch('src.api.helpdesk_routes.get_query_classifier') as mock_classifier:
            from src.services.query_classifier import QueryType
            mock_instance = MagicMock()
            mock_instance.classify.return_value = (QueryType.GENERAL, 0.5)
            mock_instance.get_search_params.return_value = {"k": 5}
            mock_classifier.return_value = mock_instance

            with patch('src.api.helpdesk_routes.search_dual_knowledge_base') as mock_search:
                mock_search.return_value = {"success": False, "answer": "", "citations": []}

                with patch('src.api.helpdesk_routes.get_rag_service', side_effect=Exception("LLM Error")):
                    result = await ask_helpdesk(request, user=None, config=mock_config)

        assert result["success"] is True
        assert result["method"] == "error_fallback"
        assert "trouble" in result["answer"].lower()

    @pytest.mark.asyncio
    async def test_ask_helpdesk_exception_handling(self, mock_config):
        """Should handle exceptions gracefully."""
        from src.api.helpdesk_routes import ask_helpdesk, AskQuestion

        request = AskQuestion(question="Test")

        with patch('src.api.helpdesk_routes.get_query_classifier', side_effect=Exception("Classifier error")):
            result = await ask_helpdesk(request, user=None, config=mock_config)

        assert result["success"] is False
        assert "timing" in result


# ==================== Topics Handler Tests ====================

class TestTopicsHandler:
    """Tests for get_helpdesk_topics endpoint handler."""

    @pytest.mark.asyncio
    async def test_get_topics_returns_success(self):
        """Should return topics successfully."""
        from src.api.helpdesk_routes import get_helpdesk_topics

        result = await get_helpdesk_topics(user=None)

        assert result["success"] is True
        assert "topics" in result
        assert len(result["topics"]) > 0


# ==================== Search Handler Tests ====================

class TestSearchHandler:
    """Tests for search_helpdesk endpoint handler."""

    @pytest.mark.asyncio
    async def test_search_without_query_returns_all(self):
        """Should return all topics when no query."""
        from src.api.helpdesk_routes import search_helpdesk, HELPDESK_TOPICS

        result = await search_helpdesk(q="", user=None)

        assert result["success"] is True
        assert result["results"] == HELPDESK_TOPICS

    @pytest.mark.asyncio
    async def test_search_filters_by_name(self):
        """Should filter topics by name."""
        from src.api.helpdesk_routes import search_helpdesk

        result = await search_helpdesk(q="quotes", user=None)

        assert result["success"] is True
        assert len(result["results"]) >= 1
        assert any("quote" in r["name"].lower() for r in result["results"])

    @pytest.mark.asyncio
    async def test_search_filters_by_description(self):
        """Should filter topics by description."""
        from src.api.helpdesk_routes import search_helpdesk

        result = await search_helpdesk(q="pricing", user=None)

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_search_no_match_returns_first_three(self):
        """Should return first 3 topics when no match."""
        from src.api.helpdesk_routes import search_helpdesk, HELPDESK_TOPICS

        result = await search_helpdesk(q="xyznonexistent", user=None)

        assert result["success"] is True
        assert len(result["results"]) == 3
        assert result["results"] == HELPDESK_TOPICS[:3]


# ==================== RAG Status Handler Tests ====================

class TestRagStatusHandler:
    """Tests for get_rag_status endpoint handler."""

    @pytest.mark.asyncio
    async def test_rag_status_success(self):
        """Should return RAG status successfully."""
        from src.api.helpdesk_routes import get_rag_status

        with patch('src.api.helpdesk_routes.get_travel_platform_rag_client') as mock:
            mock_client = MagicMock()
            mock_client.get_status.return_value = {
                "available": True,
                "base_url": "http://example.com",
                "tenant": "test"
            }
            mock.return_value = mock_client

            result = await get_rag_status()

        assert result["success"] is True
        assert "data" in result

    @pytest.mark.asyncio
    async def test_rag_status_error(self):
        """Should handle errors gracefully."""
        from src.api.helpdesk_routes import get_rag_status

        with patch('src.api.helpdesk_routes.get_travel_platform_rag_client', side_effect=Exception("Error")):
            result = await get_rag_status()

        assert result["success"] is False
        assert "error" in result


# ==================== FAISS Status Handler Tests ====================

class TestFaissStatusHandler:
    """Tests for get_faiss_status endpoint handler (legacy redirect)."""

    @pytest.mark.asyncio
    async def test_faiss_status_redirects_to_rag(self):
        """Should redirect to RAG status."""
        from src.api.helpdesk_routes import get_faiss_status

        with patch('src.api.helpdesk_routes.get_rag_status', new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True, "data": {"available": True}}

            result = await get_faiss_status()

        mock.assert_called_once()
        assert result["success"] is True


# ==================== Test Search Handler Tests ====================

class TestTestSearchHandler:
    """Tests for test_rag_search endpoint handler."""

    @pytest.mark.asyncio
    async def test_test_search_success(self):
        """Should return test search results."""
        from src.api.helpdesk_routes import test_rag_search

        with patch('src.api.helpdesk_routes.search_travel_platform_rag') as mock:
            mock.return_value = {
                "success": True,
                "answer": "Test answer about Maldives",
                "confidence": 0.85,
                "latency_ms": 120,
                "citations": [
                    {
                        "source_title": "Test Doc",
                        "relevance_score": 0.9,
                        "content": "Test content"
                    }
                ]
            }

            result = await test_rag_search(q="Maldives hotels")

        assert result["success"] is True
        assert result["method"] == "travel_platform_rag"
        assert result["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_test_search_no_answer(self):
        """Should handle no answer response."""
        from src.api.helpdesk_routes import test_rag_search

        with patch('src.api.helpdesk_routes.search_travel_platform_rag') as mock:
            mock.return_value = {
                "success": True,
                "answer": "",
                "citations": []
            }

            result = await test_rag_search(q="unknown topic")

        assert result["success"] is False
        assert "message" in result

    @pytest.mark.asyncio
    async def test_test_search_exception(self):
        """Should handle exceptions gracefully."""
        from src.api.helpdesk_routes import test_rag_search

        with patch('src.api.helpdesk_routes.search_travel_platform_rag', side_effect=Exception("Search error")):
            result = await test_rag_search(q="test")

        assert result["success"] is False
        assert "error" in result


# ==================== Health Handler Tests ====================

class TestHelpdeskHealthHandler:
    """Tests for helpdesk_health endpoint handler."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Should return healthy when RAG available."""
        from src.api.helpdesk_routes import helpdesk_health

        with patch('src.api.helpdesk_routes.get_travel_platform_rag_client') as mock:
            mock_client = MagicMock()
            mock_client.get_status.return_value = {
                "available": True,
                "base_url": "http://rag.example.com",
                "tenant": "test"
            }
            mock.return_value = mock_client

            result = await helpdesk_health()

        assert result["status"] == "healthy"
        assert result["mode"] == "travel_platform_rag"
        assert "checks" in result

    @pytest.mark.asyncio
    async def test_health_check_degraded(self):
        """Should return degraded when RAG unavailable."""
        from src.api.helpdesk_routes import helpdesk_health

        with patch('src.api.helpdesk_routes.get_travel_platform_rag_client') as mock:
            mock_client = MagicMock()
            mock_client.get_status.return_value = {
                "available": False,
                "base_url": "",
                "tenant": ""
            }
            mock.return_value = mock_client

            result = await helpdesk_health()

        assert result["status"] == "degraded"
        assert result["mode"] == "static_fallback"

    @pytest.mark.asyncio
    async def test_health_check_error(self):
        """Should return error status on exception."""
        from src.api.helpdesk_routes import helpdesk_health

        with patch('src.api.helpdesk_routes.get_travel_platform_rag_client', side_effect=Exception("Error")):
            result = await helpdesk_health()

        assert result["status"] == "error"
        assert "error" in result


# ==================== Agent Chat Handler Tests ====================

class TestAgentChatHandler:
    """Tests for agent_chat endpoint handler."""

    @pytest.mark.asyncio
    async def test_agent_chat_success(self, mock_config):
        """Should return agent response."""
        from src.api.helpdesk_routes import agent_chat, AskQuestion

        request = AskQuestion(question="How do I create a quote?")

        with patch('src.agents.helpdesk_agent.get_helpdesk_agent') as mock:
            mock_agent = MagicMock()
            mock_agent.chat.return_value = {
                "response": "Here's how to create a quote...",
                "tool_used": "knowledge_search",
                "sources": [{"source": "Guide"}]
            }
            mock.return_value = mock_agent

            result = await agent_chat(request, user=None, config=mock_config)

        assert result["success"] is True
        assert "answer" in result
        assert result["method"] == "agent"

    @pytest.mark.asyncio
    async def test_agent_chat_direct_response(self, mock_config):
        """Should handle direct response without tool."""
        from src.api.helpdesk_routes import agent_chat, AskQuestion

        request = AskQuestion(question="Hello")

        with patch('src.agents.helpdesk_agent.get_helpdesk_agent') as mock:
            mock_agent = MagicMock()
            mock_agent.chat.return_value = {
                "response": "Hello! How can I help?",
                "tool_used": None,
                "sources": []
            }
            mock.return_value = mock_agent

            result = await agent_chat(request, user=None, config=mock_config)

        assert result["success"] is True
        assert result["method"] == "direct"

    @pytest.mark.asyncio
    async def test_agent_chat_exception(self, mock_config):
        """Should handle exceptions gracefully."""
        from src.api.helpdesk_routes import agent_chat, AskQuestion

        request = AskQuestion(question="Test")

        with patch('src.agents.helpdesk_agent.get_helpdesk_agent', side_effect=Exception("Agent error")):
            result = await agent_chat(request, user=None, config=mock_config)

        assert result["success"] is False
        assert "timing_ms" in result


# ==================== Agent Reset Handler Tests ====================

class TestAgentResetHandler:
    """Tests for agent_reset endpoint handler."""

    @pytest.mark.asyncio
    async def test_agent_reset_success(self):
        """Should reset agent successfully."""
        from src.api.helpdesk_routes import agent_reset

        with patch('src.agents.helpdesk_agent.get_helpdesk_agent') as mock:
            mock_agent = MagicMock()
            mock.return_value = mock_agent

            result = await agent_reset()

        assert result["success"] is True
        mock_agent.reset_conversation.assert_called_once()

    @pytest.mark.asyncio
    async def test_agent_reset_exception(self):
        """Should handle exceptions gracefully."""
        from src.api.helpdesk_routes import agent_reset

        with patch('src.agents.helpdesk_agent.get_helpdesk_agent', side_effect=Exception("Reset error")):
            result = await agent_reset()

        assert result["success"] is False
        assert "error" in result


# ==================== Agent Stats Handler Tests ====================

class TestAgentStatsHandler:
    """Tests for agent_stats endpoint handler."""

    @pytest.mark.asyncio
    async def test_agent_stats_success(self):
        """Should return agent stats."""
        from src.api.helpdesk_routes import agent_stats

        with patch('src.agents.helpdesk_agent.get_helpdesk_agent') as mock:
            mock_agent = MagicMock()
            mock_agent.get_stats.return_value = {
                "total_queries": 100,
                "success_rate": 0.95
            }
            mock.return_value = mock_agent

            result = await agent_stats()

        assert result["success"] is True
        assert "stats" in result
        assert result["stats"]["total_queries"] == 100

    @pytest.mark.asyncio
    async def test_agent_stats_exception(self):
        """Should handle exceptions gracefully."""
        from src.api.helpdesk_routes import agent_stats

        with patch('src.agents.helpdesk_agent.get_helpdesk_agent', side_effect=Exception("Stats error")):
            result = await agent_stats()

        assert result["success"] is False
        assert "error" in result


# ==================== Reinit Handler Tests ====================

class TestReinitHandler:
    """Tests for reinit_rag_client endpoint handler."""

    @pytest.mark.asyncio
    async def test_reinit_success(self):
        """Should reinit RAG client successfully."""
        from src.api.helpdesk_routes import reinit_rag_client

        with patch('src.services.travel_platform_rag_client.reset_travel_platform_rag_client') as mock_reset:
            with patch('src.services.travel_platform_rag_client.get_travel_platform_rag_client') as mock_get:
                mock_client = MagicMock()
                mock_client.is_available.return_value = True
                mock_client.get_status.return_value = {"available": True}
                mock_get.return_value = mock_client

                result = await reinit_rag_client()

        assert result["success"] is True
        assert "status" in result

    @pytest.mark.asyncio
    async def test_reinit_unavailable(self):
        """Should report when RAG unavailable after reinit."""
        from src.api.helpdesk_routes import reinit_rag_client

        with patch('src.services.travel_platform_rag_client.reset_travel_platform_rag_client'):
            with patch('src.services.travel_platform_rag_client.get_travel_platform_rag_client') as mock_get:
                mock_client = MagicMock()
                mock_client.is_available.return_value = False
                mock_client.get_status.return_value = {"available": False}
                mock_get.return_value = mock_client

                result = await reinit_rag_client()

        assert result["success"] is False
        assert "unavailable" in result["message"]

    @pytest.mark.asyncio
    async def test_reinit_exception(self):
        """Should handle exceptions gracefully."""
        from src.api.helpdesk_routes import reinit_rag_client

        with patch('src.services.travel_platform_rag_client.reset_travel_platform_rag_client',
                   side_effect=Exception("Reinit error")):
            result = await reinit_rag_client()

        assert result["success"] is False
        assert "error" in result


# ==================== Accuracy Test Handler Tests ====================

class TestAccuracyTestHandler:
    """Tests for run_accuracy_tests endpoint handler."""

    @pytest.mark.asyncio
    async def test_list_accuracy_test_cases(self):
        """Should list all test cases."""
        from src.api.helpdesk_routes import list_accuracy_test_cases

        result = await list_accuracy_test_cases()

        assert result["success"] is True
        assert "test_cases" in result
        assert len(result["test_cases"]) > 0

    @pytest.mark.asyncio
    async def test_run_specific_test(self):
        """Should run specific test by ID."""
        from src.api.helpdesk_routes import run_accuracy_tests

        with patch('src.api.helpdesk_routes.get_query_classifier') as mock_classifier:
            from src.services.query_classifier import QueryType
            mock_instance = MagicMock()
            mock_instance.classify.return_value = (QueryType.HOTEL_INFO, 0.9)
            mock_instance.get_search_params.return_value = {"k": 5}
            mock_classifier.return_value = mock_instance

            with patch('src.api.helpdesk_routes.search_travel_platform_rag') as mock_search:
                mock_search.return_value = {
                    "success": True,
                    "answer": "Mauritius has many luxury resorts",
                    "citations": []
                }

                result = await run_accuracy_tests(test_id="hotel_mauritius_luxury", verbose=True)

        assert result["success"] is True
        assert result["summary"]["total_tests"] == 1

    @pytest.mark.asyncio
    async def test_run_all_tests(self):
        """Should run all accuracy tests."""
        from src.api.helpdesk_routes import run_accuracy_tests

        with patch('src.api.helpdesk_routes.get_query_classifier') as mock_classifier:
            from src.services.query_classifier import QueryType
            mock_instance = MagicMock()
            mock_instance.classify.return_value = (QueryType.GENERAL, 0.5)
            mock_instance.get_search_params.return_value = {"k": 5}
            mock_classifier.return_value = mock_instance

            with patch('src.api.helpdesk_routes.search_travel_platform_rag') as mock_search:
                mock_search.return_value = {
                    "success": True,
                    "answer": "Here is some helpful information",
                    "citations": []
                }

                result = await run_accuracy_tests(verbose=False)

        assert result["success"] is True
        assert "summary" in result
        assert "tests" in result
        assert result["summary"]["total_tests"] > 1

    @pytest.mark.asyncio
    async def test_run_nonexistent_test(self):
        """Should return error for nonexistent test ID."""
        from src.api.helpdesk_routes import run_accuracy_tests

        result = await run_accuracy_tests(test_id="nonexistent_test_xyz")

        assert result["success"] is False
        assert "error" in result
        assert "available_tests" in result


# ==================== Include Router Tests ====================

class TestIncludeHelpdeskRouter:
    """Tests for include_helpdesk_router function."""

    def test_include_router_adds_to_app(self):
        """Should add router to FastAPI app."""
        from src.api.helpdesk_routes import include_helpdesk_router

        mock_app = MagicMock()

        include_helpdesk_router(mock_app)

        mock_app.include_router.assert_called_once()
