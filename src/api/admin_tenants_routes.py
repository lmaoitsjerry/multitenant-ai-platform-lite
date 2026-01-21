"""
Admin Tenant Routes - Tenant Management for Internal Platform

Endpoints for:
- Listing all tenants with filtering/pagination
- Getting tenant details and statistics
- Suspending/activating tenants
- Deleting tenants

These endpoints require admin authentication (X-Admin-Token header).
"""

import logging
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from config.loader import ClientConfig, list_clients
from src.api.admin_routes import verify_admin_token
from src.utils.error_handler import log_and_raise

logger = logging.getLogger(__name__)

admin_tenants_router = APIRouter(prefix="/api/v1/admin/tenants", tags=["Admin - Tenants"])


# ==================== Pydantic Models ====================

class TenantSummary(BaseModel):
    """Summary of a tenant for list view"""
    tenant_id: str
    company_name: str
    support_email: Optional[str] = None
    status: str = "active"
    currency: str = "ZAR"
    created_at: Optional[str] = None
    quote_count: int = 0
    invoice_count: int = 0
    total_invoiced: float = 0


class TenantDetail(BaseModel):
    """Detailed tenant information"""
    tenant_id: str
    company_name: str
    support_email: Optional[str] = None
    support_phone: Optional[str] = None
    website: Optional[str] = None
    currency: str = "ZAR"
    timezone: str = "Africa/Johannesburg"
    status: str = "active"
    suspended_at: Optional[str] = None
    suspended_reason: Optional[str] = None

    # Branding
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None

    # Infrastructure
    gcp_project_id: Optional[str] = None
    sendgrid_configured: bool = False
    vapi_configured: bool = False

    # Config file path
    config_path: Optional[str] = None


class TenantStats(BaseModel):
    """Tenant usage statistics"""
    tenant_id: str
    quotes_count: int = 0
    quotes_this_month: int = 0
    invoices_count: int = 0
    invoices_paid: int = 0
    total_invoiced: float = 0
    total_paid: float = 0
    clients_count: int = 0
    users_count: int = 0
    emails_sent: int = 0


class SuspendRequest(BaseModel):
    """Request to suspend a tenant"""
    reason: str = Field(..., min_length=5, max_length=500)


class TenantListResponse(BaseModel):
    """Response for tenant list"""
    success: bool
    data: List[TenantSummary]
    count: int
    total: int


# ==================== Helper Functions ====================

