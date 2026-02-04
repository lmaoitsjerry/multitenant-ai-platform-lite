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


# ==================== Unit Tests for Endpoint Handlers ====================

class TestGenerateQuoteUnit:
    """Unit tests for generate_quote endpoint handler."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        config = MagicMock()
        config.client_id = "test-tenant"
        config.currency = "USD"
        return config

    @pytest.mark.asyncio
    async def test_generate_quote_success(self, mock_config):
        """generate_quote should return quote result."""
        from src.api.routes import generate_quote, QuoteGenerateRequest, TravelInquiry

        mock_agent = MagicMock()
        mock_agent.generate_quote.return_value = {
            'success': True,
            'quote_id': 'quote-123',
            'total': 5000
        }

        request = QuoteGenerateRequest(
            inquiry=TravelInquiry(
                name="John Doe",
                email="john@test.com",
                destination="Zanzibar"
            )
        )

        with patch('src.api.routes.get_quote_agent', return_value=mock_agent):
            result = await generate_quote(request=request, config=mock_config)

        assert result['success'] is True
        assert result['quote_id'] == 'quote-123'

    @pytest.mark.asyncio
    async def test_generate_quote_error(self, mock_config):
        """generate_quote should handle errors."""
        from src.api.routes import generate_quote, QuoteGenerateRequest, TravelInquiry
        from fastapi import HTTPException

        mock_agent = MagicMock()
        mock_agent.generate_quote.side_effect = Exception("Quote generation failed")

        request = QuoteGenerateRequest(
            inquiry=TravelInquiry(
                name="John",
                email="john@test.com",
                destination="Test"
            )
        )

        with patch('src.api.routes.get_quote_agent', return_value=mock_agent):
            with pytest.raises(HTTPException) as exc_info:
                await generate_quote(request=request, config=mock_config)

            assert exc_info.value.status_code == 500


class TestListQuotesUnit:
    """Unit tests for list_quotes endpoint handler."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.client_id = "test-tenant"
        return config

    @pytest.mark.asyncio
    async def test_list_quotes_success(self, mock_config):
        """list_quotes should return list of quotes."""
        from src.api.routes import list_quotes

        mock_agent = MagicMock()
        mock_agent.list_quotes.return_value = [
            {'quote_id': 'q1', 'status': 'sent'},
            {'quote_id': 'q2', 'status': 'draft'}
        ]

        with patch('src.api.routes.get_quote_agent', return_value=mock_agent):
            result = await list_quotes(
                status=None,
                limit=50,
                offset=0,
                config=mock_config,
                x_client_id="test-tenant"
            )

        assert result['success'] is True
        assert result['count'] == 2


class TestGetQuoteUnit:
    """Unit tests for get_quote endpoint handler."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.client_id = "test-tenant"
        return config

    @pytest.mark.asyncio
    async def test_get_quote_success(self, mock_config):
        """get_quote should return quote by ID."""
        from src.api.routes import get_quote

        mock_agent = MagicMock()
        mock_agent.get_quote.return_value = {
            'quote_id': 'q1',
            'customer_name': 'John',
            'status': 'sent'
        }

        with patch('src.api.routes.get_quote_agent', return_value=mock_agent):
            result = await get_quote(quote_id="q1", config=mock_config)

        assert result['success'] is True
        assert result['data']['quote_id'] == 'q1'

    @pytest.mark.asyncio
    async def test_get_quote_not_found(self, mock_config):
        """get_quote should raise 404 when not found."""
        from src.api.routes import get_quote
        from fastapi import HTTPException

        mock_agent = MagicMock()
        mock_agent.get_quote.return_value = None

        with patch('src.api.routes.get_quote_agent', return_value=mock_agent):
            with pytest.raises(HTTPException) as exc_info:
                await get_quote(quote_id="notfound", config=mock_config)

            assert exc_info.value.status_code == 404


class TestListClientsUnit:
    """Unit tests for list_clients endpoint handler."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.client_id = "test-tenant"
        return config

    @pytest.mark.asyncio
    async def test_list_clients_success(self, mock_config):
        """list_clients should return list of clients."""
        from src.api.routes import list_clients

        mock_crm = MagicMock()
        mock_crm.search_clients.return_value = [
            {'id': 'c1', 'name': 'Client 1'},
            {'id': 'c2', 'name': 'Client 2'}
        ]

        with patch('src.api.routes.get_crm_service', return_value=mock_crm):
            result = await list_clients(
                query=None,
                stage=None,
                consultant_id=None,
                limit=50,
                offset=0,
                config=mock_config
            )

        assert result['success'] is True
        assert result['count'] == 2


