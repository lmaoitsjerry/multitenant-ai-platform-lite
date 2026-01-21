"""
Privacy API Routes - GDPR/POPIA Compliance

Implements data subject rights:
- Consent management
- Data Subject Access Requests (DSAR)
- Data export (portability)
- Data erasure (right to be forgotten)
- Audit log access
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Header
from pydantic import BaseModel, EmailStr

from config.loader import ClientConfig, get_config
from src.middleware.auth_middleware import get_current_user, require_admin
from src.tools.supabase_tool import SupabaseTool
from src.utils.error_handler import log_and_raise

logger = logging.getLogger(__name__)

privacy_router = APIRouter(prefix="/privacy", tags=["Privacy & Compliance"])


# ==================== Dependency ====================

_client_configs = {}


def get_client_config(x_client_id: str = Header(None, alias="X-Client-ID")) -> ClientConfig:
    """Get client configuration from header"""
    client_id = x_client_id or os.getenv("CLIENT_ID", "example")

    if client_id not in _client_configs:
        try:
            _client_configs[client_id] = get_config(client_id)
        except Exception as e:
            logger.error(f"Failed to load config for {client_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load tenant configuration")

    return _client_configs[client_id]


# ============================================================
# PYDANTIC MODELS
# ============================================================

class ConsentUpdate(BaseModel):
    consent_type: str
    granted: bool
    source: str = "web"


class ConsentBulkUpdate(BaseModel):
    consents: List[ConsentUpdate]


class DSARRequest(BaseModel):
    request_type: str  # access, erasure, portability, rectification, objection
    email: EmailStr
    name: Optional[str] = None
    details: Optional[str] = None


class DSARStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None


class DataExportRequest(BaseModel):
    email: EmailStr
    include_quotes: bool = True
    include_invoices: bool = True
    include_communications: bool = True
    format: str = "json"  # json or csv


class BreachReport(BaseModel):
    breach_type: str
    severity: str
    description: str
    discovered_at: datetime
    affected_data_types: List[str]
    estimated_affected_count: Optional[int] = None


# ============================================================
# CONSENT MANAGEMENT
# ============================================================

@privacy_router.get("/consent")
async def get_my_consents(
    current_user: dict = Depends(get_current_user),
    config: ClientConfig = Depends(get_client_config)  # Will be injected by middleware
):
    """Get current user's consent status for all consent types"""
    try:
        supabase = SupabaseTool(config)
        email = current_user.get("email")

        response = supabase.client.table("consent_records").select("*").eq(
            "tenant_id", config.tenant_id
        ).eq("email", email).execute()

        # Build consent map with all types
        consent_types = [
            "marketing_email", "marketing_sms", "marketing_phone",
            "data_processing", "third_party_sharing", "analytics",
            "cookies_essential", "cookies_functional", "cookies_analytics", "cookies_marketing"
        ]

        consents = {}
        existing = {c["consent_type"]: c for c in (response.data or [])}

        for ct in consent_types:
            if ct in existing:
                record = existing[ct]
                consents[ct] = {
                    "granted": record["granted"] and not record.get("withdrawn_at"),
                    "granted_at": record.get("granted_at"),
                    "expires_at": record.get("expires_at"),
                    "can_withdraw": ct not in ["cookies_essential", "data_processing"]  # Required consents
                }
            else:
                consents[ct] = {
                    "granted": False,
                    "granted_at": None,
                    "expires_at": None,
                    "can_withdraw": ct not in ["cookies_essential", "data_processing"]
                }

        return {"success": True, "consents": consents}

    except Exception as e:
        log_and_raise(500, "retrieving consents", e, logger)


