"""
PII Audit Middleware Unit Tests

Tests for personal data access logging middleware.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient


# ==================== Fixtures ====================

@pytest.fixture
def mock_app():
    """Create a basic FastAPI app without middleware for testing."""
    app = FastAPI()

    @app.get("/api/v1/crm/clients")
    async def list_clients():
        return {"clients": []}

    @app.get("/api/v1/crm/clients/{client_id}")
    async def get_client(client_id: str):
        return {"id": client_id, "name": "Test"}

    @app.get("/api/v1/other")
    async def other_route():
        return {"data": "non-pii"}

    return app


# ==================== PII Endpoints Config Tests ====================

class TestPIIEndpointsConfig:
    """Tests for PII_ENDPOINTS configuration."""

    def test_pii_endpoints_is_dict(self):
        """PII_ENDPOINTS should be a dictionary."""
        from src.middleware.pii_audit_middleware import PII_ENDPOINTS

        assert isinstance(PII_ENDPOINTS, dict)

    def test_crm_clients_endpoint_defined(self):
        """CRM clients endpoints should be defined."""
        from src.middleware.pii_audit_middleware import PII_ENDPOINTS

        assert any("crm/clients" in pattern for pattern in PII_ENDPOINTS.keys())

    def test_endpoint_config_has_required_keys(self):
        """Each endpoint config should have resource_type, pii_fields, methods."""
        from src.middleware.pii_audit_middleware import PII_ENDPOINTS

        for pattern, config in PII_ENDPOINTS.items():
            assert "resource_type" in config, f"{pattern} missing resource_type"
            assert "pii_fields" in config, f"{pattern} missing pii_fields"
            assert "methods" in config, f"{pattern} missing methods"

    def test_pii_fields_are_lists(self):
        """pii_fields should be lists."""
        from src.middleware.pii_audit_middleware import PII_ENDPOINTS

        for pattern, config in PII_ENDPOINTS.items():
            assert isinstance(config["pii_fields"], list)

    def test_methods_are_valid_http_methods(self):
        """Methods should be valid HTTP methods."""
        from src.middleware.pii_audit_middleware import PII_ENDPOINTS

        valid_methods = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}

        for pattern, config in PII_ENDPOINTS.items():
            for method in config["methods"]:
                assert method in valid_methods, f"Invalid method {method} in {pattern}"


class TestMethodToActionMapping:
    """Tests for METHOD_TO_ACTION mapping."""

    def test_mapping_exists(self):
        """METHOD_TO_ACTION should be defined."""
        from src.middleware.pii_audit_middleware import METHOD_TO_ACTION

        assert isinstance(METHOD_TO_ACTION, dict)

    def test_get_maps_to_view(self):
        """GET should map to 'view'."""
        from src.middleware.pii_audit_middleware import METHOD_TO_ACTION

        assert METHOD_TO_ACTION["GET"] == "view"

    def test_post_maps_to_create(self):
        """POST should map to 'create'."""
        from src.middleware.pii_audit_middleware import METHOD_TO_ACTION

        assert METHOD_TO_ACTION["POST"] == "create"

    def test_put_and_patch_map_to_update(self):
        """PUT and PATCH should map to 'update'."""
        from src.middleware.pii_audit_middleware import METHOD_TO_ACTION

        assert METHOD_TO_ACTION["PUT"] == "update"
        assert METHOD_TO_ACTION["PATCH"] == "update"

    def test_delete_maps_to_delete(self):
        """DELETE should map to 'delete'."""
        from src.middleware.pii_audit_middleware import METHOD_TO_ACTION

        assert METHOD_TO_ACTION["DELETE"] == "delete"


# ==================== Middleware Initialization Tests ====================

class TestPIIAuditMiddlewareInit:
    """Tests for PIIAuditMiddleware initialization."""

    def test_init_with_enabled(self, mock_app):
        """Should initialize with enabled=True by default."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware

        middleware = PIIAuditMiddleware(mock_app, enabled=True)

        assert middleware.enabled is True

    def test_init_with_disabled(self, mock_app):
        """Should initialize with enabled=False."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware

        middleware = PIIAuditMiddleware(mock_app, enabled=False)

        assert middleware.enabled is False


# ==================== PII Config Detection Tests ====================

class TestGetPIIConfig:
    """Tests for _get_pii_config method."""

    def test_detects_pii_endpoint(self, mock_app):
        """Should detect PII endpoint patterns."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware

        middleware = PIIAuditMiddleware(mock_app)

        config = middleware._get_pii_config("/api/v1/crm/clients", "GET")

        assert config is not None
        assert config["resource_type"] == "client"

    def test_detects_pii_endpoint_with_id(self, mock_app):
        """Should detect PII endpoint with resource ID."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware

        middleware = PIIAuditMiddleware(mock_app)

        config = middleware._get_pii_config("/api/v1/crm/clients/abc-123", "GET")

        assert config is not None

    def test_returns_none_for_non_pii_path(self, mock_app):
        """Should return None for non-PII paths."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware

        middleware = PIIAuditMiddleware(mock_app)

        config = middleware._get_pii_config("/api/v1/health", "GET")

        assert config is None

    def test_returns_none_for_wrong_method(self, mock_app):
        """Should return None when method not in config."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware

        middleware = PIIAuditMiddleware(mock_app)

        # OPTIONS is not typically in PII endpoint methods
        config = middleware._get_pii_config("/api/v1/crm/clients", "OPTIONS")

        assert config is None


# ==================== Resource ID Extraction Tests ====================

class TestExtractResourceId:
    """Tests for _extract_resource_id method."""

    def test_extracts_uuid(self, mock_app):
        """Should extract UUID from path."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware

        middleware = PIIAuditMiddleware(mock_app)

        resource_id = middleware._extract_resource_id("/api/v1/crm/clients/550e8400-e29b-41d4-a716-446655440000")

        assert resource_id == "550e8400-e29b-41d4-a716-446655440000"

    def test_extracts_numeric_id(self, mock_app):
        """Should extract numeric ID from path."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware

        middleware = PIIAuditMiddleware(mock_app)

        resource_id = middleware._extract_resource_id("/api/v1/quotes/12345")

        assert resource_id == "12345"

    def test_returns_none_for_list_endpoint(self, mock_app):
        """Should return None for list endpoints without ID."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware

        middleware = PIIAuditMiddleware(mock_app)

        resource_id = middleware._extract_resource_id("/api/v1/crm/clients")

        assert resource_id is None


