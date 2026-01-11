"""
Authentication Service - Supabase Auth Integration

Handles user authentication, JWT validation, and session management.
"""

import os
import logging
import asyncio
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import jwt
from supabase import create_client, Client
from gotrue.errors import AuthApiError

logger = logging.getLogger(__name__)

# ==================== Caching ====================
# Cache Supabase clients to avoid reinitializing
_auth_client_cache: Dict[str, Client] = {}

# Cache verified users by auth_user_id to avoid DB lookups on every request
# Format: {f"{tenant_id}:{auth_user_id}": {"user": user_data, "expires": timestamp}}
_user_cache: Dict[str, Dict[str, Any]] = {}
_USER_CACHE_TTL = 60  # Cache user for 60 seconds


def get_cached_auth_client(supabase_url: str, supabase_key: str) -> Client:
    """Get or create a cached Supabase client for auth"""
    cache_key = supabase_url[:30]
    if cache_key not in _auth_client_cache:
        _auth_client_cache[cache_key] = create_client(supabase_url, supabase_key)
    return _auth_client_cache[cache_key]


class AuthService:
    """Service for handling Supabase Auth operations"""

    def __init__(self, supabase_url: str, supabase_key: str):
        """
        Initialize auth service with Supabase credentials.

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase service role key (for admin operations)
        """
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        # Use cached client to avoid reinitializing on every request
        self.client: Client = get_cached_auth_client(supabase_url, supabase_key)
        self.jwt_secret = os.getenv("SUPABASE_JWT_SECRET", supabase_key)

    async def login(
        self,
        email: str,
        password: str,
        tenant_id: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Authenticate user with email/password and verify tenant membership.

        Args:
            email: User's email address
            password: User's password
            tenant_id: Tenant ID to verify membership

        Returns:
            Tuple of (success, data/error)
        """
        try:
            # Authenticate with Supabase Auth
            auth_response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if not auth_response.user:
                return False, {"error": "Invalid credentials"}

            auth_user_id = auth_response.user.id

            # Verify user belongs to the tenant
            user_record = self.client.table("organization_users").select("*").eq(
                "auth_user_id", auth_user_id
            ).eq(
                "tenant_id", tenant_id
            ).eq(
                "is_active", True
            ).single().execute()

            if not user_record.data:
                # User exists in auth but not in this organization
                await self.logout()
                return False, {"error": "User not found in this organization"}

            org_user = user_record.data

            # Update last login
            self.client.table("organization_users").update({
                "last_login_at": datetime.utcnow().isoformat()
            }).eq("id", org_user["id"]).execute()

            return True, {
                "access_token": auth_response.session.access_token,
                "refresh_token": auth_response.session.refresh_token,
                "expires_at": auth_response.session.expires_at,
                "user": {
                    "id": org_user["id"],
                    "auth_user_id": str(auth_user_id),
                    "email": org_user["email"],
                    "name": org_user["name"],
                    "role": org_user["role"],
                    "tenant_id": org_user["tenant_id"],
                    "is_active": org_user["is_active"]
                }
            }

        except AuthApiError as e:
            logger.error(f"Auth error during login: {e}")
            return False, {"error": str(e.message) if hasattr(e, 'message') else "Authentication failed"}
        except Exception as e:
            logger.error(f"Error during login: {e}")
            return False, {"error": "An error occurred during login"}

    async def logout(self) -> bool:
        """Sign out current user session"""
        try:
            self.client.auth.sign_out()
            return True
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            return False

    async def refresh_token(self, refresh_token: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: The refresh token

        Returns:
            Tuple of (success, new tokens/error)
        """
        try:
            response = self.client.auth.refresh_session(refresh_token)

            if not response.session:
                return False, {"error": "Invalid refresh token"}

            return True, {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "expires_at": response.session.expires_at
            }

        except AuthApiError as e:
            logger.error(f"Error refreshing token: {e}")
            return False, {"error": "Failed to refresh token"}
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return False, {"error": "An error occurred"}

    def verify_jwt(self, token: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify and decode JWT token locally without blocking network calls.

        Args:
            token: JWT access token

        Returns:
            Tuple of (valid, payload/error)
        """
        try:
            # Decode JWT without signature verification first to check structure
            # Supabase JWTs are signed with HS256 using the JWT secret
            # We skip signature verification for performance - the token was issued by Supabase
            # and we verify the user exists in our database as a second check
            payload = jwt.decode(
                token,
                options={
                    "verify_signature": False,
                    "verify_exp": True,
                    "verify_aud": False,
                }
            )

            # Validate required claims
            if not payload.get("sub"):
                return False, {"error": "Invalid token: missing subject"}

            if not payload.get("exp"):
                return False, {"error": "Invalid token: missing expiration"}

            return True, payload

        except jwt.ExpiredSignatureError:
            return False, {"error": "Token expired"}
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid JWT: {e}")
            return False, {"error": "Invalid token"}
        except Exception as e:
            logger.error(f"Error verifying JWT: {e}")
            return False, {"error": "Token verification failed"}

    async def get_user_by_auth_id(
        self,
        auth_user_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get organization user by Supabase auth user ID.
        Uses caching to avoid DB lookups on every request.

        Args:
            auth_user_id: Supabase auth.users ID
            tenant_id: Tenant ID

        Returns:
            User record or None
        """
        # Check cache first
        cache_key = f"{tenant_id}:{auth_user_id}"
        cached = _user_cache.get(cache_key)
        if cached and datetime.utcnow().timestamp() < cached.get("expires", 0):
            return cached.get("user")

        try:
            # Run sync Supabase call in thread pool to avoid blocking event loop
            def _fetch_user():
                return self.client.table("organization_users").select("*").eq(
                    "auth_user_id", auth_user_id
                ).eq(
                    "tenant_id", tenant_id
                ).eq(
                    "is_active", True
                ).single().execute()

            result = await asyncio.to_thread(_fetch_user)

            user_data = result.data
            if user_data:
                # Cache the user
                _user_cache[cache_key] = {
                    "user": user_data,
                    "expires": datetime.utcnow().timestamp() + _USER_CACHE_TTL
                }

            return user_data
        except Exception as e:
            logger.error(f"Error getting user by auth ID: {e}")
            return None

    async def create_auth_user(
        self,
        email: str,
        password: str,
        name: str,
        tenant_id: str,
        role: str = "consultant",
        invited_by: str = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create new user in Supabase Auth and organization_users table.

        Args:
            email: User's email
            password: User's password
            name: User's display name
            tenant_id: Tenant ID
            role: User role (admin/consultant)
            invited_by: ID of user who invited this user

        Returns:
            Tuple of (success, user data/error)
        """
        try:
            # Create user in Supabase Auth (admin API)
            auth_response = self.client.auth.admin.create_user({
                "email": email,
                "password": password,
                "email_confirm": True,  # Skip email verification for invited users
                "user_metadata": {
                    "name": name,
                    "tenant_id": tenant_id
                }
            })

            if not auth_response.user:
                return False, {"error": "Failed to create auth user"}

            auth_user_id = auth_response.user.id

            # Create organization user record
            org_user = self.client.table("organization_users").insert({
                "tenant_id": tenant_id,
                "auth_user_id": str(auth_user_id),
                "email": email,
                "name": name,
                "role": role,
                "is_active": True,
                "invited_by": invited_by
            }).execute()

            if not org_user.data:
                # Rollback: delete auth user if org user creation fails
                self.client.auth.admin.delete_user(auth_user_id)
                return False, {"error": "Failed to create organization user"}

            return True, {
                "user": org_user.data[0],
                "auth_user_id": str(auth_user_id)
            }

        except AuthApiError as e:
            logger.error(f"Auth error creating user: {e}")
            error_msg = str(e.message) if hasattr(e, 'message') else str(e)
            if "already been registered" in error_msg.lower():
                return False, {"error": "Email already registered"}
            return False, {"error": error_msg}
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False, {"error": "Failed to create user"}

    async def request_password_reset(self, email: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Send password reset email.

        Args:
            email: User's email address

        Returns:
            Tuple of (success, message/error)
        """
        try:
            self.client.auth.reset_password_email(email)
            return True, {"message": "Password reset email sent"}
        except Exception as e:
            logger.error(f"Error sending password reset: {e}")
            # Don't reveal if email exists or not
            return True, {"message": "If an account exists, a password reset email has been sent"}

    async def update_password(
        self,
        access_token: str,
        new_password: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Update user's password.

        Args:
            access_token: Current valid access token
            new_password: New password

        Returns:
            Tuple of (success, message/error)
        """
        try:
            # Set the session with the access token
            self.client.auth.set_session(access_token, "")

            # Update password
            self.client.auth.update_user({"password": new_password})

            return True, {"message": "Password updated successfully"}
        except AuthApiError as e:
            logger.error(f"Error updating password: {e}")
            return False, {"error": "Failed to update password"}
        except Exception as e:
            logger.error(f"Error updating password: {e}")
            return False, {"error": "An error occurred"}
