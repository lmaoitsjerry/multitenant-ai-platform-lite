"""
API Routes - Multi-Tenant Version (Lite)

All API endpoints organized by domain:
- Quotes
- CRM (Clients)
- Invoices

Each endpoint uses the X-Client-ID header for tenant identification.
"""

import logging
from functools import lru_cache
from fastapi import APIRouter, HTTPException, Depends, Header, Query, Body, Request, BackgroundTasks
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum

from config.loader import ClientConfig
from src.api.dependencies import get_client_config
from src.middleware.auth_middleware import get_current_user, get_current_user_optional, UserContext

from src.utils.error_handler import log_and_raise
from src.webhooks.email_webhook import router as email_webhook_router
from src.services.crm_service import CRMService, PipelineStage

logger = logging.getLogger(__name__)

# ==================== Routers ====================

quotes_router = APIRouter(prefix="/api/v1/quotes", tags=["Quotes"])
crm_router = APIRouter(prefix="/api/v1/crm", tags=["CRM"])
invoices_router = APIRouter(prefix="/api/v1/invoices", tags=["Invoices"])
public_router = APIRouter(prefix="/api/v1/public", tags=["Public"])
legacy_webhook_router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


# ==================== Pydantic Models ====================

class TravelInquiry(BaseModel):
    """Travel inquiry for quote generation"""
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    destination: str
    check_in: Optional[str] = None  # YYYY-MM-DD
    check_out: Optional[str] = None  # YYYY-MM-DD
    adults: int = Field(default=2, ge=1, le=20)
    children: int = Field(default=0, ge=0, le=10)
    children_ages: Optional[List[int]] = None
    budget: Optional[float] = None
    message: Optional[str] = None
    requested_hotel: Optional[str] = None


class QuoteGenerateRequest(BaseModel):
    """Request to generate quote"""
    inquiry: TravelInquiry
    send_email: bool = True
    assign_consultant: bool = True
    selected_hotels: Optional[List[str]] = None  # Manually selected hotel names
    ticket_id: Optional[str] = None  # Link to enquiry ticket from triage


class QuoteLineItem(BaseModel):
    """Line item for quote from shopping cart"""
    type: str = Field(..., pattern="^(hotel|activity|flight|transfer|package)$")
    name: str
    description: Optional[str] = None
    price: float
    currency: str = "ZAR"
    quantity: int = 1
    nights: Optional[int] = None
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None


class QuoteWithItemsRequest(BaseModel):
    """Request to create quote from shopping cart items"""
    inquiry: TravelInquiry
    line_items: List[QuoteLineItem]
    send_email: bool = True
    assign_consultant: bool = True
    save_as_draft: bool = False


class PipelineStageEnum(str, Enum):
    QUOTED = "QUOTED"
    NEGOTIATING = "NEGOTIATING"
    BOOKED = "BOOKED"
    PAID = "PAID"
    TRAVELLED = "TRAVELLED"
    LOST = "LOST"


class ClientCreate(BaseModel):
    """Create CRM client"""
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = None
    source: str = "manual"
    consultant_id: Optional[str] = None


class ClientUpdate(BaseModel):
    """Update CRM client"""
    name: Optional[str] = None
    phone: Optional[str] = None
    consultant_id: Optional[str] = None
    pipeline_stage: Optional[PipelineStageEnum] = None


class ActivityLog(BaseModel):
    """Log activity for client"""
    activity_type: str
    description: str
    metadata: Optional[Dict[str, Any]] = None


class InvoiceCreate(BaseModel):
    """Create invoice from quote"""
    quote_id: str
    items: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None
    due_days: int = 7


class ManualInvoiceCreate(BaseModel):
    """Create invoice manually (without quote)"""
    customer_name: str
    customer_email: str
    customer_phone: Optional[str] = None
    items: List[Dict[str, Any]]  # List of {description, quantity, unit_price, amount}
    notes: Optional[str] = None
    due_days: int = 14
    destination: Optional[str] = None


class InvoiceStatusUpdate(BaseModel):
    """Update invoice status"""
    status: str
    payment_date: Optional[str] = None
    payment_reference: Optional[str] = None


class InvoiceSendRequest(BaseModel):
    """Request to send invoice email"""
    consultant_email: Optional[str] = None




# ==================== Dependency ====================

# Thread-safe caching using functools.lru_cache (GIL-protected atomic operations)


@lru_cache(maxsize=100)
def _get_cached_quote_agent(client_id: str):
    """Get cached QuoteAgent - thread-safe via lru_cache"""
    from src.agents.quote_agent import QuoteAgent
    config = get_client_config(client_id)
    return QuoteAgent(config)


def get_quote_agent(config: ClientConfig):
    """Get cached QuoteAgent for client"""
    return _get_cached_quote_agent(config.client_id)


@lru_cache(maxsize=100)
def _get_cached_crm_service(client_id: str):
    """Get cached CRMService - thread-safe via lru_cache"""
    config = get_client_config(client_id)
    return CRMService(config)


def get_crm_service(config: ClientConfig):
    """Get cached CRMService for client"""
    return _get_cached_crm_service(config.client_id)


# ==================== Legacy SendGrid Inbound Webhook ====================

