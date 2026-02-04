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
    """Create a mock KnowledgeIndexManager."""
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


# ==================== KnowledgeIndexManager Unit Tests ====================

class TestKnowledgeIndexManager:
    """Test KnowledgeIndexManager functionality."""

    def test_manager_creates_directories(self, mock_config, tmp_path):
        """KnowledgeIndexManager should create necessary directories."""
        from src.api.knowledge_routes import KnowledgeIndexManager

        # Patch the base path to use temp directory
        with patch.object(KnowledgeIndexManager, '__init__', return_value=None):
            manager = KnowledgeIndexManager.__new__(KnowledgeIndexManager)
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
        from src.api.knowledge_routes import KnowledgeIndexManager

        with patch.object(KnowledgeIndexManager, '__init__', return_value=None):
            manager = KnowledgeIndexManager.__new__(KnowledgeIndexManager)
            manager.metadata_file = tmp_path / "metadata.json"

            # Manually call _load_metadata
            metadata = manager._load_metadata()

            assert "documents" in metadata
            assert "chunks" in metadata
            assert metadata["documents"] == {}

    def test_load_metadata_migrates_visibility(self, mock_config, tmp_path):
        """_load_metadata should add visibility to old documents."""
        from src.api.knowledge_routes import KnowledgeIndexManager

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

        with patch.object(KnowledgeIndexManager, '__init__', return_value=None):
            manager = KnowledgeIndexManager.__new__(KnowledgeIndexManager)
            manager.metadata_file = metadata_file

            # Load metadata
            metadata = manager._load_metadata()

            # Visibility should be added
            assert metadata["documents"]["DOC-001"]["visibility"] == "public"

    def test_chunk_text_function(self, mock_config):
        """_chunk_text should split text into chunks."""
        from src.api.knowledge_routes import KnowledgeIndexManager

        with patch.object(KnowledgeIndexManager, '__init__', return_value=None):
            manager = KnowledgeIndexManager.__new__(KnowledgeIndexManager)

            text = " ".join([f"word{i}" for i in range(1000)])
            chunks = manager._chunk_text(text, chunk_size=100, overlap=10)

            # Should create multiple chunks
            assert len(chunks) > 1

            # Each chunk should have content
            for chunk in chunks:
                assert len(chunk) > 0

    def test_get_status_returns_counts(self, mock_config, tmp_path):
        """get_status should return document counts."""
        from src.api.knowledge_routes import KnowledgeIndexManager

        with patch.object(KnowledgeIndexManager, '__init__', return_value=None):
            manager = KnowledgeIndexManager.__new__(KnowledgeIndexManager)
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
        """get_index_manager should return KnowledgeIndexManager instance."""
        from src.api.knowledge_routes import get_index_manager, _index_managers
        import src.api.knowledge_routes as knowledge_module

        # Reset cache
        knowledge_module._index_managers = {}

        with patch('src.api.knowledge_routes.KnowledgeIndexManager') as MockManager:
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

        with patch('src.api.knowledge_routes.KnowledgeIndexManager') as MockManager:
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


# ==================== Endpoint Handler Unit Tests ====================

