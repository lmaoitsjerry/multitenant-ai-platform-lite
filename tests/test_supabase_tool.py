"""
SupabaseTool Unit Tests

Comprehensive tests for SupabaseTool methods:
- CRUD operations for quotes, invoices, clients, tickets
- Tenant isolation (all queries filter by tenant_id)
- Error handling
- Edge cases

Uses pytest with mocked Supabase client.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime, timedelta
import uuid


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


def create_chainable_mock():
    """Create a mock that supports method chaining for Supabase queries."""
    mock = MagicMock()
    mock.select.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.delete.return_value = mock
    mock.eq.return_value = mock
    mock.neq.return_value = mock
    mock.gt.return_value = mock
    mock.gte.return_value = mock
    mock.lt.return_value = mock
    mock.lte.return_value = mock
    mock.is_.return_value = mock
    mock.in_.return_value = mock
    mock.order.return_value = mock
    mock.limit.return_value = mock
    mock.range.return_value = mock
    mock.single.return_value = mock
    return mock


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client."""
    client = MagicMock()
    return client


# ==================== Initialization Tests ====================

class TestSupabaseToolInit:
    """Test SupabaseTool initialization."""

    def test_init_sets_tenant_id(self, mock_config):
        """Should set tenant_id from config."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_get_client.return_value = MagicMock()

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            assert tool.tenant_id == "test_tenant"

    def test_init_without_supabase_library(self, mock_config):
        """Should handle missing Supabase library gracefully."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_get_client.return_value = None

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            # Should not crash, client should be None
            assert tool.client is None

    def test_table_constants_defined(self, mock_config):
        """Should have table name constants defined."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_get_client.return_value = MagicMock()

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            assert SupabaseTool.TABLE_QUOTES == "quotes"
            assert SupabaseTool.TABLE_INVOICES == "invoices"
            assert SupabaseTool.TABLE_CLIENTS == "clients"
            assert SupabaseTool.TABLE_TICKETS == "inbound_tickets"
            assert SupabaseTool.TABLE_CALL_QUEUE == "outbound_call_queue"


# ==================== Ticket Operations Tests ====================

class TestTicketOperations:
    """Test ticket CRUD operations."""

    def test_create_ticket_success(self, mock_config):
        """Should create ticket with all required fields."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            # Setup mock response
            mock_result = MagicMock()
            mock_result.data = [{
                'id': 'ticket_123',
                'tenant_id': 'test_tenant',
                'ticket_id': 'TKT-20260121-ABC123',
                'customer_name': 'John Doe',
                'customer_email': 'john@example.com',
                'subject': 'Test Subject',
                'message': 'Test message',
                'status': 'open'
            }]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.create_ticket(
                customer_name='John Doe',
                customer_email='john@example.com',
                subject='Test Subject',
                message='Test message'
            )

            assert result is not None
            assert result['customer_name'] == 'John Doe'

    def test_create_ticket_includes_tenant_id(self, mock_config):
        """Created ticket should include tenant_id for isolation."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [{'tenant_id': 'test_tenant'}]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            tool.create_ticket(
                customer_name='Jane',
                customer_email='jane@example.com',
                subject='Test',
                message='Test'
            )

            # Verify insert was called with tenant_id
            chain.insert.assert_called_once()
            call_args = chain.insert.call_args[0][0]
            assert call_args['tenant_id'] == 'test_tenant'

    def test_create_ticket_returns_none_without_client(self, mock_config):
        """Should return None when Supabase client unavailable."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_get_client.return_value = None

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.create_ticket(
                customer_name='Test',
                customer_email='test@example.com',
                subject='Test',
                message='Test'
            )

            assert result is None

    def test_get_tickets_filters_by_tenant(self, mock_config):
        """get_tickets should filter by tenant_id."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [{'ticket_id': 'TKT-1'}, {'ticket_id': 'TKT-2'}]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.get_tickets()

            assert len(result) == 2
            # Verify tenant filter was applied
            chain.eq.assert_any_call('tenant_id', 'test_tenant')

    def test_get_tickets_with_status_filter(self, mock_config):
        """get_tickets should apply status filter when provided."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [{'ticket_id': 'TKT-1', 'status': 'open'}]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.get_tickets(status='open')

            assert len(result) == 1
            # Should have called eq for status
            chain.eq.assert_any_call('status', 'open')

    def test_update_ticket_success(self, mock_config):
        """update_ticket should update and filter by tenant."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            chain = create_chainable_mock()
            chain.execute.return_value = MagicMock()
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.update_ticket(
                ticket_id='TKT-123',
                status='closed',
                notes='Resolved'
            )

            assert result is True


# ==================== Invoice Operations Tests ====================

class TestInvoiceOperations:
    """Test invoice CRUD operations."""

    def test_create_invoice_success(self, mock_config):
        """Should create invoice with all required fields."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [{
                'id': 'inv_123',
                'invoice_id': 'INV-20260121-ABC123',
                'tenant_id': 'test_tenant',
                'customer_name': 'John Doe',
                'total_amount': 1500.00
            }]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.create_invoice(
                customer_name='John Doe',
                customer_email='john@example.com',
                items=[{'description': 'Hotel', 'amount': 1500}],
                total_amount=1500.00
            )

            assert result is not None
            assert result['total_amount'] == 1500.00

    def test_create_invoice_includes_tenant_id(self, mock_config):
        """Invoice should include tenant_id for isolation."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [{'tenant_id': 'test_tenant'}]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            tool.create_invoice(
                customer_name='Test Customer',
                customer_email='test@example.com',
                items=[{'description': 'Item', 'amount': 100}],
                total_amount=100
            )

            call_args = chain.insert.call_args[0][0]
            assert call_args['tenant_id'] == 'test_tenant'

    def test_create_invoice_with_quote_id(self, mock_config):
        """Invoice creation should link to quote_id if provided."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [{'quote_id': 'QT-12345'}]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            tool.create_invoice(
                customer_name='Test',
                customer_email='test@example.com',
                items=[{'description': 'Item', 'amount': 100}],
                total_amount=100,
                quote_id='QT-12345'
            )

            call_args = chain.insert.call_args[0][0]
            assert call_args['quote_id'] == 'QT-12345'

    def test_get_invoice_by_id(self, mock_config):
        """get_invoice should retrieve by invoice_id with tenant filter."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = {'invoice_id': 'INV-123', 'total_amount': 500}

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.get_invoice('INV-123')

            assert result is not None
            assert result['invoice_id'] == 'INV-123'

    def test_get_invoice_not_found(self, mock_config):
        """get_invoice should return None for non-existent invoice."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            chain = create_chainable_mock()
            chain.execute.side_effect = Exception("No rows returned")
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.get_invoice('NON-EXISTENT')

            assert result is None

    def test_list_invoices_returns_list(self, mock_config):
        """list_invoices should return list of invoices."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [
                {'invoice_id': 'INV-1', 'total_amount': 100},
                {'invoice_id': 'INV-2', 'total_amount': 200}
            ]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.list_invoices()

            assert len(result) == 2

    def test_list_invoices_with_status_filter(self, mock_config):
        """list_invoices should filter by status when provided."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [{'invoice_id': 'INV-1', 'status': 'paid'}]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.list_invoices(status='paid')

            assert len(result) == 1
            # eq should be called for status
            chain.eq.assert_any_call('status', 'paid')

    def test_update_invoice_status_success(self, mock_config):
        """update_invoice_status should update status."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            chain = create_chainable_mock()
            chain.execute.return_value = MagicMock()
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.update_invoice_status('INV-123', 'paid')

            assert result is True

    def test_update_invoice_status_paid_sets_paid_at(self, mock_config):
        """update_invoice_status with 'paid' should set paid_at timestamp."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            chain = create_chainable_mock()
            chain.execute.return_value = MagicMock()
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            tool.update_invoice_status('INV-123', 'paid')

            call_args = chain.update.call_args[0][0]
            assert 'paid_at' in call_args


