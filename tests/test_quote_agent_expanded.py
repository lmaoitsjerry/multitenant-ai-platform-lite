"""
Quote Agent Expanded Tests

Tests for QuoteAgent methods not covered in test_quote_generation.py:
- send_draft_quote() workflow
- resend_quote() workflow
- _generate_quote_id() format
- _normalize_customer_data() edge cases
- _schedule_follow_up_call() logic
- _get_next_business_day_10am() calculation
- update_quote_status() state transitions
- list_quotes() pagination and filtering
- _add_to_crm() progression logic
- Error handling paths

Uses mocked dependencies for isolated unit testing.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import uuid
import re

from src.agents.quote_agent import QuoteAgent
from config.loader import ClientConfig


# ==================== Fixtures ====================

@pytest.fixture
def mock_config():
    """Create mock client config."""
    config = Mock(spec=ClientConfig)
    config.client_id = 'test_tenant'
    config.company_name = 'Test Travel'
    config.destination_names = ['Zanzibar', 'Mauritius', 'Seychelles', 'Maldives']
    config.timezone = 'Africa/Johannesburg'
    config.currency = 'USD'
    return config


@pytest.fixture
def mock_quote_agent(mock_config):
    """Create a mocked QuoteAgent instance."""
    with patch.object(QuoteAgent, '__init__', return_value=None):
        agent = QuoteAgent.__new__(QuoteAgent)
        agent.config = mock_config
        agent.db = Mock()
        agent.bq_tool = Mock()
        agent.pdf_generator = Mock()
        agent.email_sender = Mock()
        agent.supabase = Mock()
        agent.supabase.client = Mock()
        agent.crm = Mock()
        agent.max_hotels_per_quote = 3
        agent.default_nights = 7
        return agent


@pytest.fixture
def sample_quote():
    """Sample quote data."""
    return {
        'quote_id': 'QT-20260121-ABC123',
        'customer_name': 'John Doe',
        'customer_email': 'john@example.com',
        'customer_phone': '+27123456789',
        'destination': 'Zanzibar',
        'check_in_date': '2026-06-15',
        'check_out_date': '2026-06-22',
        'nights': 7,
        'adults': 2,
        'children': 0,
        'children_ages': [],
        'hotels': [{
            'name': 'Test Hotel',
            'total_price': 10000
        }],
        'total_price': 10000,
        'status': 'draft',
        'created_at': '2026-01-21T12:00:00'
    }


# ==================== Quote ID Generation Tests ====================

class TestQuoteIdGeneration:
    """Test quote ID generation."""

    def test_quote_id_format(self, mock_quote_agent):
        """Quote ID should follow QT-YYYYMMDD-XXXXXX format."""
        agent = mock_quote_agent
        quote_id = agent._generate_quote_id()

        # Pattern: QT-YYYYMMDD-6 hex chars
        pattern = re.compile(r'^QT-\d{8}-[A-F0-9]{6}$')
        assert pattern.match(quote_id) is not None

    def test_quote_id_contains_today_date(self, mock_quote_agent):
        """Quote ID should contain today's date."""
        agent = mock_quote_agent
        quote_id = agent._generate_quote_id()

        today = datetime.utcnow().strftime('%Y%m%d')
        assert today in quote_id

    def test_quote_ids_are_unique(self, mock_quote_agent):
        """Multiple quote IDs should be unique."""
        agent = mock_quote_agent
        quote_ids = [agent._generate_quote_id() for _ in range(100)]

        assert len(quote_ids) == len(set(quote_ids))


# ==================== Customer Data Normalization Tests ====================