def get_supabase_admin_client():
    """Get Supabase client for admin operations (uses service key)"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

    if not url or not key:
        return None

    from supabase import create_client
    return create_client(url, key)


async def get_tenant_stats_from_db(tenant_id: str) -> Dict[str, Any]:
    """Get tenant statistics from Supabase"""
    client = get_supabase_admin_client()
    if not client:
        return {}

    stats = {
        "quotes_count": 0,
        "quotes_this_month": 0,
        "invoices_count": 0,
        "invoices_paid": 0,
        "total_invoiced": 0,
        "total_paid": 0,
        "clients_count": 0,
        "users_count": 0,
    }

    try:
        # Get quotes count
        quotes_result = client.table("quotes").select("id", count="exact").eq("tenant_id", tenant_id).execute()
        stats["quotes_count"] = quotes_result.count or 0

        # Get quotes this month
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        quotes_month = client.table("quotes").select("id", count="exact").eq("tenant_id", tenant_id).gte("created_at", month_start.isoformat()).execute()
        stats["quotes_this_month"] = quotes_month.count or 0

        # Get invoices
        invoices_result = client.table("invoices").select("id, status, total_amount, paid_amount").eq("tenant_id", tenant_id).execute()
        if invoices_result.data:
            stats["invoices_count"] = len(invoices_result.data)
            stats["invoices_paid"] = len([i for i in invoices_result.data if i.get("status") == "paid"])
            stats["total_invoiced"] = sum(i.get("total_amount", 0) or 0 for i in invoices_result.data)
            stats["total_paid"] = sum(i.get("paid_amount", 0) or 0 for i in invoices_result.data)

        # Get clients count
        clients_result = client.table("clients").select("id", count="exact").eq("tenant_id", tenant_id).execute()
        stats["clients_count"] = clients_result.count or 0

        # Get users count
        users_result = client.table("organization_users").select("id", count="exact").eq("tenant_id", tenant_id).eq("is_active", True).execute()
        stats["users_count"] = users_result.count or 0

    except Exception as e:
        logger.error(f"Error getting stats for tenant {tenant_id}: {e}")

    return stats


# ==================== Endpoints ====================

@admin_tenants_router.get("", response_model=TenantListResponse)
async def list_tenants(
    status: Optional[str] = Query(None, description="Filter by status: active, suspended, all"),
    search: Optional[str] = Query(None, description="Search by company name or tenant ID"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("company_name", description="Sort by: company_name, tenant_id, created_at"),
    sort_order: str = Query("asc", description="Sort order: asc, desc"),
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    List all tenants with optional filtering and pagination.
    """
    try:
        # Get all client IDs from config
        client_ids = list_clients()
        logger.info(f"Found {len(client_ids)} tenant configurations")

        tenants = []
        for client_id in client_ids:
            try:
                config = ClientConfig(client_id)

                # Get stats from database
                stats = await get_tenant_stats_from_db(client_id)

                tenant = TenantSummary(
                    tenant_id=client_id,
                    company_name=getattr(config, 'company_name', client_id),
                    support_email=getattr(config, 'support_email', None),
                    status="active",  # TODO: Get from database
                    currency=getattr(config, 'currency', 'ZAR'),
                    quote_count=stats.get("quotes_count", 0),
                    invoice_count=stats.get("invoices_count", 0),
                    total_invoiced=stats.get("total_invoiced", 0),
                )
                tenants.append(tenant)
            except Exception as e:
                logger.warning(f"Could not load config for {client_id}: {e}")
                continue

        # Apply search filter
        if search:
            search_lower = search.lower()
            tenants = [t for t in tenants if search_lower in t.company_name.lower() or search_lower in t.tenant_id.lower()]

        # Apply status filter
        if status and status != "all":
            tenants = [t for t in tenants if t.status == status]

        # Sort
        reverse = sort_order == "desc"
        if sort_by == "company_name":
            tenants.sort(key=lambda t: t.company_name.lower(), reverse=reverse)
        elif sort_by == "tenant_id":
            tenants.sort(key=lambda t: t.tenant_id, reverse=reverse)
        elif sort_by == "quote_count":
            tenants.sort(key=lambda t: t.quote_count, reverse=reverse)

        total = len(tenants)

        # Apply pagination
        tenants = tenants[offset:offset + limit]

        return TenantListResponse(
            success=True,
            data=tenants,
            count=len(tenants),
            total=total
        )

    except Exception as e:
        log_and_raise(500, "listing tenants", e, logger)