# ==================== Client/CRM Operations Tests ====================

class TestClientOperations:
    """Test CRM client operations."""

    def test_create_client_success(self, mock_config):
        """Should create CRM client."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [{
                'client_id': 'client_123',
                'tenant_id': 'test_tenant',
                'email': 'john@example.com',
                'name': 'John Doe'
            }]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.create_client(
                email='john@example.com',
                name='John Doe'
            )

            assert result is not None
            assert result['email'] == 'john@example.com'

    def test_create_client_normalizes_email(self, mock_config):
        """create_client should lowercase email."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [{'email': 'john@example.com'}]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            tool.create_client(
                email='JOHN@EXAMPLE.COM',
                name='John'
            )

            call_args = chain.insert.call_args[0][0]
            assert call_args['email'] == 'john@example.com'

    def test_get_client_by_email(self, mock_config):
        """get_client_by_email should find client by email."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = {'email': 'john@example.com', 'name': 'John'}

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.get_client_by_email('john@example.com')

            assert result is not None
            assert result['email'] == 'john@example.com'

    def test_get_client_by_email_not_found(self, mock_config):
        """get_client_by_email should return None for unknown email."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            chain = create_chainable_mock()
            chain.execute.side_effect = Exception("No rows")
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.get_client_by_email('unknown@example.com')

            assert result is None

    def test_update_client_stage_valid(self, mock_config):
        """update_client_stage should update with valid stage."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            chain = create_chainable_mock()
            chain.execute.return_value = MagicMock()
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.update_client_stage('client_123', 'BOOKED')

            assert result is True

    def test_update_client_stage_invalid(self, mock_config):
        """update_client_stage should reject invalid stage."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.update_client_stage('client_123', 'INVALID_STAGE')

            assert result is False

    def test_log_activity_success(self, mock_config):
        """log_activity should create activity record."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            chain = create_chainable_mock()
            chain.execute.return_value = MagicMock()
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.log_activity(
                client_id='client_123',
                activity_type='email',
                description='Sent quote email'
            )

            assert result is True

    def test_get_client_activities(self, mock_config):
        """get_client_activities should return activities list."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [
                {'activity_type': 'email', 'description': 'Sent quote'},
                {'activity_type': 'call', 'description': 'Follow-up call'}
            ]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.get_client_activities('client_123')

            assert len(result) == 2


# ==================== Call Queue Operations Tests ====================

class TestCallQueueOperations:
    """Test outbound call queue operations."""

    def test_queue_outbound_call_success(self, mock_config):
        """Should queue outbound call."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [{
                'id': 'queue_123',
                'phone_number': '+1234567890',
                'call_status': 'queued'
            }]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.queue_outbound_call(
                client_name='John Doe',
                client_email='john@example.com',
                phone_number='+1234567890',
                quote_details={'destination': 'Cape Town'}
            )

            assert result is not None
            assert result['call_status'] == 'queued'

    def test_get_pending_calls(self, mock_config):
        """get_pending_calls should return queued calls."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [
                {'id': 'call_1', 'call_status': 'queued'},
                {'id': 'call_2', 'call_status': 'queued'}
            ]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.get_pending_calls()

            assert len(result) == 2

    def test_update_call_status(self, mock_config):
        """update_call_status should update call status."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            chain = create_chainable_mock()
            chain.execute.return_value = MagicMock()
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.update_call_status(
                queue_id='queue_123',
                status='completed',
                call_id='call_abc',
                outcome='success'
            )

            assert result is True

    def test_save_call_record(self, mock_config):
        """save_call_record should create call record."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [{
                'call_id': 'call_123',
                'outcome': 'success',
                'duration_seconds': 120
            }]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.save_call_record(
                call_id='call_123',
                phone_number='+1234567890',
                transcript='Hello, this is a test call.',
                outcome='success',
                duration_seconds=120
            )

            assert result is not None
            assert result['outcome'] == 'success'


