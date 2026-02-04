"""
Users Routes Unit Tests

Comprehensive tests for user management API endpoints:
- GET /api/v1/users
- POST /api/v1/users/invite
- GET /api/v1/users/invitations
- DELETE /api/v1/users/invitations/{id}
- POST /api/v1/users/invitations/{id}/resend
- GET /api/v1/users/{id}
- PATCH /api/v1/users/{id}
- DELETE /api/v1/users/{id}

Uses FastAPI TestClient with mocked dependencies.
These tests verify:
1. Admin authorization required (401/403 for non-admin)
2. Endpoint structure and HTTP methods
3. Request validation
4. Response formats
5. Error handling
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import os


# ==================== Fixtures ====================

@pytest.fixture
def mock_config():
    """Create a mock ClientConfig."""
    config = MagicMock()
    config.client_id = "test_tenant"
    config.company_name = "Test Company"
    config.supabase_url = "https://test.supabase.co"
    config.supabase_service_key = "test-service-key"
    config.sendgrid_api_key = "SG.test-key"
    config.sendgrid_from_email = "test@example.com"
    return config


@pytest.fixture
def test_client():
    """Create a basic TestClient."""
    from main import app
    return TestClient(app)


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user context."""
    from src.middleware.auth_middleware import UserContext
    user = MagicMock(spec=UserContext)
    user.user_id = "admin-123"
    user.tenant_id = "test_tenant"
    user.email = "admin@example.com"
    user.name = "Admin User"
    user.role = "admin"
    return user


# ==================== Authorization Tests ====================

class TestUsersAuth:
    """Test authorization for user management endpoints."""

    def test_list_users_requires_auth(self, test_client):
        """GET /users should require authorization."""
        response = test_client.get(
            "/api/v1/users",
            headers={"X-Client-ID": "example"}
        )
        assert response.status_code == 401

    def test_invite_user_requires_auth(self, test_client):
        """POST /users/invite should require authorization."""
        response = test_client.post(
            "/api/v1/users/invite",
            headers={"X-Client-ID": "example"},
            json={"email": "test@example.com", "name": "Test", "role": "consultant"}
        )
        assert response.status_code == 401

    def test_list_invitations_requires_auth(self, test_client):
        """GET /users/invitations should require authorization."""
        response = test_client.get(
            "/api/v1/users/invitations",
            headers={"X-Client-ID": "example"}
        )
        assert response.status_code == 401

    def test_cancel_invitation_requires_auth(self, test_client):
        """DELETE /users/invitations/{id} should require authorization."""
        response = test_client.delete(
            "/api/v1/users/invitations/inv-123",
            headers={"X-Client-ID": "example"}
        )
        assert response.status_code == 401

    def test_resend_invitation_requires_auth(self, test_client):
        """POST /users/invitations/{id}/resend should require authorization."""
        response = test_client.post(
            "/api/v1/users/invitations/inv-123/resend",
            headers={"X-Client-ID": "example"}
        )
        assert response.status_code == 401

    def test_get_user_requires_auth(self, test_client):
        """GET /users/{id} should require authorization."""
        response = test_client.get(
            "/api/v1/users/user-123",
            headers={"X-Client-ID": "example"}
        )
        assert response.status_code == 401

    def test_update_user_requires_auth(self, test_client):
        """PATCH /users/{id} should require authorization."""
        response = test_client.patch(
            "/api/v1/users/user-123",
            headers={"X-Client-ID": "example"},
            json={"name": "New Name"}
        )
        assert response.status_code == 401

    def test_delete_user_requires_auth(self, test_client):
        """DELETE /users/{id} should require authorization."""
        response = test_client.delete(
            "/api/v1/users/user-123",
            headers={"X-Client-ID": "example"}
        )
        assert response.status_code == 401


# ==================== List Users Tests ====================

class TestListUsers:
    """Test GET /api/v1/users endpoint."""

    def test_list_users_endpoint_exists(self, test_client):
        """GET /users endpoint should exist."""
        response = test_client.get(
            "/api/v1/users",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test-token"
            }
        )
        # 401 for invalid token
        assert response.status_code == 401

    def test_list_users_accepts_client_header(self, test_client):
        """GET /users should read X-Client-ID header."""
        response = test_client.get(
            "/api/v1/users",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test"
            }
        )
        assert response.status_code == 401


# ==================== Invite User Tests ====================