@privacy_router.post("/consent")
async def update_consent(
    consent: ConsentUpdate,
    request: Request,
    current_user: dict = Depends(get_current_user),
    config: ClientConfig = Depends(get_client_config)
):
    """Update a single consent preference"""
    try:
        supabase = SupabaseTool(config)
        email = current_user.get("email")
        user_id = current_user.get("id")

        # Get client IP and user agent for audit
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")

        # Check if consent record exists
        existing = supabase.client.table("consent_records").select("id").eq(
            "tenant_id", config.tenant_id
        ).eq("email", email).eq("consent_type", consent.consent_type).execute()

        now = datetime.utcnow().isoformat()

        if existing.data:
            # Update existing
            update_data = {
                "granted": consent.granted,
                "source": consent.source,
                "ip_address": client_ip,
                "user_agent": user_agent[:500] if user_agent else None,
                "updated_at": now
            }

            if consent.granted:
                update_data["granted_at"] = now
                update_data["withdrawn_at"] = None
            else:
                update_data["withdrawn_at"] = now

            supabase.client.table("consent_records").update(update_data).eq(
                "id", existing.data[0]["id"]
            ).execute()
        else:
            # Create new
            supabase.client.table("consent_records").insert({
                "tenant_id": config.tenant_id,
                "user_id": user_id,
                "email": email,
                "consent_type": consent.consent_type,
                "granted": consent.granted,
                "legal_basis": "consent",
                "source": consent.source,
                "ip_address": client_ip,
                "user_agent": user_agent[:500] if user_agent else None,
                "granted_at": now if consent.granted else None
            }).execute()

        # Log the consent change
        _log_pii_access(
            supabase, config.tenant_id, user_id, email,
            "update", "consent", consent.consent_type,
            pii_fields=["consent_preferences"],
            ip_address=client_ip, user_agent=user_agent
        )

        return {
            "success": True,
            "consent_type": consent.consent_type,
            "granted": consent.granted
        }

    except Exception as e:
        log_and_raise(500, "updating consent", e, logger)


@privacy_router.post("/consent/bulk")
async def update_consents_bulk(
    bulk: ConsentBulkUpdate,
    request: Request,
    current_user: dict = Depends(get_current_user),
    config: ClientConfig = Depends(get_client_config)
):
    """Update multiple consent preferences at once"""
    results = []
    for consent in bulk.consents:
        try:
            result = await update_consent(consent, request, current_user, config)
            results.append(result)
        except Exception as e:
            results.append({
                "success": False,
                "consent_type": consent.consent_type,
                "error": str(e)
            })

    return {"success": True, "results": results}


# ============================================================
# DATA SUBJECT ACCESS REQUESTS (DSAR)
# ============================================================

@privacy_router.post("/dsar")
async def submit_dsar(
    dsar: DSARRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    config: ClientConfig = Depends(get_client_config)
):
    """Submit a Data Subject Access Request"""
    try:
        supabase = SupabaseTool(config)
        user_id = current_user.get("id")
        user_email = current_user.get("email")

        # Verify user is requesting for themselves (or is admin)
        if dsar.email.lower() != user_email.lower() and not current_user.get("is_admin"):
            raise HTTPException(
                status_code=403,
                detail="You can only submit requests for your own data"
            )

        # Create DSAR record
        response = supabase.client.table("data_subject_requests").insert({
            "tenant_id": config.tenant_id,
            "user_id": user_id,
            "email": dsar.email.lower(),
            "name": dsar.name,
            "request_type": dsar.request_type,
            "status": "pending",
            "notes": dsar.details
        }).execute()

        dsar_record = response.data[0] if response.data else None

        if not dsar_record:
            raise HTTPException(status_code=500, detail="Failed to create DSAR")

        # Log the request
        _log_pii_access(
            supabase, config.tenant_id, user_id, user_email,
            "create", "dsar", dsar_record["id"],
            pii_fields=["email", "name"],
            ip_address=request.client.host if request.client else None
        )

        # Send confirmation email in background
        background_tasks.add_task(
            _send_dsar_confirmation,
            config, dsar.email, dsar_record["request_number"], dsar.request_type
        )

        # Notify admins
        background_tasks.add_task(
            _notify_admins_of_dsar,
            config, dsar_record
        )

        return {
            "success": True,
            "request_number": dsar_record["request_number"],
            "request_type": dsar.request_type,
            "status": "pending",
            "due_date": dsar_record["due_date"],
            "message": f"Your {dsar.request_type} request has been submitted. You will receive a confirmation email."
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "submitting DSAR", e, logger)


@privacy_router.get("/dsar")
async def get_my_dsars(
    current_user: dict = Depends(get_current_user),
    config: ClientConfig = Depends(get_client_config)
):
    """Get current user's DSAR history"""
    try:
        supabase = SupabaseTool(config)
        email = current_user.get("email")

        response = supabase.client.table("data_subject_requests").select(
            "id, request_number, request_type, status, due_date, completed_at, created_at"
        ).eq("tenant_id", config.tenant_id).eq("email", email).order(
            "created_at", desc=True
        ).execute()

        return {"success": True, "requests": response.data or []}

    except Exception as e:
        log_and_raise(500, "retrieving DSARs", e, logger)


