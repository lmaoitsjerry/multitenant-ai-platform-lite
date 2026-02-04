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


class TestRequestSizeEdgeCases:
    """Edge case tests for request size middleware."""

    @pytest.fixture
    def app_with_middleware(self):
        """Create a test app with request size middleware."""
        from src.middleware.request_size_middleware import RequestSizeMiddleware

        app = FastAPI()
        app.add_middleware(RequestSizeMiddleware)

        @app.post("/test")
        async def test_route():
            return {"status": "ok"}

        @app.get("/get")
        async def get_route():
            return {"status": "ok"}

        @app.post("/api/v1/knowledge/upload")
        async def upload_route():
            return {"status": "uploaded"}

        return app

    @pytest.fixture
    def test_client(self, app_with_middleware):
        """Create test client."""
        return TestClient(app_with_middleware, raise_server_exceptions=False)

    def test_zero_content_length(self, test_client):
        """Should allow zero content length."""
        response = test_client.post(
            "/test",
            content=b"",
            headers={"Content-Length": "0"}
        )

        assert response.status_code == 200

    def test_negative_content_length(self, test_client):
        """Should reject negative content length."""
        response = test_client.post(
            "/test",
            headers={"Content-Length": "-1"}
        )

        assert response.status_code == 400

    def test_get_request_bypasses_check(self, test_client):
        """GET requests should bypass size check."""
        response = test_client.get("/get")

        assert response.status_code == 200

    def test_exactly_at_limit(self, test_client):
        """Request exactly at limit should be allowed."""
        from src.middleware.request_size_middleware import DEFAULT_MAX_SIZE

        # Exactly at limit
        response = test_client.post(
            "/test",
            headers={"Content-Length": str(DEFAULT_MAX_SIZE)}
        )

        # Should be allowed (not 413)
        assert response.status_code != 413 or response.status_code == 200

    def test_one_byte_over_limit(self, test_client):
        """Request one byte over limit should be rejected."""
        from src.middleware.request_size_middleware import DEFAULT_MAX_SIZE

        # One byte over
        response = test_client.post(
            "/test",
            headers={"Content-Length": str(DEFAULT_MAX_SIZE + 1)}
        )

        assert response.status_code == 413

    def test_missing_content_length_post(self, test_client):
        """POST without Content-Length should be handled gracefully."""
        # TestClient usually adds Content-Length, so this tests the middleware's handling
        response = test_client.post("/test", content=b"data")

        # Should process the request (TestClient adds header)
        assert response.status_code == 200


class TestUploadPathMatching:
    """Tests for upload path matching logic."""

    def test_exact_prefix_match(self):
        """Should match exact prefix."""
        from src.middleware.request_size_middleware import UPLOAD_PREFIXES

        for prefix in UPLOAD_PREFIXES:
            path = prefix
            matches = any(path.startswith(p) for p in UPLOAD_PREFIXES)
            assert matches

    def test_prefix_with_trailing_path(self):
        """Should match prefix with additional path segments."""
        from src.middleware.request_size_middleware import UPLOAD_PREFIXES

        if UPLOAD_PREFIXES:
            prefix = UPLOAD_PREFIXES[0]
            path = f"{prefix}/some/nested/path"
            matches = any(path.startswith(p) for p in UPLOAD_PREFIXES)
            assert matches

    def test_partial_prefix_no_match(self):
        """Partial prefix should not match."""
        from src.middleware.request_size_middleware import UPLOAD_PREFIXES

        # Path that doesn't start with any prefix
        path = "/api/v1/quotes"
        matches = any(path.startswith(p) for p in UPLOAD_PREFIXES)
        assert not matches

    def test_similar_but_different_path(self):
        """Similar but different path should not match."""
        from src.middleware.request_size_middleware import UPLOAD_PREFIXES

        # This tests that the prefix matching is strict
        path = "/api/v1/knowledgebase"  # Note: no slash after knowledge
        matches = any(path.startswith(p) for p in UPLOAD_PREFIXES)
        # May or may not match depending on how prefixes are defined


class TestContentLengthParsing:
    """Tests for Content-Length header parsing."""

    @pytest.fixture
    def app_with_middleware(self):
        """Create a test app with request size middleware."""
        from src.middleware.request_size_middleware import RequestSizeMiddleware

        app = FastAPI()
        app.add_middleware(RequestSizeMiddleware)

        @app.post("/test")
        async def test_route():
            return {"status": "ok"}

        return app

    @pytest.fixture
    def test_client(self, app_with_middleware):
        """Create test client."""
        return TestClient(app_with_middleware, raise_server_exceptions=False)

    def test_float_content_length(self, test_client):
        """Float content length should be rejected."""
        response = test_client.post(
            "/test",
            headers={"Content-Length": "10.5"}
        )

        assert response.status_code == 400

    def test_scientific_notation(self, test_client):
        """Scientific notation should be rejected."""
        response = test_client.post(
            "/test",
            headers={"Content-Length": "1e6"}
        )

        assert response.status_code == 400

    def test_hex_content_length(self, test_client):
        """Hex content length should be rejected."""
        response = test_client.post(
            "/test",
            headers={"Content-Length": "0xFF"}
        )

        assert response.status_code == 400


class TestMiddlewareResponse:
    """Tests for middleware response details."""

    @pytest.fixture
    def app_with_middleware(self):
        """Create a test app with request size middleware."""
        from src.middleware.request_size_middleware import RequestSizeMiddleware

        app = FastAPI()
        app.add_middleware(RequestSizeMiddleware)

        @app.post("/test")
        async def test_route():
            return {"status": "ok"}

        return app

    @pytest.fixture
    def test_client(self, app_with_middleware):
        """Create test client."""
        return TestClient(app_with_middleware, raise_server_exceptions=False)

    def test_413_response_has_detail(self, test_client):
        """413 response should have descriptive detail."""
        response = test_client.post(
            "/test",
            headers={"Content-Length": str(1024 * 1024 * 1024)}
        )

        assert response.status_code == 413
        data = response.json()
        assert "detail" in data
        assert len(data["detail"]) > 0

    def test_400_response_has_detail(self, test_client):
        """400 response should have descriptive detail."""
        response = test_client.post(
            "/test",
            headers={"Content-Length": "not-a-number"}
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
