"""
API Routes Unit Tests

Tests for Pydantic models, dependencies, and endpoint structure in routes.py.
"""

import pytest
from unittest.mock import MagicMock, patch
from pydantic import ValidationError
from fastapi.testclient import TestClient


# ==================== Pydantic Models Tests ====================

class TestTravelInquiryModel:
    """Tests for TravelInquiry model."""

    def test_requires_name_email_destination(self):
        """TravelInquiry should require name, email, and destination."""
        from src.api.routes import TravelInquiry

        inquiry = TravelInquiry(
            name="John Doe",
            email="john@example.com",
            destination="Zanzibar"
        )

        assert inquiry.name == "John Doe"
        assert str(inquiry.email) == "john@example.com"
        assert inquiry.destination == "Zanzibar"

    def test_default_values(self):
        """TravelInquiry should have sensible defaults."""
        from src.api.routes import TravelInquiry

        inquiry = TravelInquiry(
            name="John",
            email="john@example.com",
            destination="Maldives"
        )

        assert inquiry.adults == 2
        assert inquiry.children == 0
        assert inquiry.phone is None
        assert inquiry.check_in is None
        assert inquiry.budget is None

    def test_validates_name_length(self):
        """TravelInquiry should validate name length."""
        from src.api.routes import TravelInquiry

        # Name too short
        with pytest.raises(ValidationError):
            TravelInquiry(name="J", email="j@test.com", destination="Test")

    def test_validates_email_format(self):
        """TravelInquiry should validate email format."""
        from src.api.routes import TravelInquiry

        with pytest.raises(ValidationError):
            TravelInquiry(name="John", email="not-an-email", destination="Test")

    def test_validates_adults_range(self):
        """TravelInquiry should validate adults range."""
        from src.api.routes import TravelInquiry

        # Too many adults
        with pytest.raises(ValidationError):
            TravelInquiry(
                name="John",
                email="john@test.com",
                destination="Test",
                adults=21
            )

        # Zero adults
        with pytest.raises(ValidationError):
            TravelInquiry(
                name="John",
                email="john@test.com",
                destination="Test",
                adults=0
            )

    def test_validates_children_range(self):
        """TravelInquiry should validate children range."""
        from src.api.routes import TravelInquiry

        # Too many children
        with pytest.raises(ValidationError):
            TravelInquiry(
                name="John",
                email="john@test.com",
                destination="Test",
                children=11
            )

    def test_with_all_fields(self):
        """TravelInquiry should accept all optional fields."""
        from src.api.routes import TravelInquiry

        inquiry = TravelInquiry(
            name="John Doe",
            email="john@example.com",
            phone="+1234567890",
            destination="Zanzibar",
            check_in="2026-06-01",
            check_out="2026-06-10",
            adults=2,
            children=2,
            children_ages=[5, 8],
            budget=5000.0,
            message="Honeymoon trip",
            requested_hotel="Paradise Resort"
        )

        assert inquiry.phone == "+1234567890"
        assert inquiry.children_ages == [5, 8]
        assert inquiry.budget == 5000.0


class TestQuoteGenerateRequestModel:
    """Tests for QuoteGenerateRequest model."""

    def test_requires_inquiry(self):
        """QuoteGenerateRequest should require inquiry."""
        from src.api.routes import QuoteGenerateRequest, TravelInquiry

        request = QuoteGenerateRequest(
            inquiry=TravelInquiry(
                name="John",
                email="john@test.com",
                destination="Test"
            )
        )

        assert request.inquiry.name == "John"

    def test_default_values(self):
        """QuoteGenerateRequest should have defaults."""
        from src.api.routes import QuoteGenerateRequest, TravelInquiry

        request = QuoteGenerateRequest(
            inquiry=TravelInquiry(
                name="John",
                email="john@test.com",
                destination="Test"
            )
        )

        assert request.send_email is True
        assert request.assign_consultant is True
        assert request.selected_hotels is None

    def test_with_selected_hotels(self):
        """QuoteGenerateRequest should accept selected_hotels."""
        from src.api.routes import QuoteGenerateRequest, TravelInquiry

        request = QuoteGenerateRequest(
            inquiry=TravelInquiry(
                name="John",
                email="john@test.com",
                destination="Test"
            ),
            selected_hotels=["Hotel A", "Hotel B"]
        )

        assert request.selected_hotels == ["Hotel A", "Hotel B"]