class TestCreateClientUnit:
    """Unit tests for create_client endpoint handler."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.client_id = "test-tenant"
        return config

    @pytest.mark.asyncio
    async def test_create_client_success(self, mock_config):
        """create_client should create and return client."""
        from src.api.routes import create_client, ClientCreate

        mock_crm = MagicMock()
        mock_crm.get_or_create_client.return_value = {
            'id': 'new-client',
            'email': 'test@example.com',
            'name': 'Test Client',
            'created': True
        }

        client = ClientCreate(
            email="test@example.com",
            name="Test Client"
        )

        with patch('src.api.routes.get_crm_service', return_value=mock_crm):
            result = await create_client(client=client, config=mock_config)

        assert result['success'] is True
        assert result['data']['id'] == 'new-client'

    @pytest.mark.asyncio
    async def test_create_client_db_failure(self, mock_config):
        """create_client should raise 500 on database failure."""
        from src.api.routes import create_client, ClientCreate
        from fastapi import HTTPException

        mock_crm = MagicMock()
        mock_crm.get_or_create_client.return_value = None

        client = ClientCreate(
            email="test@example.com",
            name="Test Client"
        )

        with patch('src.api.routes.get_crm_service', return_value=mock_crm):
            with pytest.raises(HTTPException) as exc_info:
                await create_client(client=client, config=mock_config)

            assert exc_info.value.status_code == 500


class TestGetClientUnit:
    """Unit tests for get_client endpoint handler."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.client_id = "test-tenant"
        return config

    @pytest.mark.asyncio
    async def test_get_client_success(self, mock_config):
        """get_client should return client by ID."""
        from src.api.routes import get_client

        mock_crm = MagicMock()
        mock_crm.get_client.return_value = {
            'id': 'c1',
            'name': 'Client 1',
            'email': 'client@test.com'
        }

        with patch('src.api.routes.get_crm_service', return_value=mock_crm):
            result = await get_client(client_id="c1", config=mock_config)

        assert result['success'] is True
        assert result['data']['id'] == 'c1'

    @pytest.mark.asyncio
    async def test_get_client_not_found(self, mock_config):
        """get_client should raise 404 when not found."""
        from src.api.routes import get_client
        from fastapi import HTTPException

        mock_crm = MagicMock()
        mock_crm.get_client.return_value = None

        with patch('src.api.routes.get_crm_service', return_value=mock_crm):
            with pytest.raises(HTTPException) as exc_info:
                await get_client(client_id="notfound", config=mock_config)

            assert exc_info.value.status_code == 404


class TestListInvoicesUnit:
    """Unit tests for list_invoices endpoint handler."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.client_id = "test-tenant"
        return config

    @pytest.mark.asyncio
    async def test_list_invoices_success(self, mock_config):
        """list_invoices should return list of invoices."""
        from src.api.routes import list_invoices

        mock_supabase = MagicMock()
        mock_supabase.list_invoices.return_value = [
            {'invoice_id': 'inv-1', 'status': 'pending'},
            {'invoice_id': 'inv-2', 'status': 'paid'}
        ]

        with patch('src.tools.supabase_tool.SupabaseTool', return_value=mock_supabase):
            result = await list_invoices(
                status=None,
                limit=50,
                offset=0,
                config=mock_config
            )

        assert result['success'] is True
        assert result['count'] == 2


class TestGetInvoiceUnit:
    """Unit tests for get_invoice endpoint handler."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.client_id = "test-tenant"
        return config

    @pytest.mark.asyncio
    async def test_get_invoice_success(self, mock_config):
        """get_invoice should return invoice by ID."""
        from src.api.routes import get_invoice

        mock_supabase = MagicMock()
        mock_supabase.get_invoice.return_value = {
            'invoice_id': 'inv-1',
            'customer_name': 'John',
            'total_amount': 1000
        }

        with patch('src.tools.supabase_tool.SupabaseTool', return_value=mock_supabase):
            result = await get_invoice(invoice_id="inv-1", config=mock_config)

        assert result['success'] is True
        assert result['data']['invoice_id'] == 'inv-1'

    @pytest.mark.asyncio
    async def test_get_invoice_not_found(self, mock_config):
        """get_invoice should raise 404 when not found."""
        from src.api.routes import get_invoice
        from fastapi import HTTPException

        mock_supabase = MagicMock()
        mock_supabase.get_invoice.return_value = None

        with patch('src.tools.supabase_tool.SupabaseTool', return_value=mock_supabase):
            with pytest.raises(HTTPException) as exc_info:
                await get_invoice(invoice_id="notfound", config=mock_config)

            assert exc_info.value.status_code == 404


