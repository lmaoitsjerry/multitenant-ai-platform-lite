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
    Routes to africastay tenant by default.
    
    URL: /api/webhooks/sendgrid-inbound
    """
    from src.webhooks.email_webhook import receive_tenant_email
    return await receive_tenant_email("africastay", request, background_tasks)


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

        result = agent.generate_quote(
            customer_data=inquiry_data,
            send_email=request.send_email,
            assign_consultant=request.assign_consultant
        )

        return result

    except Exception as e:
        logger.error(f"Quote generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@quotes_router.get("")
async def list_quotes(
    status: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    config: ClientConfig = Depends(get_client_config)
):
    """List quotes with optional filtering"""
    from src.agents.quote_agent import QuoteAgent

    try:
        agent = get_quote_agent(config)
        quotes = agent.list_quotes(status=status, limit=limit, offset=offset)

        return {
            "success": True,
            "data": quotes,
            "count": len(quotes)
        }

    except Exception as e:
        logger.error(f"Failed to list quotes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"Failed to get quote: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@quotes_router.post("/{quote_id}/resend")
async def resend_quote(
    quote_id: str,
    config: ClientConfig = Depends(get_client_config)
):
    """Resend quote email"""
    from src.agents.quote_agent import QuoteAgent

    try:
        agent = get_quote_agent(config)
        quote = agent.get_quote(quote_id)

        if not quote:
            raise HTTPException(status_code=404, detail="Quote not found")

        # Regenerate and resend
        result = agent.generate_quote(
            customer_data={
                'name': quote['customer_name'],
                'email': quote['customer_email'],
                'phone': quote.get('customer_phone'),
                'destination': quote['destination'],
                'check_in': quote['check_in_date'],
                'check_out': quote['check_out_date'],
                'adults': quote['adults'],
                'children': quote.get('children', 0),
                'children_ages': quote.get('children_ages', [])
            },
            send_email=True,
            assign_consultant=False
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resend quote: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"Failed to list clients: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"Failed to create client: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"Failed to get client: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"Failed to update client: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"Failed to update client stage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"Failed to get activities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"Failed to log activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"Failed to get pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"Failed to get pipeline summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"Failed to get CRM stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"Failed to convert quote to invoice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"Failed to create manual invoice: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Invoice creation failed: {str(e)}")


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
        supabase = SupabaseTool(config)
        invoices = supabase.list_invoices(status=status, limit=limit, offset=offset)

        return {
            "success": True,
            "data": invoices,
            "count": len(invoices)
        }

    except Exception as e:
        logger.error(f"Failed to list invoices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"Failed to get invoice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"Failed to update invoice status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"Failed to send invoice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        supabase = SupabaseTool(config)
        invoice = supabase.get_invoice(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

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

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="Invoice_{invoice_id}.pdf"'}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate invoice PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"Failed to update travelers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== PUBLIC ENDPOINTS ====================
# These endpoints don't require authentication and are used for shareable links

@public_router.get("/invoices/{invoice_id}/pdf")
async def public_invoice_pdf(
    invoice_id: str,
    config: ClientConfig = Depends(get_client_config)
):
    """
    Public endpoint to download invoice PDF.
    Used for shareable invoice links that don't require authentication.
    """
    from src.tools.supabase_tool import SupabaseTool
    from src.utils.pdf_generator import PDFGenerator

    try:
        supabase = SupabaseTool(config)
        invoice = supabase.get_invoice(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

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
        logger.error(f"Failed to generate public invoice PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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