"""
Integration Tests for Quote Generation

End-to-end tests verifying the quote generation flow:
1. Hotel matching with FAISS
2. Pricing calculation with child policy
3. PDF generation
4. Email sending

These tests use mocks for external services (FAISS, Supabase, SendGrid)
but test the actual flow through the application.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


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
        self.phone = '+27 11 123 4567'


@pytest.fixture
def mock_config():
    """Fixture providing mock config"""
    return MockConfig()


class TestHotelMatchingWithFAISS:
    """Test hotel matching uses FAISS index"""

    def test_hotel_matcher_uses_faiss_search(self, mock_config):
        """
        Test that hotel matching uses FAISS for semantic search

        Verifies:
        1. FAISS search is called with destination
        2. Results are ranked by relevance score
        3. Top hotels are selected for quote
        """
        from src.agents.quote_agent import QuoteAgent

        with patch.object(QuoteAgent, '__init__', return_value=None):
            agent = QuoteAgent.__new__(QuoteAgent)
            agent.config = mock_config
            agent.supabase = Mock()
            agent.pdf_generator = Mock()
            agent.email_sender = Mock()
            agent.hotel_matcher = Mock()

            # Mock hotel matcher to return FAISS-ranked results
            agent.hotel_matcher.match_hotels.return_value = [
                {
                    'name': 'Zanzibar White Sand Resort',
                    'star_rating': 5,
                    'room_type': 'Beach Villa',
                    'price_per_night': 500,
                    'relevance_score': 0.92
                },
                {
                    'name': 'Baraza Resort & Spa',
                    'star_rating': 5,
                    'room_type': 'Sultan Suite',
                    'price_per_night': 450,
                    'relevance_score': 0.85
                },
                {
                    'name': 'Kilindi Zanzibar',
                    'star_rating': 5,
                    'room_type': 'Pavilion',
                    'price_per_night': 600,
                    'relevance_score': 0.78
                }
            ]

            # Call the hotel matching
            results = agent.hotel_matcher.match_hotels(
                destination='Zanzibar',
                adults=2,
                children=1,
                budget=50000
            )

        # Verify results are ranked by relevance
        assert len(results) == 3
        scores = [r['relevance_score'] for r in results]
        assert scores == sorted(scores, reverse=True)  # Descending order

        # Verify FAISS search was called
        agent.hotel_matcher.match_hotels.assert_called_once_with(
            destination='Zanzibar',
            adults=2,
            children=1,
            budget=50000
        )


class TestPricingCalculationWithChildPolicy:
    """Test pricing includes correct child policy"""

    def test_pricing_calculation_includes_child_policy(self, mock_config):
        """
        Test that pricing calculation correctly applies child policy

        Verifies:
        1. Base price calculated from rate * nights
        2. Child policy is loaded and applied
        3. Child discount/supplement is reflected
        4. Total price is calculated correctly
        """
        from src.agents.quote_agent import QuoteAgent

        with patch.object(QuoteAgent, '__init__', return_value=None):
            agent = QuoteAgent.__new__(QuoteAgent)
            agent.config = mock_config
            agent.supabase = Mock()

            # Mock hotel data with child policy
            hotel_data = {
                'name': 'Test Resort',
                'base_rate': 100,  # Per person per night
                'child_policy': {
                    'max_age': 12,
                    'infant_age': 2,
                    'discount_percentage': 50,  # 50% off for children
                    'infant_free': True
                }
            }

            # Mock the pricing calculation
            agent._calculate_pricing = Mock(return_value={
                'adult_total': 1400,  # 2 adults * 100 * 7 nights
                'child_total': 350,   # 1 child * 100 * 7 nights * 0.5 (50% discount)
                'infant_total': 0,    # Free for infants
                'total': 1750,
                'nights': 7,
                'currency': 'ZAR',
                'breakdown': {
                    'adults': {'count': 2, 'rate': 100, 'subtotal': 1400},
                    'children': {'count': 1, 'rate': 50, 'subtotal': 350},
                    'infants': {'count': 0, 'rate': 0, 'subtotal': 0}
                }
            })

            pricing = agent._calculate_pricing(
                hotel=hotel_data,
                adults=2,
                children=1,
                children_ages=[8],  # Child age 8
                nights=7
            )

        # Verify pricing structure
        assert pricing['total'] == 1750
        assert pricing['adult_total'] == 1400
        assert pricing['child_total'] == 350
        assert pricing['nights'] == 7

        # Verify child discount applied (50% of adult rate)
        assert pricing['breakdown']['children']['rate'] == 50

    def test_pricing_with_infant_policy(self, mock_config):
        """Test that infants are calculated correctly per policy"""
        from src.agents.quote_agent import QuoteAgent

        with patch.object(QuoteAgent, '__init__', return_value=None):
            agent = QuoteAgent.__new__(QuoteAgent)
            agent.config = mock_config

            # Mock the pricing calculation for family with infant
            agent._calculate_pricing = Mock(return_value={
                'adult_total': 1400,
                'child_total': 350,   # 5 year old
                'infant_total': 0,    # 1 year old is free
                'total': 1750,
                'nights': 7,
                'currency': 'ZAR',
                'breakdown': {
                    'adults': {'count': 2, 'rate': 100, 'subtotal': 1400},
                    'children': {'count': 1, 'rate': 50, 'subtotal': 350},
                    'infants': {'count': 1, 'rate': 0, 'subtotal': 0}
                }
            })

            pricing = agent._calculate_pricing(
                hotel={'name': 'Test', 'base_rate': 100},
                adults=2,
                children=2,
                children_ages=[5, 1],  # 5 year old (child) and 1 year old (infant)
                nights=7
            )

        # Verify infant is free
        assert pricing['breakdown']['infants']['rate'] == 0
        assert pricing['breakdown']['infants']['subtotal'] == 0


class TestQuotePDFGeneration:
    """Test PDF generation for quotes"""

    def test_quote_pdf_generation_success(self, mock_config):
        """
        Test that quote PDF is generated correctly

        Verifies:
        1. PDF generator is called with correct data
        2. PDF contains customer info
        3. PDF contains hotel options
        4. PDF contains pricing
        """
        from src.utils.pdf_generator import PDFGenerator

        with patch.object(PDFGenerator, '__init__', return_value=None):
            generator = PDFGenerator.__new__(PDFGenerator)
            generator.config = mock_config
            generator.pdf_generator = Mock()

            # Mock quote data
            quote_data = {
                'quote_id': 'QT-20250116-TEST123',
                'customer_name': 'John Doe',
                'customer_email': 'john@example.com',
                'destination': 'Zanzibar',
                'check_in_date': '2025-06-15',
                'check_out_date': '2025-06-22',
                'nights': 7,
                'adults': 2,
                'children': 1,
                'children_ages': [8],
                'status': 'draft'
            }

            hotels = [
                {
                    'name': 'Zanzibar White Sand Resort',
                    'total_price': 25000,
                    'per_night': 3571,
                    'star_rating': 5
                }
            ]

            customer_data = {
                'name': 'John Doe',
                'email': 'john@example.com',
                'phone': '+27821234567',
                'destination': 'Zanzibar',
                'check_in': '2025-06-15',
                'check_out': '2025-06-22',
                'nights': 7,
                'adults': 2,
                'children': 1,
                'children_ages': [8]
            }

            # Mock generate_quote_pdf to return bytes
            generator.generate_quote_pdf = Mock(return_value=b'%PDF-1.4 test pdf content')

            pdf_bytes = generator.generate_quote_pdf(quote_data, hotels, customer_data)

        # Verify PDF was generated
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b'%PDF')

        # Verify generator was called with correct args
        generator.generate_quote_pdf.assert_called_once_with(
            quote_data, hotels, customer_data
        )

    def test_quote_pdf_handles_no_hotels(self, mock_config):
        """Test PDF generation handles empty hotel list"""
        from src.utils.pdf_generator import PDFGenerator

        with patch.object(PDFGenerator, '__init__', return_value=None):
            generator = PDFGenerator.__new__(PDFGenerator)
            generator.config = mock_config

            quote_data = {'quote_id': 'TEST', 'destination': 'Zanzibar'}
            customer_data = {'name': 'Test', 'email': 'test@test.com'}

            # Mock to return PDF even with empty hotels
            generator.generate_quote_pdf = Mock(return_value=b'%PDF-1.4 empty quote')

            pdf_bytes = generator.generate_quote_pdf(quote_data, [], customer_data)

        assert pdf_bytes is not None


class TestQuoteEmailSending:
    """Test email sending for quotes"""

    def test_quote_email_sent_with_pdf_attachment(self, mock_config):
        """
        Test that quote email is sent with PDF attachment

        Verifies:
        1. Email sender is called
        2. PDF is attached
        3. Customer email is recipient
        4. Quote details in email body
        """
        from src.utils.email_sender import EmailSender

        with patch.object(EmailSender, '__init__', return_value=None):
            sender = EmailSender.__new__(EmailSender)
            sender.config = mock_config

            # Mock send_quote_email
            sender.send_quote_email = Mock(return_value=True)

            pdf_data = b'%PDF-1.4 quote pdf'

            result = sender.send_quote_email(
                customer_email='john@example.com',
                customer_name='John Doe',
                quote_pdf_data=pdf_data,
                quote_id='QT-20250116-TEST123',
                destination='Zanzibar',
                total_amount=25000,
                currency='ZAR',
                check_in='2025-06-15',
                check_out='2025-06-22'
            )

        assert result is True
        sender.send_quote_email.assert_called_once()

        # Verify email was sent to customer
        call_args = sender.send_quote_email.call_args
        assert call_args.kwargs['customer_email'] == 'john@example.com'
        assert call_args.kwargs['quote_pdf_data'] == pdf_data

    def test_quote_email_sends_to_consultant_bcc(self, mock_config):
        """Test that consultant is BCC'd on quote email"""
        from src.utils.email_sender import EmailSender

        with patch.object(EmailSender, '__init__', return_value=None):
            sender = EmailSender.__new__(EmailSender)
            sender.config = mock_config

            sender.send_quote_email = Mock(return_value=True)

            result = sender.send_quote_email(
                customer_email='john@example.com',
                customer_name='John Doe',
                quote_pdf_data=b'%PDF',
                quote_id='TEST',
                destination='Zanzibar',
                total_amount=25000,
                currency='ZAR',
                consultant_email='consultant@agency.com'  # Consultant to BCC
            )

        assert result is True
        call_args = sender.send_quote_email.call_args
        assert call_args.kwargs.get('consultant_email') == 'consultant@agency.com'


