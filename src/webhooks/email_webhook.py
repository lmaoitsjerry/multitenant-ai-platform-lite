"""
Email Webhook - Multi-Tenant Inbound Email Processing

Receives emails from SendGrid Inbound Parse and routes them to the correct tenant.

Setup Options:
1. Single domain routing: inbound@mail.zorahai.com with tenant ID in subject/headers
2. Subdomain routing: {tenant}@inbound.zorahai.com
3. Email forwarding: Client forwards to {tenant}@inbound.zorahai.com

Usage:
    Add these routes to your FastAPI app:
    
    from src.webhooks.email_webhook import router as email_webhook_router
    app.include_router(email_webhook_router, prefix="/webhooks")
"""

import json
import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel

from config.loader import ClientConfig, get_config

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Webhooks"])


class ParsedEmail(BaseModel):
    """Parsed email data"""
    tenant_id: str
    from_email: str
    from_name: Optional[str] = None
    to_email: str
    subject: str
    body_text: str
    body_html: Optional[str] = None
    attachments: list = []
    headers: Dict[str, str] = {}
    received_at: str


def extract_tenant_from_email(to_email: str, headers: Dict[str, str] = None) -> Optional[str]:
    """
    Extract tenant ID from email address or headers
    
    Supports multiple routing strategies:
    1. Subdomain: africastay@inbound.zorahai.com -> africastay
    2. Plus addressing: quotes+africastay@zorahai.com -> africastay
    3. Custom header: X-Tenant-ID header
    4. Envelope-to header analysis
    """
    to_email = to_email.lower().strip()
    
    # Strategy 1: Subdomain routing (tenant@inbound.domain.com)
    # Extract the local part before @
    local_part = to_email.split('@')[0] if '@' in to_email else to_email
    
    # Check if local part is a known tenant
    # Common patterns to skip
    skip_patterns = ['quotes', 'sales', 'info', 'support', 'inbound', 'mail']
    if local_part not in skip_patterns:
        # Try loading config to verify it's a valid tenant
        try:
            config = get_config(local_part)
            if config:
                return local_part
        except:
            pass
    
    # Strategy 2: Plus addressing (quotes+africastay@domain.com)
    if '+' in local_part:
        tenant = local_part.split('+')[1]
        try:
            config = get_config(tenant)
            if config:
                return tenant
        except:
            pass
    
    # Strategy 3: Check X-Tenant-ID header
    if headers:
        tenant_header = headers.get('x-tenant-id') or headers.get('X-Tenant-ID')
        if tenant_header:
            try:
                config = get_config(tenant_header)
                if config:
                    return tenant_header
            except:
                pass
    
    # Strategy 4: Check for tenant in subject line [TENANT:africastay]
    # This would be checked in the main handler
    
    return None


def extract_tenant_from_subject(subject: str) -> Optional[str]:
    """Extract tenant ID from subject line pattern [TENANT:xxx]"""
    match = re.search(r'\[TENANT:(\w+)\]', subject, re.IGNORECASE)
    if match:
        tenant = match.group(1).lower()
        try:
            config = get_config(tenant)
            if config:
                return tenant
        except:
            pass
    return None