# ==================== Tenant Settings Tests ====================

class TestTenantSettings:
    """Test tenant settings operations."""

    def test_get_tenant_settings(self, mock_config):
        """get_tenant_settings should retrieve settings."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = {
                'tenant_id': 'test_tenant',
                'company_name': 'Test Company',
                'currency': 'USD'
            }

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.get_tenant_settings()

            assert result is not None
            assert result['company_name'] == 'Test Company'

    def test_get_tenant_settings_not_found(self, mock_config):
        """get_tenant_settings should return None if not found."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            chain = create_chainable_mock()
            chain.execute.side_effect = Exception("No rows")
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.get_tenant_settings()

            assert result is None

    def test_update_tenant_settings_create(self, mock_config):
        """update_tenant_settings should create if not exists."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            # First call (get) throws, second call (insert) succeeds
            chain = create_chainable_mock()

            mock_insert_result = MagicMock()
            mock_insert_result.data = [{'tenant_id': 'test_tenant', 'company_name': 'New Company'}]

            # Make execute return the insert result
            call_count = [0]
            def side_effect():
                call_count[0] += 1
                if call_count[0] == 1:
                    raise Exception("No rows")
                return mock_insert_result

            chain.execute.side_effect = side_effect
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.update_tenant_settings(company_name='New Company')

            assert result is not None

    def test_update_tenant_settings_update(self, mock_config):
        """update_tenant_settings should update if exists."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_get_result = MagicMock()
            mock_get_result.data = {'tenant_id': 'test_tenant', 'company_name': 'Old Company'}

            mock_update_result = MagicMock()
            mock_update_result.data = [{'company_name': 'Updated Company'}]

            chain = create_chainable_mock()

            call_count = [0]
            def side_effect():
                call_count[0] += 1
                if call_count[0] == 1:
                    return mock_get_result
                return mock_update_result

            chain.execute.side_effect = side_effect
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.update_tenant_settings(company_name='Updated Company')

            assert result is not None


# ==================== Branding Operations Tests ====================

class TestBrandingOperations:
    """Test tenant branding operations."""

    def test_get_branding(self, mock_config):
        """get_branding should retrieve branding config."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = {
                'tenant_id': 'test_tenant',
                'preset_theme': 'professional_blue',
                'logo_url': 'https://example.com/logo.png'
            }

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.get_branding()

            assert result is not None
            assert result['preset_theme'] == 'professional_blue'

    def test_create_branding(self, mock_config):
        """create_branding should create new branding record."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [{
                'tenant_id': 'test_tenant',
                'preset_theme': 'modern_dark'
            }]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.create_branding(preset_theme='modern_dark')

            assert result is not None
            assert result['preset_theme'] == 'modern_dark'

    def test_delete_branding(self, mock_config):
        """delete_branding should remove branding record."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            chain = create_chainable_mock()
            chain.execute.return_value = MagicMock()
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.delete_branding()

            assert result is True

    def test_update_branding(self, mock_config):
        """update_branding should update existing branding."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_get_result = MagicMock()
            mock_get_result.data = {'tenant_id': 'test_tenant', 'preset_theme': 'old'}

            mock_update_result = MagicMock()
            mock_update_result.data = [{'preset_theme': 'new_theme'}]

            chain = create_chainable_mock()

            call_count = [0]
            def side_effect():
                call_count[0] += 1
                if call_count[0] == 1:
                    return mock_get_result
                return mock_update_result

            chain.execute.side_effect = side_effect
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.update_branding(preset_theme='new_theme')

            assert result is not None


# ==================== Organization Users Tests ====================

class TestOrganizationUsers:
    """Test organization user management."""

    def test_get_organization_users(self, mock_config):
        """get_organization_users should return user list."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [
                {'id': 'user_1', 'email': 'admin@example.com', 'role': 'admin'},
                {'id': 'user_2', 'email': 'user@example.com', 'role': 'user'}
            ]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.get_organization_users()

            assert len(result) == 2

    def test_create_organization_user(self, mock_config):
        """create_organization_user should create user record."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [{
                'id': 'user_123',
                'auth_user_id': 'auth_123',
                'email': 'new@example.com',
                'role': 'user'
            }]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.create_organization_user(
                auth_user_id='auth_123',
                email='new@example.com',
                name='New User',
                role='user'
            )

            assert result is not None
            assert result['email'] == 'new@example.com'

    def test_deactivate_user(self, mock_config):
        """deactivate_user should set is_active to False."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [{'id': 'user_123', 'is_active': False}]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.deactivate_user('user_123')

            assert result is True

    def test_get_user_by_id(self, mock_config):
        """get_user_by_id should retrieve specific user."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = {
                'id': 'user_123',
                'email': 'user@example.com',
                'name': 'Test User'
            }

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.get_user_by_id('user_123')

            assert result is not None
            assert result['id'] == 'user_123'


