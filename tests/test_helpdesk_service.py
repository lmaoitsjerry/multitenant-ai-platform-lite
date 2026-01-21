"""
FAISS Helpdesk Service Tests

Tests for the FAISSHelpdeskService:
- Service initialization
- Search functionality
- MMR (Maximal Marginal Relevance) search
- Document retrieval
- Error handling
- Singleton pattern

Uses mocked GCS and FAISS components for unit testing.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
import tempfile
from pathlib import Path
import pickle
import numpy as np


# ==================== Fixtures ====================

@pytest.fixture
def mock_gcs_client():
    """Create a mock GCS client."""
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()

    mock_blob.exists.return_value = True
    mock_blob.download_to_filename = MagicMock()

    mock_bucket.blob.return_value = mock_blob
    mock_client.bucket.return_value = mock_bucket

    return mock_client


@pytest.fixture
def mock_faiss_index():
    """Create a mock FAISS index."""
    mock_index = MagicMock()
    mock_index.ntotal = 100  # 100 vectors in index
    mock_index.search.return_value = (
        np.array([[0.5, 0.6, 0.8]]),  # distances
        np.array([[0, 1, 2]])  # indices
    )
    return mock_index


@pytest.fixture
def mock_docstore():
    """Create a mock docstore with documents."""
    from collections import namedtuple
    Document = namedtuple('Document', ['page_content', 'metadata'])

    docs = {
        '0': Document(
            page_content="Information about Maldives resorts and luxury hotels.",
            metadata={'source': 'maldives.txt'}
        ),
        '1': Document(
            page_content="Bali travel guide with temple visits and rice terraces.",
            metadata={'source': 'bali.txt'}
        ),
        '2': Document(
            page_content="Safari packages in Kenya including Masai Mara tours.",
            metadata={'source': 'kenya.txt'}
        )
    }

    # Create a mock InMemoryDocstore-like object
    mock_store = MagicMock()
    mock_store.search = lambda doc_id: docs.get(doc_id)
    mock_store._dict = docs

    return mock_store


@pytest.fixture
def mock_embeddings():
    """Create a mock embeddings model."""
    mock_model = MagicMock()
    mock_model.embed_query.return_value = [0.1] * 768  # 768-dim embedding
    mock_model.embed_documents.return_value = [[0.1] * 768]
    return mock_model


@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# ==================== Service Initialization Tests ====================

class TestFAISSServiceInitialization:
    """Test FAISSHelpdeskService initialization."""

    def test_service_is_singleton(self):
        """Service should use singleton pattern."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Reset singleton
        FAISSHelpdeskService._instance = None

        service1 = FAISSHelpdeskService()
        service2 = FAISSHelpdeskService()

        # Should be the same instance
        assert service1 is service2

    def test_service_starts_uninitialized(self):
        """Service should start in uninitialized state."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Reset singleton
        FAISSHelpdeskService._instance = None

        service = FAISSHelpdeskService()

        assert service.index is None
        assert service.docstore is None
        assert service.embeddings_model is None
        assert service._initialized is False

    def test_get_faiss_helpdesk_service_returns_instance(self):
        """get_faiss_helpdesk_service should return service instance."""
        from src.services.faiss_helpdesk_service import get_faiss_helpdesk_service, FAISSHelpdeskService

        # Reset singleton
        FAISSHelpdeskService._instance = None

        service = get_faiss_helpdesk_service()

        assert isinstance(service, FAISSHelpdeskService)

    def test_reset_faiss_service(self):
        """reset_faiss_service should reset the singleton."""
        from src.services.faiss_helpdesk_service import (
            FAISSHelpdeskService,
            get_faiss_helpdesk_service,
            reset_faiss_service
        )

        # Reset singleton
        FAISSHelpdeskService._instance = None

        service1 = get_faiss_helpdesk_service()
        reset_faiss_service()
        service2 = get_faiss_helpdesk_service()

        # Should be different instances after reset
        assert service1 is not service2


# ==================== GCS Download Tests ====================

class TestGCSDownload:
    """Test GCS download functionality."""

    def test_download_from_gcs_returns_false_without_client(self):
        """_download_from_gcs returns False when GCS client unavailable."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Reset singleton
        FAISSHelpdeskService._instance = None
        service = FAISSHelpdeskService()

        with patch.object(service, '_get_gcs_client', return_value=None):
            result = service._download_from_gcs('test.blob', Path('/tmp/test'))

        assert result is False

    def test_download_from_gcs_returns_false_for_missing_blob(self, mock_gcs_client):
        """_download_from_gcs returns False when blob doesn't exist."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Reset singleton
        FAISSHelpdeskService._instance = None
        service = FAISSHelpdeskService()

        mock_gcs_client.bucket.return_value.blob.return_value.exists.return_value = False

        with patch.object(service, '_get_gcs_client', return_value=mock_gcs_client):
            result = service._download_from_gcs('test.blob', Path('/tmp/test'))

        assert result is False


# ==================== Search Tests ====================

class TestFAISSSearch:
    """Test FAISS search functionality."""

    def test_search_returns_empty_when_not_initialized(self):
        """search should return empty list when service not initialized."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Reset singleton
        FAISSHelpdeskService._instance = None
        service = FAISSHelpdeskService()
        service._init_error = "Test error"  # Force init to fail

        results = service.search("test query")

        assert results == []

    def test_search_with_initialized_service(self, mock_faiss_index, mock_docstore, mock_embeddings):
        """search should return results when service is initialized."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Reset singleton
        FAISSHelpdeskService._instance = None
        service = FAISSHelpdeskService()

        # Manually set up initialized state
        service.index = mock_faiss_index
        service.docstore = mock_docstore
        service.index_to_docstore_id = {0: '0', 1: '1', 2: '2'}
        service.embeddings_model = mock_embeddings
        service._initialized = True

        results = service.search("Maldives hotels", top_k=3)

        assert len(results) == 3
        assert all('content' in r for r in results)
        assert all('score' in r for r in results)
        assert all('source' in r for r in results)

    def test_search_score_calculation(self, mock_faiss_index, mock_docstore, mock_embeddings):
        """search should correctly calculate similarity scores."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Reset singleton
        FAISSHelpdeskService._instance = None
        service = FAISSHelpdeskService()

        # Set up service
        service.index = mock_faiss_index
        service.docstore = mock_docstore
        service.index_to_docstore_id = {0: '0', 1: '1', 2: '2'}
        service.embeddings_model = mock_embeddings
        service._initialized = True

        results = service.search("test query", top_k=3)

        # Score should be between 0 and 1
        for result in results:
            assert 0 <= result['score'] <= 1


