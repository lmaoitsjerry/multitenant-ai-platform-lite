"""
API Routes - Multi-Tenant Version (Lite)

All API endpoints organized by domain:
- Quotes
- CRM (Clients)
- Invoices

Each endpoint uses the X-Client-ID header for tenant identification.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Header, Query, Body, Request, BackgroundTasks
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum

from config.loader import ClientConfig

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

# Global caches for performance - avoid re-initialization on every request
_client_configs = {}
_quote_agents = {}
_crm_services = {}


def get_client_config(x_client_id: str = Header(None, alias="X-Client-ID")) -> ClientConfig:
    """Get client configuration from header"""
    import os
    client_id = x_client_id or os.getenv("CLIENT_ID", "example")

    if client_id not in _client_configs:
        try:
            _client_configs[client_id] = ClientConfig(client_id)
            logger.info(f"Loaded configuration for client: {client_id}")
        except Exception as e:
            logger.error(f"Failed to load config for {client_id}: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid client: {client_id}")

    return _client_configs[client_id]


def get_quote_agent(config: ClientConfig):
    """Get cached QuoteAgent for client"""
    from src.agents.quote_agent import QuoteAgent

    if config.client_id not in _quote_agents:
        _quote_agents[config.client_id] = QuoteAgent(config)
        logger.info(f"Created QuoteAgent for {config.client_id}")

    return _quote_agents[config.client_id]


def get_crm_service(config: ClientConfig):
    """Get cached CRMService for client"""
    if config.client_id not in _crm_services:
        _crm_services[config.client_id] = CRMService(config)
        logger.info(f"Created CRMService for {config.client_id}")

    return _crm_services[config.client_id]


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
async def generate_quote(
    request: QuoteGenerateRequest,
    config: ClientConfig = Depends(get_client_config)
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

        return result

    except Exception as e:
        log_and_raise(500, "generating quote", e, logger)


@quotes_router.get("")
async def list_quotes(
    status: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    config: ClientConfig = Depends(get_client_config),
    x_client_id: str = Header(None, alias="X-Client-ID")
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
async def get_quote(
    quote_id: str,
    config: ClientConfig = Depends(get_client_config)
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
async def download_quote_pdf(
    quote_id: str,
    config: ClientConfig = Depends(get_client_config)
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
async def resend_quote(
    quote_id: str,
    config: ClientConfig = Depends(get_client_config)
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
async def send_quote(
    quote_id: str,
    request: Request,
    config: ClientConfig = Depends(get_client_config)
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
async def list_clients(
    query: Optional[str] = None,
    stage: Optional[PipelineStageEnum] = None,
    consultant_id: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    config: ClientConfig = Depends(get_client_config)
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
async def create_client(
    client: ClientCreate,
    config: ClientConfig = Depends(get_client_config)
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
async def get_client(
    client_id: str,
    config: ClientConfig = Depends(get_client_config)
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
async def update_client(
    client_id: str,
    update: ClientUpdate,
    config: ClientConfig = Depends(get_client_config)
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
async def update_client_stage(
    client_id: str,
    update: StageUpdate,
    config: ClientConfig = Depends(get_client_config)
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
            stage=PipelineStage(update.stage.value)
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
async def get_client_activities(
    client_id: str,
    limit: int = Query(default=20, le=100),
    config: ClientConfig = Depends(get_client_config)
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
async def log_activity(
    client_id: str,
    activity: ActivityLog,
    config: ClientConfig = Depends(get_client_config)
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
async def get_pipeline(
    config: ClientConfig = Depends(get_client_config)
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
async def get_pipeline_summary(
    config: ClientConfig = Depends(get_client_config)
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
async def get_crm_stats(
    config: ClientConfig = Depends(get_client_config)
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
async def convert_quote_to_invoice(
    request: InvoiceCreate,
    config: ClientConfig = Depends(get_client_config)
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

        if not items:
            # Extract from quote options
            for opt_key in ['option_1_json', 'option_2_json', 'option_3_json']:
                if quote.get(opt_key):
                    try:
                        opt = json.loads(quote[opt_key]) if isinstance(quote[opt_key], str) else quote[opt_key]
                        if opt:
                            items.append({
                                'description': f"{opt.get('name', 'Hotel')} - {quote.get('nights', 7)} nights",
                                'amount': opt.get('total_price', 0)
                            })
                            total += opt.get('total_price', 0)
                            break  # Just use first option
                    except:
                        pass
        else:
            total = sum(item.get('amount', 0) for item in items)

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
            customer_phone=quote.get('customer_phone')
        )

        if not invoice:
            raise HTTPException(status_code=500, detail="Failed to create invoice")

        return {
            "success": True,
            "data": invoice
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "converting quote to invoice", e, logger)


@invoices_router.post("/create")
async def create_manual_invoice(
    request: ManualInvoiceCreate,
    config: ClientConfig = Depends(get_client_config)
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
async def list_invoices(
    status: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    config: ClientConfig = Depends(get_client_config)
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
async def get_invoice(
    invoice_id: str,
    config: ClientConfig = Depends(get_client_config)
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
async def update_invoice_status(
    invoice_id: str,
    update: InvoiceStatusUpdate,
    config: ClientConfig = Depends(get_client_config)
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


@invoices_router.post("/{invoice_id}/send")
async def send_invoice_email(
    invoice_id: str,
    request: InvoiceSendRequest = Body(default=InvoiceSendRequest()),
    config: ClientConfig = Depends(get_client_config)
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
async def download_invoice_pdf(
    invoice_id: str,
    config: ClientConfig = Depends(get_client_config)
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
async def update_invoice_travelers(
    invoice_id: str,
    travelers: List[Dict[str, Any]] = Body(...),
    config: ClientConfig = Depends(get_client_config)
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
    """Get invoice by ID without tenant filter (for public access)"""
    import os
    import httpx

    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY')

    if not supabase_url or not supabase_key:
        logger.error("Missing SUPABASE_URL or SUPABASE_KEY")
        return None

    try:
        # Use direct REST API call
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
        logger.error(f"Failed to get public invoice: {e}")
        import traceback
        traceback.print_exc()
        return None

@public_router.get("/invoices/{invoice_id}/pdf")
async def public_invoice_pdf(
    invoice_id: str,
    x_client_id: str = Header(None, alias="X-Client-ID")
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
    """Get quote by ID without tenant filter (for public access)"""
    import os
    import httpx

    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY')

    if not supabase_url or not supabase_key:
        logger.error("Missing SUPABASE_URL or SUPABASE_KEY")
        return None

    try:
        # Use direct REST API call
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
        logger.error(f"Failed to get public quote: {e}")
        import traceback
        traceback.print_exc()
        return None


@public_router.get("/quotes/{quote_id}/pdf")
async def public_quote_pdf(quote_id: str):
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