# ==================== Helpdesk Session Tests ====================

class TestHelpdeskSessions:
    """Test helpdesk session operations."""

    def test_create_helpdesk_session(self, mock_config):
        """create_helpdesk_session should create new session."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [{
                'session_id': 'session_123',
                'employee_email': 'employee@example.com',
                'status': 'active'
            }]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.create_helpdesk_session(
                employee_email='employee@example.com',
                employee_name='Employee'
            )

            assert result is not None
            assert result['status'] == 'active'

    def test_add_helpdesk_message(self, mock_config):
        """add_helpdesk_message should append message to session."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_get_result = MagicMock()
            mock_get_result.data = {'messages': [{'role': 'user', 'content': 'Hello'}]}

            mock_update_result = MagicMock()

            chain = create_chainable_mock()

            call_count = [0]
            def side_effect():
                call_count[0] += 1
                if call_count[0] == 1:
                    return mock_get_result
                return mock_update_result

            chain.execute.side_effect = side_effect
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.add_helpdesk_message(
                session_id='session_123',
                role='assistant',
                content='How can I help?'
            )

            assert result is True


# ==================== Invitation Tests ====================

class TestInvitations:
    """Test user invitation operations."""

    def test_create_invitation(self, mock_config):
        """create_invitation should create new invitation."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            # First check existing user - not found
            mock_user_result = MagicMock()
            mock_user_result.data = []

            # Then check existing invite - not found
            mock_invite_check = MagicMock()
            mock_invite_check.data = []

            # Then create
            mock_create_result = MagicMock()
            mock_create_result.data = [{
                'id': 'inv_123',
                'email': 'invite@example.com',
                'token': 'abc123'
            }]

            chain = create_chainable_mock()

            call_count = [0]
            def side_effect():
                call_count[0] += 1
                if call_count[0] == 1:
                    raise Exception("No rows")  # User not found
                if call_count[0] == 2:
                    return mock_invite_check  # No existing invite
                return mock_create_result

            chain.execute.side_effect = side_effect
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.create_invitation(
                email='invite@example.com',
                name='Invitee',
                role='user'
            )

            assert result is not None

    def test_get_invitations(self, mock_config):
        """get_invitations should return invitation list."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [
                {'id': 'inv_1', 'email': 'a@example.com'},
                {'id': 'inv_2', 'email': 'b@example.com'}
            ]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.get_invitations()

            assert len(result) == 2

    def test_cancel_invitation(self, mock_config):
        """cancel_invitation should delete invitation."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            chain = create_chainable_mock()
            chain.execute.return_value = MagicMock()
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.cancel_invitation('inv_123')

            assert result is True


# ==================== Error Handling Tests ====================

class TestErrorHandling:
    """Test error handling across operations."""

    def test_operation_handles_exception(self, mock_config):
        """Operations should handle exceptions gracefully."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            chain = create_chainable_mock()
            chain.execute.side_effect = Exception("Database error")
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.get_tickets()

            # Should return empty list, not crash
            assert result == []

    def test_update_handles_exception(self, mock_config):
        """Update operations should handle exceptions."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            chain = create_chainable_mock()
            chain.execute.side_effect = Exception("Update failed")
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.update_ticket(
                ticket_id='TKT-123',
                status='closed'
            )

            # Should return False, not crash
            assert result is False

    def test_create_handles_empty_result(self, mock_config):
        """Create operations should handle empty results."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = None  # No data returned

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.create_ticket(
                customer_name='Test',
                customer_email='test@example.com',
                subject='Test',
                message='Test'
            )

            # Should return None for empty result
            assert result is None

    def test_list_invoices_handles_exception(self, mock_config):
        """list_invoices should handle exceptions gracefully."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            chain = create_chainable_mock()
            chain.execute.side_effect = Exception("Query failed")
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.list_invoices()

            # Should return empty list on error
            assert result == []


# ==================== Template Settings Tests ====================

class TestTemplateSettings:
    """Test template settings operations."""

    def test_get_template_settings(self, mock_config):
        """get_template_settings should retrieve template config."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = {
                'tenant_id': 'test_tenant',
                'quote_settings': {'header_text': 'Quote'},
                'invoice_settings': {'footer_text': 'Thank you'}
            }

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.get_template_settings()

            assert result is not None
            assert 'quote' in result
            assert 'invoice' in result

    def test_update_template_settings(self, mock_config):
        """update_template_settings should update template config."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_insert_result = MagicMock()
            mock_insert_result.data = [{'quote_settings': {'header': 'New'}}]

            chain = create_chainable_mock()

            call_count = [0]
            def side_effect():
                call_count[0] += 1
                if call_count[0] == 1:
                    raise Exception("No rows")
                return mock_insert_result

            chain.execute.side_effect = side_effect
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.update_template_settings({
                'quote': {'header': 'New'},
                'invoice': {}
            })

            # Should return settings even if insert doesn't return data
            assert result is not None


# ==================== NEW TESTS: Initialization Extended ====================

class TestSupabaseToolInitExtended:
    """Extended initialization tests for SupabaseTool."""

    def test_init_uses_service_key_over_anon_key(self, mock_config):
        """Should prefer service_key over anon_key when both available."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_get_client.return_value = MagicMock()

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            mock_get_client.assert_called_once_with(
                "https://test.supabase.co",
                "test-service-key",
                "test_tenant"
            )

    def test_init_falls_back_to_anon_key(self, mock_config):
        """Should use anon_key when service_key is None."""
        mock_config.supabase_service_key = None

        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_get_client.return_value = MagicMock()

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            mock_get_client.assert_called_once_with(
                "https://test.supabase.co",
                "test-anon-key",
                "test_tenant"
            )

    def test_init_creates_thread_pool_executor(self, mock_config):
        """Should create a ThreadPoolExecutor for timeout-protected queries."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_get_client.return_value = MagicMock()

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            assert tool._executor is not None
            assert tool._default_timeout == 10

    def test_init_all_table_constants(self, mock_config):
        """Should have all expected table name constants."""
        from src.tools.supabase_tool import SupabaseTool

        assert SupabaseTool.TABLE_CALL_QUEUE == "outbound_call_queue"
        assert SupabaseTool.TABLE_CALL_RECORDS == "call_records"
        assert SupabaseTool.TABLE_TICKETS == "inbound_tickets"
        assert SupabaseTool.TABLE_INVOICES == "invoices"
        assert SupabaseTool.TABLE_INVOICE_TRAVELERS == "invoice_travelers"
        assert SupabaseTool.TABLE_HELPDESK_SESSIONS == "helpdesk_sessions"
        assert SupabaseTool.TABLE_CLIENTS == "clients"
        assert SupabaseTool.TABLE_ACTIVITIES == "activities"
        assert SupabaseTool.TABLE_QUOTES == "quotes"


# ==================== NEW TESTS: execute_with_timeout ====================

class TestExecuteWithTimeout:
    """Tests for execute_with_timeout method."""

    def test_execute_with_timeout_success(self, mock_config):
        """Should return result on successful query within timeout."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_get_client.return_value = MagicMock()

            with patch('src.tools.supabase_tool.supabase_circuit') as mock_circuit:
                mock_circuit.can_execute.return_value = True

                from src.tools.supabase_tool import SupabaseTool
                tool = SupabaseTool(mock_config)

                result = tool.execute_with_timeout(
                    lambda: {"data": [1, 2, 3]},
                    timeout=5,
                    operation="test query"
                )

                assert result == {"data": [1, 2, 3]}
                mock_circuit.record_success.assert_called_once()

    def test_execute_with_timeout_circuit_open(self, mock_config):
        """Should raise ConnectionError when circuit breaker is open."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_get_client.return_value = MagicMock()

            with patch('src.tools.supabase_tool.supabase_circuit') as mock_circuit:
                mock_circuit.can_execute.return_value = False

                from src.tools.supabase_tool import SupabaseTool
                tool = SupabaseTool(mock_config)

                with pytest.raises(ConnectionError, match="circuit breaker OPEN"):
                    tool.execute_with_timeout(
                        lambda: None,
                        operation="blocked query"
                    )

    def test_execute_with_timeout_query_timeout(self, mock_config):
        """Should raise TimeoutError when query exceeds timeout."""
        import time as time_mod

        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_get_client.return_value = MagicMock()

            with patch('src.tools.supabase_tool.supabase_circuit') as mock_circuit:
                mock_circuit.can_execute.return_value = True

                from src.tools.supabase_tool import SupabaseTool
                tool = SupabaseTool(mock_config)

                def slow_query():
                    time_mod.sleep(5)
                    return "never"

                with pytest.raises(TimeoutError, match="timed out"):
                    tool.execute_with_timeout(
                        slow_query,
                        timeout=0.1,
                        operation="slow query"
                    )

                mock_circuit.record_failure.assert_called_once()

    def test_execute_with_timeout_query_exception(self, mock_config):
        """Should re-raise exception and record failure on circuit breaker."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_get_client.return_value = MagicMock()

            with patch('src.tools.supabase_tool.supabase_circuit') as mock_circuit:
                mock_circuit.can_execute.return_value = True

                from src.tools.supabase_tool import SupabaseTool
                tool = SupabaseTool(mock_config)

                def failing_query():
                    raise ValueError("DB connection lost")

                with pytest.raises(ValueError, match="DB connection lost"):
                    tool.execute_with_timeout(
                        failing_query,
                        operation="failing query"
                    )

                mock_circuit.record_failure.assert_called_once()

    def test_execute_with_timeout_uses_default_timeout(self, mock_config):
        """Should use default timeout when none specified."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_get_client.return_value = MagicMock()

            with patch('src.tools.supabase_tool.supabase_circuit') as mock_circuit:
                mock_circuit.can_execute.return_value = True

                from src.tools.supabase_tool import SupabaseTool
                tool = SupabaseTool(mock_config)

                # Default is 10 seconds - query should succeed well within that
                result = tool.execute_with_timeout(
                    lambda: "fast result",
                    operation="fast query"
                )

                assert result == "fast result"


# ==================== NEW TESTS: query_with_timeout ====================

class TestQueryWithTimeout:
    """Tests for query_with_timeout convenience method."""

    def test_query_with_timeout_basic(self, mock_config):
        """Should query table with tenant filter and return data."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            with patch('src.tools.supabase_tool.supabase_circuit') as mock_circuit:
                mock_circuit.can_execute.return_value = True

                mock_result = MagicMock()
                mock_result.data = [{"id": 1}, {"id": 2}]

                chain = create_chainable_mock()
                chain.execute.return_value = mock_result
                mock_client.table.return_value = chain

                from src.tools.supabase_tool import SupabaseTool
                tool = SupabaseTool(mock_config)

                result = tool.query_with_timeout("quotes")

                assert len(result) == 2
                mock_client.table.assert_called_with("quotes")

    def test_query_with_timeout_with_filters(self, mock_config):
        """Should apply additional filters to query."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            with patch('src.tools.supabase_tool.supabase_circuit') as mock_circuit:
                mock_circuit.can_execute.return_value = True

                mock_result = MagicMock()
                mock_result.data = [{"id": 1, "status": "active"}]

                chain = create_chainable_mock()
                chain.execute.return_value = mock_result
                mock_client.table.return_value = chain

                from src.tools.supabase_tool import SupabaseTool
                tool = SupabaseTool(mock_config)

                result = tool.query_with_timeout(
                    "quotes",
                    filters={"status": "active", "destination": "Paris"}
                )

                assert len(result) == 1

    def test_query_with_timeout_empty_result(self, mock_config):
        """Should return empty list when result.data is None."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            with patch('src.tools.supabase_tool.supabase_circuit') as mock_circuit:
                mock_circuit.can_execute.return_value = True

                mock_result = MagicMock()
                mock_result.data = None

                chain = create_chainable_mock()
                chain.execute.return_value = mock_result
                mock_client.table.return_value = chain

                from src.tools.supabase_tool import SupabaseTool
                tool = SupabaseTool(mock_config)

                result = tool.query_with_timeout("quotes")

                assert result == []


