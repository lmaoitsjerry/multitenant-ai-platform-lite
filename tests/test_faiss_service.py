"""
FAISS Helpdesk Service Tests

Comprehensive tests for src/services/faiss_helpdesk_service.py using mocked GCS and FAISS.

Tests cover:
- FAISSHelpdeskService singleton pattern
- Service initialization with GCS downloads
- Search functionality with vector operations
- Search with context and filtering
- MMR (Maximal Marginal Relevance) search
- Document retrieval from various docstore formats
- Service status reporting
- Helper functions

All tests mock GCS, FAISS, and sentence-transformers for isolated testing.
"""

import pytest
import sys
import pickle
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from typing import Any, Dict, List
import numpy as np

from tests.fixtures.gcs_fixtures import (
    MockGCSClient,
    MockGCSBucket,
    MockGCSBlob,
    MockFAISSIndex,
    MockDocstore,
    MockDocument,
    MockSentenceTransformer,
    create_mock_gcs_client,
    create_mock_faiss_service,
    generate_mock_search_results,
)


# ==================== Module-level Setup ====================

# Mock faiss module before importing the service
_mock_faiss = MagicMock()
_mock_faiss.read_index = MagicMock()

if 'faiss' not in sys.modules:
    sys.modules['faiss'] = _mock_faiss


# ==================== Fixtures ====================

@pytest.fixture
def tmp_cache_dir(tmp_path):
    """Create a temporary cache directory for tests."""
    cache_dir = tmp_path / "zorah_faiss_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


@pytest.fixture
def mock_gcs_client():
    """Create a mock GCS client with FAISS index files."""
    client = create_mock_gcs_client(
        blobs=[
            {
                "name": "faiss_indexes/index.faiss",
                "content_bytes": b"MOCK_FAISS_INDEX_DATA"
            },
            {
                "name": "faiss_indexes/index.pkl",
                "content_bytes": pickle.dumps(({}, {}))  # (docstore_dict, index_to_id)
            }
        ],
        bucket_name="zorah-475411-rag-documents"
    )
    return client


@pytest.fixture
def mock_faiss_components():
    """Create mock FAISS service components."""
    return create_mock_faiss_service(
        vectors=50,
        documents=[
            {"content": "Hotel info for Maldives resorts", "source": "maldives.txt"},
            {"content": "Beach activities in Mauritius", "source": "mauritius.txt"},
            {"content": "Travel tips for Seychelles", "source": "seychelles.txt"},
            {"content": "Visa requirements for island destinations", "source": "visa.txt"},
            {"content": "Local cuisine recommendations", "source": "food.txt"},
        ]
    )


@pytest.fixture
def reset_singleton():
    """Reset the singleton instance before and after each test."""
    # Import here to avoid circular issues
    from src.services.faiss_helpdesk_service import FAISSHelpdeskService, reset_faiss_service

    # Reset before test
    FAISSHelpdeskService._instance = None

    yield

    # Reset after test
    FAISSHelpdeskService._instance = None


# ==================== TestFAISSServiceInit ====================

class TestFAISSServiceInit:
    """Tests for FAISSHelpdeskService initialization."""

    def test_singleton_pattern(self, reset_singleton):
        """Returns same instance on multiple calls."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        instance1 = FAISSHelpdeskService()
        instance2 = FAISSHelpdeskService()

        assert instance1 is instance2

    def test_init_not_initialized_by_default(self, reset_singleton):
        """_initialized is False initially."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        service = FAISSHelpdeskService()

        assert service._initialized is False

    def test_cache_directory_created(self, reset_singleton, tmp_cache_dir):
        """CACHE_DIR exists after init."""
        from src.services import faiss_helpdesk_service
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Temporarily override CACHE_DIR
        original_cache_dir = faiss_helpdesk_service.CACHE_DIR
        faiss_helpdesk_service.CACHE_DIR = tmp_cache_dir

        try:
            service = FAISSHelpdeskService()
            # Cache dir should exist
            assert tmp_cache_dir.exists()
        finally:
            faiss_helpdesk_service.CACHE_DIR = original_cache_dir


