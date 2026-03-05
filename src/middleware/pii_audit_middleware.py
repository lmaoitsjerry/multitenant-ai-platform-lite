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


class PIIAuditMiddleware:
    """Pure ASGI middleware to automatically log access to PII endpoints"""

    def __init__(self, app, enabled: bool = True):
        self.app = app
        self.enabled = enabled

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not self.enabled:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "")
        pii_config = self._get_pii_config(path, method)

        if not pii_config:
            # Not a PII endpoint, skip logging
            await self.app(scope, receive, send)
            return

        # Track response status code for PII logging
        status_code = 0

        async def send_with_tracking(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
            await send(message)

        await self.app(scope, receive, send_with_tracking)

        # Only log successful requests (2xx status codes)
        if 200 <= status_code < 300:
            try:
                await self._log_pii_access(scope, pii_config)
            except Exception as e:
                logger.warning(f"Failed to log PII access: {e}")

    def _get_pii_config(self, path: str, method: str) -> Optional[dict]:
        """Check if path matches any PII endpoint pattern"""
        for pattern, config in PII_ENDPOINTS.items():
            if re.match(pattern, path):
                if method in config.get("methods", []):
                    return config
        return None

    async def _log_pii_access(self, scope, config: dict):
        """Log PII access to the audit table"""
        try:
            import asyncio

            # Extract user info from scope state (set by auth middleware)
            state = scope.get("state", {})
            user = state.get("user", None)

            # Get tenant_id from user context or headers
            tenant_id = None
            if user and hasattr(user, "tenant_id"):
                tenant_id = user.tenant_id

            if not tenant_id:
                for key, value in scope.get("headers", []):
                    if key == b"x-client-id":
                        tenant_id = value.decode("utf-8", errors="replace")
                        break

            if not tenant_id:
                return  # Can't log without tenant

            user_id = user.user_id if user else None
            user_email = user.email if user else None

            # Extract resource ID from path
            path = scope.get("path", "")
            resource_id = self._extract_resource_id(path)

            # Get action from method
            method = scope.get("method", "GET")
            action = METHOD_TO_ACTION.get(method, "view")

            # Get client IP
            client_ip = self._get_client_ip(scope)

            # Get user agent
            user_agent = ""
            for key, value in scope.get("headers", []):
                if key == b"user-agent":
                    user_agent = value.decode("utf-8", errors="replace")[:500]
                    break

            # Build audit entry
            audit_entry = {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "user_email": user_email,
                "action": action,
                "resource_type": config["resource_type"],
                "resource_id": resource_id,
                "pii_fields_accessed": config["pii_fields"],
                "ip_address": client_ip,
                "user_agent": user_agent,
                "request_path": path,
                "request_method": method
            }

            # Insert audit log in background thread to avoid blocking
            await asyncio.to_thread(self._insert_audit_log_sync, tenant_id, audit_entry)

        except Exception as e:
            logger.warning(f"Failed to log PII access: {e}")

    def _extract_resource_id(self, path: str) -> Optional[str]:
        """Extract resource ID from URL path"""
        match = re.search(r"/([a-f0-9-]{8,}|[0-9]+)(?:/|$)", path)
        return match.group(1) if match else None

    def _get_client_ip(self, scope) -> Optional[str]:
        """Get real client IP, handling proxies"""
        for key, value in scope.get("headers", []):
            if key == b"x-forwarded-for":
                return value.decode("utf-8", errors="replace").split(",")[0].strip()
            if key == b"x-real-ip":
                return value.decode("utf-8", errors="replace")

        client = scope.get("client")
        if client:
            return client[0]
        return None

    def _insert_audit_log_sync(self, tenant_id: str, audit_entry: dict):
        """Insert audit log entry into database (sync, for use in thread)"""
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
