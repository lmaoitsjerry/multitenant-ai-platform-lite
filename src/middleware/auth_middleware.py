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
from config.loader import get_config

logger = logging.getLogger(__name__)


# ==================== Public Paths ====================

# Paths that don't require authentication
PUBLIC_PATHS = {
    "/",
    "/health",
    "/health/ready",
    "/health/live",
    "/docs",
    "/openapi.json",
    "/redoc",
    # Auth endpoints (login doesn't need auth)
    "/api/v1/auth/login",
    "/api/v1/auth/password/reset",
    "/api/v1/auth/invite/accept",
    # Webhooks (use their own auth)
    "/api/v1/webhooks/",
    "/api/v1/inbound/",
    # Customer-facing endpoints
    "/api/v1/quotes/chat",
    # Branding endpoints (needed for login page theming)
    "/api/v1/branding",
    "/api/v1/branding/presets",
    "/api/v1/branding/fonts",
}

# Prefixes that don't require authentication
PUBLIC_PREFIXES = [
    "/api/v1/webhooks/",
    "/api/v1/inbound/",
    "/api/v1/admin/",  # Admin routes use X-Admin-Token auth
    "/api/v1/admin/onboarding/",  # Onboarding routes (admin token auth)
    "/api/v1/public/",  # Public shareable endpoints (invoices, quotes)
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

class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that validates JWT tokens and attaches user context to requests.

    For authenticated requests:
    - Validates the JWT token from Authorization header
    - Fetches user from organization_users table
    - Verifies user belongs to the tenant (from X-Client-ID)
    - Attaches UserContext to request.state.user

    For public paths:
    - Skips authentication
    - request.state.user will be None
    """

    async def dispatch(self, request: Request, call_next):
        # Skip auth for CORS preflight OPTIONS requests
        if request.method == "OPTIONS":
            request.state.user = None
            return await call_next(request)

        # Skip auth for public paths
        if is_public_path(request.url.path):
            request.state.user = None
            return await call_next(request)

        # Get authorization header
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authorization header required"}
            )

        # Parse Bearer token
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid authorization header format"}
            )

        token = parts[1]

        # Get tenant ID
        tenant_id = request.headers.get("X-Client-ID") or os.getenv("CLIENT_ID", "africastay")

        try:
            # Get tenant config for Supabase credentials
            config = get_config(tenant_id)
            auth_service = AuthService(
                supabase_url=config.supabase_url,
                supabase_key=config.supabase_service_key
            )

            # Verify JWT
            valid, payload = auth_service.verify_jwt(token)
            if not valid:
                return JSONResponse(
                    status_code=401,
                    content={"detail": payload.get("error", "Invalid token")}
                )

            # Get auth user ID from token
            auth_user_id = payload.get("sub")
            if not auth_user_id:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid token payload"}
                )

            # Fetch user from database
            user = await auth_service.get_user_by_auth_id(auth_user_id, tenant_id)
            if not user:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "User not found in this organization"}
                )

            if not user.get("is_active", False):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "User account is deactivated"}
                )

            # Attach user context to request
            request.state.user = UserContext(
                user_id=user["id"],
                auth_user_id=auth_user_id,
                email=user["email"],
                name=user["name"],
                role=user["role"],
                tenant_id=user["tenant_id"],
                is_active=user["is_active"]
            )

        except FileNotFoundError:
            return JSONResponse(
                status_code=400,
                content={"detail": f"Unknown client: {tenant_id}"}
            )
        except Exception as e:
            logger.error(f"Auth middleware error: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Authentication error"}
            )

        return await call_next(request)


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