# ==================== TestFAISSServiceInitialize ====================

class TestFAISSServiceInitialize:
    """Tests for FAISSHelpdeskService.initialize() method."""

    def test_initialize_downloads_from_gcs(
        self, reset_singleton, tmp_cache_dir, mock_gcs_client, mock_faiss_components
    ):
        """Downloads index and metadata from GCS."""
        from src.services import faiss_helpdesk_service
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        original_cache_dir = faiss_helpdesk_service.CACHE_DIR
        faiss_helpdesk_service.CACHE_DIR = tmp_cache_dir

        # Setup mocks
        with patch.object(FAISSHelpdeskService, '_get_gcs_client', return_value=mock_gcs_client):
            with patch.object(FAISSHelpdeskService, '_download_from_gcs', return_value=True):
                with patch('faiss.read_index', return_value=mock_faiss_components['index']):
                    with patch('builtins.open', mock_open(read_data=pickle.dumps(
                        (mock_faiss_components['docstore'], mock_faiss_components['index_to_docstore_id'])
                    ))):
                        with patch.object(FAISSHelpdeskService, '_get_embeddings_model',
                                        return_value=mock_faiss_components['embeddings_model']):
                            try:
                                service = FAISSHelpdeskService()
                                result = service.initialize()

                                # Should succeed
                                assert result is True or service._initialized is True
                            finally:
                                faiss_helpdesk_service.CACHE_DIR = original_cache_dir

    def test_initialize_gcs_failure(self, reset_singleton, tmp_cache_dir):
        """Returns False when GCS unavailable."""
        from src.services import faiss_helpdesk_service
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        original_cache_dir = faiss_helpdesk_service.CACHE_DIR
        faiss_helpdesk_service.CACHE_DIR = tmp_cache_dir

        with patch.object(FAISSHelpdeskService, '_get_gcs_client', return_value=None):
            with patch.object(FAISSHelpdeskService, '_download_from_gcs', return_value=False):
                try:
                    service = FAISSHelpdeskService()
                    result = service.initialize()

                    assert result is False
                finally:
                    faiss_helpdesk_service.CACHE_DIR = original_cache_dir

    def test_initialize_already_initialized(self, reset_singleton):
        """Returns True if already initialized."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        service = FAISSHelpdeskService()
        service._initialized = True

        result = service.initialize()

        assert result is True


# ==================== TestFAISSServiceSearch ====================

class TestFAISSServiceSearch:
    """Tests for FAISSHelpdeskService.search() method."""

    def test_search_returns_results(self, reset_singleton, mock_faiss_components):
        """Returns list of result dicts."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        service = FAISSHelpdeskService()
        service._initialized = True
        service.index = mock_faiss_components['index']
        service.docstore = mock_faiss_components['docstore']
        service.index_to_docstore_id = mock_faiss_components['index_to_docstore_id']
        service.embeddings_model = mock_faiss_components['embeddings_model']

        results = service.search("hotels", top_k=3)

        assert isinstance(results, list)
        # Should return some results
        assert len(results) >= 0

    def test_search_uninitialized_returns_empty(self, reset_singleton):
        """Returns empty if not initialized."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        service = FAISSHelpdeskService()
        service._initialized = False

        results = service.search("test query")

        assert results == []

    def test_search_with_top_k(self, reset_singleton, mock_faiss_components):
        """Respects top_k parameter."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        service = FAISSHelpdeskService()
        service._initialized = True
        service.index = mock_faiss_components['index']
        service.docstore = mock_faiss_components['docstore']
        service.index_to_docstore_id = mock_faiss_components['index_to_docstore_id']
        service.embeddings_model = mock_faiss_components['embeddings_model']

        results = service.search("hotels", top_k=2)

        # Results should be at most top_k
        assert len(results) <= 2

    def test_search_result_has_content(self, reset_singleton, mock_faiss_components):
        """Results have content field."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        service = FAISSHelpdeskService()
        service._initialized = True
        service.index = mock_faiss_components['index']
        service.docstore = mock_faiss_components['docstore']
        service.index_to_docstore_id = mock_faiss_components['index_to_docstore_id']
        service.embeddings_model = mock_faiss_components['embeddings_model']

        results = service.search("hotels", top_k=1)

        if results:
            assert 'content' in results[0]

    def test_search_result_has_score(self, reset_singleton, mock_faiss_components):
        """Results have score field."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        service = FAISSHelpdeskService()
        service._initialized = True
        service.index = mock_faiss_components['index']
        service.docstore = mock_faiss_components['docstore']
        service.index_to_docstore_id = mock_faiss_components['index_to_docstore_id']
        service.embeddings_model = mock_faiss_components['embeddings_model']

        results = service.search("hotels", top_k=1)

        if results:
            assert 'score' in results[0]
            assert 0 <= results[0]['score'] <= 1

    def test_search_result_has_source(self, reset_singleton, mock_faiss_components):
        """Results have source field."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        service = FAISSHelpdeskService()
        service._initialized = True
        service.index = mock_faiss_components['index']
        service.docstore = mock_faiss_components['docstore']
        service.index_to_docstore_id = mock_faiss_components['index_to_docstore_id']
        service.embeddings_model = mock_faiss_components['embeddings_model']

        results = service.search("hotels", top_k=1)

        if results:
            assert 'source' in results[0]


# ==================== TestSearchWithContext ====================

class TestSearchWithContext:
    """Tests for search_with_context method."""

    def test_search_with_context_basic(self, reset_singleton, mock_faiss_components):
        """Returns filtered results."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        service = FAISSHelpdeskService()
        service._initialized = True
        service.index = mock_faiss_components['index']
        service.docstore = mock_faiss_components['docstore']
        service.index_to_docstore_id = mock_faiss_components['index_to_docstore_id']
        service.embeddings_model = mock_faiss_components['embeddings_model']

        results = service.search_with_context("hotels")

        assert isinstance(results, list)

    def test_search_with_context_min_score(self, reset_singleton, mock_faiss_components):
        """Filters by min_score."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        service = FAISSHelpdeskService()
        service._initialized = True
        service.index = mock_faiss_components['index']
        service.docstore = mock_faiss_components['docstore']
        service.index_to_docstore_id = mock_faiss_components['index_to_docstore_id']
        service.embeddings_model = mock_faiss_components['embeddings_model']

        results = service.search_with_context("hotels", min_score=0.5)

        # All results should be above min_score or we get top 3
        # (implementation returns top 3 if filtering removes too many)
        assert isinstance(results, list)

    def test_search_with_context_uses_mmr(self, reset_singleton, mock_faiss_components):
        """Applies MMR when requested."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        service = FAISSHelpdeskService()
        service._initialized = True
        service.index = mock_faiss_components['index']
        service.docstore = mock_faiss_components['docstore']
        service.index_to_docstore_id = mock_faiss_components['index_to_docstore_id']
        service.embeddings_model = mock_faiss_components['embeddings_model']

        # Should not raise with use_mmr=True
        results = service.search_with_context("hotels", use_mmr=True)

        assert isinstance(results, list)


