"""
PII Audit Middleware - Automatic logging of personal data access

Logs all access to endpoints that handle personal data for GDPR/POPIA compliance.
"""

import logging
import re
from typing import Optional, List, Callable
from datetime import datetime
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# Endpoints that access PII - mapped to the PII fields they may access
PII_ENDPOINTS = {
    # CRM - Client data
    r"^/api/v1/crm/clients$": {
        "resource_type": "client",
        "pii_fields": ["email", "name", "phone"],
        "methods": ["GET", "POST"]
    },
    r"^/api/v1/crm/clients/[^/]+$": {
        "resource_type": "client",
        "pii_fields": ["email", "name", "phone", "notes"],
        "methods": ["GET", "PUT", "PATCH", "DELETE"]
    },

    # Quotes - Customer data
    r"^/api/v1/quotes$": {
        "resource_type": "quote",
        "pii_fields": ["customer_name", "customer_email", "customer_phone"],
        "methods": ["GET", "POST"]
    },
    r"^/api/v1/quotes/[^/]+$": {
        "resource_type": "quote",
        "pii_fields": ["customer_name", "customer_email", "customer_phone"],
        "methods": ["GET", "PUT", "PATCH"]
    },

    # Invoices - Billing data
    r"^/api/v1/invoices$": {
        "resource_type": "invoice",
        "pii_fields": ["customer_name", "customer_email", "billing_address"],
        "methods": ["GET", "POST"]
    },
    r"^/api/v1/invoices/[^/]+$": {
        "resource_type": "invoice",
        "pii_fields": ["customer_name", "customer_email", "billing_address"],
        "methods": ["GET", "PUT", "PATCH"]
    },

    # Users - Account data
    r"^/api/v1/users$": {
        "resource_type": "user",
        "pii_fields": ["email", "name"],
        "methods": ["GET", "POST"]
    },
    r"^/api/v1/users/[^/]+$": {
        "resource_type": "user",
        "pii_fields": ["email", "name", "role"],
        "methods": ["GET", "PUT", "PATCH", "DELETE"]
    },

    # Data exports
    r"^/privacy/export$": {
        "resource_type": "data_export",
        "pii_fields": ["all_personal_data"],
        "methods": ["POST"]
    },

    # DSAR
    r"^/privacy/dsar$": {
        "resource_type": "dsar",
        "pii_fields": ["email", "name"],
        "methods": ["GET", "POST"]
    },
}

# HTTP method to action mapping
METHOD_TO_ACTION = {
    "GET": "view",
    "POST": "create",
    "PUT": "update",
    "PATCH": "update",
    "DELETE": "delete"
}


class PIIAuditMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically log access to PII endpoints"""

    def __init__(self, app: ASGIApp, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled:
            return await call_next(request)

        # Check if this endpoint handles PII
        path = request.url.path
        method = request.method
        pii_config = self._get_pii_config(path, method)

        if not pii_config:
            # Not a PII endpoint, skip logging
            return await call_next(request)

        # Process the request
        response = await call_next(request)

        # Only log successful requests (2xx status codes)
        if 200 <= response.status_code < 300:
            await self._log_pii_access(request, response, pii_config)

        return response

    def _get_pii_config(self, path: str, method: str) -> Optional[dict]:
        """Check if path matches any PII endpoint pattern"""
        for pattern, config in PII_ENDPOINTS.items():
            if re.match(pattern, path):
                if method in config.get("methods", []):
                    return config
        return None

    async def _log_pii_access(self, request: Request, response: Response, config: dict):
        """Log PII access to the audit table"""
        try:
            # Extract user info from request state (set by auth middleware)
            user = getattr(request.state, "user", None)
            tenant_id = getattr(request.state, "tenant_id", None)

            if not tenant_id:
                # Try to get from header
                tenant_id = request.headers.get("X-Client-ID")

            if not tenant_id:
                return  # Can't log without tenant

            user_id = user.get("id") if user else None
            user_email = user.get("email") if user else None

            # Extract resource ID from path if present
            resource_id = self._extract_resource_id(request.url.path)

            # Get action from method
            action = METHOD_TO_ACTION.get(request.method, "view")

            # Build audit entry
            audit_entry = {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "user_email": user_email,
                "action": action,
                "resource_type": config["resource_type"],
                "resource_id": resource_id,
                "pii_fields_accessed": config["pii_fields"],
                "ip_address": self._get_client_ip(request),
                "user_agent": request.headers.get("user-agent", "")[:500],
                "request_path": request.url.path,
                "request_method": request.method
            }

            # Log asynchronously (don't block response)
            await self._insert_audit_log(tenant_id, audit_entry)

        except Exception as e:
            # Never fail the request due to audit logging
            logger.warning(f"Failed to log PII access: {e}")

    def _extract_resource_id(self, path: str) -> Optional[str]:
        """Extract resource ID from URL path"""
        # Match patterns like /api/v1/crm/clients/123 or /api/v1/quotes/abc-123
        match = re.search(r"/([a-f0-9-]{8,}|[0-9]+)(?:/|$)", path)
        return match.group(1) if match else None

    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Get real client IP, handling proxies"""
        # Check X-Forwarded-For first (for proxied requests)
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # Take the first IP (original client)
            return forwarded.split(",")[0].strip()

        # Check X-Real-IP
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct connection
        if request.client:
            return request.client.host

        return None

    async def _insert_audit_log(self, tenant_id: str, audit_entry: dict):
        """Insert audit log entry into database"""
        try:
            from config.loader import get_config
            from src.tools.supabase_tool import SupabaseTool

            config = get_config(tenant_id)
            supabase = SupabaseTool(config)

            supabase.client.table("data_audit_log").insert(audit_entry).execute()

        except Exception as e:
            logger.warning(f"Failed to insert audit log: {e}")


def setup_pii_audit_middleware(app, enabled: bool = True):
    """Add PII audit middleware to FastAPI app"""
    app.add_middleware(PIIAuditMiddleware, enabled=enabled)
    logger.info(f"PII Audit middleware {'enabled' if enabled else 'disabled'}")
