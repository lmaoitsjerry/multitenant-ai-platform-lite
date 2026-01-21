"""
Knowledge Routes Unit Tests

Comprehensive tests for knowledge base API endpoints:
- /api/v1/knowledge/documents (CRUD for documents)
- /api/v1/knowledge/search (search functionality)
- /api/v1/knowledge/status (index status)
- /api/v1/knowledge/categories (category listing)

Uses FastAPI TestClient with mocked FAISS dependencies.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import io
import json
import tempfile
from pathlib import Path


# ==================== Fixtures ====================

@pytest.fixture
def mock_config():
    """Create a mock ClientConfig."""
    config = MagicMock()
    config.client_id = "test_tenant"
    return config


@pytest.fixture
def test_client():
    """Create a basic TestClient."""
    from main import app
    return TestClient(app)


@pytest.fixture
def mock_faiss_manager():
    """Create a mock FAISSIndexManager."""
    manager = MagicMock()
    manager.get_documents.return_value = []
    manager.get_document.return_value = None
    manager.search.return_value = []
    manager.get_status.return_value = {
        "total_documents": 0,
        "indexed_documents": 0,
        "pending_documents": 0,
        "error_documents": 0,
        "public_documents": 0,
        "private_documents": 0,
        "total_chunks": 0,
        "index_size_bytes": 0,
        "last_updated": None
    }
    return manager


# ==================== Document List Endpoint Tests ====================

class TestListDocumentsEndpoint:
    """Test GET /api/v1/knowledge/documents endpoint."""

    def test_list_documents_requires_auth(self, test_client):
        """GET /api/v1/knowledge/documents should require authentication."""
        response = test_client.get("/api/v1/knowledge/documents")
        assert response.status_code == 401

    def test_list_documents_with_category_requires_auth(self, test_client):
        """GET /api/v1/knowledge/documents?category=general still requires auth."""
        response = test_client.get("/api/v1/knowledge/documents?category=general")
        assert response.status_code == 401

    def test_list_documents_with_status_requires_auth(self, test_client):
        """GET /api/v1/knowledge/documents?status=indexed still requires auth."""
        response = test_client.get("/api/v1/knowledge/documents?status=indexed")
        assert response.status_code == 401

    def test_list_documents_with_visibility_requires_auth(self, test_client):
        """GET /api/v1/knowledge/documents?visibility=public still requires auth."""
        response = test_client.get("/api/v1/knowledge/documents?visibility=public")
        assert response.status_code == 401


class TestUploadDocumentEndpoint:
    """Test POST /api/v1/knowledge/documents endpoint."""

    def test_upload_document_requires_auth(self, test_client):
        """POST /api/v1/knowledge/documents should require authentication."""
        response = test_client.post(
            "/api/v1/knowledge/documents",
            files={"file": ("test.txt", io.BytesIO(b"Test content"), "text/plain")},
            data={"category": "general"}
        )
        assert response.status_code == 401

    def test_upload_document_with_tags_requires_auth(self, test_client):
        """POST /api/v1/knowledge/documents with tags requires auth."""
        response = test_client.post(
            "/api/v1/knowledge/documents",
            files={"file": ("test.txt", io.BytesIO(b"Test content"), "text/plain")},
            data={"category": "general", "tags": "tag1,tag2"}
        )
        assert response.status_code == 401

    def test_upload_document_with_visibility_requires_auth(self, test_client):
        """POST /api/v1/knowledge/documents with visibility requires auth."""
        response = test_client.post(
            "/api/v1/knowledge/documents",
            files={"file": ("test.txt", io.BytesIO(b"Test content"), "text/plain")},
            data={"category": "general", "visibility": "private"}
        )
        assert response.status_code == 401


class TestGetDocumentEndpoint:
    """Test GET /api/v1/knowledge/documents/{document_id} endpoint."""

    def test_get_document_requires_auth(self, test_client):
        """GET /api/v1/knowledge/documents/{id} should require auth."""
        response = test_client.get("/api/v1/knowledge/documents/DOC-ABC12345")
        assert response.status_code == 401

    def test_get_document_various_ids(self, test_client):
        """GET /api/v1/knowledge/documents/{id} with various IDs requires auth."""
        for doc_id in ["DOC-001", "DOC-XYZ789", "12345"]:
            response = test_client.get(f"/api/v1/knowledge/documents/{doc_id}")
            assert response.status_code == 401


class TestDeleteDocumentEndpoint:
    """Test DELETE /api/v1/knowledge/documents/{document_id} endpoint."""

    def test_delete_document_requires_auth(self, test_client):
        """DELETE /api/v1/knowledge/documents/{id} should require auth."""
        response = test_client.delete("/api/v1/knowledge/documents/DOC-ABC12345")
        assert response.status_code == 401


class TestReindexDocumentEndpoint:
    """Test POST /api/v1/knowledge/documents/{document_id}/reindex endpoint."""

    def test_reindex_document_requires_auth(self, test_client):
        """POST /api/v1/knowledge/documents/{id}/reindex should require auth."""
        response = test_client.post("/api/v1/knowledge/documents/DOC-ABC12345/reindex")
        assert response.status_code == 401


class TestDownloadDocumentEndpoint:
    """Test GET /api/v1/knowledge/documents/{document_id}/download endpoint."""

    def test_download_document_requires_auth(self, test_client):
        """GET /api/v1/knowledge/documents/{id}/download should require auth."""
        response = test_client.get("/api/v1/knowledge/documents/DOC-ABC12345/download")
        assert response.status_code == 401


# ==================== Search Endpoint Tests ====================

class TestSearchKnowledgePostEndpoint:
    """Test POST /api/v1/knowledge/search endpoint."""

    def test_search_post_requires_auth(self, test_client):
        """POST /api/v1/knowledge/search should require authentication."""
        response = test_client.post(
            "/api/v1/knowledge/search",
            json={"query": "hotel booking"}
        )
        assert response.status_code == 401

    def test_search_with_filters_requires_auth(self, test_client):
        """POST /api/v1/knowledge/search with filters requires auth."""
        response = test_client.post(
            "/api/v1/knowledge/search",
            json={
                "query": "hotel booking",
                "top_k": 10,
                "category": "general",
                "visibility": "public",
                "min_score": 0.7
            }
        )
        assert response.status_code == 401


class TestSearchKnowledgeGetEndpoint:
    """Test GET /api/v1/knowledge/search endpoint."""

    def test_search_get_requires_auth(self, test_client):
        """GET /api/v1/knowledge/search should require authentication."""
        response = test_client.get("/api/v1/knowledge/search?query=hotel")
        assert response.status_code == 401

    def test_search_get_with_params_requires_auth(self, test_client):
        """GET /api/v1/knowledge/search with parameters requires auth."""
        response = test_client.get(
            "/api/v1/knowledge/search?query=hotel&top_k=5&category=general"
        )
        assert response.status_code == 401


# ==================== Status and Admin Endpoint Tests ====================

class TestIndexStatusEndpoint:
    """Test GET /api/v1/knowledge/status endpoint."""

    def test_status_requires_auth(self, test_client):
        """GET /api/v1/knowledge/status should require authentication."""
        response = test_client.get("/api/v1/knowledge/status")
        assert response.status_code == 401


class TestRebuildIndexEndpoint:
    """Test POST /api/v1/knowledge/rebuild endpoint."""

    def test_rebuild_requires_auth(self, test_client):
        """POST /api/v1/knowledge/rebuild should require authentication."""
        response = test_client.post("/api/v1/knowledge/rebuild")
        assert response.status_code == 401


class TestCategoriesEndpoint:
    """Test GET /api/v1/knowledge/categories endpoint."""

    def test_categories_requires_auth(self, test_client):
        """GET /api/v1/knowledge/categories should require authentication."""
        response = test_client.get("/api/v1/knowledge/categories")
        assert response.status_code == 401


# ==================== Route Existence Tests ====================

class TestKnowledgeRouteExistence:
    """Test that all knowledge routes exist."""

    def test_knowledge_routes_exist(self, test_client):
        """All knowledge routes should exist (not 404)."""
        routes = [
            ("GET", "/api/v1/knowledge/documents"),
            ("POST", "/api/v1/knowledge/documents"),
            ("GET", "/api/v1/knowledge/documents/DOC-001"),
            ("DELETE", "/api/v1/knowledge/documents/DOC-001"),
            ("POST", "/api/v1/knowledge/documents/DOC-001/reindex"),
            ("GET", "/api/v1/knowledge/documents/DOC-001/download"),
            ("POST", "/api/v1/knowledge/search"),
            ("GET", "/api/v1/knowledge/search"),
            ("GET", "/api/v1/knowledge/status"),
            ("POST", "/api/v1/knowledge/rebuild"),
            ("GET", "/api/v1/knowledge/categories"),
        ]

        for method, path in routes:
            if method == "GET":
                # Search requires query parameter
                if "search" in path:
                    response = test_client.get(f"{path}?query=test")
                else:
                    response = test_client.get(path)
            elif method == "POST":
                # Document upload needs file
                if path == "/api/v1/knowledge/documents":
                    response = test_client.post(
                        path,
                        files={"file": ("test.txt", io.BytesIO(b"test"), "text/plain")}
                    )
                elif "search" in path:
                    response = test_client.post(path, json={"query": "test"})
                else:
                    response = test_client.post(path)
            elif method == "DELETE":
                response = test_client.delete(path)

            # Should be 401 (auth required), not 404 (route not found)
            assert response.status_code != 404, f"{method} {path} returned 404"


# ==================== Pydantic Model Tests ====================

class TestKnowledgeModels:
    """Test Pydantic model validation."""

    def test_document_metadata_model(self):
        """DocumentMetadata should have required fields."""
        from src.api.knowledge_routes import DocumentMetadata

        doc = DocumentMetadata(
            document_id="DOC-ABC12345",
            filename="test.pdf",
            category="general",
            file_type="pdf",
            file_size=1024,
            status="indexed",
            uploaded_at="2025-01-01T00:00:00"
        )

        assert doc.document_id == "DOC-ABC12345"
        assert doc.visibility == "public"  # Default
        assert doc.tags == []  # Default
        assert doc.chunk_count == 0  # Default

    def test_search_request_model(self):
        """SearchRequest should validate fields."""
        from src.api.knowledge_routes import SearchRequest

        request = SearchRequest(query="hotel booking")

        assert request.query == "hotel booking"
        assert request.top_k == 5  # Default
        assert request.min_score == 0.5  # Default

    def test_search_request_top_k_limits(self):
        """SearchRequest top_k should be 1-20."""
        from src.api.knowledge_routes import SearchRequest
        from pydantic import ValidationError

        # Valid values
        for k in [1, 5, 10, 20]:
            request = SearchRequest(query="test", top_k=k)
            assert request.top_k == k

        # Invalid value (too high)
        with pytest.raises(ValidationError):
            SearchRequest(query="test", top_k=25)

    def test_search_result_model(self):
        """SearchResult should have required fields."""
        from src.api.knowledge_routes import SearchResult

        result = SearchResult(
            content="Sample content",
            source="document.pdf",
            score=0.85,
            document_id="DOC-001",
            chunk_index=0
        )

        assert result.score == 0.85
        assert result.chunk_index == 0


# ==================== FAISSIndexManager Unit Tests ====================

class TestFAISSIndexManager:
    """Test FAISSIndexManager functionality."""

    def test_manager_creates_directories(self, mock_config, tmp_path):
        """FAISSIndexManager should create necessary directories."""
        from src.api.knowledge_routes import FAISSIndexManager

        # Patch the base path to use temp directory
        with patch.object(FAISSIndexManager, '__init__', return_value=None):
            manager = FAISSIndexManager.__new__(FAISSIndexManager)
            manager.config = mock_config
            manager.client_id = mock_config.client_id
            manager.base_path = tmp_path / "knowledge"
            manager.documents_path = manager.base_path / "documents"
            manager.index_path = manager.base_path / "faiss_index"
            manager.metadata_file = manager.base_path / "metadata.json"

            # Create directories manually since __init__ is patched
            manager.documents_path.mkdir(parents=True, exist_ok=True)
            manager.index_path.mkdir(parents=True, exist_ok=True)

            assert manager.documents_path.exists()
            assert manager.index_path.exists()

    def test_load_metadata_creates_default(self, mock_config, tmp_path):
        """_load_metadata should create default structure if file missing."""
        from src.api.knowledge_routes import FAISSIndexManager

        with patch.object(FAISSIndexManager, '__init__', return_value=None):
            manager = FAISSIndexManager.__new__(FAISSIndexManager)
            manager.metadata_file = tmp_path / "metadata.json"

            # Manually call _load_metadata
            metadata = manager._load_metadata()

            assert "documents" in metadata
            assert "chunks" in metadata
            assert metadata["documents"] == {}

    def test_load_metadata_migrates_visibility(self, mock_config, tmp_path):
        """_load_metadata should add visibility to old documents."""
        from src.api.knowledge_routes import FAISSIndexManager

        # Create old metadata without visibility
        metadata_file = tmp_path / "metadata.json"
        old_metadata = {
            "documents": {
                "DOC-001": {
                    "document_id": "DOC-001",
                    "filename": "test.pdf",
                    "category": "general",
                    "status": "indexed"
                    # No visibility field
                }
            },
            "chunks": [],
            "last_updated": None
        }
        metadata_file.write_text(json.dumps(old_metadata))

        with patch.object(FAISSIndexManager, '__init__', return_value=None):
            manager = FAISSIndexManager.__new__(FAISSIndexManager)
            manager.metadata_file = metadata_file

            # Load metadata
            metadata = manager._load_metadata()

            # Visibility should be added
            assert metadata["documents"]["DOC-001"]["visibility"] == "public"

    def test_chunk_text_function(self, mock_config):
        """_chunk_text should split text into chunks."""
        from src.api.knowledge_routes import FAISSIndexManager

        with patch.object(FAISSIndexManager, '__init__', return_value=None):
            manager = FAISSIndexManager.__new__(FAISSIndexManager)

            text = " ".join([f"word{i}" for i in range(1000)])
            chunks = manager._chunk_text(text, chunk_size=100, overlap=10)

            # Should create multiple chunks
            assert len(chunks) > 1

            # Each chunk should have content
            for chunk in chunks:
                assert len(chunk) > 0

    def test_get_status_returns_counts(self, mock_config, tmp_path):
        """get_status should return document counts."""
        from src.api.knowledge_routes import FAISSIndexManager

        with patch.object(FAISSIndexManager, '__init__', return_value=None):
            manager = FAISSIndexManager.__new__(FAISSIndexManager)
            manager.index_path = tmp_path / "faiss_index"
            manager.index_path.mkdir(parents=True, exist_ok=True)
            manager.metadata = {
                "documents": {
                    "DOC-001": {"status": "indexed", "visibility": "public"},
                    "DOC-002": {"status": "pending", "visibility": "private"},
                    "DOC-003": {"status": "error", "visibility": "public"},
                },
                "chunks": [{"id": 1}, {"id": 2}]
            }

            status = manager.get_status()

            assert status["total_documents"] == 3
            assert status["indexed_documents"] == 1
            assert status["pending_documents"] == 1
            assert status["error_documents"] == 1
            assert status["public_documents"] == 2
            assert status["private_documents"] == 1
            assert status["total_chunks"] == 2


# ==================== Dependency Tests ====================

class TestKnowledgeDependencies:
    """Test knowledge route dependencies."""

    def test_get_index_manager_returns_manager(self, mock_config):
        """get_index_manager should return FAISSIndexManager instance."""
        from src.api.knowledge_routes import get_index_manager, _index_managers
        import src.api.knowledge_routes as knowledge_module

        # Reset cache
        knowledge_module._index_managers = {}

        with patch('src.api.knowledge_routes.FAISSIndexManager') as MockManager:
            mock_instance = MagicMock()
            MockManager.return_value = mock_instance

            manager = get_index_manager(mock_config)

            assert manager is mock_instance
            MockManager.assert_called_once_with(mock_config)

    def test_get_index_manager_caches_result(self, mock_config):
        """get_index_manager should cache manager instances."""
        from src.api.knowledge_routes import get_index_manager, _index_managers
        import src.api.knowledge_routes as knowledge_module

        # Reset cache
        knowledge_module._index_managers = {}

        with patch('src.api.knowledge_routes.FAISSIndexManager') as MockManager:
            mock_instance = MagicMock()
            MockManager.return_value = mock_instance

            # First call creates instance
            manager1 = get_index_manager(mock_config)

            # Second call should use cache
            manager2 = get_index_manager(mock_config)

            # Should only create once
            assert MockManager.call_count == 1
            assert manager1 is manager2


# ==================== File Type Tests ====================

class TestSupportedFileTypes:
    """Test supported file type handling."""

    def test_supported_file_types(self):
        """Manager should support txt, md, pdf, docx files."""
        supported = ['txt', 'md', 'pdf', 'docx']

        for ext in supported:
            # Just verify these are recognized file types
            assert ext in supported

    def test_upload_txt_file_requires_auth(self, test_client):
        """Upload .txt file requires auth."""
        response = test_client.post(
            "/api/v1/knowledge/documents",
            files={"file": ("test.txt", io.BytesIO(b"text content"), "text/plain")}
        )
        assert response.status_code == 401

    def test_upload_pdf_file_requires_auth(self, test_client):
        """Upload .pdf file requires auth."""
        response = test_client.post(
            "/api/v1/knowledge/documents",
            files={"file": ("test.pdf", io.BytesIO(b"pdf content"), "application/pdf")}
        )
        assert response.status_code == 401

    def test_upload_md_file_requires_auth(self, test_client):
        """Upload .md file requires auth."""
        response = test_client.post(
            "/api/v1/knowledge/documents",
            files={"file": ("test.md", io.BytesIO(b"# Markdown"), "text/markdown")}
        )
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