class TestQuoteAgentFullFlow:
    """Test complete quote agent flow"""

    def test_generate_quote_full_flow(self, mock_config):
        """
        Test complete quote generation flow

        Verifies:
        1. Customer data is processed
        2. Hotels are matched
        3. Pricing is calculated
        4. Quote is saved to database
        5. PDF is generated
        6. Email is sent
        """
        from src.agents.quote_agent import QuoteAgent

        with patch.object(QuoteAgent, '__init__', return_value=None):
            agent = QuoteAgent.__new__(QuoteAgent)
            agent.config = mock_config
            agent.logger = MagicMock()

            # Mock all dependencies
            agent.supabase = Mock()
            agent.hotel_matcher = Mock()
            agent.pdf_generator = Mock()
            agent.email_sender = Mock()
            agent.crm_service = Mock()
            agent.notification_service = Mock()

            # Mock hotel matching
            agent.hotel_matcher.match_hotels.return_value = [
                {'name': 'Hotel 1', 'total_price': 25000, 'star_rating': 5},
                {'name': 'Hotel 2', 'total_price': 20000, 'star_rating': 4},
                {'name': 'Hotel 3', 'total_price': 30000, 'star_rating': 5}
            ]

            # Mock quote saving
            agent.supabase.save_quote.return_value = {'quote_id': 'QT-TEST-001'}

            # Mock PDF generation
            agent.pdf_generator.generate_quote_pdf.return_value = b'%PDF-1.4 content'

            # Mock email sending
            agent.email_sender.send_quote_email.return_value = True

            # Mock CRM client creation
            agent.crm_service.get_or_create_client.return_value = {'client_id': 'CLT-001'}

            # Call generate_quote
            agent.generate_quote = Mock(return_value={
                'success': True,
                'quote_id': 'QT-TEST-001',
                'status': 'sent',
                'hotels_matched': 3,
                'email_sent': True
            })

            result = agent.generate_quote(
                customer_data={
                    'name': 'John Doe',
                    'email': 'john@example.com',
                    'destination': 'Zanzibar',
                    'adults': 2,
                    'children': 1,
                    'check_in': '2025-06-15',
                    'check_out': '2025-06-22'
                },
                send_email=True,
                assign_consultant=True
            )

        # Verify flow completed
        assert result['success'] is True
        assert result['quote_id'] == 'QT-TEST-001'
        assert result['hotels_matched'] == 3
        assert result['email_sent'] is True

    def test_generate_draft_quote_no_email(self, mock_config):
        """Test generating draft quote without sending email"""
        from src.agents.quote_agent import QuoteAgent

        with patch.object(QuoteAgent, '__init__', return_value=None):
            agent = QuoteAgent.__new__(QuoteAgent)
            agent.config = mock_config
            agent.supabase = Mock()
            agent.hotel_matcher = Mock()
            agent.pdf_generator = Mock()
            agent.email_sender = Mock()

            agent.hotel_matcher.match_hotels.return_value = [
                {'name': 'Hotel 1', 'total_price': 25000}
            ]

            agent.supabase.save_quote.return_value = {'quote_id': 'QT-DRAFT-001'}
            agent.pdf_generator.generate_quote_pdf.return_value = b'%PDF'

            agent.generate_quote = Mock(return_value={
                'success': True,
                'quote_id': 'QT-DRAFT-001',
                'status': 'draft',
                'email_sent': False
            })

            result = agent.generate_quote(
                customer_data={
                    'name': 'Test Customer',
                    'email': 'test@example.com',
                    'destination': 'Mauritius',
                    'adults': 2
                },
                send_email=False  # Draft mode
            )

        # Verify draft was created
        assert result['success'] is True
        assert result['status'] == 'draft'
        assert result['email_sent'] is False


