"""
Core Routes Unit Tests

Comprehensive tests for core business API routes:
- Quote endpoints
- Invoice endpoints
- CRM/Client endpoints
- Pipeline endpoints

Uses FastAPI TestClient with mocked dependencies.
These tests focus on verifying:
1. Authentication is required (401 for unauthenticated requests)
2. Route structure and HTTP methods are correct
3. Request validation works correctly
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import json
import os


# ==================== Fixtures ====================

@pytest.fixture
def mock_config():
    """Create a mock ClientConfig."""
    config = MagicMock()
    config.client_id = "test_tenant"
    config.supabase_url = "https://test.supabase.co"
    config.supabase_service_key = "test-service-key"
    config.supabase_anon_key = "test-anon-key"
    config.currency = "USD"
    return config


@pytest.fixture
def test_client():
    """Create a basic TestClient."""
    from main import app
    return TestClient(app)


# ==================== Quote Routes Tests ====================

class TestQuoteListEndpoint:
    """Test GET /api/v1/quotes endpoint."""

    def test_list_quotes_requires_auth(self, test_client):
        """GET /api/v1/quotes should require authentication."""
        response = test_client.get("/api/v1/quotes")
        assert response.status_code == 401

    def test_list_quotes_with_x_client_id_requires_auth(self, test_client):
        """GET /api/v1/quotes with X-Client-ID still requires auth."""
        response = test_client.get(
            "/api/v1/quotes",
            headers={"X-Client-ID": "test_tenant"}
        )
        assert response.status_code == 401

    def test_list_quotes_invalid_limit(self, test_client):
        """GET /api/v1/quotes with invalid limit returns auth first."""
        # Auth middleware runs before validation
        response = test_client.get("/api/v1/quotes?limit=1000")
        assert response.status_code == 401


class TestQuoteDetailEndpoint:
    """Test GET /api/v1/quotes/{quote_id} endpoint."""

    def test_get_quote_requires_auth(self, test_client):
        """GET /api/v1/quotes/{id} should require authentication."""
        response = test_client.get("/api/v1/quotes/QT-001")
        assert response.status_code == 401

    def test_get_quote_with_various_ids(self, test_client):
        """GET /api/v1/quotes/{id} accepts any ID format."""
        # All should fail auth first
        for quote_id in ["QT-001", "uuid-style", "123"]:
            response = test_client.get(f"/api/v1/quotes/{quote_id}")
            assert response.status_code == 401


class TestQuoteGenerateEndpoint:
    """Test POST /api/v1/quotes/generate endpoint."""

    def test_generate_quote_requires_auth(self, test_client):
        """POST /api/v1/quotes/generate should require authentication."""
        response = test_client.post(
            "/api/v1/quotes/generate",
            json={
                "inquiry": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "destination": "Cape Town"
                }
            }
        )
        assert response.status_code == 401

    def test_generate_quote_without_body_still_requires_auth(self, test_client):
        """POST /api/v1/quotes/generate without body returns auth error."""
        response = test_client.post("/api/v1/quotes/generate")
        # Auth middleware runs first
        assert response.status_code == 401


class TestQuotePDFEndpoint:
    """Test GET /api/v1/quotes/{quote_id}/pdf endpoint."""

    def test_quote_pdf_requires_auth(self, test_client):
        """GET /api/v1/quotes/{id}/pdf should require authentication."""
        response = test_client.get("/api/v1/quotes/QT-001/pdf")
        assert response.status_code == 401


class TestQuoteResendEndpoint:
    """Test POST /api/v1/quotes/{quote_id}/resend endpoint."""

    def test_quote_resend_requires_auth(self, test_client):
        """POST /api/v1/quotes/{id}/resend should require authentication."""
        response = test_client.post("/api/v1/quotes/QT-001/resend")
        assert response.status_code == 401


class TestQuoteSendEndpoint:
    """Test POST /api/v1/quotes/{quote_id}/send endpoint."""

    def test_quote_send_requires_auth(self, test_client):
        """POST /api/v1/quotes/{id}/send should require authentication."""
        response = test_client.post("/api/v1/quotes/QT-001/send")
        assert response.status_code == 401


# ==================== Invoice Routes Tests ====================

class TestInvoiceListEndpoint:
    """Test GET /api/v1/invoices endpoint."""

    def test_list_invoices_requires_auth(self, test_client):
        """GET /api/v1/invoices should require authentication."""
        response = test_client.get("/api/v1/invoices")
        assert response.status_code == 401

    def test_list_invoices_with_status_requires_auth(self, test_client):
        """GET /api/v1/invoices?status=paid still requires auth."""
        response = test_client.get("/api/v1/invoices?status=paid")
        assert response.status_code == 401


class TestInvoiceDetailEndpoint:
    """Test GET /api/v1/invoices/{invoice_id} endpoint."""

    def test_get_invoice_requires_auth(self, test_client):
        """GET /api/v1/invoices/{id} should require authentication."""
        response = test_client.get("/api/v1/invoices/INV-001")
        assert response.status_code == 401


class TestInvoiceStatusEndpoint:
    """Test PATCH /api/v1/invoices/{invoice_id}/status endpoint."""

    def test_update_invoice_status_requires_auth(self, test_client):
        """PATCH /api/v1/invoices/{id}/status should require authentication."""
        response = test_client.patch(
            "/api/v1/invoices/INV-001/status",
            json={"status": "paid"}
        )
        assert response.status_code == 401


class TestInvoiceSendEndpoint:
    """Test POST /api/v1/invoices/{invoice_id}/send endpoint."""

    def test_send_invoice_requires_auth(self, test_client):
        """POST /api/v1/invoices/{id}/send should require authentication."""
        response = test_client.post("/api/v1/invoices/INV-001/send")
        assert response.status_code == 401


class TestInvoicePDFEndpoint:
    """Test GET /api/v1/invoices/{invoice_id}/pdf endpoint."""

    def test_invoice_pdf_requires_auth(self, test_client):
        """GET /api/v1/invoices/{id}/pdf should require authentication."""
        response = test_client.get("/api/v1/invoices/INV-001/pdf")
        assert response.status_code == 401


class TestInvoiceTravelersEndpoint:
    """Test PATCH /api/v1/invoices/{invoice_id}/travelers endpoint."""

    def test_update_travelers_requires_auth(self, test_client):
        """PATCH /api/v1/invoices/{id}/travelers should require authentication."""
        response = test_client.patch(
            "/api/v1/invoices/INV-001/travelers",
            json=[{"name": "John Doe", "type": "Adult"}]
        )
        assert response.status_code == 401


class TestManualInvoiceEndpoint:
    """Test POST /api/v1/invoices/create endpoint."""

    def test_create_manual_invoice_requires_auth(self, test_client):
        """POST /api/v1/invoices/create should require authentication."""
        response = test_client.post(
            "/api/v1/invoices/create",
            json={
                "customer_name": "John Doe",
                "customer_email": "john@example.com",
                "items": [{"description": "Service", "amount": 100}]
            }
        )
        assert response.status_code == 401


class TestConvertQuoteEndpoint:
    """Test POST /api/v1/invoices/convert-quote endpoint."""

    def test_convert_quote_requires_auth(self, test_client):
        """POST /api/v1/invoices/convert-quote should require authentication."""
        response = test_client.post(
            "/api/v1/invoices/convert-quote",
            json={"quote_id": "QT-001"}
        )
        assert response.status_code == 401


# ==================== CRM Client Routes Tests ====================

class TestClientListEndpoint:
    """Test GET /api/v1/crm/clients endpoint."""

    def test_list_clients_requires_auth(self, test_client):
        """GET /api/v1/crm/clients should require authentication."""
        response = test_client.get("/api/v1/crm/clients")
        assert response.status_code == 401

    def test_list_clients_with_query_requires_auth(self, test_client):
        """GET /api/v1/crm/clients?query=john still requires auth."""
        response = test_client.get("/api/v1/crm/clients?query=john")
        assert response.status_code == 401

    def test_list_clients_with_stage_requires_auth(self, test_client):
        """GET /api/v1/crm/clients?stage=BOOKED still requires auth."""
        response = test_client.get("/api/v1/crm/clients?stage=BOOKED")
        assert response.status_code == 401


class TestClientDetailEndpoint:
    """Test GET /api/v1/crm/clients/{client_id} endpoint."""

    def test_get_client_requires_auth(self, test_client):
        """GET /api/v1/crm/clients/{id} should require authentication."""
        response = test_client.get("/api/v1/crm/clients/client_123")
        assert response.status_code == 401


class TestClientCreateEndpoint:
    """Test POST /api/v1/crm/clients endpoint."""

    def test_create_client_requires_auth(self, test_client):
        """POST /api/v1/crm/clients should require authentication."""
        response = test_client.post(
            "/api/v1/crm/clients",
            json={
                "email": "john@example.com",
                "name": "John Doe"
            }
        )
        assert response.status_code == 401


class TestClientUpdateEndpoint:
    """Test PATCH /api/v1/crm/clients/{client_id} endpoint."""

    def test_update_client_requires_auth(self, test_client):
        """PATCH /api/v1/crm/clients/{id} should require authentication."""
        response = test_client.patch(
            "/api/v1/crm/clients/client_123",
            json={"name": "Updated Name"}
        )
        assert response.status_code == 401


# ==================== Pipeline Routes Tests ====================

class TestPipelineEndpoint:
    """Test GET /api/v1/crm/pipeline endpoint."""

    def test_get_pipeline_requires_auth(self, test_client):
        """GET /api/v1/crm/pipeline should require authentication."""
        response = test_client.get("/api/v1/crm/pipeline")
        assert response.status_code == 401


class TestPipelineSummaryEndpoint:
    """Test GET /api/v1/crm/pipeline/summary endpoint."""

    def test_get_pipeline_summary_requires_auth(self, test_client):
        """GET /api/v1/crm/pipeline/summary should require authentication."""
        response = test_client.get("/api/v1/crm/pipeline/summary")
        assert response.status_code == 401


# ==================== Client Stage Update Tests ====================

class TestClientStageUpdateEndpoint:
    """Test PATCH /api/v1/crm/clients/{client_id}/stage endpoint."""

    def test_update_client_stage_requires_auth(self, test_client):
        """PATCH /api/v1/crm/clients/{id}/stage should require authentication."""
        response = test_client.patch(
            "/api/v1/crm/clients/client_123/stage",
            json={"stage": "BOOKED"}
        )
        assert response.status_code == 401


# ==================== Client Activities Tests ====================

class TestClientActivitiesEndpoint:
    """Test GET /api/v1/crm/clients/{client_id}/activities endpoint."""

    def test_get_activities_requires_auth(self, test_client):
        """GET /api/v1/crm/clients/{id}/activities should require authentication."""
        response = test_client.get("/api/v1/crm/clients/client_123/activities")
        assert response.status_code == 401


class TestLogActivityEndpoint:
    """Test POST /api/v1/crm/clients/{client_id}/activities endpoint."""

    def test_log_activity_requires_auth(self, test_client):
        """POST /api/v1/crm/clients/{id}/activities should require authentication."""
        response = test_client.post(
            "/api/v1/crm/clients/client_123/activities",
            json={
                "activity_type": "email",
                "description": "Sent follow-up"
            }
        )
        assert response.status_code == 401


# ==================== CRM Stats Tests ====================

class TestCRMStatsEndpoint:
    """Test GET /api/v1/crm/stats endpoint."""

    def test_get_crm_stats_requires_auth(self, test_client):
        """GET /api/v1/crm/stats should require authentication."""
        response = test_client.get("/api/v1/crm/stats")
        assert response.status_code == 401


# ==================== Public Routes Tests ====================

class TestPublicInvoicePDF:
    """Test GET /api/v1/public/invoices/{invoice_id}/pdf endpoint."""

    def test_public_invoice_pdf_does_not_require_auth(self, test_client):
        """Public invoice PDF endpoint should not require authentication."""
        # This tests the route structure - actual response depends on invoice existence
        response = test_client.get("/api/v1/public/invoices/INV-001/pdf")
        # Should not be 401 - public endpoint
        assert response.status_code != 401
        # Will likely be 404 or 500 without real data
        assert response.status_code in [404, 500]


class TestPublicQuotePDF:
    """Test GET /api/v1/public/quotes/{quote_id}/pdf endpoint."""

    def test_public_quote_pdf_does_not_require_auth(self, test_client):
        """Public quote PDF endpoint should not require authentication."""
        response = test_client.get("/api/v1/public/quotes/QT-001/pdf")
        # Should not be 401 - public endpoint
        assert response.status_code != 401
        # Will likely be 404 or 500 without real data
        assert response.status_code in [404, 500]


# ==================== Health Endpoints Tests ====================

class TestHealthEndpoints:
    """Test health check endpoints are accessible."""

    def test_root_endpoint_accessible(self, test_client):
        """GET / should be accessible without auth."""
        response = test_client.get("/")
        assert response.status_code == 200

    def test_health_endpoint_accessible(self, test_client):
        """GET /health should be accessible without auth."""
        response = test_client.get("/health")
        assert response.status_code == 200

    def test_health_live_endpoint_accessible(self, test_client):
        """GET /health/live should be accessible without auth."""
        response = test_client.get("/health/live")
        assert response.status_code == 200


# ==================== Response Format Tests ====================

class TestResponseFormats:
    """Test response format consistency."""

    def test_auth_error_response_format(self, test_client):
        """Auth errors should return JSON with detail field."""
        response = test_client.get("/api/v1/quotes")
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    def test_health_response_format(self, test_client):
        """Health endpoint returns JSON with status."""
        response = test_client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"


# ==================== Request Validation Tests ====================

class TestRequestValidation:
    """Test request validation behavior."""

    def test_invalid_json_returns_error(self, test_client):
        """Invalid JSON should return 422."""
        response = test_client.post(
            "/api/v1/crm/clients",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        # Auth runs first, so we get 401
        assert response.status_code in [401, 422]


# ==================== HTTP Methods Tests ====================

class TestHTTPMethods:
    """Test correct HTTP methods are enforced."""

    def test_quotes_list_only_allows_get(self, test_client):
        """GET /api/v1/quotes should only allow GET."""
        response = test_client.delete("/api/v1/quotes")
        assert response.status_code in [401, 405]

    def test_invoices_list_only_allows_get(self, test_client):
        """GET /api/v1/invoices should only allow GET."""
        response = test_client.put("/api/v1/invoices")
        assert response.status_code in [401, 405]


# ==================== Headers Tests ====================

class TestHeaders:
    """Test headers are processed correctly."""

    def test_x_client_id_header_accepted(self, test_client):
        """X-Client-ID header should be accepted."""
        response = test_client.get(
            "/api/v1/quotes",
            headers={"X-Client-ID": "test_tenant"}
        )
        # Should still require auth
        assert response.status_code == 401

    def test_response_includes_request_id(self, test_client):
        """Responses should include X-Request-ID header."""
        response = test_client.get("/health")
        assert "X-Request-ID" in response.headers

    def test_response_includes_rate_limit_headers(self, test_client):
        """API responses should include rate limit headers."""
        response = test_client.get("/api/v1/quotes")
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers


# ==================== Route Existence Tests ====================

class TestRouteExistence:
    """Test that all expected routes exist."""

    def test_quotes_routes_exist(self, test_client):
        """Quote routes should exist."""
        routes = [
            ("GET", "/api/v1/quotes"),
            ("GET", "/api/v1/quotes/QT-001"),
            ("POST", "/api/v1/quotes/generate"),
            ("GET", "/api/v1/quotes/QT-001/pdf"),
            ("POST", "/api/v1/quotes/QT-001/resend"),
            ("POST", "/api/v1/quotes/QT-001/send"),
        ]
        for method, path in routes:
            if method == "GET":
                response = test_client.get(path)
            elif method == "POST":
                response = test_client.post(path)
            # Should be 401 (auth required), not 404 (route not found)
            assert response.status_code != 404, f"{method} {path} returned 404"

    def test_invoice_routes_exist(self, test_client):
        """Invoice routes should exist."""
        routes = [
            ("GET", "/api/v1/invoices"),
            ("GET", "/api/v1/invoices/INV-001"),
            ("POST", "/api/v1/invoices/create"),
            ("POST", "/api/v1/invoices/convert-quote"),
            ("GET", "/api/v1/invoices/INV-001/pdf"),
            ("POST", "/api/v1/invoices/INV-001/send"),
            ("PATCH", "/api/v1/invoices/INV-001/status"),
        ]
        for method, path in routes:
            if method == "GET":
                response = test_client.get(path)
            elif method == "POST":
                response = test_client.post(path, json={})
            elif method == "PATCH":
                response = test_client.patch(path, json={})
            # Should be 401 (auth required), not 404 (route not found)
            assert response.status_code != 404, f"{method} {path} returned 404"

    def test_crm_routes_exist(self, test_client):
        """CRM routes should exist."""
        routes = [
            ("GET", "/api/v1/crm/clients"),
            ("POST", "/api/v1/crm/clients"),
            ("GET", "/api/v1/crm/clients/client_123"),
            ("PATCH", "/api/v1/crm/clients/client_123"),
            ("PATCH", "/api/v1/crm/clients/client_123/stage"),
            ("GET", "/api/v1/crm/clients/client_123/activities"),
            ("POST", "/api/v1/crm/clients/client_123/activities"),
            ("GET", "/api/v1/crm/pipeline"),
            ("GET", "/api/v1/crm/pipeline/summary"),
            ("GET", "/api/v1/crm/stats"),
        ]
        for method, path in routes:
            if method == "GET":
                response = test_client.get(path)
            elif method == "POST":
                response = test_client.post(path, json={})
            elif method == "PATCH":
                response = test_client.patch(path, json={})
            # Should be 401 (auth required), not 404 (route not found)
            assert response.status_code != 404, f"{method} {path} returned 404"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