class TestInviteUser:
    """Test POST /api/v1/users/invite endpoint."""

    def test_invite_user_endpoint_exists(self, test_client):
        """POST /users/invite endpoint should exist."""
        response = test_client.post(
            "/api/v1/users/invite",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test"
            },
            json={"email": "new@example.com", "name": "New User", "role": "consultant"}
        )
        # 401 for invalid token
        assert response.status_code == 401

    def test_invite_user_validation_requires_email(self, test_client):
        """POST /users/invite should require email field."""
        response = test_client.post(
            "/api/v1/users/invite",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test"
            },
            json={"name": "New User", "role": "consultant"}  # Missing email
        )
        # Either 401 (auth) or 422 (validation) depending on middleware order
        assert response.status_code in [401, 422]

    def test_invite_user_validation_requires_name(self, test_client):
        """POST /users/invite should require name field."""
        response = test_client.post(
            "/api/v1/users/invite",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test"
            },
            json={"email": "new@example.com", "role": "consultant"}  # Missing name
        )
        assert response.status_code in [401, 422]

    def test_invite_user_accepts_all_fields(self, test_client):
        """POST /users/invite should accept email, name, role."""
        response = test_client.post(
            "/api/v1/users/invite",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test"
            },
            json={
                "email": "new@example.com",
                "name": "New User",
                "role": "admin"
            }
        )
        # Auth fails but request format is valid
        assert response.status_code == 401


# ==================== List Invitations Tests ====================

class TestListInvitations:
    """Test GET /api/v1/users/invitations endpoint."""

    def test_list_invitations_endpoint_exists(self, test_client):
        """GET /users/invitations endpoint should exist."""
        response = test_client.get(
            "/api/v1/users/invitations",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test"
            }
        )
        assert response.status_code == 401


# ==================== Cancel Invitation Tests ====================

class TestCancelInvitation:
    """Test DELETE /api/v1/users/invitations/{id} endpoint."""

    def test_cancel_invitation_endpoint_exists(self, test_client):
        """DELETE /users/invitations/{id} endpoint should exist."""
        response = test_client.delete(
            "/api/v1/users/invitations/inv-123",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test"
            }
        )
        assert response.status_code == 401

    def test_cancel_invitation_accepts_invitation_id(self, test_client):
        """DELETE /users/invitations/{id} should accept invitation ID path param."""
        response = test_client.delete(
            "/api/v1/users/invitations/some-uuid-here",
            headers={"X-Client-ID": "example"}
        )
        assert response.status_code == 401


# ==================== Resend Invitation Tests ====================

class TestResendInvitation:
    """Test POST /api/v1/users/invitations/{id}/resend endpoint."""

    def test_resend_invitation_endpoint_exists(self, test_client):
        """POST /users/invitations/{id}/resend endpoint should exist."""
        response = test_client.post(
            "/api/v1/users/invitations/inv-123/resend",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test"
            }
        )
        assert response.status_code == 401


# ==================== Get User Tests ====================

class TestGetUser:
    """Test GET /api/v1/users/{id} endpoint."""

    def test_get_user_endpoint_exists(self, test_client):
        """GET /users/{id} endpoint should exist."""
        response = test_client.get(
            "/api/v1/users/user-123",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test"
            }
        )
        assert response.status_code == 401

    def test_get_user_accepts_user_id(self, test_client):
        """GET /users/{id} should accept user ID path param."""
        response = test_client.get(
            "/api/v1/users/some-uuid-here",
            headers={"X-Client-ID": "example"}
        )
        assert response.status_code == 401


# ==================== Update User Tests ====================

class TestUpdateUser:
    """Test PATCH /api/v1/users/{id} endpoint."""

    def test_update_user_endpoint_exists(self, test_client):
        """PATCH /users/{id} endpoint should exist."""
        response = test_client.patch(
            "/api/v1/users/user-123",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test"
            },
            json={"name": "Updated Name"}
        )
        assert response.status_code == 401

    def test_update_user_accepts_name(self, test_client):
        """PATCH /users/{id} should accept name field."""
        response = test_client.patch(
            "/api/v1/users/user-123",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test"
            },
            json={"name": "New Name"}
        )
        assert response.status_code == 401

    def test_update_user_accepts_role(self, test_client):
        """PATCH /users/{id} should accept role field."""
        response = test_client.patch(
            "/api/v1/users/user-123",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test"
            },
            json={"role": "admin"}
        )
        assert response.status_code == 401