class TestPipelineStageEnum:
    """Tests for PipelineStageEnum."""

    def test_has_all_stages(self):
        """PipelineStageEnum should have all pipeline stages."""
        from src.api.routes import PipelineStageEnum

        stages = list(PipelineStageEnum)

        assert PipelineStageEnum.QUOTED in stages
        assert PipelineStageEnum.NEGOTIATING in stages
        assert PipelineStageEnum.BOOKED in stages
        assert PipelineStageEnum.PAID in stages
        assert PipelineStageEnum.TRAVELLED in stages
        assert PipelineStageEnum.LOST in stages

    def test_enum_values(self):
        """PipelineStageEnum values should be uppercase strings."""
        from src.api.routes import PipelineStageEnum

        assert PipelineStageEnum.QUOTED.value == "QUOTED"
        assert PipelineStageEnum.PAID.value == "PAID"


class TestClientCreateModel:
    """Tests for ClientCreate model."""

    def test_requires_email_name(self):
        """ClientCreate should require email and name."""
        from src.api.routes import ClientCreate

        client = ClientCreate(
            email="test@example.com",
            name="Test Client"
        )

        assert str(client.email) == "test@example.com"
        assert client.name == "Test Client"

    def test_default_values(self):
        """ClientCreate should have defaults."""
        from src.api.routes import ClientCreate

        client = ClientCreate(
            email="test@example.com",
            name="Test Client"
        )

        assert client.source == "manual"
        assert client.phone is None
        assert client.consultant_id is None

    def test_validates_name_length(self):
        """ClientCreate should validate name length."""
        from src.api.routes import ClientCreate

        with pytest.raises(ValidationError):
            ClientCreate(email="test@test.com", name="X")


class TestClientUpdateModel:
    """Tests for ClientUpdate model."""

    def test_all_fields_optional(self):
        """ClientUpdate should have all optional fields."""
        from src.api.routes import ClientUpdate

        update = ClientUpdate()

        assert update.name is None
        assert update.phone is None
        assert update.consultant_id is None
        assert update.pipeline_stage is None

    def test_accepts_pipeline_stage(self):
        """ClientUpdate should accept pipeline_stage enum."""
        from src.api.routes import ClientUpdate, PipelineStageEnum

        update = ClientUpdate(
            pipeline_stage=PipelineStageEnum.BOOKED
        )

        assert update.pipeline_stage == PipelineStageEnum.BOOKED


class TestActivityLogModel:
    """Tests for ActivityLog model."""

    def test_requires_type_and_description(self):
        """ActivityLog should require activity_type and description."""
        from src.api.routes import ActivityLog

        log = ActivityLog(
            activity_type="call",
            description="Called client about quote"
        )

        assert log.activity_type == "call"
        assert log.description == "Called client about quote"

    def test_metadata_optional(self):
        """ActivityLog metadata should be optional."""
        from src.api.routes import ActivityLog

        log = ActivityLog(
            activity_type="email",
            description="Sent email"
        )

        assert log.metadata is None

    def test_accepts_metadata(self):
        """ActivityLog should accept metadata dict."""
        from src.api.routes import ActivityLog

        log = ActivityLog(
            activity_type="email",
            description="Sent quote",
            metadata={"quote_id": "123", "recipient": "test@test.com"}
        )

        assert log.metadata["quote_id"] == "123"


