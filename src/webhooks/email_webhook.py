"""
Email Webhook - Multi-Tenant Inbound Email Processing

Receives emails from SendGrid Inbound Parse and routes them to the correct tenant.

Setup Options:
1. Single domain routing: inbound@mail.zorahai.com with tenant ID in subject/headers
2. Subdomain routing: {tenant}@inbound.zorahai.com
3. Email forwarding: Client forwards to {tenant}@inbound.zorahai.com

Tenant Resolution Strategies (in order):
1. Match TO address against tenant's support_email (any domain)
2. Match TO address against tenant's sendgrid_username + @zorah.ai
3. Match TO address against tenant's primary email
4. Direct tenant ID lookup (local part of TO address)
5. Plus addressing: quotes+{tenant_id}@domain.com
6. X-Tenant-ID header
7. [TENANT:xxx] in subject line

Usage:
    Add these routes to your FastAPI app:

    from src.webhooks.email_webhook import router as email_webhook_router
    app.include_router(email_webhook_router, prefix="/webhooks")
"""

import json
import logging
import os
import re
import time
import uuid
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel

from config.loader import ClientConfig, get_config, list_clients
from src.utils.error_handler import log_and_raise

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Webhooks"])

# ==================== Tenant Email Cache ====================
# Cache for tenant email mappings to avoid O(n) iteration on every request
_tenant_email_cache: Dict[str, Any] = {}
TENANT_CACHE_TTL = 300  # 5 minutes


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


# ==================== Cache Management ====================

def _refresh_tenant_email_cache() -> Dict[str, str]:
    """
    Refresh the tenant email cache by loading all tenant email mappings.

    Returns:
        Dict mapping email (lowercase) -> tenant_id
    """
    global _tenant_email_cache

    email_to_tenant: Dict[str, str] = {}

    try:
        tenant_ids = list_clients()
        logger.info(f"[EMAIL_WEBHOOK][CACHE] Refreshing tenant email cache for {len(tenant_ids)} tenants")

        for tenant_id in tenant_ids:
            try:
                emails = get_tenant_email_addresses(tenant_id)

                # Map each email type to tenant_id
                if emails.get('support_email'):
                    email_to_tenant[emails['support_email'].lower()] = {
                        'tenant_id': tenant_id,
                        'strategy': 'support_email'
                    }
                if emails.get('sendgrid_email'):
                    email_to_tenant[emails['sendgrid_email'].lower()] = {
                        'tenant_id': tenant_id,
                        'strategy': 'sendgrid_email'
                    }
                if emails.get('primary_email'):
                    email_to_tenant[emails['primary_email'].lower()] = {
                        'tenant_id': tenant_id,
                        'strategy': 'primary_email'
                    }
            except Exception as e:
                logger.debug(f"[EMAIL_WEBHOOK][CACHE] Error loading tenant {tenant_id}: {e}")

        _tenant_email_cache = {
            'data': email_to_tenant,
            'timestamp': time.time(),
            'tenant_count': len(tenant_ids),
            'email_count': len(email_to_tenant)
        }

        logger.info(f"[EMAIL_WEBHOOK][CACHE] Cache refreshed: {len(email_to_tenant)} email mappings for {len(tenant_ids)} tenants")

    except Exception as e:
        logger.error(f"[EMAIL_WEBHOOK][CACHE] Failed to refresh cache: {e}")
        _tenant_email_cache = {
            'data': {},
            'timestamp': time.time(),
            'error': str(e)
        }

    return _tenant_email_cache.get('data', {})


def _get_cached_tenant_lookup(email: str) -> Optional[Dict[str, str]]:
    """
    Get tenant info from cache for an email.

    Returns:
        Dict with tenant_id and strategy if found, None otherwise
    """
    global _tenant_email_cache

    # Check if cache needs refresh
    cache_timestamp = _tenant_email_cache.get('timestamp', 0)
    cache_age = time.time() - cache_timestamp

    if cache_age > TENANT_CACHE_TTL or not _tenant_email_cache.get('data'):
        _refresh_tenant_email_cache()

    email_lower = email.lower().strip()
    return _tenant_email_cache.get('data', {}).get(email_lower)


# ==================== Diagnostic Logging Helpers ====================

def diagnostic_log(diagnostic_id: str, step: int, message: str, data: Dict[str, Any] = None):
    """Log a diagnostic step with consistent formatting"""
    log_msg = f"[EMAIL_WEBHOOK][{diagnostic_id}][STEP_{step}] {message}"
    if data:
        log_msg += f" | data={json.dumps(data, default=str)}"
    logger.info(log_msg)