@privacy_router.get("/dsar/{request_id}")
async def get_dsar_status(
    request_id: str,
    current_user: dict = Depends(get_current_user),
    config: ClientConfig = Depends(get_client_config)
):
    """Get status of a specific DSAR"""
    try:
        supabase = SupabaseTool(config)
        email = current_user.get("email")

        response = supabase.client.table("data_subject_requests").select("*").eq(
            "id", request_id
        ).eq("tenant_id", config.tenant_id).single().execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Request not found")

        # Verify ownership (unless admin)
        if response.data["email"] != email and not current_user.get("is_admin"):
            raise HTTPException(status_code=403, detail="Access denied")

        return {"success": True, "request": response.data}

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "retrieving DSAR", e, logger)


# ============================================================
# DATA EXPORT (PORTABILITY)
# ============================================================

@privacy_router.post("/export")
async def request_data_export(
    export_request: DataExportRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    config: ClientConfig = Depends(get_client_config)
):
    """Request a data export (data portability)"""
    try:
        supabase = SupabaseTool(config)
        user_id = current_user.get("id")
        user_email = current_user.get("email")

        # Verify user is requesting their own data
        if export_request.email.lower() != user_email.lower() and not current_user.get("is_admin"):
            raise HTTPException(
                status_code=403,
                detail="You can only export your own data"
            )

        # Create DSAR record for tracking
        dsar_response = supabase.client.table("data_subject_requests").insert({
            "tenant_id": config.tenant_id,
            "user_id": user_id,
            "email": export_request.email.lower(),
            "request_type": "portability",
            "status": "in_progress",
            "notes": f"Format: {export_request.format}"
        }).execute()

        dsar_id = dsar_response.data[0]["id"] if dsar_response.data else None

        # Process export in background
        background_tasks.add_task(
            _generate_data_export,
            config, export_request.email, dsar_id, export_request
        )

        return {
            "success": True,
            "message": "Data export initiated. You will receive an email when ready.",
            "request_id": dsar_id
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "requesting data export", e, logger)


# ============================================================
# DATA ERASURE
# ============================================================

@privacy_router.post("/erasure")
async def request_data_erasure(
    email: EmailStr,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    config: ClientConfig = Depends(get_client_config)
):
    """Request data erasure (right to be forgotten)"""
    try:
        supabase = SupabaseTool(config)
        user_id = current_user.get("id")
        user_email = current_user.get("email")

        # Verify user is requesting for themselves
        if email.lower() != user_email.lower() and not current_user.get("is_admin"):
            raise HTTPException(
                status_code=403,
                detail="You can only request erasure of your own data"
            )

        # Create DSAR record
        dsar_response = supabase.client.table("data_subject_requests").insert({
            "tenant_id": config.tenant_id,
            "user_id": user_id,
            "email": email.lower(),
            "request_type": "erasure",
            "status": "pending",
            "notes": "Erasure request submitted via privacy portal"
        }).execute()

        dsar_id = dsar_response.data[0]["id"] if dsar_response.data else None

        # Log the request
        _log_pii_access(
            supabase, config.tenant_id, user_id, user_email,
            "create", "dsar", dsar_id,
            pii_fields=["erasure_request"],
            ip_address=request.client.host if request.client else None
        )

        # Notify admins for manual review (erasure requires verification)
        background_tasks.add_task(
            _notify_admins_of_dsar,
            config, dsar_response.data[0]
        )

        return {
            "success": True,
            "message": "Erasure request submitted. This will be reviewed within 30 days.",
            "request_id": dsar_id,
            "note": "Some data may be retained for legal compliance (e.g., invoices for tax purposes)"
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "requesting data erasure", e, logger)


# ============================================================
# ADMIN ENDPOINTS
# ============================================================

@privacy_router.get("/admin/dsars")
async def list_all_dsars(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(require_admin),
    config: ClientConfig = Depends(get_client_config)
):
    """List all DSARs for the tenant (admin only)"""
    try:
        supabase = SupabaseTool(config)

        query = supabase.client.table("data_subject_requests").select("*").eq(
            "tenant_id", config.tenant_id
        )

        if status:
            query = query.eq("status", status)

        response = query.order("created_at", desc=True).range(
            offset, offset + limit - 1
        ).execute()

        return {
            "success": True,
            "requests": response.data or [],
            "count": len(response.data or [])
        }

    except Exception as e:
        log_and_raise(500, "listing DSARs", e, logger)


