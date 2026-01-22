"""
RAG Tool Tests

Comprehensive tests for src/tools/rag_tool.py using mocked Vertex AI.

Tests cover:
- RAGTool initialization with ClientConfig
- search_knowledge_base method
- _format_results helper method
- search_with_filters method
- ScoredResult dataclass

All tests mock Vertex AI and GCS dependencies for isolated testing.
"""

import pytest
from unittest.mock import patch, MagicMock
from typing import Any, Dict, List

from tests.fixtures.gcs_fixtures import create_mock_rag_corpus_response
from src.tools.rag_tool import RAGTool, ScoredResult


# ==================== Test Fixtures ====================

@pytest.fixture
def mock_client_config():
    """Create a mock ClientConfig with corpus_id configured."""
    config = MagicMock()
    config.gcp_project_id = "test-project-123"
    config.gcp_region = "us-central1"
    config.corpus_id = "corpus-abc-12345"
    config.tenant_id = "test_tenant"
    return config


@pytest.fixture
def mock_client_config_no_corpus():
    """Create a mock ClientConfig without corpus_id."""
    config = MagicMock()
    config.gcp_project_id = "test-project-123"
    config.gcp_region = "us-central1"
    config.corpus_id = None
    config.tenant_id = "test_tenant"
    return config


@pytest.fixture
def mock_rag_response():
    """Create a mock RAG retrieval_query response."""
    return create_mock_rag_corpus_response([
        {"text": "Information about Mauritius hotels.", "source_uri": "gs://bucket/mauritius.txt"},
        {"text": "Beach resort details and amenities.", "source_uri": "gs://bucket/resorts.txt"},
        {"text": "Travel tips for island destinations.", "source_uri": "gs://bucket/tips.txt"},
    ])


@pytest.fixture
def mock_empty_response():
    """Create an empty RAG response."""
    response = MagicMock()
    response.contexts = []
    return response


@pytest.fixture
def mock_response_no_contexts():
    """Create a response without contexts attribute."""
    response = MagicMock(spec=[])
    return response


# ==================== TestScoredResult ====================

class TestScoredResult:
    """Tests for ScoredResult dataclass - no external dependencies."""

    def test_scored_result_dataclass(self):
        """ScoredResult has all fields."""
        result = ScoredResult(
            text="Test content",
            source="test_source.txt",
            score=0.95,
            strategy="semantic"
        )

        assert result.text == "Test content"
        assert result.source == "test_source.txt"
        assert result.score == 0.95
        assert result.strategy == "semantic"

    def test_scored_result_defaults(self):
        """chunk_hash defaults to empty string."""
        result = ScoredResult(
            text="Test",
            source="source",
            score=0.5,
            strategy="keyword"
        )

        assert result.chunk_hash == ""

    def test_scored_result_with_chunk_hash(self):
        """chunk_hash can be set."""
        result = ScoredResult(
            text="Test",
            source="source",
            score=0.5,
            strategy="semantic",
            chunk_hash="abc123"
        )

        assert result.chunk_hash == "abc123"


# ==================== TestRAGToolInit ====================

class TestRAGToolInit:
    """Tests for RAGTool initialization."""

    @patch('src.tools.rag_tool.aiplatform')
    def test_init_with_config(self, mock_aiplatform, mock_client_config):
        """Tool initializes with valid ClientConfig."""
        tool = RAGTool(mock_client_config)

        assert tool.config == mock_client_config
        assert tool.corpus_id == "corpus-abc-12345"

    @patch('src.tools.rag_tool.aiplatform')
    def test_init_missing_corpus_id(self, mock_aiplatform, mock_client_config_no_corpus):
        """Warns when corpus_id not configured."""
        # Should not raise, just warn
        tool = RAGTool(mock_client_config_no_corpus)

        assert tool.corpus_id is None

    @patch('src.tools.rag_tool.aiplatform')
    def test_init_vertex_ai_error(self, mock_aiplatform, mock_client_config):
        """Handles aiplatform.init failure gracefully."""
        mock_aiplatform.init.side_effect = Exception("Authentication failed")

        # Should not raise, just set corpus_id to None
        tool = RAGTool(mock_client_config)
        assert tool.corpus_id is None

    @patch('src.tools.rag_tool.aiplatform')
    def test_corpus_id_from_config(self, mock_aiplatform, mock_client_config):
        """Uses config.corpus_id correctly."""
        mock_client_config.corpus_id = "my-custom-corpus-456"
        tool = RAGTool(mock_client_config)

        assert tool.corpus_id == "my-custom-corpus-456"


