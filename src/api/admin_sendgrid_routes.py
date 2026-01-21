"""
Admin SendGrid Routes - Email Management

Endpoints for:
- Listing SendGrid subusers
- Getting subuser statistics
- Enabling/disabling subusers
- Global email statistics

These endpoints require admin authentication (X-Admin-Token header).
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from config.loader import list_clients, ClientConfig
from src.api.admin_routes import verify_admin_token
from src.services.sendgrid_admin import get_sendgrid_admin_service
from src.utils.error_handler import log_and_raise

logger = logging.getLogger(__name__)

admin_sendgrid_router = APIRouter(prefix="/api/v1/admin/sendgrid", tags=["Admin - SendGrid"])


# ==================== Pydantic Models ====================

class SubuserInfo(BaseModel):
    """SendGrid subuser information"""
    username: str
    email: Optional[str] = None
    disabled: bool = False
    tenant_id: Optional[str] = None
    tenant_name: Optional[str] = None


class SubuserStats(BaseModel):
    """Email statistics for a subuser"""
    username: str
    period_days: int
    totals: Dict[str, Any]
    daily: Optional[List[Dict[str, Any]]] = None


class GlobalEmailStats(BaseModel):
    """Platform-wide email statistics"""
    period_days: int
    totals: Dict[str, Any]


# ==================== Helper Functions ====================

def match_subuser_to_tenant(username: str) -> tuple[Optional[str], Optional[str]]:
    """
    Try to match a SendGrid subuser to a tenant.

    Returns:
        Tuple of (tenant_id, company_name) or (None, None)
    """
    # Try to find tenant by sendgrid username in config
    client_ids = list_clients()

    for client_id in client_ids:
        try:
            config = ClientConfig(client_id)
            sg_username = getattr(config, 'sendgrid_username', None)

            if sg_username and sg_username == username:
                company_name = getattr(config, 'company_name', client_id)
                return client_id, company_name

            # Also check if username contains tenant ID
            if client_id in username:
                company_name = getattr(config, 'company_name', client_id)
                return client_id, company_name

        except Exception:
            continue

    return None, None


# ==================== Endpoints ====================

@admin_sendgrid_router.get("/subusers")
async def list_sendgrid_subusers(
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    List all SendGrid subusers with tenant matching.

    Returns subusers enriched with tenant information where possible.
    """
    try:
        service = get_sendgrid_admin_service()

        if not service.is_available():
            return {
                "success": True,
                "data": [],
                "message": "SendGrid not configured"
            }

        subusers = service.list_subusers()

        # Enrich with tenant info
        enriched_subusers = []
        for su in subusers:
            tenant_id, tenant_name = match_subuser_to_tenant(su["username"])

            enriched_subusers.append(SubuserInfo(
                username=su["username"],
                email=su.get("email"),
                disabled=su.get("disabled", False),
                tenant_id=tenant_id,
                tenant_name=tenant_name
            ))

        return {
            "success": True,
            "data": [su.model_dump() for su in enriched_subusers],
            "count": len(enriched_subusers)
        }

    except Exception as e:
        log_and_raise(500, "listing SendGrid subusers", e, logger)


@admin_sendgrid_router.get("/subusers/{username}/stats")
async def get_subuser_statistics(
    username: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    Get email statistics for a specific SendGrid subuser.
    """
    try:
        service = get_sendgrid_admin_service()

        if not service.is_available():
            raise HTTPException(status_code=503, detail="SendGrid not configured")

        stats = service.get_subuser_stats(username, days)

        if "error" in stats:
            raise HTTPException(status_code=400, detail=stats["error"])

        return {
            "success": True,
            "data": stats
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "retrieving subuser statistics", e, logger)


@admin_sendgrid_router.post("/subusers/{username}/disable")
async def disable_sendgrid_subuser(
    username: str,
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    Disable a SendGrid subuser (stop them from sending emails).
    """
    try:
        service = get_sendgrid_admin_service()

        if not service.is_available():
            raise HTTPException(status_code=503, detail="SendGrid not configured")

        success = service.disable_subuser(username)

        if success:
            logger.info(f"[ADMIN] Disabled SendGrid subuser: {username}")
            return {
                "success": True,
                "message": f"Subuser {username} has been disabled",
                "username": username,
                "disabled": True
            }
        else:
            raise HTTPException(status_code=400, detail=f"Failed to disable subuser {username}")

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "disabling SendGrid subuser", e, logger)