@router.post("/email/inbound")
async def receive_inbound_email(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Receive inbound email from SendGrid Inbound Parse
    
    SendGrid sends multipart/form-data with these fields:
    - from: Sender email
    - to: Recipient email
    - subject: Email subject
    - text: Plain text body
    - html: HTML body
    - envelope: JSON with routing info
    - headers: Email headers
    - attachments: Number of attachments
    - attachment1, attachment2, etc.: Actual attachments
    """
    try:
        # Parse form data
        form = await request.form()
        
        # Extract basic fields
        from_email = form.get('from', '')
        to_email = form.get('to', '')
        subject = form.get('subject', '')
        body_text = form.get('text', '')
        body_html = form.get('html', '')
        
        # Parse envelope for additional routing info
        envelope_str = form.get('envelope', '{}')
        try:
            envelope = json.loads(envelope_str)
        except:
            envelope = {}
        
        # Parse headers
        headers_str = form.get('headers', '')
        headers = {}
        for line in headers_str.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip().lower()] = value.strip()
        
        # Extract sender name from "Name <email>" format
        from_name = None
        if '<' in from_email and '>' in from_email:
            from_name = from_email.split('<')[0].strip().strip('"')
            from_email = from_email.split('<')[1].split('>')[0].strip()
        
        # Determine tenant
        tenant_id = (
            extract_tenant_from_email(to_email, headers) or
            extract_tenant_from_subject(subject) or
            extract_tenant_from_email(envelope.get('to', [''])[0] if envelope.get('to') else '', headers)
        )
        
        if not tenant_id:
            logger.warning(f"Could not determine tenant for email to: {to_email}")
            # Default tenant or reject
            return {
                "success": False,
                "error": "Could not determine tenant",
                "to_email": to_email
            }
        
        logger.info(f"📧 Inbound email for tenant '{tenant_id}' from {from_email}: {subject}")

        # Trigger notification for new email
        try:
            config = get_config(tenant_id)
            from src.api.notifications_routes import NotificationService
            notification_service = NotificationService(config)
            notification_service.notify_email_received(
                sender_email=from_email,
                subject=subject
            )
        except Exception as e:
            logger.warning(f"Failed to send email notification: {e}")

        # Parse attachments
        attachments = []
        num_attachments = int(form.get('attachments', 0))
        for i in range(1, num_attachments + 1):
            attachment = form.get(f'attachment{i}')
            if attachment:
                attachments.append({
                    'filename': attachment.filename,
                    'content_type': attachment.content_type,
                    'size': attachment.size if hasattr(attachment, 'size') else 0
                })
        
        # Create parsed email object
        parsed_email = ParsedEmail(
            tenant_id=tenant_id,
            from_email=from_email,
            from_name=from_name,
            to_email=to_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            headers=headers,
            received_at=datetime.utcnow().isoformat()
        )
        
        # Process in background
        background_tasks.add_task(process_inbound_email, parsed_email)
        
        return {
            "success": True,
            "tenant_id": tenant_id,
            "from": from_email,
            "subject": subject,
            "message": "Email queued for processing"
        }
        
    except Exception as e:
        logger.error(f"Error receiving inbound email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_inbound_email(email: ParsedEmail):
    """
    Process inbound email - parse and generate quote
    
    This runs in the background after the webhook returns
    """
    try:
        logger.info(f"Processing email for {email.tenant_id}: {email.subject}")
        
        # Load tenant config
        config = get_config(email.tenant_id)
        
        # Import here to avoid circular imports
        from src.agents.universal_email_parser import UniversalEmailParser
        from src.agents.quote_agent import QuoteAgent
        
        # Parse the email
        parser = UniversalEmailParser(config)
        parsed_data = parser.parse(email.body_text, email.subject)
        
        # Add sender info
        parsed_data['email'] = email.from_email
        parsed_data['name'] = email.from_name or email.from_email.split('@')[0]
        parsed_data['source'] = 'email'
        parsed_data['original_subject'] = email.subject
        
        # Check if this is a travel inquiry
        if parsed_data.get('destination') or parsed_data.get('is_travel_inquiry'):
            # Generate quote
            quote_agent = QuoteAgent(config)
            result = quote_agent.generate_quote(
                customer_data=parsed_data,
                send_email=True,
                assign_consultant=True
            )
            
            logger.info(f"✅ Quote generated for {email.from_email}: {result.get('quote_id')}")
        else:
            # Not a travel inquiry - maybe forward to helpdesk or log
            logger.info(f"Email from {email.from_email} not identified as travel inquiry")
            
            # Log to BigQuery for review
            from src.tools.bigquery_tool import BigQueryTool
            bq = BigQueryTool(config)
            bq.log_email({
                'tenant_id': email.tenant_id,
                'from_email': email.from_email,
                'subject': email.subject,
                'body_preview': email.body_text[:500],
                'parsed_data': parsed_data,
                'status': 'not_travel_inquiry',
                'received_at': email.received_at
            })
            
    except Exception as e:
        logger.error(f"Error processing email: {e}")
        import traceback
        traceback.print_exc()


@router.post("/email/inbound/{tenant_id}")
async def receive_tenant_email(
    tenant_id: str,
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Receive inbound email for a specific tenant
    
    Use this endpoint if you set up per-tenant webhook URLs in SendGrid:
    https://api.yourdomain.com/webhooks/email/inbound/africastay
    """
    try:
        # Verify tenant exists
        try:
            config = get_config(tenant_id)
        except:
            raise HTTPException(status_code=404, detail=f"Tenant not found: {tenant_id}")
        
        # Parse form data
        form = await request.form()
        
        from_email = form.get('from', '')
        to_email = form.get('to', '')
        subject = form.get('subject', '')
        body_text = form.get('text', '')
        body_html = form.get('html', '')
        
        # Extract sender name
        from_name = None
        if '<' in from_email and '>' in from_email:
            from_name = from_email.split('<')[0].strip().strip('"')
            from_email = from_email.split('<')[1].split('>')[0].strip()
        
        logger.info(f"📧 Inbound email for tenant '{tenant_id}' from {from_email}: {subject}")
        
        # Create parsed email
        parsed_email = ParsedEmail(
            tenant_id=tenant_id,
            from_email=from_email,
            from_name=from_name,
            to_email=to_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            attachments=[],
            headers={},
            received_at=datetime.utcnow().isoformat()
        )
        
        # Process in background
        background_tasks.add_task(process_inbound_email, parsed_email)
        
        return {
            "success": True,
            "tenant_id": tenant_id,
            "from": from_email,
            "subject": subject,
            "message": "Email queued for processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error receiving email for {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/email/test/{tenant_id}")
async def test_email_processing(tenant_id: str, email: str, subject: str = "Test inquiry for Zanzibar"):
    """
    Test endpoint to simulate email processing
    
    Usage: GET /webhooks/email/test/africastay?email=test@example.com&subject=Zanzibar%20quote
    """
    try:
        config = get_config(tenant_id)
    except:
        raise HTTPException(status_code=404, detail=f"Tenant not found: {tenant_id}")
    
    # Create test email
    test_email = ParsedEmail(
        tenant_id=tenant_id,
        from_email=email,
        from_name="Test User",
        to_email=f"{tenant_id}@inbound.zorahai.com",
        subject=subject,
        body_text=f"""
Hi,

I'm interested in a holiday to Zanzibar.

We're looking at traveling in September 2025, for about 7 nights.
There will be 2 adults.

We'd prefer a 4 or 5 star hotel with all-inclusive.

Please send us some options.

Thanks,
Test User
        """,
        received_at=datetime.utcnow().isoformat()
    )
    
    # Process synchronously for testing
    await process_inbound_email(test_email)
    
    return {
        "success": True,
        "message": f"Test email processed for {tenant_id}",
        "email": email
    }
