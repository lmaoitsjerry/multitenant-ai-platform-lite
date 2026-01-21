"""
Document Templates API Routes

Handles customizable templates for quotes and invoices:
- PDF layout style (standard, modern, minimal)
- Default terms and conditions
- Default payment instructions
- Default notes
- PDF branding options
"""

import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field
import os

from config.loader import ClientConfig
from src.tools.supabase_tool import SupabaseTool
from src.utils.error_handler import log_and_raise

logger = logging.getLogger(__name__)

templates_router = APIRouter(prefix="/api/v1/templates", tags=["Templates"])

# ==================== Dependency ====================

_client_configs = {}


def get_client_config(x_client_id: str = Header(None, alias="X-Client-ID")) -> ClientConfig:
    """Get client configuration from header"""
    client_id = x_client_id or os.getenv("CLIENT_ID", "example")

    if client_id not in _client_configs:
        try:
            _client_configs[client_id] = ClientConfig(client_id)
        except Exception as e:
            logger.error(f"Failed to load config for {client_id}: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid client: {client_id}")

    return _client_configs[client_id]


# ==================== Pydantic Models ====================

class QuoteTemplateSettings(BaseModel):
    """Quote template settings"""
    pdf_layout: Optional[str] = Field(None, description="Layout style: standard, modern, minimal")
    default_terms: Optional[str] = Field(None, max_length=2000)
    default_notes: Optional[str] = Field(None, max_length=1000)
    validity_days: Optional[int] = Field(14, ge=1, le=90)
    show_price_breakdown: Optional[bool] = True
    show_transfers: Optional[bool] = True
    show_company_address: Optional[bool] = True
    show_website: Optional[bool] = True


class InvoiceTemplateSettings(BaseModel):
    """Invoice template settings"""
    pdf_layout: Optional[str] = Field(None, description="Layout style: standard, modern, minimal")
    default_terms: Optional[str] = Field(None, max_length=2000)
    default_payment_instructions: Optional[str] = Field(None, max_length=1000)
    default_notes: Optional[str] = Field(None, max_length=1000)
    due_days: Optional[int] = Field(14, ge=1, le=90)
    show_banking_details: Optional[bool] = True
    show_vat: Optional[bool] = True
    show_traveler_details: Optional[bool] = True
    show_company_address: Optional[bool] = True


class TemplateSettingsUpdate(BaseModel):
    """Update request for all template settings"""
    quote: Optional[QuoteTemplateSettings] = None
    invoice: Optional[InvoiceTemplateSettings] = None


# ==================== Default Templates ====================

DEFAULT_QUOTE_TERMS = """1. All quotes are subject to availability at time of booking.
2. Prices are subject to exchange rate fluctuations.
3. A deposit of 50% is required to confirm booking.
4. Full payment is due 30 days before arrival.
5. Cancellation fees apply as per our terms and conditions."""

DEFAULT_INVOICE_TERMS = """1. Payment is due by the due date shown above.
2. All prices are in the currency indicated.
3. Bank charges for international transfers are the responsibility of the payer.
4. Please use the invoice number as payment reference."""

DEFAULT_PAYMENT_INSTRUCTIONS = """Please transfer the total amount to our bank account using the invoice number as reference.
For international payments, please use the SWIFT code provided.
Once payment is made, please send proof of payment to our email."""


# ==================== Helper Functions ====================

def get_default_settings() -> Dict[str, Any]:
    """Get default template settings"""
    return {
        "quote": {
            "pdf_layout": "standard",
            "default_terms": DEFAULT_QUOTE_TERMS,
            "default_notes": "",
            "validity_days": 14,
            "show_price_breakdown": True,
            "show_transfers": True,
            "show_company_address": True,
            "show_website": True
        },
        "invoice": {
            "pdf_layout": "standard",
            "default_terms": DEFAULT_INVOICE_TERMS,
            "default_payment_instructions": DEFAULT_PAYMENT_INSTRUCTIONS,
            "default_notes": "",
            "due_days": 14,
            "show_banking_details": True,
            "show_vat": True,
            "show_traveler_details": True,
            "show_company_address": True
        }
    }