def get_tenant_email_addresses(tenant_id: str) -> Dict[str, Optional[str]]:
    """
    Get all email addresses associated with a tenant for matching.

    Returns dict with:
    - support_email: The tenant's support email (any domain)
    - sendgrid_email: The tenant's sendgrid_username@zorah.ai
    - primary_email: The tenant's primary/contact email
    """
    result = {
        'support_email': None,
        'sendgrid_email': None,
        'primary_email': None,
        'tenant_id': tenant_id
    }

    try:
        config = get_config(tenant_id)

        # Primary email from config
        result['primary_email'] = getattr(config, 'primary_email', None)

        # Try to get from database (tenant_settings table)
        try:
            from src.tools.supabase_tool import SupabaseTool
            supabase = SupabaseTool(config)
            settings = supabase.get_tenant_settings()
            if settings:
                result['support_email'] = settings.get('support_email')
                sendgrid_username = settings.get('sendgrid_username')
                if sendgrid_username:
                    result['sendgrid_email'] = f"{sendgrid_username}@zorah.ai"
        except Exception as e:
            logger.debug(f"Could not load tenant settings from DB for {tenant_id}: {e}")

    except Exception as e:
        logger.debug(f"Could not load config for {tenant_id}: {e}")

    return result


def find_tenant_by_email(to_email: str, diagnostic_id: str = None) -> Tuple[Optional[str], str, bool]:
    """
    Find tenant by matching TO email against tenant email addresses.

    Uses O(1) cached lookup first, falls back to O(n) iteration if cache miss.

    Supports:
    - support_email (any domain, e.g., support@company.com or someone@gmail.com)
    - sendgrid_username@zorah.ai (SendGrid subuser format)
    - primary_email (contact email)

    Returns:
        Tuple of (tenant_id, match_strategy, cache_hit) or (None, "none", cache_hit)
    """
    to_email_lower = to_email.lower().strip()
    start_time = time.time()

    if diagnostic_id:
        diagnostic_log(diagnostic_id, 3, f"Searching for tenant matching email: {to_email_lower}")

    # First, try O(1) cache lookup
    cached_result = _get_cached_tenant_lookup(to_email_lower)
    if cached_result:
        tenant_id = cached_result['tenant_id']
        strategy = cached_result['strategy']
        if diagnostic_id:
            elapsed = (time.time() - start_time) * 1000
            diagnostic_log(diagnostic_id, 3, f"CACHE HIT: {strategy} for tenant {tenant_id}", {
                'matched_email': to_email_lower,
                'elapsed_ms': round(elapsed, 2)
            })
        return tenant_id, strategy, True

    # Cache miss - fall back to O(n) iteration (defensive)
    if diagnostic_id:
        diagnostic_log(diagnostic_id, 3, "Cache miss - falling back to iteration")

    # Get all tenant IDs
    try:
        tenant_ids = list_clients()
    except Exception as e:
        logger.error(f"Failed to list clients: {e}")
        return None, "error", False

    strategies_tried = []

    for tenant_id in tenant_ids:
        emails = get_tenant_email_addresses(tenant_id)

        # Strategy 1: Match support_email (any domain)
        if emails['support_email'] and emails['support_email'].lower() == to_email_lower:
            if diagnostic_id:
                diagnostic_log(diagnostic_id, 3, f"MATCH (fallback): support_email for tenant {tenant_id}", {
                    'matched_email': emails['support_email']
                })
            return tenant_id, "support_email", False

        # Strategy 2: Match sendgrid_username@zorah.ai
        if emails['sendgrid_email'] and emails['sendgrid_email'].lower() == to_email_lower:
            if diagnostic_id:
                diagnostic_log(diagnostic_id, 3, f"MATCH (fallback): sendgrid_email for tenant {tenant_id}", {
                    'matched_email': emails['sendgrid_email']
                })
            return tenant_id, "sendgrid_email", False

        # Strategy 3: Match primary_email
        if emails['primary_email'] and emails['primary_email'].lower() == to_email_lower:
            if diagnostic_id:
                diagnostic_log(diagnostic_id, 3, f"MATCH (fallback): primary_email for tenant {tenant_id}", {
                    'matched_email': emails['primary_email']
                })
            return tenant_id, "primary_email", False

        # Track what we tried for debugging
        strategies_tried.append({
            'tenant_id': tenant_id,
            'support_email': emails['support_email'],
            'sendgrid_email': emails['sendgrid_email'],
            'primary_email': emails['primary_email']
        })

    if diagnostic_id:
        elapsed = (time.time() - start_time) * 1000
        diagnostic_log(diagnostic_id, 3, f"No match found. Tried {len(tenant_ids)} tenants", {
            'to_email': to_email_lower,
            'elapsed_ms': round(elapsed, 2),
            'sample_strategies': strategies_tried[:3]  # Log first 3 for debugging
        })

    return None, "none", False