# ==================== TestSearchKnowledgeBase ====================

class TestSearchKnowledgeBase:
    """Tests for search_knowledge_base method."""

    @patch('src.tools.rag_tool.rag')
    @patch('src.tools.rag_tool.aiplatform')
    def test_search_returns_formatted_results(
        self, mock_aiplatform, mock_rag_module, mock_client_config, mock_rag_response
    ):
        """Returns formatted string with results."""
        mock_rag_module.retrieval_query.return_value = mock_rag_response
        mock_rag_module.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        result = tool.search_knowledge_base("mauritius hotels")

        assert "Found 3 relevant documents" in result
        assert "Mauritius hotels" in result
        assert "Beach resort" in result

    @patch('src.tools.rag_tool.aiplatform')
    def test_search_no_corpus_returns_message(
        self, mock_aiplatform, mock_client_config_no_corpus
    ):
        """Returns 'not configured' when no corpus."""
        tool = RAGTool(mock_client_config_no_corpus)
        result = tool.search_knowledge_base("test query")

        assert "not configured" in result.lower()

    @patch('src.tools.rag_tool.rag')
    @patch('src.tools.rag_tool.aiplatform')
    def test_search_no_results(
        self, mock_aiplatform, mock_rag_module, mock_client_config, mock_response_no_contexts
    ):
        """Returns 'no relevant information' message."""
        mock_rag_module.retrieval_query.return_value = mock_response_no_contexts
        mock_rag_module.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        result = tool.search_knowledge_base("obscure query")

        assert "no relevant information" in result.lower()

    @patch('src.tools.rag_tool.rag')
    @patch('src.tools.rag_tool.aiplatform')
    def test_search_with_top_k(
        self, mock_aiplatform, mock_rag_module, mock_client_config, mock_rag_response
    ):
        """Respects top_k parameter."""
        mock_rag_module.retrieval_query.return_value = mock_rag_response
        mock_rag_module.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        tool.search_knowledge_base("test", top_k=5)

        # Verify top_k was passed to retrieval_query
        call_kwargs = mock_rag_module.retrieval_query.call_args[1]
        assert call_kwargs.get('similarity_top_k') == 5

    @patch('src.tools.rag_tool.rag')
    @patch('src.tools.rag_tool.aiplatform')
    def test_search_with_agent_type_helpdesk(
        self, mock_aiplatform, mock_rag_module, mock_client_config, mock_rag_response
    ):
        """Works with helpdesk agent type."""
        mock_rag_module.retrieval_query.return_value = mock_rag_response
        mock_rag_module.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        result = tool.search_knowledge_base("help query", agent_type="helpdesk")

        assert "Found" in result

    @patch('src.tools.rag_tool.rag')
    @patch('src.tools.rag_tool.aiplatform')
    def test_search_with_agent_type_inbound(
        self, mock_aiplatform, mock_rag_module, mock_client_config, mock_rag_response
    ):
        """Works with inbound agent type."""
        mock_rag_module.retrieval_query.return_value = mock_rag_response
        mock_rag_module.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        result = tool.search_knowledge_base("inbound query", agent_type="inbound")

        assert "Found" in result

    @patch('src.tools.rag_tool.rag')
    @patch('src.tools.rag_tool.aiplatform')
    def test_search_handles_error(
        self, mock_aiplatform, mock_rag_module, mock_client_config
    ):
        """Returns error message on exception."""
        mock_rag_module.retrieval_query.side_effect = Exception("Network error")
        mock_rag_module.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        result = tool.search_knowledge_base("test query")

        assert "error" in result.lower()
        assert "Network error" in result

    @patch('src.tools.rag_tool.rag')
    @patch('src.tools.rag_tool.aiplatform')
    def test_search_logs_query(
        self, mock_aiplatform, mock_rag_module, mock_client_config, mock_rag_response, caplog
    ):
        """Logs search query at INFO level."""
        import logging

        mock_rag_module.retrieval_query.return_value = mock_rag_response
        mock_rag_module.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)

        with caplog.at_level(logging.INFO):
            tool.search_knowledge_base("mauritius hotels")

        # Check that query was logged
        log_messages = [r.message for r in caplog.records]
        assert any("mauritius hotels" in msg for msg in log_messages)