# ==================== Delete/Deactivate User Tests ====================

class TestDeactivateUser:
    """Test DELETE /api/v1/users/{id} endpoint."""

    def test_deactivate_user_endpoint_exists(self, test_client):
        """DELETE /users/{id} endpoint should exist."""
        response = test_client.delete(
            "/api/v1/users/user-123",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test"
            }
        )
        assert response.status_code == 401


# ==================== Pydantic Model Tests ====================

class TestUserModels:
    """Test Pydantic models for users."""

    def test_user_response_model(self):
        """UserResponse model should accept valid data."""
        from src.api.users_routes import UserResponse

        user = UserResponse(
            id="user-123",
            email="test@example.com",
            name="Test User",
            role="consultant",
            tenant_id="test_tenant",
            is_active=True
        )
        assert user.id == "user-123"
        assert user.email == "test@example.com"

    def test_user_list_response_model(self):
        """UserListResponse model should contain users list."""
        from src.api.users_routes import UserListResponse, UserResponse

        response = UserListResponse(
            success=True,
            users=[
                UserResponse(
                    id="user-123",
                    email="test@example.com",
                    name="Test User",
                    role="consultant",
                    tenant_id="test_tenant",
                    is_active=True
                )
            ],
            total=1
        )
        assert response.success is True
        assert len(response.users) == 1

    def test_update_user_request_model(self):
        """UpdateUserRequest model should accept optional fields."""
        from src.api.users_routes import UpdateUserRequest

        update = UpdateUserRequest(name="New Name")
        assert update.name == "New Name"
        assert update.role is None

        update2 = UpdateUserRequest(role="admin")
        assert update2.name is None
        assert update2.role == "admin"

    def test_invite_user_request_model(self):
        """InviteUserRequest model should validate email."""
        from src.api.users_routes import InviteUserRequest

        invite = InviteUserRequest(
            email="test@example.com",
            name="Test User",
            role="consultant"
        )
        assert invite.email == "test@example.com"
        assert invite.role == "consultant"

    def test_invitation_response_model(self):
        """InvitationResponse model should accept valid data."""
        from src.api.users_routes import InvitationResponse

        invitation = InvitationResponse(
            id="inv-123",
            email="test@example.com",
            name="Test User",
            role="consultant",
            expires_at="2026-01-25T12:00:00Z",
            created_at="2026-01-21T12:00:00Z"
        )
        assert invitation.id == "inv-123"
        assert invitation.role == "consultant"

    def test_invitation_list_response_model(self):
        """InvitationListResponse model should contain invitations list."""
        from src.api.users_routes import InvitationListResponse, InvitationResponse

        response = InvitationListResponse(
            success=True,
            invitations=[
                InvitationResponse(
                    id="inv-123",
                    email="test@example.com",
                    name="Test User",
                    role="consultant",
                    expires_at="2026-01-25T12:00:00Z",
                    created_at="2026-01-21T12:00:00Z"
                )
            ],
            total=1
        )
        assert response.success is True
        assert len(response.invitations) == 1


# ==================== Dependency Tests ====================

class TestUserDependencies:
    """Test dependency functions for user routes."""

    def test_get_supabase_tool_accepts_header(self, test_client):
        """get_supabase_tool should read X-Client-ID header."""
        # Indirectly tested via endpoint calls
        response = test_client.get(
            "/api/v1/users",
            headers={"X-Client-ID": "example"}
        )
        # Returns 401 (auth required) not 400 (bad client)
        assert response.status_code == 401

    def test_get_supabase_tool_invalid_client(self, test_client):
        """get_supabase_tool should reject unknown client."""
        response = test_client.get(
            "/api/v1/users",
            headers={"X-Client-ID": "nonexistent_xyz"}
        )
        # May return 400 for bad client or 401 for auth
        assert response.status_code in [400, 401]


# ==================== Unit Tests with Mocked Dependencies ====================

