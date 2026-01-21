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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
