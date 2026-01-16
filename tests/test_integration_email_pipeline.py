"""
Integration Tests for Email Pipeline

End-to-end tests verifying the full email -> quote pipeline:
1. Inbound email -> Tenant lookup -> Parse -> Draft Quote
2. Draft quote -> Approve -> Send
3. Error handling for unknown tenants
4. LLM parser fallback to rule-based

These tests use mocks for external services (SendGrid, OpenAI, Supabase)
but test the actual flow through the application.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from fastapi import FastAPI


class MockConfig:
    """Mock ClientConfig for testing"""
    def __init__(self, client_id='test_tenant'):
        self.client_id = client_id
        self.company_name = 'Test Travel Agency'
        self.destination_names = ['Zanzibar', 'Mauritius', 'Seychelles', 'Maldives']
        self.timezone = 'Africa/Johannesburg'
        self.currency = 'ZAR'
        self.primary_email = 'test@example.com'
        self.sendgrid_api_key = 'test_key'
        self.sendgrid_from_email = 'quotes@test.com'
        self.sendgrid_from_name = 'Test Travel'
        self.sendgrid_reply_to = 'reply@test.com'
        self.primary_color = '#000000'
        self.secondary_color = '#ffffff'
        self.logo_url = 'https://example.com/logo.png'
        self.bank_name = 'Test Bank'
        self.bank_account_name = 'Test Account'
        self.bank_account_number = '1234567890'
        self.bank_branch_code = '123456'
        self.bank_swift_code = 'TESTSWIFT'
        self.payment_reference_prefix = 'TEST'


@pytest.fixture
def mock_config():
    """Fixture providing mock config"""
    return MockConfig()


@pytest.fixture
def app_with_mocked_deps():
    """Create FastAPI app with mocked dependencies"""
    # Create a minimal FastAPI app with email webhook router
    app = FastAPI()

    from src.webhooks.email_webhook import router as email_webhook_router
    app.include_router(email_webhook_router, prefix="/webhooks")

    return app


class TestFullEmailToDraftQuotePipeline:
    """Test complete email -> draft quote pipeline"""

    @pytest.fixture
    def test_client(self, app_with_mocked_deps):
        """Create test client"""
        return TestClient(app_with_mocked_deps)

    @patch('src.webhooks.email_webhook.list_clients')
    @patch('src.webhooks.email_webhook.get_config')
    @patch('src.webhooks.email_webhook.get_tenant_email_addresses')
    @patch('src.webhooks.email_webhook._tenant_email_cache', {'data': {}, 'timestamp': 0})
    def test_full_email_to_draft_quote_pipeline(
        self,
        mock_get_tenant_emails,
        mock_get_config,
        mock_list_clients,
        test_client,
        mock_config
    ):
        """
        Test complete pipeline: inbound email -> tenant lookup -> parse -> draft quote

        Verifies:
        1. Email is received and parsed
        2. Tenant is resolved correctly
        3. Background task is queued for processing
        4. Returns success with tenant info
        """
        # Setup mocks
        mock_list_clients.return_value = ['test_tenant']
        mock_get_config.return_value = mock_config
        mock_get_tenant_emails.return_value = {
            'support_email': 'support@testagency.com',
            'sendgrid_email': 'test-tenant@zorah.ai',
            'primary_email': 'admin@testagency.com',
            'tenant_id': 'test_tenant'
        }

        # Simulate SendGrid inbound parse POST data
        form_data = {
            'from': 'John Doe <john@example.com>',
            'to': 'support@testagency.com',
            'subject': 'Quote request for Zanzibar',
            'text': '''Hi,

I'm looking for a holiday to Zanzibar for 2 adults.
We want to travel in June 2025 for 7 nights.
Budget around R50,000 total.

Thanks,
John
''',
            'envelope': '{"to":["support@testagency.com"],"from":"john@example.com"}',
            'headers': 'Content-Type: text/plain',
            'attachments': '0'
        }

        # Make request
        response = test_client.post(
            '/webhooks/email/inbound',
            data=form_data
        )

        # Verify response
        assert response.status_code == 200
        result = response.json()

        assert result['success'] is True
        assert result['tenant_id'] == 'test_tenant'
        assert result['from'] == 'john@example.com'
        assert 'diagnostic_id' in result
        assert result['message'] == 'Email queued for processing'

    @patch('src.webhooks.email_webhook.list_clients')
    @patch('src.webhooks.email_webhook._tenant_email_cache', {'data': {}, 'timestamp': 0})
    def test_tenant_not_found_handled_gracefully(
        self,
        mock_list_clients,
        test_client
    ):
        """
        Test that unknown tenant email returns 200 but with success=False

        The webhook should not fail with 4xx/5xx for unknown tenants,
        as SendGrid will retry. Instead, return 200 with error info.
        """
        # Setup - no matching tenants
        mock_list_clients.return_value = []

        form_data = {
            'from': 'unknown@nowhere.com',
            'to': 'nonexistent@unknown.com',
            'subject': 'Test',
            'text': 'Test email',
            'envelope': '{}',
            'headers': '',
            'attachments': '0'
        }

        response = test_client.post(
            '/webhooks/email/inbound',
            data=form_data
        )

        # Should return 200 (not fail) but indicate tenant not found
        assert response.status_code == 200
        result = response.json()

        assert result['success'] is False
        assert 'Could not determine tenant' in result.get('error', '')
        assert 'diagnostic_id' in result


class TestDraftQuoteApproveAndSend:
    """Test draft quote approval and sending workflow"""

    def test_draft_quote_approve_and_send(self):
        """
        Test approving and sending a draft quote via QuoteAgent.send_draft_quote()

        Verifies:
        1. QuoteAgent.send_draft_quote() is called correctly
        2. Returns success with correct fields
        3. Status changed to 'sent'
        """
        from src.agents.quote_agent import QuoteAgent
        from unittest.mock import Mock

        # Create mock config
        mock_config = Mock()
        mock_config.client_id = 'test_tenant'
        mock_config.timezone = 'Africa/Johannesburg'

        # Create QuoteAgent with mocked dependencies
        with patch.object(QuoteAgent, '__init__', return_value=None):
            agent = QuoteAgent.__new__(QuoteAgent)
            agent.config = mock_config
            agent.supabase = Mock()
            agent.pdf_generator = Mock()
            agent.email_sender = Mock()

            # Mock get_quote to return a draft quote
            agent.get_quote = Mock(return_value={
                'quote_id': 'QT-20250116-ABC123',
                'status': 'draft',
                'customer_email': 'john@example.com',
                'customer_name': 'John Doe',
                'customer_phone': '+27821234567',
                'destination': 'Zanzibar',
                'check_in_date': '2025-06-15',
                'check_out_date': '2025-06-22',
                'nights': 7,
                'adults': 2,
                'children': 0,
                'children_ages': [],
                'hotels': [{'name': 'Test Hotel', 'total_price': 50000}]
            })

            # Mock PDF generation
            agent.pdf_generator.generate_quote_pdf.return_value = b'PDF_CONTENT'

            # Mock email sending success
            agent.email_sender.send_quote_email.return_value = True

            # Mock status update
            agent.update_quote_status = Mock(return_value=True)

            # Mock follow-up call scheduling
            agent._schedule_follow_up_call = Mock(return_value=True)

            # Call send_draft_quote
            result = agent.send_draft_quote('QT-20250116-ABC123')

        # Verify result
        assert result['success'] is True
        assert result['quote_id'] == 'QT-20250116-ABC123'
        assert result['status'] == 'sent'
        assert 'sent_at' in result
        assert result['customer_email'] == 'john@example.com'

        # Verify PDF was regenerated
        agent.pdf_generator.generate_quote_pdf.assert_called_once()

        # Verify email was sent
        agent.email_sender.send_quote_email.assert_called_once()

        # Verify status was updated
        agent.update_quote_status.assert_called_with('QT-20250116-ABC123', 'sent')

    def test_send_non_draft_quote_fails(self):
        """Test that sending a non-draft quote fails gracefully"""
        from src.agents.quote_agent import QuoteAgent
        from unittest.mock import Mock

        mock_config = Mock()
        mock_config.client_id = 'test_tenant'

        with patch.object(QuoteAgent, '__init__', return_value=None):
            agent = QuoteAgent.__new__(QuoteAgent)
            agent.config = mock_config
            agent.supabase = Mock()

            # Mock get_quote to return a quote that's already sent
            agent.get_quote = Mock(return_value={
                'quote_id': 'QT-20250116-XYZ789',
                'status': 'sent',  # Already sent
                'customer_email': 'test@example.com'
            })

            result = agent.send_draft_quote('QT-20250116-XYZ789')

        # Should fail because it's not a draft
        assert result['success'] is False
        assert 'not a draft' in result.get('error', '').lower()


class TestEmailParserFallback:
    """Test LLM parser fallback to rule-based"""

    @patch('src.agents.llm_email_parser.LLMEmailParser._parse_with_llm')
    def test_email_parse_fallback_to_rules(self, mock_llm_parse):
        """
        Test that LLM parser falls back to UniversalEmailParser on failure

        Verifies:
        1. LLM parser is tried first
        2. On exception, fallback to rule-based parser
        3. Fallback still extracts destination
        """
        # Mock LLM parsing to raise exception
        mock_llm_parse.side_effect = Exception("API Error: Rate limit exceeded")

        # Import with API key set to trigger LLM path
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            from src.agents.llm_email_parser import LLMEmailParser

            parser = LLMEmailParser(MockConfig())

            # parse() takes email_body, subject (positional args)
            result = parser.parse(
                "I want to go to Zanzibar for 2 adults in June",
                "Holiday inquiry"
            )

        # Should have used fallback
        assert result['parse_method'] == 'fallback'
        # Fallback should still extract destination
        assert result['destination'] == 'Zanzibar'
        assert result['adults'] == 2

    def test_rule_based_parser_handles_complex_email(self):
        """Test rule-based parser with realistic email content"""
        from src.agents.universal_email_parser import UniversalEmailParser

        parser = UniversalEmailParser(MockConfig())

        complex_email = """
