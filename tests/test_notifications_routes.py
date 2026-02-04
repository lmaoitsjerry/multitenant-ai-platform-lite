"""
Notifications Routes Unit Tests

Comprehensive tests for notification API endpoints:
- GET /api/v1/notifications
- GET /api/v1/notifications/unread-count
- PATCH /api/v1/notifications/{id}/read
- POST /api/v1/notifications/mark-all-read
- GET /api/v1/notifications/preferences
- PUT /api/v1/notifications/preferences

Uses FastAPI TestClient with mocked dependencies.
These tests verify:
1. Authorization required (401 for missing/invalid token)
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
    config.primary_color = "#6366F1"
    return config


@pytest.fixture
def test_client():
    """Create a basic TestClient."""
    from main import app
    return TestClient(app)


@pytest.fixture
def mock_user_context():
    """Create a mock UserContext."""
    user = MagicMock()
    user.user_id = "user-123"
    user.tenant_id = "test_tenant"
    user.email = "test@example.com"
    user.name = "Test User"
    user.role = "admin"
    return user


# ==================== Authorization Tests ====================

class TestNotificationsAuth:
    """Test authorization for notification endpoints."""

    def test_list_notifications_requires_auth(self, test_client):
        """GET /notifications should require authorization."""
        response = test_client.get(
            "/api/v1/notifications",
            headers={"X-Client-ID": "example"}
        )
        assert response.status_code == 401

    def test_unread_count_requires_auth(self, test_client):
        """GET /notifications/unread-count should require authorization."""
        response = test_client.get(
            "/api/v1/notifications/unread-count",
            headers={"X-Client-ID": "example"}
        )
        assert response.status_code == 401

    def test_mark_read_requires_auth(self, test_client):
        """PATCH /notifications/{id}/read should require authorization."""
        response = test_client.patch(
            "/api/v1/notifications/notif-123/read",
            headers={"X-Client-ID": "example"}
        )
        assert response.status_code == 401

    def test_mark_all_read_requires_auth(self, test_client):
        """POST /notifications/mark-all-read should require authorization."""
        response = test_client.post(
            "/api/v1/notifications/mark-all-read",
            headers={"X-Client-ID": "example"}
        )
        assert response.status_code == 401

    def test_get_preferences_requires_auth(self, test_client):
        """GET /notifications/preferences should require authorization."""
        response = test_client.get(
            "/api/v1/notifications/preferences",
            headers={"X-Client-ID": "example"}
        )
        assert response.status_code == 401

    def test_update_preferences_requires_auth(self, test_client):
        """PUT /notifications/preferences should require authorization."""
        response = test_client.put(
            "/api/v1/notifications/preferences",
            headers={"X-Client-ID": "example"},
            json={"email_quote_request": True}
        )
        assert response.status_code == 401


# ==================== Notification List Tests ====================

class TestListNotifications:
    """Test GET /api/v1/notifications endpoint."""

    def test_list_notifications_invalid_client(self, test_client):
        """GET /notifications should return 400 for invalid client."""
        response = test_client.get(
            "/api/v1/notifications",
            headers={
                "X-Client-ID": "nonexistent_client_xyz",
                "Authorization": "Bearer test-token"
            }
        )
        # 400 for invalid client or 401 for bad token
        assert response.status_code in [400, 401]

    def test_list_notifications_with_example_client(self, test_client):
        """GET /notifications should accept valid client ID."""
        response = test_client.get(
            "/api/v1/notifications",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test-token"
            }
        )
        # 401 for invalid token is expected with valid client
        assert response.status_code == 401

    def test_list_notifications_accepts_query_params(self, test_client):
        """GET /notifications should accept limit, offset, unread_only params."""
        response = test_client.get(
            "/api/v1/notifications?limit=10&offset=5&unread_only=true",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test-token"
            }
        )
        # Request format is valid, just auth fails
        assert response.status_code == 401


# ==================== Unread Count Tests ====================

class TestUnreadCount:
    """Test GET /api/v1/notifications/unread-count endpoint."""

    def test_unread_count_endpoint_exists(self, test_client):
        """GET /notifications/unread-count endpoint should exist."""
        response = test_client.get(
            "/api/v1/notifications/unread-count",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test-token"
            }
        )
        # Endpoint exists, auth fails
        assert response.status_code == 401

    def test_unread_count_accepts_client_header(self, test_client):
        """GET /notifications/unread-count should read X-Client-ID header."""
        response = test_client.get(
            "/api/v1/notifications/unread-count",
            headers={"X-Client-ID": "example"}
        )
        # Missing auth
        assert response.status_code == 401


# ==================== Mark Read Tests ====================

class TestMarkRead:
    """Test PATCH /api/v1/notifications/{id}/read endpoint."""

    def test_mark_notification_read_endpoint_exists(self, test_client):
        """PATCH /notifications/{id}/read endpoint should exist."""
        response = test_client.patch(
            "/api/v1/notifications/notif-123/read",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test-token"
            }
        )
        # Endpoint exists, auth fails
        assert response.status_code == 401

    def test_mark_notification_read_accepts_notification_id(self, test_client):
        """PATCH /notifications/{id}/read should accept notification ID path param."""
        response = test_client.patch(
            "/api/v1/notifications/some-uuid-here/read",
            headers={"X-Client-ID": "example"}
        )
        assert response.status_code == 401


# ==================== Mark All Read Tests ====================

class TestMarkAllRead:
    """Test POST /api/v1/notifications/mark-all-read endpoint."""

    def test_mark_all_notifications_read_endpoint_exists(self, test_client):
        """POST /notifications/mark-all-read endpoint should exist."""
        response = test_client.post(
            "/api/v1/notifications/mark-all-read",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test-token"
            }
        )
        # Endpoint exists, auth fails
        assert response.status_code == 401

    def test_mark_all_notifications_no_body_required(self, test_client):
        """POST /notifications/mark-all-read should not require body."""
        response = test_client.post(
            "/api/v1/notifications/mark-all-read",
            headers={"X-Client-ID": "example"}
        )
        # Auth fails but format is valid
        assert response.status_code == 401


# ==================== Preferences Tests ====================

class TestNotificationPreferences:
    """Test notification preferences endpoints."""

    def test_get_preferences_endpoint_exists(self, test_client):
        """GET /notifications/preferences endpoint should exist."""
        response = test_client.get(
            "/api/v1/notifications/preferences",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test-token"
            }
        )
        # Endpoint exists, auth fails
        assert response.status_code == 401

    def test_update_preferences_endpoint_exists(self, test_client):
        """PUT /notifications/preferences endpoint should exist."""
        response = test_client.put(
            "/api/v1/notifications/preferences",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test-token"
            },
            json={"email_quote_request": False}
        )
        # Endpoint exists, auth fails
        assert response.status_code == 401

    def test_update_preferences_accepts_all_fields(self, test_client):
        """PUT /notifications/preferences should accept all preference fields."""
        response = test_client.put(
            "/api/v1/notifications/preferences",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test-token"
            },
            json={
                "email_quote_request": True,
                "email_email_received": True,
                "email_invoice_paid": True,
                "email_invoice_overdue": False,
                "email_booking_confirmed": True,
                "email_client_added": False,
                "email_team_invite": True,
                "email_system": True,
                "email_mention": True,
                "email_digest_enabled": False,
                "email_digest_frequency": "daily"
            }
        )
        # Auth fails but request format is valid
        assert response.status_code == 401


# ==================== Notification Service Tests ====================

class TestNotificationService:
    """Test NotificationService class."""

    def test_notification_service_init(self, mock_config):
        """NotificationService should initialize with config."""
        from src.api.notifications_routes import NotificationService

        with patch("src.api.notifications_routes.SupabaseTool"):
            service = NotificationService(mock_config)
            assert service.config == mock_config

    def test_notification_type_to_preference_mapping(self, mock_config):
        """NotificationService should have type to preference mapping."""
        from src.api.notifications_routes import NotificationService

        with patch("src.api.notifications_routes.SupabaseTool"):
            service = NotificationService(mock_config)
            assert "quote_request" in service.TYPE_TO_PREFERENCE
            assert "invoice_paid" in service.TYPE_TO_PREFERENCE
            assert "email_received" in service.TYPE_TO_PREFERENCE


# ==================== Time Formatting Tests ====================

class TestTimeFormatting:
    """Test time formatting helper."""

    def test_format_time_ago_function_exists(self):
        """_format_time_ago helper should exist."""
        from src.api.notifications_routes import _format_time_ago

        result = _format_time_ago("2026-01-21T12:00:00Z")
        assert isinstance(result, str)

    def test_format_time_ago_handles_invalid(self):
        """_format_time_ago should handle invalid timestamps."""
        from src.api.notifications_routes import _format_time_ago

        result = _format_time_ago("invalid-timestamp")
        assert result == "Recently"

    def test_format_time_ago_just_now(self):
        """_format_time_ago should return 'Just now' for recent times."""
        from src.api.notifications_routes import _format_time_ago
        from datetime import datetime, timezone

        # Current time
        now = datetime.now(timezone.utc).isoformat()
        result = _format_time_ago(now)
        assert result in ["Just now", "Recently"]

    def test_format_time_ago_minutes(self):
        """_format_time_ago should format minutes correctly."""
        from src.api.notifications_routes import _format_time_ago
        from datetime import datetime, timezone, timedelta

        # 5 minutes ago
        five_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        result = _format_time_ago(five_min_ago)
        assert "m ago" in result or result == "Just now"

    def test_format_time_ago_hours(self):
        """_format_time_ago should format hours correctly."""
        from src.api.notifications_routes import _format_time_ago
        from datetime import datetime, timezone, timedelta

        # 3 hours ago
        three_hrs_ago = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
        result = _format_time_ago(three_hrs_ago)
        assert "h ago" in result

    def test_format_time_ago_days(self):
        """_format_time_ago should format days correctly."""
        from src.api.notifications_routes import _format_time_ago
        from datetime import datetime, timezone, timedelta

        # 3 days ago
        three_days_ago = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        result = _format_time_ago(three_days_ago)
        assert "d ago" in result

    def test_format_time_ago_old_date(self):
        """_format_time_ago should format old dates with month/day."""
        from src.api.notifications_routes import _format_time_ago
        from datetime import datetime, timezone, timedelta

        # 30 days ago
        old_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        result = _format_time_ago(old_date)
        # Should be a formatted date like "Jan 05"
        assert "ago" not in result or result == "Recently"

    def test_format_time_ago_handles_z_suffix(self):
        """_format_time_ago should handle timestamps with Z suffix."""
        from src.api.notifications_routes import _format_time_ago

        result = _format_time_ago("2025-01-01T12:00:00Z")
        assert isinstance(result, str)


# ==================== Pydantic Model Tests ====================

class TestPydanticModels:
    """Test Pydantic models for notifications."""

    def test_notification_response_model(self):
        """NotificationResponse model should validate correctly."""
        from src.api.notifications_routes import NotificationResponse

        notif = NotificationResponse(
            id="notif-123",
            type="quote_request",
            title="New Quote Request",
            message="Customer requested a quote",
            entity_type="quote",
            entity_id="quote-456",
            read=False,
            created_at="2026-01-21T12:00:00Z"
        )
        assert notif.id == "notif-123"
        assert notif.type == "quote_request"
        assert notif.read is False

    def test_notification_response_optional_fields(self):
        """NotificationResponse should allow optional entity fields."""
        from src.api.notifications_routes import NotificationResponse

        notif = NotificationResponse(
            id="notif-123",
            type="system",
            title="System Message",
            message="System notification",
            read=True,
            created_at="2026-01-21T12:00:00Z"
        )
        assert notif.entity_type is None
        assert notif.entity_id is None

    def test_notification_preferences_update_model(self):
        """NotificationPreferencesUpdate model should validate correctly."""
        from src.api.notifications_routes import NotificationPreferencesUpdate

        prefs = NotificationPreferencesUpdate(
            email_quote_request=True,
            email_invoice_paid=False,
            email_digest_frequency="weekly"
        )
        assert prefs.email_quote_request is True
        assert prefs.email_invoice_paid is False
        assert prefs.email_digest_frequency == "weekly"
        # Unset fields should be None
        assert prefs.email_email_received is None

    def test_notification_preferences_all_optional(self):
        """NotificationPreferencesUpdate should allow empty update."""
        from src.api.notifications_routes import NotificationPreferencesUpdate

        prefs = NotificationPreferencesUpdate()
        assert prefs.email_quote_request is None
        assert prefs.email_system is None

    def test_mark_read_request_model(self):
        """MarkReadRequest model should require notification_ids list."""
        from src.api.notifications_routes import MarkReadRequest

        req = MarkReadRequest(notification_ids=["notif-1", "notif-2", "notif-3"])
        assert len(req.notification_ids) == 3
        assert "notif-1" in req.notification_ids


# ==================== Unit Tests for Endpoint Handlers ====================

class TestListNotificationsUnit:
    """Unit tests for list_notifications endpoint handler."""

    @pytest.fixture
    def mock_supabase(self):
        """Create mock supabase client."""
        mock = MagicMock()
        # Setup query chain for notifications
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.or_.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.execute.return_value = MagicMock(
            data=[
                {
                    'id': 'notif-1',
                    'type': 'quote_request',
                    'title': 'New Quote',
                    'message': 'Customer requested quote',
                    'entity_type': 'quote',
                    'entity_id': 'quote-123',
                    'read': False,
                    'created_at': '2026-01-21T12:00:00Z'
                }
            ],
            count=1
        )
        mock.client.table.return_value = mock_query
        return mock

    @pytest.mark.asyncio
    async def test_list_notifications_success(self, mock_config, mock_supabase):
        """list_notifications should return formatted notifications."""
        from src.api.notifications_routes import list_notifications

        with patch("src.api.notifications_routes.SupabaseTool", return_value=mock_supabase):
            result = await list_notifications(
                config=mock_config,
                user_id="user-123",
                limit=20,
                offset=0,
                unread_only=False
            )

        assert result['success'] is True
        assert 'data' in result
        assert len(result['data']) == 1
        assert result['data'][0]['id'] == 'notif-1'
        assert 'time_ago' in result['data'][0]

    @pytest.mark.asyncio
    async def test_list_notifications_with_pagination(self, mock_config, mock_supabase):
        """list_notifications should respect pagination params."""
        from src.api.notifications_routes import list_notifications

        with patch("src.api.notifications_routes.SupabaseTool", return_value=mock_supabase):
            result = await list_notifications(
                config=mock_config,
                user_id="user-123",
                limit=10,
                offset=5,
                unread_only=False
            )

        assert result['limit'] == 10
        assert result['offset'] == 5

    @pytest.mark.asyncio
    async def test_list_notifications_unread_only(self, mock_config, mock_supabase):
        """list_notifications should filter unread only when requested."""
        from src.api.notifications_routes import list_notifications

        with patch("src.api.notifications_routes.SupabaseTool", return_value=mock_supabase):
            result = await list_notifications(
                config=mock_config,
                user_id="user-123",
                limit=20,
                offset=0,
                unread_only=True
            )

        assert result['success'] is True

    @pytest.mark.asyncio
    async def test_list_notifications_error_handling(self, mock_config):
        """list_notifications should handle errors gracefully."""
        from src.api.notifications_routes import list_notifications
        from fastapi import HTTPException

        mock_supabase = MagicMock()
        mock_supabase.client.table.side_effect = Exception("Database error")

        with patch("src.api.notifications_routes.SupabaseTool", return_value=mock_supabase):
            with pytest.raises(HTTPException) as exc_info:
                await list_notifications(
                    config=mock_config,
                    user_id="user-123",
                    limit=20,
                    offset=0,
                    unread_only=False
                )
            assert exc_info.value.status_code == 500


class TestUnreadCountUnit:
    """Unit tests for get_unread_count endpoint handler."""

    @pytest.mark.asyncio
    async def test_get_unread_count_success(self, mock_config):
        """get_unread_count should return count of unread notifications."""
        from src.api.notifications_routes import get_unread_count

        mock_supabase = MagicMock()
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.or_.return_value = mock_query
        mock_result = MagicMock()
        mock_result.count = 5
        mock_query.execute.return_value = mock_result
        mock_supabase.client.table.return_value = mock_query

        with patch("src.api.notifications_routes.SupabaseTool", return_value=mock_supabase):
            result = await get_unread_count(
                config=mock_config,
                user_id="user-123"
            )

        assert result['success'] is True
        assert result['unread_count'] == 5

    @pytest.mark.asyncio
    async def test_get_unread_count_zero(self, mock_config):
        """get_unread_count should return 0 when no unread notifications."""
        from src.api.notifications_routes import get_unread_count

        mock_supabase = MagicMock()
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.or_.return_value = mock_query
        mock_result = MagicMock()
        mock_result.count = 0
        mock_query.execute.return_value = mock_result
        mock_supabase.client.table.return_value = mock_query

        with patch("src.api.notifications_routes.SupabaseTool", return_value=mock_supabase):
            result = await get_unread_count(
                config=mock_config,
                user_id="user-123"
            )

        assert result['unread_count'] == 0

    @pytest.mark.asyncio
    async def test_get_unread_count_error_returns_zero(self, mock_config):
        """get_unread_count should return 0 on error."""
        from src.api.notifications_routes import get_unread_count

        mock_supabase = MagicMock()
        mock_supabase.client.table.side_effect = Exception("Database error")

        with patch("src.api.notifications_routes.SupabaseTool", return_value=mock_supabase):
            result = await get_unread_count(
                config=mock_config,
                user_id="user-123"
            )

        # Error handling returns 0 instead of raising
        assert result['success'] is True
        assert result['unread_count'] == 0


class TestMarkNotificationReadUnit:
    """Unit tests for mark_notification_read endpoint handler."""

    @pytest.mark.asyncio
    async def test_mark_notification_read_success(self, mock_config):
        """mark_notification_read should update notification as read."""
        from src.api.notifications_routes import mark_notification_read

        mock_supabase = MagicMock()
        mock_query = MagicMock()
        mock_query.update.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.or_.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=[{'id': 'notif-123'}])
        mock_supabase.client.table.return_value = mock_query

        with patch("src.api.notifications_routes.SupabaseTool", return_value=mock_supabase):
            result = await mark_notification_read(
                notification_id="notif-123",
                config=mock_config,
                user_id="user-123"
            )

        assert result['success'] is True
        assert result['message'] == 'Notification marked as read'

    @pytest.mark.asyncio
    async def test_mark_notification_read_error(self, mock_config):
        """mark_notification_read should handle errors."""
        from src.api.notifications_routes import mark_notification_read
        from fastapi import HTTPException

        mock_supabase = MagicMock()
        mock_supabase.client.table.side_effect = Exception("Database error")

        with patch("src.api.notifications_routes.SupabaseTool", return_value=mock_supabase):
            with pytest.raises(HTTPException) as exc_info:
                await mark_notification_read(
                    notification_id="notif-123",
                    config=mock_config,
                    user_id="user-123"
                )
            assert exc_info.value.status_code == 500


class TestMarkAllReadUnit:
    """Unit tests for mark_all_read endpoint handler."""

    @pytest.mark.asyncio
    async def test_mark_all_read_success(self, mock_config):
        """mark_all_read should update all notifications as read."""
        from src.api.notifications_routes import mark_all_read

        mock_supabase = MagicMock()
        mock_query = MagicMock()
        mock_query.update.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.is_.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=[])
        mock_supabase.client.table.return_value = mock_query

        with patch("src.api.notifications_routes.SupabaseTool", return_value=mock_supabase):
            result = await mark_all_read(
                config=mock_config,
                user_id="user-123"
            )

        assert result['success'] is True
        assert result['message'] == 'All notifications marked as read'

    @pytest.mark.asyncio
    async def test_mark_all_read_error(self, mock_config):
        """mark_all_read should handle errors."""
        from src.api.notifications_routes import mark_all_read
        from fastapi import HTTPException

        mock_supabase = MagicMock()
        mock_supabase.client.table.side_effect = Exception("Database error")

        with patch("src.api.notifications_routes.SupabaseTool", return_value=mock_supabase):
            with pytest.raises(HTTPException) as exc_info:
                await mark_all_read(
                    config=mock_config,
                    user_id="user-123"
                )
            assert exc_info.value.status_code == 500


class TestNotificationPreferencesUnit:
    """Unit tests for notification preferences endpoints."""

    @pytest.mark.asyncio
    async def test_get_preferences_success(self, mock_config):
        """get_notification_preferences should return user preferences."""
        from src.api.notifications_routes import get_notification_preferences

        mock_supabase = MagicMock()
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.single.return_value = mock_query
        mock_query.execute.return_value = MagicMock(
            data={
                'email_quote_request': True,
                'email_invoice_paid': True,
                'email_system': False
            }
        )
        mock_supabase.client.table.return_value = mock_query

        with patch("src.api.notifications_routes.SupabaseTool", return_value=mock_supabase):
            result = await get_notification_preferences(
                config=mock_config,
                user_id="user-123"
            )

        assert result['success'] is True
        assert result['data']['email_quote_request'] is True

    @pytest.mark.asyncio
    async def test_get_preferences_returns_defaults(self, mock_config):
        """get_notification_preferences should return defaults if none exist."""
        from src.api.notifications_routes import get_notification_preferences

        mock_supabase = MagicMock()
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.single.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=None)
        mock_supabase.client.table.return_value = mock_query

        with patch("src.api.notifications_routes.SupabaseTool", return_value=mock_supabase):
            result = await get_notification_preferences(
                config=mock_config,
                user_id="user-123"
            )

        assert result['success'] is True
        # Should have default preferences
        assert result['data']['email_quote_request'] is True
        assert result['data']['email_digest_enabled'] is False

    @pytest.mark.asyncio
    async def test_update_preferences_success(self, mock_config):
        """update_notification_preferences should update preferences."""
        from src.api.notifications_routes import (
            update_notification_preferences,
            NotificationPreferencesUpdate
        )

        mock_supabase = MagicMock()
        mock_query = MagicMock()
        mock_query.upsert.return_value = mock_query
        mock_query.execute.return_value = MagicMock(
            data=[{'email_quote_request': False}]
        )
        mock_supabase.client.table.return_value = mock_query

        prefs = NotificationPreferencesUpdate(email_quote_request=False)

        with patch("src.api.notifications_routes.SupabaseTool", return_value=mock_supabase):
            result = await update_notification_preferences(
                preferences=prefs,
                config=mock_config,
                user_id="user-123"
            )

        assert result['success'] is True
        assert result['message'] == 'Preferences updated'

    @pytest.mark.asyncio
    async def test_update_preferences_empty_raises_error(self, mock_config):
        """update_notification_preferences should reject empty updates."""
        from src.api.notifications_routes import (
            update_notification_preferences,
            NotificationPreferencesUpdate
        )
        from fastapi import HTTPException

        prefs = NotificationPreferencesUpdate()  # All None

        with patch("src.api.notifications_routes.SupabaseTool"):
            with pytest.raises(HTTPException) as exc_info:
                await update_notification_preferences(
                    preferences=prefs,
                    config=mock_config,
                    user_id="user-123"
                )
            assert exc_info.value.status_code == 400
            assert "No preferences to update" in str(exc_info.value.detail)


# ==================== NotificationService Unit Tests ====================

class TestNotificationServiceUnit:
    """Unit tests for NotificationService class."""

    @pytest.fixture
    def service(self, mock_config):
        """Create NotificationService with mocked dependencies."""
        with patch("src.api.notifications_routes.SupabaseTool") as mock_supabase:
            from src.api.notifications_routes import NotificationService
            service = NotificationService(mock_config)
            service.supabase = mock_supabase.return_value
            return service

    def test_create_notification_success(self, service, mock_config):
        """create_notification should insert notification and return ID."""
        mock_query = MagicMock()
        mock_query.insert.return_value = mock_query
        mock_query.execute.return_value = MagicMock(
            data=[{'id': 'notif-new-123'}]
        )
        service.supabase.client.table.return_value = mock_query

        with patch.object(service, '_send_notification_email'):
            result = service.create_notification(
                user_id="user-123",
                type="quote_request",
                title="New Quote",
                message="Customer requested quote",
                entity_type="quote",
                entity_id="quote-456"
            )

        assert result == 'notif-new-123'

    def test_create_notification_without_email(self, service, mock_config):
        """create_notification should skip email when send_email=False."""
        mock_query = MagicMock()
        mock_query.insert.return_value = mock_query
        mock_query.execute.return_value = MagicMock(
            data=[{'id': 'notif-new-123'}]
        )
        service.supabase.client.table.return_value = mock_query

        with patch.object(service, '_send_notification_email') as mock_email:
            service.create_notification(
                user_id="user-123",
                type="quote_request",
                title="New Quote",
                message="Message",
                send_email=False
            )

        mock_email.assert_not_called()

    def test_create_notification_handles_error(self, service, mock_config):
        """create_notification should return None on error."""
        service.supabase.client.table.side_effect = Exception("DB error")

        result = service.create_notification(
            user_id="user-123",
            type="quote_request",
            title="New Quote",
            message="Message"
        )

        assert result is None

    def test_notify_all_users(self, service, mock_config):
        """notify_all_users should notify all active tenant users."""
        # Mock getting users
        users_query = MagicMock()
        users_query.select.return_value = users_query
        users_query.eq.return_value = users_query
        users_query.execute.return_value = MagicMock(
            data=[
                {'id': 'user-1'},
                {'id': 'user-2'},
                {'id': 'user-3'}
            ]
        )

        # Mock creating notifications
        notif_query = MagicMock()
        notif_query.insert.return_value = notif_query
        notif_query.execute.return_value = MagicMock(
            data=[{'id': 'notif-123'}]
        )

        def table_router(table_name):
            if table_name == 'organization_users':
                return users_query
            return notif_query

        service.supabase.client.table.side_effect = table_router

        with patch.object(service, '_send_notification_email'):
            count = service.notify_all_users(
                type="system",
                title="System Message",
                message="Important announcement"
            )

        assert count == 3

    def test_notify_quote_request(self, service, mock_config):
        """notify_quote_request should create quote request notification."""
        with patch.object(service, 'notify_all_users') as mock_notify:
            service.notify_quote_request(
                customer_name="John Doe",
                destination="Paris",
                quote_id="quote-123"
            )

        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args[1]
        assert call_kwargs['type'] == 'quote_request'
        assert 'John Doe' in call_kwargs['message']
        assert 'Paris' in call_kwargs['message']

    def test_notify_quote_sent(self, service, mock_config):
        """notify_quote_sent should create quote sent notification."""
        with patch.object(service, 'notify_all_users') as mock_notify:
            service.notify_quote_sent(
                customer_name="Jane Smith",
                customer_email="jane@example.com",
                destination="Tokyo",
                quote_id="quote-456"
            )

        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args[1]
        assert call_kwargs['type'] == 'system'
        assert 'Jane Smith' in call_kwargs['message']

    def test_notify_email_received(self, service, mock_config):
        """notify_email_received should create email notification."""
        with patch.object(service, 'notify_all_users') as mock_notify:
            service.notify_email_received(
                sender_email="customer@example.com",
                subject="Inquiry about trip"
            )

        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args[1]
        assert call_kwargs['type'] == 'email_received'

    def test_notify_invoice_paid(self, service, mock_config):
        """notify_invoice_paid should create payment notification."""
        with patch.object(service, 'notify_all_users') as mock_notify:
            service.notify_invoice_paid(
                customer_name="Bob Wilson",
                invoice_id="inv-789",
                amount=1500.50,
                currency="USD"
            )

        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args[1]
        assert call_kwargs['type'] == 'invoice_paid'
        assert 'Bob Wilson' in call_kwargs['message']
        assert '1,500.50' in call_kwargs['message']

    def test_notify_client_added(self, service, mock_config):
        """notify_client_added should create client notification."""
        with patch.object(service, 'notify_all_users') as mock_notify:
            service.notify_client_added(
                client_name="New Client Corp",
                client_id="client-123",
                added_by="Admin User"
            )

        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args[1]
        assert call_kwargs['type'] == 'client_added'

    def test_get_user_preferences_returns_defaults(self, service, mock_config):
        """_get_user_preferences should return defaults on error."""
        service.supabase.client.table.side_effect = Exception("DB error")

        result = service._get_user_preferences("user-123")

        assert result['email_quote_request'] is True
        assert result['email_client_added'] is False

    def test_get_user_email_success(self, service, mock_config):
        """_get_user_email should return user email."""
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.single.return_value = mock_query
        mock_query.execute.return_value = MagicMock(
            data={'email': 'user@example.com'}
        )
        service.supabase.client.table.return_value = mock_query

        result = service._get_user_email("user-123")

        assert result == 'user@example.com'

    def test_get_user_email_returns_none_on_error(self, service, mock_config):
        """_get_user_email should return None on error."""
        service.supabase.client.table.side_effect = Exception("DB error")

        result = service._get_user_email("user-123")

        assert result is None

    def test_should_send_email_unknown_type(self, service, mock_config):
        """_should_send_email should return False for unknown type."""
        result = service._should_send_email("user-123", "unknown_type")
        assert result is False

    def test_should_send_email_checks_preferences(self, service, mock_config):
        """_should_send_email should check user preferences."""
        with patch.object(service, '_get_user_preferences') as mock_prefs:
            mock_prefs.return_value = {'email_quote_request': True}

            result = service._should_send_email("user-123", "quote_request")

        assert result is True

    def test_email_sender_lazy_load(self, mock_config):
        """email_sender property should lazy-load EmailSender."""
        with patch("src.api.notifications_routes.SupabaseTool"):
            from src.api.notifications_routes import NotificationService
            service = NotificationService(mock_config)

            with patch("src.utils.email_sender.EmailSender") as mock_email_sender:
                mock_email_sender.return_value = MagicMock()
                sender = service.email_sender

                assert sender is not None

    def test_email_sender_handles_import_error(self, mock_config):
        """email_sender should handle import errors gracefully."""
        with patch("src.api.notifications_routes.SupabaseTool"):
            from src.api.notifications_routes import NotificationService
            service = NotificationService(mock_config)

            with patch.object(service, '_email_sender', None):
                with patch("src.utils.email_sender.EmailSender", side_effect=Exception("Import error")):
                    sender = service.email_sender

                    # Should return None on error
                    assert sender is None


# ==================== get_current_user_id Tests ====================

class TestGetCurrentUserId:
    """Unit tests for get_current_user_id helper function."""

    def test_get_current_user_id_no_auth_header(self, mock_config):
        """get_current_user_id should raise 401 without auth header."""
        from src.api.notifications_routes import get_current_user_id
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            get_current_user_id(authorization=None, config=mock_config)

        assert exc_info.value.status_code == 401
        assert "Authorization required" in str(exc_info.value.detail)

    def test_get_current_user_id_invalid_format(self, mock_config):
        """get_current_user_id should raise 401 for invalid format."""
        from src.api.notifications_routes import get_current_user_id
        from fastapi import HTTPException

        with patch("src.services.auth_service.get_cached_auth_client") as mock_client:
            mock_client.return_value = MagicMock()
            with pytest.raises(HTTPException) as exc_info:
                get_current_user_id(authorization="InvalidToken", config=mock_config)

            assert exc_info.value.status_code == 401
            assert "Invalid authorization format" in str(exc_info.value.detail)

    def test_get_current_user_id_invalid_token(self, mock_config):
        """get_current_user_id should raise 401 for invalid token."""
        from src.api.notifications_routes import get_current_user_id
        from fastapi import HTTPException

        with patch("src.services.auth_service.get_cached_auth_client") as mock_client:
            mock_client.return_value = MagicMock()
            with patch("src.services.auth_service.AuthService.verify_jwt") as mock_verify:
                mock_verify.return_value = (False, None)

                with pytest.raises(HTTPException) as exc_info:
                    get_current_user_id(
                        authorization="Bearer invalid-token",
                        config=mock_config
                    )

                assert exc_info.value.status_code == 401
                assert "Invalid token" in str(exc_info.value.detail)

    def test_get_current_user_id_user_not_found(self, mock_config):
        """get_current_user_id should raise 401 when user not found."""
        from src.api.notifications_routes import get_current_user_id
        from fastapi import HTTPException

        with patch("src.services.auth_service.get_cached_auth_client") as mock_client:
            mock_client.return_value = MagicMock()
            with patch("src.services.auth_service.AuthService.verify_jwt") as mock_verify:
                mock_verify.return_value = (True, {'sub': 'auth-user-id'})

                with patch("src.api.notifications_routes.SupabaseTool") as mock_supabase:
                    mock_query = MagicMock()
                    mock_query.select.return_value = mock_query
                    mock_query.eq.return_value = mock_query
                    mock_query.single.return_value = mock_query
                    mock_query.execute.return_value = MagicMock(data=None)
                    mock_supabase.return_value.client.table.return_value = mock_query

                    with pytest.raises(HTTPException) as exc_info:
                        get_current_user_id(
                            authorization="Bearer valid-token",
                            config=mock_config
                        )

                    assert exc_info.value.status_code == 401
                    assert "User not found" in str(exc_info.value.detail)

    def test_get_current_user_id_success(self, mock_config):
        """get_current_user_id should return org user ID on success."""
        from src.api.notifications_routes import get_current_user_id

        with patch("src.services.auth_service.get_cached_auth_client") as mock_client:
            mock_client.return_value = MagicMock()
            with patch("src.services.auth_service.AuthService.verify_jwt") as mock_verify:
                mock_verify.return_value = (True, {'sub': 'auth-user-id'})

                with patch("src.api.notifications_routes.SupabaseTool") as mock_supabase:
                    mock_query = MagicMock()
                    mock_query.select.return_value = mock_query
                    mock_query.eq.return_value = mock_query
                    mock_query.single.return_value = mock_query
                    mock_query.execute.return_value = MagicMock(data={'id': 'org-user-123'})
                    mock_supabase.return_value.client.table.return_value = mock_query

                    result = get_current_user_id(
                        authorization="Bearer valid-token",
                        config=mock_config
                    )

                    assert result == 'org-user-123'
