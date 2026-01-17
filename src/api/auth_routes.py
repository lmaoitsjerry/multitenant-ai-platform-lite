"""
Authentication API Routes

Endpoints for user authentication, session management, and password operations.
"""

import os
import logging
from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.services.auth_service import AuthService
from config.loader import get_config, ClientConfig

logger = logging.getLogger(__name__)

# Initialize rate limiter for auth endpoints
# Key function uses remote IP address for rate limiting
limiter = Limiter(key_func=get_remote_address)

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


# ==================== Pydantic Models ====================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: Optional[str] = None  # Can be provided or use header


class LoginResponse(BaseModel):
    success: bool
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[int] = None
    user: Optional[dict] = None
    error: Optional[str] = None


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordChangeRequest(BaseModel):
    new_password: str


class PasswordUpdateWithTokenRequest(BaseModel):
    token: str
    new_password: str


class AcceptInviteRequest(BaseModel):
    password: str
    name: Optional[str] = None  # Can update name if desired


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None


# ==================== Dependencies ====================

def get_auth_service(x_client_id: str = Header(None, alias="X-Client-ID")) -> AuthService:
    """Get AuthService instance for the tenant"""
    client_id = x_client_id or os.getenv("CLIENT_ID", "africastay")

    try:
        config = get_config(client_id)
        return AuthService(
            supabase_url=config.supabase_url,
            supabase_key=config.supabase_service_key
        )
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail=f"Unknown client: {client_id}")


def get_platform_auth_service() -> AuthService:
    """
    Get platform-level AuthService for tenant-agnostic operations like login.

    Uses environment variables directly since all tenants share the same Supabase instance.
    This allows users to login without knowing their tenant ID - the system will
    auto-detect their tenant from their organization membership.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        raise HTTPException(status_code=500, detail="Platform auth not configured")

    return AuthService(
        supabase_url=supabase_url,
        supabase_key=supabase_key
    )


def get_tenant_id(x_client_id: str = Header(None, alias="X-Client-ID")) -> str:
    """Get tenant ID from header"""
    return x_client_id or os.getenv("CLIENT_ID", "africastay")


# ==================== Auth Endpoints ====================

@auth_router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")  # Prevent brute force: 5 login attempts per minute per IP
async def login(
    request: Request,  # Required for rate limiter
    login_data: LoginRequest,  # Renamed from 'request' to avoid conflict
    auth_service: AuthService = Depends(get_platform_auth_service),
    x_client_id: str = Header(None, alias="X-Client-ID")
):
    """
    Authenticate user with email and password.

    TENANT-AGNOSTIC: If no tenant_id is provided (in request body or header),
    the system will automatically determine the user's tenant from their
    organization membership. This allows users to login without knowing their tenant ID.

    Returns JWT tokens and user information if successful.
    The response includes the user's tenant_id which should be stored for future requests.

    Rate limited to 5 requests per minute per IP to prevent brute force attacks.
    """
    # Use tenant_id from request body if provided, then header, otherwise None (auto-detect)
    effective_tenant_id = login_data.tenant_id or x_client_id or None

    success, result = await auth_service.login(
        email=login_data.email,
        password=login_data.password,
        tenant_id=effective_tenant_id
    )

    if not success:
        return LoginResponse(
            success=False,
            error=result.get("error", "Login failed")
        )

    return LoginResponse(
        success=True,
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        expires_at=result["expires_at"],
        user=result["user"]
    )


@auth_router.post("/logout")
async def logout(
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Log out current user and invalidate session.
    """
    await auth_service.logout()
    return {"success": True, "message": "Logged out successfully"}