def extract_tenant_from_email(to_email: str, headers: Dict[str, str] = None, diagnostic_id: str = None) -> Tuple[Optional[str], str]:
    """
    Extract tenant ID from email address or headers

    Supports multiple routing strategies:
    1. Database lookup: Match TO against support_email, sendgrid_email, primary_email
    2. Direct tenant ID: local part is tenant ID (e.g., africastay@inbound.zorahai.com)
    3. Plus addressing: quotes+africastay@domain.com -> africastay
    4. Custom header: X-Tenant-ID header

    Returns:
        Tuple of (tenant_id, strategy_used) or (None, "none")
    """
    to_email = to_email.lower().strip()
    local_part = to_email.split('@')[0] if '@' in to_email else to_email

    # Strategy 1: Database lookup (support_email, sendgrid_email, primary_email)
    tenant_id, strategy, _cache_hit = find_tenant_by_email(to_email, diagnostic_id)
    if tenant_id:
        return tenant_id, strategy

    # Strategy 2: Direct tenant ID lookup (local part is the tenant ID)
    skip_patterns = ['quotes', 'sales', 'info', 'support', 'inbound', 'mail', 'admin', 'noreply']
    if local_part not in skip_patterns:
        try:
            config = get_config(local_part)
            if config:
                if diagnostic_id:
                    diagnostic_log(diagnostic_id, 3, f"MATCH: direct tenant ID from local part", {
                        'local_part': local_part
                    })
                return local_part, "direct_tenant_id"
        except:
            pass

    # Strategy 3: Plus addressing (quotes+africastay@domain.com)
    if '+' in local_part:
        tenant = local_part.split('+')[1]
        try:
            config = get_config(tenant)
            if config:
                if diagnostic_id:
                    diagnostic_log(diagnostic_id, 3, f"MATCH: plus addressing", {
                        'extracted_tenant': tenant
                    })
                return tenant, "plus_addressing"
        except:
            pass

    # Strategy 4: Check X-Tenant-ID header
    if headers:
        tenant_header = headers.get('x-tenant-id') or headers.get('X-Tenant-ID')
        if tenant_header:
            try:
                config = get_config(tenant_header)
                if config:
                    if diagnostic_id:
                        diagnostic_log(diagnostic_id, 3, f"MATCH: X-Tenant-ID header", {
                            'header_value': tenant_header
                        })
                    return tenant_header, "x_tenant_id_header"
            except:
                pass

    return None, "none"


def extract_tenant_from_subject(subject: str, diagnostic_id: str = None) -> Tuple[Optional[str], str]:
    """Extract tenant ID from subject line pattern [TENANT:xxx]"""
    match = re.search(r'\[TENANT:(\w+)\]', subject, re.IGNORECASE)
    if match:
        tenant = match.group(1).lower()
        try:
            config = get_config(tenant)
            if config:
                if diagnostic_id:
                    diagnostic_log(diagnostic_id, 3, f"MATCH: subject line pattern", {
                        'extracted_tenant': tenant
                    })
                return tenant, "subject_pattern"
        except:
            pass
    return None, "none"


