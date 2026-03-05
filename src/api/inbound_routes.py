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
from src.api.dependencies import get_client_config
from src.utils.error_handler import log_and_raise

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



# ==================== Endpoints ====================

@inbound_router.get("/tickets")
def list_tickets(
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

        # Check if client is available
        if not supabase.client:
            logger.warning("Supabase client not available for inbound tickets")
            return {
                "success": True,
                "data": [],
                "count": 0,
                "stats": {"total": 0, "open": 0, "in_progress": 0, "resolved": 0}
            }

        tickets = supabase.get_tickets(status=status, limit=limit, offset=offset)

        # Calculate stats - always get all tickets for accurate counts
        try:
            all_tickets = supabase.get_tickets(limit=1000)
        except Exception:
            all_tickets = tickets if not status else []

        stats = {
            "total": len(all_tickets),
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
        # Log error but return empty data instead of 500
        logger.error(f"Error listing tickets: {e}")
        return {
            "success": True,
            "data": [],
            "count": 0,
            "stats": {"total": 0, "open": 0, "in_progress": 0, "resolved": 0},
            "warning": "Tickets table may not exist yet. Run migration 016_inbound_tickets.sql"
        }


@inbound_router.get("/tickets/{ticket_id}")
def get_ticket(
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
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Ticket not found")

        ticket = result.data[0]

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
        log_and_raise(500, "getting ticket details", e, logger)


@inbound_router.patch("/tickets/{ticket_id}")
def update_ticket(
    ticket_id: str,
    update: TicketStatusUpdate,
    config: ClientConfig = Depends(get_client_config)
):
    """Update ticket status and assignment with transition validation"""
    from src.tools.supabase_tool import SupabaseTool
    from src.utils.status_transitions import validate_transition, TICKET_STATUS_TRANSITIONS

    try:
        supabase = SupabaseTool(config)

        # Verify ticket exists and belongs to tenant
        existing = supabase.client.table(supabase.TABLE_TICKETS)\
            .select("ticket_id, status")\
            .eq('ticket_id', ticket_id)\
            .eq('tenant_id', config.client_id)\
            .execute()

        if not existing.data:
            raise HTTPException(status_code=404, detail="Ticket not found")

        # Validate status transition
        if update.status:
            validate_transition(
                current_status=existing.data[0].get("status", "open"),
                target_status=update.status,
                transitions=TICKET_STATUS_TRANSITIONS,
                entity_name="ticket",
            )

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
            .execute()

        return {
            "success": True,
            "data": result.data[0] if result.data else None
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "updating ticket", e, logger)


@inbound_router.post("/tickets/{ticket_id}/reply")
def reply_to_ticket(
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
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Ticket not found")

        ticket = result.data[0]

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
        log_and_raise(500, "adding reply to ticket", e, logger)


@inbound_router.post("/tickets/seed")
def seed_sample_tickets(
    config: ClientConfig = Depends(get_client_config)
):
    """
    Create sample tickets for testing the triage UI
    Only creates tickets if none exist
    """
    from src.tools.supabase_tool import SupabaseTool
    import secrets

    try:
        supabase = SupabaseTool(config)

        if not supabase.client:
            raise HTTPException(status_code=500, detail="Database not available")

        # Check if tickets already exist
        existing = supabase.get_tickets(limit=1)
        if existing:
            return {
                "success": True,
                "message": "Sample tickets already exist",
                "count": 0
            }

        # Sample enquiries for testing
        sample_tickets = [
            {
                "customer_name": "John Smith",
                "customer_email": "john.smith@example.com",
                "subject": "Zanzibar Honeymoon Package",
                "message": "Hi, my wife and I are looking for a romantic honeymoon in Zanzibar for 7 nights in March 2025. We'd prefer a beachfront resort with all-inclusive meals. Our budget is around R80,000 for 2 adults. Could you please send us some options?",
                "priority": "high",
                "source": "email",
                "metadata": {"parsed_details": {"destination": "Zanzibar", "travelers": "2 adults", "budget": "R80,000"}}
            },
            {
                "customer_name": "Sarah Johnson",
                "customer_email": "sarah.j@gmail.com",
                "subject": "Family trip to Mauritius",
                "message": "Hello! We're a family of 4 (2 adults, 2 kids aged 8 and 12) wanting to visit Mauritius in December. Looking for a kid-friendly resort with activities. About 10 nights. What packages do you have available?",
                "priority": "normal",
                "source": "web",
                "metadata": {"parsed_details": {"destination": "Mauritius", "travelers": "2 adults, 2 children"}}
            },
            {
                "customer_name": "Michael Chen",
                "customer_email": "m.chen@corporate.com",
                "subject": "Corporate retreat - Maldives",
                "message": "We need to book a corporate retreat for 8 executives in the Maldives. Prefer overwater villas, 5 nights, sometime in April. Need meeting facilities. Please advise on options and pricing.",
                "priority": "urgent",
                "source": "email",
                "metadata": {"parsed_details": {"destination": "Maldives", "travelers": "8 adults"}}
            },
            {
                "customer_name": "Emma Wilson",
                "customer_email": "emma.w@outlook.com",
                "subject": "Safari and beach combo",
                "message": "I'm interested in doing a Kenya safari followed by beach relaxation in Zanzibar. Probably 4 days safari + 5 days beach. Traveling solo in June. Mid-range budget. What would you recommend?",
                "priority": "normal",
                "source": "chat",
                "metadata": {"parsed_details": {"destination": "Kenya + Zanzibar", "travelers": "1 adult"}}
            },
            {
                "customer_name": "David Brown",
                "customer_email": "dbrown@mail.co.za",
                "subject": "Quick question about Dubai",
                "message": "Just checking prices for Dubai. 2 people. 5 nights. Thanks.",
                "priority": "low",
                "source": "web",
                "metadata": {"parsed_details": {"destination": "Dubai", "travelers": "2 adults"}}
            },
        ]

        created_count = 0
        for ticket_data in sample_tickets:
            ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"
            record = {
                "tenant_id": config.client_id,
                "ticket_id": ticket_id,
                "status": "open",
                "conversation": [],
                **ticket_data
            }

            try:
                supabase.client.table(supabase.TABLE_TICKETS).insert(record).execute()
                created_count += 1
            except Exception as e:
                logger.warning(f"Failed to create sample ticket: {e}")

        return {
            "success": True,
            "message": f"Created {created_count} sample tickets",
            "count": created_count
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "seeding sample tickets", e, logger)


@inbound_router.get("/stats")
def get_inbound_stats(
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
        log_and_raise(500, "getting inbound stats", e, logger)
