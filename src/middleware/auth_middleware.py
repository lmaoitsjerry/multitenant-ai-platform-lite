"""
Authentication Middleware

Validates JWT tokens and extracts user context for protected routes.
Works alongside the existing X-Client-ID header-based tenant identification.
"""

import os
import time
import logging
from typing import Optional, Callable
from collections import defaultdict
from functools import wraps
from fastapi import Request, HTTPException, Depends, Header
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.services.auth_service import AuthService
from src.utils.structured_logger import set_tenant_id
from config.loader import get_config

logger = logging.getLogger(__name__)


# ==================== Tenant Suspension Cache ====================

# Simple time-based cache for tenant suspension status (avoids DB hit on every request)
_tenant_status_cache: dict[str, tuple[str, float]] = {}
_TENANT_STATUS_TTL = 300  # 5 minutes


def _is_tenant_suspended(tenant_id: str) -> bool:
    """
    Check if a tenant is suspended, using a cached lookup.
    Returns True if the tenant is confirmed suspended.
    Returns False if active, unknown, or if the check fails (fail-open).
    """
    # Evict stale entries if cache is too large
    if len(_tenant_status_cache) > 500:
        now_evict = time.time()
        expired = [k for k, (_, ts) in _tenant_status_cache.items()
                   if now_evict - ts >= _TENANT_STATUS_TTL]
        for k in expired:
            del _tenant_status_cache[k]
        if len(_tenant_status_cache) > 500:
            for k in list(_tenant_status_cache.keys())[:len(_tenant_status_cache) // 2]:
                del _tenant_status_cache[k]

    now = time.time()
    cached = _tenant_status_cache.get(tenant_id)
    if cached and (now - cached[1]) < _TENANT_STATUS_TTL:
        return cached[0] == "suspended"

    # Refresh from DB
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            return False

        from supabase import create_client
        client = create_client(supabase_url, supabase_key)
        result = client.table("tenants").select("status").eq(
            "tenant_id", tenant_id
        ).execute()

        if result.data and result.data[0].get("status") == "suspended":
            _tenant_status_cache[tenant_id] = ("suspended", now)
            return True
        else:
            _tenant_status_cache[tenant_id] = ("active", now)
            return False
    except Exception as e:
        logger.debug(f"Tenant status check failed (fail-open): {e}")
        return False


# ==================== Spoofing Rate Limiter ====================

# Module-level spoofing attempt tracker
_spoof_attempts: dict[str, list[float]] = defaultdict(list)
_spoof_blocked: dict[str, float] = {}
SPOOF_MAX_ATTEMPTS = 3
SPOOF_WINDOW = 300      # 5 minutes
SPOOF_BLOCK = 1800      # 30 minutes


def _get_client_ip(scope: dict) -> str:
    """Extract client IP from x-forwarded-for header or ASGI client."""
    for key, value in scope.get("headers", []):
        if key == b"x-forwarded-for":
            # Take first IP (original client) from comma-separated list
            return value.decode("latin-1").split(",")[0].strip()
    client = scope.get("client")
    if client:
        return client[0]
    return "unknown"


def _is_spoof_blocked(key: str) -> bool:
    """Check if a key (ip:tenant) is currently blocked."""
    blocked_at = _spoof_blocked.get(key)
    if blocked_at is None:
        return False
    if time.time() - blocked_at >= SPOOF_BLOCK:
        del _spoof_blocked[key]
        return False
    return True


def _record_spoof_attempt(key: str) -> bool:
    """Record a spoofing attempt. Returns True if the key is now blocked."""
    now = time.time()
    # Prune old attempts outside the window
    _spoof_attempts[key] = [t for t in _spoof_attempts[key] if now - t < SPOOF_WINDOW]
    _spoof_attempts[key].append(now)
    if len(_spoof_attempts[key]) >= SPOOF_MAX_ATTEMPTS:
        _spoof_blocked[key] = now
        _spoof_attempts[key] = []  # Reset counter after blocking
        return True
    return False


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
    "/api/v1/branding/theme-pack",
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
    "/api/v1/wb/",  # Website builder proxy — WB handles its own auth via X-Tenant-ID
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
            try:
                config = get_config(tenant_id)
                auth_service = AuthService(
                    supabase_url=config.supabase_url,
                    supabase_key=config.supabase_service_key
                )
            except FileNotFoundError:
                # Fallback to env vars - all tenants share the same Supabase instance
                supabase_url = os.getenv("SUPABASE_URL")
                supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
                if not supabase_url or not supabase_key:
                    await self._send_json(send, 400, {"detail": f"Unknown client: {tenant_id}"})
                    return
                logger.info(f"Tenant '{tenant_id}' not in DB config cache, using env vars for auth")
                auth_service = AuthService(supabase_url=supabase_url, supabase_key=supabase_key)

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
                client_ip = _get_client_ip(scope)
                limiter_key = f"{client_ip}:{header_tenant_id}"

                if _is_spoof_blocked(limiter_key):
                    logger.warning(
                        f"Blocked spoofing from {client_ip} "
                        f"(JWT={user['tenant_id']}, header={header_tenant_id})"
                    )
                    await self._send_json_with_headers(
                        send, 429, {"detail": "Too many requests"},
                        extra_headers=[(b"retry-after", str(SPOOF_BLOCK).encode())]
                    )
                    return

                now_blocked = _record_spoof_attempt(limiter_key)
                logger.warning(
                    f"Tenant spoofing attempt from {client_ip}: "
                    f"header={header_tenant_id}, user tenant={user['tenant_id']}, "
                    f"auth_user_id={auth_user_id}"
                    f"{' — NOW BLOCKED' if now_blocked else ''}"
                )
                await self._send_json(send, 403, {"detail": "Access denied: tenant mismatch"})
                return

            # Check if tenant is suspended
            if _is_tenant_suspended(user["tenant_id"]):
                await self._send_json(send, 403, {"detail": "Tenant account is suspended"})
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

        except Exception as e:
            logger.error(f"Auth middleware error: {e}", exc_info=True)
            await self._send_json(send, 500, {"detail": "Authentication error"})
            return

        await self.app(scope, receive, send)

    async def _send_json(self, send, status_code: int, content: dict):
        """Send a JSON response directly."""
        await self._send_json_with_headers(send, status_code, content)

    async def _send_json_with_headers(self, send, status_code: int, content: dict,
                                       extra_headers: list = None):
        """Send a JSON response with optional extra headers."""
        import json
        body = json.dumps(content).encode()
        headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
        ]
        if extra_headers:
            headers.extend(extra_headers)
        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": headers,
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