# ==================== Main Webhook Endpoint ====================

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
    # Generate unique diagnostic ID for this request
    diagnostic_id = str(uuid.uuid4())[:8].upper()
    start_time = time.time()

    try:
        # STEP 1: Request received
        content_type = request.headers.get('content-type', 'unknown')
        diagnostic_log(diagnostic_id, 1, "Request received", {
            'timestamp': datetime.utcnow().isoformat(),
            'content_type': content_type,
            'method': request.method,
            'url': str(request.url)
        })

        # Parse form data
        form = await request.form()

        # STEP 2: Form data parsed
        form_fields = list(form.keys())
        from_email = form.get('from', '')
        to_email = form.get('to', '')
        subject = form.get('subject', '')
        body_text = form.get('text', '')
        body_html = form.get('html', '')
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
        original_from = from_email
        if '<' in from_email and '>' in from_email:
            from_name = from_email.split('<')[0].strip().strip('"')
            from_email = from_email.split('<')[1].split('>')[0].strip()

        diagnostic_log(diagnostic_id, 2, "Form data parsed", {
            'form_fields': form_fields,
            'from': from_email,
            'from_name': from_name,
            'to': to_email,
            'subject': subject[:100] if subject else None,
            'envelope_to': envelope.get('to', []),
            'envelope_from': envelope.get('from'),
            'body_length': len(body_text) if body_text else 0,
            'html_length': len(body_html) if body_html else 0
        })

        # STEP 3 & 4: Tenant resolution
        diagnostic_log(diagnostic_id, 3, "Starting tenant resolution", {
            'to_email': to_email,
            'envelope_to': envelope.get('to', [])
        })

        # Try multiple strategies in order
        strategies_tried = []

        # Strategy 1: From TO email address
        tenant_id, strategy = extract_tenant_from_email(to_email, headers, diagnostic_id)
        strategies_tried.append({'source': 'to_email', 'value': to_email, 'strategy': strategy, 'result': tenant_id})

        # Strategy 2: From subject line
        if not tenant_id:
            tenant_id, strategy = extract_tenant_from_subject(subject, diagnostic_id)
            strategies_tried.append({'source': 'subject', 'value': subject[:50], 'strategy': strategy, 'result': tenant_id})

        # Strategy 3: From envelope TO
        if not tenant_id and envelope.get('to'):
            envelope_to = envelope.get('to', [''])[0] if envelope.get('to') else ''
            if envelope_to and envelope_to != to_email:
                tenant_id, strategy = extract_tenant_from_email(envelope_to, headers, diagnostic_id)
                strategies_tried.append({'source': 'envelope_to', 'value': envelope_to, 'strategy': strategy, 'result': tenant_id})

        diagnostic_log(diagnostic_id, 4, "Tenant resolution result", {
            'resolved_tenant_id': tenant_id,
            'final_strategy': strategy if tenant_id else 'none',
            'strategies_tried': strategies_tried
        })

        if not tenant_id:
            elapsed = time.time() - start_time
            diagnostic_log(diagnostic_id, 4, "FAILED: Could not determine tenant", {
                'to_email': to_email,
                'elapsed_ms': round(elapsed * 1000, 2)
            })
            return {
                "success": False,
                "error": "Could not determine tenant",
                "diagnostic_id": diagnostic_id,
                "to_email": to_email,
                "strategies_tried": strategies_tried
            }

        # STEP 5: Config loaded
        try:
            config = get_config(tenant_id)
            diagnostic_log(diagnostic_id, 5, "Config loaded", {
                'tenant_id': tenant_id,
                'company_name': getattr(config, 'company_name', None),
                'destinations': getattr(config, 'destination_names', [])[:3]
            })
        except Exception as e:
            diagnostic_log(diagnostic_id, 5, f"FAILED: Config load error", {
                'tenant_id': tenant_id,
                'error': str(e)
            })
            return {
                "success": False,
                "error": f"Config load failed for tenant {tenant_id}",
                "diagnostic_id": diagnostic_id,
                "detail": str(e)
            }

        # Trigger notification for new email
        try:
            from src.api.notifications_routes import NotificationService
            notification_service = NotificationService(config)
            notification_service.notify_email_received(
                sender_email=from_email,
                subject=subject
            )
        except Exception as e:
            logger.warning(f"[{diagnostic_id}] Failed to send email notification: {e}")

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

        # STEP 6: Background task queued
        diagnostic_log(diagnostic_id, 6, "Background task queued", {
            'tenant_id': tenant_id,
            'from_email': from_email,
            'subject': subject[:100] if subject else None,
            'body_length': len(body_text) if body_text else 0,
            'attachments_count': len(attachments)
        })

        background_tasks.add_task(process_inbound_email, parsed_email, diagnostic_id)

        elapsed = time.time() - start_time
        return {
            "success": True,
            "diagnostic_id": diagnostic_id,
            "tenant_id": tenant_id,
            "resolution_strategy": strategy,
            "from": from_email,
            "subject": subject,
            "message": "Email queued for processing",
            "elapsed_ms": round(elapsed * 1000, 2)
        }

    except Exception as e:
        elapsed = time.time() - start_time
        diagnostic_log(diagnostic_id, 0, f"EXCEPTION: {str(e)}", {
            'elapsed_ms': round(elapsed * 1000, 2)
        })
        logger.exception(f"[{diagnostic_id}] Error receiving inbound email")
        log_and_raise(500, "receiving inbound email", e, logger)


