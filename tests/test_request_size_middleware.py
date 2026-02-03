"""
Request Size Middleware Tests

Tests for the request body size limit middleware.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestRequestSizeMiddlewareConstants:
    """Tests for request size middleware constants."""

    def test_default_max_size_is_10mb(self):
        """DEFAULT_MAX_SIZE should be 10 MB."""
        from src.middleware.request_size_middleware import DEFAULT_MAX_SIZE

        assert DEFAULT_MAX_SIZE == 10 * 1024 * 1024

    def test_upload_max_size_is_50mb(self):
        """UPLOAD_MAX_SIZE should be 50 MB."""
        from src.middleware.request_size_middleware import UPLOAD_MAX_SIZE

        assert UPLOAD_MAX_SIZE == 50 * 1024 * 1024

    def test_upload_prefixes_defined(self):
        """UPLOAD_PREFIXES should be defined."""
        from src.middleware.request_size_middleware import UPLOAD_PREFIXES

        assert isinstance(UPLOAD_PREFIXES, tuple)
        assert len(UPLOAD_PREFIXES) > 0

    def test_upload_prefixes_include_knowledge(self):
        """Upload prefixes should include knowledge endpoints."""
        from src.middleware.request_size_middleware import UPLOAD_PREFIXES

        has_knowledge = any('knowledge' in prefix for prefix in UPLOAD_PREFIXES)
        assert has_knowledge


class TestRequestSizeMiddlewareIntegration:
    """Integration tests for RequestSizeMiddleware."""

    @pytest.fixture
    def app_with_middleware(self):
        """Create a test app with request size middleware."""
        from src.middleware.request_size_middleware import RequestSizeMiddleware

        app = FastAPI()
        app.add_middleware(RequestSizeMiddleware)

        @app.post("/test")
        async def test_route():
            return {"status": "ok"}

        @app.post("/api/v1/knowledge/upload")
        async def upload_route():
            return {"status": "uploaded"}

        return app

    @pytest.fixture
    def test_client(self, app_with_middleware):
        """Create test client."""
        return TestClient(app_with_middleware, raise_server_exceptions=False)

    def test_allows_small_requests(self, test_client):
        """Should allow requests below the size limit."""
        response = test_client.post(
            "/test",
            content=b"small body",
            headers={"Content-Length": "10"}
        )

        assert response.status_code == 200

    def test_rejects_oversized_requests(self, test_client):
        """Should return 413 for oversized requests."""
        # Claim a huge content length (1 GB)
        response = test_client.post(
            "/test",
            headers={"Content-Length": str(1024 * 1024 * 1024)}
        )

        assert response.status_code == 413
        assert "too large" in response.json()["detail"].lower()

    def test_rejects_invalid_content_length(self, test_client):
        """Should return 400 for invalid Content-Length header."""
        response = test_client.post(
            "/test",
            headers={"Content-Length": "not-a-number"}
        )

        assert response.status_code == 400
        assert "Invalid Content-Length" in response.json()["detail"]

    def test_allows_larger_uploads_on_upload_paths(self, test_client):
        """Should allow larger files on upload endpoints."""
        # 15 MB - over general limit but under upload limit
        response = test_client.post(
            "/api/v1/knowledge/upload",
            headers={"Content-Length": str(15 * 1024 * 1024)}
        )

        # Should NOT be 413 (within upload limit)
        assert response.status_code != 413

    def test_rejects_huge_uploads(self, test_client):
        """Should reject uploads over 50 MB."""
        # 100 MB - over both limits
        response = test_client.post(
            "/api/v1/knowledge/upload",
            headers={"Content-Length": str(100 * 1024 * 1024)}
        )

        assert response.status_code == 413

    def test_allows_requests_without_content_length(self, test_client):
        """Should allow requests without Content-Length header."""
        # GET requests typically don't have Content-Length
        response = test_client.get("/test")

        # May be 404/405 since it's a POST endpoint, but not 413
        assert response.status_code != 413


class TestSizeLimitLogic:
    """Tests for size limit calculation logic."""

    def test_general_endpoint_uses_default_limit(self):
        """Non-upload endpoints should use DEFAULT_MAX_SIZE."""
        from src.middleware.request_size_middleware import (
            DEFAULT_MAX_SIZE, UPLOAD_MAX_SIZE, UPLOAD_PREFIXES
        )

        # Regular path should not match upload prefixes
        path = "/api/v1/quotes"
        matches_upload = any(path.startswith(p) for p in UPLOAD_PREFIXES)

        assert not matches_upload

    def test_upload_endpoint_uses_upload_limit(self):
        """Upload endpoints should use UPLOAD_MAX_SIZE."""
        from src.middleware.request_size_middleware import UPLOAD_PREFIXES

        # Knowledge upload path should match
        path = "/api/v1/knowledge/upload/file.pdf"
        matches_upload = any(path.startswith(p) for p in UPLOAD_PREFIXES)

        assert matches_upload

    def test_documents_endpoint_uses_upload_limit(self):
        """Documents endpoint should use UPLOAD_MAX_SIZE."""
        from src.middleware.request_size_middleware import UPLOAD_PREFIXES

        path = "/api/v1/knowledge/documents/123"
        matches_upload = any(path.startswith(p) for p in UPLOAD_PREFIXES)

        assert matches_upload