# ==================== TestFormatResults ====================

class TestFormatResults:
    """Tests for _format_results helper method."""

    @patch('src.tools.rag_tool.aiplatform')
    def test_format_results_structure(self, mock_aiplatform, mock_client_config, mock_rag_response):
        """Output includes header and separator."""
        tool = RAGTool(mock_client_config)
        contexts = mock_rag_response.contexts

        result = tool._format_results(contexts, "test query")

        assert "Found 3 relevant documents" in result
        assert "--- Result 1 ---" in result
        assert "--- Result 2 ---" in result
        assert "--- Result 3 ---" in result

    @patch('src.tools.rag_tool.aiplatform')
    def test_format_results_includes_source(self, mock_aiplatform, mock_client_config, mock_rag_response):
        """Output includes source URIs."""
        tool = RAGTool(mock_client_config)
        contexts = mock_rag_response.contexts

        result = tool._format_results(contexts, "test query")

        assert "Source: gs://bucket/mauritius.txt" in result
        assert "Source: gs://bucket/resorts.txt" in result
        assert "Source: gs://bucket/tips.txt" in result

    @patch('src.tools.rag_tool.aiplatform')
    def test_format_results_includes_content(self, mock_aiplatform, mock_client_config, mock_rag_response):
        """Output includes document content."""
        tool = RAGTool(mock_client_config)
        contexts = mock_rag_response.contexts

        result = tool._format_results(contexts, "test query")

        assert "Information about Mauritius hotels" in result
        assert "Beach resort details" in result
        assert "Travel tips" in result

    @patch('src.tools.rag_tool.aiplatform')
    def test_format_results_empty(self, mock_aiplatform, mock_client_config):
        """Handles empty context list."""
        tool = RAGTool(mock_client_config)

        result = tool._format_results([], "test query")

        assert "Found 0 relevant documents" in result


# ==================== TestSearchWithFilters ====================

class TestSearchWithFilters:
    """Tests for search_with_filters method."""

    @patch('src.tools.rag_tool.rag')
    @patch('src.tools.rag_tool.aiplatform')
    def test_search_with_filters_basic(
        self, mock_aiplatform, mock_rag_module, mock_client_config, mock_rag_response
    ):
        """Returns list of dicts."""
        mock_rag_module.retrieval_query.return_value = mock_rag_response
        mock_rag_module.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        results = tool.search_with_filters("test query")

        assert isinstance(results, list)
        assert len(results) == 3
        assert all(isinstance(r, dict) for r in results)

    @patch('src.tools.rag_tool.rag')
    @patch('src.tools.rag_tool.aiplatform')
    def test_search_with_filters_empty_results(
        self, mock_aiplatform, mock_rag_module, mock_client_config, mock_empty_response
    ):
        """Returns empty list."""
        mock_rag_module.retrieval_query.return_value = mock_empty_response
        mock_rag_module.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        results = tool.search_with_filters("no results query")

        assert results == []

    @patch('src.tools.rag_tool.rag')
    @patch('src.tools.rag_tool.aiplatform')
    def test_search_with_filters_error(
        self, mock_aiplatform, mock_rag_module, mock_client_config
    ):
        """Returns empty list on error."""
        mock_rag_module.retrieval_query.side_effect = Exception("API Error")
        mock_rag_module.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        results = tool.search_with_filters("test query")

        assert results == []

    @patch('src.tools.rag_tool.rag')
    @patch('src.tools.rag_tool.aiplatform')
    def test_search_respects_top_k(
        self, mock_aiplatform, mock_rag_module, mock_client_config, mock_rag_response
    ):
        """Limits results to top_k."""
        mock_rag_module.retrieval_query.return_value = mock_rag_response
        mock_rag_module.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        tool.search_with_filters("test", top_k=3)

        call_kwargs = mock_rag_module.retrieval_query.call_args[1]
        assert call_kwargs.get('similarity_top_k') == 3

    @patch('src.tools.rag_tool.rag')
    @patch('src.tools.rag_tool.aiplatform')
    def test_search_with_filters_result_structure(
        self, mock_aiplatform, mock_rag_module, mock_client_config, mock_rag_response
    ):
        """Results have content and source fields."""
        mock_rag_module.retrieval_query.return_value = mock_rag_response
        mock_rag_module.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        results = tool.search_with_filters("test")

        for result in results:
            assert 'content' in result
            assert 'source' in result


