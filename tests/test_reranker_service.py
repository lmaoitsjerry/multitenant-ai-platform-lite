"""
ReRanker Service Unit Tests

Tests for the cross-encoder re-ranking service.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestReRankerServiceInit:
    """Tests for ReRankerService initialization."""

    def test_singleton_pattern(self):
        """ReRankerService should follow singleton pattern."""
        from src.services.reranker_service import ReRankerService

        # Clear singleton for testing
        ReRankerService._instance = None

        service1 = ReRankerService()
        service2 = ReRankerService()

        assert service1 is service2

    def test_init_sets_defaults(self):
        """ReRankerService should set default values."""
        from src.services.reranker_service import ReRankerService

        ReRankerService._instance = None
        service = ReRankerService()

        assert service.model is None
        assert service._init_error is None
        assert service._initialized is True


class TestReRankerLazyInit:
    """Tests for lazy initialization of cross-encoder model."""

    def test_lazy_init_returns_false_after_import_error(self):
        """_lazy_init should return False after ImportError."""
        from src.services.reranker_service import ReRankerService

        ReRankerService._instance = None
        service = ReRankerService()

        # Simulate a previous import error
        service._init_error = "sentence-transformers not installed"

        result = service._lazy_init()

        assert result is False

    def test_lazy_init_caches_error(self):
        """_lazy_init should cache initialization error."""
        from src.services.reranker_service import ReRankerService

        ReRankerService._instance = None
        service = ReRankerService()
        service._init_error = "previous error"

        result = service._lazy_init()

        assert result is False

    def test_lazy_init_returns_true_when_model_exists(self):
        """_lazy_init should return True when model already loaded."""
        from src.services.reranker_service import ReRankerService

        ReRankerService._instance = None
        service = ReRankerService()
        service.model = MagicMock()

        result = service._lazy_init()

        assert result is True


class TestReRankerRerank:
    """Tests for rerank method."""

    def test_rerank_empty_documents(self):
        """rerank should return empty list for empty input."""
        from src.services.reranker_service import ReRankerService

        ReRankerService._instance = None
        service = ReRankerService()

        result = service.rerank("test query", [])

        assert result == []

    def test_rerank_without_model_returns_original(self):
        """rerank should return original order when model not available."""
        from src.services.reranker_service import ReRankerService

        ReRankerService._instance = None
        service = ReRankerService()
        service._init_error = "not available"

        documents = [
            {"content": "doc1", "score": 0.8},
            {"content": "doc2", "score": 0.7},
            {"content": "doc3", "score": 0.6},
        ]

        result = service.rerank("query", documents, top_k=2)

        assert len(result) == 2
        assert result[0]["content"] == "doc1"
        assert result[1]["content"] == "doc2"

    def test_rerank_with_model(self):
        """rerank should use model when available."""
        from src.services.reranker_service import ReRankerService

        ReRankerService._instance = None
        service = ReRankerService()

        mock_model = MagicMock()
        mock_model.predict.return_value = [0.3, 0.9, 0.5]
        service.model = mock_model

        documents = [
            {"content": "doc1", "score": 0.8},
            {"content": "doc2", "score": 0.7},
            {"content": "doc3", "score": 0.6},
        ]

        result = service.rerank("query", documents, top_k=2)

        assert len(result) == 2
        # doc2 should be first (highest rerank score 0.9)
        assert result[0]["content"] == "doc2"
        assert result[0]["rerank_score"] == 0.9

    def test_rerank_truncates_long_content(self):
        """rerank should truncate content longer than 1000 chars."""
        from src.services.reranker_service import ReRankerService

        ReRankerService._instance = None
        service = ReRankerService()

        mock_model = MagicMock()
        mock_model.predict.return_value = [0.5]
        service.model = mock_model

        long_content = "x" * 2000
        documents = [{"content": long_content}]

        service.rerank("query", documents)

        call_args = mock_model.predict.call_args[0][0]
        # Check that the content was truncated
        assert len(call_args[0][1]) == 1000

    def test_rerank_handles_non_string_content(self):
        """rerank should handle non-string content by converting."""
        from src.services.reranker_service import ReRankerService

        ReRankerService._instance = None
        service = ReRankerService()

        mock_model = MagicMock()
        mock_model.predict.return_value = [0.5]
        service.model = mock_model

        documents = [{"content": 12345}]

        service.rerank("query", documents)

        call_args = mock_model.predict.call_args[0][0]
        assert call_args[0][1] == "12345"

    def test_rerank_handles_exception(self):
        """rerank should handle exceptions gracefully."""
        from src.services.reranker_service import ReRankerService

        ReRankerService._instance = None
        service = ReRankerService()

        mock_model = MagicMock()
        mock_model.predict.side_effect = Exception("Model error")
        service.model = mock_model

        documents = [
            {"content": "doc1"},
            {"content": "doc2"},
        ]

        result = service.rerank("query", documents, top_k=2)

        # Should return original order on error
        assert len(result) == 2
        assert result[0]["content"] == "doc1"

    def test_rerank_custom_content_key(self):
        """rerank should use custom content key."""
        from src.services.reranker_service import ReRankerService

        ReRankerService._instance = None
        service = ReRankerService()

        mock_model = MagicMock()
        mock_model.predict.return_value = [0.8]
        service.model = mock_model

        documents = [{"text": "doc content"}]

        service.rerank("query", documents, content_key="text")

        call_args = mock_model.predict.call_args[0][0]
        assert call_args[0][1] == "doc content"


class TestReRankerStatus:
    """Tests for status methods."""

    def test_is_available_false_without_model(self):
        """is_available should return False when model not loaded."""
        from src.services.reranker_service import ReRankerService

        ReRankerService._instance = None
        service = ReRankerService()
        service._init_error = "not available"

        result = service.is_available()

        assert result is False

    def test_get_status_not_initialized(self):
        """get_status should return correct status when not initialized."""
        from src.services.reranker_service import ReRankerService

        ReRankerService._instance = None
        service = ReRankerService()

        status = service.get_status()

        assert status["initialized"] is False
        assert status["available"] is True
        assert status["error"] is None
        assert status["model"] is None

    def test_get_status_with_error(self):
        """get_status should return error info."""
        from src.services.reranker_service import ReRankerService

        ReRankerService._instance = None
        service = ReRankerService()
        service._init_error = "test error"

        status = service.get_status()

        assert status["available"] is False
        assert status["error"] == "test error"

    def test_get_status_initialized(self):
        """get_status should return model name when initialized."""
        from src.services.reranker_service import ReRankerService

        ReRankerService._instance = None
        service = ReRankerService()
        service.model = MagicMock()

        status = service.get_status()

        assert status["initialized"] is True
        assert status["model"] == "cross-encoder/ms-marco-MiniLM-L-6-v2"


class TestGetReranker:
    """Tests for get_reranker singleton function."""

    def test_get_reranker_returns_singleton(self):
        """get_reranker should return same instance."""
        from src.services.reranker_service import get_reranker, ReRankerService
        import src.services.reranker_service as module

        # Reset singleton
        module._reranker = None
        ReRankerService._instance = None

        reranker1 = get_reranker()
        reranker2 = get_reranker()

        assert reranker1 is reranker2


class TestRerankResults:
    """Tests for rerank_results convenience function."""

    def test_rerank_results_uses_singleton(self):
        """rerank_results should use singleton service."""
        from src.services.reranker_service import rerank_results, ReRankerService
        import src.services.reranker_service as module

        module._reranker = None
        ReRankerService._instance = None

        documents = [{"content": "test"}]
        result = rerank_results("query", documents)

        # Should return documents (model not available, returns original)
        assert result == documents
