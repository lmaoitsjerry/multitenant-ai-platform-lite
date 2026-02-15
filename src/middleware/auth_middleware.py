"""
Authentication Middleware

Validates JWT tokens and extracts user context for protected routes.
Works alongside the existing X-Client-ID header-based tenant identification.
"""

import os
import logging
from typing import Optional, Callable
from functools import wraps
from fastapi import Request, HTTPException, Depends, Header
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.services.auth_service import AuthService
from src.utils.structured_logger import set_tenant_id
from config.loader import get_config

logger = logging.getLogger(__name__)


# ==================== Public Paths ====================

# Paths that don't require authentication
PUBLIC_PATHS = {
    "/",
    "/health",
    "/health/ready",
    "/health/live",
    "/metrics",
    # Auth endpoints (login doesn't need auth)
    "/api/v1/auth/login",
    "/api/v1/auth/password/reset",
    "/api/v1/auth/invite/accept",
    # Webhooks (use their own auth)
    "/api/v1/webhooks/",
    "/webhooks/",
    "/api/v1/inbound/",
    # Customer-facing endpoints
    "/api/v1/quotes/chat",
    # Branding endpoints (needed for login page theming)
    "/api/v1/branding",
    "/api/v1/branding/presets",
    "/api/v1/branding/fonts",
    # Helpdesk endpoints (search uses X-Client-ID for tenant context)
    "/api/v1/helpdesk/faiss-status",
    "/api/v1/helpdesk/test-search",
    "/api/v1/helpdesk/ask",
    "/api/v1/helpdesk/topics",
    "/api/v1/helpdesk/search",
}

# Prefixes that don't require authentication
PUBLIC_PREFIXES = [
    "/api/v1/webhooks/",
    "/api/webhooks/",  # Legacy webhook endpoints (SendGrid inbound)
    "/webhooks/",
    "/api/v1/inbound/",
    "/api/v1/admin/",  # Admin routes use X-Admin-Token auth
    "/api/v1/onboarding/",  # Tenant onboarding (new signups - no auth)
    "/api/v1/public/",  # Public shareable endpoints (invoices, quotes)
    "/api/v1/rates/",  # Rates engine endpoints (use X-Client-ID for tenant context)
    "/api/v1/travel/",  # Travel services endpoints (flights, transfers, activities)
    "/api/v1/knowledge/global",  # Global KB proxy (uses Travel Platform auth, not user auth)
    "/api/v1/agent/",  # Unified RAG for AI agents (uses X-Client-ID for tenant context)
]


def is_public_path(path: str) -> bool:
    """Check if path is public (no auth required)"""
    if path in PUBLIC_PATHS:
        return True

    for prefix in PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return True

    return False


# ==================== User Context ====================

class UserContext:
    """Container for authenticated user information"""

    def __init__(
        self,
        user_id: str,
        auth_user_id: str,
        email: str,
        name: str,
        role: str,
        tenant_id: str,
        is_active: bool = True
    ):
        self.user_id = user_id
        self.auth_user_id = auth_user_id
        self.email = email
        self.name = name
        self.role = role
        self.tenant_id = tenant_id
        self.is_active = is_active

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_consultant(self) -> bool:
        return self.role == "consultant"

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "auth_user_id": self.auth_user_id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "tenant_id": self.tenant_id,
            "is_active": self.is_active
        }


# ==================== Auth Middleware ====================