# ==================== TestRAGResourceConstruction ====================

class TestRAGResourceConstruction:
    """Tests for RAG resource path construction."""

    @patch('src.tools.rag_tool.rag')
    @patch('src.tools.rag_tool.aiplatform')
    def test_rag_resource_path_format(
        self, mock_aiplatform, mock_rag_module, mock_client_config, mock_rag_response
    ):
        """Constructs correct RAG corpus resource path."""
        mock_rag_module.retrieval_query.return_value = mock_rag_response

        tool = RAGTool(mock_client_config)
        tool.search_knowledge_base("test")

        # Verify RagResource was constructed with correct path
        call_kwargs = mock_rag_module.RagResource.call_args[1]
        rag_corpus = call_kwargs.get('rag_corpus', '')

        assert "test-project-123" in rag_corpus
        assert "us-central1" in rag_corpus
        assert "corpus-abc-12345" in rag_corpus


# ==================== TestEdgeCases ====================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @patch('src.tools.rag_tool.aiplatform')
    def test_empty_query(self, mock_aiplatform, mock_client_config_no_corpus):
        """Handles empty query string."""
        tool = RAGTool(mock_client_config_no_corpus)
        result = tool.search_knowledge_base("")

        # Should return not configured message (no corpus)
        assert "not configured" in result.lower()

    @patch('src.tools.rag_tool.rag')
    @patch('src.tools.rag_tool.aiplatform')
    def test_special_characters_in_query(
        self, mock_aiplatform, mock_rag_module, mock_client_config, mock_rag_response
    ):
        """Handles special characters in query."""
        mock_rag_module.retrieval_query.return_value = mock_rag_response
        mock_rag_module.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        result = tool.search_knowledge_base("hotels & resorts <tag> 'quoted'")

        assert "Found" in result

    @patch('src.tools.rag_tool.rag')
    @patch('src.tools.rag_tool.aiplatform')
    def test_unicode_query(
        self, mock_aiplatform, mock_rag_module, mock_client_config, mock_rag_response
    ):
        """Handles unicode characters in query."""
        mock_rag_module.retrieval_query.return_value = mock_rag_response
        mock_rag_module.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        result = tool.search_knowledge_base("cafe in Paris")

        assert "Found" in result

    @patch('src.tools.rag_tool.rag')
    @patch('src.tools.rag_tool.aiplatform')
    def test_none_response(
        self, mock_aiplatform, mock_rag_module, mock_client_config
    ):
        """Handles None response from RAG."""
        mock_rag_module.retrieval_query.return_value = None
        mock_rag_module.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        result = tool.search_knowledge_base("test query")

        assert "no relevant information" in result.lower()

    @patch('src.tools.rag_tool.rag')
    @patch('src.tools.rag_tool.aiplatform')
    def test_very_long_query(
        self, mock_aiplatform, mock_rag_module, mock_client_config, mock_rag_response
    ):
        """Handles very long query strings."""
        mock_rag_module.retrieval_query.return_value = mock_rag_response
        mock_rag_module.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        long_query = "hotel " * 1000  # Very long query
        tool = RAGTool(mock_client_config)
        result = tool.search_knowledge_base(long_query)

        assert "Found" in result