Hi there,

We're planning a family trip to Mauritius.
There will be 2 adults and 2 children (ages 5 and 8).
We're looking at traveling from June 15th to June 22nd 2025.
Our budget is around R80,000 for the whole trip.

Please can you send us some options?

Kind regards,
Sarah Johnson
sarah.johnson@gmail.com
+27 82 123 4567
"""

        result = parser.parse(complex_email, "Family holiday to Mauritius")

        assert result['destination'] == 'Mauritius'
        assert result['adults'] == 2
        assert result['children'] == 2
        # Parser should extract contact info if present
        assert 'email' in result or 'name' in result


class TestEmailPipelineErrorHandling:
    """Test error handling in email pipeline"""

    @pytest.fixture
    def test_client(self, app_with_mocked_deps):
        return TestClient(app_with_mocked_deps)

    @patch('src.webhooks.email_webhook.list_clients')
    @patch('src.webhooks.email_webhook.get_config')
    @patch('src.webhooks.email_webhook.get_tenant_email_addresses')
    @patch('src.webhooks.email_webhook._tenant_email_cache', {'data': {}, 'timestamp': 0})
    def test_config_load_error_handled(
        self,
        mock_get_tenant_emails,
        mock_get_config,
        mock_list_clients,
        test_client
    ):
        """Test handling when config fails to load"""
        mock_list_clients.return_value = ['test_tenant']
        mock_get_tenant_emails.return_value = {
            'support_email': 'support@test.com',
            'sendgrid_email': None,
            'primary_email': None,
            'tenant_id': 'test_tenant'
        }
        # Config loading fails
        mock_get_config.side_effect = Exception("Config file not found")

        form_data = {
            'from': 'test@example.com',
            'to': 'support@test.com',
            'subject': 'Test',
            'text': 'Test email',
            'envelope': '{}',
            'headers': '',
            'attachments': '0'
        }

        response = test_client.post('/webhooks/email/inbound', data=form_data)

        # Should return 200 with error (not crash)
        assert response.status_code == 200
        result = response.json()
        assert result['success'] is False
        assert 'Config load failed' in result.get('error', '')

    def test_malformed_envelope_handled(self, test_client):
        """Test handling of malformed envelope JSON"""
        with patch('src.webhooks.email_webhook.list_clients') as mock_list:
            with patch('src.webhooks.email_webhook._tenant_email_cache', {'data': {}, 'timestamp': 0}):
                mock_list.return_value = []

                form_data = {
                    'from': 'test@example.com',
                    'to': 'test@test.com',
                    'subject': 'Test',
                    'text': 'Test',
                    'envelope': 'not valid json {{{',  # Malformed
                    'headers': '',
                    'attachments': '0'
                }

                response = test_client.post('/webhooks/email/inbound', data=form_data)

                # Should not crash - envelope parsing is defensive
                assert response.status_code == 200


class TestTenantLookupStrategies:
    """Test different tenant lookup strategies"""

    @pytest.fixture
    def test_client(self, app_with_mocked_deps):
        return TestClient(app_with_mocked_deps)

    @patch('src.webhooks.email_webhook.list_clients')
    @patch('src.webhooks.email_webhook.get_config')
    @patch('src.webhooks.email_webhook.get_tenant_email_addresses')
    @patch('src.webhooks.email_webhook._tenant_email_cache', {'data': {}, 'timestamp': 0})
    def test_lookup_by_sendgrid_email(
        self,
        mock_get_tenant_emails,
        mock_get_config,
        mock_list_clients,
        test_client,
        mock_config
    ):
        """Test tenant lookup by sendgrid_username@zorah.ai format"""
        mock_list_clients.return_value = ['africastay']
        mock_get_config.return_value = mock_config
        mock_get_tenant_emails.return_value = {
            'support_email': None,
            'sendgrid_email': 'final-itc-3@zorah.ai',
            'primary_email': None,
            'tenant_id': 'africastay'
        }

        form_data = {
            'from': 'customer@gmail.com',
            'to': 'final-itc-3@zorah.ai',  # SendGrid format
            'subject': 'Zanzibar quote please',
            'text': 'I want to go to Zanzibar',
            'envelope': '{}',
            'headers': '',
            'attachments': '0'
        }

        response = test_client.post('/webhooks/email/inbound', data=form_data)

        assert response.status_code == 200
        result = response.json()
        assert result['success'] is True
        assert result['tenant_id'] == 'africastay'
        assert result['resolution_strategy'] == 'sendgrid_email'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