@privacy_router.patch("/admin/dsar/{request_id}")
async def update_dsar_status(
    request_id: str,
    update: DSARStatusUpdate,
    current_user: dict = Depends(require_admin),
    config: ClientConfig = Depends(get_client_config)
):
    """Update DSAR status (admin only)"""
    try:
        supabase = SupabaseTool(config)

        update_data = {
            "status": update.status,
            "updated_at": datetime.utcnow().isoformat()
        }

        if update.notes:
            update_data["notes"] = update.notes
        if update.rejection_reason:
            update_data["rejection_reason"] = update.rejection_reason
        if update.status == "completed":
            update_data["completed_at"] = datetime.utcnow().isoformat()

        supabase.client.table("data_subject_requests").update(update_data).eq(
            "id", request_id
        ).eq("tenant_id", config.tenant_id).execute()

        return {"success": True, "status": update.status}

    except Exception as e:
        log_and_raise(500, "updating DSAR", e, logger)


@privacy_router.get("/admin/audit-log")
async def get_audit_log(
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
    user_email: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(require_admin),
    config: ClientConfig = Depends(get_client_config)
):
    """View PII access audit log (admin only)"""
    try:
        supabase = SupabaseTool(config)

        query = supabase.client.table("data_audit_log").select("*").eq(
            "tenant_id", config.tenant_id
        )

        if resource_type:
            query = query.eq("resource_type", resource_type)
        if action:
            query = query.eq("action", action)
        if user_email:
            query = query.eq("user_email", user_email)
        if start_date:
            query = query.gte("created_at", start_date)
        if end_date:
            query = query.lte("created_at", end_date)

        response = query.order("created_at", desc=True).range(
            offset, offset + limit - 1
        ).execute()

        return {
            "success": True,
            "logs": response.data or [],
            "count": len(response.data or [])
        }

    except Exception as e:
        log_and_raise(500, "retrieving audit log", e, logger)


@privacy_router.post("/admin/breach")
async def report_breach(
    breach: BreachReport,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_admin),
    config: ClientConfig = Depends(get_client_config)
):
    """Report a data breach (admin only)"""
    try:
        supabase = SupabaseTool(config)
        user_id = current_user.get("id")

        response = supabase.client.table("data_breach_log").insert({
            "tenant_id": config.tenant_id,
            "breach_type": breach.breach_type,
            "severity": breach.severity,
            "description": breach.description,
            "discovered_at": breach.discovered_at.isoformat(),
            "affected_data_types": breach.affected_data_types,
            "estimated_affected_count": breach.estimated_affected_count,
            "reported_by": user_id,
            "status": "open"
        }).execute()

        breach_record = response.data[0] if response.data else None

        # For high/critical severity, send immediate alerts
        if breach.severity in ["high", "critical"]:
            background_tasks.add_task(
                _send_breach_alerts,
                config, breach_record
            )

        return {
            "success": True,
            "breach_number": breach_record["breach_number"],
            "message": "Breach reported. GDPR requires authority notification within 72 hours for high-risk breaches."
        }

    except Exception as e:
        log_and_raise(500, "reporting breach", e, logger)


@privacy_router.get("/admin/breaches")
async def list_breaches(
    status: Optional[str] = None,
    current_user: dict = Depends(require_admin),
    config: ClientConfig = Depends(get_client_config)
):
    """List all data breaches (admin only)"""
    try:
        supabase = SupabaseTool(config)

        query = supabase.client.table("data_breach_log").select("*").eq(
            "tenant_id", config.tenant_id
        )

        if status:
            query = query.eq("status", status)

        response = query.order("discovered_at", desc=True).execute()

        return {"success": True, "breaches": response.data or []}

    except Exception as e:
        log_and_raise(500, "listing breaches", e, logger)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _log_pii_access(
    supabase: SupabaseTool,
    tenant_id: str,
    user_id: str,
    user_email: str,
    action: str,
    resource_type: str,
    resource_id: str,
    pii_fields: List[str] = None,
    ip_address: str = None,
    user_agent: str = None
):
    """Log access to PII for compliance"""
    try:
        supabase.client.table("data_audit_log").insert({
            "tenant_id": tenant_id,
            "user_id": user_id,
            "user_email": user_email,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "pii_fields_accessed": pii_fields or [],
            "ip_address": ip_address,
            "user_agent": user_agent[:500] if user_agent else None
        }).execute()
    except Exception as e:
        logger.warning(f"Failed to log PII access: {e}")