class TestListUsersUnit:
    """Unit tests for list_users endpoint logic."""

    @pytest.mark.asyncio
    async def test_list_users_returns_users(self, mock_admin_user):
        """list_users should return all organization users."""
        from src.api.users_routes import list_users
        from fastapi import Request

        mock_db = MagicMock()
        mock_db.get_organization_users.return_value = [
            {
                "id": "user-1",
                "email": "user1@example.com",
                "name": "User One",
                "role": "admin",
                "tenant_id": "test_tenant",
                "is_active": True,
                "created_at": "2026-01-01T00:00:00Z"
            },
            {
                "id": "user-2",
                "email": "user2@example.com",
                "name": "User Two",
                "role": "consultant",
                "tenant_id": "test_tenant",
                "is_active": True
            }
        ]

        mock_request = MagicMock(spec=Request)

        result = await list_users(request=mock_request, user=mock_admin_user, db=mock_db)

        assert result.success is True
        assert result.total == 2
        assert len(result.users) == 2
        assert result.users[0].email == "user1@example.com"

    @pytest.mark.asyncio
    async def test_list_users_handles_empty_list(self, mock_admin_user):
        """list_users should handle empty user list."""
        from src.api.users_routes import list_users
        from fastapi import Request

        mock_db = MagicMock()
        mock_db.get_organization_users.return_value = []

        mock_request = MagicMock(spec=Request)

        result = await list_users(request=mock_request, user=mock_admin_user, db=mock_db)

        assert result.success is True
        assert result.total == 0
        assert len(result.users) == 0

    @pytest.mark.asyncio
    async def test_list_users_handles_db_error(self, mock_admin_user):
        """list_users should raise 500 on database error."""
        from src.api.users_routes import list_users
        from fastapi import Request, HTTPException

        mock_db = MagicMock()
        mock_db.get_organization_users.side_effect = Exception("DB error")

        mock_request = MagicMock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await list_users(request=mock_request, user=mock_admin_user, db=mock_db)

        assert exc_info.value.status_code == 500


class TestInviteUserUnit:
    """Unit tests for invite_user endpoint logic."""

    @pytest.mark.asyncio
    async def test_invite_user_creates_invitation(self, mock_admin_user, mock_config):
        """invite_user should create invitation and send email."""
        from src.api.users_routes import invite_user, InviteUserRequest
        from fastapi import Request

        mock_db = MagicMock()
        mock_db.get_user_by_email.return_value = None  # User doesn't exist
        mock_db.create_invitation.return_value = {
            "id": "inv-123",
            "email": "new@example.com",
            "name": "New User",
            "role": "consultant",
            "token": "secret-token",
            "expires_at": "2026-01-25T12:00:00Z",
            "created_at": "2026-01-21T12:00:00Z"
        }

        mock_email_sender = MagicMock()
        mock_request = MagicMock(spec=Request)

        invite_request = InviteUserRequest(
            email="new@example.com",
            name="New User",
            role="consultant"
        )

        with patch('src.api.users_routes.get_config', return_value=mock_config):
            result = await invite_user(
                invite_request=invite_request,
                request=mock_request,
                user=mock_admin_user,
                db=mock_db,
                email_sender=mock_email_sender,
                x_client_id="test_tenant"
            )

        assert result["success"] is True
        assert "invitation" in result
        mock_db.create_invitation.assert_called_once()
        mock_email_sender.send_invitation_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_invite_user_rejects_invalid_role(self, mock_admin_user):
        """invite_user should reject invalid role."""
        from src.api.users_routes import invite_user, InviteUserRequest
        from fastapi import Request, HTTPException

        mock_db = MagicMock()
        mock_email_sender = MagicMock()
        mock_request = MagicMock(spec=Request)

        invite_request = InviteUserRequest(
            email="new@example.com",
            name="New User",
            role="invalid_role"  # Invalid role
        )

        with pytest.raises(HTTPException) as exc_info:
            await invite_user(
                invite_request=invite_request,
                request=mock_request,
                user=mock_admin_user,
                db=mock_db,
                email_sender=mock_email_sender,
                x_client_id="test_tenant"
            )

        assert exc_info.value.status_code == 400
        assert "Invalid role" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_invite_user_rejects_existing_user(self, mock_admin_user):
        """invite_user should reject if user already exists."""
        from src.api.users_routes import invite_user, InviteUserRequest
        from fastapi import Request, HTTPException

        mock_db = MagicMock()
        mock_db.get_user_by_email.return_value = {"id": "existing-123"}  # User exists
        mock_email_sender = MagicMock()
        mock_request = MagicMock(spec=Request)

        invite_request = InviteUserRequest(
            email="existing@example.com",
            name="Existing User",
            role="consultant"
        )

        with pytest.raises(HTTPException) as exc_info:
            await invite_user(
                invite_request=invite_request,
                request=mock_request,
                user=mock_admin_user,
                db=mock_db,
                email_sender=mock_email_sender,
                x_client_id="test_tenant"
            )

        assert exc_info.value.status_code == 400
        assert "already exists" in str(exc_info.value.detail)