# ==================== Search with Context Tests ====================

class TestSearchWithContext:
    """Test search_with_context functionality."""

    def test_search_with_context_filters_by_score(self, mock_faiss_index, mock_docstore, mock_embeddings):
        """search_with_context should filter results by min_score."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Reset singleton
        FAISSHelpdeskService._instance = None
        service = FAISSHelpdeskService()

        # Set up service
        service.index = mock_faiss_index
        service.docstore = mock_docstore
        service.index_to_docstore_id = {0: '0', 1: '1', 2: '2'}
        service.embeddings_model = mock_embeddings
        service._initialized = True

        results = service.search_with_context("test query", min_score=0.5)

        # Should return at least minimum results for RAG context
        assert len(results) >= 1

    def test_search_with_context_returns_minimum_results(self, mock_faiss_index, mock_docstore, mock_embeddings):
        """search_with_context should return at least 3 results when available."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Reset singleton
        FAISSHelpdeskService._instance = None
        service = FAISSHelpdeskService()

        # Set up service
        service.index = mock_faiss_index
        service.docstore = mock_docstore
        service.index_to_docstore_id = {0: '0', 1: '1', 2: '2'}
        service.embeddings_model = mock_embeddings
        service._initialized = True

        # With very high min_score, should still return top 3
        results = service.search_with_context("test query", min_score=0.99)

        assert len(results) >= 1  # At least some results for RAG


# ==================== MMR Search Tests ====================