@auth_router.post("/refresh")
async def refresh_token(
    request: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Refresh access token using refresh token.

    Returns new access and refresh tokens.
    """
    success, result = await auth_service.refresh_token(request.refresh_token)

    if not success:
        raise HTTPException(status_code=401, detail=result.get("error", "Invalid refresh token"))

    return {
        "success": True,
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "expires_at": result["expires_at"]
    }


@auth_router.get("/me")
async def get_current_user(
    request: Request,
    authorization: str = Header(None),
    auth_service: AuthService = Depends(get_auth_service),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Get current authenticated user information.

    Requires valid JWT token in Authorization header.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    token = parts[1]

    # Verify JWT
    valid, payload = auth_service.verify_jwt(token)
    if not valid:
        raise HTTPException(status_code=401, detail=payload.get("error", "Invalid token"))

    # Get user from database
    auth_user_id = payload.get("sub")
    if not auth_user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = await auth_service.get_user_by_auth_id(auth_user_id, tenant_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {
        "success": True,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "tenant_id": user["tenant_id"],
            "is_active": user["is_active"],
            "last_login_at": user.get("last_login_at")
        }
    }


@auth_router.post("/password/reset")
@limiter.limit("3/minute")  # Strict limit to prevent email enumeration abuse
async def request_password_reset(
    request: Request,  # Required for rate limiter
    reset_data: PasswordResetRequest,  # Renamed from 'request' to avoid conflict
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Request password reset email.

    Sends a password reset link to the user's email if the account exists.
    Always returns success to prevent email enumeration.

    Rate limited to 3 requests per minute per IP to prevent abuse.
    """
    await auth_service.request_password_reset(reset_data.email)
    return {
        "success": True,
        "message": "If an account exists with this email, a password reset link has been sent"
    }


@auth_router.post("/password/update")
@limiter.limit("5/minute")  # Prevent token brute force attempts
async def update_password_with_token(
    request: Request,  # Required for rate limiter
    update_data: PasswordUpdateWithTokenRequest,  # Renamed from 'request' to avoid conflict
    auth_service: AuthService = Depends(get_platform_auth_service)
):
    """
    Update password using a reset token from email.

    This endpoint handles the password reset flow:
    1. User clicks link in password reset email
    2. Frontend extracts token from URL
    3. Frontend calls this endpoint with token and new password
    4. Backend verifies token with Supabase and updates password

    Rate limited to 5 requests per minute per IP to prevent token brute force.
    """
    try:
        # Use Supabase's verify OTP to exchange token for session
        # Then update password with that session
        result = auth_service.client.auth.verify_otp({
            "token_hash": update_data.token,
            "type": "recovery"
        })

        if result.user:
            # Now update the password for this user
            auth_service.client.auth.admin.update_user_by_id(
                str(result.user.id),
                {"password": update_data.new_password}
            )
            return {"success": True, "message": "Password updated successfully"}
        else:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    except Exception as e:
        logger.error(f"Password update error: {e}")
        raise HTTPException(status_code=400, detail="Invalid or expired reset token. Please request a new reset link.")


@auth_router.post("/password/change")
async def change_password(
    request: PasswordChangeRequest,
    authorization: str = Header(None),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Change password for authenticated user.

    Requires valid JWT token in Authorization header.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    token = parts[1]

    # Verify current token is valid
    valid, payload = auth_service.verify_jwt(token)
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Update password
    success, result = await auth_service.update_password(token, request.new_password)

    if not success:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to change password"))

    return {"success": True, "message": "Password changed successfully"}


@auth_router.patch("/profile")
async def update_profile(
    request_body: ProfileUpdateRequest,
    request: Request,
    authorization: str = Header(None),
    auth_service: AuthService = Depends(get_auth_service),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Update current user's profile.

    Allows users to update their own name and phone number.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    token = parts[1]

    # Verify JWT
    valid, payload = auth_service.verify_jwt(token)
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Get user from database
    auth_user_id = payload.get("sub")
    if not auth_user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = await auth_service.get_user_by_auth_id(auth_user_id, tenant_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Build update data
    update_data = {}
    if request_body.name:
        update_data["name"] = request_body.name
    if request_body.phone is not None:
        update_data["phone"] = request_body.phone

    if not update_data:
        raise HTTPException(status_code=400, detail="No updates provided")

    # Update user in database
    from src.tools.supabase_tool import SupabaseTool

    try:
        config = get_config(tenant_id)
        db = SupabaseTool(config)

        updated = db.update_organization_user(user["id"], update_data)

        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update profile")

        return {
            "success": True,
            "message": "Profile updated successfully",
            "user": {
                "id": updated["id"],
                "email": updated["email"],
                "name": updated["name"],
                "role": updated["role"],
                "tenant_id": updated["tenant_id"],
                "is_active": updated["is_active"],
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to update profile")


@auth_router.post("/invite/accept")
async def accept_invitation(
    request: AcceptInviteRequest,
    token: str,  # Query parameter
    auth_service: AuthService = Depends(get_auth_service),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Accept an invitation and create user account.

    This is a public endpoint - no authentication required.
    The invitation token validates the request.
    """
    from src.tools.supabase_tool import SupabaseTool
    from config.loader import get_config

    try:
        config = get_config(tenant_id)
        db = SupabaseTool(config)

        # Get invitation by token
        invitation = db.get_invitation_by_token(token)
        if not invitation:
            raise HTTPException(status_code=400, detail="Invalid or expired invitation")

        # Check if already accepted
        if invitation.get("accepted_at"):
            raise HTTPException(status_code=400, detail="Invitation already accepted")

        # Check expiration
        expires_at = datetime.fromisoformat(invitation["expires_at"].replace("Z", "+00:00"))
        if expires_at < datetime.now(expires_at.tzinfo):
            raise HTTPException(status_code=400, detail="Invitation has expired")

        # Create auth user and organization user
        name = request.name or invitation["name"]
        success, result = await auth_service.create_auth_user(
            email=invitation["email"],
            password=request.password,
            name=name,
            tenant_id=invitation["tenant_id"],
            role=invitation["role"],
            invited_by=invitation.get("invited_by")
        )

        if not success:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to create account"))

        # Mark invitation as accepted
        db.accept_invitation(token, result["auth_user_id"])

        return {
            "success": True,
            "message": "Account created successfully. You can now log in.",
            "user": result["user"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accepting invitation: {e}")
        raise HTTPException(status_code=500, detail="An error occurred")


# ==================== Rate Limiter Export ====================

def get_auth_limiter():
    """
    Get the rate limiter instance for app state registration.

    The limiter must be registered with FastAPI's app state for the
    rate limiting decorators to work correctly.

    Usage in main.py:
        from src.api.auth_routes import get_auth_limiter
        limiter = get_auth_limiter()
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    """
    return limiter
