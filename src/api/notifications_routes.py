"""
Notifications API Routes

Endpoints for managing user notifications:
- List notifications
- Mark as read
- Mark all as read
- Get unread count
- Manage preferences
"""

import os
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Header, Query
from pydantic import BaseModel
from datetime import datetime, timedelta

from config.loader import ClientConfig
from src.tools.supabase_tool import SupabaseTool

logger = logging.getLogger(__name__)

notifications_router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])


# ==================== Pydantic Models ====================

class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    message: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    read: bool
    created_at: str


class NotificationPreferencesUpdate(BaseModel):
    email_quote_request: Optional[bool] = None
    email_email_received: Optional[bool] = None
    email_invoice_paid: Optional[bool] = None
    email_invoice_overdue: Optional[bool] = None
    email_booking_confirmed: Optional[bool] = None
    email_client_added: Optional[bool] = None
    email_team_invite: Optional[bool] = None
    email_system: Optional[bool] = None
    email_mention: Optional[bool] = None
    email_digest_enabled: Optional[bool] = None
    email_digest_frequency: Optional[str] = None


class MarkReadRequest(BaseModel):
    notification_ids: List[str]


# ==================== Dependency ====================

_client_configs = {}


def get_client_config(x_client_id: str = Header(None, alias="X-Client-ID")) -> ClientConfig:
    """Get client configuration from header"""
    client_id = x_client_id or os.getenv("CLIENT_ID", "example")

    if client_id not in _client_configs:
        try:
            _client_configs[client_id] = ClientConfig(client_id)
        except Exception as e:
            logger.error(f"Failed to load config for {client_id}: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid client: {client_id}")

    return _client_configs[client_id]