async def process_inbound_email(email: ParsedEmail, diagnostic_id: str = None):
    """
    Process inbound email - parse and generate quote

    This runs in the background after the webhook returns
    """
    if not diagnostic_id:
        diagnostic_id = str(uuid.uuid4())[:8].upper()

    start_time = time.time()

    try:
        # STEP 7: Processing started
        diagnostic_log(diagnostic_id, 7, "Background processing started", {
            'tenant_id': email.tenant_id,
            'from_email': email.from_email,
            'subject': email.subject[:100] if email.subject else None
        })

        # Load tenant config
        config = get_config(email.tenant_id)

        # STEP 8: Email parser import
        try:
            from src.agents.llm_email_parser import LLMEmailParser
            from src.agents.universal_email_parser import UniversalEmailParser
            from src.agents.quote_agent import QuoteAgent
            diagnostic_log(diagnostic_id, 8, "Email parsers imported successfully", {
                'llm_parser': 'LLMEmailParser',
                'fallback_parser': 'UniversalEmailParser'
            })
        except ImportError as e:
            diagnostic_log(diagnostic_id, 8, f"FAILED: Import error", {
                'error': str(e),
                'module': 'LLMEmailParser or QuoteAgent'
            })
            raise

        # STEP 9: Email parsed
        # Try LLM parser first (has built-in fallback to rule-based)
        parser = LLMEmailParser(config)
        parsed_data = parser.parse(email.body_text, email.subject)

        # Add sender info
        parsed_data['email'] = email.from_email
        parsed_data['name'] = email.from_name or email.from_email.split('@')[0]
        parsed_data['source'] = 'email'
        parsed_data['original_subject'] = email.subject

        diagnostic_log(diagnostic_id, 9, "Email parsed", {
            'destination': parsed_data.get('destination'),
            'is_travel_inquiry': parsed_data.get('is_travel_inquiry'),
            'parse_method': parsed_data.get('parse_method', 'unknown'),
            'customer_name': parsed_data.get('name'),
            'customer_email': parsed_data.get('email'),
            'adults': parsed_data.get('adults'),
            'children': parsed_data.get('children'),
            'check_in': parsed_data.get('check_in'),
            'check_out': parsed_data.get('check_out'),
            'budget': parsed_data.get('budget')
        })

        # STEP 10: Quote generation decision
        should_generate_quote = parsed_data.get('destination') or parsed_data.get('is_travel_inquiry')
        diagnostic_log(diagnostic_id, 10, "Quote generation decision", {
            'should_generate': should_generate_quote,
            'reason': 'destination found' if parsed_data.get('destination') else
                     ('is_travel_inquiry flag' if parsed_data.get('is_travel_inquiry') else 'no destination or travel indicator')
        })

        # STEP 11: Quote result
        if should_generate_quote:
            try:
                quote_agent = QuoteAgent(config)
                # Create draft quote for consultant review before sending
                result = quote_agent.generate_quote(
                    customer_data=parsed_data,
                    send_email=False,  # Don't send email automatically
                    assign_consultant=True,
                    initial_status='draft'  # Draft status for consultant review
                )

                quote_id = result.get('quote_id')
                elapsed = time.time() - start_time
                diagnostic_log(diagnostic_id, 11, "Draft quote generated for consultant review", {
                    'quote_id': quote_id,
                    'status': 'draft',
                    'customer_email': email.from_email,
                    'destination': parsed_data.get('destination'),
                    'elapsed_ms': round(elapsed * 1000, 2)
                })

                # Create notification for draft quote requiring review
                try:
                    from src.api.notifications_routes import NotificationService
                    notification_service = NotificationService(config)
                    customer_name = parsed_data.get('name', email.from_email.split('@')[0])
                    destination = parsed_data.get('destination', 'travel inquiry')
                    notification_service.notify_quote_request(
                        customer_name=customer_name,
                        destination=f"{destination} (DRAFT - review required)",
                        quote_id=quote_id or 'unknown'
                    )
                except Exception as notif_err:
                    logger.warning(f"[{diagnostic_id}] Failed to create draft quote notification: {notif_err}")

            except Exception as e:
                elapsed = time.time() - start_time
                diagnostic_log(diagnostic_id, 11, f"FAILED: Quote generation error", {
                    'error': str(e),
                    'elapsed_ms': round(elapsed * 1000, 2)
                })
                raise
        else:
            elapsed = time.time() - start_time
            diagnostic_log(diagnostic_id, 11, "Skipped quote generation - not a travel inquiry", {
                'from_email': email.from_email,
                'elapsed_ms': round(elapsed * 1000, 2)
            })

            # Log to BigQuery for review
            try:
                from src.tools.bigquery_tool import BigQueryTool
                bq = BigQueryTool(config)
                bq.log_email({
                    'tenant_id': email.tenant_id,
                    'from_email': email.from_email,
                    'subject': email.subject,
                    'body_preview': email.body_text[:500] if email.body_text else '',
                    'parsed_data': parsed_data,
                    'status': 'not_travel_inquiry',
                    'received_at': email.received_at,
                    'diagnostic_id': diagnostic_id
                })
            except Exception as bq_err:
                logger.warning(f"[{diagnostic_id}] Failed to log to BigQuery: {bq_err}")

    except Exception as e:
        diagnostic_log(diagnostic_id, 0, f"EXCEPTION in background processing: {str(e)}")
        logger.exception(f"[{diagnostic_id}] Error processing email")