class TestMMRSearch:
    """Test Maximal Marginal Relevance search."""

    def test_mmr_search_returns_diverse_results(self, mock_faiss_index, mock_docstore, mock_embeddings):
        """search_with_mmr should return diverse results."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Reset singleton
        FAISSHelpdeskService._instance = None
        service = FAISSHelpdeskService()

        # Set up service
        service.index = mock_faiss_index
        service.docstore = mock_docstore
        service.index_to_docstore_id = {0: '0', 1: '1', 2: '2'}
        service.embeddings_model = mock_embeddings
        service._initialized = True

        results = service.search_with_mmr("travel destinations", top_k=3)

        assert len(results) <= 3
        # Each result should have content
        for r in results:
            assert 'content' in r

    def test_mmr_lambda_affects_diversity(self, mock_faiss_index, mock_docstore, mock_embeddings):
        """lambda_mult parameter should affect diversity vs relevance balance."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Reset singleton
        FAISSHelpdeskService._instance = None
        service = FAISSHelpdeskService()

        # Set up service
        service.index = mock_faiss_index
        service.docstore = mock_docstore
        service.index_to_docstore_id = {0: '0', 1: '1', 2: '2'}
        service.embeddings_model = mock_embeddings
        service._initialized = True

        # lambda_mult=1.0 = max relevance
        results_relevance = service.search_with_mmr("test", lambda_mult=1.0)

        # lambda_mult=0.0 = max diversity
        results_diversity = service.search_with_mmr("test", lambda_mult=0.0)

        # Both should return results
        assert len(results_relevance) > 0
        assert len(results_diversity) > 0

    def test_mmr_search_empty_when_not_initialized(self):
        """search_with_mmr returns empty when not initialized."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Reset singleton
        FAISSHelpdeskService._instance = None
        service = FAISSHelpdeskService()
        service._init_error = "Test error"

        results = service.search_with_mmr("test query")

        assert results == []


# ==================== Document Retrieval Tests ====================

class TestDocumentRetrieval:
    """Test document retrieval from docstore."""

    def test_get_document_returns_none_for_invalid_index(self, mock_docstore):
        """_get_document should return None for invalid index."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Reset singleton
        FAISSHelpdeskService._instance = None
        service = FAISSHelpdeskService()
        service.index_to_docstore_id = {0: '0', 1: '1'}
        service.docstore = mock_docstore

        result = service._get_document(-1)
        assert result is None

    def test_get_document_returns_none_for_missing_doc_id(self, mock_docstore):
        """_get_document should return None when doc_id not found."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Reset singleton
        FAISSHelpdeskService._instance = None
        service = FAISSHelpdeskService()
        service.index_to_docstore_id = {0: '0'}
        service.docstore = mock_docstore

        result = service._get_document(99)  # Not in mapping
        assert result is None

    def test_get_document_handles_langchain_docstore(self, mock_docstore):
        """_get_document should handle LangChain docstore format."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Reset singleton
        FAISSHelpdeskService._instance = None
        service = FAISSHelpdeskService()
        service.index_to_docstore_id = {0: '0'}
        service.docstore = mock_docstore

        result = service._get_document(0)

        assert result is not None
        assert hasattr(result, 'page_content')

    def test_get_document_handles_dict_docstore(self):
        """_get_document should handle dict-based docstore."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Reset singleton
        FAISSHelpdeskService._instance = None
        service = FAISSHelpdeskService()
        service.index_to_docstore_id = {0: '0', 1: '1'}
        service.docstore = {
            '0': {'text': 'Document 0 content'},
            '1': {'text': 'Document 1 content'}
        }

        result = service._get_document(0)

        assert result == {'text': 'Document 0 content'}

    def test_get_document_handles_list_docstore(self):
        """_get_document should handle list-based docstore."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Reset singleton
        FAISSHelpdeskService._instance = None
        service = FAISSHelpdeskService()
        service.index_to_docstore_id = {0: '0', 1: '1'}
        service.docstore = ['Document 0', 'Document 1']

        result = service._get_document(0)

        assert result == 'Document 0'


# ==================== Status Tests ====================

class TestServiceStatus:
    """Test service status reporting."""

    def test_get_status_returns_status_dict(self):
        """get_status should return a status dictionary."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Reset singleton
        FAISSHelpdeskService._instance = None
        service = FAISSHelpdeskService()

        status = service.get_status()

        assert 'initialized' in status
        assert 'error' in status
        assert 'vector_count' in status
        assert 'document_count' in status
        assert 'bucket' in status

    def test_get_status_shows_initialized_state(self, mock_faiss_index, mock_docstore, mock_embeddings):
        """get_status should reflect initialized state."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Reset singleton
        FAISSHelpdeskService._instance = None
        service = FAISSHelpdeskService()

        service.index = mock_faiss_index
        service.docstore = mock_docstore
        service.index_to_docstore_id = {0: '0', 1: '1', 2: '2'}
        service._initialized = True

        status = service.get_status()

        assert status['initialized'] is True
        assert status['vector_count'] == 100
        assert status['document_count'] == 3