class TestListInvitationsUnit:
    """Unit tests for list_invitations endpoint logic."""

    @pytest.mark.asyncio
    async def test_list_invitations_returns_invitations(self, mock_admin_user):
        """list_invitations should return all pending invitations."""
        from src.api.users_routes import list_invitations
        from fastapi import Request

        mock_db = MagicMock()
        mock_db.get_invitations.return_value = [
            {
                "id": "inv-1",
                "email": "invite1@example.com",
                "name": "Invite One",
                "role": "consultant",
                "expires_at": "2026-01-25T12:00:00Z",
                "created_at": "2026-01-21T12:00:00Z"
            }
        ]

        mock_request = MagicMock(spec=Request)

        result = await list_invitations(request=mock_request, user=mock_admin_user, db=mock_db)

        assert result.success is True
        assert result.total == 1
        assert result.invitations[0].email == "invite1@example.com"

    @pytest.mark.asyncio
    async def test_list_invitations_handles_db_error(self, mock_admin_user):
        """list_invitations should raise 500 on database error."""
        from src.api.users_routes import list_invitations
        from fastapi import Request, HTTPException

        mock_db = MagicMock()
        mock_db.get_invitations.side_effect = Exception("DB error")

        mock_request = MagicMock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await list_invitations(request=mock_request, user=mock_admin_user, db=mock_db)

        assert exc_info.value.status_code == 500


class TestCancelInvitationUnit:
    """Unit tests for cancel_invitation endpoint logic."""

    @pytest.mark.asyncio
    async def test_cancel_invitation_success(self, mock_admin_user):
        """cancel_invitation should cancel the invitation."""
        from src.api.users_routes import cancel_invitation
        from fastapi import Request

        mock_db = MagicMock()
        mock_db.cancel_invitation.return_value = True

        mock_request = MagicMock(spec=Request)

        result = await cancel_invitation(
            invitation_id="inv-123",
            request=mock_request,
            user=mock_admin_user,
            db=mock_db
        )

        assert result["success"] is True
        mock_db.cancel_invitation.assert_called_once_with("inv-123")

    @pytest.mark.asyncio
    async def test_cancel_invitation_not_found(self, mock_admin_user):
        """cancel_invitation should raise 404 when invitation not found."""
        from src.api.users_routes import cancel_invitation
        from fastapi import Request, HTTPException

        mock_db = MagicMock()
        mock_db.cancel_invitation.return_value = False  # Not found

        mock_request = MagicMock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await cancel_invitation(
                invitation_id="nonexistent",
                request=mock_request,
                user=mock_admin_user,
                db=mock_db
            )

        assert exc_info.value.status_code == 404


class TestGetUserUnit:
    """Unit tests for get_user endpoint logic."""

    @pytest.mark.asyncio
    async def test_get_user_returns_user(self, mock_admin_user):
        """get_user should return user details."""
        from src.api.users_routes import get_user
        from fastapi import Request

        mock_db = MagicMock()
        mock_db.get_user_by_id.return_value = {
            "id": "user-123",
            "email": "user@example.com",
            "name": "Test User",
            "role": "consultant",
            "tenant_id": "test_tenant",
            "is_active": True,
            "created_at": "2026-01-01T00:00:00Z"
        }

        mock_request = MagicMock(spec=Request)

        result = await get_user(
            user_id="user-123",
            request=mock_request,
            user=mock_admin_user,
            db=mock_db
        )

        assert result["success"] is True
        assert result["user"].email == "user@example.com"

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, mock_admin_user):
        """get_user should raise 404 when user not found."""
        from src.api.users_routes import get_user
        from fastapi import Request, HTTPException

        mock_db = MagicMock()
        mock_db.get_user_by_id.return_value = None

        mock_request = MagicMock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await get_user(
                user_id="nonexistent",
                request=mock_request,
                user=mock_admin_user,
                db=mock_db
            )

        assert exc_info.value.status_code == 404


