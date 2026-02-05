"""
Tests for Email Sender - Multi-Tenant Email Service

Tests cover:
- EmailSender initialization and configuration
- SendGrid API integration (mocked)
- SMTP fallback (mocked)
- Quote emails with attachments
- Invoice emails with banking details
- Consultant notifications
- Team invitation emails
- Error handling for API failures
"""

import pytest
import base64
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.email_sender import EmailSender


# ==================== Fixtures ====================

@pytest.fixture(autouse=True)
def reset_sendgrid_circuit():
    """Reset the SendGrid circuit breaker before each test to prevent cross-test contamination."""
    from src.utils.circuit_breaker import sendgrid_circuit
    sendgrid_circuit.failures = 0
    sendgrid_circuit.state = "closed"
    sendgrid_circuit.last_failure_time = 0
    yield


@pytest.fixture
def mock_config_sendgrid():
    """Create a mock config with SendGrid enabled."""
    config = MagicMock()
    config.client_id = "test_tenant"
    config.sendgrid_api_key = "SG.test-api-key-12345"
    config.sendgrid_from_email = "quotes@testcompany.com"
    config.sendgrid_from_name = "Test Travel Co"
    config.sendgrid_reply_to = "support@testcompany.com"
    config.primary_email = "admin@testcompany.com"
    config.company_name = "Test Travel Company"
    config.primary_color = "#FF6B6B"
    config.secondary_color = "#4ECDC4"
    config.email_signature = "Best regards,\nThe Test Travel Team"
    config.bank_name = "Test Bank"
    config.bank_account_name = "Test Travel Co"
    config.bank_account_number = "1234567890"
    config.bank_branch_code = "123456"
    config.payment_reference_prefix = "TTC"
    config.frontend_url = "https://app.testtravel.com"
    return config


@pytest.fixture
def mock_config_smtp():
    """Create a mock config with SMTP fallback (no SendGrid)."""
    config = MagicMock()
    config.client_id = "test_tenant_smtp"
    config.sendgrid_api_key = None
    config.primary_email = "info@testcompany.com"
    config.company_name = "Test Travel SMTP"
    config.smtp_host = "smtp.test.com"
    config.smtp_port = 465
    config.smtp_username = "smtp_user"
    config.smtp_password = "smtp_pass"
    config.primary_color = "#2E86AB"
    config.secondary_color = "#A23B72"
    config.email_signature = "Thanks,\nTest Team"
    return config


@pytest.fixture
def mock_supabase_tool():
    """Mock SupabaseTool for database settings."""
    with patch('src.tools.supabase_tool.SupabaseTool') as mock:
        mock_instance = MagicMock()
        mock_instance.get_tenant_settings.return_value = None
        mock.return_value = mock_instance
        yield mock


# ==================== Initialization Tests ====================

class TestEmailSenderInit:
    """Test EmailSender initialization."""

    def test_init_with_sendgrid_config(self, mock_config_sendgrid, mock_supabase_tool):
        """Should initialize with SendGrid when API key is provided."""
        sender = EmailSender(mock_config_sendgrid)

        assert sender.use_sendgrid is True
        assert sender.sendgrid_api_key == "SG.test-api-key-12345"
        assert sender.from_email == "quotes@testcompany.com"
        assert sender.from_name == "Test Travel Co"
        assert sender.reply_to == "support@testcompany.com"

    def test_init_with_smtp_fallback(self, mock_config_smtp, mock_supabase_tool):
        """Should fallback to SMTP when no SendGrid key."""
        sender = EmailSender(mock_config_smtp)

        assert sender.use_sendgrid is False
        assert sender.smtp_host == "smtp.test.com"
        assert sender.smtp_port == 465
        assert sender.smtp_username == "smtp_user"

    def test_init_loads_db_settings_first(self, mock_config_sendgrid):
        """Should prefer database settings over config file."""
        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase:
            mock_instance = MagicMock()
            mock_instance.get_tenant_settings.return_value = {
                'sendgrid_api_key': 'SG.db-api-key',
                'email_from_email': 'db@company.com',
                'email_from_name': 'DB Company',
                'email_reply_to': 'reply@company.com'
            }
            mock_supabase.return_value = mock_instance

            sender = EmailSender(mock_config_sendgrid)

            assert sender.sendgrid_api_key == 'SG.db-api-key'
            assert sender.from_email == 'db@company.com'
            assert sender.from_name == 'DB Company'
            assert sender.reply_to == 'reply@company.com'

    def test_init_handles_db_error_gracefully(self, mock_config_sendgrid):
        """Should fallback to config when database fails."""
        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase:
            mock_supabase.side_effect = Exception("Database error")

            sender = EmailSender(mock_config_sendgrid)

            # Should still work with config values
            assert sender.sendgrid_api_key == "SG.test-api-key-12345"
            assert sender.from_email == "quotes@testcompany.com"


# ==================== SendGrid Tests ====================