async def _send_dsar_confirmation(config: ClientConfig, email: str, request_number: str, request_type: str):
    """Send DSAR confirmation email"""
    try:
        from src.utils.email_sender import EmailSender

        sender = EmailSender(config)
        sender.send_email(
            to_email=email,
            subject=f"Data Request Confirmation - {request_number}",
            body=f"""
Your data {request_type} request has been received.

Request Number: {request_number}

We will process your request within 30 days as required by data protection regulations.

If you have any questions, please contact our privacy team.
            """,
            template="privacy_confirmation"
        )
    except Exception as e:
        logger.warning(f"Failed to send DSAR confirmation: {e}")


async def _notify_admins_of_dsar(config: ClientConfig, dsar_record: dict):
    """Notify admins of new DSAR"""
    try:
        from src.api.notifications_routes import NotificationService

        notification_service = NotificationService(config)
        # This would need to be extended to notify all admins
        logger.info(f"DSAR {dsar_record['request_number']} submitted - notify admins")
    except Exception as e:
        logger.warning(f"Failed to notify admins of DSAR: {e}")


async def _generate_data_export(
    config: ClientConfig,
    email: str,
    dsar_id: str,
    export_request: DataExportRequest
):
    """Generate data export file"""
    try:
        supabase = SupabaseTool(config)
        export_data = {"email": email, "exported_at": datetime.utcnow().isoformat()}

        # Collect all user data
        if export_request.include_quotes:
            quotes = supabase.client.table("quotes").select("*").eq(
                "tenant_id", config.tenant_id
            ).eq("customer_email", email).execute()
            export_data["quotes"] = quotes.data or []

        if export_request.include_invoices:
            invoices = supabase.client.table("invoices").select("*").eq(
                "tenant_id", config.tenant_id
            ).eq("customer_email", email).execute()
            export_data["invoices"] = invoices.data or []

        # Get client record
        client = supabase.client.table("clients").select("*").eq(
            "tenant_id", config.tenant_id
        ).eq("email", email).execute()
        export_data["profile"] = client.data[0] if client.data else None

        # Get consent records
        consents = supabase.client.table("consent_records").select("*").eq(
            "tenant_id", config.tenant_id
        ).eq("email", email).execute()
        export_data["consents"] = consents.data or []

        # TODO: Upload to Supabase Storage and generate download link
        # For now, we'll store in the DSAR record

        # Update DSAR with export data
        supabase.client.table("data_subject_requests").update({
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
            "notes": f"Export generated with {len(export_data.get('quotes', []))} quotes, {len(export_data.get('invoices', []))} invoices"
        }).eq("id", dsar_id).execute()

        # Send email with export (in production, this would be a secure download link)
        from src.utils.email_sender import EmailSender
        sender = EmailSender(config)
        sender.send_email(
            to_email=email,
            subject="Your Data Export is Ready",
            body=f"""
Your data export has been generated.

Summary:
- Profile information: {'Yes' if export_data.get('profile') else 'No'}
- Quotes: {len(export_data.get('quotes', []))}
- Invoices: {len(export_data.get('invoices', []))}
- Consent records: {len(export_data.get('consents', []))}

For security reasons, please contact our privacy team to receive your full export file.
            """
        )

        logger.info(f"Data export generated for {email}")

    except Exception as e:
        logger.error(f"Failed to generate data export: {e}")


async def _send_breach_alerts(config: ClientConfig, breach_record: dict):
    """Send alerts for high-severity breaches"""
    try:
        logger.critical(f"HIGH SEVERITY BREACH: {breach_record['breach_number']} - {breach_record['description']}")
        # In production, this would:
        # 1. Send SMS/email to security team
        # 2. Create incident in monitoring system
        # 3. Potentially notify data protection authority
    except Exception as e:
        logger.error(f"Failed to send breach alerts: {e}")
