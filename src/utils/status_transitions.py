"""
Reusable status transition validation for all entities with status workflows.
"""

from typing import Dict, Set
from fastapi import HTTPException


# --- Invoice Status Machine ---

INVOICE_STATUS_TRANSITIONS: Dict[str, Set[str]] = {
    "draft": {"sent", "paid", "cancelled"},
    "sent": {"viewed", "paid", "partially_paid", "overdue", "cancelled"},
    "viewed": {"paid", "partially_paid", "overdue", "cancelled"},
    "partially_paid": {"paid", "cancelled"},
    "partial": {"paid", "cancelled"},  # legacy alias for partially_paid
    "overdue": {"paid", "cancelled"},
    "cancelled": set(),  # terminal
    "paid": set(),        # terminal
}

# --- Quote Status Machine ---

QUOTE_STATUS_TRANSITIONS: Dict[str, Set[str]] = {
    "draft": {"quoted", "cancelled"},
    "quoted": {"sent", "accepted", "declined", "expired", "cancelled"},
    "sent": {"viewed", "accepted", "declined", "expired", "cancelled"},
    "viewed": {"accepted", "declined", "expired", "cancelled"},
    "accepted": {"converted", "cancelled"},
    "declined": {"quoted"},  # allow re-quoting
    "expired": {"quoted"},   # allow re-quoting
    "converted": set(),      # terminal
    "cancelled": set(),      # terminal
}

# --- Enquiry/Ticket Status Machine ---
# Matches Pydantic TicketStatusUpdate regex: open|in_progress|resolved|closed

TICKET_STATUS_TRANSITIONS: Dict[str, Set[str]] = {
    "open": {"in_progress", "closed"},
    "in_progress": {"resolved", "closed"},
    "resolved": {"closed"},
    "closed": set(),  # terminal
}


def validate_transition(
    current_status: str,
    target_status: str,
    transitions: Dict[str, Set[str]],
    entity_name: str = "record",
) -> None:
    """
    Validate a status transition. Raises HTTPException if invalid.

    Args:
        current_status: Current status (will be lowercased)
        target_status: Desired new status (will be lowercased)
        transitions: The transition map to validate against
        entity_name: For error messages (e.g., "invoice", "quote")

    Raises:
        HTTPException 409 if transition is invalid
        HTTPException 400 if current status is unknown
    """
    current = current_status.lower()
    target = target_status.lower()

    if current not in transitions:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown {entity_name} status: '{current_status}'"
        )

    allowed = transitions[current]

    if not allowed:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot change {entity_name} status from '{current}' — "
                   f"it is in a terminal state."
        )

    if target not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot change {entity_name} status from '{current}' to '{target}'. "
                   f"Allowed transitions: {', '.join(sorted(allowed))}"
        )