class TestUpdateInvoiceStatusUnit:
    """Unit tests for update_invoice_status endpoint handler."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.client_id = "test-tenant"
        config.currency = "USD"
        return config

    @pytest.mark.asyncio
    async def test_update_invoice_status_success(self, mock_config):
        """update_invoice_status should update and return invoice."""
        from src.api.routes import update_invoice_status, InvoiceStatusUpdate

        mock_supabase = MagicMock()
        mock_supabase.update_invoice_status.return_value = True
        mock_supabase.get_invoice.return_value = {
            'invoice_id': 'inv-1',
            'status': 'paid',
            'customer_name': 'John',
            'total_amount': 1000
        }

        update = InvoiceStatusUpdate(status="paid")

        with patch('src.tools.supabase_tool.SupabaseTool', return_value=mock_supabase):
            with patch('src.api.notifications_routes.NotificationService') as mock_notif:
                result = await update_invoice_status(
                    invoice_id="inv-1",
                    update=update,
                    config=mock_config
                )

        assert result['success'] is True
        assert result['data']['status'] == 'paid'

    @pytest.mark.asyncio
    async def test_update_invoice_status_failure(self, mock_config):
        """update_invoice_status should raise 500 on failure."""
        from src.api.routes import update_invoice_status, InvoiceStatusUpdate
        from fastapi import HTTPException

        mock_supabase = MagicMock()
        mock_supabase.update_invoice_status.return_value = False

        update = InvoiceStatusUpdate(status="paid")

        with patch('src.tools.supabase_tool.SupabaseTool', return_value=mock_supabase):
            with pytest.raises(HTTPException) as exc_info:
                await update_invoice_status(
                    invoice_id="inv-1",
                    update=update,
                    config=mock_config
                )

            assert exc_info.value.status_code == 500


class TestCreateManualInvoiceUnit:
    """Unit tests for create_manual_invoice endpoint handler."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.client_id = "test-tenant"
        config.currency = "USD"
        return config

    @pytest.mark.asyncio
    async def test_create_manual_invoice_success(self, mock_config):
        """create_manual_invoice should create invoice."""
        from src.api.routes import create_manual_invoice, ManualInvoiceCreate

        mock_supabase = MagicMock()
        mock_supabase.create_invoice.return_value = {
            'invoice_id': 'new-inv',
            'customer_name': 'John',
            'total_amount': 500
        }

        request = ManualInvoiceCreate(
            customer_name="John",
            customer_email="john@test.com",
            items=[{'description': 'Service', 'quantity': 1, 'unit_price': 500, 'amount': 500}]
        )

        with patch('src.tools.supabase_tool.SupabaseTool', return_value=mock_supabase):
            result = await create_manual_invoice(request=request, config=mock_config)

        assert result['success'] is True
        assert result['invoice_id'] == 'new-inv'

    @pytest.mark.asyncio
    async def test_create_manual_invoice_no_items(self, mock_config):
        """create_manual_invoice should reject empty items."""
        from src.api.routes import create_manual_invoice, ManualInvoiceCreate
        from fastapi import HTTPException

        request = ManualInvoiceCreate(
            customer_name="John",
            customer_email="john@test.com",
            items=[]
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_manual_invoice(request=request, config=mock_config)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_create_manual_invoice_calculates_total(self, mock_config):
        """create_manual_invoice should calculate amount from qty*unit_price."""
        from src.api.routes import create_manual_invoice, ManualInvoiceCreate

        mock_supabase = MagicMock()
        mock_supabase.create_invoice.return_value = {
            'invoice_id': 'new-inv',
            'total_amount': 300
        }

        request = ManualInvoiceCreate(
            customer_name="John",
            customer_email="john@test.com",
            items=[
                {'description': 'Item 1', 'quantity': 2, 'unit_price': 100},
                {'description': 'Item 2', 'quantity': 1, 'unit_price': 100}
            ]
        )

        with patch('src.tools.supabase_tool.SupabaseTool', return_value=mock_supabase):
            result = await create_manual_invoice(request=request, config=mock_config)

        # Check that create_invoice was called with correct total
        call_args = mock_supabase.create_invoice.call_args
        assert call_args[1]['total_amount'] == 300


class TestPipelineSummaryUnit:
    """Unit tests for pipeline summary endpoints."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.client_id = "test-tenant"
        return config

    @pytest.mark.asyncio
    async def test_get_pipeline_summary_success(self, mock_config):
        """get_pipeline_summary should return pipeline data."""
        from src.api.routes import get_pipeline_summary

        mock_crm = MagicMock()
        mock_crm.get_pipeline_summary.return_value = {
            'QUOTED': 10,
            'NEGOTIATING': 5,
            'BOOKED': 3,
            'PAID': 2
        }

        with patch('src.api.routes.get_crm_service', return_value=mock_crm):
            result = await get_pipeline_summary(config=mock_config)

        assert result['success'] is True
        assert result['data']['QUOTED'] == 10


class TestPublicInvoiceHelpers:
    """Unit tests for public invoice helper functions."""

    def test_get_invoice_public_invalid_format(self):
        """get_invoice_public should reject invalid UUID format."""
        from src.api.routes import get_invoice_public

        result = get_invoice_public("invalid-id")
        assert result is None

    def test_get_invoice_public_valid_format(self):
        """get_invoice_public should accept valid UUID format."""
        from src.api.routes import get_invoice_public
        import httpx

        with patch.dict('os.environ', {'SUPABASE_URL': 'http://test', 'SUPABASE_KEY': 'key'}):
            with patch.object(httpx, 'get') as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.raise_for_status = MagicMock()
                mock_response.json.return_value = [{'invoice_id': '12345678-1234-1234-1234-123456789abc'}]
                mock_get.return_value = mock_response

                result = get_invoice_public("12345678-1234-1234-1234-123456789abc")

        assert result is not None

    def test_get_quote_public_invalid_format(self):
        """get_quote_public should reject invalid UUID format."""
        from src.api.routes import get_quote_public

        result = get_quote_public("invalid-id")
        assert result is None

    def test_get_invoice_public_no_env_vars(self):
        """get_invoice_public should return None without env vars."""
        from src.api.routes import get_invoice_public

        with patch.dict('os.environ', {'SUPABASE_URL': '', 'SUPABASE_KEY': ''}):
            result = get_invoice_public("12345678-1234-1234-1234-123456789abc")

        assert result is None


class TestIncludeRouters:
    """Unit tests for include_routers function."""

    def test_include_routers_includes_all(self):
        """include_routers should include all routers."""
        from src.api.routes import include_routers

        mock_app = MagicMock()

        with patch.multiple(
            'src.api.routes',
            quotes_router=MagicMock(),
            crm_router=MagicMock(),
            invoices_router=MagicMock(),
            public_router=MagicMock(),
            legacy_webhook_router=MagicMock(),
            email_webhook_router=MagicMock()
        ):
            include_routers(mock_app)

        # Should have called include_router multiple times
        assert mock_app.include_router.call_count > 5


class TestLogActivityUnit:
    """Unit tests for log_activity endpoint handler."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.client_id = "test-tenant"
        return config

    @pytest.mark.asyncio
    async def test_log_activity_success(self, mock_config):
        """log_activity should log activity and return success."""
        from src.api.routes import log_activity, ActivityLog

        mock_supabase = MagicMock()
        mock_supabase.log_activity.return_value = True

        activity = ActivityLog(
            activity_type="call",
            description="Called about quote"
        )

        with patch('src.tools.supabase_tool.SupabaseTool', return_value=mock_supabase):
            result = await log_activity(
                client_id="c1",
                activity=activity,
                config=mock_config
            )

        assert result['success'] is True

    @pytest.mark.asyncio
    async def test_log_activity_failure(self, mock_config):
        """log_activity should raise 500 on failure."""
        from src.api.routes import log_activity, ActivityLog
        from fastapi import HTTPException

        mock_supabase = MagicMock()
        mock_supabase.log_activity.return_value = False

        activity = ActivityLog(
            activity_type="call",
            description="Called about quote"
        )

        with patch('src.tools.supabase_tool.SupabaseTool', return_value=mock_supabase):
            with pytest.raises(HTTPException) as exc_info:
                await log_activity(
                    client_id="c1",
                    activity=activity,
                    config=mock_config
                )

            assert exc_info.value.status_code == 500


class TestGetCRMStatsUnit:
    """Unit tests for get_crm_stats endpoint handler."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.client_id = "test-tenant"
        return config

    @pytest.mark.asyncio
    async def test_get_crm_stats_success(self, mock_config):
        """get_crm_stats should return CRM statistics."""
        from src.api.routes import get_crm_stats

        mock_crm = MagicMock()
        mock_crm.get_client_stats.return_value = {
            'total_clients': 100,
            'active_clients': 80,
            'conversion_rate': 0.25
        }

        with patch('src.api.routes.get_crm_service', return_value=mock_crm):
            result = await get_crm_stats(config=mock_config)

        assert result['success'] is True
        assert result['data']['total_clients'] == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
