"""
Admin Routes - Tenant Provisioning and Management

Endpoints for:
- VAPI provisioning (assistants + phone numbers)
- Tenant configuration management
- Usage tracking and statistics
- System administration

These endpoints require admin authentication (X-Admin-Token header).
"""

import logging
import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Header, BackgroundTasks
from pydantic import BaseModel, Field

from config.loader import ClientConfig, list_clients, get_client_config

logger = logging.getLogger(__name__)

admin_router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


# ==================== Pydantic Models ====================

class VAPIProvisionRequest(BaseModel):
    """Request to provision VAPI resources for a tenant"""
    tenant_id: str = Field(..., min_length=2, max_length=50)
    company_name: Optional[str] = None
    country_code: str = Field(default="ZA", description="Country for phone number")
    buy_phone_number: bool = Field(default=True, description="Whether to purchase a new phone number")
    use_existing_number_id: Optional[str] = Field(None, description="Use existing VAPI phone number ID")
    vapi_api_key: Optional[str] = Field(None, description="VAPI API key (overrides env var)")


class VAPIProvisionResponse(BaseModel):
    """Response from VAPI provisioning"""
    success: bool
    tenant_id: str
    inbound_assistant_id: Optional[str] = None
    outbound_assistant_id: Optional[str] = None
    phone_number_id: Optional[str] = None
    phone_number: Optional[str] = None
    config_updated: bool = False
    message: str


class TenantConfigUpdate(BaseModel):
    """Update tenant VAPI configuration"""
    vapi_api_key: Optional[str] = None
    vapi_phone_number_id: Optional[str] = None
    vapi_assistant_id: Optional[str] = None
    vapi_outbound_assistant_id: Optional[str] = None


class PhoneNumberSearchRequest(BaseModel):
    """Search for available phone numbers"""
    country_code: str = Field(default="ZA")
    area_code: Optional[str] = None
    limit: int = Field(default=5, ge=1, le=20)


# ==================== Admin Auth Dependency ====================

def verify_admin_token(x_admin_token: str = Header(None, alias="X-Admin-Token")) -> bool:
    """Verify admin authentication token"""
    admin_token = os.getenv("ADMIN_API_TOKEN")

    if not admin_token:
        # If no admin token configured, allow access (dev mode)
        logger.warning("No ADMIN_API_TOKEN configured - admin endpoints are unprotected")
        return True

    if x_admin_token != admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")

    return True


# ==================== VAPI Provisioning Endpoints ====================