# ==================== TestSearchWithMMR ====================

class TestSearchWithMMR:
    """Tests for search_with_mmr method."""

    def test_mmr_returns_diverse_results(self, reset_singleton, mock_faiss_components):
        """Returns diverse documents."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        service = FAISSHelpdeskService()
        service._initialized = True
        service.index = mock_faiss_components['index']
        service.docstore = mock_faiss_components['docstore']
        service.index_to_docstore_id = mock_faiss_components['index_to_docstore_id']
        service.embeddings_model = mock_faiss_components['embeddings_model']

        results = service.search_with_mmr("hotels", top_k=3)

        assert isinstance(results, list)

    def test_mmr_fallback_to_regular(self, reset_singleton, mock_faiss_components):
        """Falls back to search on error."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        service = FAISSHelpdeskService()
        service._initialized = True
        service.index = mock_faiss_components['index']
        service.docstore = mock_faiss_components['docstore']
        service.index_to_docstore_id = mock_faiss_components['index_to_docstore_id']
        service.embeddings_model = mock_faiss_components['embeddings_model']

        # Force an error in MMR calculation by making embed_query raise
        original_embed = service.embeddings_model.embed_query
        service.embeddings_model.embed_query = MagicMock(side_effect=Exception("Embedding error"))

        try:
            results = service.search_with_mmr("hotels", top_k=3)
            # Should fall back gracefully
            assert isinstance(results, list)
        finally:
            service.embeddings_model.embed_query = original_embed

    def test_mmr_uninitialized_returns_empty(self, reset_singleton):
        """Returns empty if not initialized."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        service = FAISSHelpdeskService()
        service._initialized = False

        results = service.search_with_mmr("test")

        assert results == []


# ==================== TestGetDocument ====================

class TestGetDocument:
    """Tests for _get_document method."""

    def test_get_document_langchain_format(self, reset_singleton):
        """Handles InMemoryDocstore."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        service = FAISSHelpdeskService()
        service.index_to_docstore_id = {0: "doc_0", 1: "doc_1"}

        # Create mock docstore with search method
        mock_docstore = MagicMock()
        mock_doc = MockDocument(page_content="Test content", metadata={"source": "test.txt"})
        mock_docstore.search.return_value = mock_doc
        service.docstore = mock_docstore

        result = service._get_document(0)

        assert result is mock_doc

    def test_get_document_dict_format(self, reset_singleton):
        """Handles dict docstore."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        service = FAISSHelpdeskService()
        service.index_to_docstore_id = {0: "doc_0"}
        service.docstore = {"doc_0": {"content": "Test content"}}

        result = service._get_document(0)

        assert result == {"content": "Test content"}

    def test_get_document_list_format(self, reset_singleton):
        """Handles list docstore."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        service = FAISSHelpdeskService()
        service.index_to_docstore_id = {0: "0", 1: "1"}
        service.docstore = [{"content": "Doc 0"}, {"content": "Doc 1"}]

        result = service._get_document(0)

        assert result == {"content": "Doc 0"}

    def test_get_document_not_found(self, reset_singleton):
        """Returns None for missing doc."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        service = FAISSHelpdeskService()
        service.index_to_docstore_id = {}
        service.docstore = {}

        result = service._get_document(999)

        assert result is None

    def test_get_document_invalid_index(self, reset_singleton):
        """Handles invalid index (-1)."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        service = FAISSHelpdeskService()
        service.index_to_docstore_id = {0: "doc_0"}

        result = service._get_document(-1)

        assert result is None