@admin_sendgrid_router.post("/subusers/{username}/enable")
async def enable_sendgrid_subuser(
    username: str,
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    Enable a SendGrid subuser.
    """
    try:
        service = get_sendgrid_admin_service()

        if not service.is_available():
            raise HTTPException(status_code=503, detail="SendGrid not configured")

        success = service.enable_subuser(username)

        if success:
            logger.info(f"[ADMIN] Enabled SendGrid subuser: {username}")
            return {
                "success": True,
                "message": f"Subuser {username} has been enabled",
                "username": username,
                "disabled": False
            }
        else:
            raise HTTPException(status_code=400, detail=f"Failed to enable subuser {username}")

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "enabling SendGrid subuser", e, logger)


@admin_sendgrid_router.get("/stats")
async def get_global_email_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    Get platform-wide email statistics.
    """
    try:
        service = get_sendgrid_admin_service()

        if not service.is_available():
            return {
                "success": True,
                "data": {
                    "period_days": days,
                    "totals": {
                        "requests": 0,
                        "delivered": 0,
                        "opens": 0,
                        "bounces": 0,
                        "open_rate": 0,
                        "delivery_rate": 0
                    }
                },
                "message": "SendGrid not configured"
            }

        stats = service.get_global_stats(days)

        if "error" in stats:
            return {
                "success": True,
                "data": stats,
                "message": stats["error"]
            }

        return {
            "success": True,
            "data": stats
        }

    except Exception as e:
        log_and_raise(500, "retrieving global SendGrid stats", e, logger)


# ==================== Tenant Credential Management ====================

class SubuserCredentials(BaseModel):
    """SendGrid subuser credentials to store for a tenant"""
    api_key: str
    username: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None


@admin_sendgrid_router.post("/tenants/{tenant_id}/credentials")
async def store_sendgrid_credentials(
    tenant_id: str,
    credentials: SubuserCredentials,
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    Store SendGrid subuser credentials for a tenant.

    This enables the tenant to send emails using their dedicated SendGrid subuser.
    The credentials are stored in the tenant_settings table.
    """
    try:
        # Verify tenant exists
        try:
            config = ClientConfig(tenant_id)
        except Exception:
            raise HTTPException(status_code=404, detail=f"Tenant not found: {tenant_id}")

        from src.tools.supabase_tool import SupabaseTool
        supabase = SupabaseTool(config)

        # Store credentials in tenant_settings
        result = supabase.update_tenant_settings(
            sendgrid_api_key=credentials.api_key,
            sendgrid_username=credentials.username,
            email_from_email=credentials.from_email,
            email_from_name=credentials.from_name
        )

        if result:
            logger.info(f"[ADMIN] Stored SendGrid credentials for tenant: {tenant_id}")
            return {
                "success": True,
                "message": f"SendGrid credentials stored for {tenant_id}",
                "tenant_id": tenant_id,
                "username": credentials.username
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to store credentials")

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "storing SendGrid credentials", e, logger)


@admin_sendgrid_router.get("/tenants/{tenant_id}/credentials")
async def get_sendgrid_credentials(
    tenant_id: str,
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    Get SendGrid configuration status for a tenant.

    Returns whether credentials are configured (but not the actual API key for security).
    """
    try:
        # Verify tenant exists
        try:
            config = ClientConfig(tenant_id)
        except Exception:
            raise HTTPException(status_code=404, detail=f"Tenant not found: {tenant_id}")

        from src.tools.supabase_tool import SupabaseTool
        supabase = SupabaseTool(config)

        settings = supabase.get_tenant_settings()

        # Check if credentials are in database
        db_configured = bool(settings and settings.get('sendgrid_api_key'))

        # Check if credentials are in config file
        config_configured = bool(config.sendgrid_api_key)

        return {
            "success": True,
            "tenant_id": tenant_id,
            "configured": db_configured or config_configured,
            "source": "database" if db_configured else ("config" if config_configured else "none"),
            "username": settings.get('sendgrid_username') if settings else None,
            "from_email": settings.get('email_from_email') if settings else config.sendgrid_from_email,
            "from_name": settings.get('email_from_name') if settings else config.sendgrid_from_name
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "retrieving SendGrid credentials", e, logger)


@admin_sendgrid_router.delete("/tenants/{tenant_id}/credentials")
async def delete_sendgrid_credentials(
    tenant_id: str,
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    Remove SendGrid credentials for a tenant from the database.

    The tenant will fall back to config file credentials (if any).
    """
    try:
        # Verify tenant exists
        try:
            config = ClientConfig(tenant_id)
        except Exception:
            raise HTTPException(status_code=404, detail=f"Tenant not found: {tenant_id}")

        from src.tools.supabase_tool import SupabaseTool
        supabase = SupabaseTool(config)

        # Clear credentials by setting to empty strings
        result = supabase.update_tenant_settings(
            sendgrid_api_key="",
            sendgrid_username=""
        )

        if result:
            logger.info(f"[ADMIN] Removed SendGrid credentials for tenant: {tenant_id}")
            return {
                "success": True,
                "message": f"SendGrid credentials removed for {tenant_id}",
                "tenant_id": tenant_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to remove credentials")

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "removing SendGrid credentials", e, logger)


# ==================== Router Registration ====================

def include_admin_sendgrid_router(app):
    """Include admin SendGrid router in the FastAPI app"""
    app.include_router(admin_sendgrid_router)