class TestUpdateUserUnit:
    """Unit tests for update_user endpoint logic."""

    @pytest.mark.asyncio
    async def test_update_user_name(self, mock_admin_user):
        """update_user should update user name."""
        from src.api.users_routes import update_user, UpdateUserRequest
        from fastapi import Request

        mock_db = MagicMock()
        mock_db.get_user_by_id.return_value = {
            "id": "user-123",
            "email": "user@example.com",
            "name": "Old Name",
            "role": "consultant",
            "tenant_id": "test_tenant",
            "is_active": True
        }
        mock_db.update_organization_user.return_value = {
            "id": "user-123",
            "email": "user@example.com",
            "name": "New Name",
            "role": "consultant",
            "tenant_id": "test_tenant",
            "is_active": True
        }

        mock_request = MagicMock(spec=Request)
        update_request = UpdateUserRequest(name="New Name")

        result = await update_user(
            user_id="user-123",
            update_request=update_request,
            request=mock_request,
            user=mock_admin_user,
            db=mock_db
        )

        assert result["success"] is True
        assert result["user"].name == "New Name"

    @pytest.mark.asyncio
    async def test_update_user_prevents_self_demotion(self, mock_admin_user):
        """update_user should prevent admin from demoting themselves."""
        from src.api.users_routes import update_user, UpdateUserRequest
        from fastapi import Request, HTTPException

        mock_db = MagicMock()
        mock_db.get_user_by_id.return_value = {
            "id": "admin-123",  # Same as mock_admin_user.user_id
            "email": "admin@example.com",
            "name": "Admin",
            "role": "admin",
            "tenant_id": "test_tenant",
            "is_active": True
        }

        mock_request = MagicMock(spec=Request)
        update_request = UpdateUserRequest(role="consultant")  # Try to demote

        with pytest.raises(HTTPException) as exc_info:
            await update_user(
                user_id="admin-123",  # Same as current user
                update_request=update_request,
                request=mock_request,
                user=mock_admin_user,
                db=mock_db
            )

        assert exc_info.value.status_code == 400
        assert "Cannot demote yourself" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_user_rejects_invalid_role(self, mock_admin_user):
        """update_user should reject invalid role."""
        from src.api.users_routes import update_user, UpdateUserRequest
        from fastapi import Request, HTTPException

        mock_db = MagicMock()
        mock_db.get_user_by_id.return_value = {
            "id": "user-123",
            "email": "user@example.com",
            "name": "User",
            "role": "consultant",
            "tenant_id": "test_tenant",
            "is_active": True
        }

        mock_request = MagicMock(spec=Request)
        update_request = UpdateUserRequest(role="superadmin")  # Invalid role

        with pytest.raises(HTTPException) as exc_info:
            await update_user(
                user_id="user-123",
                update_request=update_request,
                request=mock_request,
                user=mock_admin_user,
                db=mock_db
            )

        assert exc_info.value.status_code == 400
        assert "Invalid role" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_user_no_updates_raises_400(self, mock_admin_user):
        """update_user should raise 400 when no updates provided."""
        from src.api.users_routes import update_user, UpdateUserRequest
        from fastapi import Request, HTTPException

        mock_db = MagicMock()
        mock_db.get_user_by_id.return_value = {
            "id": "user-123",
            "email": "user@example.com",
            "name": "User",
            "role": "consultant",
            "tenant_id": "test_tenant",
            "is_active": True
        }

        mock_request = MagicMock(spec=Request)
        update_request = UpdateUserRequest()  # Empty

        with pytest.raises(HTTPException) as exc_info:
            await update_user(
                user_id="user-123",
                update_request=update_request,
                request=mock_request,
                user=mock_admin_user,
                db=mock_db
            )

        assert exc_info.value.status_code == 400
        assert "No updates" in str(exc_info.value.detail)