class TestInvoiceCreateModel:
    """Tests for InvoiceCreate model."""

    def test_requires_quote_id(self):
        """InvoiceCreate should require quote_id."""
        from src.api.routes import InvoiceCreate

        invoice = InvoiceCreate(quote_id="quote-123")

        assert invoice.quote_id == "quote-123"

    def test_default_values(self):
        """InvoiceCreate should have defaults."""
        from src.api.routes import InvoiceCreate

        invoice = InvoiceCreate(quote_id="quote-123")

        assert invoice.items is None
        assert invoice.notes is None
        assert invoice.due_days == 7


class TestManualInvoiceCreateModel:
    """Tests for ManualInvoiceCreate model."""

    def test_requires_fields(self):
        """ManualInvoiceCreate should require customer details and items."""
        from src.api.routes import ManualInvoiceCreate

        invoice = ManualInvoiceCreate(
            customer_name="John Doe",
            customer_email="john@test.com",
            items=[{"description": "Service", "quantity": 1, "unit_price": 100, "amount": 100}]
        )

        assert invoice.customer_name == "John Doe"
        assert len(invoice.items) == 1

    def test_default_values(self):
        """ManualInvoiceCreate should have defaults."""
        from src.api.routes import ManualInvoiceCreate

        invoice = ManualInvoiceCreate(
            customer_name="John",
            customer_email="john@test.com",
            items=[]
        )

        assert invoice.due_days == 14
        assert invoice.customer_phone is None
        assert invoice.destination is None


class TestInvoiceStatusUpdateModel:
    """Tests for InvoiceStatusUpdate model."""

    def test_requires_status(self):
        """InvoiceStatusUpdate should require status."""
        from src.api.routes import InvoiceStatusUpdate

        update = InvoiceStatusUpdate(status="paid")

        assert update.status == "paid"

    def test_optional_fields(self):
        """InvoiceStatusUpdate should have optional payment fields."""
        from src.api.routes import InvoiceStatusUpdate

        update = InvoiceStatusUpdate(status="paid")

        assert update.payment_date is None
        assert update.payment_reference is None

    def test_with_payment_details(self):
        """InvoiceStatusUpdate should accept payment details."""
        from src.api.routes import InvoiceStatusUpdate

        update = InvoiceStatusUpdate(
            status="paid",
            payment_date="2026-01-15",
            payment_reference="REF-123"
        )

        assert update.payment_date == "2026-01-15"
        assert update.payment_reference == "REF-123"


class TestInvoiceSendRequestModel:
    """Tests for InvoiceSendRequest model."""

    def test_all_optional(self):
        """InvoiceSendRequest should have all optional fields."""
        from src.api.routes import InvoiceSendRequest

        request = InvoiceSendRequest()

        assert request.consultant_email is None

    def test_accepts_consultant_email(self):
        """InvoiceSendRequest should accept consultant_email."""
        from src.api.routes import InvoiceSendRequest

        request = InvoiceSendRequest(
            consultant_email="consultant@test.com"
        )

        assert request.consultant_email == "consultant@test.com"


# ==================== Router Tests ====================

class TestRouterConfiguration:
    """Tests for router configuration."""

    def test_quotes_router_prefix(self):
        """Quotes router should have correct prefix."""
        from src.api.routes import quotes_router

        assert quotes_router.prefix == "/api/v1/quotes"
        assert "Quotes" in quotes_router.tags

    def test_crm_router_prefix(self):
        """CRM router should have correct prefix."""
        from src.api.routes import crm_router

        assert crm_router.prefix == "/api/v1/crm"
        assert "CRM" in crm_router.tags

    def test_invoices_router_prefix(self):
        """Invoices router should have correct prefix."""
        from src.api.routes import invoices_router

        assert invoices_router.prefix == "/api/v1/invoices"
        assert "Invoices" in invoices_router.tags

    def test_public_router_prefix(self):
        """Public router should have correct prefix."""
        from src.api.routes import public_router

        assert public_router.prefix == "/api/v1/public"
        assert "Public" in public_router.tags

    def test_legacy_webhook_router_prefix(self):
        """Legacy webhook router should have correct prefix."""
        from src.api.routes import legacy_webhook_router

        assert legacy_webhook_router.prefix == "/api/webhooks"


# ==================== Dependency Function Tests ====================