# ==================== NEW TESTS: Call Queue Extended ====================

class TestCallQueueExtended:
    """Extended call queue tests."""

    def test_queue_outbound_call_no_client_returns_none(self, mock_config):
        """Should return None when Supabase client is not available."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_get_client.return_value = None

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.queue_outbound_call(
                client_name="Test",
                client_email="test@example.com",
                phone_number="+1234567890",
                quote_details={}
            )

            assert result is None

    def test_queue_outbound_call_includes_consultant_fields(self, mock_config):
        """Should include consultant_id and consultant_email in record."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [{"id": "q1"}]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            tool.queue_outbound_call(
                client_name="Test",
                client_email="test@test.com",
                phone_number="+27123456",
                quote_details={"dest": "Cape Town"},
                consultant_id="c-1",
                consultant_email="consultant@test.com"
            )

            call_args = chain.insert.call_args[0][0]
            assert call_args["consultant_id"] == "c-1"
            assert call_args["consultant_email"] == "consultant@test.com"

    def test_queue_outbound_call_exception(self, mock_config):
        """Should return None on exception."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            chain = create_chainable_mock()
            chain.execute.side_effect = Exception("Insert failed")
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.queue_outbound_call(
                client_name="Test",
                client_email="test@test.com",
                phone_number="+1",
                quote_details={}
            )

            assert result is None

    def test_get_pending_calls_no_client(self, mock_config):
        """Should return empty list when client is None."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_get_client.return_value = None

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.get_pending_calls()

            assert result == []

    def test_update_call_status_no_client(self, mock_config):
        """Should return False when client is None."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_get_client.return_value = None

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.update_call_status("q1", "completed")

            assert result is False

    def test_save_call_record_no_client(self, mock_config):
        """Should return None when client is None."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_get_client.return_value = None

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.save_call_record(
                call_id="c1", phone_number="+1", transcript="hi",
                outcome="success", duration_seconds=10
            )

            assert result is None