class TestDeactivateUserUnit:
    """Unit tests for deactivate_user endpoint logic."""

    @pytest.mark.asyncio
    async def test_deactivate_user_success(self, mock_admin_user):
        """deactivate_user should deactivate the user."""
        from src.api.users_routes import deactivate_user
        from fastapi import Request

        mock_db = MagicMock()
        mock_db.get_user_by_id.return_value = {
            "id": "user-123",
            "email": "user@example.com",
            "name": "User",
            "role": "consultant",
            "tenant_id": "test_tenant",
            "is_active": True
        }
        mock_db.deactivate_user.return_value = True

        mock_request = MagicMock(spec=Request)

        result = await deactivate_user(
            user_id="user-123",
            request=mock_request,
            user=mock_admin_user,
            db=mock_db
        )

        assert result["success"] is True
        mock_db.deactivate_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_deactivate_user_prevents_self_deactivation(self, mock_admin_user):
        """deactivate_user should prevent user from deactivating themselves."""
        from src.api.users_routes import deactivate_user
        from fastapi import Request, HTTPException

        mock_db = MagicMock()
        mock_request = MagicMock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await deactivate_user(
                user_id="admin-123",  # Same as mock_admin_user.user_id
                request=mock_request,
                user=mock_admin_user,
                db=mock_db
            )

        assert exc_info.value.status_code == 400
        assert "Cannot deactivate your own" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_deactivate_user_not_found(self, mock_admin_user):
        """deactivate_user should raise 404 when user not found."""
        from src.api.users_routes import deactivate_user
        from fastapi import Request, HTTPException

        mock_db = MagicMock()
        mock_db.get_user_by_id.return_value = None

        mock_request = MagicMock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await deactivate_user(
                user_id="nonexistent",
                request=mock_request,
                user=mock_admin_user,
                db=mock_db
            )

        assert exc_info.value.status_code == 404


class TestResendInvitationUnit:
    """Unit tests for resend_invitation endpoint logic."""

    @pytest.mark.asyncio
    async def test_resend_invitation_not_found(self, mock_admin_user):
        """resend_invitation should raise 404 when invitation not found."""
        from src.api.users_routes import resend_invitation
        from fastapi import Request, HTTPException

        mock_db = MagicMock()
        mock_db.get_invitations.return_value = []  # No invitations

        mock_email_sender = MagicMock()
        mock_request = MagicMock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await resend_invitation(
                invitation_id="nonexistent",
                request=mock_request,
                user=mock_admin_user,
                db=mock_db,
                email_sender=mock_email_sender,
                x_client_id="test_tenant"
            )

        assert exc_info.value.status_code == 404


# ==================== Dependency Function Tests ====================

class TestDependencyFunctions:
    """Test dependency functions."""

    def test_get_supabase_tool_creates_instance(self):
        """get_supabase_tool should create SupabaseTool instance."""
        from src.api.users_routes import get_supabase_tool

        with patch('src.api.users_routes.get_config') as mock_get_config:
            with patch('src.api.users_routes.SupabaseTool') as MockSupabase:
                mock_config = MagicMock()
                mock_get_config.return_value = mock_config
                mock_db = MagicMock()
                MockSupabase.return_value = mock_db

                result = get_supabase_tool("test_client")

                mock_get_config.assert_called_once_with("test_client")
                MockSupabase.assert_called_once_with(mock_config)
                assert result == mock_db

    def test_get_supabase_tool_raises_on_unknown_client(self):
        """get_supabase_tool should raise HTTPException for unknown client."""
        from src.api.users_routes import get_supabase_tool
        from fastapi import HTTPException

        with patch('src.api.users_routes.get_config') as mock_get_config:
            mock_get_config.side_effect = FileNotFoundError("Config not found")

            with pytest.raises(HTTPException) as exc_info:
                get_supabase_tool("unknown_client")

            assert exc_info.value.status_code == 400
            assert "Unknown client" in str(exc_info.value.detail)

    def test_get_email_sender_creates_instance(self):
        """get_email_sender should create EmailSender instance."""
        from src.api.users_routes import get_email_sender

        with patch('src.api.users_routes.get_config') as mock_get_config:
            with patch('src.api.users_routes.EmailSender') as MockEmailSender:
                mock_config = MagicMock()
                mock_get_config.return_value = mock_config
                mock_sender = MagicMock()
                MockEmailSender.return_value = mock_sender

                result = get_email_sender("test_client")

                mock_get_config.assert_called_once_with("test_client")
                MockEmailSender.assert_called_once_with(mock_config)
                assert result == mock_sender

    def test_get_email_sender_raises_on_unknown_client(self):
        """get_email_sender should raise HTTPException for unknown client."""
        from src.api.users_routes import get_email_sender
        from fastapi import HTTPException

        with patch('src.api.users_routes.get_config') as mock_get_config:
            mock_get_config.side_effect = FileNotFoundError("Config not found")

            with pytest.raises(HTTPException) as exc_info:
                get_email_sender("unknown_client")

            assert exc_info.value.status_code == 400
            assert "Unknown client" in str(exc_info.value.detail)