class TestGetClientConfigDependency:
    """Tests for get_client_config dependency."""

    def test_uses_header_value(self):
        """Should use X-Client-ID header value."""
        from src.api.routes import get_client_config, _get_cached_config

        # Clear cache first
        _get_cached_config.cache_clear()

        with patch('src.api.routes._get_cached_config') as mock_cached:
            mock_config = MagicMock()
            mock_cached.return_value = mock_config

            result = get_client_config(x_client_id="test-tenant")

            mock_cached.assert_called_once_with("test-tenant")

    def test_falls_back_to_env_var(self):
        """Should fall back to CLIENT_ID env var."""
        from src.api.routes import get_client_config, _get_cached_config

        _get_cached_config.cache_clear()

        with patch('src.api.routes._get_cached_config') as mock_cached:
            mock_config = MagicMock()
            mock_cached.return_value = mock_config

            with patch.dict('os.environ', {'CLIENT_ID': 'env-tenant'}):
                result = get_client_config(x_client_id=None)

                mock_cached.assert_called_once_with("env-tenant")

    def test_raises_on_invalid_client(self):
        """Should raise HTTPException for invalid client."""
        from src.api.routes import get_client_config, _get_cached_config
        from fastapi import HTTPException

        _get_cached_config.cache_clear()

        with patch('src.api.routes._get_cached_config') as mock_cached:
            mock_cached.side_effect = Exception("Not found")

            with pytest.raises(HTTPException) as exc_info:
                get_client_config(x_client_id="unknown")

            assert exc_info.value.status_code == 400


class TestCacheHelpers:
    """Tests for cached helper functions."""

    def test_get_cached_config_caches(self):
        """_get_cached_config should cache results."""
        from src.api.routes import _get_cached_config

        _get_cached_config.cache_clear()

        with patch('src.api.routes.ClientConfig') as MockConfig:
            mock_config = MagicMock()
            MockConfig.return_value = mock_config

            # First call
            result1 = _get_cached_config("test-client")
            # Second call
            result2 = _get_cached_config("test-client")

            # Should only create once
            assert MockConfig.call_count == 1
            assert result1 is result2

    def test_get_cached_config_different_clients(self):
        """_get_cached_config should cache per client."""
        from src.api.routes import _get_cached_config

        _get_cached_config.cache_clear()

        with patch('src.api.routes.ClientConfig') as MockConfig:
            mock_config1 = MagicMock()
            mock_config2 = MagicMock()
            MockConfig.side_effect = [mock_config1, mock_config2]

            result1 = _get_cached_config("client-1")
            result2 = _get_cached_config("client-2")

            assert MockConfig.call_count == 2
            assert result1 is not result2


# ==================== Endpoint Auth Tests ====================

class TestEndpointAuth:
    """Tests for endpoint authentication."""

    @pytest.fixture
    def test_client(self):
        """Create test client."""
        from main import app
        return TestClient(app)

    def test_quotes_list_requires_auth(self, test_client):
        """GET /quotes should require auth."""
        response = test_client.get(
            "/api/v1/quotes",
            headers={"X-Client-ID": "example"}
        )
        assert response.status_code == 401

    def test_crm_clients_requires_auth(self, test_client):
        """GET /crm/clients should require auth."""
        response = test_client.get(
            "/api/v1/crm/clients",
            headers={"X-Client-ID": "example"}
        )
        assert response.status_code == 401

    def test_invoices_list_requires_auth(self, test_client):
        """GET /invoices should require auth."""
        response = test_client.get(
            "/api/v1/invoices",
            headers={"X-Client-ID": "example"}
        )
        assert response.status_code == 401

    def test_quote_generate_requires_auth(self, test_client):
        """POST /quotes/generate should require auth."""
        response = test_client.post(
            "/api/v1/quotes/generate",
            headers={"X-Client-ID": "example"},
            json={
                "inquiry": {
                    "name": "Test",
                    "email": "test@test.com",
                    "destination": "Test"
                }
            }
        )
        assert response.status_code == 401
