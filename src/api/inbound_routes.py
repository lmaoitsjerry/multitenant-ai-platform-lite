"""
Inbound Tickets API Routes

Provides endpoints for managing customer support tickets:
- List tickets
- Get ticket details
- Update ticket status
- Add replies
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Header, Query, Body
from pydantic import BaseModel, Field

from config.loader import ClientConfig

logger = logging.getLogger(__name__)

# ==================== Router ====================

inbound_router = APIRouter(prefix="/api/v1/inbound", tags=["Inbound"])


# ==================== Models ====================

class TicketReply(BaseModel):
    """Reply to a ticket"""
    message: str = Field(..., min_length=1)


class TicketStatusUpdate(BaseModel):
    """Update ticket status"""
    status: str = Field(..., pattern="^(open|in_progress|resolved|closed)$")
    assigned_to: Optional[str] = None
    notes: Optional[str] = None


# ==================== Dependency ====================

_client_configs = {}


def get_client_config(x_client_id: str = Header(None, alias="X-Client-ID")) -> ClientConfig:
    """Get client configuration from header"""
    import os
    client_id = x_client_id or os.getenv("CLIENT_ID", "example")

    if client_id not in _client_configs:
        try:
            _client_configs[client_id] = ClientConfig(client_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid client: {client_id}")

    return _client_configs[client_id]


# ==================== Endpoints ====================

@inbound_router.get("/tickets")
async def list_tickets(
    status: Optional[str] = Query(None, pattern="^(open|in_progress|resolved|closed)$"),
    priority: Optional[str] = Query(None, pattern="^(low|normal|high|urgent)$"),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    config: ClientConfig = Depends(get_client_config)
):
    """
    List inbound tickets with optional filtering

    Status: open, in_progress, resolved, closed
    Priority: low, normal, high, urgent
    """
    from src.tools.supabase_tool import SupabaseTool

    try:
        supabase = SupabaseTool(config)
        tickets = supabase.list_tickets(status=status, limit=limit, offset=offset)

        # Calculate stats
        all_tickets = supabase.list_tickets(limit=1000) if not status else tickets
        stats = {
            "total": len(all_tickets) if not status else 0,
            "open": len([t for t in all_tickets if t.get('status') == 'open']),
            "in_progress": len([t for t in all_tickets if t.get('status') == 'in_progress']),
            "resolved": len([t for t in all_tickets if t.get('status') == 'resolved']),
        }

        return {
            "success": True,
            "data": tickets,
            "count": len(tickets),
            "stats": stats
        }

    except Exception as e:
        logger.error(f"Failed to list tickets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@inbound_router.get("/tickets/{ticket_id}")
async def get_ticket(
    ticket_id: str,
    config: ClientConfig = Depends(get_client_config)
):
    """Get ticket by ID with conversation history"""
    from src.tools.supabase_tool import SupabaseTool

    try:
        supabase = SupabaseTool(config)

        if not supabase.client:
            raise HTTPException(status_code=500, detail="Database not available")

        # Get ticket
        result = supabase.client.table(supabase.TABLE_TICKETS)\
            .select("*")\
            .eq('ticket_id', ticket_id)\
            .eq('tenant_id', config.client_id)\
            .single()\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Ticket not found")

        ticket = result.data

        # Get conversation history from metadata or separate table
        conversation = ticket.get('conversation', []) or ticket.get('metadata', {}).get('conversation', [])

        return {
            "success": True,
            "data": {
                **ticket,
                "conversation": conversation
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get ticket: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@inbound_router.patch("/tickets/{ticket_id}")
async def update_ticket(
    ticket_id: str,
    update: TicketStatusUpdate,
    config: ClientConfig = Depends(get_client_config)
):
    """Update ticket status and assignment"""
    from src.tools.supabase_tool import SupabaseTool

    try:
        supabase = SupabaseTool(config)

        success = supabase.update_ticket(
            ticket_id=ticket_id,
            status=update.status,
            assigned_to=update.assigned_to,
            notes=update.notes
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update ticket")

        # Get updated ticket
        result = supabase.client.table(supabase.TABLE_TICKETS)\
            .select("*")\
            .eq('ticket_id', ticket_id)\
            .eq('tenant_id', config.client_id)\
            .single()\
            .execute()

        return {
            "success": True,
            "data": result.data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update ticket: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@inbound_router.post("/tickets/{ticket_id}/reply")
async def reply_to_ticket(
    ticket_id: str,
    reply: TicketReply,
    config: ClientConfig = Depends(get_client_config)
):
    """Add a reply to a ticket"""
    from src.tools.supabase_tool import SupabaseTool

    try:
        supabase = SupabaseTool(config)

        if not supabase.client:
            raise HTTPException(status_code=500, detail="Database not available")

        # Get ticket
        result = supabase.client.table(supabase.TABLE_TICKETS)\
            .select("*")\
            .eq('ticket_id', ticket_id)\
            .eq('tenant_id', config.client_id)\
            .single()\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Ticket not found")

        ticket = result.data

        # Add reply to conversation
        conversation = ticket.get('conversation', []) or ticket.get('metadata', {}).get('conversation', [])
        conversation.append({
            "role": "agent",
            "content": reply.message,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Update ticket with new conversation and mark in_progress
        update_data = {
            'conversation': conversation,
            'status': 'in_progress' if ticket.get('status') == 'open' else ticket.get('status'),
            'updated_at': datetime.utcnow().isoformat()
        }

        supabase.client.table(supabase.TABLE_TICKETS)\
            .update(update_data)\
            .eq('ticket_id', ticket_id)\
            .eq('tenant_id', config.client_id)\
            .execute()

        return {
            "success": True,
            "message": "Reply added",
            "conversation": conversation
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add reply: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@inbound_router.get("/stats")
async def get_inbound_stats(
    config: ClientConfig = Depends(get_client_config)
):
    """Get inbound ticket statistics"""
    from src.tools.supabase_tool import SupabaseTool

    try:
        supabase = SupabaseTool(config)

        if not supabase.client:
            return {
                "success": True,
                "data": {"total": 0, "open": 0, "in_progress": 0, "resolved": 0, "closed": 0}
            }

        result = supabase.client.table(supabase.TABLE_TICKETS)\
            .select("status")\
            .eq('tenant_id', config.client_id)\
            .execute()

        tickets = result.data or []

        stats = {
            "total": len(tickets),
            "open": len([t for t in tickets if t.get('status') == 'open']),
            "in_progress": len([t for t in tickets if t.get('status') == 'in_progress']),
            "resolved": len([t for t in tickets if t.get('status') == 'resolved']),
            "closed": len([t for t in tickets if t.get('status') == 'closed']),
        }

        return {
            "success": True,
            "data": stats
        }

    except Exception as e:
        logger.error(f"Failed to get inbound stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