# ==================== NEW TESTS: Invoice Extended ====================

class TestInvoiceExtended:
    """Extended invoice operation tests."""

    def test_create_invoice_no_client(self, mock_config):
        """Should return None when no Supabase client."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_get_client.return_value = None

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.create_invoice(
                customer_name="Test",
                customer_email="t@t.com",
                items=[],
                total_amount=0
            )

            assert result is None

    def test_create_invoice_generates_invoice_id(self, mock_config):
        """Should generate an invoice ID with INV- prefix."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [{"invoice_id": "INV-20260205-ABC123"}]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            tool.create_invoice(
                customer_name="Test",
                customer_email="t@t.com",
                items=[{"desc": "item"}],
                total_amount=100
            )

            call_args = chain.insert.call_args[0][0]
            assert call_args["invoice_id"].startswith("INV-")

    def test_create_invoice_default_due_date(self, mock_config):
        """Should set due_date to 7 days from now if not provided."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [{"invoice_id": "INV-1"}]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            tool.create_invoice(
                customer_name="Test",
                customer_email="t@t.com",
                items=[],
                total_amount=500
            )

            call_args = chain.insert.call_args[0][0]
            assert "due_date" in call_args
            # Should be an ISO format string
            assert "T" in call_args["due_date"]

    def test_create_invoice_raises_on_exception(self, mock_config):
        """create_invoice should re-raise exception (unlike other methods)."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            chain = create_chainable_mock()
            chain.execute.side_effect = Exception("Constraint violation")
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            with pytest.raises(Exception, match="Constraint violation"):
                tool.create_invoice(
                    customer_name="Test",
                    customer_email="t@t.com",
                    items=[],
                    total_amount=100
                )

    def test_update_invoice_status_no_client(self, mock_config):
        """Should return False when client is None."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_get_client.return_value = None

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.update_invoice_status("INV-1", "paid")

            assert result is False

    def test_update_invoice_status_with_payment_reference(self, mock_config):
        """Should include payment_reference in update data."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            chain = create_chainable_mock()
            chain.execute.return_value = MagicMock()
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            tool.update_invoice_status(
                "INV-1", "paid",
                payment_reference="PAY-REF-123"
            )

            call_args = chain.update.call_args[0][0]
            assert call_args["payment_reference"] == "PAY-REF-123"

    def test_list_invoices_enriches_destination_from_items(self, mock_config):
        """list_invoices should try to extract destination from items."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [{
                'invoice_id': 'INV-1',
                'items': [{'destination': 'Cape Town', 'amount': 1000}],
                'total_amount': 1000
            }]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.list_invoices()

            assert len(result) == 1
            assert result[0].get('destination') == 'Cape Town'


# ==================== NEW TESTS: Branding Extended ====================

class TestBrandingExtended:
    """Extended branding operation tests."""

    def test_create_branding_with_colors(self, mock_config):
        """Should map color keys to color_ prefixed DB columns."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [{"tenant_id": "test_tenant"}]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            tool.create_branding(
                colors={"primary": "#FF0000", "secondary": "#00FF00"}
            )

            call_args = chain.insert.call_args[0][0]
            assert call_args["color_primary"] == "#FF0000"
            assert call_args["color_secondary"] == "#00FF00"

    def test_create_branding_with_fonts(self, mock_config):
        """Should map font keys to font_family_ DB columns."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [{"tenant_id": "test_tenant"}]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            tool.create_branding(
                fonts={"heading": "Inter", "body": "Roboto"}
            )

            call_args = chain.insert.call_args[0][0]
            assert call_args["font_family_heading"] == "Inter"
            assert call_args["font_family_body"] == "Roboto"

    def test_get_branding_no_client(self, mock_config):
        """Should return None when client is None."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_get_client.return_value = None

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.get_branding()

            assert result is None

    def test_delete_branding_no_client(self, mock_config):
        """Should return False when client is None."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_get_client.return_value = None

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.delete_branding()

            assert result is False

    def test_delete_branding_exception(self, mock_config):
        """Should return False on exception."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            chain = create_chainable_mock()
            chain.execute.side_effect = Exception("Delete failed")
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.delete_branding()

            assert result is False

    def test_update_branding_creates_when_none_exists(self, mock_config):
        """update_branding should create new record when none exists."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            # get_branding returns None (no existing), create_branding succeeds
            mock_create_result = MagicMock()
            mock_create_result.data = [{"preset_theme": "sunset", "tenant_id": "test_tenant"}]

            chain = create_chainable_mock()

            call_count = [0]
            def side_effect():
                call_count[0] += 1
                if call_count[0] == 1:
                    raise Exception("No rows")  # get_branding fails
                return mock_create_result

            chain.execute.side_effect = side_effect
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.update_branding(preset_theme="sunset")

            assert result is not None


# ==================== NEW TESTS: Organization Users Extended ====================

class TestOrganizationUsersExtended:
    """Extended organization user management tests."""

    def test_get_organization_users_include_inactive(self, mock_config):
        """Should include inactive users when flag is set."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [
                {"id": "u1", "is_active": True},
                {"id": "u2", "is_active": False}
            ]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.get_organization_users(include_inactive=True)

            assert len(result) == 2

    def test_get_organization_users_exception(self, mock_config):
        """Should return empty list on exception."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            chain = create_chainable_mock()
            chain.execute.side_effect = Exception("DB error")
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.get_organization_users()

            assert result == []

    def test_update_organization_user_filters_allowed_fields(self, mock_config):
        """Should only update allowed fields (name, role, is_active, phone)."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [{"id": "u1", "name": "New Name"}]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.update_organization_user("u1", {
                "name": "New Name",
                "role": "admin",
                "email": "hacked@evil.com",  # Should be filtered out
                "tenant_id": "other-tenant"   # Should be filtered out
            })

            call_args = chain.update.call_args[0][0]
            assert "name" in call_args
            assert "role" in call_args
            assert "email" not in call_args
            assert "tenant_id" not in call_args

    def test_update_organization_user_empty_updates(self, mock_config):
        """Should return None when no allowed fields are provided."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.update_organization_user("u1", {
                "email": "not-allowed@test.com"
            })

            assert result is None

    def test_get_user_by_email_returns_first_match(self, mock_config):
        """Should return first match from result data."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = [
                {"id": "u1", "email": "test@test.com"},
                {"id": "u2", "email": "test@test.com"}
            ]

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.get_user_by_email("test@test.com")

            assert result["id"] == "u1"

    def test_get_user_by_email_empty_result(self, mock_config):
        """Should return None when no users found."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = []

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.get_user_by_email("noone@test.com")

            assert result is None


# ==================== NEW TESTS: Helpdesk Extended ====================

class TestHelpdeskExtended:
    """Extended helpdesk session tests."""

    def test_create_helpdesk_session_no_client(self, mock_config):
        """Should return None when client is None."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_get_client.return_value = None

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.create_helpdesk_session("e@e.com", "Employee")

            assert result is None

    def test_create_helpdesk_session_exception(self, mock_config):
        """Should return None on exception."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            chain = create_chainable_mock()
            chain.execute.side_effect = Exception("Insert error")
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.create_helpdesk_session("e@e.com", "Employee")

            assert result is None

    def test_add_helpdesk_message_no_client(self, mock_config):
        """Should return False when client is None."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_get_client.return_value = None

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.add_helpdesk_message("s1", "user", "hello")

            assert result is False

    def test_add_helpdesk_message_session_not_found(self, mock_config):
        """Should return False when session does not exist."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = None

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.add_helpdesk_message("nonexistent", "user", "hello")

            assert result is False


# ==================== NEW TESTS: Invitation Extended ====================

class TestInvitationExtended:
    """Extended invitation operation tests."""

    def test_get_invitation_by_token(self, mock_config):
        """Should retrieve invitation by token."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_result = MagicMock()
            mock_result.data = {
                "id": "inv-1",
                "token": "abc123",
                "email": "invite@test.com"
            }

            chain = create_chainable_mock()
            chain.execute.return_value = mock_result
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.get_invitation_by_token("abc123")

            assert result is not None
            assert result["token"] == "abc123"

    def test_get_invitation_by_token_not_found(self, mock_config):
        """Should return None when token not found."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            chain = create_chainable_mock()
            chain.execute.side_effect = Exception("No rows")
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.get_invitation_by_token("invalid-token")

            assert result is None

    def test_accept_invitation_success(self, mock_config):
        """Should mark invitation as accepted."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            chain = create_chainable_mock()
            chain.execute.return_value = MagicMock()
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.accept_invitation("token-123", "auth-user-456")

            assert result is True

    def test_accept_invitation_exception(self, mock_config):
        """Should return False on exception."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            chain = create_chainable_mock()
            chain.execute.side_effect = Exception("Update error")
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.accept_invitation("token-bad", "auth-user-456")

            assert result is False

    def test_cancel_invitation_exception(self, mock_config):
        """Should return False on exception."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            chain = create_chainable_mock()
            chain.execute.side_effect = Exception("Delete failed")
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.cancel_invitation("inv-bad")

            assert result is False