# ==================== Client IP Extraction Tests ====================

class TestGetClientIP:
    """Tests for _get_client_ip method."""

    def test_extracts_forwarded_for(self, mock_app):
        """Should extract IP from X-Forwarded-For header."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware

        middleware = PIIAuditMiddleware(mock_app)

        mock_request = MagicMock()
        mock_request.headers = {"x-forwarded-for": "203.0.113.195, 70.41.3.18"}
        mock_request.client = MagicMock(host="10.0.0.1")

        ip = middleware._get_client_ip(mock_request)

        assert ip == "203.0.113.195"

    def test_extracts_real_ip(self, mock_app):
        """Should extract IP from X-Real-IP header."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware

        middleware = PIIAuditMiddleware(mock_app)

        mock_request = MagicMock()
        mock_request.headers = {"x-real-ip": "192.168.1.100"}
        mock_request.client = MagicMock(host="10.0.0.1")

        ip = middleware._get_client_ip(mock_request)

        assert ip == "192.168.1.100"

    def test_falls_back_to_client_host(self, mock_app):
        """Should fall back to direct client host."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware

        middleware = PIIAuditMiddleware(mock_app)

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = MagicMock(host="192.168.1.50")

        ip = middleware._get_client_ip(mock_request)

        assert ip == "192.168.1.50"

    def test_returns_none_when_no_client(self, mock_app):
        """Should return None when no client info."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware

        middleware = PIIAuditMiddleware(mock_app)

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = None

        ip = middleware._get_client_ip(mock_request)

        assert ip is None


# ==================== Setup Function Tests ====================

class TestSetupPIIAuditMiddleware:
    """Tests for setup_pii_audit_middleware function."""

    def test_setup_adds_middleware(self):
        """setup_pii_audit_middleware should add middleware to app."""
        from src.middleware.pii_audit_middleware import setup_pii_audit_middleware

        app = FastAPI()

        with patch.object(app, 'add_middleware') as mock_add:
            setup_pii_audit_middleware(app, enabled=True)

            mock_add.assert_called_once()

    def test_setup_with_disabled(self):
        """setup_pii_audit_middleware should respect enabled flag."""
        from src.middleware.pii_audit_middleware import setup_pii_audit_middleware

        app = FastAPI()

        with patch.object(app, 'add_middleware') as mock_add:
            setup_pii_audit_middleware(app, enabled=False)

            # Should still add middleware but with enabled=False
            call_kwargs = mock_add.call_args[1]
            assert call_kwargs.get("enabled") is False