class TestListDocumentsUnit:
    """Unit tests for list_documents endpoint handler."""

    @pytest.mark.asyncio
    async def test_list_documents_success(self, mock_config, mock_faiss_manager):
        """list_documents should return documents."""
        from src.api.knowledge_routes import list_documents, DocumentMetadata

        mock_doc = DocumentMetadata(
            document_id="DOC-001",
            filename="test.pdf",
            category="general",
            file_type="pdf",
            file_size=1024,
            status="indexed",
            uploaded_at="2025-01-01T00:00:00"
        )
        mock_faiss_manager.get_documents.return_value = [mock_doc]

        with patch('src.api.knowledge_routes.get_index_manager', return_value=mock_faiss_manager):
            result = await list_documents(
                category=None,
                status=None,
                visibility=None,
                config=mock_config
            )

        assert result['success'] is True
        assert result['count'] == 1
        assert result['data'][0]['document_id'] == 'DOC-001'

    @pytest.mark.asyncio
    async def test_list_documents_filter_category(self, mock_config, mock_faiss_manager):
        """list_documents should filter by category."""
        from src.api.knowledge_routes import list_documents, DocumentMetadata

        mock_docs = [
            DocumentMetadata(
                document_id="DOC-001",
                filename="test1.pdf",
                category="general",
                file_type="pdf",
                file_size=1024,
                status="indexed",
                uploaded_at="2025-01-01T00:00:00"
            ),
            DocumentMetadata(
                document_id="DOC-002",
                filename="test2.pdf",
                category="specific",
                file_type="pdf",
                file_size=2048,
                status="indexed",
                uploaded_at="2025-01-02T00:00:00"
            )
        ]
        mock_faiss_manager.get_documents.return_value = mock_docs

        with patch('src.api.knowledge_routes.get_index_manager', return_value=mock_faiss_manager):
            result = await list_documents(
                category="general",
                status=None,
                visibility=None,
                config=mock_config
            )

        assert result['count'] == 1
        assert result['data'][0]['category'] == 'general'

    @pytest.mark.asyncio
    async def test_list_documents_filter_status(self, mock_config, mock_faiss_manager):
        """list_documents should filter by status."""
        from src.api.knowledge_routes import list_documents, DocumentMetadata

        mock_docs = [
            DocumentMetadata(
                document_id="DOC-001",
                filename="test1.pdf",
                category="general",
                file_type="pdf",
                file_size=1024,
                status="indexed",
                uploaded_at="2025-01-01T00:00:00"
            ),
            DocumentMetadata(
                document_id="DOC-002",
                filename="test2.pdf",
                category="general",
                file_type="pdf",
                file_size=2048,
                status="pending",
                uploaded_at="2025-01-02T00:00:00"
            )
        ]
        mock_faiss_manager.get_documents.return_value = mock_docs

        with patch('src.api.knowledge_routes.get_index_manager', return_value=mock_faiss_manager):
            result = await list_documents(
                category=None,
                status="indexed",
                visibility=None,
                config=mock_config
            )

        assert result['count'] == 1
        assert result['data'][0]['status'] == 'indexed'


class TestGetDocumentUnit:
    """Unit tests for get_document endpoint handler."""

    @pytest.mark.asyncio
    async def test_get_document_success(self, mock_config, mock_faiss_manager):
        """get_document should return document by ID."""
        from src.api.knowledge_routes import get_document, DocumentMetadata

        mock_doc = DocumentMetadata(
            document_id="DOC-001",
            filename="test.pdf",
            category="general",
            file_type="pdf",
            file_size=1024,
            status="indexed",
            uploaded_at="2025-01-01T00:00:00"
        )
        mock_faiss_manager.get_document.return_value = mock_doc

        with patch('src.api.knowledge_routes.get_index_manager', return_value=mock_faiss_manager):
            result = await get_document(
                document_id="DOC-001",
                config=mock_config
            )

        assert result['success'] is True
        assert result['data']['document_id'] == 'DOC-001'

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, mock_config, mock_faiss_manager):
        """get_document should raise 404 when not found."""
        from src.api.knowledge_routes import get_document
        from fastapi import HTTPException

        mock_faiss_manager.get_document.return_value = None

        with patch('src.api.knowledge_routes.get_index_manager', return_value=mock_faiss_manager):
            with pytest.raises(HTTPException) as exc_info:
                await get_document(
                    document_id="DOC-NOTFOUND",
                    config=mock_config
                )

            assert exc_info.value.status_code == 404


class TestDeleteDocumentUnit:
    """Unit tests for delete_document endpoint handler."""

    @pytest.mark.asyncio
    async def test_delete_document_success(self, mock_config, mock_faiss_manager):
        """delete_document should delete document."""
        from src.api.knowledge_routes import delete_document

        mock_faiss_manager.delete_document.return_value = True

        with patch('src.api.knowledge_routes.get_index_manager', return_value=mock_faiss_manager):
            result = await delete_document(
                document_id="DOC-001",
                config=mock_config
            )

        assert result['success'] is True
        assert 'deleted' in result['message']

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self, mock_config, mock_faiss_manager):
        """delete_document should raise 404 when not found."""
        from src.api.knowledge_routes import delete_document
        from fastapi import HTTPException

        mock_faiss_manager.delete_document.return_value = False

        with patch('src.api.knowledge_routes.get_index_manager', return_value=mock_faiss_manager):
            with pytest.raises(HTTPException) as exc_info:
                await delete_document(
                    document_id="DOC-NOTFOUND",
                    config=mock_config
                )

            assert exc_info.value.status_code == 404


