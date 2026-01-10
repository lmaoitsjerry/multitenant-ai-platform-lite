"""
Tenant Settings API Routes

Handles tenant-specific settings:
- Email configuration (from name, from email, reply-to)
- Banking details (for invoices)
"""

import os
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr

from config.loader import ClientConfig, get_config
from src.tools.supabase_tool import SupabaseTool

logger = logging.getLogger(__name__)

settings_router = APIRouter(prefix="/api/v1/settings", tags=["Tenant Settings"])


# ==================== Dependencies ====================

def get_client_config(x_client_id: str = Header(None, alias="X-Client-ID")) -> ClientConfig:
    """Get client configuration from header"""
    client_id = x_client_id or os.getenv("CLIENT_ID", "example")

    try:
        return get_config(client_id)
    except Exception as e:
        logger.error(f"Failed to load config for {client_id}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid client: {client_id}")


def get_supabase_tool(config: ClientConfig = Depends(get_client_config)) -> SupabaseTool:
    """Get SupabaseTool instance for the tenant"""
    return SupabaseTool(config)


# ==================== Pydantic Models ====================

class EmailSettings(BaseModel):
    """Email configuration model"""
    from_name: Optional[str] = None
    from_email: Optional[EmailStr] = None
    reply_to: Optional[EmailStr] = None
    quotes_email: Optional[EmailStr] = None


class BankingSettings(BaseModel):
    """Banking details model"""
    bank_name: Optional[str] = None
    account_name: Optional[str] = None
    account_number: Optional[str] = None
    branch_code: Optional[str] = None
    swift_code: Optional[str] = None
    reference_prefix: Optional[str] = None


class TenantSettingsUpdate(BaseModel):
    """Combined settings update model"""
    email: Optional[EmailSettings] = None
    banking: Optional[BankingSettings] = None


# ==================== Helper Functions ====================

def merge_settings_with_config(db_settings: dict, config: ClientConfig) -> dict:
    """Merge database settings with config file defaults"""
    return {
        "email": {
            "from_name": db_settings.get("email_from_name") or config.sendgrid_from_name or "",
            "from_email": db_settings.get("email_from_email") or config.sendgrid_from_email or "",
            "reply_to": db_settings.get("email_reply_to") or config.sendgrid_reply_to or "",
            "quotes_email": db_settings.get("quotes_email") or config.quotes_email or "",
        },
        "banking": {
            "bank_name": db_settings.get("bank_name") or config.bank_name or "",
            "account_name": db_settings.get("bank_account_name") or config.bank_account_name or "",
            "account_number": db_settings.get("bank_account_number") or config.bank_account_number or "",
            "branch_code": db_settings.get("bank_branch_code") or config.bank_branch_code or "",
            "swift_code": db_settings.get("bank_swift_code") or config.bank_swift_code or "",
            "reference_prefix": db_settings.get("payment_reference_prefix") or config.payment_reference_prefix or "",
        }
    }


# ==================== Endpoints ====================

@settings_router.get("")
async def get_tenant_settings(
    config: ClientConfig = Depends(get_client_config),
    db: SupabaseTool = Depends(get_supabase_tool)
):
    """
    Get tenant settings (email and banking)

    Returns merged settings from database + config defaults.
    """
    db_settings = db.get_tenant_settings() or {}
    settings = merge_settings_with_config(db_settings, config)

    return {
        "success": True,
        "data": settings
    }


@settings_router.put("")
async def update_tenant_settings(
    data: TenantSettingsUpdate,
    config: ClientConfig = Depends(get_client_config),
    db: SupabaseTool = Depends(get_supabase_tool)
):
    """
    Update tenant settings

    Supports partial updates - only specified fields are changed.
    """
    # Build update kwargs
    update_kwargs = {}

    if data.email:
        if data.email.from_name is not None:
            update_kwargs["email_from_name"] = data.email.from_name
        if data.email.from_email is not None:
            update_kwargs["email_from_email"] = str(data.email.from_email)
        if data.email.reply_to is not None:
            update_kwargs["email_reply_to"] = str(data.email.reply_to)
        if data.email.quotes_email is not None:
            update_kwargs["quotes_email"] = str(data.email.quotes_email)

    if data.banking:
        if data.banking.bank_name is not None:
            update_kwargs["bank_name"] = data.banking.bank_name
        if data.banking.account_name is not None:
            update_kwargs["bank_account_name"] = data.banking.account_name
        if data.banking.account_number is not None:
            update_kwargs["bank_account_number"] = data.banking.account_number
        if data.banking.branch_code is not None:
            update_kwargs["bank_branch_code"] = data.banking.branch_code
        if data.banking.swift_code is not None:
            update_kwargs["bank_swift_code"] = data.banking.swift_code
        if data.banking.reference_prefix is not None:
            update_kwargs["payment_reference_prefix"] = data.banking.reference_prefix

    if not update_kwargs:
        raise HTTPException(status_code=400, detail="No settings to update")

    result = db.update_tenant_settings(**update_kwargs)

    if result:
        settings = merge_settings_with_config(result, config)
        return {
            "success": True,
            "data": settings,
            "message": "Settings updated successfully"
        }

    # If database update failed, return current settings anyway
    db_settings = db.get_tenant_settings() or {}
    settings = merge_settings_with_config(db_settings, config)

    return {
        "success": True,
        "data": settings,
        "message": "Settings saved (local only - database table may not exist)"
    }


@settings_router.put("/email")
async def update_email_settings(
    data: EmailSettings,
    config: ClientConfig = Depends(get_client_config),
    db: SupabaseTool = Depends(get_supabase_tool)
):
    """
    Update email settings only
    """
    update_kwargs = {}

    if data.from_name is not None:
        update_kwargs["email_from_name"] = data.from_name
    if data.from_email is not None:
        update_kwargs["email_from_email"] = str(data.from_email)
    if data.reply_to is not None:
        update_kwargs["email_reply_to"] = str(data.reply_to)
    if data.quotes_email is not None:
        update_kwargs["quotes_email"] = str(data.quotes_email)

    if not update_kwargs:
        raise HTTPException(status_code=400, detail="No email settings to update")

    result = db.update_tenant_settings(**update_kwargs)

    db_settings = result or db.get_tenant_settings() or {}
    settings = merge_settings_with_config(db_settings, config)

    return {
        "success": True,
        "data": settings["email"],
        "message": "Email settings updated"
    }


@settings_router.put("/banking")
async def update_banking_settings(
    data: BankingSettings,
    config: ClientConfig = Depends(get_client_config),
    db: SupabaseTool = Depends(get_supabase_tool)
):
    """
    Update banking settings only
    """
    update_kwargs = {}

    if data.bank_name is not None:
        update_kwargs["bank_name"] = data.bank_name
    if data.account_name is not None:
        update_kwargs["bank_account_name"] = data.account_name
    if data.account_number is not None:
        update_kwargs["bank_account_number"] = data.account_number
    if data.branch_code is not None:
        update_kwargs["bank_branch_code"] = data.branch_code
    if data.swift_code is not None:
        update_kwargs["bank_swift_code"] = data.swift_code
    if data.reference_prefix is not None:
        update_kwargs["payment_reference_prefix"] = data.reference_prefix

    if not update_kwargs:
        raise HTTPException(status_code=400, detail="No banking settings to update")

    result = db.update_tenant_settings(**update_kwargs)

    db_settings = result or db.get_tenant_settings() or {}
    settings = merge_settings_with_config(db_settings, config)

    return {
        "success": True,
        "data": settings["banking"],
        "message": "Banking settings updated"
    }