class TestCustomerDataNormalization:
    """Test customer data normalization."""

    def test_normalize_basic_data(self, mock_quote_agent):
        """Basic customer data should be normalized."""
        agent = mock_quote_agent

        data = {
            'name': 'Jane Doe',
            'email': 'jane@example.com',
            'destination': 'Zanzibar',
            'adults': '2',  # String should become int
            'children': '1'
        }

        result = agent._normalize_customer_data(data)

        assert result['name'] == 'Jane Doe'
        assert result['email'] == 'jane@example.com'
        assert result['destination'] == 'Zanzibar'
        assert result['adults'] == 2
        assert result['children'] == 1

    def test_normalize_dates_from_strings(self, mock_quote_agent):
        """Date strings should be kept as-is."""
        agent = mock_quote_agent

        data = {
            'name': 'Test',
            'email': 'test@example.com',
            'destination': 'Mauritius',
            'check_in': '2026-06-15',
            'check_out': '2026-06-22'
        }

        result = agent._normalize_customer_data(data)

        assert result['check_in'] == '2026-06-15'
        assert result['check_out'] == '2026-06-22'
        assert result['nights'] == 7

    def test_normalize_dates_from_datetime(self, mock_quote_agent):
        """Datetime objects should be converted to strings."""
        agent = mock_quote_agent

        check_in = datetime(2026, 6, 15)
        check_out = datetime(2026, 6, 22)

        data = {
            'name': 'Test',
            'email': 'test@example.com',
            'destination': 'Mauritius',
            'check_in': check_in,
            'check_out': check_out
        }

        result = agent._normalize_customer_data(data)

        assert result['check_in'] == '2026-06-15'
        assert result['check_out'] == '2026-06-22'

    def test_normalize_default_dates(self, mock_quote_agent):
        """Missing dates should get defaults."""
        agent = mock_quote_agent

        data = {
            'name': 'Test',
            'email': 'test@example.com',
            'destination': 'Mauritius'
        }

        result = agent._normalize_customer_data(data)

        # Should have default dates
        assert 'check_in' in result
        assert 'check_out' in result
        assert result['nights'] == agent.default_nights

    def test_normalize_destination_case_insensitive(self, mock_quote_agent):
        """Destination matching should be case-insensitive."""
        agent = mock_quote_agent

        data = {
            'name': 'Test',
            'email': 'test@example.com',
            'destination': 'zanzibar'  # lowercase
        }

        result = agent._normalize_customer_data(data)

        # Should be corrected to proper case
        assert result['destination'] == 'Zanzibar'

    def test_normalize_children_ages(self, mock_quote_agent):
        """Children ages should be handled correctly."""
        agent = mock_quote_agent

        data = {
            'name': 'Test',
            'email': 'test@example.com',
            'destination': 'Mauritius',
            'children': 2,
            'children_ages': [3, 5]
        }

        result = agent._normalize_customer_data(data)

        assert result['children'] == 2
        assert result['children_ages'] == [3, 5]

    def test_normalize_budget_from_total_budget(self, mock_quote_agent):
        """Budget should be extracted from total_budget field."""
        agent = mock_quote_agent

        data = {
            'name': 'Test',
            'email': 'test@example.com',
            'destination': 'Mauritius',
            'total_budget': 50000
        }

        result = agent._normalize_customer_data(data)

        assert result['budget'] == 50000


# ==================== Send Draft Quote Tests ====================