@admin_router.post("/provision/vapi", response_model=VAPIProvisionResponse)
async def provision_vapi_for_tenant(
    request: VAPIProvisionRequest,
    background_tasks: BackgroundTasks,
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    Provision VAPI resources for a tenant.

    This endpoint:
    1. Creates inbound and outbound VAPI assistants
    2. Optionally purchases a phone number via Twilio
    3. Imports phone number to VAPI
    4. Updates the tenant's config.yaml with new IDs

    Requires:
    - VAPI_API_KEY environment variable (master account key)
    - TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN (for phone purchase)
    """
    from src.tools.vapi_tool import VAPIProvisioner

    # Get master VAPI API key (from request or environment)
    master_vapi_key = request.vapi_api_key or os.getenv("VAPI_API_KEY")
    if not master_vapi_key:
        raise HTTPException(
            status_code=500,
            detail="VAPI_API_KEY not configured. Provide vapi_api_key in request or set VAPI_API_KEY env var."
        )

    # Verify tenant exists
    try:
        config = ClientConfig(request.tenant_id)
        company_name = request.company_name or config.company_name
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Tenant configuration not found: {request.tenant_id}"
        )

    # Check if already provisioned
    if config.vapi_assistant_id and config.vapi_outbound_assistant_id:
        logger.warning(f"Tenant {request.tenant_id} already has VAPI assistants configured")
        # Allow re-provisioning but log it

    # Initialize provisioner
    provisioner = VAPIProvisioner(master_vapi_key)

    try:
        # Provision assistants
        result = provisioner.provision_tenant(
            client_id=request.tenant_id,
            company_name=company_name,
            phone_number_id=request.use_existing_number_id
        )

        response = VAPIProvisionResponse(
            success=bool(result.get("inbound_assistant_id")),
            tenant_id=request.tenant_id,
            inbound_assistant_id=result.get("inbound_assistant_id"),
            outbound_assistant_id=result.get("outbound_assistant_id"),
            phone_number_id=result.get("phone_number_id"),
            config_updated=False,
            message="Assistants created"
        )

        # Handle phone number provisioning
        if request.buy_phone_number and not request.use_existing_number_id:
            # Use Twilio provisioner for phone numbers
            twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
            twilio_token = os.getenv("TWILIO_AUTH_TOKEN")

            if twilio_sid and twilio_token:
                from src.tools.twilio_vapi_provisioner import TwilioVAPIProvisioner

                phone_provisioner = TwilioVAPIProvisioner(
                    twilio_account_sid=twilio_sid,
                    twilio_auth_token=twilio_token,
                    vapi_api_key=master_vapi_key
                )

                phone_result = phone_provisioner.provision_phone_for_tenant(
                    country_code=request.country_code,
                    client_id=request.tenant_id,
                    assistant_id=result.get("inbound_assistant_id")
                )

                if phone_result.get("success"):
                    response.phone_number_id = phone_result.get("vapi_id")
                    response.phone_number = phone_result.get("phone_number")
                    response.message = f"Provisioning complete. Phone: {response.phone_number}"
                else:
                    response.message = f"Assistants created. Phone provisioning failed: {phone_result.get('error', 'Unknown error')}"
            else:
                response.message = "Assistants created. Twilio credentials not configured for phone provisioning."

        # Update tenant config in background
        if response.success:
            background_tasks.add_task(
                update_tenant_config_file,
                tenant_id=request.tenant_id,
                vapi_api_key=master_vapi_key,
                inbound_assistant_id=response.inbound_assistant_id,
                outbound_assistant_id=response.outbound_assistant_id,
                phone_number_id=response.phone_number_id
            )
            response.config_updated = True

        return response

    except Exception as e:
        logger.error(f"VAPI provisioning failed for {request.tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/provision/vapi/{tenant_id}")
async def get_vapi_status(
    tenant_id: str,
    admin_verified: bool = Depends(verify_admin_token)
):
    """Get current VAPI provisioning status for a tenant"""
    try:
        config = ClientConfig(tenant_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tenant not found: {tenant_id}")

    return {
        "tenant_id": tenant_id,
        "company_name": config.company_name,
        "vapi_configured": bool(config.vapi_api_key),
        "inbound_assistant_id": config.vapi_assistant_id,
        "outbound_assistant_id": config.vapi_outbound_assistant_id,
        "phone_number_id": config.vapi_phone_number_id,
        "ready_for_calls": all([
            config.vapi_api_key,
            config.vapi_assistant_id or config.vapi_outbound_assistant_id,
            config.vapi_phone_number_id
        ])
    }


@admin_router.post("/provision/phone/search")
async def search_available_phones(
    request: PhoneNumberSearchRequest,
    admin_verified: bool = Depends(verify_admin_token)
):
    """Search for available phone numbers to purchase"""
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    vapi_key = os.getenv("VAPI_API_KEY")

    if not all([twilio_sid, twilio_token, vapi_key]):
        raise HTTPException(
            status_code=500,
            detail="Twilio/VAPI credentials not configured"
        )

    from src.tools.twilio_vapi_provisioner import TwilioVAPIProvisioner

    provisioner = TwilioVAPIProvisioner(twilio_sid, twilio_token, vapi_key)

    numbers = provisioner.get_available_numbers_for_client(
        country_code=request.country_code,
        area_code=request.area_code,
        limit=request.limit
    )

    return {
        "success": True,
        "country_code": request.country_code,
        "available_numbers": numbers,
        "count": len(numbers)
    }


@admin_router.patch("/provision/vapi/{tenant_id}/config")
async def update_tenant_vapi_config(
    tenant_id: str,
    update: TenantConfigUpdate,
    admin_verified: bool = Depends(verify_admin_token)
):
    """Manually update tenant VAPI configuration"""
    try:
        config = ClientConfig(tenant_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tenant not found: {tenant_id}")

    # Update config file
    updated = await update_tenant_config_file(
        tenant_id=tenant_id,
        vapi_api_key=update.vapi_api_key,
        inbound_assistant_id=update.vapi_assistant_id,
        outbound_assistant_id=update.vapi_outbound_assistant_id,
        phone_number_id=update.vapi_phone_number_id
    )

    return {
        "success": updated,
        "tenant_id": tenant_id,
        "message": "Configuration updated" if updated else "Update failed"
    }


# ==================== Tenant Management ====================

@admin_router.get("/tenants/summary")
async def get_all_tenants_summary(
    admin_verified: bool = Depends(verify_admin_token)
):
    """Get summary list of all tenants with key info."""
    summaries = []

    for client_id in list_clients():
        try:
            config = ClientConfig(client_id)
            summaries.append(TenantSummary(
                client_id=client_id,
                name=config.name,
                company_name=config.company_name,
                currency=config.currency,
                timezone=config.timezone,
                destinations_count=len(config.destination_names),
                vapi_configured=bool(config.vapi_api_key),
                sendgrid_configured=bool(config.sendgrid_api_key),
                supabase_configured=bool(config.supabase_url),
                status="active"
            ))
        except Exception as e:
            logger.warning(f"Could not load tenant {client_id}: {e}")
            continue

    return {
        "tenants": summaries,
        "count": len(summaries)
    }


@admin_router.get("/tenants")
async def list_tenants(
    admin_verified: bool = Depends(verify_admin_token)
):
    """List all configured tenants"""
    clients_dir = Path("clients")

    if not clients_dir.exists():
        return {"tenants": [], "count": 0}

    tenants = []
    for client_dir in clients_dir.iterdir():
        if client_dir.is_dir():
            config_file = client_dir / "client.yaml"
            if config_file.exists():
                try:
                    config = ClientConfig(client_dir.name)
                    tenants.append({
                        "tenant_id": client_dir.name,
                        "company_name": config.company_name,
                        "currency": config.currency,
                        "destinations": config.destination_names,
                        "vapi_configured": bool(config.vapi_api_key),
                        "sendgrid_configured": bool(config.sendgrid_api_key)
                    })
                except Exception as e:
                    logger.warning(f"Could not load config for {client_dir.name}: {e}")
                    tenants.append({
                        "tenant_id": client_dir.name,
                        "error": str(e)
                    })

    return {
        "tenants": tenants,
        "count": len(tenants)
    }


@admin_router.get("/tenants/{tenant_id}")
async def get_tenant_details(
    tenant_id: str,
    admin_verified: bool = Depends(verify_admin_token)
):
    """Get detailed tenant configuration"""
    try:
        config = ClientConfig(tenant_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tenant not found: {tenant_id}")

    return {
        "tenant_id": tenant_id,
        "client": {
            "name": config.name,
            "short_name": config.short_name,
            "company_name": config.company_name,
            "timezone": config.timezone,
            "currency": config.currency
        },
        "destinations": config.destinations,
        "consultants": config.consultants,
        "infrastructure": {
            "gcp_project": config.gcp_project_id,
            "gcp_region": config.gcp_region,
            "dataset": config.dataset_name,
            "supabase_configured": bool(config.supabase_url),
            "vapi": {
                "configured": bool(config.vapi_api_key),
                "assistant_id": config.vapi_assistant_id,
                "outbound_assistant_id": config.vapi_outbound_assistant_id,
                "phone_number_id": config.vapi_phone_number_id
            },
            "email": {
                "sendgrid_configured": bool(config.sendgrid_api_key),
                "from_email": config.sendgrid_from_email
            }
        }
    }


# ==================== Helper Functions ====================

async def update_tenant_config_file(
    tenant_id: str,
    vapi_api_key: str = None,
    inbound_assistant_id: str = None,
    outbound_assistant_id: str = None,
    phone_number_id: str = None
) -> bool:
    """
    Update tenant's client.yaml with new VAPI configuration.

    Note: This modifies the YAML file directly. The API key is stored
    as an environment variable reference for security.
    """
    config_path = Path(f"clients/{tenant_id}/client.yaml")

    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        return False

    try:
        # Read current config
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)

        # Ensure infrastructure.vapi section exists
        if 'infrastructure' not in config_data:
            config_data['infrastructure'] = {}
        if 'vapi' not in config_data['infrastructure']:
            config_data['infrastructure']['vapi'] = {}

        vapi_config = config_data['infrastructure']['vapi']

        # Update values (only if provided)
        if vapi_api_key:
            # Store as env var reference for security
            env_var_name = f"{tenant_id.upper()}_VAPI_API_KEY"
            vapi_config['api_key'] = f"${{{env_var_name}}}"
            # Also set the actual env var
            os.environ[env_var_name] = vapi_api_key
            logger.info(f"Set {env_var_name} environment variable")

        if inbound_assistant_id:
            vapi_config['assistant_id'] = inbound_assistant_id

        if outbound_assistant_id:
            vapi_config['outbound_assistant_id'] = outbound_assistant_id

        if phone_number_id:
            vapi_config['phone_number_id'] = phone_number_id

        # Write updated config
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

        logger.info(f"Updated VAPI config for {tenant_id}")

        # Clear config cache to reload
        from config.loader import _config_cache
        if tenant_id in _config_cache:
            del _config_cache[tenant_id]

        return True

    except Exception as e:
        logger.error(f"Failed to update config for {tenant_id}: {e}")
        return False


# ==================== Usage & Stats Models ====================

class TenantUsageStats(BaseModel):
    """Usage statistics for a tenant"""
    client_id: str
    period: str
    quotes_generated: int = 0
    invoices_created: int = 0
    invoices_paid: int = 0
    total_revenue: float = 0
    emails_sent: int = 0
    calls_made: int = 0
    active_users: int = 0
    total_clients: int = 0


class SystemHealthResponse(BaseModel):
    """System health status"""
    status: str
    total_tenants: int
    active_tenants: int
    database_status: str
    timestamp: str


class TenantSummary(BaseModel):
    """Summary info for tenant list"""
    client_id: str
    name: str
    company_name: str
    currency: str
    timezone: str
    destinations_count: int
    vapi_configured: bool
    sendgrid_configured: bool
    supabase_configured: bool
    status: str = "active"


# ==================== Usage Tracking Endpoints ====================

@admin_router.get("/tenants/{tenant_id}/usage")
async def get_tenant_usage(
    tenant_id: str,
    period: str = "month",
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    Get usage statistics for a specific tenant.

    Period options: day, week, month, quarter, year
    """
    # Verify tenant exists
    try:
        config = ClientConfig(tenant_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tenant not found: {tenant_id}")

    # Calculate date range
    now = datetime.utcnow()
    period_days = {
        "day": 1,
        "week": 7,
        "month": 30,
        "quarter": 90,
        "year": 365
    }
    days = period_days.get(period, 30)
    start_date = now - timedelta(days=days)

    # Get stats from database
    try:
        from src.tools.supabase_tool import SupabaseTool
        supabase = SupabaseTool(tenant_id)

        # Quotes count
        quotes_result = supabase.client.table("quotes").select("id", count="exact").gte(
            "created_at", start_date.isoformat()
        ).execute()
        quotes_count = quotes_result.count or 0

        # Invoices data
        invoices_result = supabase.client.table("invoices").select(
            "id,total_amount,status"
        ).gte("created_at", start_date.isoformat()).execute()
        invoices_data = invoices_result.data or []
        invoices_count = len(invoices_data)
        invoices_paid = len([i for i in invoices_data if i.get("status") == "paid"])
        total_revenue = sum(
            float(i.get("total_amount", 0) or 0)
            for i in invoices_data if i.get("status") == "paid"
        )

        # Active users
        users_result = supabase.client.table("organization_users").select(
            "id", count="exact"
        ).eq("is_active", True).execute()
        active_users = users_result.count or 0

        # Total CRM clients
        clients_result = supabase.client.table("crm_clients").select(
            "id", count="exact"
        ).execute()
        total_clients = clients_result.count or 0

        return TenantUsageStats(
            client_id=tenant_id,
            period=period,
            quotes_generated=quotes_count,
            invoices_created=invoices_count,
            invoices_paid=invoices_paid,
            total_revenue=total_revenue,
            emails_sent=0,  # Would need email tracking table
            calls_made=0,   # Would need calls tracking table
            active_users=active_users,
            total_clients=total_clients
        )

    except Exception as e:
        logger.error(f"Failed to get usage for {tenant_id}: {e}")
        return TenantUsageStats(
            client_id=tenant_id,
            period=period
        )


@admin_router.get("/usage/summary")
async def get_all_tenants_usage_summary(
    period: str = "month",
    admin_verified: bool = Depends(verify_admin_token)
):
    """Get aggregated usage across all tenants."""
    all_usage = []

    for client_id in list_clients():
        try:
            usage = await get_tenant_usage(client_id, period, admin_verified)
            all_usage.append(usage)
        except Exception as e:
            logger.warning(f"Could not get usage for {client_id}: {e}")
            continue

    # Calculate totals
    totals = {
        "total_quotes": sum(u.quotes_generated for u in all_usage),
        "total_invoices": sum(u.invoices_created for u in all_usage),
        "total_invoices_paid": sum(u.invoices_paid for u in all_usage),
        "total_revenue": sum(u.total_revenue for u in all_usage),
        "total_active_users": sum(u.active_users for u in all_usage),
        "total_crm_clients": sum(u.total_clients for u in all_usage),
        "tenant_count": len(all_usage)
    }

    return {
        "period": period,
        "totals": totals,
        "by_tenant": [u.dict() for u in all_usage]
    }


@admin_router.get("/health")
async def get_system_health(
    admin_verified: bool = Depends(verify_admin_token)
):
    """Get overall system health status."""
    tenants = list_clients()

    # Check database connectivity
    db_status = "healthy"
    try:
        if tenants:
            from src.tools.supabase_tool import SupabaseTool
            supabase = SupabaseTool(tenants[0])
            supabase.client.table("quotes").select("id").limit(1).execute()
    except Exception as e:
        db_status = f"error: {str(e)[:100]}"

    return SystemHealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        total_tenants=len(tenants),
        active_tenants=len(tenants),
        database_status=db_status,
        timestamp=datetime.utcnow().isoformat()
    )


# ==================== Include Router ====================

def include_admin_router(app):
    """Include admin router in FastAPI app"""
    app.include_router(admin_router)