@legacy_webhook_router.post("/sendgrid-inbound")
async def sendgrid_inbound_legacy(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Legacy SendGrid Inbound Parse endpoint for production compatibility.
    Dynamically routes to tenant based on the 'to' email address.

    URL: /api/webhooks/sendgrid-inbound
    """
    from src.webhooks.email_webhook import receive_inbound_email

    # Use the generic inbound handler which does proper tenant lookup
    return await receive_inbound_email(request, background_tasks)


# ==================== Quote Endpoints ====================

@quotes_router.post("/generate")
def generate_quote(
    request: QuoteGenerateRequest,
    config: ClientConfig = Depends(get_client_config),
    user: UserContext = Depends(get_current_user),
):
    """
    Generate a travel quote

    Matches hotels, calculates pricing, generates PDF, and optionally sends email.
    """
    from src.agents.quote_agent import QuoteAgent

    try:
        agent = get_quote_agent(config)

        # Convert inquiry to dict
        inquiry_data = request.inquiry.model_dump()

        # Pass selected hotels if provided
        result = agent.generate_quote(
            customer_data=inquiry_data,
            send_email=request.send_email,
            assign_consultant=request.assign_consultant,
            selected_hotels=request.selected_hotels
        )

        # If quote was generated from an enquiry ticket, resolve the ticket
        if request.ticket_id and result.get('success'):
            try:
                from src.tools.supabase_tool import SupabaseTool
                supabase = SupabaseTool(config)
                supabase.update_ticket(
                    ticket_id=request.ticket_id,
                    status='resolved',
                    notes=f"Quote {result.get('quote_id')} generated and sent to customer"
                )
                result['ticket_resolved'] = True
                logger.info(f"Resolved ticket {request.ticket_id} after generating quote {result.get('quote_id')}")
            except Exception as e:
                logger.warning(f"Failed to resolve ticket {request.ticket_id}: {e}")
                result['ticket_resolved'] = False

        return result

    except Exception as e:
        log_and_raise(500, "generating quote", e, logger)


@quotes_router.post("/create-with-items")
def create_quote_with_items(
    request: QuoteWithItemsRequest,
    config: ClientConfig = Depends(get_client_config),
    user: UserContext = Depends(get_current_user),
):
    """
    Create a quote from shopping cart items (hotels, activities, transfers, flights).

    Unlike /generate which searches for hotels, this endpoint uses pre-selected items
    from the shopping cart to create a quote directly.
    """
    from src.tools.supabase_tool import SupabaseTool
    from src.services.email_sender import EmailSender
    import secrets
    from datetime import datetime

    try:
        # Initialize Supabase with retry for transient connection errors
        supabase = None
        for attempt in range(2):
            try:
                supabase = SupabaseTool(config)
                break
            except Exception as e:
                if attempt == 0:
                    logger.warning(f"Supabase init failed, retrying: {e}")
                    continue
                logger.error(f"Supabase init failed after retry: {e}")
                raise HTTPException(
                    status_code=503,
                    detail="Database temporarily unavailable. Please try again."
                )

        inquiry = request.inquiry

        # Generate quote ID
        quote_id = f"QUO-{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"

        # Calculate totals by currency
        totals_by_currency = {}
        for item in request.line_items:
            currency = item.currency or 'ZAR'
            if currency not in totals_by_currency:
                totals_by_currency[currency] = 0
            totals_by_currency[currency] += item.price * item.quantity

        # Format line items for storage
        formatted_items = []
        for item in request.line_items:
            formatted_items.append({
                "type": item.type,
                "name": item.name,
                "description": item.description,
                "price": item.price,
                "currency": item.currency,
                "quantity": item.quantity,
                "nights": item.nights,
                "check_in": item.check_in,
                "check_out": item.check_out,
                "raw_data": item.raw_data,
            })

        # Build quote record
        quote_data = {
            "tenant_id": config.client_id,
            "quote_id": quote_id,
            "customer_name": inquiry.name,
            "customer_email": inquiry.email,
            "customer_phone": inquiry.phone,
            "destination": inquiry.destination,
            "check_in": inquiry.check_in,
            "check_out": inquiry.check_out,
            "adults": inquiry.adults,
            "children": inquiry.children,
            "children_ages": inquiry.children_ages,
            "budget": inquiry.budget,
            "message": inquiry.message,
            "status": "Draft" if request.save_as_draft else "Quoted",
            "line_items": formatted_items,
            "totals_by_currency": totals_by_currency,
            "total_amount": sum(totals_by_currency.values()),  # For backwards compatibility
            "currency": list(totals_by_currency.keys())[0] if totals_by_currency else 'ZAR',
            "source": "shopping_cart",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Save to database with retry for transient errors
        if supabase and supabase.client:
            for attempt in range(2):
                try:
                    result = supabase.client.table("quotes").insert(quote_data).execute()
                    if not result.data:
                        logger.warning(f"Quote insert returned no data for {quote_id}")
                    break
                except Exception as db_err:
                    if attempt == 0:
                        logger.warning(f"Quote DB insert failed, retrying: {db_err}")
                        continue
                    logger.error(f"Failed to save quote to database after retry: {db_err}")
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to save quote to database. Please try again."
                    )
        else:
            raise HTTPException(
                status_code=503,
                detail="Database unavailable. Please try again."
            )

        # Send email if requested and not a draft
        email_sent = False
        if request.send_email and not request.save_as_draft:
            try:
                email_sender = EmailSender(config)
                # Build email content with line items
                items_html = "".join([
                    f"<tr><td>{item.name}</td><td>{item.type.title()}</td>"
                    f"<td>{item.currency} {item.price:,.0f}</td></tr>"
                    for item in request.line_items
                ])

                totals_html = "<br>".join([
                    f"<strong>{curr}:</strong> {amt:,.0f}"
                    for curr, amt in totals_by_currency.items()
                ])

                email_content = f"""
                <h2>Your Travel Quote</h2>
                <p>Dear {inquiry.name},</p>
                <p>Thank you for your interest! Here's your personalized quote:</p>

                <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%;">
                    <tr style="background: #f3f4f6;">
                        <th>Item</th><th>Type</th><th>Price</th>
                    </tr>
                    {items_html}
                </table>

                <p style="margin-top: 20px;"><strong>Totals:</strong><br>{totals_html}</p>

                <p>Quote Reference: {quote_id}</p>
                <p>Please reply to this email if you have any questions or would like to proceed with booking.</p>
                """

                email_sent = email_sender.send_email(
                    to=inquiry.email,
                    subject=f"Your Travel Quote - {inquiry.destination}",
                    body_html=email_content,
                )
            except Exception as email_err:
                logger.error(f"Failed to send quote email: {email_err}")

        # Create CRM client if needed
        if request.assign_consultant and supabase and supabase.client:
            try:
                # Check if client exists
                existing = supabase.client.table("clients")\
                    .select("id")\
                    .eq("tenant_id", config.client_id)\
                    .eq("email", inquiry.email)\
                    .execute()

                if not existing.data:
                    # Create new client
                    supabase.client.table("clients").insert({
                        "tenant_id": config.client_id,
                        "name": inquiry.name,
                        "email": inquiry.email,
                        "phone": inquiry.phone,
                        "source": "shopping_cart",
                        "created_at": datetime.utcnow().isoformat(),
                    }).execute()
            except Exception as client_err:
                logger.warning(f"Failed to create/update client: {client_err}")

        return {
            "success": True,
            "quote_id": quote_id,
            "email_sent": email_sent,
            "items_count": len(request.line_items),
            "totals": totals_by_currency,
            "is_draft": request.save_as_draft,
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "creating quote with items", e, logger)


@quotes_router.get("")
def list_quotes(
    status: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    config: ClientConfig = Depends(get_client_config),
    x_client_id: Optional[str] = Header(None, alias="X-Client-ID"),
    user: UserContext = Depends(get_current_user),
):
    """List quotes with optional filtering"""
    from src.agents.quote_agent import QuoteAgent

    logger.info(f"[LIST_QUOTES] X-Client-ID header: {x_client_id}, resolved config.client_id: {config.client_id}")

    try:
        agent = get_quote_agent(config)
        quotes = agent.list_quotes(status=status, limit=limit, offset=offset)

        logger.info(f"[LIST_QUOTES] Returning {len(quotes)} quotes for tenant {config.client_id}")

        return {
            "success": True,
            "data": quotes,
            "count": len(quotes)
        }

    except Exception as e:
        log_and_raise(500, "listing quotes", e, logger)


@quotes_router.get("/{quote_id}")
def get_quote(
    quote_id: str,
    config: ClientConfig = Depends(get_client_config),
    user: UserContext = Depends(get_current_user),
):
    """Get quote by ID"""
    from src.agents.quote_agent import QuoteAgent

    try:
        agent = get_quote_agent(config)
        quote = agent.get_quote(quote_id)

        if not quote:
            raise HTTPException(status_code=404, detail="Quote not found")

        return {
            "success": True,
            "data": quote
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "retrieving quote", e, logger)


@quotes_router.get("/{quote_id}/pdf")
def download_quote_pdf(
    quote_id: str,
    config: ClientConfig = Depends(get_client_config),
    user: UserContext = Depends(get_current_user),
):
    """Generate and download quote PDF"""
    from src.utils.pdf_generator import PDFGenerator

    try:
        agent = get_quote_agent(config)
        quote = agent.get_quote(quote_id)

        if not quote:
            raise HTTPException(status_code=404, detail="Quote not found")

        # Build customer data
        customer_data = {
            'name': quote.get('customer_name', ''),
            'email': quote.get('customer_email', ''),
            'phone': quote.get('customer_phone', ''),
            'destination': quote.get('destination', ''),
            'check_in': quote.get('check_in_date', ''),
            'check_out': quote.get('check_out_date', ''),
            'nights': quote.get('nights', 7),
            'adults': quote.get('adults', 2),
            'children': quote.get('children', 0),
            'children_ages': quote.get('children_ages', [])
        }

        hotels = quote.get('hotels', [])

        pdf_generator = PDFGenerator(config)
        pdf_bytes = pdf_generator.generate_quote_pdf(quote, hotels, customer_data)

        if not pdf_bytes:
            raise HTTPException(status_code=500, detail="Failed to generate quote PDF")

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="Quote_{quote_id}.pdf"'}
        )

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "generating quote PDF", e, logger)


@quotes_router.post("/{quote_id}/resend")
def resend_quote(
    quote_id: str,
    config: ClientConfig = Depends(get_client_config),
    user: UserContext = Depends(get_current_user),
):
    """
    Resend an existing quote email to the customer.

    Unlike /send (for drafts only), this works on quotes of any status.
    Regenerates the PDF and resends the email without changing status.
    """
    from src.agents.quote_agent import QuoteAgent

    try:
        agent = get_quote_agent(config)
        result = agent.resend_quote(quote_id)

        if result.get('success'):
            return {
                'success': True,
                'quote_id': quote_id,
                'sent_at': result.get('sent_at'),
                'message': result.get('message', 'Quote resent successfully')
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get('error', 'Failed to resend quote')
            )

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "resending quote", e, logger)


@quotes_router.post("/{quote_id}/send")
def send_quote(
    quote_id: str,
    request: Request,
    config: ClientConfig = Depends(get_client_config),
    user: UserContext = Depends(get_current_user),
):
    """
    Send a draft quote to the customer.

    Requires authentication. Only draft quotes can be sent.

    The quote will be:
    1. Retrieved from database
    2. Validated as 'draft' status
    3. PDF regenerated
    4. Email sent to customer via tenant's SendGrid subuser
    5. Status updated to 'sent'
    6. Notification created for consultant
    """
    from src.agents.quote_agent import QuoteAgent
    from src.middleware.auth_middleware import get_current_user

    # Ensure user is authenticated
    try:
        user = get_current_user(request)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        quote_agent = QuoteAgent(config)
        result = quote_agent.send_draft_quote(quote_id)

        if result.get('success'):
            return {
                'success': True,
                'quote_id': quote_id,
                'status': 'sent',
                'sent_at': result.get('sent_at'),
                'message': f"Quote sent to {result.get('customer_email')}"
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get('error', 'Failed to send quote')
            )

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "sending quote", e, logger)


# ==================== CRM Endpoints ====================

@crm_router.get("/clients")
def list_clients(
    query: Optional[str] = None,
    stage: Optional[PipelineStageEnum] = None,
    consultant_id: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    config: ClientConfig = Depends(get_client_config),
    user: UserContext = Depends(get_current_user),
):
    """Search and list CRM clients"""
    try:
        crm = get_crm_service(config)

        stage_enum = PipelineStage(stage.value) if stage else None

        clients = crm.search_clients(
            query=query,
            stage=stage_enum,
            consultant_id=consultant_id,
            limit=limit,
            offset=offset
        )

        return {
            "success": True,
            "data": clients,
            "count": len(clients)
        }

    except Exception as e:
        log_and_raise(500, "listing clients", e, logger)


@crm_router.post("/clients")
def create_client(
    client: ClientCreate,
    config: ClientConfig = Depends(get_client_config),
    user: UserContext = Depends(get_current_user),
):
    """Create new CRM client"""
    try:
        crm = get_crm_service(config)

        result = crm.get_or_create_client(
            email=client.email,
            name=client.name,
            phone=client.phone,
            source=client.source,
            consultant_id=client.consultant_id
        )

        if not result:
            raise HTTPException(status_code=500, detail="Failed to create client - database operation returned no data")

        return {
            "success": True,
            "data": result,
            "created": result.get('created', True)
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "creating client", e, logger)


@crm_router.get("/clients/{client_id}")
def get_client(
    client_id: str,
    config: ClientConfig = Depends(get_client_config),
    user: UserContext = Depends(get_current_user),
):
    """Get client by ID"""
    try:
        crm = get_crm_service(config)
        client = crm.get_client(client_id)

        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        return {
            "success": True,
            "data": client
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "retrieving client", e, logger)


@crm_router.patch("/clients/{client_id}")
def update_client(
    client_id: str,
    update: ClientUpdate,
    config: ClientConfig = Depends(get_client_config),
    user: UserContext = Depends(get_current_user),
):
    """Update client details"""
    try:
        crm = get_crm_service(config)

        # Update basic fields
        if update.name or update.phone or update.consultant_id:
            crm.update_client(
                client_id=client_id,
                name=update.name,
                phone=update.phone,
                consultant_id=update.consultant_id
            )

        # Update stage if provided
        if update.pipeline_stage:
            crm.update_stage(
                client_id=client_id,
                stage=PipelineStage(update.pipeline_stage.value)
            )

        # Get updated client
        client = crm.get_client(client_id)

        return {
            "success": True,
            "data": client
        }

    except Exception as e:
        log_and_raise(500, "updating client", e, logger)


class StageUpdate(BaseModel):
    """Update client pipeline stage"""
    stage: PipelineStageEnum


@crm_router.patch("/clients/{client_id}/stage")
def update_client_stage(
    client_id: str,
    stage_update: StageUpdate,
    config: ClientConfig = Depends(get_client_config),
    user: UserContext = Depends(get_current_user),
):
    """Update client pipeline stage"""
    try:
        crm = get_crm_service(config)

        # Check client exists
        client = crm.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        # Update stage
        crm.update_stage(
            client_id=client_id,
            stage=PipelineStage(stage_update.stage.value)
        )

        # Get updated client
        updated_client = crm.get_client(client_id)

        return {
            "success": True,
            "data": updated_client
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "updating client stage", e, logger)


@crm_router.get("/clients/{client_id}/activities")
def get_client_activities(
    client_id: str,
    limit: int = Query(default=20, le=100),
    config: ClientConfig = Depends(get_client_config),
    user: UserContext = Depends(get_current_user),
):
    """Get activities for a client"""
    try:
        crm = get_crm_service(config)
        activities = crm.get_activities(client_id, limit=limit)

        return {
            "success": True,
            "data": activities,
            "count": len(activities)
        }

    except Exception as e:
        log_and_raise(500, "retrieving activities", e, logger)


@crm_router.post("/clients/{client_id}/activities")
def log_activity(
    client_id: str,
    activity: ActivityLog,
    config: ClientConfig = Depends(get_client_config),
    user: UserContext = Depends(get_current_user),
):
    """Log activity for a client"""
    from src.tools.supabase_tool import SupabaseTool

    try:
        supabase = SupabaseTool(config)

        success = supabase.log_activity(
            client_id=client_id,
            activity_type=activity.activity_type,
            description=activity.description,
            metadata=activity.metadata
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to log activity")

        return {
            "success": True,
            "message": "Activity logged"
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "logging activity", e, logger)


@crm_router.get("/pipeline")
def get_pipeline(
    config: ClientConfig = Depends(get_client_config),
    user: UserContext = Depends(get_current_user),
):
    """Get pipeline data - alias for /pipeline/summary for frontend compatibility"""
    try:
        crm = get_crm_service(config)
        summary = crm.get_pipeline_summary()

        return {
            "success": True,
            "data": summary
        }

    except Exception as e:
        log_and_raise(500, "retrieving pipeline", e, logger)


@crm_router.get("/pipeline/summary")
def get_pipeline_summary(
    config: ClientConfig = Depends(get_client_config),
    user: UserContext = Depends(get_current_user),
):
    """Get pipeline stage summary"""
    try:
        crm = get_crm_service(config)
        summary = crm.get_pipeline_summary()

        return {
            "success": True,
            "data": summary
        }

    except Exception as e:
        log_and_raise(500, "retrieving pipeline summary", e, logger)


@crm_router.get("/stats")
def get_crm_stats(
    config: ClientConfig = Depends(get_client_config),
    user: UserContext = Depends(get_current_user),
):
    """Get CRM statistics"""
    try:
        crm = get_crm_service(config)
        stats = crm.get_client_stats()

        return {
            "success": True,
            "data": stats
        }

    except Exception as e:
        log_and_raise(500, "retrieving CRM stats", e, logger)


# ==================== Invoice Endpoints ====================

@invoices_router.post("/convert-quote")
def convert_quote_to_invoice(
    request: InvoiceCreate,
    config: ClientConfig = Depends(get_client_config),
    user: UserContext = Depends(get_current_user),
):
    """Create invoice from quote"""
    from src.agents.quote_agent import QuoteAgent
    from src.tools.supabase_tool import SupabaseTool
    from datetime import timedelta

    try:
        # Get quote
        agent = get_quote_agent(config)
        quote = agent.get_quote(request.quote_id)

        if not quote:
            raise HTTPException(status_code=404, detail="Quote not found")

        # Calculate total from quote
        import json
        total = 0
        items = request.items or []

        # Extract trip details from quote
        destination = quote.get('destination', '')
        check_in = quote.get('check_in_date', '')
        check_out = quote.get('check_out_date', '')
        nights = quote.get('nights', 7)

        if not items:
            # Extract from quote options
            for opt_key in ['option_1_json', 'option_2_json', 'option_3_json']:
                if quote.get(opt_key):
                    try:
                        opt = json.loads(quote[opt_key]) if isinstance(quote[opt_key], str) else quote[opt_key]
                        if opt:
                            items.append({
                                'description': f"{opt.get('name', 'Hotel')} - {nights} nights",
                                'hotel_name': opt.get('name', 'Hotel'),
                                'room_type': opt.get('room_type', ''),
                                'meal_plan': opt.get('meal_plan', ''),
                                'amount': opt.get('total_price', 0),
                                'destination': destination,
                                'check_in': check_in,
                                'check_out': check_out,
                                'nights': nights
                            })
                            total += opt.get('total_price', 0)
                            break  # Just use first option
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.debug(f"Failed to parse hotels JSON: {e}")
        else:
            total = sum(item.get('amount', 0) for item in items)
            # Add trip details to each item if not present
            for item in items:
                if 'destination' not in item:
                    item['destination'] = destination
                if 'check_in' not in item:
                    item['check_in'] = check_in
                if 'check_out' not in item:
                    item['check_out'] = check_out
                if 'nights' not in item:
                    item['nights'] = nights

        # Create invoice
        supabase = SupabaseTool(config)
        due_date = datetime.utcnow() + timedelta(days=request.due_days)

        invoice = supabase.create_invoice(
            customer_name=quote['customer_name'],
            customer_email=quote['customer_email'],
            items=items,
            total_amount=total,
            currency=config.currency,
            due_date=due_date,
            notes=request.notes,
            quote_id=request.quote_id,
            customer_phone=quote.get('customer_phone'),
            destination=destination,
            check_in=check_in,
            check_out=check_out,
            nights=nights
        )

        if not invoice:
            raise HTTPException(status_code=500, detail="Failed to create invoice")

        # Mark quote as 'accepted' when invoice is created from it
        try:
            if supabase.client:
                supabase.client.table('quotes')\
                    .update({'status': 'accepted'})\
                    .eq('quote_id', request.quote_id)\
                    .eq('tenant_id', config.client_id)\
                    .execute()
                logger.info(f"Quote {request.quote_id} marked as accepted (invoice created)")
            else:
                logger.warning("Supabase client not available — could not update quote status")
        except Exception as quote_update_err:
            logger.warning(f"Failed to update quote status to accepted: {quote_update_err}")

        return {
            "success": True,
            "data": invoice
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "converting quote to invoice", e, logger)


@invoices_router.post("/create")
def create_manual_invoice(
    request: ManualInvoiceCreate,
    config: ClientConfig = Depends(get_client_config),
    user: UserContext = Depends(get_current_user),
):
    """Create invoice manually (without a quote)"""
    from src.tools.supabase_tool import SupabaseTool
    from datetime import timedelta

    try:
        logger.info(f"Creating manual invoice for: {request.customer_name}")
        logger.info(f"Items received: {request.items}")

        # Validate items
        if not request.items:
            raise HTTPException(status_code=400, detail="At least one item is required")

        # Calculate total from items - make a copy to avoid modifying the original
        items_list = []
        total = 0
        for item in request.items:
            item_copy = dict(item)  # Make a copy
            item_amount = item_copy.get('amount')
            if item_amount is None:
                # Calculate from quantity * unit_price if amount not provided
                qty = item_copy.get('quantity', 1)
                unit_price = item_copy.get('unit_price', 0)
                item_amount = qty * unit_price
                item_copy['amount'] = item_amount
            total += item_amount
            items_list.append(item_copy)

        logger.info(f"Calculated total: {total}, Items: {items_list}")

        # Create invoice
        supabase = SupabaseTool(config)
        due_date = datetime.utcnow() + timedelta(days=request.due_days)

        invoice = supabase.create_invoice(
            customer_name=request.customer_name,
            customer_email=request.customer_email,
            items=items_list,
            total_amount=total,
            currency=config.currency,
            due_date=due_date,
            notes=request.notes,
            customer_phone=request.customer_phone
        )

        if not invoice:
            raise HTTPException(status_code=500, detail="Failed to create invoice - database returned no data")

        logger.info(f"Invoice created successfully: {invoice.get('invoice_id')}")
        return {
            "success": True,
            "invoice_id": invoice.get('invoice_id'),
            "data": invoice
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "creating manual invoice", e, logger)


@invoices_router.get("")
def list_invoices(
    status: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    config: ClientConfig = Depends(get_client_config),
    user: UserContext = Depends(get_current_user),
):
    """List invoices"""
    from src.tools.supabase_tool import SupabaseTool

    try:
        logger.info(f"[LIST_INVOICES] tenant_id={config.client_id}, status={status}, limit={limit}")
        supabase = SupabaseTool(config)
        invoices = supabase.list_invoices(status=status, limit=limit, offset=offset)
        logger.info(f"[LIST_INVOICES] Found {len(invoices)} invoices for tenant {config.client_id}")

        return {
            "success": True,
            "data": invoices,
            "count": len(invoices)
        }

    except Exception as e:
        log_and_raise(500, "listing invoices", e, logger)


@invoices_router.get("/{invoice_id}")
def get_invoice(
    invoice_id: str,
    config: ClientConfig = Depends(get_client_config),
    user: UserContext = Depends(get_current_user),
):
    """Get invoice by ID"""
    from src.tools.supabase_tool import SupabaseTool

    try:
        supabase = SupabaseTool(config)
        invoice = supabase.get_invoice(invoice_id)

        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        return {
            "success": True,
            "data": invoice
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "retrieving invoice", e, logger)


@invoices_router.patch("/{invoice_id}/status")
def update_invoice_status(
    invoice_id: str,
    update: InvoiceStatusUpdate,
    config: ClientConfig = Depends(get_client_config),
    user: UserContext = Depends(get_current_user),
):
    """Update invoice status"""
    from src.tools.supabase_tool import SupabaseTool

    try:
        supabase = SupabaseTool(config)

        payment_date = None
        if update.payment_date:
            payment_date = datetime.fromisoformat(update.payment_date)

        success = supabase.update_invoice_status(
            invoice_id=invoice_id,
            status=update.status,
            payment_date=payment_date,
            payment_reference=update.payment_reference
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update invoice")

        # If marking as paid, also set paid_amount to total_amount
        if update.status == 'paid':
            invoice_before = supabase.get_invoice(invoice_id)
            if invoice_before:
                total_amount = invoice_before.get('total_amount', 0)
                result = supabase.client.table('invoices').update({
                    'paid_amount': total_amount
                }).eq('invoice_id', invoice_id).eq('tenant_id', config.client_id).execute()
                if not result.data:
                    raise HTTPException(status_code=500, detail="Failed to update paid amount")

        # Get updated invoice
        invoice = supabase.get_invoice(invoice_id)

        # Trigger notification if paid
        if update.status == 'paid' and invoice:
            try:
                from src.api.notifications_routes import NotificationService
                notification_service = NotificationService(config)
                notification_service.notify_invoice_paid(
                    customer_name=invoice.get('customer_name', 'Customer'),
                    invoice_id=invoice_id,
                    amount=invoice.get('total_amount', 0),
                    currency=config.currency or 'USD'
                )
            except Exception as e:
                logger.warning(f"Failed to send invoice paid notification: {e}")

        return {
            "success": True,
            "data": invoice
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "updating invoice status", e, logger)


class PaymentRecordRequest(BaseModel):
    """Request model for recording a payment"""
    amount: float
    payment_date: str  # ISO date string
    payment_method: str = "bank_transfer"  # bank_transfer, credit_card, cash, other
    reference: Optional[str] = None
    notes: Optional[str] = None


@invoices_router.post("/{invoice_id}/payments")
def record_payment(
    invoice_id: str,
    payment: PaymentRecordRequest,
    config: ClientConfig = Depends(get_client_config),
    user: UserContext = Depends(get_current_user),
):
    """
    Record a payment against an invoice.

    Updates the invoice status based on payment amount:
    - Full payment: marks as 'paid'
    - Partial payment: marks as 'partial'
    """
    from src.tools.supabase_tool import SupabaseTool

    try:
        supabase = SupabaseTool(config)

        # Get current invoice
        invoice = supabase.get_invoice(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        total_amount = invoice.get('total_amount', 0)
        current_paid = invoice.get('paid_amount', 0) or 0
        new_total_paid = current_paid + payment.amount

        # Determine new status
        if new_total_paid >= total_amount:
            new_status = 'paid'
        else:
            new_status = 'partial'

        # Parse payment date
        payment_date = None
        if payment.payment_date:
            payment_date = datetime.fromisoformat(payment.payment_date.replace('Z', '+00:00'))

        # Build reference string
        reference = payment.reference or f"{payment.payment_method.upper()}-{datetime.now().strftime('%Y%m%d')}"
        if payment.notes:
            reference = f"{reference} | {payment.notes}"

        # Update invoice
        success = supabase.update_invoice_status(
            invoice_id=invoice_id,
            status=new_status,
            payment_date=payment_date,
            payment_reference=reference
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to record payment")

        # Update paid_amount in invoice
        result = supabase.client.table('invoices').update({
            'paid_amount': new_total_paid
        }).eq('invoice_id', invoice_id).eq('tenant_id', config.client_id).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to update paid amount")

        # Get updated invoice
        updated_invoice = supabase.get_invoice(invoice_id)

        # Trigger notification if fully paid
        if new_status == 'paid':
            try:
                from src.api.notifications_routes import NotificationService
                notification_service = NotificationService(config)
                notification_service.notify_invoice_paid(
                    customer_name=invoice.get('customer_name', 'Customer'),
                    invoice_id=invoice_id,
                    amount=total_amount,
                    currency=config.currency or 'ZAR'
                )
            except Exception as e:
                logger.warning(f"Failed to send payment notification: {e}")

        return {
            "success": True,
            "message": f"Payment of {payment.amount} recorded successfully",
            "data": {
                "invoice_id": invoice_id,
                "amount_recorded": payment.amount,
                "total_paid": new_total_paid,
                "total_amount": total_amount,
                "outstanding": max(0, total_amount - new_total_paid),
                "status": new_status,
                "payment_reference": reference
            },
            "invoice": updated_invoice
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "recording payment", e, logger)


@invoices_router.post("/{invoice_id}/send")
def send_invoice_email(
    invoice_id: str,
    request: InvoiceSendRequest = Body(default=InvoiceSendRequest()),
    config: ClientConfig = Depends(get_client_config),
    user: UserContext = Depends(get_current_user),
):
    """Generate and send invoice PDF via email"""
    from src.tools.supabase_tool import SupabaseTool
    from src.utils.pdf_generator import PDFGenerator
    from src.utils.email_sender import EmailSender
    from src.agents.quote_agent import QuoteAgent

    try:
        supabase = SupabaseTool(config)
        invoice = supabase.get_invoice(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        # Get trip details from quote
        trip_details = {}
        if invoice.get('quote_id'):
            quote_agent = get_quote_agent(config)
            quote = quote_agent.get_quote(invoice['quote_id'])
            if quote:
                trip_details = {
                    'destination': quote.get('destination'),
                    'check_in': quote.get('check_in_date'),
                    'check_out': quote.get('check_out_date'),
                    'nights': quote.get('nights')
                }

        invoice_data = {
            'invoice_id': invoice['invoice_id'],
            'quote_id': invoice.get('quote_id', ''),
            'created_at': invoice.get('created_at', ''),
            'due_date': invoice.get('due_date', ''),
            'total_amount': invoice.get('total_amount', 0),
            'currency': invoice.get('currency', config.currency),
            'notes': invoice.get('notes', ''),
            'trip_details': trip_details,
            'travelers': invoice.get('travelers', [])
        }

        customer_data = {
            'name': invoice.get('customer_name', ''),
            'email': invoice.get('customer_email', ''),
            'phone': invoice.get('customer_phone', '')
        }

        # Generate PDF
        pdf_generator = PDFGenerator(config)
        pdf_bytes = pdf_generator.generate_invoice_pdf(invoice_data, invoice.get('items', []), customer_data)

        if not pdf_bytes:
            raise HTTPException(status_code=500, detail="Failed to generate invoice PDF")

        # Send email
        email_sender = EmailSender(config)
        success = email_sender.send_invoice_email(
            customer_email=customer_data['email'],
            customer_name=customer_data['name'],
            invoice_pdf_data=pdf_bytes,
            invoice_id=invoice['invoice_id'],
            total_amount=invoice.get('total_amount', 0),
            currency=invoice.get('currency', config.currency),
            due_date=invoice.get('due_date', ''),
            destination=trip_details.get('destination'),
            consultant_email=request.consultant_email
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to send invoice email")

        # Mark as sent
        supabase.client.table(SupabaseTool.TABLE_INVOICES)\
            .update({'email_sent': True, 'email_sent_at': datetime.utcnow().isoformat()})\
            .eq('invoice_id', invoice_id)\
            .eq('tenant_id', config.client_id)\
            .execute()

        return {"success": True, "message": f"Invoice sent to {customer_data['email']}", "invoice_id": invoice_id}

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "sending invoice", e, logger)


@invoices_router.get("/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: str,
    config: ClientConfig = Depends(get_client_config),
    user: UserContext = Depends(get_current_user),
):
    """Generate and download invoice PDF"""
    from src.tools.supabase_tool import SupabaseTool
    from src.utils.pdf_generator import PDFGenerator
    from src.agents.quote_agent import QuoteAgent

    try:
        logger.info(f"Generating PDF for invoice: {invoice_id}")
        supabase = SupabaseTool(config)
        invoice = supabase.get_invoice(invoice_id)
        if not invoice:
            logger.warning(f"Invoice not found: {invoice_id}")
            raise HTTPException(status_code=404, detail="Invoice not found")

        logger.info(f"Invoice found with {len(invoice.get('items', []))} items")

        trip_details = {}
        if invoice.get('quote_id'):
            quote_agent = get_quote_agent(config)
            quote = quote_agent.get_quote(invoice['quote_id'])
            if quote:
                trip_details = {
                    'destination': quote.get('destination'),
                    'check_in': quote.get('check_in_date'),
                    'check_out': quote.get('check_out_date'),
                    'nights': quote.get('nights')
                }

        invoice_data = {
            'invoice_id': invoice['invoice_id'],
            'quote_id': invoice.get('quote_id', ''),
            'created_at': invoice.get('created_at', ''),
            'due_date': invoice.get('due_date', ''),
            'total_amount': invoice.get('total_amount', 0),
            'currency': invoice.get('currency', config.currency),
            'notes': invoice.get('notes', ''),
            'trip_details': trip_details,
            'travelers': invoice.get('travelers', [])
        }

        customer_data = {
            'name': invoice.get('customer_name', ''),
            'email': invoice.get('customer_email', ''),
            'phone': invoice.get('customer_phone', '')
        }

        pdf_generator = PDFGenerator(config)
        logger.info(f"Calling PDF generator with invoice_data keys: {list(invoice_data.keys())}")
        pdf_bytes = pdf_generator.generate_invoice_pdf(invoice_data, invoice.get('items', []), customer_data)

        if not pdf_bytes:
            logger.error("PDF generator returned empty bytes")
            raise HTTPException(status_code=500, detail="Failed to generate invoice PDF - empty result")

        logger.info(f"PDF generated successfully: {len(pdf_bytes)} bytes")
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="Invoice_{invoice_id}.pdf"',
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "generating invoice PDF", e, logger)


@invoices_router.patch("/{invoice_id}/travelers")
def update_invoice_travelers(
    invoice_id: str,
    travelers: List[Dict[str, Any]] = Body(...),
    config: ClientConfig = Depends(get_client_config),
    user: UserContext = Depends(get_current_user),
):
    """
    Update traveler details on invoice

    Travelers should include:
    - name: Traveler full name
    - type: 'Adult' or 'Child'
    - passport_number: Passport number (optional)
    - date_of_birth: DOB in YYYY-MM-DD format (optional)
    - nationality: Nationality (optional)
    """
    from src.tools.supabase_tool import SupabaseTool

    try:
        supabase = SupabaseTool(config)
        invoice = supabase.get_invoice(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        supabase.client.table(SupabaseTool.TABLE_INVOICES)\
            .update({'travelers': travelers, 'updated_at': datetime.utcnow().isoformat()})\
            .eq('invoice_id', invoice_id)\
            .eq('tenant_id', config.client_id)\
            .execute()

        return {"success": True, "data": supabase.get_invoice(invoice_id)}

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "updating travelers", e, logger)


# ==================== PUBLIC ENDPOINTS ====================
# These endpoints don't require authentication and are used for shareable links

def get_invoice_public(invoice_id: str):
    """Get invoice by ID without tenant filter (for public shareable links)."""
    import os
    import httpx
    import re

    # Validate invoice_id format to prevent injection
    # Supports: INV-YYYYMMDD-XXXXXX format (e.g., INV-20260211-298BA0)
    # Also supports UUID format for backwards compatibility
    invoice_pattern = r'^INV-\d{8}-[A-F0-9]{6}$'
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'

    if not (re.match(invoice_pattern, invoice_id, re.I) or re.match(uuid_pattern, invoice_id, re.I)):
        logger.warning(f"Invalid invoice_id format in public access: {invoice_id[:50]}")
        return None

    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY')

    if not supabase_url or not supabase_key:
        logger.error("Missing SUPABASE_URL or SUPABASE_KEY")
        return None

    try:
        url = f"{supabase_url}/rest/v1/invoices"
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json"
        }
        params = {
            "invoice_id": f"eq.{invoice_id}",
            "select": "*"
        }

        response = httpx.get(url, headers=headers, params=params, timeout=10.0)
        response.raise_for_status()
        data = response.json()

        if data and len(data) > 0:
            return data[0]
        return None
    except Exception as e:
        logger.error(f"Failed to get public invoice: {e}", exc_info=True)
        return None

@public_router.get("/invoices/{invoice_id}/pdf")
def public_invoice_pdf(
    invoice_id: str,
    x_client_id: Optional[str] = Header(None, alias="X-Client-ID")
):
    """
    Public endpoint to download invoice PDF.
    Used for shareable invoice links that don't require authentication.
    """
    from src.utils.pdf_generator import PDFGenerator

    try:
        # Get invoice without tenant filter (public access)
        invoice = get_invoice_public(invoice_id)
        if not invoice:
            logger.warning(f"Invoice not found for public access: {invoice_id}")
            raise HTTPException(status_code=404, detail="Invoice not found")

        # Load config for the invoice's tenant
        tenant_id = invoice.get('tenant_id')
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Invoice has no tenant")

        # Get config from tenant_id
        try:
            config = ClientConfig(tenant_id)
        except Exception:
            # Fallback to default config
            config = ClientConfig('example')

        # Get trip details if linked to a quote
        trip_details = {}
        if invoice.get('quote_id'):
            quote_agent = get_quote_agent(config)
            quote = quote_agent.get_quote(invoice['quote_id'])
            if quote:
                trip_details = {
                    'destination': quote.get('destination'),
                    'check_in': quote.get('check_in_date'),
                    'check_out': quote.get('check_out_date'),
                    'nights': quote.get('nights')
                }

        invoice_data = {
            'invoice_id': invoice['invoice_id'],
            'quote_id': invoice.get('quote_id', ''),
            'created_at': invoice.get('created_at', ''),
            'due_date': invoice.get('due_date', ''),
            'total_amount': invoice.get('total_amount', 0),
            'currency': invoice.get('currency', config.currency),
            'notes': invoice.get('notes', ''),
            'trip_details': trip_details,
            'travelers': invoice.get('travelers', [])
        }

        customer_data = {
            'name': invoice.get('customer_name', ''),
            'email': invoice.get('customer_email', ''),
            'phone': invoice.get('customer_phone', '')
        }

        pdf_generator = PDFGenerator(config)
        pdf_bytes = pdf_generator.generate_invoice_pdf(invoice_data, invoice.get('items', []), customer_data)

        if not pdf_bytes:
            raise HTTPException(status_code=500, detail="Failed to generate invoice PDF")

        # Return as inline PDF (viewable in browser)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="Invoice_{invoice_id}.pdf"'}
        )

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "generating public invoice PDF", e, logger)


def get_quote_public(quote_id: str):
    """Get quote by ID without tenant filter (for public shareable links)."""
    import os
    import httpx
    import re

    # Validate quote_id format to prevent injection
    # Supports: QT-YYYYMMDD-XXXXXX format (e.g., QT-20260210-A80413)
    # Also supports UUID format for backwards compatibility
    quote_pattern = r'^QT-\d{8}-[A-F0-9]{6}$'
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'

    if not (re.match(quote_pattern, quote_id, re.I) or re.match(uuid_pattern, quote_id, re.I)):
        logger.warning(f"Invalid quote_id format in public access: {quote_id[:50]}")
        return None

    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY')

    if not supabase_url or not supabase_key:
        logger.error("Missing SUPABASE_URL or SUPABASE_KEY")
        return None

    try:
        url = f"{supabase_url}/rest/v1/quotes"
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json"
        }
        params = {
            "quote_id": f"eq.{quote_id}",
            "select": "*"
        }

        response = httpx.get(url, headers=headers, params=params, timeout=10.0)
        response.raise_for_status()
        data = response.json()

        if data and len(data) > 0:
            return data[0]
        return None
    except Exception as e:
        logger.error(f"Failed to get public quote: {e}", exc_info=True)
        return None


@public_router.get("/quotes/{quote_id}/pdf")
def public_quote_pdf(quote_id: str):
    """
    Public endpoint to view quote PDF.
    Used for shareable quote links that don't require authentication.
    """
    from src.utils.pdf_generator import PDFGenerator

    try:
        # Get quote without tenant filter (public access)
        quote = get_quote_public(quote_id)
        if not quote:
            logger.warning(f"Quote not found for public access: {quote_id}")
            raise HTTPException(status_code=404, detail="Quote not found")

        # Load config for the quote's tenant
        tenant_id = quote.get('tenant_id')
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Quote has no tenant")

        try:
            config = ClientConfig(tenant_id)
        except Exception:
            config = ClientConfig('example')

        # Build customer data
        customer_data = {
            'name': quote.get('customer_name', ''),
            'email': quote.get('customer_email', ''),
            'phone': quote.get('customer_phone', ''),
            'destination': quote.get('destination', ''),
            'check_in': quote.get('check_in_date', ''),
            'check_out': quote.get('check_out_date', ''),
            'nights': quote.get('nights', 7),
            'adults': quote.get('adults', 2),
            'children': quote.get('children', 0),
            'children_ages': quote.get('children_ages', [])
        }

        hotels = quote.get('hotels', [])

        pdf_generator = PDFGenerator(config)
        pdf_bytes = pdf_generator.generate_quote_pdf(quote, hotels, customer_data)

        if not pdf_bytes:
            raise HTTPException(status_code=500, detail="Failed to generate quote PDF")

        # Return as inline PDF (viewable in browser)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="Quote_{quote_id}.pdf"'}
        )

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "generating public quote PDF", e, logger)


# ==================== Export all routers ====================

def include_routers(app):
    """Include all routers in the FastAPI app"""
    app.include_router(quotes_router)
    app.include_router(crm_router)
    app.include_router(invoices_router)
    app.include_router(public_router)  # Public shareable endpoints
    app.include_router(legacy_webhook_router)  # Legacy SendGrid endpoint

    app.include_router(email_webhook_router, prefix="/webhooks")

    # Rate limiting usage stats
    from src.middleware.rate_limiter import get_rate_limit_router
    app.include_router(get_rate_limit_router())

    # Pricing Guide
    from src.api.pricing_routes import pricing_router
    app.include_router(pricing_router)

    # Knowledge Base
    from src.api.knowledge_routes import knowledge_router
    app.include_router(knowledge_router)

    # Analytics & Dashboard
    from src.api.analytics_routes import include_analytics_routers
    include_analytics_routers(app)

    # Admin & Provisioning
    from src.api.admin_routes import include_admin_router
    include_admin_router(app)

    # Admin Extended Routes (Internal Platform)
    from src.api.admin_tenants_routes import include_admin_tenants_router
    include_admin_tenants_router(app)

    from src.api.admin_analytics_routes import include_admin_analytics_router
    include_admin_analytics_router(app)

    from src.api.admin_sendgrid_routes import include_admin_sendgrid_router
    include_admin_sendgrid_router(app)

    from src.api.admin_knowledge_routes import include_admin_knowledge_router
    include_admin_knowledge_router(app)

    # Branding & White-labeling
    from src.api.branding_routes import branding_router
    app.include_router(branding_router)

    # Tenant Settings (Email, Banking)
    from src.api.settings_routes import settings_router
    app.include_router(settings_router)

    # Document Templates
    from src.api.templates_routes import templates_router
    app.include_router(templates_router)

    # Authentication
    from src.api.auth_routes import auth_router
    app.include_router(auth_router)

    # User Management
    from src.api.users_routes import users_router
    app.include_router(users_router)

    # Tenant Onboarding
    from src.api.onboarding_routes import onboarding_router
    app.include_router(onboarding_router)

    # Inbound Tickets
    from src.api.inbound_routes import inbound_router
    app.include_router(inbound_router)

    # Helpdesk
    from src.api.helpdesk_routes import helpdesk_router
    app.include_router(helpdesk_router)

    # Notifications
    from src.api.notifications_routes import notifications_router
    app.include_router(notifications_router)

    # Privacy & Compliance (GDPR/POPIA)
    from src.api.privacy_routes import privacy_router
    app.include_router(privacy_router)

    # Rates Engine (Live Hotel Availability)
    from src.api.rates_routes import rates_router
    app.include_router(rates_router)

    # Travel Services (Flights, Transfers, Activities)
    from src.api.travel_services_routes import travel_router
    app.include_router(travel_router)

    # HotelBeds API (Live Hotels, Activities, Transfers)
    from src.api.hotelbeds_routes import hotelbeds_router
    app.include_router(hotelbeds_router)

    # Unified RAG for AI Agents (Local + Global Knowledge)
    from src.api.unified_rag_routes import unified_rag_router
    app.include_router(unified_rag_router)

    # Prometheus Metrics - DISABLED (prometheus_client import hangs on some systems)
    # TODO: Investigate prometheus_client hanging issue and re-enable
    # from src.api.metrics_routes import metrics_router
    # app.include_router(metrics_router)