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
import sys
from unittest.mock import patch, MagicMock
from typing import Any, Dict, List

from tests.fixtures.gcs_fixtures import create_mock_rag_corpus_response


# ==================== Module-level mocking ====================
# Create mock modules to insert into sys.modules BEFORE importing rag_tool

def _create_mock_aiplatform():
    """Create a mock google.cloud.aiplatform module."""
    mock = MagicMock()
    mock.init = MagicMock()
    return mock


def _create_mock_rag():
    """Create a mock vertexai.preview.rag module."""
    mock = MagicMock()
    mock.retrieval_query = MagicMock()
    mock.RagResource = MagicMock()
    return mock


def _create_mock_generative_models():
    """Create a mock vertexai.preview.generative_models module."""
    mock = MagicMock()
    mock.GenerativeModel = MagicMock()
    mock.Tool = MagicMock()
    return mock


def _create_mock_vertexai():
    """Create a mock vertexai module with preview submodule."""
    mock = MagicMock()
    mock.__version__ = "1.0.0"
    return mock


# Setup module mocks before any imports
_mock_aiplatform = _create_mock_aiplatform()
_mock_rag = _create_mock_rag()
_mock_generative_models = _create_mock_generative_models()
_mock_vertexai = _create_mock_vertexai()

# Pre-inject mocks into sys.modules before the test module is fully loaded
# This allows rag_tool.py to import the mocked versions
if 'vertexai' not in sys.modules:
    sys.modules['vertexai'] = _mock_vertexai
if 'vertexai.preview' not in sys.modules:
    sys.modules['vertexai.preview'] = MagicMock()
if 'vertexai.preview.rag' not in sys.modules:
    sys.modules['vertexai.preview.rag'] = _mock_rag
if 'vertexai.preview.generative_models' not in sys.modules:
    sys.modules['vertexai.preview.generative_models'] = _mock_generative_models


# Now we can safely import from rag_tool
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


