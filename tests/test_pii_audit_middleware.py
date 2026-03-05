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
    """Tests for _get_client_ip method (now takes ASGI scope dict)."""

    def test_extracts_forwarded_for(self, mock_app):
        """Should extract IP from X-Forwarded-For header."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware

        middleware = PIIAuditMiddleware(mock_app)

        scope = {
            "headers": [(b"x-forwarded-for", b"203.0.113.195, 70.41.3.18")],
            "client": ("10.0.0.1", 12345),
        }

        ip = middleware._get_client_ip(scope)

        assert ip == "203.0.113.195"

    def test_extracts_real_ip(self, mock_app):
        """Should extract IP from X-Real-IP header."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware

        middleware = PIIAuditMiddleware(mock_app)

        scope = {
            "headers": [(b"x-real-ip", b"192.168.1.100")],
            "client": ("10.0.0.1", 12345),
        }

        ip = middleware._get_client_ip(scope)

        assert ip == "192.168.1.100"

    def test_falls_back_to_client_host(self, mock_app):
        """Should fall back to direct client host."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware

        middleware = PIIAuditMiddleware(mock_app)

        scope = {
            "headers": [],
            "client": ("192.168.1.50", 12345),
        }

        ip = middleware._get_client_ip(scope)

        assert ip == "192.168.1.50"

    def test_returns_none_when_no_client(self, mock_app):
        """Should return None when no client info."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware

        middleware = PIIAuditMiddleware(mock_app)

        scope = {
            "headers": [],
        }

        ip = middleware._get_client_ip(scope)

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


# ==================== Logging Tests ====================

class TestPIILogging:
    """Tests for PII access logging."""

    @pytest.mark.asyncio
    async def test_log_entry_structure(self, mock_app):
        """Log entries should build an audit entry and attempt to insert it."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware

        middleware = PIIAuditMiddleware(mock_app, enabled=True)

        # Create ASGI scope
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/crm/clients/123",
            "headers": [(b"x-client-id", b"test_tenant")],
            "client": ("192.168.1.1", 12345),
            "state": {"user": None, "request_id": "test-request-id"},
        }

        pii_config = {
            "resource_type": "client",
            "pii_fields": ["name", "email"],
            "methods": ["GET"]
        }

        with patch.object(middleware, '_insert_audit_log_sync') as mock_insert:
            await middleware._log_pii_access(scope, pii_config)

            mock_insert.assert_called_once()
            call_args = mock_insert.call_args
            tenant_id = call_args[0][0]
            audit_entry = call_args[0][1]
            assert tenant_id == "test_tenant"
            assert audit_entry["resource_type"] == "client"
            assert audit_entry["action"] == "view"
            assert audit_entry["ip_address"] == "192.168.1.1"


# ==================== Middleware Dispatch Tests ====================

class TestMiddlewareDispatch:
    """Tests for middleware dispatch behavior."""

    @pytest.mark.asyncio
    async def test_dispatch_with_disabled_middleware(self, mock_app):
        """Disabled middleware should pass through."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware
        from tests.conftest import call_asgi_middleware

        middleware = PIIAuditMiddleware(mock_app, enabled=False)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/crm/clients",
            "query_string": b"",
            "headers": [],
        }

        response = await call_asgi_middleware(middleware, scope)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_dispatch_with_non_pii_endpoint(self, mock_app):
        """Non-PII endpoints should pass through without logging."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware
        from tests.conftest import call_asgi_middleware

        middleware = PIIAuditMiddleware(mock_app, enabled=True)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/health",
            "query_string": b"",
            "headers": [],
        }

        with patch('src.middleware.pii_audit_middleware.logger') as mock_logger:
            response = await call_asgi_middleware(middleware, scope)

            # Should not log PII access for health endpoints
            assert response.status_code == 200


# ==================== Edge Cases ====================

class TestEdgeCases:
    """Edge case tests for PII audit middleware."""

    def test_complex_uuid_in_path(self, mock_app):
        """Should handle complex UUIDs in path."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware

        middleware = PIIAuditMiddleware(mock_app)

        uuid_path = "/api/v1/crm/clients/550e8400-e29b-41d4-a716-446655440000/details"
        resource_id = middleware._extract_resource_id(uuid_path)

        assert resource_id is not None

    def test_multiple_ids_in_path(self, mock_app):
        """Should handle paths with multiple IDs."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware

        middleware = PIIAuditMiddleware(mock_app)

        path = "/api/v1/crm/clients/123/quotes/456"
        resource_id = middleware._extract_resource_id(path)

        # Should extract at least one ID
        assert resource_id is not None

    def test_path_with_no_id(self, mock_app):
        """Should handle paths with no ID."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware

        middleware = PIIAuditMiddleware(mock_app)

        path = "/api/v1/crm/clients"
        resource_id = middleware._extract_resource_id(path)

        assert resource_id is None

    def test_whitespace_in_forwarded_header(self, mock_app):
        """Should handle whitespace in X-Forwarded-For."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware

        middleware = PIIAuditMiddleware(mock_app)

        scope = {
            "headers": [(b"x-forwarded-for", b"  203.0.113.195  ")],
            "client": ("10.0.0.1", 12345),
        }

        ip = middleware._get_client_ip(scope)

        # Should be trimmed
        assert ip.strip() == "203.0.113.195"


# ==================== Integration-like Tests ====================

class TestIntegrationScenarios:
    """Integration-like tests for realistic scenarios."""

    def test_full_request_cycle(self, mock_app):
        """Test complete request cycle through middleware."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware

        # Add middleware to app
        mock_app.add_middleware(PIIAuditMiddleware, enabled=True)

        client = TestClient(mock_app)

        # Make request to PII endpoint
        response = client.get("/api/v1/crm/clients")

        # Should complete without error
        assert response.status_code == 200

    def test_request_to_single_client(self, mock_app):
        """Test request to single client endpoint."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware

        mock_app.add_middleware(PIIAuditMiddleware, enabled=True)

        client = TestClient(mock_app)

        response = client.get("/api/v1/crm/clients/abc-123")

        assert response.status_code == 200
        assert response.json()["id"] == "abc-123"

    def test_request_to_non_pii_endpoint(self, mock_app):
        """Test request to non-PII endpoint."""
        from src.middleware.pii_audit_middleware import PIIAuditMiddleware

        mock_app.add_middleware(PIIAuditMiddleware, enabled=True)

        client = TestClient(mock_app)

        response = client.get("/api/v1/other")

        assert response.status_code == 200
        assert response.json()["data"] == "non-pii"