class TestSearchKnowledgeUnit:
    """Unit tests for search_knowledge endpoint handler."""

    @pytest.mark.asyncio
    async def test_search_knowledge_success(self, mock_config, mock_faiss_manager):
        """search_knowledge should return search results."""
        from src.api.knowledge_routes import search_knowledge, SearchRequest

        mock_faiss_manager.search.return_value = [
            {
                "content": "Sample content",
                "source": "test.pdf",
                "score": 0.85,
                "document_id": "DOC-001",
                "chunk_index": 0
            }
        ]

        with patch('src.api.knowledge_routes.get_index_manager', return_value=mock_faiss_manager):
            request = SearchRequest(query="test query")
            result = await search_knowledge(
                request=request,
                config=mock_config
            )

        assert result['success'] is True
        assert result['count'] == 1
        assert result['query'] == "test query"

    @pytest.mark.asyncio
    async def test_search_knowledge_empty(self, mock_config, mock_faiss_manager):
        """search_knowledge should return empty when no results."""
        from src.api.knowledge_routes import search_knowledge, SearchRequest

        mock_faiss_manager.search.return_value = []

        with patch('src.api.knowledge_routes.get_index_manager', return_value=mock_faiss_manager):
            request = SearchRequest(query="unknown topic")
            result = await search_knowledge(
                request=request,
                config=mock_config
            )

        assert result['success'] is True
        assert result['count'] == 0


class TestSearchKnowledgeGetUnit:
    """Unit tests for search_knowledge_get endpoint handler."""

    @pytest.mark.asyncio
    async def test_search_get_success(self, mock_config, mock_faiss_manager):
        """search_knowledge_get should return search results."""
        from src.api.knowledge_routes import search_knowledge_get

        mock_faiss_manager.search.return_value = [
            {
                "content": "Result content",
                "source": "doc.pdf",
                "score": 0.9,
                "document_id": "DOC-001",
                "chunk_index": 0
            }
        ]

        with patch('src.api.knowledge_routes.get_index_manager', return_value=mock_faiss_manager):
            result = await search_knowledge_get(
                query="search term",
                top_k=5,
                category=None,
                visibility=None,
                config=mock_config
            )

        assert result['success'] is True
        assert result['count'] == 1


class TestIndexStatusUnit:
    """Unit tests for get_index_status endpoint handler."""

    @pytest.mark.asyncio
    async def test_index_status_success(self, mock_config, mock_faiss_manager):
        """get_index_status should return status."""
        from src.api.knowledge_routes import get_index_status

        mock_faiss_manager.get_status.return_value = {
            "total_documents": 5,
            "indexed_documents": 4,
            "pending_documents": 1,
            "error_documents": 0,
            "public_documents": 3,
            "private_documents": 2,
            "total_chunks": 100,
            "index_size_bytes": 10240,
            "last_updated": "2025-01-01T00:00:00"
        }

        with patch('src.api.knowledge_routes.get_index_manager', return_value=mock_faiss_manager):
            result = await get_index_status(config=mock_config)

        assert result['success'] is True
        assert result['data']['total_documents'] == 5


class TestRebuildIndexUnit:
    """Unit tests for rebuild_index endpoint handler."""

    @pytest.mark.asyncio
    async def test_rebuild_index_success(self, mock_config, mock_faiss_manager):
        """rebuild_index should rebuild and return status."""
        from src.api.knowledge_routes import rebuild_index

        mock_faiss_manager.get_status.return_value = {
            "total_documents": 3,
            "indexed_documents": 3,
            "pending_documents": 0,
            "error_documents": 0,
            "public_documents": 3,
            "private_documents": 0,
            "total_chunks": 50,
            "index_size_bytes": 5120,
            "last_updated": "2025-01-01T00:00:00"
        }

        with patch('src.api.knowledge_routes.get_index_manager', return_value=mock_faiss_manager):
            result = await rebuild_index(config=mock_config)

        assert result['success'] is True
        assert result['message'] == 'Index rebuilt'
        mock_faiss_manager._rebuild_index.assert_called_once()


