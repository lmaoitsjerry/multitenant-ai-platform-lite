"""
Email Sender - Multi-Tenant Version with SendGrid Support

Uses requests library directly for SendGrid API (more reliable than sendgrid-python).
Each tenant can have their own SendGrid API key (subuser) for isolation.
"""

import smtplib
import base64
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class EmailSender:
    """Send emails using client-specific SendGrid or SMTP configuration"""

    SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"

    def __init__(self, config):
        """
        Initialize email sender with client configuration
        
        Args:
            config: ClientConfig instance
        """
        self.config = config
        self.sendgrid_api_key = getattr(config, 'sendgrid_api_key', None)
        self.use_sendgrid = bool(self.sendgrid_api_key)
        
        # Email settings
        self.from_email = getattr(config, 'sendgrid_from_email', None) or getattr(config, 'primary_email', 'noreply@example.com')
        self.from_name = getattr(config, 'sendgrid_from_name', None) or getattr(config, 'company_name', 'Travel Agency')
        self.reply_to = getattr(config, 'sendgrid_reply_to', None) or self.from_email
        
        # SMTP fallback settings
        self.smtp_host = getattr(config, 'smtp_host', 'smtp.gmail.com')
        self.smtp_port = getattr(config, 'smtp_port', 465)
        self.smtp_username = getattr(config, 'smtp_username', '')
        self.smtp_password = getattr(config, 'smtp_password', '')
        
        logger.info(f"Email sender initialized for {config.client_id} (SendGrid: {self.use_sendgrid})")

    def send_email(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> bool:
        """
        Send an email via SendGrid or SMTP
        
        Args:
            to: Recipient email address
            subject: Email subject
            body_html: HTML email body
            body_text: Plain text email body (optional)
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)
            attachments: List of attachments [{'filename': 'file.pdf', 'data': bytes, 'type': 'application/pdf'}]
            from_name: Custom from name (defaults to company name)
            reply_to: Reply-to address (optional)
            
        Returns:
            True if sent successfully, False otherwise
        """
        if self.use_sendgrid:
            return self._send_via_sendgrid(
                to=to,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
                cc=cc,
                bcc=bcc,
                attachments=attachments,
                from_name=from_name,
                reply_to=reply_to
            )
        else:
            return self._send_via_smtp(
                to=to,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
                cc=cc,
                bcc=bcc,
                attachments=attachments,
                from_name=from_name
            )

    def _send_via_sendgrid(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> bool:
        """Send email via SendGrid API using requests"""
        try:
            # Build personalizations
            personalization = {"to": [{"email": to}]}
            
            if cc:
                personalization["cc"] = [{"email": email} for email in cc]
            if bcc:
                personalization["bcc"] = [{"email": email} for email in bcc]
            
            # Build payload
            payload = {
                "personalizations": [personalization],
                "from": {
                    "email": self.from_email,
                    "name": from_name or self.from_name
                },
                "subject": subject,
                "content": [{"type": "text/html", "value": body_html}]
            }
            
            # Add plain text if provided
            if body_text:
                payload["content"].insert(0, {"type": "text/plain", "value": body_text})
            
            # Add reply-to
            if reply_to or self.reply_to:
                payload["reply_to"] = {"email": reply_to or self.reply_to}
            
            # Add attachments
            if attachments:
                payload["attachments"] = []
                for att in attachments:
                    payload["attachments"].append({
                        "content": base64.b64encode(att['data']).decode(),
                        "filename": att['filename'],
                        "type": att.get('type', 'application/octet-stream'),
                        "disposition": "attachment"
                    })
            
            # Send request
            headers = {
                "Authorization": f"Bearer {self.sendgrid_api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                self.SENDGRID_API_URL,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"✅ Email sent via SendGrid to {to}: {subject}")
                return True
            else:
                logger.error(f"SendGrid error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ SendGrid send failed to {to}: {e}")
            return False

    def _send_via_smtp(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        from_name: Optional[str] = None
    ) -> bool:
        """Send email via SMTP (fallback)"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{from_name or self.from_name} <{self.from_email}>"
            msg['To'] = to
            
            if cc:
                msg['Cc'] = ', '.join(cc)
            if bcc:
                msg['Bcc'] = ', '.join(bcc)
            
            # Add plain text version if provided
            if body_text:
                msg.attach(MIMEText(body_text, 'plain'))
            
            # Add HTML version
            msg.attach(MIMEText(body_html, 'html'))
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    part = MIMEApplication(
                        attachment['data'], 
                        Name=attachment['filename']
                    )
                    part['Content-Disposition'] = f'attachment; filename="{attachment["filename"]}"'
                    msg.attach(part)
            
            # Build recipient list
            recipients = [to]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)
            
            # Send email
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.from_email, recipients, msg.as_string())
            
            logger.info(f"✅ Email sent via SMTP to {to}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"❌ SMTP send failed to {to}: {e}")
            return False

    def send_quote_email(
        self,
        customer_email: str,
        customer_name: str,
        quote_pdf_data: bytes,
        destination: str,
        quote_id: str = "",
        consultant_email: Optional[str] = None
    ) -> bool:
        """
        Send quote email with PDF attachment
        """
        subject = f"Your {destination} Travel Quote from {self.from_name}"
        
        primary_color = getattr(self.config, 'primary_color', '#FF6B6B')
        secondary_color = getattr(self.config, 'secondary_color', '#4ECDC4')
        company_name = getattr(self.config, 'company_name', 'Travel Agency')
        email_signature = getattr(self.config, 'email_signature', f'Best regards,\nThe {company_name} Team')
        
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, {primary_color}, {secondary_color}); color: white; padding: 30px; text-align: center;">
                <h1 style="margin: 0;">Your {destination} Travel Quote</h1>
            </div>
            
            <div style="padding: 30px;">
                <p>Dear {customer_name},</p>
                
                <p>Thank you for your interest in traveling to <strong>{destination}</strong>!</p>
                
                <p>Please find attached your personalized travel quote. We've carefully selected the best 
                accommodation options based on your requirements.</p>
                
                <div style="margin: 30px 0; padding: 20px; background-color: #f8f9fa; border-left: 4px solid {primary_color};">
                    <p style="margin: 0;"><strong>Ready to book?</strong></p>
                    <p style="margin: 5px 0 0 0;">Simply reply to this email or call us to secure your dream vacation!</p>
                </div>
                
                <p>If you have any questions or would like to make changes to your quote, 
                please don't hesitate to reach out.</p>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0;">
                    {email_signature.replace(chr(10), '<br>')}
                </div>
            </div>
            
            <div style="background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666;">
                <p style="margin: 0;">&copy; {company_name}. All rights reserved.</p>
                <p style="margin: 5px 0 0 0;">{self.from_email}</p>
            </div>
        </body>
        </html>
        """
        
        # Build filename
        safe_name = customer_name.replace(" ", "_").replace("/", "-")
        filename = f"{destination}_Quote_{safe_name}.pdf"
        if quote_id:
            filename = f"{quote_id}_{destination}_Quote.pdf"
        
        # CC list
        cc_list = [consultant_email] if consultant_email else None
        
        # Only attach PDF if we have actual data
        attachments = None
        if quote_pdf_data and len(quote_pdf_data) > 0:
            attachments = [{
                'filename': filename,
                'data': quote_pdf_data,
                'type': 'application/pdf'
            }]
        
        return self.send_email(
            to=customer_email,
            subject=subject,
            body_html=body_html,
            cc=cc_list,
            attachments=attachments
        )

    def send_consultant_notification(
        self,
        consultant_email: str,
        customer_name: str,
        customer_email: str,
        customer_phone: Optional[str],
        inquiry_details: str,
        quote_id: Optional[str] = None
    ) -> bool:
        """
        Send notification to consultant about new inquiry
        """
        subject = f"🔔 New Inquiry: {customer_name}"
        if quote_id:
            subject = f"🔔 Quote {quote_id}: {customer_name}"
        
        primary_color = getattr(self.config, 'primary_color', '#FF6B6B')
        company_name = getattr(self.config, 'company_name', 'Travel Agency')
        
        phone_row = f"""
            <tr>
                <td style="padding: 8px; font-weight: bold; color: #666;">Phone:</td>
                <td style="padding: 8px;">{customer_phone}</td>
            </tr>
        """ if customer_phone else ""
        
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto;">
                <div style="background-color: {primary_color}; color: white; padding: 20px;">
                    <h2 style="margin: 0;">New Customer Inquiry</h2>
                </div>
                
                <div style="padding: 20px; background-color: #f8f9fa;">
                    <h3 style="margin-top: 0; color: {primary_color};">Customer Information</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; font-weight: bold; color: #666;">Name:</td>
                            <td style="padding: 8px;">{customer_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold; color: #666;">Email:</td>
                            <td style="padding: 8px;"><a href="mailto:{customer_email}">{customer_email}</a></td>
                        </tr>
                        {phone_row}
                        {"<tr><td style='padding: 8px; font-weight: bold; color: #666;'>Quote ID:</td><td style='padding: 8px;'>" + quote_id + "</td></tr>" if quote_id else ""}
                    </table>
                    
                    <h3 style="color: {primary_color};">Inquiry Details</h3>
                    <p style="background-color: white; padding: 15px; border-radius: 5px;">{inquiry_details}</p>
                </div>
                
                <div style="padding: 20px; text-align: center;">
                    <p>Please follow up with this customer at your earliest convenience.</p>
                    <a href="mailto:{customer_email}?subject=Re: Your {company_name} Quote" 
                       style="display: inline-block; background-color: {primary_color}; color: white; 
                              padding: 12px 30px; text-decoration: none; border-radius: 5px;">
                        Reply to Customer
                    </a>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(
            to=consultant_email,
            subject=subject,
            body_html=body_html
        )

    def send_invoice_email(
        self,
        customer_email: str,
        customer_name: str,
        invoice_pdf_data: bytes,
        invoice_id: str,
        total_amount: float,
        currency: str,
        due_date: str,
        destination: Optional[str] = None,
        consultant_email: Optional[str] = None
    ) -> bool:
        """
        Send invoice email with PDF attachment
        """
        subject = f"Invoice {invoice_id} from {self.from_name}"
        if destination:
            subject = f"Invoice {invoice_id} - {destination} Trip from {self.from_name}"
        
        primary_color = getattr(self.config, 'primary_color', '#2E86AB')
        secondary_color = getattr(self.config, 'secondary_color', '#A23B72')
        company_name = getattr(self.config, 'company_name', 'Travel Agency')
        email_signature = getattr(self.config, 'email_signature', f'Best regards,\nThe {company_name} Team')
        
        # Banking details
        bank_name = getattr(self.config, 'bank_name', '')
        account_name = getattr(self.config, 'bank_account_name', '')
        account_number = getattr(self.config, 'bank_account_number', '')
        branch_code = getattr(self.config, 'bank_branch_code', '')
        ref_prefix = getattr(self.config, 'payment_reference_prefix', 'INV')
        
        # Format due date
        if due_date and 'T' in str(due_date):
            due_date = str(due_date).split('T')[0]
        
        # Banking section HTML
        banking_html = ""
        if bank_name and account_number:
            banking_html = f"""
            <div style="margin: 25px 0; padding: 20px; background-color: {secondary_color}; color: white; border-radius: 8px;">
                <h3 style="margin: 0 0 15px 0; font-size: 16px;">Payment Details</h3>
                <table style="width: 100%; color: white;">
                    <tr><td style="padding: 3px 0;"><strong>Bank:</strong> {bank_name}</td></tr>
                    <tr><td style="padding: 3px 0;"><strong>Account Name:</strong> {account_name}</td></tr>
                    <tr><td style="padding: 3px 0;"><strong>Account Number:</strong> {account_number}</td></tr>
                    {"<tr><td style='padding: 3px 0;'><strong>Branch Code:</strong> " + branch_code + "</td></tr>" if branch_code else ""}
                    <tr><td style="padding: 8px 0 0 0;"><strong>Payment Reference:</strong> {ref_prefix}-{invoice_id}</td></tr>
                </table>
            </div>
            """
        
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, {primary_color}, {secondary_color}); color: white; padding: 30px; text-align: center;">
                <h1 style="margin: 0; font-size: 28px;">Invoice</h1>
                <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">{invoice_id}</p>
            </div>
            
            <div style="padding: 30px;">
                <p>Dear {customer_name},</p>
                <p>Please find attached your invoice{f' for your {destination} trip' if destination else ''}.</p>
                
                <div style="margin: 25px 0; padding: 20px; background-color: #f8f9fa; border-left: 4px solid {primary_color};">
                    <table style="width: 100%;">
                        <tr>
                            <td style="padding: 5px 0;"><strong>Invoice Number:</strong></td>
                            <td style="text-align: right;">{invoice_id}</td>
                        </tr>
                        <tr>
                            <td style="padding: 5px 0;"><strong>Amount Due:</strong></td>
                            <td style="text-align: right; font-size: 18px; color: {primary_color};"><strong>{currency} {total_amount:,.2f}</strong></td>
                        </tr>
                        <tr>
                            <td style="padding: 5px 0;"><strong>Due Date:</strong></td>
                            <td style="text-align: right;">{due_date}</td>
                        </tr>
                    </table>
                </div>
                
                {banking_html}
                
                <p>Please ensure payment is made by the due date. Use <strong>{ref_prefix}-{invoice_id}</strong> as your payment reference.</p>
                <p>If you have any questions, please don't hesitate to contact us.</p>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0;">
                    {email_signature.replace(chr(10), '<br>')}
                </div>
            </div>
            
            <div style="background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666;">
                <p style="margin: 0;">&copy; {company_name}. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        attachments = None
        if invoice_pdf_data and len(invoice_pdf_data) > 0:
            attachments = [{
                'filename': f"Invoice_{invoice_id}.pdf",
                'data': invoice_pdf_data,
                'type': 'application/pdf'
            }]
        
        return self.send_email(
            to=customer_email,
            subject=subject,
            body_html=body_html,
            cc=[consultant_email] if consultant_email else None,
            attachments=attachments
        )

    def send_invitation_email(
        self,
        to_email: str,
        to_name: str,
        invited_by_name: str,
        organization_name: str,
        invitation_token: str,
        expires_at,
        frontend_url: Optional[str] = None
    ) -> bool:
        """
        Send invitation email to new team member

        Args:
            to_email: Recipient email
            to_name: Recipient name
            invited_by_name: Name of person who sent the invite
            organization_name: Organization/tenant name
            invitation_token: Secure token for accepting invite
            expires_at: Expiration datetime
            frontend_url: Base URL for frontend (optional)
        """
        # Build invitation URL
        base_url = frontend_url or getattr(self.config, 'frontend_url', 'http://localhost:5173')
        invitation_url = f"{base_url}/accept-invite?token={invitation_token}"

        # Format expiry
        if hasattr(expires_at, 'strftime'):
            expiry_str = expires_at.strftime('%B %d, %Y at %I:%M %p')
        else:
            expiry_str = str(expires_at)

        subject = f"You're invited to join {organization_name}"

        primary_color = getattr(self.config, 'primary_color', '#2E86AB')
        secondary_color = getattr(self.config, 'secondary_color', '#4ECDC4')
        company_name = getattr(self.config, 'company_name', organization_name)

        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto; padding: 0;">
            <div style="background: linear-gradient(135deg, {primary_color}, {secondary_color}); color: white; padding: 40px 30px; text-align: center;">
                <h1 style="margin: 0; font-size: 28px;">You're Invited!</h1>
                <p style="margin: 15px 0 0 0; font-size: 16px; opacity: 0.9;">Join {organization_name}</p>
            </div>

            <div style="padding: 30px;">
                <p style="font-size: 16px;">Hello {to_name},</p>

                <p><strong>{invited_by_name}</strong> has invited you to join the <strong>{organization_name}</strong> team.</p>

                <p>Click the button below to accept the invitation and set up your account:</p>

                <div style="text-align: center; margin: 35px 0;">
                    <a href="{invitation_url}"
                       style="display: inline-block; background-color: {primary_color}; color: white;
                              padding: 15px 40px; text-decoration: none; border-radius: 6px;
                              font-size: 16px; font-weight: bold;">
                        Accept Invitation
                    </a>
                </div>

                <div style="margin: 30px 0; padding: 20px; background-color: #fff3cd; border-left: 4px solid #ffc107; border-radius: 4px;">
                    <p style="margin: 0; font-size: 14px;">
                        <strong>Note:</strong> This invitation expires on <strong>{expiry_str}</strong>.
                    </p>
                </div>

                <p style="font-size: 14px; color: #666;">
                    If you didn't expect this invitation, you can safely ignore this email.
                </p>

                <p style="font-size: 13px; color: #999; margin-top: 25px;">
                    If the button doesn't work, copy and paste this link into your browser:<br>
                    <a href="{invitation_url}" style="color: {primary_color}; word-break: break-all;">{invitation_url}</a>
                </p>
            </div>

            <div style="background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666;">
                <p style="margin: 0;">&copy; {company_name}. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        body_text = f"""
Hello {to_name},

{invited_by_name} has invited you to join the {organization_name} team.

Click the link below to accept the invitation and set up your account:
{invitation_url}

Note: This invitation expires on {expiry_str}.

If you didn't expect this invitation, you can safely ignore this email.
        """

        return self.send_email(
            to=to_email,
            subject=subject,
            body_html=body_html,
            body_text=body_text
        )