# ==================== Endpoints ====================

@templates_router.get("")
async def get_template_settings(config: ClientConfig = Depends(get_client_config)):
    """
    Get all template settings for the tenant

    Returns quote and invoice template settings.
    """
    try:
        supabase = SupabaseTool(config)
        settings = supabase.get_template_settings()

        if not settings:
            settings = get_default_settings()

        return {
            "success": True,
            "data": settings
        }
    except Exception as e:
        logger.error(f"Failed to get template settings: {e}")
        # Return defaults on error
        return {
            "success": True,
            "data": get_default_settings()
        }


@templates_router.put("")
async def update_template_settings(
    data: TemplateSettingsUpdate,
    config: ClientConfig = Depends(get_client_config)
):
    """
    Update template settings

    Supports partial updates - only specified fields are changed.
    """
    try:
        supabase = SupabaseTool(config)

        # Get current settings
        current = supabase.get_template_settings() or get_default_settings()

        # Merge updates
        if data.quote:
            quote_updates = {k: v for k, v in data.quote.model_dump().items() if v is not None}
            current["quote"] = {**current.get("quote", {}), **quote_updates}

        if data.invoice:
            invoice_updates = {k: v for k, v in data.invoice.model_dump().items() if v is not None}
            current["invoice"] = {**current.get("invoice", {}), **invoice_updates}

        # Save
        result = supabase.update_template_settings(current)

        return {
            "success": True,
            "data": result or current,
            "message": "Template settings updated"
        }
    except Exception as e:
        log_and_raise(500, "updating template settings", e, logger)


@templates_router.get("/quote")
async def get_quote_template(config: ClientConfig = Depends(get_client_config)):
    """Get quote template settings only"""
    try:
        supabase = SupabaseTool(config)
        settings = supabase.get_template_settings()

        quote_settings = (settings or {}).get("quote", get_default_settings()["quote"])

        return {
            "success": True,
            "data": quote_settings
        }
    except Exception as e:
        logger.error(f"Failed to get quote template: {e}")
        return {
            "success": True,
            "data": get_default_settings()["quote"]
        }


@templates_router.get("/invoice")
async def get_invoice_template(config: ClientConfig = Depends(get_client_config)):
    """Get invoice template settings only"""
    try:
        supabase = SupabaseTool(config)
        settings = supabase.get_template_settings()

        invoice_settings = (settings or {}).get("invoice", get_default_settings()["invoice"])

        return {
            "success": True,
            "data": invoice_settings
        }
    except Exception as e:
        logger.error(f"Failed to get invoice template: {e}")
        return {
            "success": True,
            "data": get_default_settings()["invoice"]
        }


@templates_router.post("/reset")
async def reset_template_settings(config: ClientConfig = Depends(get_client_config)):
    """Reset template settings to defaults"""
    try:
        supabase = SupabaseTool(config)
        defaults = get_default_settings()
        result = supabase.update_template_settings(defaults)

        return {
            "success": True,
            "data": result or defaults,
            "message": "Template settings reset to defaults"
        }
    except Exception as e:
        log_and_raise(500, "resetting template settings", e, logger)


@templates_router.get("/layouts")
async def get_available_layouts():
    """Get available PDF layout styles"""
    return {
        "success": True,
        "data": [
            {
                "id": "standard",
                "name": "Standard",
                "description": "Clean, professional layout with company info on the left"
            },
            {
                "id": "modern",
                "name": "Modern",
                "description": "Contemporary design with colored header band"
            },
            {
                "id": "minimal",
                "name": "Minimal",
                "description": "Elegant, centered design with maximum whitespace"
            }
        ]
    }