# ==================== Diagnostic Endpoints ====================

@router.get("/email/lookup/{email:path}")
async def lookup_tenant_by_email(email: str):
    """
    Lookup which tenant an email address maps to.

    Use this to test tenant resolution without sending full emails.

    Args:
        email: Email address to lookup (e.g., final-itc-3@zorah.ai)

    Returns:
        JSON with tenant lookup result including timing and cache hit status
    """
    diagnostic_id = str(uuid.uuid4())[:8].upper()
    start_time = time.time()

    tenant_id, strategy, cache_hit = find_tenant_by_email(email, diagnostic_id)

    elapsed_ms = round((time.time() - start_time) * 1000, 2)

    if tenant_id:
        # Get matched email for response
        try:
            emails = get_tenant_email_addresses(tenant_id)
            matched_email = None
            if strategy == 'support_email':
                matched_email = emails.get('support_email')
            elif strategy == 'sendgrid_email':
                matched_email = emails.get('sendgrid_email')
            elif strategy == 'primary_email':
                matched_email = emails.get('primary_email')
        except:
            matched_email = email

        return {
            "found": True,
            "tenant_id": tenant_id,
            "strategy": strategy,
            "matched_email": matched_email,
            "diagnostic_id": diagnostic_id,
            "cache_hit": cache_hit,
            "elapsed_ms": elapsed_ms
        }
    else:
        return {
            "found": False,
            "tenant_id": None,
            "strategy": "none",
            "diagnostic_id": diagnostic_id,
            "cache_hit": cache_hit,
            "elapsed_ms": elapsed_ms,
            "suggestion": "Email not registered. Check tenant_settings.support_email or sendgrid_username."
        }