@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset mocks before each test."""
    _mock_aiplatform.reset_mock()
    _mock_rag.reset_mock()
    _mock_rag.retrieval_query.reset_mock()
    _mock_rag.RagResource.reset_mock()
    yield


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

    def test_init_with_config(self, mock_client_config):
        """Tool initializes with valid ClientConfig."""
        tool = RAGTool(mock_client_config)

        assert tool.config == mock_client_config
        assert tool.corpus_id == "corpus-abc-12345"

    def test_init_missing_corpus_id(self, mock_client_config_no_corpus):
        """Warns when corpus_id not configured."""
        # Should not raise, just warn
        tool = RAGTool(mock_client_config_no_corpus)

        assert tool.corpus_id is None

    def test_init_vertex_ai_error(self, mock_client_config):
        """Handles aiplatform.init failure gracefully."""
        from google.cloud import aiplatform
        original_init = aiplatform.init
        aiplatform.init = MagicMock(side_effect=Exception("Authentication failed"))

        try:
            # Should not raise, just set corpus_id to None
            tool = RAGTool(mock_client_config)
            assert tool.corpus_id is None
        finally:
            aiplatform.init = original_init

    def test_corpus_id_from_config(self, mock_client_config):
        """Uses config.corpus_id correctly."""
        mock_client_config.corpus_id = "my-custom-corpus-456"
        tool = RAGTool(mock_client_config)

        assert tool.corpus_id == "my-custom-corpus-456"


# ==================== TestSearchKnowledgeBase ====================

class TestSearchKnowledgeBase:
    """Tests for search_knowledge_base method."""

    def test_search_returns_formatted_results(
        self, mock_client_config, mock_rag_response
    ):
        """Returns formatted string with results."""
        _mock_rag.retrieval_query.return_value = mock_rag_response
        _mock_rag.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        result = tool.search_knowledge_base("mauritius hotels")

        assert "Found 3 relevant documents" in result
        assert "Mauritius hotels" in result
        assert "Beach resort" in result

    def test_search_no_corpus_returns_message(
        self, mock_client_config_no_corpus
    ):
        """Returns 'not configured' when no corpus."""
        tool = RAGTool(mock_client_config_no_corpus)
        result = tool.search_knowledge_base("test query")

        assert "not configured" in result.lower()

    def test_search_no_results(
        self, mock_client_config, mock_response_no_contexts
    ):
        """Returns 'no relevant information' message."""
        _mock_rag.retrieval_query.return_value = mock_response_no_contexts
        _mock_rag.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        result = tool.search_knowledge_base("obscure query")

        assert "no relevant information" in result.lower()

    def test_search_with_top_k(
        self, mock_client_config, mock_rag_response
    ):
        """Respects top_k parameter."""
        _mock_rag.retrieval_query.return_value = mock_rag_response
        _mock_rag.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        tool.search_knowledge_base("test", top_k=5)

        # Verify top_k was passed to retrieval_query
        call_kwargs = _mock_rag.retrieval_query.call_args[1]
        assert call_kwargs.get('similarity_top_k') == 5

    def test_search_with_agent_type_helpdesk(
        self, mock_client_config, mock_rag_response
    ):
        """Works with helpdesk agent type."""
        _mock_rag.retrieval_query.return_value = mock_rag_response
        _mock_rag.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        result = tool.search_knowledge_base("help query", agent_type="helpdesk")

        assert "Found" in result

    def test_search_with_agent_type_inbound(
        self, mock_client_config, mock_rag_response
    ):
        """Works with inbound agent type."""
        _mock_rag.retrieval_query.return_value = mock_rag_response
        _mock_rag.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        result = tool.search_knowledge_base("inbound query", agent_type="inbound")

        assert "Found" in result

    def test_search_handles_error(
        self, mock_client_config
    ):
        """Returns error message on exception."""
        _mock_rag.retrieval_query.side_effect = Exception("Network error")
        _mock_rag.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        result = tool.search_knowledge_base("test query")

        assert "error" in result.lower()
        assert "Network error" in result

    def test_search_logs_query(
        self, mock_client_config, mock_rag_response, caplog
    ):
        """Logs search query at INFO level."""
        import logging

        _mock_rag.retrieval_query.return_value = mock_rag_response
        _mock_rag.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)

        with caplog.at_level(logging.INFO):
            tool.search_knowledge_base("mauritius hotels")

        # Check that query was logged
        log_messages = [r.message for r in caplog.records]
        assert any("mauritius hotels" in msg for msg in log_messages)


# ==================== TestFormatResults ====================

class TestFormatResults:
    """Tests for _format_results helper method."""

    def test_format_results_multiple_documents(
        self, mock_client_config, mock_rag_response
    ):
        """Formats multiple results."""
        tool = RAGTool(mock_client_config)
        result = tool._format_results(mock_rag_response.contexts, "test query")

        assert "Result 1" in result
        assert "Result 2" in result
        assert "Result 3" in result

    def test_format_results_with_source_uri(
        self, mock_client_config, mock_rag_response
    ):
        """Includes source URI from context."""
        tool = RAGTool(mock_client_config)
        result = tool._format_results(mock_rag_response.contexts, "test query")

        assert "gs://bucket/mauritius.txt" in result
        assert "gs://bucket/resorts.txt" in result

    def test_format_results_missing_text(self, mock_client_config):
        """Handles contexts without text attribute."""
        tool = RAGTool(mock_client_config)

        # Create context without 'text' attribute
        context = MagicMock(spec=['source_uri'])
        context.source_uri = "gs://bucket/test.txt"

        result = tool._format_results([context], "test query")

        # Should still include context (converted to string)
        assert "Result 1" in result

    def test_format_results_empty_list(self, mock_client_config):
        """Handles empty contexts."""
        tool = RAGTool(mock_client_config)
        result = tool._format_results([], "test query")

        assert "Found 0 relevant documents" in result


# ==================== TestSearchWithFilters ====================

class TestSearchWithFilters:
    """Tests for search_with_filters method."""

    def test_search_with_filters_basic(
        self, mock_client_config, mock_rag_response
    ):
        """Returns list of dicts."""
        _mock_rag.retrieval_query.return_value = mock_rag_response
        _mock_rag.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        results = tool.search_with_filters("test query")

        assert isinstance(results, list)
        assert len(results) == 3
        assert all(isinstance(r, dict) for r in results)

    def test_search_with_filters_empty_results(
        self, mock_client_config, mock_empty_response
    ):
        """Returns empty list."""
        _mock_rag.retrieval_query.return_value = mock_empty_response
        _mock_rag.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        results = tool.search_with_filters("no results query")

        assert results == []

    def test_search_with_filters_error(
        self, mock_client_config
    ):
        """Returns empty list on error."""
        _mock_rag.retrieval_query.side_effect = Exception("API Error")
        _mock_rag.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        results = tool.search_with_filters("test query")

        assert results == []

    def test_search_respects_top_k(
        self, mock_client_config, mock_rag_response
    ):
        """Limits results to top_k."""
        _mock_rag.retrieval_query.return_value = mock_rag_response
        _mock_rag.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        tool.search_with_filters("test", top_k=3)

        call_kwargs = _mock_rag.retrieval_query.call_args[1]
        assert call_kwargs.get('similarity_top_k') == 3

    def test_search_with_filters_result_structure(
        self, mock_client_config, mock_rag_response
    ):
        """Results have content and source fields."""
        _mock_rag.retrieval_query.return_value = mock_rag_response
        _mock_rag.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        results = tool.search_with_filters("test")

        for result in results:
            assert 'content' in result
            assert 'source' in result


# ==================== TestRAGResourceConstruction ====================

class TestRAGResourceConstruction:
    """Tests for RAG resource path construction."""

    def test_rag_resource_path_format(
        self, mock_client_config, mock_rag_response
    ):
        """Constructs correct RAG corpus resource path."""
        _mock_rag.retrieval_query.return_value = mock_rag_response

        tool = RAGTool(mock_client_config)
        tool.search_knowledge_base("test")

        # Verify RagResource was constructed with correct path
        call_kwargs = _mock_rag.RagResource.call_args[1]
        rag_corpus = call_kwargs.get('rag_corpus', '')

        assert "test-project-123" in rag_corpus
        assert "us-central1" in rag_corpus
        assert "corpus-abc-12345" in rag_corpus


# ==================== TestEdgeCases ====================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_query(self, mock_client_config_no_corpus):
        """Handles empty query string."""
        tool = RAGTool(mock_client_config_no_corpus)
        result = tool.search_knowledge_base("")

        # Should return not configured message (no corpus)
        assert "not configured" in result.lower()

    def test_special_characters_in_query(
        self, mock_client_config, mock_rag_response
    ):
        """Handles special characters in query."""
        _mock_rag.retrieval_query.return_value = mock_rag_response
        _mock_rag.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        result = tool.search_knowledge_base("hotels & resorts <tag> 'quoted'")

        assert "Found" in result

    def test_unicode_query(
        self, mock_client_config, mock_rag_response
    ):
        """Handles unicode characters in query."""
        _mock_rag.retrieval_query.return_value = mock_rag_response
        _mock_rag.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        result = tool.search_knowledge_base("hotels in Muenchen")

        assert "Found" in result

    def test_none_response(
        self, mock_client_config
    ):
        """Handles None response from RAG."""
        _mock_rag.retrieval_query.return_value = None
        _mock_rag.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        result = tool.search_knowledge_base("test")

        assert "no relevant information" in result.lower()

    def test_very_long_query(
        self, mock_client_config, mock_rag_response
    ):
        """Handles very long query string."""
        _mock_rag.retrieval_query.return_value = mock_rag_response
        _mock_rag.RagResource.return_value = MagicMock(rag_corpus="test-corpus")

        tool = RAGTool(mock_client_config)
        long_query = "hotels " * 100
        result = tool.search_knowledge_base(long_query)

        assert "Found" in result