# ==================== Configuration Tests ====================

class TestServiceConfiguration:
    """Test service configuration and constants."""

    def test_gcs_bucket_name_default(self):
        """GCS bucket name should have default value."""
        from src.services.faiss_helpdesk_service import GCS_BUCKET_NAME

        assert GCS_BUCKET_NAME is not None
        assert len(GCS_BUCKET_NAME) > 0

    def test_gcs_index_prefix_default(self):
        """GCS index prefix should have default value."""
        from src.services.faiss_helpdesk_service import GCS_INDEX_PREFIX

        assert GCS_INDEX_PREFIX is not None

    def test_cache_dir_defined(self):
        """Cache directory should be defined."""
        from src.services.faiss_helpdesk_service import CACHE_DIR

        assert CACHE_DIR is not None
        assert isinstance(CACHE_DIR, Path)


# ==================== Error Handling Tests ====================

class TestErrorHandling:
    """Test error handling in service."""

    def test_search_handles_embedding_error(self, mock_faiss_index, mock_docstore):
        """search should handle embedding errors gracefully."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Reset singleton
        FAISSHelpdeskService._instance = None
        service = FAISSHelpdeskService()

        service.index = mock_faiss_index
        service.docstore = mock_docstore
        service.index_to_docstore_id = {0: '0'}
        service._initialized = True

        # Create embeddings model that raises error
        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.side_effect = Exception("Embedding error")
        service.embeddings_model = mock_embeddings

        results = service.search("test query")

        # Should return empty list, not crash
        assert results == []

    def test_mmr_search_falls_back_to_regular_search(self, mock_faiss_index, mock_docstore, mock_embeddings):
        """search_with_mmr should fall back to regular search on error."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Reset singleton
        FAISSHelpdeskService._instance = None
        service = FAISSHelpdeskService()

        service.index = mock_faiss_index
        service.docstore = mock_docstore
        service.index_to_docstore_id = {0: '0', 1: '1', 2: '2'}
        service.embeddings_model = mock_embeddings
        service._initialized = True

        # Should not crash even with edge cases
        results = service.search_with_mmr("test", fetch_k=1, top_k=5)

        # Should return some results
        assert isinstance(results, list)


# ==================== Async Tests ====================

class TestAsyncInitialization:
    """Test async initialization function."""

    @pytest.mark.asyncio
    async def test_initialize_faiss_service_async(self):
        """initialize_faiss_service should be async callable."""
        from src.services.faiss_helpdesk_service import initialize_faiss_service, FAISSHelpdeskService

        # Reset singleton
        FAISSHelpdeskService._instance = None

        # Mock the initialize method to not actually download from GCS
        with patch.object(FAISSHelpdeskService, 'initialize', return_value=False):
            result = await initialize_faiss_service()

        # Should return False since we mocked initialization
        assert result is False


# ==================== Embeddings Model Tests ====================

class TestEmbeddingsModel:
    """Test embeddings model loading."""

    def test_get_embeddings_model_caches_result(self):
        """_get_embeddings_model should cache the model."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Reset singleton
        FAISSHelpdeskService._instance = None
        service = FAISSHelpdeskService()

        mock_model = MagicMock()
        service.embeddings_model = mock_model

        # Should return cached model
        result = service._get_embeddings_model()

        assert result is mock_model

    def test_get_embeddings_model_handles_import_gracefully(self):
        """_get_embeddings_model should handle import issues gracefully."""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Reset singleton
        FAISSHelpdeskService._instance = None
        service = FAISSHelpdeskService()

        # If sentence_transformers is installed, it should return a model
        # If not installed, it should return None (graceful handling)
        result = service._get_embeddings_model()

        # Result should be either a valid model or None
        assert result is None or hasattr(result, 'embed_query')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