class AuthMiddleware:
    """
    Pure ASGI middleware that validates JWT tokens and attaches user context to requests.

    For authenticated requests:
    - Validates the JWT token from Authorization header
    - Fetches user from organization_users table
    - Verifies user belongs to the tenant (from X-Client-ID)
    - Attaches UserContext to request.state.user

    For public paths:
    - Skips authentication
    - request.state.user will be None
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Ensure state dict exists on scope
        if "state" not in scope:
            scope["state"] = {}

        method = scope.get("method", "")
        path = scope.get("path", "")

        # Skip auth for CORS preflight OPTIONS requests
        if method == "OPTIONS":
            scope["state"]["user"] = None
            await self.app(scope, receive, send)
            return

        # Skip auth for public paths
        if is_public_path(path):
            scope["state"]["user"] = None
            await self.app(scope, receive, send)
            return

        # Parse headers
        headers_dict = {}
        for key, value in scope.get("headers", []):
            headers_dict[key.decode("latin-1").lower()] = value.decode("latin-1")

        auth_header = headers_dict.get("authorization")

        if not auth_header:
            await self._send_json(send, 401, {"detail": "Authorization header required"})
            return

        # Parse Bearer token
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            await self._send_json(send, 401, {"detail": "Invalid authorization header format"})
            return

        token = parts[1]

        # Get tenant ID
        tenant_id = headers_dict.get("x-client-id") or os.getenv("CLIENT_ID", "africastay")

        try:
            # Get tenant config for Supabase credentials
            config = get_config(tenant_id)
            auth_service = AuthService(
                supabase_url=config.supabase_url,
                supabase_key=config.supabase_service_key
            )

            # Verify JWT (sync - fast operation, just decodes token)
            valid, payload = auth_service.verify_jwt(token)
            if not valid:
                await self._send_json(send, 401, {"detail": payload.get("error", "Invalid token")})
                return

            # Get auth user ID from token
            auth_user_id = payload.get("sub")
            if not auth_user_id:
                await self._send_json(send, 401, {"detail": "Invalid token payload"})
                return

            # Fetch user from database (uses asyncio.to_thread internally)
            user = await auth_service.get_user_by_auth_id(auth_user_id, tenant_id)
            if not user:
                await self._send_json(send, 401, {"detail": "User not found in this organization"})
                return

            if not user.get("is_active", False):
                await self._send_json(send, 401, {"detail": "User account is deactivated"})
                return

            # Validate X-Client-ID matches user's actual tenant
            header_tenant_id = headers_dict.get("x-client-id")
            if header_tenant_id and header_tenant_id != user["tenant_id"]:
                logger.warning(
                    f"Tenant spoofing attempt: header X-Client-ID={header_tenant_id}, "
                    f"user tenant_id={user['tenant_id']}, auth_user_id={auth_user_id}"
                )
                await self._send_json(send, 403, {"detail": "Access denied: tenant mismatch"})
                return

            # Set tenant_id in contextvars for structured logging
            set_tenant_id(user["tenant_id"])

            # Attach user context to scope state (accessible via request.state)
            scope["state"]["user"] = UserContext(
                user_id=user["id"],
                auth_user_id=auth_user_id,
                email=user["email"],
                name=user["name"],
                role=user["role"],
                tenant_id=user["tenant_id"],
                is_active=user["is_active"]
            )

        except FileNotFoundError:
            await self._send_json(send, 400, {"detail": f"Unknown client: {tenant_id}"})
            return
        except Exception as e:
            logger.error(f"Auth middleware error: {e}")
            await self._send_json(send, 500, {"detail": "Authentication error"})
            return

        await self.app(scope, receive, send)

    async def _send_json(self, send, status_code: int, content: dict):
        """Send a JSON response directly."""
        import json
        body = json.dumps(content).encode()
        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        })
        await send({"type": "http.response.body", "body": body})


# ==================== Dependency Functions ====================

def get_current_user(request: Request) -> UserContext:
    """
    FastAPI dependency to get current authenticated user.

    Usage:
        @router.get("/endpoint")
        async def endpoint(user: UserContext = Depends(get_current_user)):
            ...
    """
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def get_current_user_optional(request: Request) -> Optional[UserContext]:
    """
    FastAPI dependency to optionally get current user.
    Returns None if not authenticated.

    Usage for endpoints that work with or without auth:
        @router.get("/endpoint")
        async def endpoint(user: Optional[UserContext] = Depends(get_current_user_optional)):
            if user:
                # Authenticated
            else:
                # Anonymous
    """
    return getattr(request.state, "user", None)


def require_admin(request: Request) -> UserContext:
    """
    FastAPI dependency that requires admin role.

    Usage:
        @router.post("/admin-only")
        async def admin_endpoint(user: UserContext = Depends(require_admin)):
            ...
    """
    user = get_current_user(request)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ==================== Decorator Functions ====================

def require_auth(func: Callable) -> Callable:
    """
    Decorator to require authentication on a route.

    Usage:
        @router.get("/protected")
        @require_auth
        async def protected_endpoint(request: Request):
            user = request.state.user
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get("request")
        if not request:
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

        if not request or not getattr(request.state, "user", None):
            raise HTTPException(status_code=401, detail="Authentication required")

        return await func(*args, **kwargs)

    return wrapper


def require_role(role: str) -> Callable:
    """
    Decorator to require a specific role.

    Usage:
        @router.post("/admin-action")
        @require_role("admin")
        async def admin_action(request: Request):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            user = getattr(request.state, "user", None)
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")

            if user.role != role:
                raise HTTPException(status_code=403, detail=f"{role.title()} access required")

            return await func(*args, **kwargs)

        return wrapper
    return decorator