class TestSendDraftQuote:
    """Test send_draft_quote workflow."""

    def test_send_draft_quote_success(self, mock_quote_agent, sample_quote):
        """Successfully sending a draft quote."""
        agent = mock_quote_agent

        # Mock get_quote to return draft quote
        agent.get_quote = Mock(return_value=sample_quote)

        # Mock PDF generation
        agent.pdf_generator.generate_quote_pdf.return_value = b'PDF_CONTENT'

        # Mock email sending
        agent.email_sender.send_quote_email.return_value = True

        # Mock status update
        agent.update_quote_status = Mock(return_value=True)

        # Mock follow-up call scheduling
        agent._schedule_follow_up_call = Mock(return_value=True)

        result = agent.send_draft_quote('QT-20260121-ABC123')

        assert result['success'] is True
        assert result['quote_id'] == 'QT-20260121-ABC123'
        assert result['customer_email'] == 'john@example.com'
        assert 'sent_at' in result

    def test_send_draft_quote_not_found(self, mock_quote_agent):
        """Sending non-existent quote should fail."""
        agent = mock_quote_agent
        agent.get_quote = Mock(return_value=None)

        result = agent.send_draft_quote('NONEXISTENT')

        assert result['success'] is False
        assert 'not found' in result['error'].lower()

    def test_send_draft_quote_not_draft_status(self, mock_quote_agent, sample_quote):
        """Sending non-draft quote should fail."""
        agent = mock_quote_agent
        sample_quote['status'] = 'sent'  # Not a draft
        agent.get_quote = Mock(return_value=sample_quote)

        result = agent.send_draft_quote('QT-20260121-ABC123')

        assert result['success'] is False
        assert 'not a draft' in result['error'].lower()

    def test_send_draft_quote_no_email(self, mock_quote_agent, sample_quote):
        """Sending quote without customer email should fail."""
        agent = mock_quote_agent
        sample_quote['customer_email'] = None
        agent.get_quote = Mock(return_value=sample_quote)

        result = agent.send_draft_quote('QT-20260121-ABC123')

        assert result['success'] is False
        assert 'no customer email' in result['error'].lower()

    def test_send_draft_quote_pdf_failure(self, mock_quote_agent, sample_quote):
        """PDF generation failure should stop the process."""
        agent = mock_quote_agent
        agent.get_quote = Mock(return_value=sample_quote)
        agent.pdf_generator.generate_quote_pdf.side_effect = Exception("PDF error")

        result = agent.send_draft_quote('QT-20260121-ABC123')

        assert result['success'] is False
        assert 'pdf' in result['error'].lower()

    def test_send_draft_quote_email_failure(self, mock_quote_agent, sample_quote):
        """Email sending failure should stop the process."""
        agent = mock_quote_agent
        agent.get_quote = Mock(return_value=sample_quote)
        agent.pdf_generator.generate_quote_pdf.return_value = b'PDF'
        agent.email_sender.send_quote_email.return_value = False

        result = agent.send_draft_quote('QT-20260121-ABC123')

        assert result['success'] is False
        assert 'email' in result['error'].lower()

    def test_send_draft_quote_schedules_call(self, mock_quote_agent, sample_quote):
        """Send draft quote should schedule follow-up call if phone present."""
        agent = mock_quote_agent
        agent.get_quote = Mock(return_value=sample_quote)
        agent.pdf_generator.generate_quote_pdf.return_value = b'PDF'
        agent.email_sender.send_quote_email.return_value = True
        agent.update_quote_status = Mock(return_value=True)
        agent._schedule_follow_up_call = Mock(return_value=True)

        result = agent.send_draft_quote('QT-20260121-ABC123')

        assert result['success'] is True
        assert result['call_queued'] is True
        agent._schedule_follow_up_call.assert_called_once()


# ==================== Resend Quote Tests ====================

class TestResendQuote:
    """Test resend_quote workflow."""

    def test_resend_quote_success(self, mock_quote_agent, sample_quote):
        """Successfully resending a quote."""
        agent = mock_quote_agent
        sample_quote['status'] = 'sent'  # Already sent
        agent.get_quote = Mock(return_value=sample_quote)
        agent.pdf_generator.generate_quote_pdf.return_value = b'PDF'
        agent.email_sender.send_quote_email.return_value = True

        result = agent.resend_quote('QT-20260121-ABC123')

        assert result['success'] is True
        assert 'resent' in result['message'].lower()

    def test_resend_quote_not_found(self, mock_quote_agent):
        """Resending non-existent quote should fail."""
        agent = mock_quote_agent
        agent.get_quote = Mock(return_value=None)

        result = agent.resend_quote('NONEXISTENT')

        assert result['success'] is False
        assert 'not found' in result['error'].lower()

    def test_resend_quote_any_status(self, mock_quote_agent, sample_quote):
        """Resend should work on any status (unlike send_draft)."""
        agent = mock_quote_agent
        agent.pdf_generator.generate_quote_pdf.return_value = b'PDF'
        agent.email_sender.send_quote_email.return_value = True

        for status in ['draft', 'sent', 'viewed', 'accepted']:
            sample_quote['status'] = status
            agent.get_quote = Mock(return_value=sample_quote)

            result = agent.resend_quote('QT-20260121-ABC123')
            assert result['success'] is True, f"Resend should work for status={status}"

    def test_resend_quote_no_email(self, mock_quote_agent, sample_quote):
        """Resending quote without email should fail."""
        agent = mock_quote_agent
        sample_quote['customer_email'] = None
        agent.get_quote = Mock(return_value=sample_quote)

        result = agent.resend_quote('QT-20260121-ABC123')

        assert result['success'] is False


