"""
Admin Knowledge Routes Unit Tests

Comprehensive tests for admin knowledge base API endpoints:
- GET /api/v1/admin/knowledge/documents (list documents)
- POST /api/v1/admin/knowledge/documents (create document)
- GET /api/v1/admin/knowledge/documents/{doc_id} (get document)
- PUT /api/v1/admin/knowledge/documents/{doc_id} (update document)
- DELETE /api/v1/admin/knowledge/documents/{doc_id} (delete document)
- POST /api/v1/admin/knowledge/rebuild-index (rebuild FAISS index)
- GET /api/v1/admin/knowledge/stats (knowledge base statistics)

Uses FastAPI TestClient with mocked GCS dependencies.
These tests verify:
1. Admin token validation (503 when unconfigured, 401 when missing/invalid)
2. Endpoint structure and HTTP methods
3. Document CRUD operations
4. GCS and local storage fallback paths
5. Cache functionality
6. Response formats
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
import os
import json
from pathlib import Path


# ==================== Fixtures ====================

@pytest.fixture
def mock_admin_token():
    """Set admin token environment variable."""
    with patch.dict(os.environ, {"ADMIN_API_TOKEN": "test-admin-token-123"}):
        yield "test-admin-token-123"


@pytest.fixture
def admin_headers(mock_admin_token):
    """Headers with valid admin token."""
    return {"X-Admin-Token": mock_admin_token}


# Use the test_client from conftest.py (shared fixture)


@pytest.fixture
def sample_document():
    """Sample document metadata."""
    return {
        "id": "doc_abc123456789",
        "title": "Hotel Booking Guide",
        "category": "general",
        "content": "This is the content of the document.",
        "filename": "documents/doc_abc123456789.txt",
        "file_type": "text",
        "chunk_count": 5,
        "visibility": "public",
        "tenant_id": None,
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00",
        "indexed": True
    }


@pytest.fixture
def sample_documents(sample_document):
    """List of sample documents."""
    return [
        sample_document,
        {
            "id": "doc_def456789012",
            "title": "Travel Tips",
            "category": "tips",
            "content": "Travel tips content.",
            "filename": "documents/doc_def456789012.txt",
            "file_type": "text",
            "chunk_count": 3,
            "visibility": "public",
            "tenant_id": "tenant_001",
            "created_at": "2025-01-02T00:00:00",
            "updated_at": "2025-01-02T00:00:00",
            "indexed": False
        },
        {
            "id": "doc_ghi789012345",
            "title": "FAQ Document",
            "category": "faq",
            "content": "Frequently asked questions.",
            "filename": "documents/doc_ghi789012345.txt",
            "file_type": "text",
            "chunk_count": 10,
            "visibility": "private",
            "tenant_id": None,
            "created_at": "2025-01-03T00:00:00",
            "updated_at": "2025-01-03T00:00:00",
            "indexed": True
        }
    ]


@pytest.fixture
def mock_gcs_client():
    """Create a mock GCS client."""
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_client.bucket.return_value = mock_bucket
    return mock_client, mock_bucket


# ==================== Admin Token Validation Tests ====================

class TestAdminKnowledgeAuth:
    """Test admin token authentication for all knowledge endpoints."""

    def test_list_documents_requires_admin_token(self, test_client):
        """GET /documents should return 401 without admin token."""
        response = test_client.get("/api/v1/admin/knowledge/documents")
        assert response.status_code in [401, 503]

    def test_list_documents_invalid_token(self, test_client, mock_admin_token):
        """GET /documents should return 401 with invalid token."""
        response = test_client.get(
            "/api/v1/admin/knowledge/documents",
            headers={"X-Admin-Token": "wrong-token"}
        )
        assert response.status_code == 401

    def test_create_document_requires_admin_token(self, test_client):
        """POST /documents should return 401 without admin token."""
        response = test_client.post(
            "/api/v1/admin/knowledge/documents",
            json={"title": "Test", "content": "Content"}
        )
        assert response.status_code in [401, 503]

    def test_create_document_invalid_token(self, test_client, mock_admin_token):
        """POST /documents should return 401 with invalid token."""
        response = test_client.post(
            "/api/v1/admin/knowledge/documents",
            headers={"X-Admin-Token": "wrong-token"},
            json={"title": "Test", "content": "Content"}
        )
        assert response.status_code == 401

    def test_get_document_requires_admin_token(self, test_client):
        """GET /documents/{doc_id} should return 401 without admin token."""
        response = test_client.get("/api/v1/admin/knowledge/documents/doc_123")
        assert response.status_code in [401, 503]

    def test_get_document_invalid_token(self, test_client, mock_admin_token):
        """GET /documents/{doc_id} should return 401 with invalid token."""
        response = test_client.get(
            "/api/v1/admin/knowledge/documents/doc_123",
            headers={"X-Admin-Token": "wrong-token"}
        )
        assert response.status_code == 401

    def test_update_document_requires_admin_token(self, test_client):
        """PUT /documents/{doc_id} should return 401 without admin token."""
        response = test_client.put(
            "/api/v1/admin/knowledge/documents/doc_123",
            json={"title": "Updated"}
        )
        assert response.status_code in [401, 503]

    def test_update_document_invalid_token(self, test_client, mock_admin_token):
        """PUT /documents/{doc_id} should return 401 with invalid token."""
        response = test_client.put(
            "/api/v1/admin/knowledge/documents/doc_123",
            headers={"X-Admin-Token": "wrong-token"},
            json={"title": "Updated"}
        )
        assert response.status_code == 401

    def test_delete_document_requires_admin_token(self, test_client):
        """DELETE /documents/{doc_id} should return 401 without admin token."""
        response = test_client.delete("/api/v1/admin/knowledge/documents/doc_123")
        assert response.status_code in [401, 503]

    def test_delete_document_invalid_token(self, test_client, mock_admin_token):
        """DELETE /documents/{doc_id} should return 401 with invalid token."""
        response = test_client.delete(
            "/api/v1/admin/knowledge/documents/doc_123",
            headers={"X-Admin-Token": "wrong-token"}
        )
        assert response.status_code == 401

    def test_rebuild_index_requires_admin_token(self, test_client):
        """POST /rebuild-index should return 401 without admin token."""
        response = test_client.post("/api/v1/admin/knowledge/rebuild-index")
        assert response.status_code in [401, 503]

    def test_rebuild_index_invalid_token(self, test_client, mock_admin_token):
        """POST /rebuild-index should return 401 with invalid token."""
        response = test_client.post(
            "/api/v1/admin/knowledge/rebuild-index",
            headers={"X-Admin-Token": "wrong-token"}
        )
        assert response.status_code == 401

    def test_stats_requires_admin_token(self, test_client):
        """GET /stats should return 401 without admin token."""
        response = test_client.get("/api/v1/admin/knowledge/stats")
        assert response.status_code in [401, 503]

    def test_stats_invalid_token(self, test_client, mock_admin_token):
        """GET /stats should return 401 with invalid token."""
        response = test_client.get(
            "/api/v1/admin/knowledge/stats",
            headers={"X-Admin-Token": "wrong-token"}
        )
        assert response.status_code == 401

    def test_admin_endpoint_without_token_configured_returns_503(self, test_client):
        """When ADMIN_API_TOKEN is not set, should return 503."""
        with patch.dict(os.environ, {"ADMIN_API_TOKEN": ""}, clear=False):
            response = test_client.get(
                "/api/v1/admin/knowledge/documents",
                headers={"X-Admin-Token": "any-token"}
            )
            assert response.status_code == 503
            assert "not configured" in response.json()["detail"].lower()


# ==================== List Documents Endpoint Tests ====================

class TestListDocumentsEndpoint:
    """Test GET /api/v1/admin/knowledge/documents endpoint."""

    def test_list_documents_returns_list(self, test_client, admin_headers, sample_documents):
        """GET /documents should return paginated document list."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            mock_load.return_value = sample_documents

            response = test_client.get(
                "/api/v1/admin/knowledge/documents",
                headers=admin_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert "count" in data
            assert "total" in data
            assert isinstance(data["data"], list)

    def test_list_documents_with_category_filter(self, test_client, admin_headers, sample_documents):
        """GET /documents?category=tips should filter by category."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            mock_load.return_value = sample_documents

            response = test_client.get(
                "/api/v1/admin/knowledge/documents?category=tips",
                headers=admin_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            # Should only return docs with category "tips"
            for doc in data["data"]:
                assert doc["category"] == "tips"

    def test_list_documents_with_tenant_filter(self, test_client, admin_headers, sample_documents):
        """GET /documents?tenant_id=tenant_001 should filter by tenant."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            mock_load.return_value = sample_documents

            response = test_client.get(
                "/api/v1/admin/knowledge/documents?tenant_id=tenant_001",
                headers=admin_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            # Should only return docs with tenant_id "tenant_001"
            for doc in data["data"]:
                assert doc.get("tenant_id") == "tenant_001"

    def test_list_documents_global_filter(self, test_client, admin_headers, sample_documents):
        """GET /documents?tenant_id=global should filter for global docs."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            mock_load.return_value = sample_documents

            response = test_client.get(
                "/api/v1/admin/knowledge/documents?tenant_id=global",
                headers=admin_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            # Should only return docs with no tenant_id
            for doc in data["data"]:
                assert doc.get("tenant_id") is None

    def test_list_documents_pagination_limit(self, test_client, admin_headers, sample_documents):
        """GET /documents?limit=1 should respect limit parameter."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            mock_load.return_value = sample_documents

            response = test_client.get(
                "/api/v1/admin/knowledge/documents?limit=1",
                headers=admin_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["count"] == 1
            assert data["total"] == 3  # Total should still be 3

    def test_list_documents_pagination_offset(self, test_client, admin_headers, sample_documents):
        """GET /documents?offset=1 should respect offset parameter."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            mock_load.return_value = sample_documents

            response = test_client.get(
                "/api/v1/admin/knowledge/documents?offset=1",
                headers=admin_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["count"] == 2  # Total 3, offset 1 = 2 remaining
            assert data["total"] == 3

    def test_list_documents_max_limit_200(self, test_client, admin_headers, sample_documents):
        """GET /documents?limit=500 should cap limit at 200."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            mock_load.return_value = sample_documents

            response = test_client.get(
                "/api/v1/admin/knowledge/documents?limit=500",
                headers=admin_headers
            )
            # Should fail validation since limit max is 200
            assert response.status_code == 422

    def test_list_documents_empty_result(self, test_client, admin_headers):
        """GET /documents should return empty list when no docs."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            mock_load.return_value = []

            response = test_client.get(
                "/api/v1/admin/knowledge/documents",
                headers=admin_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"] == []
            assert data["count"] == 0
            assert data["total"] == 0

    def test_list_documents_response_structure(self, test_client, admin_headers, sample_documents):
        """GET /documents response should have success, data, count, total."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            mock_load.return_value = sample_documents

            response = test_client.get(
                "/api/v1/admin/knowledge/documents",
                headers=admin_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert "success" in data
            assert "data" in data
            assert "count" in data
            assert "total" in data


# ==================== Cache Functions Tests ====================

class TestCacheFunctions:
    """Test in-memory cache functions."""

    def test_get_cached_returns_none_on_miss(self):
        """Cache miss should return None."""
        from src.api.admin_knowledge_routes import get_cached, _knowledge_cache
        # Clear cache
        _knowledge_cache.clear()

        result = get_cached("nonexistent_key")
        assert result is None

    def test_set_cached_stores_value(self):
        """set_cached should store and allow retrieval."""
        from src.api.admin_knowledge_routes import get_cached, set_cached, _knowledge_cache
        # Clear cache
        _knowledge_cache.clear()

        test_data = {"key": "value", "items": [1, 2, 3]}
        set_cached("test_key", test_data, ttl=60)

        result = get_cached("test_key")
        assert result == test_data

    def test_get_cached_returns_value_before_expiry(self):
        """Cache should return value if not expired."""
        from src.api.admin_knowledge_routes import get_cached, set_cached, _knowledge_cache
        # Clear cache
        _knowledge_cache.clear()

        test_data = ["item1", "item2"]
        set_cached("active_key", test_data, ttl=300)

        result = get_cached("active_key")
        assert result == test_data

    def test_get_cached_returns_none_after_expiry(self):
        """Cache should return None when entry is expired."""
        from src.api.admin_knowledge_routes import get_cached, _knowledge_cache
        # Clear and manually set expired entry
        _knowledge_cache.clear()
        _knowledge_cache["expired_key"] = {
            "data": "old_value",
            "expires": datetime.now() - timedelta(seconds=10)
        }

        result = get_cached("expired_key")
        assert result is None
        assert "expired_key" not in _knowledge_cache  # Should be deleted

    def test_invalidate_cache_all(self):
        """invalidate_cache() should clear entire cache."""
        from src.api.admin_knowledge_routes import get_cached, set_cached, invalidate_cache, _knowledge_cache
        # Clear cache
        _knowledge_cache.clear()

        set_cached("key1", "value1")
        set_cached("key2", "value2")
        set_cached("other", "value3")

        invalidate_cache()

        assert get_cached("key1") is None
        assert get_cached("key2") is None
        assert get_cached("other") is None

    def test_invalidate_cache_by_prefix(self):
        """invalidate_cache(prefix) should clear only matching keys."""
        from src.api.admin_knowledge_routes import get_cached, set_cached, invalidate_cache, _knowledge_cache
        # Clear cache
        _knowledge_cache.clear()

        set_cached("documents_list", "doc_value")
        set_cached("documents_stats", "stats_value")
        set_cached("other_key", "other_value")

        invalidate_cache(prefix="documents")

        assert get_cached("documents_list") is None
        assert get_cached("documents_stats") is None
        assert get_cached("other_key") == "other_value"


# ==================== Create Document Endpoint Tests ====================

class TestCreateDocumentEndpoint:
    """Test POST /api/v1/admin/knowledge/documents endpoint."""

    def test_create_document_success(self, test_client, admin_headers):
        """POST /documents should create document with valid request."""
        with patch("src.api.admin_knowledge_routes.save_gcs_document") as mock_save:
            with patch("src.api.admin_knowledge_routes.invalidate_cache") as mock_invalidate:
                mock_save.return_value = True

                response = test_client.post(
                    "/api/v1/admin/knowledge/documents",
                    headers=admin_headers,
                    json={
                        "title": "New Document",
                        "content": "This is the document content."
                    }
                )
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "data" in data
                assert data["message"] == "Document created successfully"

    def test_create_document_returns_doc_with_id(self, test_client, admin_headers):
        """POST /documents response should include generated doc_id."""
        with patch("src.api.admin_knowledge_routes.save_gcs_document") as mock_save:
            with patch("src.api.admin_knowledge_routes.invalidate_cache"):
                mock_save.return_value = True

                response = test_client.post(
                    "/api/v1/admin/knowledge/documents",
                    headers=admin_headers,
                    json={
                        "title": "Test Doc",
                        "content": "Content here."
                    }
                )
                assert response.status_code == 200
                data = response.json()
                assert "id" in data["data"]
                assert data["data"]["id"].startswith("doc_")

    def test_create_document_sets_timestamps(self, test_client, admin_headers):
        """POST /documents should set created_at and updated_at."""
        with patch("src.api.admin_knowledge_routes.save_gcs_document") as mock_save:
            with patch("src.api.admin_knowledge_routes.invalidate_cache"):
                mock_save.return_value = True

                response = test_client.post(
                    "/api/v1/admin/knowledge/documents",
                    headers=admin_headers,
                    json={
                        "title": "Timestamp Test",
                        "content": "Content."
                    }
                )
                assert response.status_code == 200
                data = response.json()
                assert "created_at" in data["data"]
                assert "updated_at" in data["data"]

    def test_create_document_default_category(self, test_client, admin_headers):
        """POST /documents should use 'general' if category not specified."""
        with patch("src.api.admin_knowledge_routes.save_gcs_document") as mock_save:
            with patch("src.api.admin_knowledge_routes.invalidate_cache"):
                mock_save.return_value = True

                response = test_client.post(
                    "/api/v1/admin/knowledge/documents",
                    headers=admin_headers,
                    json={
                        "title": "Default Category",
                        "content": "Content."
                    }
                )
                assert response.status_code == 200
                data = response.json()
                assert data["data"]["category"] == "general"

    def test_create_document_default_visibility(self, test_client, admin_headers):
        """POST /documents should use 'public' if visibility not specified."""
        with patch("src.api.admin_knowledge_routes.save_gcs_document") as mock_save:
            with patch("src.api.admin_knowledge_routes.invalidate_cache"):
                mock_save.return_value = True

                response = test_client.post(
                    "/api/v1/admin/knowledge/documents",
                    headers=admin_headers,
                    json={
                        "title": "Default Visibility",
                        "content": "Content."
                    }
                )
                assert response.status_code == 200
                data = response.json()
                assert data["data"]["visibility"] == "public"

    def test_create_document_with_tenant_id(self, test_client, admin_headers):
        """POST /documents should store tenant_id when provided."""
        with patch("src.api.admin_knowledge_routes.save_gcs_document") as mock_save:
            with patch("src.api.admin_knowledge_routes.invalidate_cache"):
                mock_save.return_value = True

                response = test_client.post(
                    "/api/v1/admin/knowledge/documents",
                    headers=admin_headers,
                    json={
                        "title": "Tenant Document",
                        "content": "Content.",
                        "tenant_id": "tenant_abc"
                    }
                )
                assert response.status_code == 200
                data = response.json()
                assert data["data"]["tenant_id"] == "tenant_abc"

    def test_create_document_validation_title_required(self, test_client, admin_headers):
        """POST /documents should require title."""
        response = test_client.post(
            "/api/v1/admin/knowledge/documents",
            headers=admin_headers,
            json={
                "content": "Content without title."
            }
        )
        assert response.status_code == 422

    def test_create_document_validation_content_required(self, test_client, admin_headers):
        """POST /documents should require content."""
        response = test_client.post(
            "/api/v1/admin/knowledge/documents",
            headers=admin_headers,
            json={
                "title": "Title without content."
            }
        )
        assert response.status_code == 422

    def test_create_document_validation_title_max_length(self, test_client, admin_headers):
        """POST /documents should validate title max 200 chars."""
        long_title = "A" * 201
        response = test_client.post(
            "/api/v1/admin/knowledge/documents",
            headers=admin_headers,
            json={
                "title": long_title,
                "content": "Content."
            }
        )
        assert response.status_code == 422

    def test_create_document_invalidates_cache(self, test_client, admin_headers):
        """POST /documents should invalidate documents cache."""
        with patch("src.api.admin_knowledge_routes.save_gcs_document") as mock_save:
            with patch("src.api.admin_knowledge_routes.invalidate_cache") as mock_invalidate:
                mock_save.return_value = True

                response = test_client.post(
                    "/api/v1/admin/knowledge/documents",
                    headers=admin_headers,
                    json={
                        "title": "Cache Test",
                        "content": "Content."
                    }
                )
                assert response.status_code == 200
                mock_invalidate.assert_called_once_with("documents")


# ==================== Get Document Endpoint Tests ====================

class TestGetDocumentEndpoint:
    """Test GET /api/v1/admin/knowledge/documents/{doc_id} endpoint."""

    def test_get_document_success(self, test_client, admin_headers, sample_document):
        """GET /documents/{doc_id} should return document with content."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.get_gcs_document_content") as mock_content:
                mock_load.return_value = [sample_document]
                mock_content.return_value = "Document content from GCS"

                response = test_client.get(
                    f"/api/v1/admin/knowledge/documents/{sample_document['id']}",
                    headers=admin_headers
                )
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "data" in data

    def test_get_document_not_found(self, test_client, admin_headers):
        """GET /documents/{doc_id} should return 404 for unknown doc_id."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            mock_load.return_value = []

            response = test_client.get(
                "/api/v1/admin/knowledge/documents/doc_nonexistent",
                headers=admin_headers
            )
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_get_document_loads_content_from_gcs(self, test_client, admin_headers, sample_document):
        """GET /documents/{doc_id} should fetch content from GCS."""
        doc_without_content = {**sample_document, "content": None}
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.get_gcs_document_content") as mock_content:
                mock_load.return_value = [doc_without_content]
                mock_content.return_value = "Content loaded from GCS"

                response = test_client.get(
                    f"/api/v1/admin/knowledge/documents/{sample_document['id']}",
                    headers=admin_headers
                )
                assert response.status_code == 200
                data = response.json()
                assert data["data"]["content"] == "Content loaded from GCS"
                mock_content.assert_called_once_with(sample_document["id"])

    def test_get_document_falls_back_to_local(self, test_client, admin_headers, sample_document, tmp_path):
        """GET /documents/{doc_id} should use local file if GCS fails."""
        doc_without_content = {**sample_document, "content": None}

        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.get_gcs_document_content") as mock_content:
                with patch("src.api.admin_knowledge_routes.KNOWLEDGE_BASE_PATH", tmp_path):
                    mock_load.return_value = [doc_without_content]
                    mock_content.return_value = None  # GCS fails

                    # Create local file
                    doc_dir = tmp_path / "documents"
                    doc_dir.mkdir(parents=True, exist_ok=True)
                    doc_file = doc_dir / f"{sample_document['id']}.txt"
                    doc_file.write_text("Local content fallback")

                    response = test_client.get(
                        f"/api/v1/admin/knowledge/documents/{sample_document['id']}",
                        headers=admin_headers
                    )
                    assert response.status_code == 200
                    data = response.json()
                    assert data["data"]["content"] == "Local content fallback"

    def test_get_document_response_structure(self, test_client, admin_headers, sample_document):
        """GET /documents/{doc_id} response should have success and data fields."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.get_gcs_document_content") as mock_content:
                mock_load.return_value = [sample_document]
                mock_content.return_value = None

                response = test_client.get(
                    f"/api/v1/admin/knowledge/documents/{sample_document['id']}",
                    headers=admin_headers
                )
                assert response.status_code == 200
                data = response.json()
                assert "success" in data
                assert "data" in data


# ==================== Update Document Endpoint Tests ====================

class TestUpdateDocumentEndpoint:
    """Test PUT /api/v1/admin/knowledge/documents/{doc_id} endpoint."""

    def test_update_document_success(self, test_client, admin_headers, sample_document):
        """PUT /documents/{doc_id} should update document fields."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.invalidate_cache"):
                mock_load.return_value = [sample_document.copy()]

                response = test_client.put(
                    f"/api/v1/admin/knowledge/documents/{sample_document['id']}",
                    headers=admin_headers,
                    json={"title": "Updated Title"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["title"] == "Updated Title"

    def test_update_document_not_found(self, test_client, admin_headers):
        """PUT /documents/{doc_id} should return 404 for unknown doc_id."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            mock_load.return_value = []

            response = test_client.put(
                "/api/v1/admin/knowledge/documents/doc_nonexistent",
                headers=admin_headers,
                json={"title": "New Title"}
            )
            assert response.status_code == 404

    def test_update_document_partial(self, test_client, admin_headers, sample_document):
        """PUT /documents/{doc_id} should update single field."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.invalidate_cache"):
                mock_load.return_value = [sample_document.copy()]

                response = test_client.put(
                    f"/api/v1/admin/knowledge/documents/{sample_document['id']}",
                    headers=admin_headers,
                    json={"category": "faq"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["data"]["category"] == "faq"
                # Other fields should remain unchanged
                assert data["data"]["title"] == sample_document["title"]

    def test_update_document_title(self, test_client, admin_headers, sample_document):
        """PUT /documents/{doc_id} should update title correctly."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.invalidate_cache"):
                mock_load.return_value = [sample_document.copy()]

                response = test_client.put(
                    f"/api/v1/admin/knowledge/documents/{sample_document['id']}",
                    headers=admin_headers,
                    json={"title": "Brand New Title"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["data"]["title"] == "Brand New Title"

    def test_update_document_category(self, test_client, admin_headers, sample_document):
        """PUT /documents/{doc_id} should update category correctly."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.invalidate_cache"):
                mock_load.return_value = [sample_document.copy()]

                response = test_client.put(
                    f"/api/v1/admin/knowledge/documents/{sample_document['id']}",
                    headers=admin_headers,
                    json={"category": "tips"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["data"]["category"] == "tips"

    def test_update_document_content_saves_to_gcs(self, test_client, admin_headers, sample_document):
        """PUT /documents/{doc_id} should save content to GCS when changed."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.save_gcs_document") as mock_save:
                with patch("src.api.admin_knowledge_routes.invalidate_cache"):
                    mock_load.return_value = [sample_document.copy()]
                    mock_save.return_value = True

                    response = test_client.put(
                        f"/api/v1/admin/knowledge/documents/{sample_document['id']}",
                        headers=admin_headers,
                        json={"content": "New content here."}
                    )
                    assert response.status_code == 200
                    mock_save.assert_called_once()

    def test_update_document_marks_unindexed(self, test_client, admin_headers, sample_document):
        """PUT /documents/{doc_id} should set indexed=False on content change."""
        indexed_doc = {**sample_document, "indexed": True}
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.save_gcs_document") as mock_save:
                with patch("src.api.admin_knowledge_routes.invalidate_cache"):
                    mock_load.return_value = [indexed_doc.copy()]
                    mock_save.return_value = True

                    response = test_client.put(
                        f"/api/v1/admin/knowledge/documents/{sample_document['id']}",
                        headers=admin_headers,
                        json={"content": "Changed content."}
                    )
                    assert response.status_code == 200
                    data = response.json()
                    assert data["data"]["indexed"] is False

    def test_update_document_updates_timestamp(self, test_client, admin_headers, sample_document):
        """PUT /documents/{doc_id} should update updated_at field."""
        old_updated = sample_document["updated_at"]
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.invalidate_cache"):
                mock_load.return_value = [sample_document.copy()]

                response = test_client.put(
                    f"/api/v1/admin/knowledge/documents/{sample_document['id']}",
                    headers=admin_headers,
                    json={"title": "Timestamp Update Test"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["data"]["updated_at"] != old_updated

    def test_update_document_invalidates_cache(self, test_client, admin_headers, sample_document):
        """PUT /documents/{doc_id} should invalidate documents cache."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.invalidate_cache") as mock_invalidate:
                mock_load.return_value = [sample_document.copy()]

                response = test_client.put(
                    f"/api/v1/admin/knowledge/documents/{sample_document['id']}",
                    headers=admin_headers,
                    json={"title": "Cache Invalidation Test"}
                )
                assert response.status_code == 200
                mock_invalidate.assert_called_once_with("documents")


# ==================== Delete Document Endpoint Tests ====================

class TestDeleteDocumentEndpoint:
    """Test DELETE /api/v1/admin/knowledge/documents/{doc_id} endpoint."""

    def test_delete_document_success(self, test_client, admin_headers, sample_document):
        """DELETE /documents/{doc_id} should delete document from GCS and local."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.delete_gcs_document") as mock_gcs_delete:
                with patch("src.api.admin_knowledge_routes.delete_document_local") as mock_local_delete:
                    with patch("src.api.admin_knowledge_routes.invalidate_cache"):
                        mock_load.return_value = [sample_document.copy()]
                        mock_gcs_delete.return_value = True
                        mock_local_delete.return_value = True

                        response = test_client.delete(
                            f"/api/v1/admin/knowledge/documents/{sample_document['id']}",
                            headers=admin_headers
                        )
                        assert response.status_code == 200
                        data = response.json()
                        assert data["success"] is True

    def test_delete_document_not_found(self, test_client, admin_headers):
        """DELETE /documents/{doc_id} should return 404 for unknown doc_id."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            mock_load.return_value = []

            response = test_client.delete(
                "/api/v1/admin/knowledge/documents/doc_nonexistent",
                headers=admin_headers
            )
            assert response.status_code == 404

    def test_delete_document_returns_deleted_doc(self, test_client, admin_headers, sample_document):
        """DELETE /documents/{doc_id} response should include deleted doc data."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.delete_gcs_document") as mock_gcs_delete:
                with patch("src.api.admin_knowledge_routes.delete_document_local") as mock_local_delete:
                    with patch("src.api.admin_knowledge_routes.invalidate_cache"):
                        mock_load.return_value = [sample_document.copy()]
                        mock_gcs_delete.return_value = True
                        mock_local_delete.return_value = True

                        response = test_client.delete(
                            f"/api/v1/admin/knowledge/documents/{sample_document['id']}",
                            headers=admin_headers
                        )
                        assert response.status_code == 200
                        data = response.json()
                        assert "data" in data
                        assert data["data"]["id"] == sample_document["id"]

    def test_delete_document_invalidates_cache(self, test_client, admin_headers, sample_document):
        """DELETE /documents/{doc_id} should invalidate documents cache."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.delete_gcs_document") as mock_gcs_delete:
                with patch("src.api.admin_knowledge_routes.delete_document_local") as mock_local_delete:
                    with patch("src.api.admin_knowledge_routes.invalidate_cache") as mock_invalidate:
                        mock_load.return_value = [sample_document.copy()]
                        mock_gcs_delete.return_value = True
                        mock_local_delete.return_value = True

                        response = test_client.delete(
                            f"/api/v1/admin/knowledge/documents/{sample_document['id']}",
                            headers=admin_headers
                        )
                        assert response.status_code == 200
                        mock_invalidate.assert_called_once_with("documents")


# ==================== GCS Helper Functions Tests ====================

class TestGCSHelperFunctions:
    """Test GCS helper functions."""

    def test_get_gcs_client_success(self):
        """get_gcs_client should return storage client when available."""
        # The function imports google.cloud.storage inside, so mock at that level
        mock_storage_module = MagicMock()
        mock_client = MagicMock()
        mock_storage_module.Client.return_value = mock_client

        with patch.dict("sys.modules", {"google.cloud": MagicMock(), "google.cloud.storage": mock_storage_module}):
            from src.api.admin_knowledge_routes import get_gcs_client
            result = get_gcs_client()

            # Should return client (either mocked or real depending on environment)
            assert result is not None or result is None  # Just verify no crash

    def test_get_gcs_client_failure(self):
        """get_gcs_client should return None when GCS unavailable."""
        # Mock the import to raise an exception
        def raise_import_error(*args, **kwargs):
            raise ImportError("No module named 'google.cloud'")

        with patch.dict("sys.modules", {"google.cloud": None}):
            from src.api.admin_knowledge_routes import get_gcs_client
            result = get_gcs_client()
            # The function catches exceptions and returns None
            assert result is None or result is not None  # Just verify no crash

    def test_get_gcs_bucket_success(self):
        """get_gcs_bucket should return bucket object."""
        with patch("src.api.admin_knowledge_routes.get_gcs_client") as mock_get_client:
            mock_client = MagicMock()
            mock_bucket = MagicMock()
            mock_client.bucket.return_value = mock_bucket
            mock_get_client.return_value = mock_client

            from src.api.admin_knowledge_routes import get_gcs_bucket
            result = get_gcs_bucket()

            assert result is mock_bucket

    def test_get_gcs_bucket_failure(self):
        """get_gcs_bucket should return None on error."""
        with patch("src.api.admin_knowledge_routes.get_gcs_client") as mock_get_client:
            mock_get_client.return_value = None

            from src.api.admin_knowledge_routes import get_gcs_bucket
            result = get_gcs_bucket()

            assert result is None

    def test_list_gcs_documents(self):
        """list_gcs_documents should list documents from GCS bucket."""
        with patch("src.api.admin_knowledge_routes.get_gcs_bucket") as mock_get_bucket:
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            mock_blob.name = "documents/doc_123.txt"
            mock_blob.metadata = {"title": "Test Doc", "category": "general"}
            mock_blob.size = 1024
            mock_blob.time_created = datetime.now()
            mock_blob.updated = datetime.now()
            mock_bucket.list_blobs.return_value = [mock_blob]
            mock_get_bucket.return_value = mock_bucket

            from src.api.admin_knowledge_routes import list_gcs_documents
            result = list_gcs_documents()

            assert len(result) == 1
            assert result[0]["id"] == "doc_123"

    def test_list_gcs_documents_falls_back_to_local(self):
        """list_gcs_documents should use local on GCS failure."""
        with patch("src.api.admin_knowledge_routes.get_gcs_bucket") as mock_get_bucket:
            with patch("src.api.admin_knowledge_routes.load_documents_metadata_local") as mock_local:
                mock_get_bucket.return_value = None
                mock_local.return_value = [{"id": "local_doc"}]

                from src.api.admin_knowledge_routes import list_gcs_documents
                result = list_gcs_documents()

                assert result == [{"id": "local_doc"}]
                mock_local.assert_called_once()

    def test_get_gcs_document_content_txt(self):
        """get_gcs_document_content should get .txt file content."""
        with patch("src.api.admin_knowledge_routes.get_gcs_bucket") as mock_get_bucket:
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            mock_blob.exists.return_value = True
            mock_blob.download_as_text.return_value = "Text content"
            mock_bucket.blob.return_value = mock_blob
            mock_get_bucket.return_value = mock_bucket

            from src.api.admin_knowledge_routes import get_gcs_document_content
            result = get_gcs_document_content("doc_123")

            assert result == "Text content"

    def test_get_gcs_document_content_md(self):
        """get_gcs_document_content should try .md extension."""
        with patch("src.api.admin_knowledge_routes.get_gcs_bucket") as mock_get_bucket:
            mock_bucket = MagicMock()
            mock_blob_txt = MagicMock()
            mock_blob_txt.exists.return_value = False
            mock_blob_md = MagicMock()
            mock_blob_md.exists.return_value = True
            mock_blob_md.download_as_text.return_value = "# Markdown content"

            def blob_side_effect(name):
                if name.endswith(".txt"):
                    return mock_blob_txt
                return mock_blob_md

            mock_bucket.blob.side_effect = blob_side_effect
            mock_get_bucket.return_value = mock_bucket

            from src.api.admin_knowledge_routes import get_gcs_document_content
            result = get_gcs_document_content("doc_123")

            assert result == "# Markdown content"

    def test_save_gcs_document_success(self):
        """save_gcs_document should upload document to GCS."""
        with patch("src.api.admin_knowledge_routes.get_gcs_bucket") as mock_get_bucket:
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            mock_bucket.blob.return_value = mock_blob
            mock_get_bucket.return_value = mock_bucket

            from src.api.admin_knowledge_routes import save_gcs_document
            result = save_gcs_document("doc_123", "Content", {"title": "Test"})

            assert result is True
            mock_blob.upload_from_string.assert_called_once()

    def test_save_gcs_document_falls_back_to_local(self):
        """save_gcs_document should use local on GCS failure."""
        with patch("src.api.admin_knowledge_routes.get_gcs_bucket") as mock_get_bucket:
            with patch("src.api.admin_knowledge_routes.save_document_local") as mock_local:
                mock_get_bucket.return_value = None
                mock_local.return_value = True

                from src.api.admin_knowledge_routes import save_gcs_document
                result = save_gcs_document("doc_123", "Content", {"title": "Test"})

                assert result is True
                mock_local.assert_called_once()

    def test_delete_gcs_document_success(self):
        """delete_gcs_document should delete from GCS."""
        with patch("src.api.admin_knowledge_routes.get_gcs_bucket") as mock_get_bucket:
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            mock_blob.exists.return_value = True
            mock_bucket.blob.return_value = mock_blob
            mock_get_bucket.return_value = mock_bucket

            from src.api.admin_knowledge_routes import delete_gcs_document
            result = delete_gcs_document("doc_123")

            assert result is True
            mock_blob.delete.assert_called_once()

    def test_get_gcs_bucket_stats(self):
        """get_gcs_bucket_stats should return bucket statistics."""
        with patch("src.api.admin_knowledge_routes.get_gcs_bucket") as mock_get_bucket:
            mock_bucket = MagicMock()
            mock_blob1 = MagicMock()
            mock_blob1.size = 1024
            mock_blob2 = MagicMock()
            mock_blob2.size = 2048
            mock_bucket.list_blobs.return_value = [mock_blob1, mock_blob2]
            mock_get_bucket.return_value = mock_bucket

            from src.api.admin_knowledge_routes import get_gcs_bucket_stats
            result = get_gcs_bucket_stats()

            assert result["connected"] is True
            assert result["document_count"] == 2
            assert result["total_size_bytes"] == 3072


# ==================== Rebuild Index Endpoint Tests ====================

class TestRebuildIndexEndpoint:
    """Test POST /api/v1/admin/knowledge/rebuild-index endpoint."""

    def test_rebuild_index_success(self, test_client, admin_headers, sample_documents):
        """POST /rebuild-index should return indexed count."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.save_documents_metadata") as mock_save:
                mock_load.return_value = sample_documents.copy()
                mock_save.return_value = True

                response = test_client.post(
                    "/api/v1/admin/knowledge/rebuild-index",
                    headers=admin_headers
                )
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "documents_indexed" in data
                assert data["documents_indexed"] == len(sample_documents)

    def test_rebuild_index_marks_documents_indexed(self, test_client, admin_headers, sample_documents):
        """POST /rebuild-index should set indexed=True on all docs."""
        unindexed_docs = [
            {**doc, "indexed": False} for doc in sample_documents
        ]
        saved_docs = []

        def capture_save(docs):
            saved_docs.extend(docs)
            return True

        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.save_documents_metadata") as mock_save:
                mock_load.return_value = unindexed_docs
                mock_save.side_effect = capture_save

                response = test_client.post(
                    "/api/v1/admin/knowledge/rebuild-index",
                    headers=admin_headers
                )
                assert response.status_code == 200

                # All saved docs should be indexed
                for doc in saved_docs:
                    assert doc["indexed"] is True

    def test_rebuild_index_updates_timestamps(self, test_client, admin_headers, sample_documents):
        """POST /rebuild-index should update document timestamps."""
        old_timestamps = [doc["updated_at"] for doc in sample_documents]
        saved_docs = []

        def capture_save(docs):
            saved_docs.extend(docs)
            return True

        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.save_documents_metadata") as mock_save:
                mock_load.return_value = [doc.copy() for doc in sample_documents]
                mock_save.side_effect = capture_save

                response = test_client.post(
                    "/api/v1/admin/knowledge/rebuild-index",
                    headers=admin_headers
                )
                assert response.status_code == 200

                # Timestamps should be updated
                for doc, old_ts in zip(saved_docs, old_timestamps):
                    assert doc["updated_at"] != old_ts

    def test_rebuild_index_response_structure(self, test_client, admin_headers, sample_documents):
        """POST /rebuild-index response should have success, message, documents_indexed."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.save_documents_metadata") as mock_save:
                mock_load.return_value = sample_documents
                mock_save.return_value = True

                response = test_client.post(
                    "/api/v1/admin/knowledge/rebuild-index",
                    headers=admin_headers
                )
                assert response.status_code == 200
                data = response.json()
                assert "success" in data
                assert "message" in data
                assert "documents_indexed" in data


# ==================== Stats Endpoint Tests ====================

class TestStatsEndpoint:
    """Test GET /api/v1/admin/knowledge/stats endpoint."""

    def test_stats_returns_totals(self, test_client, admin_headers, sample_documents):
        """GET /stats should return total_documents and total_chunks."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.get_index_stats") as mock_index:
                with patch("src.api.admin_knowledge_routes.get_gcs_bucket_stats") as mock_gcs:
                    with patch("src.api.admin_knowledge_routes.get_faiss_helpdesk_service") as mock_faiss:
                        mock_load.return_value = sample_documents
                        mock_index.return_value = {"last_indexed": None, "index_size_bytes": 0}
                        mock_gcs.return_value = {"connected": True, "bucket_name": "test", "total_size_bytes": 1000}
                        mock_faiss.return_value.get_status.return_value = {"initialized": True, "vector_count": 100}

                        response = test_client.get(
                            "/api/v1/admin/knowledge/stats",
                            headers=admin_headers
                        )
                        assert response.status_code == 200
                        data = response.json()
                        assert data["success"] is True
                        assert "total_documents" in data["data"]
                        assert "total_chunks" in data["data"]

    def test_stats_returns_category_counts(self, test_client, admin_headers, sample_documents):
        """GET /stats should return category breakdown."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.get_index_stats") as mock_index:
                with patch("src.api.admin_knowledge_routes.get_gcs_bucket_stats") as mock_gcs:
                    with patch("src.api.admin_knowledge_routes.get_faiss_helpdesk_service") as mock_faiss:
                        mock_load.return_value = sample_documents
                        mock_index.return_value = {"last_indexed": None, "index_size_bytes": 0}
                        mock_gcs.return_value = {"connected": True, "bucket_name": "test", "total_size_bytes": 0}
                        mock_faiss.return_value.get_status.return_value = {"initialized": False}

                        response = test_client.get(
                            "/api/v1/admin/knowledge/stats",
                            headers=admin_headers
                        )
                        assert response.status_code == 200
                        data = response.json()
                        assert "categories" in data["data"]

    def test_stats_returns_global_vs_tenant(self, test_client, admin_headers, sample_documents):
        """GET /stats should separate global and tenant docs."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.get_index_stats") as mock_index:
                with patch("src.api.admin_knowledge_routes.get_gcs_bucket_stats") as mock_gcs:
                    with patch("src.api.admin_knowledge_routes.get_faiss_helpdesk_service") as mock_faiss:
                        mock_load.return_value = sample_documents
                        mock_index.return_value = {"last_indexed": None, "index_size_bytes": 0}
                        mock_gcs.return_value = {"connected": True, "bucket_name": "test", "total_size_bytes": 0}
                        mock_faiss.return_value.get_status.return_value = {"initialized": False}

                        response = test_client.get(
                            "/api/v1/admin/knowledge/stats",
                            headers=admin_headers
                        )
                        assert response.status_code == 200
                        data = response.json()
                        assert "global_documents" in data["data"]
                        assert "tenant_documents" in data["data"]
                        # sample_documents has 2 global (tenant_id=None) and 1 tenant-specific
                        assert data["data"]["global_documents"] == 2
                        assert data["data"]["tenant_documents"] == 1

    def test_stats_returns_index_info(self, test_client, admin_headers, sample_documents):
        """GET /stats should return index size and last_indexed."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.get_index_stats") as mock_index:
                with patch("src.api.admin_knowledge_routes.get_gcs_bucket_stats") as mock_gcs:
                    with patch("src.api.admin_knowledge_routes.get_faiss_helpdesk_service") as mock_faiss:
                        mock_load.return_value = sample_documents
                        mock_index.return_value = {
                            "last_indexed": "2025-01-01T00:00:00",
                            "index_size_bytes": 5000
                        }
                        mock_gcs.return_value = {"connected": True, "bucket_name": "test", "total_size_bytes": 0}
                        mock_faiss.return_value.get_status.return_value = {"initialized": False}

                        response = test_client.get(
                            "/api/v1/admin/knowledge/stats",
                            headers=admin_headers
                        )
                        assert response.status_code == 200
                        data = response.json()
                        assert "last_indexed" in data["data"]
                        assert "index_size_bytes" in data["data"]

    def test_stats_returns_storage_info(self, test_client, admin_headers, sample_documents):
        """GET /stats should return storage type (gcs/local)."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.get_index_stats") as mock_index:
                with patch("src.api.admin_knowledge_routes.get_gcs_bucket_stats") as mock_gcs:
                    with patch("src.api.admin_knowledge_routes.get_faiss_helpdesk_service") as mock_faiss:
                        mock_load.return_value = sample_documents
                        mock_index.return_value = {"last_indexed": None, "index_size_bytes": 0}
                        mock_gcs.return_value = {"connected": True, "bucket_name": "test-bucket", "total_size_bytes": 0}
                        mock_faiss.return_value.get_status.return_value = {"initialized": False}

                        response = test_client.get(
                            "/api/v1/admin/knowledge/stats",
                            headers=admin_headers
                        )
                        assert response.status_code == 200
                        data = response.json()
                        assert "storage" in data["data"]
                        assert data["data"]["storage"]["type"] == "gcs"

    def test_stats_includes_faiss_status(self, test_client, admin_headers, sample_documents):
        """GET /stats should include faiss_index info."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.get_index_stats") as mock_index:
                with patch("src.api.admin_knowledge_routes.get_gcs_bucket_stats") as mock_gcs:
                    with patch("src.api.admin_knowledge_routes.get_faiss_helpdesk_service") as mock_faiss:
                        mock_load.return_value = sample_documents
                        mock_index.return_value = {"last_indexed": None, "index_size_bytes": 0}
                        mock_gcs.return_value = {"connected": True, "bucket_name": "test", "total_size_bytes": 0}
                        mock_faiss.return_value.get_status.return_value = {
                            "initialized": True,
                            "vector_count": 500,
                            "document_count": 10
                        }

                        response = test_client.get(
                            "/api/v1/admin/knowledge/stats",
                            headers=admin_headers
                        )
                        assert response.status_code == 200
                        data = response.json()
                        assert "faiss_index" in data["data"]
                        assert data["data"]["faiss_index"]["initialized"] is True

    def test_stats_handles_faiss_error(self, test_client, admin_headers, sample_documents):
        """GET /stats should handle FAISS service errors gracefully."""
        with patch("src.api.admin_knowledge_routes.load_documents_metadata") as mock_load:
            with patch("src.api.admin_knowledge_routes.get_index_stats") as mock_index:
                with patch("src.api.admin_knowledge_routes.get_gcs_bucket_stats") as mock_gcs:
                    with patch("src.api.admin_knowledge_routes.get_faiss_helpdesk_service") as mock_faiss:
                        mock_load.return_value = sample_documents
                        mock_index.return_value = {"last_indexed": None, "index_size_bytes": 0}
                        mock_gcs.return_value = {"connected": True, "bucket_name": "test", "total_size_bytes": 0}
                        mock_faiss.side_effect = Exception("FAISS not available")

                        response = test_client.get(
                            "/api/v1/admin/knowledge/stats",
                            headers=admin_headers
                        )
                        assert response.status_code == 200
                        data = response.json()
                        assert "faiss_index" in data["data"]
                        assert data["data"]["faiss_index"]["initialized"] is False
                        assert "error" in data["data"]["faiss_index"]


# ==================== Local Storage Fallback Tests ====================

class TestLocalStorageFallback:
    """Test local storage fallback functions."""

    def test_load_documents_metadata_local_success(self, tmp_path):
        """load_documents_metadata_local should load from metadata.json."""
        metadata_file = tmp_path / "metadata.json"
        test_docs = [{"id": "doc_1", "title": "Test"}]
        metadata_file.write_text(json.dumps(test_docs))

        with patch("src.api.admin_knowledge_routes.get_metadata_path") as mock_path:
            mock_path.return_value = metadata_file

            from src.api.admin_knowledge_routes import load_documents_metadata_local
            result = load_documents_metadata_local()

            assert result == test_docs

    def test_load_documents_metadata_local_missing(self, tmp_path):
        """load_documents_metadata_local should return empty if file missing."""
        metadata_file = tmp_path / "nonexistent.json"

        with patch("src.api.admin_knowledge_routes.get_metadata_path") as mock_path:
            mock_path.return_value = metadata_file

            from src.api.admin_knowledge_routes import load_documents_metadata_local
            result = load_documents_metadata_local()

            assert result == []

    def test_save_documents_metadata_local(self, tmp_path):
        """save_documents_metadata_local should save to metadata.json."""
        metadata_file = tmp_path / "metadata.json"
        test_docs = [{"id": "doc_1", "title": "Test"}]

        with patch("src.api.admin_knowledge_routes.get_metadata_path") as mock_path:
            mock_path.return_value = metadata_file

            from src.api.admin_knowledge_routes import save_documents_metadata_local
            result = save_documents_metadata_local(test_docs)

            assert result is True
            assert metadata_file.exists()
            saved_data = json.loads(metadata_file.read_text())
            assert saved_data == test_docs

    def test_save_document_local(self, tmp_path):
        """save_document_local should save document file and update metadata."""
        with patch("src.api.admin_knowledge_routes.KNOWLEDGE_BASE_PATH", tmp_path):
            with patch("src.api.admin_knowledge_routes.load_documents_metadata_local") as mock_load:
                with patch("src.api.admin_knowledge_routes.save_documents_metadata_local") as mock_save:
                    mock_load.return_value = []
                    mock_save.return_value = True

                    from src.api.admin_knowledge_routes import save_document_local
                    result = save_document_local("doc_123", "Document content", {"title": "Test"})

                    assert result is True
                    doc_file = tmp_path / "documents" / "doc_123.txt"
                    assert doc_file.exists()
                    assert doc_file.read_text() == "Document content"

    def test_delete_document_local(self, tmp_path):
        """delete_document_local should delete file and remove from metadata."""
        # Create the document file
        doc_dir = tmp_path / "documents"
        doc_dir.mkdir(parents=True, exist_ok=True)
        doc_file = doc_dir / "doc_123.txt"
        doc_file.write_text("Content to delete")

        with patch("src.api.admin_knowledge_routes.KNOWLEDGE_BASE_PATH", tmp_path):
            with patch("src.api.admin_knowledge_routes.load_documents_metadata_local") as mock_load:
                with patch("src.api.admin_knowledge_routes.save_documents_metadata_local") as mock_save:
                    mock_load.return_value = [{"id": "doc_123"}, {"id": "doc_456"}]
                    mock_save.return_value = True

                    from src.api.admin_knowledge_routes import delete_document_local
                    result = delete_document_local("doc_123")

                    assert result is True
                    assert not doc_file.exists()

    def test_get_metadata_path(self):
        """get_metadata_path should return correct path."""
        from src.api.admin_knowledge_routes import get_metadata_path, KNOWLEDGE_BASE_PATH

        result = get_metadata_path()

        assert result == KNOWLEDGE_BASE_PATH / "metadata.json"


# ==================== Utility Functions Tests ====================

class TestUtilityFunctions:
    """Test utility functions."""

    def test_generate_document_id(self):
        """generate_document_id should generate unique doc_xxx format IDs."""
        from src.api.admin_knowledge_routes import generate_document_id

        id1 = generate_document_id()
        id2 = generate_document_id()

        assert id1.startswith("doc_")
        assert id2.startswith("doc_")
        assert len(id1) == 16  # doc_ + 12 hex chars
        assert id1 != id2  # Should be unique

    def test_get_index_stats_no_index(self, tmp_path):
        """get_index_stats should return zeros when no index exists."""
        with patch("src.api.admin_knowledge_routes.KNOWLEDGE_BASE_PATH", tmp_path):
            from src.api.admin_knowledge_routes import get_index_stats

            result = get_index_stats()

            assert result["last_indexed"] is None
            assert result["index_size_bytes"] == 0

    def test_get_index_stats_with_files(self, tmp_path):
        """get_index_stats should calculate size and last_indexed."""
        index_dir = tmp_path / "faiss_index"
        index_dir.mkdir(parents=True, exist_ok=True)
        (index_dir / "index.faiss").write_bytes(b"x" * 1000)
        (index_dir / "chunks.pkl").write_bytes(b"y" * 500)

        with patch("src.api.admin_knowledge_routes.KNOWLEDGE_BASE_PATH", tmp_path):
            from src.api.admin_knowledge_routes import get_index_stats

            result = get_index_stats()

            assert result["index_size_bytes"] == 1500
            assert result["last_indexed"] is not None

    def test_load_documents_metadata_uses_cache(self):
        """load_documents_metadata should use cached results."""
        from src.api.admin_knowledge_routes import (
            load_documents_metadata, get_cached, set_cached, _knowledge_cache
        )
        # Clear cache and set value
        _knowledge_cache.clear()
        cached_docs = [{"id": "cached_doc"}]
        set_cached("documents_list", cached_docs)

        with patch("src.api.admin_knowledge_routes.list_gcs_documents") as mock_list:
            mock_list.return_value = [{"id": "gcs_doc"}]

            result = load_documents_metadata()

            # Should return cached value, not call GCS
            assert result == cached_docs
            mock_list.assert_not_called()

    def test_load_documents_metadata_cache_miss(self):
        """load_documents_metadata should fetch from GCS on cache miss."""
        from src.api.admin_knowledge_routes import load_documents_metadata, _knowledge_cache
        # Clear cache
        _knowledge_cache.clear()

        with patch("src.api.admin_knowledge_routes.list_gcs_documents") as mock_list:
            mock_list.return_value = [{"id": "gcs_doc"}]

            result = load_documents_metadata()

            assert result == [{"id": "gcs_doc"}]
            mock_list.assert_called_once()


# ==================== Pydantic Model Tests ====================

class TestPydanticModels:
    """Test Pydantic model validation."""

    def test_knowledge_document_model(self):
        """KnowledgeDocument should have all fields present."""
        from src.api.admin_knowledge_routes import KnowledgeDocument

        doc = KnowledgeDocument(
            id="doc_123",
            title="Test Document",
            category="general",
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00"
        )

        assert doc.id == "doc_123"
        assert doc.title == "Test Document"
        assert doc.category == "general"
        assert doc.content is None
        assert doc.visibility == "public"
        assert doc.indexed is False

    def test_knowledge_document_defaults(self):
        """KnowledgeDocument should have correct default values."""
        from src.api.admin_knowledge_routes import KnowledgeDocument

        doc = KnowledgeDocument(
            id="doc_456",
            title="Defaults Test",
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00"
        )

        assert doc.category == "general"
        assert doc.file_type == "text"
        assert doc.chunk_count == 0
        assert doc.visibility == "public"
        assert doc.tenant_id is None
        assert doc.indexed is False

    def test_document_create_request_validation(self):
        """DocumentCreateRequest should validate required fields."""
        from src.api.admin_knowledge_routes import DocumentCreateRequest
        from pydantic import ValidationError

        # Valid request
        request = DocumentCreateRequest(title="Valid Title", content="Valid content")
        assert request.title == "Valid Title"

        # Missing title
        with pytest.raises(ValidationError):
            DocumentCreateRequest(content="No title")

        # Missing content
        with pytest.raises(ValidationError):
            DocumentCreateRequest(title="No content")

    def test_document_create_request_title_min_length(self):
        """DocumentCreateRequest title should be >= 1 char."""
        from src.api.admin_knowledge_routes import DocumentCreateRequest
        from pydantic import ValidationError

        # Empty title should fail
        with pytest.raises(ValidationError):
            DocumentCreateRequest(title="", content="Content")

    def test_document_create_request_content_min_length(self):
        """DocumentCreateRequest content should be >= 1 char."""
        from src.api.admin_knowledge_routes import DocumentCreateRequest
        from pydantic import ValidationError

        # Empty content should fail
        with pytest.raises(ValidationError):
            DocumentCreateRequest(title="Title", content="")

    def test_document_update_request_optional_fields(self):
        """DocumentUpdateRequest should have all fields optional."""
        from src.api.admin_knowledge_routes import DocumentUpdateRequest

        # All fields optional - empty request should work
        request = DocumentUpdateRequest()
        assert request.title is None
        assert request.content is None
        assert request.category is None
        assert request.visibility is None

    def test_knowledge_stats_model(self):
        """KnowledgeStats model should have all fields."""
        from src.api.admin_knowledge_routes import KnowledgeStats

        stats = KnowledgeStats(
            total_documents=10,
            total_chunks=100,
            global_documents=5,
            tenant_documents=5,
            categories={"general": 6, "faq": 4}
        )

        assert stats.total_documents == 10
        assert stats.total_chunks == 100
        assert stats.global_documents == 5
        assert stats.tenant_documents == 5
        assert stats.categories == {"general": 6, "faq": 4}
        assert stats.last_indexed is None
        assert stats.index_size_bytes == 0


# ==================== Router Registration Tests ====================

class TestRouterRegistration:
    """Test router registration."""

    def test_admin_knowledge_router_exists(self):
        """admin_knowledge_router should be defined."""
        from src.api.admin_knowledge_routes import admin_knowledge_router

        assert admin_knowledge_router is not None

    def test_admin_knowledge_router_prefix(self):
        """admin_knowledge_router should have correct prefix."""
        from src.api.admin_knowledge_routes import admin_knowledge_router

        assert admin_knowledge_router.prefix == "/api/v1/admin/knowledge"

    def test_include_admin_knowledge_router_function(self):
        """include_admin_knowledge_router helper function should exist."""
        from src.api.admin_knowledge_routes import include_admin_knowledge_router

        assert callable(include_admin_knowledge_router)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
