"""
Tests for Quote Generation Pipeline

Verifies:
1. Parsed email data flows correctly to QuoteAgent
2. Draft quotes created with correct status
3. Hotels queried for destination
4. Quote saved to database
5. No email sent for draft quotes
6. Backward compatibility maintained
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.agents.quote_agent import QuoteAgent
from config.loader import ClientConfig


class TestQuoteGenerationPipeline:
    """Test email -> quote generation flow"""

    @pytest.fixture
    def mock_config(self):
        """Create mock client config"""
        config = Mock(spec=ClientConfig)
        config.client_id = 'test_tenant'
        config.destination_names = ['Zanzibar', 'Mauritius', 'Seychelles']
        config.timezone = 'Africa/Johannesburg'
        return config

    @pytest.fixture
    def parsed_email_data(self):
        """Sample parsed email data from LLMEmailParser"""
        return {
            'name': 'John Doe',
            'email': 'john@example.com',
            'destination': 'Zanzibar',
            'check_in': '2025-06-15',
            'check_out': '2025-06-22',
            'adults': 2,
            'children': 0,
            'children_ages': [],
            'budget': 50000,
            'is_travel_inquiry': True,
            'parse_method': 'llm'
        }

    @pytest.fixture
    def mock_quote_agent(self, mock_config):
        """Create a mocked QuoteAgent instance"""
        with patch.object(QuoteAgent, '__init__', return_value=None):
            agent = QuoteAgent.__new__(QuoteAgent)
            agent.config = mock_config
            agent.db = Mock()
            agent.bq_tool = Mock()
            agent.pdf_generator = Mock()
            agent.email_sender = Mock()
            agent.supabase = Mock()
            agent.supabase.client = Mock()
            agent.supabase.client.table.return_value.insert.return_value.execute.return_value = Mock(data=[{}])
            agent.crm = Mock()
            agent.max_hotels_per_quote = 3
            agent.default_nights = 7
            return agent

    def test_draft_quote_created_with_correct_status(self, mock_quote_agent, parsed_email_data):
        """Verify draft quotes have status='draft'"""
        agent = mock_quote_agent

        # Mock hotel finding
        agent.bq_tool.find_matching_hotels.return_value = [{
            'hotel_name': 'Test Hotel',
            'rate_id': 'rate_123',
            'hotel_rating': '4*',
            'room_type': 'Deluxe',
            'meal_plan': 'BB'
        }]

        # Mock pricing
        agent.bq_tool.calculate_quote_price.return_value = {
            'per_person_rates': {'adult_sharing': 5000},
            'totals': {'grand_total': 10000}
        }

        # Mock consultant
        agent.bq_tool.get_next_consultant_round_robin.return_value = {
            'consultant_id': 'consultant_1'
        }

        result = agent.generate_quote(
            customer_data=parsed_email_data,
            send_email=False,
            initial_status='draft'
        )

        assert result['success'] == True
        assert result['quote']['status'] == 'draft'
        assert result['email_sent'] == False

    def test_destination_passed_to_hotel_query(self, mock_quote_agent, parsed_email_data):
        """Verify destination from parsed email used in hotel query"""
        agent = mock_quote_agent

        agent.bq_tool.find_matching_hotels.return_value = []

        result = agent.generate_quote(
            customer_data=parsed_email_data,
            send_email=False,
            initial_status='draft'
        )

        # Verify destination was passed to hotel query
        call_args = agent.bq_tool.find_matching_hotels.call_args
        assert call_args[1]['destination'] == 'Zanzibar'

    def test_quote_contains_customer_details(self, mock_quote_agent, parsed_email_data):
        """Verify quote contains all customer details from parsed email"""
        agent = mock_quote_agent

        agent.bq_tool.find_matching_hotels.return_value = [{
            'hotel_name': 'Test Hotel',
            'rate_id': 'rate_123'
        }]
        agent.bq_tool.calculate_quote_price.return_value = {
            'per_person_rates': {'adult_sharing': 5000},
            'totals': {'grand_total': 10000}
        }
        agent.bq_tool.get_next_consultant_round_robin.return_value = None

        result = agent.generate_quote(
            customer_data=parsed_email_data,
            send_email=False,
            initial_status='draft'
        )

        quote = result['quote']
        assert quote['customer_name'] == 'John Doe'
        assert quote['customer_email'] == 'john@example.com'
        assert quote['destination'] == 'Zanzibar'
        assert quote['check_in_date'] == '2025-06-15'
        assert quote['check_out_date'] == '2025-06-22'
        assert quote['adults'] == 2
        assert quote['children'] == 0

    def test_no_email_sent_for_draft(self, mock_quote_agent, parsed_email_data):
        """Verify no email is sent when creating draft quote"""
        agent = mock_quote_agent

        agent.bq_tool.find_matching_hotels.return_value = [{
            'hotel_name': 'Test Hotel',
            'rate_id': 'rate_123'
        }]
        agent.bq_tool.calculate_quote_price.return_value = {
            'per_person_rates': {'adult_sharing': 5000},
            'totals': {'grand_total': 10000}
        }
        agent.bq_tool.get_next_consultant_round_robin.return_value = None

        result = agent.generate_quote(
            customer_data=parsed_email_data,
            send_email=True,  # Even with True, draft should not send
            initial_status='draft'
        )

        agent.email_sender.send_quote_email.assert_not_called()

    def test_quote_saved_to_supabase(self, mock_quote_agent, parsed_email_data):
        """Verify quote is saved to Supabase"""
        agent = mock_quote_agent

        agent.bq_tool.find_matching_hotels.return_value = [{
            'hotel_name': 'Test Hotel',
            'rate_id': 'rate_123'
        }]
        agent.bq_tool.calculate_quote_price.return_value = {
            'per_person_rates': {'adult_sharing': 5000},
            'totals': {'grand_total': 10000}
        }
        agent.bq_tool.get_next_consultant_round_robin.return_value = None

        result = agent.generate_quote(
            customer_data=parsed_email_data,
            send_email=False,
            initial_status='draft'
        )

        # Verify Supabase insert was called
        agent.supabase.client.table.assert_called_with('quotes')

    def test_no_follow_up_call_scheduled_for_draft(self, mock_quote_agent, parsed_email_data):
        """Verify no follow-up call is scheduled for draft quotes"""
        agent = mock_quote_agent

        # Add phone number to customer data
        parsed_email_data['phone'] = '+27123456789'

        agent.bq_tool.find_matching_hotels.return_value = [{
            'hotel_name': 'Test Hotel',
            'rate_id': 'rate_123'
        }]
        agent.bq_tool.calculate_quote_price.return_value = {
            'per_person_rates': {'adult_sharing': 5000},
            'totals': {'grand_total': 10000}
        }
        agent.bq_tool.get_next_consultant_round_robin.return_value = None

        result = agent.generate_quote(
            customer_data=parsed_email_data,
            send_email=True,
            initial_status='draft'
        )

        # Call should not be queued for drafts
        assert result['call_queued'] == False

    def test_consultant_still_assigned_for_draft(self, mock_quote_agent, parsed_email_data):
        """Verify consultant is still assigned for draft quotes"""
        agent = mock_quote_agent

        mock_consultant = {'consultant_id': 'consultant_1', 'name': 'Test Consultant'}
        agent.bq_tool.find_matching_hotels.return_value = [{
            'hotel_name': 'Test Hotel',
            'rate_id': 'rate_123'
        }]
        agent.bq_tool.calculate_quote_price.return_value = {
            'per_person_rates': {'adult_sharing': 5000},
            'totals': {'grand_total': 10000}
        }
        agent.bq_tool.get_next_consultant_round_robin.return_value = mock_consultant

        result = agent.generate_quote(
            customer_data=parsed_email_data,
            send_email=False,
            assign_consultant=True,
            initial_status='draft'
        )

        assert result['consultant'] == mock_consultant


class TestQuoteAgentBackwardCompatibility:
    """Ensure existing behavior is preserved"""

    @pytest.fixture
    def mock_config(self):
        config = Mock(spec=ClientConfig)
        config.client_id = 'test_tenant'
        config.destination_names = ['Zanzibar']
        config.timezone = 'UTC'
        return config

    @pytest.fixture
    def mock_quote_agent(self, mock_config):
        """Create a mocked QuoteAgent instance"""
        with patch.object(QuoteAgent, '__init__', return_value=None):
            agent = QuoteAgent.__new__(QuoteAgent)
            agent.config = mock_config
            agent.db = Mock()
            agent.bq_tool = Mock()
            agent.pdf_generator = Mock()
            agent.email_sender = Mock()
            agent.supabase = Mock()
            agent.crm = Mock()
            agent.max_hotels_per_quote = 3
            agent.default_nights = 7
            return agent

    def test_default_status_is_generated(self, mock_quote_agent):
        """Verify default behavior (no initial_status) still works"""
        agent = mock_quote_agent

        agent.bq_tool.find_matching_hotels.return_value = []

        result = agent.generate_quote(
            customer_data={'email': 'test@test.com', 'destination': 'Zanzibar'},
            send_email=False
            # No initial_status = should default to 'generated'
        )

        # With no hotels found, returns no_availability
        assert result['status'] == 'no_availability'

    def test_generated_status_sends_email(self, mock_quote_agent):
        """Verify non-draft quotes still send emails when requested"""
        agent = mock_quote_agent

        agent.bq_tool.find_matching_hotels.return_value = [{
            'hotel_name': 'Test Hotel',
            'rate_id': 'rate_123'
        }]
        agent.bq_tool.calculate_quote_price.return_value = {
            'per_person_rates': {'adult_sharing': 5000},
            'totals': {'grand_total': 10000}
        }
        agent.bq_tool.get_next_consultant_round_robin.return_value = None
        agent.pdf_generator.generate_quote_pdf.return_value = b'PDF_CONTENT'
        agent.email_sender.send_quote_email.return_value = True

        result = agent.generate_quote(
            customer_data={'email': 'test@test.com', 'name': 'Test', 'destination': 'Zanzibar'},
            send_email=True,
            initial_status='generated'
        )

        # Email should be sent for non-draft
        agent.email_sender.send_quote_email.assert_called_once()
        assert result['email_sent'] == True
        assert result['quote']['status'] == 'sent'

    def test_sent_status_when_email_successful(self, mock_quote_agent):
        """Verify status is 'sent' when email is successful for non-draft"""
        agent = mock_quote_agent

        agent.bq_tool.find_matching_hotels.return_value = [{
            'hotel_name': 'Test Hotel',
            'rate_id': 'rate_123'
        }]
        agent.bq_tool.calculate_quote_price.return_value = {
            'per_person_rates': {'adult_sharing': 5000},
            'totals': {'grand_total': 10000}
        }
        agent.bq_tool.get_next_consultant_round_robin.return_value = None
        agent.pdf_generator.generate_quote_pdf.return_value = b'PDF_CONTENT'
        agent.email_sender.send_quote_email.return_value = True

        result = agent.generate_quote(
            customer_data={'email': 'test@test.com', 'name': 'Test', 'destination': 'Zanzibar'},
            send_email=True
        )

        assert result['quote']['status'] == 'sent'

    def test_generated_status_when_email_fails(self, mock_quote_agent):
        """Verify status is 'generated' when email fails"""
        agent = mock_quote_agent

        agent.bq_tool.find_matching_hotels.return_value = [{
            'hotel_name': 'Test Hotel',
            'rate_id': 'rate_123'
        }]
        agent.bq_tool.calculate_quote_price.return_value = {
            'per_person_rates': {'adult_sharing': 5000},
            'totals': {'grand_total': 10000}
        }
        agent.bq_tool.get_next_consultant_round_robin.return_value = None
        agent.pdf_generator.generate_quote_pdf.return_value = b'PDF_CONTENT'
        agent.email_sender.send_quote_email.return_value = False

        result = agent.generate_quote(
            customer_data={'email': 'test@test.com', 'name': 'Test', 'destination': 'Zanzibar'},
            send_email=True
        )

        assert result['quote']['status'] == 'generated'


class TestDraftQuoteWorkflow:
    """Test the draft -> review -> send workflow"""

    @pytest.fixture
    def mock_config(self):
        config = Mock(spec=ClientConfig)
        config.client_id = 'test_tenant'
        config.destination_names = ['Zanzibar', 'Mauritius']
        config.timezone = 'Africa/Johannesburg'
        return config

    @pytest.fixture
    def mock_quote_agent(self, mock_config):
        """Create a mocked QuoteAgent instance"""
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

    def test_draft_quote_preserves_all_details(self, mock_quote_agent):
        """Verify all parsed details are preserved in draft quote"""
        agent = mock_quote_agent

        customer_data = {
            'name': 'Jane Smith',
            'email': 'jane@example.com',
            'phone': '+27987654321',
            'destination': 'Mauritius',
            'check_in': '2025-07-01',
            'check_out': '2025-07-10',
            'adults': 2,
            'children': 2,
            'children_ages': [5, 8],
            'budget': 100000,
            'special_requests': 'Ocean view room'
        }

        agent.bq_tool.find_matching_hotels.return_value = [{
            'hotel_name': 'Luxury Resort',
            'rate_id': 'rate_456',
            'hotel_rating': '5*',
            'room_type': 'Family Suite',
            'meal_plan': 'AI'
        }]
        agent.bq_tool.calculate_quote_price.return_value = {
            'per_person_rates': {'adult_sharing': 8000, 'child_sharing': 4000},
            'totals': {'grand_total': 24000}
        }
        agent.bq_tool.get_next_consultant_round_robin.return_value = None
        agent.supabase.client.table.return_value.insert.return_value.execute.return_value = Mock(data=[{}])

        result = agent.generate_quote(
            customer_data=customer_data,
            send_email=False,
            initial_status='draft'
        )

        quote = result['quote']
        assert quote['status'] == 'draft'
        assert quote['customer_name'] == 'Jane Smith'
        assert quote['customer_email'] == 'jane@example.com'
        assert quote['destination'] == 'Mauritius'
        assert quote['adults'] == 2
        assert quote['children'] == 2
        assert quote['children_ages'] == [5, 8]
        assert quote['nights'] == 9  # July 1-10

    def test_pdf_still_generated_for_draft(self, mock_quote_agent):
        """Verify PDF is generated even for draft quotes (for preview)"""
        agent = mock_quote_agent

        agent.bq_tool.find_matching_hotels.return_value = [{
            'hotel_name': 'Test Hotel',
            'rate_id': 'rate_123'
        }]
        agent.bq_tool.calculate_quote_price.return_value = {
            'per_person_rates': {'adult_sharing': 5000},
            'totals': {'grand_total': 10000}
        }
        agent.bq_tool.get_next_consultant_round_robin.return_value = None
        agent.pdf_generator.generate_quote_pdf.return_value = b'PDF_CONTENT'
        agent.supabase.client.table.return_value.insert.return_value.execute.return_value = Mock(data=[{}])

        result = agent.generate_quote(
            customer_data={'email': 'test@test.com', 'name': 'Test', 'destination': 'Zanzibar'},
            send_email=False,
            initial_status='draft'
        )

        # PDF should still be generated for preview
        agent.pdf_generator.generate_quote_pdf.assert_called_once()
        assert result['quote']['pdf_generated'] == True