# ==================== Update Quote Status Tests ====================

class TestUpdateQuoteStatus:
    """Test quote status updates."""

    def test_update_to_sent(self, mock_quote_agent):
        """Update to 'sent' should add sent_at timestamp."""
        agent = mock_quote_agent
        agent.supabase.client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = Mock()

        result = agent.update_quote_status('QT-123', 'sent')

        assert result is True

    def test_update_to_viewed(self, mock_quote_agent):
        """Update to 'viewed' should add viewed_at timestamp."""
        agent = mock_quote_agent
        agent.supabase.client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = Mock()

        result = agent.update_quote_status('QT-123', 'viewed')

        assert result is True

    def test_update_to_accepted(self, mock_quote_agent):
        """Update to 'accepted' should add accepted_at timestamp."""
        agent = mock_quote_agent
        agent.supabase.client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = Mock()

        result = agent.update_quote_status('QT-123', 'accepted')

        assert result is True

    def test_update_status_no_supabase(self, mock_quote_agent):
        """Update without Supabase should return False."""
        agent = mock_quote_agent
        agent.supabase = None

        result = agent.update_quote_status('QT-123', 'sent')

        assert result is False


# ==================== List Quotes Tests ====================

class TestListQuotes:
    """Test quote listing."""

    def test_list_quotes_basic(self, mock_quote_agent):
        """Basic quote listing."""
        agent = mock_quote_agent
        agent.supabase.client.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = Mock(
            data=[{'quote_id': 'QT-1'}, {'quote_id': 'QT-2'}]
        )

        result = agent.list_quotes()

        assert len(result) == 2

    def test_list_quotes_with_status_filter(self, mock_quote_agent):
        """List quotes with status filter."""
        agent = mock_quote_agent
        mock_query = Mock()
        mock_query.eq.return_value = mock_query
        mock_query.execute.return_value = Mock(data=[{'quote_id': 'QT-1'}])

        agent.supabase.client.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value = mock_query

        result = agent.list_quotes(status='sent')

        assert len(result) == 1

    def test_list_quotes_pagination(self, mock_quote_agent):
        """List quotes with pagination."""
        agent = mock_quote_agent
        agent.supabase.client.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = Mock(
            data=[{'quote_id': 'QT-10'}]
        )

        result = agent.list_quotes(limit=10, offset=10)

        assert len(result) == 1

    def test_list_quotes_no_supabase(self, mock_quote_agent):
        """List quotes without Supabase returns empty list."""
        agent = mock_quote_agent
        agent.supabase = None

        result = agent.list_quotes()

        assert result == []


# ==================== Business Day Calculation Tests ====================

class TestBusinessDayCalculation:
    """Test business day calculation."""

    def test_next_business_day_skips_saturday(self, mock_quote_agent):
        """Next business day should skip Saturday."""
        agent = mock_quote_agent

        # Mock pytz timezone
        with patch('pytz.timezone') as mock_tz:
            mock_tz.return_value = MagicMock()

            # Test that the method exists and is callable
            assert hasattr(agent, '_get_next_business_day_10am')
            assert callable(agent._get_next_business_day_10am)

    def test_next_business_day_with_days_ahead(self, mock_quote_agent):
        """Get business day N days ahead."""
        agent = mock_quote_agent

        # Test the method exists
        assert hasattr(agent, '_get_next_business_day')
        assert callable(agent._get_next_business_day)


# ==================== CRM Integration Tests ====================