def get_current_user_id(
    authorization: str = Header(None),
    config: ClientConfig = Depends(get_client_config)
) -> str:
    """Extract user ID from JWT token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization required")

    from src.services.auth_service import AuthService

    auth_service = AuthService(
        supabase_url=config.supabase_url,
        supabase_key=config.supabase_service_key
    )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    valid, payload = auth_service.verify_jwt(parts[1])
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Get organization user ID from auth user ID
    supabase = SupabaseTool(config)
    result = supabase.client.table('organization_users')\
        .select('id')\
        .eq('auth_user_id', payload.get('sub'))\
        .eq('tenant_id', config.client_id)\
        .single()\
        .execute()

    if not result.data:
        raise HTTPException(status_code=401, detail="User not found")

    return result.data['id']


# ==================== Endpoints ====================

@notifications_router.get("")
async def list_notifications(
    config: ClientConfig = Depends(get_client_config),
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0),
    unread_only: bool = Query(default=False)
):
    """
    List notifications for current user

    Returns paginated list of notifications, newest first.
    """
    try:
        supabase = SupabaseTool(config)

        query = supabase.client.table('notifications')\
            .select('*')\
            .eq('tenant_id', config.client_id)\
            .or_(f'user_id.eq.{user_id},user_id.is.null')\
            .order('created_at', desc=True)\
            .limit(limit)\
            .offset(offset)

        if unread_only:
            query = query.eq('read', False)

        result = query.execute()

        # Get total count for pagination
        count_query = supabase.client.table('notifications')\
            .select('id', count='exact')\
            .eq('tenant_id', config.client_id)\
            .or_(f'user_id.eq.{user_id},user_id.is.null')

        if unread_only:
            count_query = count_query.eq('read', False)

        count_result = count_query.execute()

        # Format timestamps for frontend
        notifications = []
        for n in (result.data or []):
            notifications.append({
                'id': n['id'],
                'type': n['type'],
                'title': n['title'],
                'message': n['message'],
                'entity_type': n.get('entity_type'),
                'entity_id': n.get('entity_id'),
                'read': n['read'],
                'created_at': n['created_at'],
                'time_ago': _format_time_ago(n['created_at'])
            })

        return {
            'success': True,
            'data': notifications,
            'total': count_result.count if hasattr(count_result, 'count') else len(result.data or []),
            'limit': limit,
            'offset': offset
        }

    except Exception as e:
        logger.error(f"Error listing notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@notifications_router.get("/unread-count")
async def get_unread_count(
    config: ClientConfig = Depends(get_client_config),
    user_id: str = Depends(get_current_user_id)
):
    """Get count of unread notifications"""
    try:
        supabase = SupabaseTool(config)

        result = supabase.client.table('notifications')\
            .select('id', count='exact')\
            .eq('tenant_id', config.client_id)\
            .or_(f'user_id.eq.{user_id},user_id.is.null')\
            .eq('read', False)\
            .execute()

        return {
            'success': True,
            'unread_count': result.count if hasattr(result, 'count') else 0
        }

    except Exception as e:
        logger.error(f"Error getting unread count: {e}")
        return {'success': True, 'unread_count': 0}


@notifications_router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    config: ClientConfig = Depends(get_client_config),
    user_id: str = Depends(get_current_user_id)
):
    """Mark a single notification as read"""
    try:
        supabase = SupabaseTool(config)

        result = supabase.client.table('notifications')\
            .update({'read': True, 'read_at': datetime.utcnow().isoformat()})\
            .eq('id', notification_id)\
            .eq('tenant_id', config.client_id)\
            .or_(f'user_id.eq.{user_id},user_id.is.null')\
            .execute()

        return {
            'success': True,
            'message': 'Notification marked as read'
        }

    except Exception as e:
        logger.error(f"Error marking notification read: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@notifications_router.post("/mark-all-read")
async def mark_all_read(
    config: ClientConfig = Depends(get_client_config),
    user_id: str = Depends(get_current_user_id)
):
    """Mark all notifications as read for current user"""
    try:
        supabase = SupabaseTool(config)

        # Update all unread notifications for this user
        result = supabase.client.table('notifications')\
            .update({'read': True, 'read_at': datetime.utcnow().isoformat()})\
            .eq('tenant_id', config.client_id)\
            .eq('user_id', user_id)\
            .eq('read', False)\
            .execute()

        # Also mark system-wide notifications as read
        supabase.client.table('notifications')\
            .update({'read': True, 'read_at': datetime.utcnow().isoformat()})\
            .eq('tenant_id', config.client_id)\
            .is_('user_id', None)\
            .eq('read', False)\
            .execute()

        return {
            'success': True,
            'message': 'All notifications marked as read'
        }

    except Exception as e:
        logger.error(f"Error marking all read: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@notifications_router.get("/preferences")
async def get_notification_preferences(
    config: ClientConfig = Depends(get_client_config),
    user_id: str = Depends(get_current_user_id)
):
    """Get notification preferences for current user"""
    try:
        supabase = SupabaseTool(config)

        result = supabase.client.table('notification_preferences')\
            .select('*')\
            .eq('tenant_id', config.client_id)\
            .eq('user_id', user_id)\
            .single()\
            .execute()

        if not result.data:
            # Return defaults if no preferences exist
            return {
                'success': True,
                'data': {
                    'email_quote_request': True,
                    'email_email_received': True,
                    'email_invoice_paid': True,
                    'email_invoice_overdue': True,
                    'email_booking_confirmed': True,
                    'email_client_added': False,
                    'email_team_invite': True,
                    'email_system': True,
                    'email_mention': True,
                    'email_digest_enabled': False,
                    'email_digest_frequency': 'daily'
                }
            }

        return {
            'success': True,
            'data': result.data
        }

    except Exception as e:
        logger.error(f"Error getting preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@notifications_router.put("/preferences")
async def update_notification_preferences(
    preferences: NotificationPreferencesUpdate,
    config: ClientConfig = Depends(get_client_config),
    user_id: str = Depends(get_current_user_id)
):
    """Update notification preferences for current user"""
    try:
        supabase = SupabaseTool(config)

        # Build update data (only include non-None values)
        update_data = {k: v for k, v in preferences.model_dump().items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No preferences to update")

        # Upsert preferences
        result = supabase.client.table('notification_preferences')\
            .upsert({
                'tenant_id': config.client_id,
                'user_id': user_id,
                **update_data
            })\
            .execute()

        return {
            'success': True,
            'message': 'Preferences updated',
            'data': result.data[0] if result.data else update_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Helper Functions ====================

def _format_time_ago(timestamp_str: str) -> str:
    """Format timestamp as human-readable time ago string"""
    try:
        if 'Z' in timestamp_str:
            timestamp_str = timestamp_str.replace('Z', '+00:00')

        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.utcnow()

        diff = now - timestamp

        if diff.days > 7:
            return timestamp.strftime('%b %d')
        elif diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "Just now"
    except Exception:
        return "Recently"


# ==================== Notification Service ====================

class NotificationService:
    """Service for creating notifications from backend events"""

    def __init__(self, config: ClientConfig):
        self.config = config
        self.supabase = SupabaseTool(config)

    def create_notification(
        self,
        user_id: str,
        type: str,
        title: str,
        message: str,
        entity_type: str = None,
        entity_id: str = None,
        metadata: dict = None
    ) -> Optional[str]:
        """Create a notification for a specific user"""
        try:
            result = self.supabase.client.table('notifications').insert({
                'tenant_id': self.config.client_id,
                'user_id': user_id,
                'type': type,
                'title': title,
                'message': message,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'metadata': metadata or {}
            }).execute()

            return result.data[0]['id'] if result.data else None
        except Exception as e:
            logger.error(f"Failed to create notification: {e}")
            return None

    def notify_all_users(
        self,
        type: str,
        title: str,
        message: str,
        entity_type: str = None,
        entity_id: str = None,
        metadata: dict = None
    ) -> int:
        """Create notifications for all tenant users"""
        try:
            # Get all active users
            users = self.supabase.client.table('organization_users')\
                .select('id')\
                .eq('tenant_id', self.config.client_id)\
                .eq('is_active', True)\
                .execute()

            count = 0
            for user in (users.data or []):
                if self.create_notification(
                    user_id=user['id'],
                    type=type,
                    title=title,
                    message=message,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    metadata=metadata
                ):
                    count += 1

            return count
        except Exception as e:
            logger.error(f"Failed to notify all users: {e}")
            return 0

    def notify_quote_request(self, customer_name: str, destination: str, quote_id: str):
        """Notify about new quote request"""
        self.notify_all_users(
            type='quote_request',
            title='New quote request',
            message=f'{customer_name} requested a quote for {destination}',
            entity_type='quote',
            entity_id=quote_id
        )

    def notify_email_received(self, sender_email: str, subject: str):
        """Notify about new email received"""
        self.notify_all_users(
            type='email_received',
            title='Email received',
            message=f'New inquiry from {sender_email}',
            metadata={'subject': subject}
        )

    def notify_invoice_paid(self, customer_name: str, invoice_id: str, amount: float, currency: str):
        """Notify about invoice payment"""
        self.notify_all_users(
            type='invoice_paid',
            title='Invoice paid',
            message=f'Payment received from {customer_name}: {currency} {amount:,.2f}',
            entity_type='invoice',
            entity_id=invoice_id
        )

    def notify_client_added(self, client_name: str, client_id: str, added_by: str):
        """Notify about new client"""
        self.notify_all_users(
            type='client_added',
            title='New client added',
            message=f'{client_name} was added by {added_by}',
            entity_type='client',
            entity_id=client_id
        )