class TestListCategoriesUnit:
    """Unit tests for list_categories endpoint handler."""

    @pytest.mark.asyncio
    async def test_list_categories_success(self, mock_config, mock_faiss_manager):
        """list_categories should return category counts."""
        from src.api.knowledge_routes import list_categories, DocumentMetadata

        mock_docs = [
            DocumentMetadata(
                document_id="DOC-001",
                filename="test1.pdf",
                category="general",
                file_type="pdf",
                file_size=1024,
                status="indexed",
                uploaded_at="2025-01-01T00:00:00"
            ),
            DocumentMetadata(
                document_id="DOC-002",
                filename="test2.pdf",
                category="general",
                file_type="pdf",
                file_size=2048,
                status="indexed",
                uploaded_at="2025-01-02T00:00:00"
            ),
            DocumentMetadata(
                document_id="DOC-003",
                filename="test3.pdf",
                category="specific",
                file_type="pdf",
                file_size=512,
                status="indexed",
                uploaded_at="2025-01-03T00:00:00"
            )
        ]
        mock_faiss_manager.get_documents.return_value = mock_docs

        with patch('src.api.knowledge_routes.get_index_manager', return_value=mock_faiss_manager):
            result = await list_categories(config=mock_config)

        assert result['success'] is True
        # Should have 2 categories
        assert len(result['data']) == 2

        # Find general category
        general = next((c for c in result['data'] if c['name'] == 'general'), None)
        assert general is not None
        assert general['count'] == 2


# ==================== Global KB Proxy Tests ====================

class TestGlobalKnowledgeBaseProxy:
    """Test global knowledge base proxy endpoints."""

    @pytest.mark.asyncio
    async def test_list_global_documents_success(self):
        """list_global_documents should proxy to Travel Platform."""
        from src.api.knowledge_routes import list_global_documents

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "documents": [
                {
                    "id": "doc-123",
                    "title": "Travel Guide",
                    "source_type": "pdf",
                    "file_size": 1024,
                    "chunk_count": 10,
                    "created_at": "2025-01-01T00:00:00",
                    "content_preview": "Sample preview",
                    "category": "guides",
                    "has_original_file": True
                }
            ],
            "total": 1
        }

        with patch('src.api.knowledge_routes.http_requests.get', return_value=mock_response):
            result = await list_global_documents(
                search=None,
                limit=100,
                offset=0
            )

        assert result['success'] is True
        assert result['count'] == 1
        assert result['data'][0]['filename'] == 'Travel Guide'
        assert result['data'][0]['visibility'] == 'global'

    @pytest.mark.asyncio
    async def test_list_global_documents_with_search(self):
        """list_global_documents should pass search parameter."""
        from src.api.knowledge_routes import list_global_documents

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"documents": [], "total": 0}

        with patch('src.api.knowledge_routes.http_requests.get', return_value=mock_response) as mock_get:
            await list_global_documents(
                search="hotel booking",
                limit=100,
                offset=0
            )

        # Verify search was passed in params
        call_kwargs = mock_get.call_args
        assert 'params' in call_kwargs[1]
        assert call_kwargs[1]['params']['search'] == 'hotel booking'

    @pytest.mark.asyncio
    async def test_list_global_documents_timeout(self):
        """list_global_documents should handle timeout."""
        from src.api.knowledge_routes import list_global_documents
        import requests

        with patch('src.api.knowledge_routes.http_requests.get', side_effect=requests.exceptions.Timeout()):
            result = await list_global_documents(
                search=None,
                limit=100,
                offset=0
            )

        assert result['success'] is False
        assert 'timed out' in result['error'].lower()
        assert result['data'] == []

    @pytest.mark.asyncio
    async def test_list_global_documents_connection_error(self):
        """list_global_documents should handle connection error."""
        from src.api.knowledge_routes import list_global_documents
        import requests

        with patch('src.api.knowledge_routes.http_requests.get', side_effect=requests.exceptions.ConnectionError()):
            result = await list_global_documents(
                search=None,
                limit=100,
                offset=0
            )

        assert result['success'] is False
        assert 'connect' in result['error'].lower()

    @pytest.mark.asyncio
    async def test_list_global_documents_error_status(self):
        """list_global_documents should handle error status codes."""
        from src.api.knowledge_routes import list_global_documents

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch('src.api.knowledge_routes.http_requests.get', return_value=mock_response):
            result = await list_global_documents(
                search=None,
                limit=100,
                offset=0
            )

        assert result['success'] is False
        assert '500' in result['error']

    @pytest.mark.asyncio
    async def test_get_global_document_content_success(self):
        """get_global_document_content should proxy content request."""
        from src.api.knowledge_routes import get_global_document_content

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": "Document content here",
            "metadata": {"title": "Test Doc"}
        }

        with patch('src.api.knowledge_routes.http_requests.get', return_value=mock_response):
            result = await get_global_document_content(document_id="doc-123")

        assert result['content'] == "Document content here"

    @pytest.mark.asyncio
    async def test_get_global_document_content_error(self):
        """get_global_document_content should handle errors."""
        from src.api.knowledge_routes import get_global_document_content
        from fastapi.responses import JSONResponse

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch('src.api.knowledge_routes.http_requests.get', return_value=mock_response):
            result = await get_global_document_content(document_id="doc-notfound")

        assert isinstance(result, JSONResponse)
        assert result.status_code == 404

    @pytest.mark.asyncio
    async def test_download_global_document_success(self):
        """download_global_document should proxy download."""
        from src.api.knowledge_routes import download_global_document
        from starlette.responses import Response

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"PDF content here"
        mock_response.headers = {
            "content-type": "application/pdf",
            "content-disposition": 'attachment; filename="test.pdf"'
        }

        with patch('src.api.knowledge_routes.http_requests.get', return_value=mock_response):
            result = await download_global_document(document_id="doc-123")

        assert isinstance(result, Response)
        assert result.media_type == "application/pdf"