@router.get("/email/diagnose")
async def diagnose_email_webhook():
    """
    Diagnostic endpoint - returns system state for debugging

    Returns:
    - All webhook endpoints and their routes
    - Current tenant list with email addresses
    - Environment variable status
    - Python import test for key modules
    - Sample test of get_config()
    """
    import os

    results = {
        'timestamp': datetime.utcnow().isoformat(),
        'webhook_endpoints': {},
        'tenants': [],
        'environment': {},
        'import_tests': {},
        'config_test': {}
    }

    # Webhook endpoints
    results['webhook_endpoints'] = {
        'inbound': '/webhooks/email/inbound',
        'inbound_with_tenant': '/webhooks/email/inbound/{tenant_id}',
        'lookup': '/webhooks/email/lookup/{email}',
        'debug': '/webhooks/email/debug',
        'diagnose': '/webhooks/email/diagnose',
        'status': '/webhooks/email/status',
        'test': '/webhooks/email/test/{tenant_id}'
    }

    # Environment variables
    results['environment'] = {
        'SENDGRID_API_KEY_set': bool(os.getenv('SENDGRID_API_KEY')),
        'OPENAI_API_KEY_set': bool(os.getenv('OPENAI_API_KEY')),
        'SUPABASE_URL_set': bool(os.getenv('SUPABASE_URL')),
        'SUPABASE_KEY_set': bool(os.getenv('SUPABASE_KEY') or os.getenv('SUPABASE_SERVICE_KEY')),
        'BASE_URL': os.getenv('BASE_URL', 'not set'),
        'GCP_PROJECT_ID': os.getenv('GCP_PROJECT_ID', 'not set')
    }

    # Import tests
    import_tests = {
        'UniversalEmailParser': False,
        'QuoteAgent': False,
        'BigQueryTool': False,
        'SupabaseTool': False
    }

    try:
        from src.agents.universal_email_parser import UniversalEmailParser
        import_tests['UniversalEmailParser'] = True
    except Exception as e:
        import_tests['UniversalEmailParser'] = f"Error: {str(e)}"

    try:
        from src.agents.quote_agent import QuoteAgent
        import_tests['QuoteAgent'] = True
    except Exception as e:
        import_tests['QuoteAgent'] = f"Error: {str(e)}"

    try:
        from src.tools.bigquery_tool import BigQueryTool
        import_tests['BigQueryTool'] = True
    except Exception as e:
        import_tests['BigQueryTool'] = f"Error: {str(e)}"

    try:
        from src.tools.supabase_tool import SupabaseTool
        import_tests['SupabaseTool'] = True
    except Exception as e:
        import_tests['SupabaseTool'] = f"Error: {str(e)}"

    results['import_tests'] = import_tests

    # Tenant list with email addresses
    try:
        tenant_ids = list_clients()
        tenants_info = []

        for tenant_id in tenant_ids[:20]:  # Limit to first 20 for response size
            try:
                emails = get_tenant_email_addresses(tenant_id)
                config = get_config(tenant_id)
                tenants_info.append({
                    'tenant_id': tenant_id,
                    'company_name': getattr(config, 'company_name', None),
                    'support_email': emails.get('support_email'),
                    'sendgrid_email': emails.get('sendgrid_email'),
                    'primary_email': emails.get('primary_email'),
                    'config_loaded': True
                })
            except Exception as e:
                tenants_info.append({
                    'tenant_id': tenant_id,
                    'config_loaded': False,
                    'error': str(e)
                })

        results['tenants'] = tenants_info
        results['total_tenants'] = len(tenant_ids)

    except Exception as e:
        results['tenants'] = []
        results['tenants_error'] = str(e)

    # Config test with known tenant
    try:
        # Try africastay as it's likely to exist
        test_tenant = 'africastay'
        config = get_config(test_tenant)
        results['config_test'] = {
            'tenant_id': test_tenant,
            'success': True,
            'company_name': getattr(config, 'company_name', None),
            'destinations': getattr(config, 'destination_names', [])[:5],
            'sendgrid_configured': bool(getattr(config, 'sendgrid_api_key', None))
        }
    except Exception as e:
        results['config_test'] = {
            'tenant_id': 'africastay',
            'success': False,
            'error': str(e)
        }

    return results


# ==================== Other Endpoints ====================

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
    diagnostic_id = str(uuid.uuid4())[:8].upper()

    try:
        # Verify tenant exists
        try:
            config = get_config(tenant_id)
        except:
            raise HTTPException(status_code=404, detail=f"Tenant not found: {tenant_id}")

        diagnostic_log(diagnostic_id, 1, f"Direct tenant email received for {tenant_id}")

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

        diagnostic_log(diagnostic_id, 2, "Form parsed", {
            'from': from_email,
            'to': to_email,
            'subject': subject[:100] if subject else None
        })

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
        background_tasks.add_task(process_inbound_email, parsed_email, diagnostic_id)

        return {
            "success": True,
            "diagnostic_id": diagnostic_id,
            "tenant_id": tenant_id,
            "from": from_email,
            "subject": subject,
            "message": "Email queued for processing"
        }

    except HTTPException:
        raise
    except Exception as e:
        diagnostic_log(diagnostic_id, 0, f"EXCEPTION: {str(e)}")
        logger.exception(f"[{diagnostic_id}] Error receiving email for {tenant_id}")
        log_and_raise(500, f"receiving email for tenant {tenant_id}", e, logger)