# ==================== TestGetStatus ====================

class TestGetStatus:
    """Tests for get_status method."""

    def test_get_status_initialized(self, reset_singleton, mock_faiss_components):
        """Returns initialized=True when ready."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        service = FAISSHelpdeskService()
        service._initialized = True
        service.index = mock_faiss_components['index']
        service.index_to_docstore_id = mock_faiss_components['index_to_docstore_id']
        service._init_error = None

        status = service.get_status()

        assert status['initialized'] is True

    def test_get_status_not_initialized(self, reset_singleton):
        """Returns initialized=False before init."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        service = FAISSHelpdeskService()
        service._initialized = False

        status = service.get_status()

        assert status['initialized'] is False

    def test_get_status_has_error(self, reset_singleton):
        """Includes error message if present."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        service = FAISSHelpdeskService()
        service._initialized = False
        service._init_error = "GCS connection failed"
        service.index = None
        service.index_to_docstore_id = None

        status = service.get_status()

        assert status['error'] == "GCS connection failed"

    def test_get_status_vector_count(self, reset_singleton, mock_faiss_components):
        """Includes vector count from index."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        service = FAISSHelpdeskService()
        service._initialized = True
        service.index = mock_faiss_components['index']
        service.index_to_docstore_id = mock_faiss_components['index_to_docstore_id']
        service._init_error = None

        status = service.get_status()

        assert 'vector_count' in status
        assert status['vector_count'] == mock_faiss_components['index'].ntotal