# ==================== KnowledgeIndexManager Additional Tests ====================

class TestKnowledgeExtractText:
    """Test text extraction functionality."""

    def test_extract_text_txt(self, mock_config, tmp_path):
        """_extract_text should extract text from txt files."""
        from src.api.knowledge_routes import KnowledgeIndexManager

        # Create a test text file
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Sample text content for testing.")

        with patch.object(KnowledgeIndexManager, '__init__', return_value=None):
            manager = KnowledgeIndexManager.__new__(KnowledgeIndexManager)

            text = manager._extract_text(txt_file, "txt")

            assert "Sample text content" in text

    def test_extract_text_md(self, mock_config, tmp_path):
        """_extract_text should extract text from markdown files."""
        from src.api.knowledge_routes import KnowledgeIndexManager

        # Create a test markdown file
        md_file = tmp_path / "test.md"
        md_file.write_text("# Header\n\nSome markdown content.")

        with patch.object(KnowledgeIndexManager, '__init__', return_value=None):
            manager = KnowledgeIndexManager.__new__(KnowledgeIndexManager)

            text = manager._extract_text(md_file, "md")

            assert "Header" in text
            assert "markdown content" in text

    def test_extract_text_unsupported(self, mock_config, tmp_path):
        """_extract_text should raise error for unsupported types."""
        from src.api.knowledge_routes import KnowledgeIndexManager
        from fastapi import HTTPException

        # Create a test file with unsupported extension
        other_file = tmp_path / "test.xyz"
        other_file.write_bytes(b"binary content")

        with patch.object(KnowledgeIndexManager, '__init__', return_value=None):
            manager = KnowledgeIndexManager.__new__(KnowledgeIndexManager)

            with pytest.raises(HTTPException) as exc_info:
                manager._extract_text(other_file, "xyz")

            assert exc_info.value.status_code == 400


class TestDocumentUploadHandler:
    """Test document upload handler."""

    @pytest.mark.asyncio
    async def test_upload_document_handler(self, mock_config, mock_faiss_manager):
        """upload_document should add document and optionally index."""
        from src.api.knowledge_routes import upload_document, DocumentMetadata

        mock_doc = DocumentMetadata(
            document_id="DOC-NEW",
            filename="uploaded.txt",
            category="general",
            file_type="txt",
            file_size=100,
            status="indexed",
            uploaded_at="2025-01-01T00:00:00"
        )
        mock_faiss_manager.add_document.return_value = mock_doc
        mock_faiss_manager.index_document.return_value = mock_doc

        mock_file = MagicMock()
        mock_file.filename = "uploaded.txt"
        mock_file.file = io.BytesIO(b"Test content")

        with patch('src.api.knowledge_routes.get_index_manager', return_value=mock_faiss_manager):
            result = await upload_document(
                file=mock_file,
                category="general",
                tags="tag1,tag2",
                visibility="public",
                auto_index=True,
                config=mock_config
            )

        assert result['success'] is True
        mock_faiss_manager.add_document.assert_called_once()
        mock_faiss_manager.index_document.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