@router.get("/email/test/{tenant_id}")
async def test_email_processing(tenant_id: str, email: str, subject: str = "Test inquiry for Zanzibar"):
    """
    Test endpoint to simulate email processing

    Usage: GET /webhooks/email/test/africastay?email=test@example.com&subject=Zanzibar%20quote
    """
    diagnostic_id = str(uuid.uuid4())[:8].upper()

    try:
        config = get_config(tenant_id)
    except:
        raise HTTPException(status_code=404, detail=f"Tenant not found: {tenant_id}")

    diagnostic_log(diagnostic_id, 1, f"Test email processing for {tenant_id}", {
        'email': email,
        'subject': subject
    })

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
    await process_inbound_email(test_email, diagnostic_id)

    return {
        "success": True,
        "diagnostic_id": diagnostic_id,
        "message": f"Test email processed for {tenant_id}",
        "email": email
    }


@router.get("/email/status")
async def get_webhook_status():
    """
    Check webhook status and configuration

    Returns information about:
    - Webhook endpoint availability
    - Known tenant IDs
    - Configuration status
    - SendGrid Inbound Parse setup instructions
    """
    import os

    try:
        tenant_ids = list_clients()
    except Exception as e:
        tenant_ids = []
        logger.error(f"Failed to list tenants: {e}")

    # Get actual domain from environment if available
    base_url = os.getenv("BASE_URL", "https://api.zorah.ai")

    return {
        "status": "active",
        "webhook_endpoints": {
            "generic": "/webhooks/email/inbound",
            "per_tenant": "/webhooks/email/inbound/{tenant_id}",
            "lookup": "/webhooks/email/lookup/{email}",
            "test": "/webhooks/email/test/{tenant_id}",
            "debug": "/webhooks/email/debug",
            "diagnose": "/webhooks/email/diagnose"
        },
        "supported_routing": [
            "Database lookup: tenant.support_email (any domain)",
            "Database lookup: tenant.sendgrid_username@zorah.ai",
            "Database lookup: tenant.primary_email",
            "{tenant_id}@inbound.domain.com (direct tenant ID)",
            "quotes+{tenant_id}@domain.com (plus addressing)",
            "X-Tenant-ID header",
            "[TENANT:xxx] in subject line"
        ],
        "known_tenants": tenant_ids,
        "tenant_count": len(tenant_ids),
        "sendgrid_configuration": {
            "step_1_mx_record": {
                "type": "MX",
                "host": "inbound.zorah.ai",
                "value": "mx.sendgrid.net",
                "priority": 10
            },
            "step_2_inbound_parse": {
                "domain": "inbound.zorah.ai",
                "webhook_url": f"{base_url}/webhooks/email/inbound",
                "check_incoming_emails": True,
                "spam_check": False,
                "send_raw": False,
                "note": "Configure in SendGrid Dashboard > Settings > Inbound Parse"
            },
            "step_3_test": {
                "send_test_email_to": "{tenant_id}@inbound.zorah.ai",
                "example": "final-itc-3@inbound.zorah.ai",
                "check_logs": "Look for '[EMAIL_WEBHOOK]' in server logs"
            }
        },
        "environment": {
            "sendgrid_api_key_set": bool(os.getenv("SENDGRID_API_KEY")),
            "openai_api_key_set": bool(os.getenv("OPENAI_API_KEY")),
            "base_url": base_url
        }
    }


@router.post("/email/debug")
async def debug_inbound_email(request: Request):
    """
    Debug endpoint - logs all incoming data without processing

    Use this to verify SendGrid is correctly sending data to your webhook.
    """
    diagnostic_id = str(uuid.uuid4())[:8].upper()

    try:
        diagnostic_log(diagnostic_id, 1, "DEBUG WEBHOOK - RAW DATA")

        # Log all form fields
        form = await request.form()
        form_data = {}
        for key in form.keys():
            value = form.get(key)
            if key in ['text', 'html', 'headers']:
                # Truncate long values
                value_str = str(value)[:500] + "..." if len(str(value)) > 500 else str(value)
            else:
                value_str = str(value)
            form_data[key] = value_str
            logger.info(f"[{diagnostic_id}] {key}: {value_str}")

        return {
            "success": True,
            "diagnostic_id": diagnostic_id,
            "message": "Debug data logged - check server logs",
            "fields_received": list(form.keys()),
            "data_preview": {k: v[:100] if len(str(v)) > 100 else v for k, v in form_data.items()}
        }

    except Exception as e:
        diagnostic_log(diagnostic_id, 0, f"Debug endpoint error: {str(e)}")
        return {"success": False, "diagnostic_id": diagnostic_id, "error": str(e)}
