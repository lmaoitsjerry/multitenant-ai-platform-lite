"""
User Management API Routes

Endpoints for managing organization users and invitations.
Most endpoints require admin role.
"""

import os
import logging
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel, EmailStr
from typing import Optional, List

from src.middleware.auth_middleware import get_current_user, require_admin, UserContext
from src.tools.supabase_tool import SupabaseTool
from src.utils.email_sender import EmailSender
from config.loader import get_config

logger = logging.getLogger(__name__)

users_router = APIRouter(prefix="/api/v1/users", tags=["User Management"])


# ==================== Pydantic Models ====================

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    tenant_id: str
    is_active: bool
    created_at: Optional[str] = None
    last_login_at: Optional[str] = None


class UserListResponse(BaseModel):
    success: bool
    users: List[UserResponse]
    total: int


class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None


class InviteUserRequest(BaseModel):
    email: EmailStr
    name: str
    role: str = "consultant"


class InvitationResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    expires_at: str
    created_at: str


class InvitationListResponse(BaseModel):
    success: bool
    invitations: List[InvitationResponse]
    total: int


# ==================== Dependencies ====================

def get_supabase_tool(x_client_id: str = Header(None, alias="X-Client-ID")) -> SupabaseTool:
    """Get SupabaseTool instance for the tenant"""
    client_id = x_client_id or os.getenv("CLIENT_ID", "africastay")

    try:
        config = get_config(client_id)
        return SupabaseTool(config)
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail=f"Unknown client: {client_id}")


def get_email_sender(x_client_id: str = Header(None, alias="X-Client-ID")) -> EmailSender:
    """Get EmailSender instance for the tenant"""
    client_id = x_client_id or os.getenv("CLIENT_ID", "africastay")

    try:
        config = get_config(client_id)
        return EmailSender(config)
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail=f"Unknown client: {client_id}")


# ==================== User Endpoints ====================

@users_router.get("", response_model=UserListResponse)
async def list_users(
    request: Request,
    user: UserContext = Depends(require_admin),
    db: SupabaseTool = Depends(get_supabase_tool)
):
    """
    List all users in the organization.

    Requires admin role.
    """
    try:
        users = db.get_organization_users()

        return UserListResponse(
            success=True,
            users=[
                UserResponse(
                    id=u["id"],
                    email=u["email"],
                    name=u["name"],
                    role=u["role"],
                    tenant_id=u["tenant_id"],
                    is_active=u["is_active"],
                    created_at=u.get("created_at"),
                    last_login_at=u.get("last_login_at")
                )
                for u in users
            ],
            total=len(users)
        )
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail="Failed to list users")


# ==================== Invitation Endpoints ====================
# NOTE: These routes MUST be defined before /{user_id} routes to avoid path conflicts