# ==================== NEW TESTS: Client Caching ====================

class TestSupabaseClientCaching:
    """Tests for the Supabase client caching mechanism."""

    def test_get_cached_client_returns_same_instance(self):
        """Should return cached instance for same parameters."""
        from src.tools.supabase_tool import get_cached_supabase_client, _supabase_client_cache
        _supabase_client_cache.clear()

        with patch('src.tools.supabase_tool.create_client') as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            c1 = get_cached_supabase_client("https://url.co", "key", "tenant-a")
            c2 = get_cached_supabase_client("https://url.co", "key", "tenant-a")

            assert c1 is c2
            mock_create.assert_called_once()

        _supabase_client_cache.clear()

    def test_get_cached_client_different_tenants(self):
        """Should create separate clients for different tenants."""
        from src.tools.supabase_tool import get_cached_supabase_client, _supabase_client_cache
        _supabase_client_cache.clear()

        with patch('src.tools.supabase_tool.create_client') as mock_create:
            mock_create.side_effect = [MagicMock(), MagicMock()]

            c1 = get_cached_supabase_client("https://url.co", "key", "tenant-a")
            c2 = get_cached_supabase_client("https://url.co", "key", "tenant-b")

            assert c1 is not c2
            assert mock_create.call_count == 2

        _supabase_client_cache.clear()

    def test_get_cached_client_creation_failure(self):
        """Should return None when create_client fails."""
        from src.tools.supabase_tool import get_cached_supabase_client, _supabase_client_cache
        _supabase_client_cache.clear()

        with patch('src.tools.supabase_tool.create_client') as mock_create:
            mock_create.side_effect = Exception("Connection refused")

            result = get_cached_supabase_client("https://url.co", "key", "tenant-fail")

            assert result is None

        _supabase_client_cache.clear()