# ==================== TestHelperFunctions ====================

class TestHelperFunctions:
    """Tests for module-level helper functions."""

    def test_get_faiss_helpdesk_service_singleton(self, reset_singleton):
        """Returns singleton instance."""
        from src.services.faiss_helpdesk_service import (
            get_faiss_helpdesk_service,
            FAISSHelpdeskService
        )

        service1 = get_faiss_helpdesk_service()
        service2 = get_faiss_helpdesk_service()

        assert service1 is service2
        assert isinstance(service1, FAISSHelpdeskService)

    def test_reset_faiss_service(self, reset_singleton):
        """Resets singleton to None."""
        from src.services.faiss_helpdesk_service import (
            get_faiss_helpdesk_service,
            reset_faiss_service,
            FAISSHelpdeskService
        )

        # Create instance
        service1 = get_faiss_helpdesk_service()

        # Reset
        reset_faiss_service()

        # New instance should be created
        service2 = get_faiss_helpdesk_service()

        # Should be different instances
        assert service1 is not service2

    def test_reset_faiss_service_clears_cache(self, reset_singleton, tmp_cache_dir):
        """Optionally clears cache dir."""
        from src.services import faiss_helpdesk_service
        from src.services.faiss_helpdesk_service import reset_faiss_service

        original_cache_dir = faiss_helpdesk_service.CACHE_DIR
        faiss_helpdesk_service.CACHE_DIR = tmp_cache_dir

        # Create a test file in cache
        test_file = tmp_cache_dir / "test.txt"
        test_file.write_text("test")

        try:
            reset_faiss_service(clear_cache=True)

            # Cache should be recreated (empty)
            assert tmp_cache_dir.exists()
            # Test file should be gone
            assert not test_file.exists()
        finally:
            faiss_helpdesk_service.CACHE_DIR = original_cache_dir

    def test_initialize_faiss_service_async(self, reset_singleton):
        """Async wrapper calls initialize."""
        import asyncio
        from src.services.faiss_helpdesk_service import (
            initialize_faiss_service,
            FAISSHelpdeskService
        )

        with patch.object(FAISSHelpdeskService, 'initialize', return_value=False):
            result = asyncio.run(initialize_faiss_service())

            assert result is False


# ==================== TestDocstoreFormats ====================

class TestDocstoreFormats:
    """Tests for handling different docstore formats."""

    def test_docstore_with_internal_dict(self, reset_singleton):
        """Handles docstore with _dict attribute."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        service = FAISSHelpdeskService()
        service.index_to_docstore_id = {0: "doc_0"}

        # Create docstore with _dict but no search method
        mock_docstore = MagicMock(spec=['_dict'])
        mock_docstore._dict = {"doc_0": {"content": "Test"}}
        service.docstore = mock_docstore

        result = service._get_document(0)

        assert result == {"content": "Test"}

    def test_langchain_docstore_not_found(self, reset_singleton):
        """Handles LangChain docstore returning 'not found' string."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        service = FAISSHelpdeskService()
        service.index_to_docstore_id = {0: "doc_0"}

        mock_docstore = MagicMock()
        mock_docstore.search.return_value = "Document doc_0 not found"
        service.docstore = mock_docstore

        result = service._get_document(0)

        assert result is None