@users_router.post("/invite")
async def invite_user(
    invite_request: InviteUserRequest,
    request: Request,
    user: UserContext = Depends(require_admin),
    db: SupabaseTool = Depends(get_supabase_tool),
    email_sender: EmailSender = Depends(get_email_sender),
    x_client_id: str = Header(None, alias="X-Client-ID")
):
    """
    Invite a new user to the organization.

    Sends an invitation email with a secure token.
    Invitation expires in 48 hours.
    """
    client_id = x_client_id or os.getenv("CLIENT_ID", "africastay")

    # Validate role
    if invite_request.role not in ["admin", "consultant"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'admin' or 'consultant'")

    # Check if user already exists
    existing_user = db.get_user_by_email(invite_request.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    try:
        # Create invitation record
        invitation = db.create_invitation(
            email=invite_request.email,
            name=invite_request.name,
            role=invite_request.role,
            invited_by=user.user_id
        )

        if not invitation:
            raise HTTPException(status_code=500, detail="Failed to create invitation")

        # Get config for branding
        config = get_config(client_id)

        # Send invitation email
        try:
            email_sender.send_invitation_email(
                to_email=invite_request.email,
                to_name=invite_request.name,
                invited_by_name=user.name,
                organization_name=config.company_name or client_id,
                invitation_token=invitation["token"],
                expires_at=datetime.fromisoformat(invitation["expires_at"].replace("Z", "+00:00"))
            )
        except Exception as e:
            logger.error(f"Failed to send invitation email: {e}")
            # Don't fail the whole request if email fails
            # Admin can resend or share token manually

        return {
            "success": True,
            "message": f"Invitation sent to {invite_request.email}",
            "invitation": InvitationResponse(
                id=invitation["id"],
                email=invitation["email"],
                name=invitation["name"],
                role=invitation["role"],
                expires_at=invitation["expires_at"],
                created_at=invitation["created_at"]
            )
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating invitation: {e}")
        raise HTTPException(status_code=500, detail="Failed to create invitation")


@users_router.get("/invitations", response_model=InvitationListResponse)
async def list_invitations(
    request: Request,
    user: UserContext = Depends(require_admin),
    db: SupabaseTool = Depends(get_supabase_tool)
):
    """
    List all pending invitations for the organization.

    Requires admin role.
    """
    try:
        invitations = db.get_invitations()

        return InvitationListResponse(
            success=True,
            invitations=[
                InvitationResponse(
                    id=inv["id"],
                    email=inv["email"],
                    name=inv["name"],
                    role=inv["role"],
                    expires_at=inv["expires_at"],
                    created_at=inv["created_at"]
                )
                for inv in invitations
            ],
            total=len(invitations)
        )
    except Exception as e:
        logger.error(f"Error listing invitations: {e}")
        raise HTTPException(status_code=500, detail="Failed to list invitations")


@users_router.delete("/invitations/{invitation_id}")
async def cancel_invitation(
    invitation_id: str,
    request: Request,
    user: UserContext = Depends(require_admin),
    db: SupabaseTool = Depends(get_supabase_tool)
):
    """
    Cancel a pending invitation.

    Requires admin role.
    """
    try:
        success = db.cancel_invitation(invitation_id)

        if not success:
            raise HTTPException(status_code=404, detail="Invitation not found")

        return {
            "success": True,
            "message": "Invitation cancelled"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling invitation: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel invitation")


@users_router.post("/invitations/{invitation_id}/resend")
async def resend_invitation(
    invitation_id: str,
    request: Request,
    user: UserContext = Depends(require_admin),
    db: SupabaseTool = Depends(get_supabase_tool),
    email_sender: EmailSender = Depends(get_email_sender),
    x_client_id: str = Header(None, alias="X-Client-ID")
):
    """
    Resend an invitation email.

    Generates a new token and extends expiration.
    """
    client_id = x_client_id or os.getenv("CLIENT_ID", "africastay")

    # Get existing invitation
    invitations = db.get_invitations()
    invitation = next((inv for inv in invitations if inv["id"] == invitation_id), None)

    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    try:
        # Cancel old invitation and create new one
        db.cancel_invitation(invitation_id)

        new_invitation = db.create_invitation(
            email=invitation["email"],
            name=invitation["name"],
            role=invitation["role"],
            invited_by=user.user_id
        )

        if not new_invitation:
            raise HTTPException(status_code=500, detail="Failed to resend invitation")

        # Get config for branding
        config = get_config(client_id)

        # Send invitation email
        email_sender.send_invitation_email(
            to_email=invitation["email"],
            to_name=invitation["name"],
            invited_by_name=user.name,
            organization_name=config.company_name or client_id,
            invitation_token=new_invitation["token"],
            expires_at=datetime.fromisoformat(new_invitation["expires_at"].replace("Z", "+00:00"))
        )

        return {
            "success": True,
            "message": f"Invitation resent to {invitation['email']}",
            "invitation": InvitationResponse(
                id=new_invitation["id"],
                email=new_invitation["email"],
                name=new_invitation["name"],
                role=new_invitation["role"],
                expires_at=new_invitation["expires_at"],
                created_at=new_invitation["created_at"]
            )
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resending invitation: {e}")
        raise HTTPException(status_code=500, detail="Failed to resend invitation")


# ==================== User Detail Endpoints ====================

@users_router.get("/{user_id}")
async def get_user(
    user_id: str,
    request: Request,
    user: UserContext = Depends(require_admin),
    db: SupabaseTool = Depends(get_supabase_tool)
):
    """
    Get user details by ID.

    Requires admin role.
    """
    try:
        target_user = db.get_user_by_id(user_id)

        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "success": True,
            "user": UserResponse(
                id=target_user["id"],
                email=target_user["email"],
                name=target_user["name"],
                role=target_user["role"],
                tenant_id=target_user["tenant_id"],
                is_active=target_user["is_active"],
                created_at=target_user.get("created_at"),
                last_login_at=target_user.get("last_login_at")
            )
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user")


@users_router.patch("/{user_id}")
async def update_user(
    user_id: str,
    update_request: UpdateUserRequest,
    request: Request,
    user: UserContext = Depends(require_admin),
    db: SupabaseTool = Depends(get_supabase_tool)
):
    """
    Update user details.

    Admins can update name and role.
    Cannot demote yourself from admin.
    """
    # Check if user exists
    target_user = db.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent self-demotion
    if user_id == user.user_id and update_request.role and update_request.role != "admin":
        raise HTTPException(status_code=400, detail="Cannot demote yourself from admin")

    # Build update data
    update_data = {}
    if update_request.name:
        update_data["name"] = update_request.name
    if update_request.role:
        if update_request.role not in ["admin", "consultant"]:
            raise HTTPException(status_code=400, detail="Invalid role. Must be 'admin' or 'consultant'")
        update_data["role"] = update_request.role

    if not update_data:
        raise HTTPException(status_code=400, detail="No updates provided")

    try:
        updated_user = db.update_organization_user(user_id, user.tenant_id, update_data)

        if not updated_user:
            raise HTTPException(status_code=500, detail="Failed to update user")

        return {
            "success": True,
            "user": UserResponse(
                id=updated_user["id"],
                email=updated_user["email"],
                name=updated_user["name"],
                role=updated_user["role"],
                tenant_id=updated_user["tenant_id"],
                is_active=updated_user["is_active"],
                created_at=updated_user.get("created_at"),
                last_login_at=updated_user.get("last_login_at")
            )
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user")


@users_router.delete("/{user_id}")
async def deactivate_user(
    user_id: str,
    request: Request,
    user: UserContext = Depends(require_admin),
    db: SupabaseTool = Depends(get_supabase_tool)
):
    """
    Deactivate a user account.

    Users can be reactivated by updating is_active to true.
    Cannot deactivate yourself.
    """
    # Prevent self-deactivation
    if user_id == user.user_id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    # Check if user exists
    target_user = db.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        success = db.deactivate_user(user_id, user.tenant_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to deactivate user")

        return {
            "success": True,
            "message": f"User {target_user['email']} has been deactivated"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating user: {e}")
        raise HTTPException(status_code=500, detail="Failed to deactivate user")