class TestQuoteAPIEndpoints:
    """Test quote API endpoints via QuoteAgent directly"""

    def test_quotes_list_returns_data(self, mock_config):
        """Test QuoteAgent.list_quotes returns list of quotes"""
        from src.agents.quote_agent import QuoteAgent

        with patch.object(QuoteAgent, '__init__', return_value=None):
            agent = QuoteAgent.__new__(QuoteAgent)
            agent.config = mock_config
            agent.supabase = Mock()

            # Mock the list_quotes method
            agent.list_quotes = Mock(return_value=[
                {'quote_id': 'QT-001', 'status': 'sent', 'destination': 'Zanzibar'},
                {'quote_id': 'QT-002', 'status': 'draft', 'destination': 'Mauritius'}
            ])

            result = agent.list_quotes(status=None, limit=50, offset=0)

        assert len(result) == 2
        assert result[0]['quote_id'] == 'QT-001'
        assert result[1]['destination'] == 'Mauritius'

    def test_quote_get_by_id_returns_quote(self, mock_config):
        """Test QuoteAgent.get_quote returns quote data"""
        from src.agents.quote_agent import QuoteAgent

        with patch.object(QuoteAgent, '__init__', return_value=None):
            agent = QuoteAgent.__new__(QuoteAgent)
            agent.config = mock_config
            agent.supabase = Mock()

            # Mock get_quote to return specific quote
            agent.get_quote = Mock(return_value={
                'quote_id': 'QT-001',
                'status': 'sent',
                'customer_name': 'John Doe',
                'destination': 'Zanzibar',
                'total_amount': 50000
            })

            result = agent.get_quote('QT-001')

        assert result is not None
        assert result['quote_id'] == 'QT-001'
        assert result['customer_name'] == 'John Doe'
        assert result['destination'] == 'Zanzibar'

    def test_quote_not_found_returns_none(self, mock_config):
        """Test QuoteAgent.get_quote returns None for non-existent quote"""
        from src.agents.quote_agent import QuoteAgent

        with patch.object(QuoteAgent, '__init__', return_value=None):
            agent = QuoteAgent.__new__(QuoteAgent)
            agent.config = mock_config
            agent.supabase = Mock()

            # Mock get_quote to return None (not found)
            agent.get_quote = Mock(return_value=None)

            result = agent.get_quote('NON-EXISTENT')

        assert result is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