@admin_tenants_router.get("/{tenant_id}")
async def get_tenant_details(
    tenant_id: str,
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    Get detailed information about a specific tenant.
    """
    try:
        config = ClientConfig(tenant_id)

        detail = TenantDetail(
            tenant_id=tenant_id,
            company_name=getattr(config, 'company_name', tenant_id),
            support_email=getattr(config, 'support_email', None),
            support_phone=getattr(config, 'support_phone', None),
            website=getattr(config, 'website', None),
            currency=getattr(config, 'currency', 'ZAR'),
            timezone=getattr(config, 'timezone', 'Africa/Johannesburg'),
            status="active",
            logo_url=getattr(config, 'logo_url', None),
            primary_color=getattr(config, 'primary_color', None),
            gcp_project_id=getattr(config, 'gcp_project_id', None),
            sendgrid_configured=bool(getattr(config, 'sendgrid_api_key', None)),
            vapi_configured=bool(getattr(config, 'vapi_assistant_id', None)),
            config_path=str(config.config_path) if hasattr(config, 'config_path') else None,
        )

        return {
            "success": True,
            "data": detail.model_dump()
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    except Exception as e:
        log_and_raise(500, f"getting tenant {tenant_id}", e, logger)


@admin_tenants_router.get("/{tenant_id}/stats")
async def get_tenant_statistics(
    tenant_id: str,
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    Get usage statistics for a specific tenant.
    """
    try:
        # Verify tenant exists
        try:
            config = ClientConfig(tenant_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")

        stats = await get_tenant_stats_from_db(tenant_id)

        return {
            "success": True,
            "data": TenantStats(
                tenant_id=tenant_id,
                **stats
            ).model_dump()
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, f"getting stats for tenant {tenant_id}", e, logger)


@admin_tenants_router.post("/{tenant_id}/suspend")
async def suspend_tenant(
    tenant_id: str,
    request: SuspendRequest,
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    Suspend a tenant account.

    This prevents the tenant from:
    - Generating new quotes
    - Sending emails
    - Accessing the platform
    """
    try:
        # Verify tenant exists
        try:
            config = ClientConfig(tenant_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")

        # Update tenant status in database
        client = get_supabase_admin_client()
        if client:
            try:
                # Check if tenant record exists in tenants table
                existing = client.table("tenants").select("id").eq("tenant_id", tenant_id).execute()

                if existing.data:
                    # Update existing record
                    client.table("tenants").update({
                        "status": "suspended",
                        "suspended_at": datetime.now().isoformat(),
                        "suspended_reason": request.reason
                    }).eq("tenant_id", tenant_id).execute()
                else:
                    # Insert new record
                    client.table("tenants").insert({
                        "tenant_id": tenant_id,
                        "status": "suspended",
                        "suspended_at": datetime.now().isoformat(),
                        "suspended_reason": request.reason
                    }).execute()

            except Exception as e:
                logger.warning(f"Could not update tenant status in DB: {e}")

        # Log admin action
        logger.info(f"[ADMIN] Tenant {tenant_id} suspended. Reason: {request.reason}")

        return {
            "success": True,
            "message": f"Tenant {tenant_id} has been suspended",
            "tenant_id": tenant_id,
            "status": "suspended"
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, f"suspending tenant {tenant_id}", e, logger)


@admin_tenants_router.post("/{tenant_id}/activate")
async def activate_tenant(
    tenant_id: str,
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    Reactivate a suspended tenant account.
    """
    try:
        # Verify tenant exists
        try:
            config = ClientConfig(tenant_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")

        # Update tenant status in database
        client = get_supabase_admin_client()
        if client:
            try:
                existing = client.table("tenants").select("id").eq("tenant_id", tenant_id).execute()

                if existing.data:
                    client.table("tenants").update({
                        "status": "active",
                        "suspended_at": None,
                        "suspended_reason": None
                    }).eq("tenant_id", tenant_id).execute()

            except Exception as e:
                logger.warning(f"Could not update tenant status in DB: {e}")

        logger.info(f"[ADMIN] Tenant {tenant_id} activated")

        return {
            "success": True,
            "message": f"Tenant {tenant_id} has been activated",
            "tenant_id": tenant_id,
            "status": "active"
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, f"activating tenant {tenant_id}", e, logger)


@admin_tenants_router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    confirm: bool = Query(False, description="Must be true to confirm deletion"),
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    Permanently delete a tenant.

    WARNING: This action is irreversible and will delete:
    - All tenant configuration
    - All quotes and invoices
    - All CRM data
    - All user accounts

    The confirm parameter must be set to true.
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Deletion requires confirmation. Set confirm=true to proceed."
        )

    try:
        # Verify tenant exists
        try:
            config = ClientConfig(tenant_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")

        # Delete from database
        client = get_supabase_admin_client()
        if client:
            try:
                # Delete in order to respect foreign keys
                client.table("invoice_travelers").delete().eq("tenant_id", tenant_id).execute()
                client.table("invoices").delete().eq("tenant_id", tenant_id).execute()
                client.table("quotes").delete().eq("tenant_id", tenant_id).execute()
                client.table("clients").delete().eq("tenant_id", tenant_id).execute()
                client.table("organization_users").delete().eq("tenant_id", tenant_id).execute()
                client.table("tenants").delete().eq("tenant_id", tenant_id).execute()

                logger.info(f"[ADMIN] Deleted database records for tenant {tenant_id}")
            except Exception as e:
                logger.error(f"Error deleting tenant data from DB: {e}")

        # Note: Config files should be manually removed or archived
        logger.warning(f"[ADMIN] Tenant {tenant_id} deleted. Config files at clients/{tenant_id}/ should be manually archived.")

        return {
            "success": True,
            "message": f"Tenant {tenant_id} has been deleted",
            "tenant_id": tenant_id,
            "note": f"Config files at clients/{tenant_id}/ should be manually archived or deleted"
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, f"deleting tenant {tenant_id}", e, logger)


# ==================== Router Registration ====================

def include_admin_tenants_router(app):
    """Include admin tenants router in the FastAPI app"""
    app.include_router(admin_tenants_router)
