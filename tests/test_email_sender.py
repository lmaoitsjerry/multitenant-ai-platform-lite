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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