class TestSendViaSendGrid:
    """Test SendGrid email sending."""

    @patch('src.utils.email_sender.requests.post')
    def test_send_basic_email_success(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should send basic email via SendGrid."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)
        result = sender.send_email(
            to="customer@example.com",
            subject="Test Subject",
            body_html="<p>Test body</p>"
        )

        assert result is True
        mock_post.assert_called_once()

        # Verify payload structure
        call_args = mock_post.call_args
        payload = call_args.kwargs['json']

        assert payload['personalizations'][0]['to'][0]['email'] == "customer@example.com"
        assert payload['subject'] == "Test Subject"
        assert payload['from']['email'] == "quotes@testcompany.com"

    @patch('src.utils.email_sender.requests.post')
    def test_send_email_with_cc_bcc(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should include CC and BCC recipients."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)
        result = sender.send_email(
            to="customer@example.com",
            subject="Test",
            body_html="<p>Test</p>",
            cc=["cc1@example.com", "cc2@example.com"],
            bcc=["bcc@example.com"]
        )

        assert result is True

        payload = mock_post.call_args.kwargs['json']
        assert len(payload['personalizations'][0]['cc']) == 2
        assert payload['personalizations'][0]['bcc'][0]['email'] == "bcc@example.com"

    @patch('src.utils.email_sender.requests.post')
    def test_send_email_with_plain_text(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should include plain text content when provided."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)
        result = sender.send_email(
            to="customer@example.com",
            subject="Test",
            body_html="<p>HTML body</p>",
            body_text="Plain text body"
        )

        assert result is True

        payload = mock_post.call_args.kwargs['json']
        # Plain text should be first in content array
        assert payload['content'][0]['type'] == "text/plain"
        assert payload['content'][0]['value'] == "Plain text body"
        assert payload['content'][1]['type'] == "text/html"

    @patch('src.utils.email_sender.requests.post')
    def test_send_email_with_attachments(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should include base64 encoded attachments."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)
        pdf_data = b"PDF content here"

        result = sender.send_email(
            to="customer@example.com",
            subject="Invoice",
            body_html="<p>See attached</p>",
            attachments=[{
                'filename': 'invoice.pdf',
                'data': pdf_data,
                'type': 'application/pdf'
            }]
        )

        assert result is True

        payload = mock_post.call_args.kwargs['json']
        assert 'attachments' in payload
        assert len(payload['attachments']) == 1
        assert payload['attachments'][0]['filename'] == 'invoice.pdf'
        assert payload['attachments'][0]['content'] == base64.b64encode(pdf_data).decode()
        assert payload['attachments'][0]['type'] == 'application/pdf'

    @patch('src.utils.email_sender.requests.post')
    def test_send_email_with_reply_to(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should include custom reply-to address."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)
        result = sender.send_email(
            to="customer@example.com",
            subject="Test",
            body_html="<p>Test</p>",
            reply_to="custom-reply@example.com"
        )

        assert result is True

        payload = mock_post.call_args.kwargs['json']
        assert payload['reply_to']['email'] == "custom-reply@example.com"

    @patch('src.utils.email_sender.requests.post')
    def test_send_email_api_error_returns_false(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should return False on API error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)
        result = sender.send_email(
            to="customer@example.com",
            subject="Test",
            body_html="<p>Test</p>"
        )

        assert result is False

    @patch('src.utils.email_sender.requests.post')
    def test_send_email_exception_returns_false(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should return False on network exception."""
        mock_post.side_effect = Exception("Network error")

        sender = EmailSender(mock_config_sendgrid)
        result = sender.send_email(
            to="customer@example.com",
            subject="Test",
            body_html="<p>Test</p>"
        )

        assert result is False


# ==================== SMTP Tests ====================

class TestSendViaSMTP:
    """Test SMTP email sending."""

    @patch('src.utils.email_sender.smtplib.SMTP_SSL')
    def test_send_basic_email_smtp(self, mock_smtp, mock_config_smtp, mock_supabase_tool):
        """Should send email via SMTP when SendGrid unavailable."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = Mock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = Mock(return_value=False)

        sender = EmailSender(mock_config_smtp)
        result = sender.send_email(
            to="customer@example.com",
            subject="Test Subject",
            body_html="<p>Test body</p>"
        )

        assert result is True
        mock_server.login.assert_called_once_with("smtp_user", "smtp_pass")
        mock_server.sendmail.assert_called_once()

    @patch('src.utils.email_sender.smtplib.SMTP_SSL')
    def test_send_smtp_with_cc_bcc(self, mock_smtp, mock_config_smtp, mock_supabase_tool):
        """Should include all recipients in SMTP sendmail."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = Mock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = Mock(return_value=False)

        sender = EmailSender(mock_config_smtp)
        sender.send_email(
            to="customer@example.com",
            subject="Test",
            body_html="<p>Test</p>",
            cc=["cc@example.com"],
            bcc=["bcc@example.com"]
        )

        # Sendmail should receive all recipients
        call_args = mock_server.sendmail.call_args
        recipients = call_args[0][1]  # Second argument is recipient list
        assert "customer@example.com" in recipients
        assert "cc@example.com" in recipients
        assert "bcc@example.com" in recipients

    @patch('src.utils.email_sender.smtplib.SMTP_SSL')
    def test_send_smtp_exception_returns_false(self, mock_smtp, mock_config_smtp, mock_supabase_tool):
        """Should return False on SMTP exception."""
        mock_smtp.side_effect = Exception("SMTP connection failed")

        sender = EmailSender(mock_config_smtp)
        result = sender.send_email(
            to="customer@example.com",
            subject="Test",
            body_html="<p>Test</p>"
        )

        assert result is False


# ==================== Quote Email Tests ====================

class TestSendQuoteEmail:
    """Test quote email functionality."""

    @patch('src.utils.email_sender.requests.post')
    def test_send_quote_email_with_pdf(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should send quote email with PDF attachment."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)
        pdf_data = b"Quote PDF content"

        result = sender.send_quote_email(
            customer_email="customer@example.com",
            customer_name="John Doe",
            quote_pdf_data=pdf_data,
            destination="Cape Town",
            quote_id="QT-12345"
        )

        assert result is True

        payload = mock_post.call_args.kwargs['json']
        assert "Cape Town Travel Quote" in payload['subject']
        # Filename uses destination as-is (with space), not underscored
        assert payload['attachments'][0]['filename'] == "QT-12345_Cape Town_Quote.pdf"

    @patch('src.utils.email_sender.requests.post')
    def test_send_quote_email_cc_consultant(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should CC consultant when provided."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)

        result = sender.send_quote_email(
            customer_email="customer@example.com",
            customer_name="John Doe",
            quote_pdf_data=b"PDF",
            destination="Zanzibar",
            consultant_email="consultant@company.com"
        )

        assert result is True

        payload = mock_post.call_args.kwargs['json']
        assert payload['personalizations'][0]['cc'][0]['email'] == "consultant@company.com"

    @patch('src.utils.email_sender.requests.post')
    def test_send_quote_email_no_pdf(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should send quote email without attachment when no PDF."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)

        result = sender.send_quote_email(
            customer_email="customer@example.com",
            customer_name="John Doe",
            quote_pdf_data=b"",  # Empty PDF
            destination="Maldives"
        )

        assert result is True

        payload = mock_post.call_args.kwargs['json']
        assert 'attachments' not in payload

    @patch('src.utils.email_sender.requests.post')
    def test_send_quote_email_includes_branding(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should include company branding in HTML."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)

        sender.send_quote_email(
            customer_email="customer@example.com",
            customer_name="John Doe",
            quote_pdf_data=b"PDF",
            destination="Safari"
        )

        payload = mock_post.call_args.kwargs['json']
        html_content = payload['content'][-1]['value']  # HTML is last

        assert "#FF6B6B" in html_content  # Primary color
        assert "Test Travel Company" in html_content  # Company name


# ==================== Invoice Email Tests ====================

class TestSendInvoiceEmail:
    """Test invoice email functionality."""

    @patch('src.utils.email_sender.requests.post')
    def test_send_invoice_email_with_pdf(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should send invoice email with PDF attachment."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)

        result = sender.send_invoice_email(
            customer_email="customer@example.com",
            customer_name="Jane Smith",
            invoice_pdf_data=b"Invoice PDF",
            invoice_id="INV-67890",
            total_amount=5000.00,
            currency="ZAR",
            due_date="2026-02-15"
        )

        assert result is True

        payload = mock_post.call_args.kwargs['json']
        assert "Invoice INV-67890" in payload['subject']
        assert payload['attachments'][0]['filename'] == "Invoice_INV-67890.pdf"

    @patch('src.utils.email_sender.requests.post')
    def test_send_invoice_email_with_destination(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should include destination in subject when provided."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)

        sender.send_invoice_email(
            customer_email="customer@example.com",
            customer_name="Jane Smith",
            invoice_pdf_data=b"Invoice PDF",
            invoice_id="INV-67890",
            total_amount=3000.00,
            currency="USD",
            due_date="2026-02-15",
            destination="Bali"
        )

        payload = mock_post.call_args.kwargs['json']
        assert "Bali Trip" in payload['subject']

    @patch('src.utils.email_sender.requests.post')
    def test_send_invoice_email_includes_banking_details(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should include banking details in email HTML."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)

        sender.send_invoice_email(
            customer_email="customer@example.com",
            customer_name="Jane Smith",
            invoice_pdf_data=b"Invoice PDF",
            invoice_id="INV-67890",
            total_amount=5000.00,
            currency="ZAR",
            due_date="2026-02-15"
        )

        payload = mock_post.call_args.kwargs['json']
        html_content = payload['content'][-1]['value']

        assert "Test Bank" in html_content
        assert "1234567890" in html_content  # Account number
        assert "TTC-INV-67890" in html_content  # Payment reference

    @patch('src.utils.email_sender.requests.post')
    def test_send_invoice_email_formats_due_date(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should strip time from ISO datetime due date."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)

        sender.send_invoice_email(
            customer_email="customer@example.com",
            customer_name="Jane Smith",
            invoice_pdf_data=b"Invoice PDF",
            invoice_id="INV-67890",
            total_amount=5000.00,
            currency="ZAR",
            due_date="2026-02-15T00:00:00Z"  # ISO format with time
        )

        payload = mock_post.call_args.kwargs['json']
        html_content = payload['content'][-1]['value']

        # Should show just date, not full ISO string
        assert "2026-02-15" in html_content
        assert "T00:00:00Z" not in html_content


# ==================== Consultant Notification Tests ====================

class TestSendConsultantNotification:
    """Test consultant notification functionality."""

    @patch('src.utils.email_sender.requests.post')
    def test_send_consultant_notification(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should send notification to consultant about new inquiry."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)

        result = sender.send_consultant_notification(
            consultant_email="consultant@company.com",
            customer_name="John Doe",
            customer_email="john@example.com",
            customer_phone="+1234567890",
            inquiry_details="Looking for a Zanzibar trip for 2 adults"
        )

        assert result is True

        payload = mock_post.call_args.kwargs['json']
        assert "New Inquiry: John Doe" in payload['subject']
        assert payload['personalizations'][0]['to'][0]['email'] == "consultant@company.com"

    @patch('src.utils.email_sender.requests.post')
    def test_send_consultant_notification_with_quote_id(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should include quote ID in subject when provided."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)

        sender.send_consultant_notification(
            consultant_email="consultant@company.com",
            customer_name="John Doe",
            customer_email="john@example.com",
            customer_phone=None,
            inquiry_details="Details",
            quote_id="QT-12345"
        )

        payload = mock_post.call_args.kwargs['json']
        assert "Quote QT-12345" in payload['subject']

    @patch('src.utils.email_sender.requests.post')
    def test_send_consultant_notification_no_phone(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should handle missing phone number gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)

        sender.send_consultant_notification(
            consultant_email="consultant@company.com",
            customer_name="John Doe",
            customer_email="john@example.com",
            customer_phone=None,
            inquiry_details="Details"
        )

        payload = mock_post.call_args.kwargs['json']
        html_content = payload['content'][-1]['value']

        # Phone row should not be included
        assert "Phone:" not in html_content


# ==================== Invitation Email Tests ====================

class TestSendInvitationEmail:
    """Test team invitation email functionality."""

    @patch('src.utils.email_sender.requests.post')
    def test_send_invitation_email(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should send invitation email with accept link."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)
        expires = datetime(2026, 2, 1, 12, 0, 0)

        result = sender.send_invitation_email(
            to_email="newuser@example.com",
            to_name="New User",
            invited_by_name="Admin User",
            organization_name="Test Travel Co",
            invitation_token="abc123xyz",
            expires_at=expires
        )

        assert result is True

        payload = mock_post.call_args.kwargs['json']
        assert "invited to join Test Travel Co" in payload['subject']

        html_content = payload['content'][-1]['value']
        assert "abc123xyz" in html_content
        assert "New User" in html_content
        assert "Admin User" in html_content

    @patch('src.utils.email_sender.requests.post')
    def test_send_invitation_email_with_custom_url(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should use custom frontend URL when provided."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)

        sender.send_invitation_email(
            to_email="newuser@example.com",
            to_name="New User",
            invited_by_name="Admin",
            organization_name="Test Co",
            invitation_token="token123",
            expires_at=datetime.now(),
            frontend_url="https://custom.app.com"
        )

        payload = mock_post.call_args.kwargs['json']
        html_content = payload['content'][-1]['value']

        assert "https://custom.app.com/accept-invite?token=token123" in html_content

    @patch('src.utils.email_sender.requests.post')
    def test_send_invitation_email_includes_plain_text(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should include plain text version of invitation."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)

        sender.send_invitation_email(
            to_email="newuser@example.com",
            to_name="New User",
            invited_by_name="Admin",
            organization_name="Test Co",
            invitation_token="token123",
            expires_at=datetime.now()
        )

        payload = mock_post.call_args.kwargs['json']

        # Should have both plain text and HTML
        content_types = [c['type'] for c in payload['content']]
        assert 'text/plain' in content_types
        assert 'text/html' in content_types


# ==================== Error Handling Tests ====================

class TestEmailSenderErrors:
    """Test error handling scenarios."""

    @patch('src.utils.email_sender.requests.post')
    def test_handles_rate_limit_error(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should handle 429 rate limit error."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)
        result = sender.send_email(
            to="customer@example.com",
            subject="Test",
            body_html="<p>Test</p>"
        )

        assert result is False

    @patch('src.utils.email_sender.requests.post')
    def test_handles_server_error(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should handle 500 server error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)
        result = sender.send_email(
            to="customer@example.com",
            subject="Test",
            body_html="<p>Test</p>"
        )

        assert result is False

    @patch('src.utils.email_sender.requests.post')
    def test_handles_timeout(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should handle request timeout."""
        from requests.exceptions import Timeout
        mock_post.side_effect = Timeout("Request timed out")

        sender = EmailSender(mock_config_sendgrid)
        result = sender.send_email(
            to="customer@example.com",
            subject="Test",
            body_html="<p>Test</p>"
        )

        assert result is False


# ==================== NEW TESTS: Initialization Extended ====================

class TestEmailSenderInitExtended:
    """Extended tests for EmailSender initialization and config handling."""

    def test_init_defaults_from_email_to_primary_email(self, mock_supabase_tool):
        """Should use primary_email as fallback when sendgrid_from_email is missing."""
        config = MagicMock()
        config.client_id = "test"
        config.sendgrid_api_key = None
        config.sendgrid_from_email = None
        config.sendgrid_from_name = None
        config.sendgrid_reply_to = None
        config.primary_email = "fallback@company.com"
        config.company_name = "Fallback Co"
        config.smtp_host = "smtp.test.com"
        config.smtp_port = 465
        config.smtp_username = ""
        config.smtp_password = ""

        sender = EmailSender(config)

        assert sender.from_email == "fallback@company.com"
        assert sender.from_name == "Fallback Co"

    def test_init_reply_to_defaults_to_from_email(self, mock_supabase_tool):
        """reply_to should default to from_email when no explicit reply_to."""
        config = MagicMock()
        config.client_id = "test"
        config.sendgrid_api_key = "SG.key"
        config.sendgrid_from_email = "noreply@test.com"
        config.sendgrid_from_name = "Test"
        config.sendgrid_reply_to = None
        config.primary_email = "noreply@test.com"
        config.company_name = "Test"

        sender = EmailSender(config)

        assert sender.reply_to == "noreply@test.com"

    def test_init_partial_db_settings_merge(self):
        """Should merge partial DB settings with config file values."""
        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase:
            mock_instance = MagicMock()
            # DB only has API key, not from_email
            mock_instance.get_tenant_settings.return_value = {
                'sendgrid_api_key': 'SG.from-db',
                'email_from_email': None,
                'email_from_name': None,
                'email_reply_to': None
            }
            mock_supabase.return_value = mock_instance

            config = MagicMock()
            config.client_id = "test"
            config.sendgrid_api_key = "SG.from-config"
            config.sendgrid_from_email = "config@test.com"
            config.sendgrid_from_name = "Config Name"
            config.sendgrid_reply_to = "reply@test.com"
            config.primary_email = "admin@test.com"
            config.company_name = "Test Co"

            sender = EmailSender(config)

            # DB API key wins
            assert sender.sendgrid_api_key == 'SG.from-db'
            # Config from_email wins since DB returned None
            assert sender.from_email == "config@test.com"

    def test_init_use_sendgrid_false_when_no_key(self, mock_supabase_tool):
        """use_sendgrid should be False when there is no API key anywhere."""
        config = MagicMock()
        config.client_id = "test"
        config.sendgrid_api_key = None
        config.sendgrid_from_email = None
        config.sendgrid_from_name = None
        config.sendgrid_reply_to = None
        config.primary_email = "test@test.com"
        config.company_name = "Test"
        config.smtp_host = "smtp.test.com"
        config.smtp_port = 587
        config.smtp_username = "user"
        config.smtp_password = "pass"

        sender = EmailSender(config)

        assert sender.use_sendgrid is False


# ==================== NEW TESTS: send_quote_email ====================

class TestSendQuoteEmailExtended:
    """Extended tests for send_quote_email functionality."""

    @patch('src.utils.email_sender.requests.post')
    def test_quote_email_filename_without_quote_id(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should use customer name in filename when no quote_id."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)

        sender.send_quote_email(
            customer_email="test@example.com",
            customer_name="John Doe",
            quote_pdf_data=b"PDF data",
            destination="Zanzibar"
        )

        payload = mock_post.call_args.kwargs['json']
        assert payload['attachments'][0]['filename'] == "Zanzibar_Quote_John_Doe.pdf"

    @patch('src.utils.email_sender.requests.post')
    def test_quote_email_subject_includes_destination(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Subject should include the destination name."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)

        sender.send_quote_email(
            customer_email="test@example.com",
            customer_name="Jane",
            quote_pdf_data=b"PDF",
            destination="Maldives"
        )

        payload = mock_post.call_args.kwargs['json']
        assert "Maldives" in payload['subject']
        assert "Test Travel Co" in payload['subject']

    @patch('src.utils.email_sender.requests.post')
    def test_quote_email_html_contains_customer_name(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """HTML body should contain the customer's name."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)

        sender.send_quote_email(
            customer_email="test@example.com",
            customer_name="Alice Wonderland",
            quote_pdf_data=b"PDF",
            destination="Kenya"
        )

        payload = mock_post.call_args.kwargs['json']
        html_content = payload['content'][-1]['value']
        assert "Alice Wonderland" in html_content
        assert "Kenya" in html_content

    @patch('src.utils.email_sender.requests.post')
    def test_quote_email_failure_returns_false(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """send_quote_email should return False when SendGrid returns error."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)

        result = sender.send_quote_email(
            customer_email="test@example.com",
            customer_name="Test",
            quote_pdf_data=b"PDF",
            destination="Paris"
        )

        assert result is False

    @patch('src.utils.email_sender.requests.post')
    def test_quote_email_name_with_slash_sanitized(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Customer name with slash should be sanitized in filename."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)

        sender.send_quote_email(
            customer_email="test@example.com",
            customer_name="John/Jane Doe",
            quote_pdf_data=b"PDF",
            destination="Rome"
        )

        payload = mock_post.call_args.kwargs['json']
        filename = payload['attachments'][0]['filename']
        assert "/" not in filename


# ==================== NEW TESTS: SendGrid vs SMTP fallback ====================

class TestSendGridSMTPFallback:
    """Tests for SendGrid vs SMTP fallback behavior."""

    @patch('src.utils.email_sender.smtplib.SMTP_SSL')
    def test_uses_smtp_when_no_sendgrid_key(self, mock_smtp, mock_config_smtp, mock_supabase_tool):
        """Should use SMTP path when use_sendgrid is False."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = Mock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = Mock(return_value=False)

        sender = EmailSender(mock_config_smtp)
        assert sender.use_sendgrid is False

        result = sender.send_email(
            to="test@example.com",
            subject="Test",
            body_html="<p>Test</p>"
        )

        assert result is True
        mock_server.sendmail.assert_called_once()

    @patch('src.utils.email_sender.requests.post')
    def test_uses_sendgrid_when_key_available(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should use SendGrid path when API key is present."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)
        assert sender.use_sendgrid is True

        result = sender.send_email(
            to="test@example.com",
            subject="Test",
            body_html="<p>Test</p>"
        )

        assert result is True
        mock_post.assert_called_once()

    @patch('src.utils.email_sender.smtplib.SMTP_SSL')
    def test_smtp_skips_login_without_credentials(self, mock_smtp, mock_supabase_tool):
        """SMTP should skip login when username/password are empty."""
        config = MagicMock()
        config.client_id = "test"
        config.sendgrid_api_key = None
        config.sendgrid_from_email = None
        config.sendgrid_from_name = None
        config.sendgrid_reply_to = None
        config.primary_email = "test@test.com"
        config.company_name = "Test"
        config.smtp_host = "smtp.test.com"
        config.smtp_port = 465
        config.smtp_username = ""
        config.smtp_password = ""

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = Mock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = Mock(return_value=False)

        sender = EmailSender(config)
        sender.send_email(to="test@example.com", subject="Test", body_html="<p>Test</p>")

        mock_server.login.assert_not_called()

    @patch('src.utils.email_sender.smtplib.SMTP_SSL')
    def test_smtp_with_attachments(self, mock_smtp, mock_config_smtp, mock_supabase_tool):
        """SMTP should handle file attachments."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = Mock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = Mock(return_value=False)

        sender = EmailSender(mock_config_smtp)
        result = sender.send_email(
            to="test@example.com",
            subject="With attachment",
            body_html="<p>See attached</p>",
            attachments=[{
                'filename': 'doc.pdf',
                'data': b'PDF bytes here',
                'type': 'application/pdf'
            }]
        )

        assert result is True
        # Verify sendmail was called (attachment was constructed)
        mock_server.sendmail.assert_called_once()

    @patch('src.utils.email_sender.smtplib.SMTP_SSL')
    def test_smtp_with_custom_from_name(self, mock_smtp, mock_config_smtp, mock_supabase_tool):
        """SMTP should use custom from_name when provided."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = Mock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = Mock(return_value=False)

        sender = EmailSender(mock_config_smtp)
        sender.send_email(
            to="test@example.com",
            subject="Test",
            body_html="<p>Test</p>",
            from_name="Custom Sender"
        )

        # The sendmail call's message should contain "Custom Sender"
        msg_string = mock_server.sendmail.call_args[0][2]
        assert "Custom Sender" in msg_string


# ==================== NEW TESTS: Attachment handling ====================

class TestAttachmentHandling:
    """Tests for attachment handling including PDF bytes."""

    @patch('src.utils.email_sender.requests.post')
    def test_attachment_base64_encoding(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Attachment data should be base64 encoded correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)
        raw_data = b'\x00\x01\x02\x03\xff\xfe\xfd'

        sender.send_email(
            to="test@example.com",
            subject="Binary attachment",
            body_html="<p>Test</p>",
            attachments=[{
                'filename': 'data.bin',
                'data': raw_data,
                'type': 'application/octet-stream'
            }]
        )

        payload = mock_post.call_args.kwargs['json']
        encoded = payload['attachments'][0]['content']
        # Verify roundtrip
        assert base64.b64decode(encoded) == raw_data

    @patch('src.utils.email_sender.requests.post')
    def test_multiple_attachments(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should handle multiple attachments in a single email."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)

        sender.send_email(
            to="test@example.com",
            subject="Multi-attach",
            body_html="<p>Test</p>",
            attachments=[
                {'filename': 'quote.pdf', 'data': b'pdf1', 'type': 'application/pdf'},
                {'filename': 'itinerary.pdf', 'data': b'pdf2', 'type': 'application/pdf'},
                {'filename': 'photo.jpg', 'data': b'jpg1', 'type': 'image/jpeg'}
            ]
        )

        payload = mock_post.call_args.kwargs['json']
        assert len(payload['attachments']) == 3
        assert payload['attachments'][0]['filename'] == 'quote.pdf'
        assert payload['attachments'][2]['filename'] == 'photo.jpg'

    @patch('src.utils.email_sender.requests.post')
    def test_attachment_default_type(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Attachment without explicit type should default to application/octet-stream."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)

        sender.send_email(
            to="test@example.com",
            subject="Test",
            body_html="<p>Test</p>",
            attachments=[{
                'filename': 'unknown.dat',
                'data': b'binary data'
                # No 'type' key
            }]
        )

        payload = mock_post.call_args.kwargs['json']
        assert payload['attachments'][0]['type'] == 'application/octet-stream'

    @patch('src.utils.email_sender.requests.post')
    def test_attachment_disposition_is_attachment(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """All SendGrid attachments should have disposition='attachment'."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)

        sender.send_email(
            to="test@example.com",
            subject="Test",
            body_html="<p>Test</p>",
            attachments=[{'filename': 'file.pdf', 'data': b'data', 'type': 'application/pdf'}]
        )

        payload = mock_post.call_args.kwargs['json']
        assert payload['attachments'][0]['disposition'] == 'attachment'


# ==================== NEW TESTS: Circuit Breaker Integration ====================

class TestCircuitBreakerIntegration:
    """Tests for SendGrid circuit breaker behavior."""

    @patch('src.utils.email_sender.sendgrid_circuit')
    @patch('src.utils.email_sender.requests.post')
    def test_circuit_open_skips_sending(self, mock_post, mock_circuit, mock_config_sendgrid, mock_supabase_tool):
        """Should skip sending when circuit breaker is open."""
        mock_circuit.can_execute.return_value = False

        sender = EmailSender(mock_config_sendgrid)
        result = sender._send_via_sendgrid(
            to="test@example.com",
            subject="Test",
            body_html="<p>Test</p>"
        )

        assert result is False
        mock_post.assert_not_called()

    @patch('src.utils.email_sender.sendgrid_circuit')
    @patch('src.utils.email_sender.requests.post')
    def test_circuit_records_success_on_202(self, mock_post, mock_circuit, mock_config_sendgrid, mock_supabase_tool):
        """Should record success with circuit breaker on successful send."""
        mock_circuit.can_execute.return_value = True
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)
        sender._send_via_sendgrid(
            to="test@example.com",
            subject="Test",
            body_html="<p>Test</p>"
        )

        mock_circuit.record_success.assert_called_once()

    @patch('src.utils.email_sender.sendgrid_circuit')
    @patch('src.utils.email_sender.requests.post')
    def test_circuit_records_failure_on_error(self, mock_post, mock_circuit, mock_config_sendgrid, mock_supabase_tool):
        """Should record failure with circuit breaker on API error."""
        mock_circuit.can_execute.return_value = True
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Server error"
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)
        sender._send_via_sendgrid(
            to="test@example.com",
            subject="Test",
            body_html="<p>Test</p>"
        )

        mock_circuit.record_failure.assert_called_once()

    @patch('src.utils.email_sender.sendgrid_circuit')
    @patch('src.utils.email_sender.requests.post')
    def test_circuit_records_failure_on_exception(self, mock_post, mock_circuit, mock_config_sendgrid, mock_supabase_tool):
        """Should record failure with circuit breaker on network exception."""
        mock_circuit.can_execute.return_value = True
        mock_post.side_effect = Exception("Connection refused")

        sender = EmailSender(mock_config_sendgrid)
        sender._send_via_sendgrid(
            to="test@example.com",
            subject="Test",
            body_html="<p>Test</p>"
        )

        mock_circuit.record_failure.assert_called_once()


# ==================== NEW TESTS: Template Variable Substitution ====================

class TestTemplateRendering:
    """Tests for email template HTML construction and variable substitution."""

    @patch('src.utils.email_sender.requests.post')
    def test_quote_email_uses_config_colors(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Quote email HTML should use the config's primary and secondary colors."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)
        sender.send_quote_email(
            customer_email="test@example.com",
            customer_name="Test",
            quote_pdf_data=b"PDF",
            destination="Safari"
        )

        html = mock_post.call_args.kwargs['json']['content'][-1]['value']
        assert "#FF6B6B" in html
        assert "#4ECDC4" in html

    @patch('src.utils.email_sender.requests.post')
    def test_invoice_email_includes_amount_formatted(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Invoice email should format the amount with commas and decimals."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)
        sender.send_invoice_email(
            customer_email="test@example.com",
            customer_name="Test",
            invoice_pdf_data=b"PDF",
            invoice_id="INV-001",
            total_amount=12500.50,
            currency="ZAR",
            due_date="2026-03-15"
        )

        html = mock_post.call_args.kwargs['json']['content'][-1]['value']
        assert "ZAR 12,500.50" in html

    @patch('src.utils.email_sender.requests.post')
    def test_invoice_email_without_banking_details(self, mock_post, mock_supabase_tool):
        """Invoice email should omit banking section when no bank_name configured."""
        config = MagicMock()
        config.client_id = "test"
        config.sendgrid_api_key = "SG.key"
        config.sendgrid_from_email = "from@test.com"
        config.sendgrid_from_name = "Test"
        config.sendgrid_reply_to = "reply@test.com"
        config.primary_email = "from@test.com"
        config.company_name = "Test"
        config.primary_color = "#333"
        config.secondary_color = "#666"
        config.email_signature = "Thanks"
        config.bank_name = ""
        config.bank_account_name = ""
        config.bank_account_number = ""
        config.bank_branch_code = ""
        config.payment_reference_prefix = "INV"

        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(config)
        sender.send_invoice_email(
            customer_email="test@example.com",
            customer_name="Test",
            invoice_pdf_data=b"PDF",
            invoice_id="INV-001",
            total_amount=100.00,
            currency="USD",
            due_date="2026-03-15"
        )

        html = mock_post.call_args.kwargs['json']['content'][-1]['value']
        assert "Payment Details" not in html

    @patch('src.utils.email_sender.requests.post')
    def test_invitation_email_expiry_datetime_format(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Invitation email should format expiry datetime nicely."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)
        expires = datetime(2026, 6, 15, 14, 30, 0)

        sender.send_invitation_email(
            to_email="test@example.com",
            to_name="User",
            invited_by_name="Admin",
            organization_name="TestOrg",
            invitation_token="tok123",
            expires_at=expires
        )

        html = mock_post.call_args.kwargs['json']['content'][-1]['value']
        assert "June 15, 2026" in html

    @patch('src.utils.email_sender.requests.post')
    def test_invitation_email_string_expiry(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Invitation email should handle string expiry without strftime."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)

        sender.send_invitation_email(
            to_email="test@example.com",
            to_name="User",
            invited_by_name="Admin",
            organization_name="TestOrg",
            invitation_token="tok",
            expires_at="2026-06-15 14:30:00"  # String, not datetime
        )

        html = mock_post.call_args.kwargs['json']['content'][-1]['value']
        assert "2026-06-15 14:30:00" in html


# ==================== NEW TESTS: Error Handling Extended ====================

class TestEmailSenderErrorsExtended:
    """Extended error handling tests for each send method."""

    @patch('src.utils.email_sender.requests.post')
    def test_sendgrid_403_forbidden(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should handle 403 Forbidden response."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)
        result = sender.send_email(to="test@example.com", subject="Test", body_html="<p>Test</p>")
        assert result is False

    @patch('src.utils.email_sender.requests.post')
    def test_sendgrid_200_is_success(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """200 should be accepted as success alongside 201 and 202."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)
        result = sender.send_email(to="test@example.com", subject="Test", body_html="<p>Test</p>")
        assert result is True

    @patch('src.utils.email_sender.requests.post')
    def test_sendgrid_201_is_success(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """201 Created should be accepted as success."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)
        result = sender.send_email(to="test@example.com", subject="Test", body_html="<p>Test</p>")
        assert result is True

    @patch('src.utils.email_sender.requests.post')
    def test_send_email_connection_error(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should return False on ConnectionError."""
        from requests.exceptions import ConnectionError as ReqConnectionError
        mock_post.side_effect = ReqConnectionError("Connection refused")

        sender = EmailSender(mock_config_sendgrid)
        result = sender.send_email(to="test@example.com", subject="Test", body_html="<p>Test</p>")
        assert result is False

    @patch('src.utils.email_sender.smtplib.SMTP_SSL')
    def test_smtp_authentication_error(self, mock_smtp, mock_config_smtp, mock_supabase_tool):
        """Should return False on SMTP authentication failure."""
        mock_server = MagicMock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Authentication failed")
        mock_smtp.return_value.__enter__ = Mock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = Mock(return_value=False)

        sender = EmailSender(mock_config_smtp)
        result = sender.send_email(to="test@example.com", subject="Test", body_html="<p>Test</p>")
        assert result is False

    @patch('src.utils.email_sender.smtplib.SMTP_SSL')
    def test_smtp_connection_refused(self, mock_smtp, mock_config_smtp, mock_supabase_tool):
        """Should return False when SMTP server connection is refused."""
        mock_smtp.side_effect = ConnectionRefusedError("Connection refused")

        sender = EmailSender(mock_config_smtp)
        result = sender.send_email(to="test@example.com", subject="Test", body_html="<p>Test</p>")
        assert result is False


# ==================== NEW TESTS: Edge Cases ====================

class TestEmailSenderEdgeCases:
    """Edge cases: empty recipients, special characters, large payloads."""

    @patch('src.utils.email_sender.requests.post')
    def test_send_to_email_with_plus_addressing(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should handle plus-addressed emails correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)
        result = sender.send_email(
            to="user+tag@example.com",
            subject="Test",
            body_html="<p>Test</p>"
        )

        assert result is True
        payload = mock_post.call_args.kwargs['json']
        assert payload['personalizations'][0]['to'][0]['email'] == "user+tag@example.com"

    @patch('src.utils.email_sender.requests.post')
    def test_send_email_with_unicode_subject(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Should handle Unicode characters in subject."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)
        result = sender.send_email(
            to="test@example.com",
            subject="Your Quote for Curacao (R25,000)",
            body_html="<p>Test</p>"
        )

        assert result is True

    @patch('src.utils.email_sender.requests.post')
    def test_send_email_with_empty_cc_list(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Empty CC list should not add cc to personalizations."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)
        sender.send_email(
            to="test@example.com",
            subject="Test",
            body_html="<p>Test</p>",
            cc=[],
            bcc=[]
        )

        payload = mock_post.call_args.kwargs['json']
        # Empty lists are falsy, so cc/bcc should not be in personalizations
        assert 'cc' not in payload['personalizations'][0]
        assert 'bcc' not in payload['personalizations'][0]

    @patch('src.utils.email_sender.requests.post')
    def test_no_attachments_key_when_none(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Payload should not have 'attachments' key when attachments is None."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)
        sender.send_email(
            to="test@example.com",
            subject="No attachments",
            body_html="<p>Test</p>",
            attachments=None
        )

        payload = mock_post.call_args.kwargs['json']
        assert 'attachments' not in payload

    @patch('src.utils.email_sender.requests.post')
    def test_sendgrid_api_url_constant(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """EmailSender should use the correct SendGrid API URL."""
        assert EmailSender.SENDGRID_API_URL == "https://api.sendgrid.com/v3/mail/send"

    @patch('src.utils.email_sender.requests.post')
    def test_invoice_email_no_pdf_data(self, mock_post, mock_config_sendgrid, mock_supabase_tool):
        """Invoice email with empty PDF data should not include attachments."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sender = EmailSender(mock_config_sendgrid)
        sender.send_invoice_email(
            customer_email="test@example.com",
            customer_name="Test",
            invoice_pdf_data=b"",
            invoice_id="INV-001",
            total_amount=100.00,
            currency="USD",
            due_date="2026-01-01"
        )

        payload = mock_post.call_args.kwargs['json']
        assert 'attachments' not in payload


# We need smtplib import for SMTPAuthenticationError
import smtplib


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