# ==================== NEW TESTS: Storage/Logo Upload ====================

class TestLogoUpload:
    """Tests for logo upload to Supabase Storage."""

    def test_upload_logo_no_client(self, mock_config):
        """Should raise Exception when client is None."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_get_client.return_value = None

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            with pytest.raises(Exception, match="not initialized"):
                tool.upload_logo_to_storage(b"image-data", "logo.png")

    def test_upload_logo_success(self, mock_config):
        """Should upload logo and return public URL."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_bucket = MagicMock()
            mock_bucket.upload.return_value = MagicMock()
            mock_bucket.get_public_url.return_value = "https://storage.supabase.co/branding/test_tenant/primary.png"
            mock_client.storage.from_.return_value = mock_bucket

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.upload_logo_to_storage(b"png-data", "logo.png", "primary")

            assert result == "https://storage.supabase.co/branding/test_tenant/primary.png"

    def test_upload_logo_bucket_not_found(self, mock_config):
        """Should raise descriptive error when bucket not found."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_bucket = MagicMock()
            mock_bucket.remove.side_effect = Exception("pass")
            mock_bucket.upload.side_effect = Exception("Bucket not found")
            mock_client.storage.from_.return_value = mock_bucket

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            with pytest.raises(Exception, match="tenant-assets"):
                tool.upload_logo_to_storage(b"data", "logo.png")

    def test_upload_logo_permission_denied(self, mock_config):
        """Should raise descriptive error on 403/permission error."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_bucket = MagicMock()
            mock_bucket.remove.return_value = None
            mock_bucket.upload.side_effect = Exception("403 permission denied by policy")
            mock_client.storage.from_.return_value = mock_bucket

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            with pytest.raises(Exception, match="permission denied"):
                tool.upload_logo_to_storage(b"data", "logo.png")


# ==================== NEW TESTS: Template Settings Extended ====================

class TestTemplateSettingsExtended:
    """Extended template settings tests."""

    def test_get_template_settings_no_client(self, mock_config):
        """Should return None when client is None."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_get_client.return_value = None

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.get_template_settings()

            assert result is None

    def test_update_template_settings_no_client(self, mock_config):
        """Should return None when client is None."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_get_client.return_value = None

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            result = tool.update_template_settings({"quote": {}, "invoice": {}})

            assert result is None

    def test_update_template_settings_returns_input_on_error(self, mock_config):
        """Should return input settings for graceful degradation on error."""
        with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            chain = create_chainable_mock()
            chain.execute.side_effect = Exception("DB error")
            mock_client.table.return_value = chain

            from src.tools.supabase_tool import SupabaseTool
            tool = SupabaseTool(mock_config)

            input_settings = {"quote": {"header": "My Quote"}, "invoice": {"footer": "Thanks"}}
            result = tool.update_template_settings(input_settings)

            # Should return input even on error
            assert result == input_settings


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