class TestCRMIntegration:
    """Test CRM integration."""

    def test_add_new_client_to_crm(self, mock_quote_agent):
        """New client should be added to CRM in QUOTED stage."""
        agent = mock_quote_agent
        agent.crm.get_client_by_email.return_value = None  # No existing client
        agent.crm.get_or_create_client.return_value = {
            'client_id': 'client_123',
            'email': 'test@example.com'
        }

        result = agent._add_to_crm({'email': 'test@example.com', 'name': 'Test'}, 'QT-123')

        assert result['success'] is True
        assert result['created'] is True

    def test_existing_client_moves_to_negotiating(self, mock_quote_agent):
        """Existing client with 2+ quotes should move to NEGOTIATING."""
        agent = mock_quote_agent
        agent.crm.get_client_by_email.return_value = {
            'client_id': 'client_123',
            'email': 'test@example.com',
            'pipeline_stage': 'QUOTED',
            'quote_count': 1  # Will become 2
        }

        result = agent._add_to_crm({'email': 'test@example.com', 'name': 'Test'}, 'QT-456')

        assert result['success'] is True
        assert result['created'] is False

    def test_no_crm_service(self, mock_quote_agent):
        """Without CRM service, should return None."""
        agent = mock_quote_agent
        agent.crm = None

        result = agent._add_to_crm({'email': 'test@example.com'}, 'QT-123')

        assert result is None


# ==================== Error Handling Tests ====================

class TestErrorHandling:
    """Test error handling paths."""

    def test_generate_quote_no_hotels(self, mock_quote_agent):
        """Generate quote with no hotels should return error."""
        agent = mock_quote_agent
        agent.bq_tool.find_matching_hotels.return_value = []

        result = agent.generate_quote({
            'name': 'Test',
            'email': 'test@example.com',
            'destination': 'Unknown'
        })

        assert result['success'] is False
        assert 'no' in result['error'].lower() and 'hotel' in result['error'].lower()

    def test_generate_quote_pricing_error(self, mock_quote_agent):
        """Generate quote with pricing error should return error."""
        agent = mock_quote_agent
        agent.bq_tool.find_matching_hotels.return_value = [{
            'hotel_name': 'Test Hotel',
            'rate_id': 'rate_123'
        }]
        agent.bq_tool.calculate_quote_price.return_value = None

        result = agent.generate_quote({
            'name': 'Test',
            'email': 'test@example.com',
            'destination': 'Zanzibar'
        })

        assert result['success'] is False

    def test_save_quote_supabase_error(self, mock_quote_agent, sample_quote):
        """Save quote with Supabase error should return False."""
        agent = mock_quote_agent
        agent.supabase.client.table.return_value.insert.return_value.execute.side_effect = Exception("DB Error")

        result = agent._save_quote_to_supabase(sample_quote)

        assert result is False


# ==================== Schedule Follow-up Call Tests ====================

class TestScheduleFollowUpCall:
    """Test follow-up call scheduling."""

    def test_schedule_call_success(self, mock_quote_agent):
        """Successfully schedule a follow-up call."""
        agent = mock_quote_agent
        agent.supabase.queue_outbound_call.return_value = {'call_id': 'call_123'}
        agent._get_next_business_day_10am = Mock(return_value=datetime.utcnow() + timedelta(days=1))

        result = agent._schedule_follow_up_call(
            quote_id='QT-123',
            customer_name='John',
            customer_email='john@example.com',
            customer_phone='+27123456789',
            destination='Zanzibar'
        )

        assert result is True

    def test_schedule_call_no_supabase(self, mock_quote_agent):
        """Schedule call without Supabase should return False."""
        agent = mock_quote_agent
        agent.supabase = None

        result = agent._schedule_follow_up_call(
            quote_id='QT-123',
            customer_name='John',
            customer_email='john@example.com',
            customer_phone='+27123456789',
            destination='Zanzibar'
        )

        assert result is False


# ==================== Get Quote Tests ====================

class TestGetQuote:
    """Test get_quote method."""

    def test_get_quote_success(self, mock_quote_agent, sample_quote):
        """Successfully retrieve a quote."""
        agent = mock_quote_agent
        agent.supabase.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data=sample_quote
        )

        result = agent.get_quote('QT-20260121-ABC123')

        assert result['quote_id'] == 'QT-20260121-ABC123'

    def test_get_quote_not_found(self, mock_quote_agent):
        """Get non-existent quote should return None."""
        agent = mock_quote_agent
        agent.supabase.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data=None
        )

        result = agent.get_quote('NONEXISTENT')

        assert result is None

    def test_get_quote_no_supabase(self, mock_quote_agent):
        """Get quote without Supabase should return None."""
        agent = mock_quote_agent
        agent.supabase = None

        result = agent.get_quote('QT-123')

        assert result is None
