"""Tests for status transition validation."""

import pytest
from fastapi import HTTPException
from src.utils.status_transitions import (
    validate_transition,
    INVOICE_STATUS_TRANSITIONS,
    QUOTE_STATUS_TRANSITIONS,
    TICKET_STATUS_TRANSITIONS,
)


class TestInvoiceTransitions:
    """Test invoice status transition validation."""

    @pytest.mark.parametrize("current,target", [
        ("draft", "sent"),
        ("draft", "cancelled"),
        ("sent", "paid"),
        ("sent", "partially_paid"),
        ("sent", "overdue"),
        ("sent", "cancelled"),
        ("partially_paid", "paid"),
        ("partially_paid", "cancelled"),
        ("overdue", "paid"),
        ("overdue", "cancelled"),
    ])
    def test_valid_transitions(self, current, target):
        """All valid transitions should not raise."""
        validate_transition(current, target, INVOICE_STATUS_TRANSITIONS, "invoice")

    @pytest.mark.parametrize("current,target", [
        ("draft", "overdue"),
        ("sent", "draft"),
        ("partially_paid", "draft"),
        ("overdue", "draft"),
        ("viewed", "draft"),
    ])
    def test_invalid_transitions_raise_409(self, current, target):
        """Invalid transitions should raise HTTPException 409."""
        with pytest.raises(HTTPException) as exc_info:
            validate_transition(current, target, INVOICE_STATUS_TRANSITIONS, "invoice")
        assert exc_info.value.status_code == 409

    @pytest.mark.parametrize("terminal", ["paid", "cancelled"])
    def test_terminal_states_raise_409(self, terminal):
        """Terminal states should reject all transitions."""
        with pytest.raises(HTTPException) as exc_info:
            validate_transition(terminal, "draft", INVOICE_STATUS_TRANSITIONS, "invoice")
        assert exc_info.value.status_code == 409
        assert "terminal" in str(exc_info.value.detail)

    def test_unknown_status_raises_400(self):
        """Unknown current status should raise 400."""
        with pytest.raises(HTTPException) as exc_info:
            validate_transition("nonexistent", "draft", INVOICE_STATUS_TRANSITIONS, "invoice")
        assert exc_info.value.status_code == 400

    def test_case_insensitive(self):
        """Transitions should be case-insensitive."""
        validate_transition("Draft", "Sent", INVOICE_STATUS_TRANSITIONS, "invoice")
        validate_transition("SENT", "PAID", INVOICE_STATUS_TRANSITIONS, "invoice")

    def test_error_message_includes_allowed(self):
        """Error message should list allowed transitions."""
        with pytest.raises(HTTPException) as exc_info:
            validate_transition("draft", "overdue", INVOICE_STATUS_TRANSITIONS, "invoice")
        detail = str(exc_info.value.detail)
        assert "cancelled" in detail
        assert "sent" in detail


class TestQuoteTransitions:
    """Test quote status transition validation."""

    @pytest.mark.parametrize("current,target", [
        ("draft", "quoted"),
        ("draft", "cancelled"),
        ("quoted", "sent"),
        ("quoted", "accepted"),
        ("quoted", "declined"),
        ("sent", "viewed"),
        ("sent", "accepted"),
        ("accepted", "converted"),
        ("declined", "quoted"),
        ("expired", "quoted"),
    ])
    def test_valid_transitions(self, current, target):
        """All valid quote transitions should not raise."""
        validate_transition(current, target, QUOTE_STATUS_TRANSITIONS, "quote")

    @pytest.mark.parametrize("terminal", ["converted", "cancelled"])
    def test_terminal_states(self, terminal):
        """Terminal quote states should reject all transitions."""
        with pytest.raises(HTTPException) as exc_info:
            validate_transition(terminal, "draft", QUOTE_STATUS_TRANSITIONS, "quote")
        assert exc_info.value.status_code == 409

    def test_invalid_transition(self):
        """Cannot go from draft directly to paid."""
        with pytest.raises(HTTPException) as exc_info:
            validate_transition("draft", "accepted", QUOTE_STATUS_TRANSITIONS, "quote")
        assert exc_info.value.status_code == 409


class TestTicketTransitions:
    """Test ticket status transition validation."""

    @pytest.mark.parametrize("current,target", [
        ("open", "in_progress"),
        ("open", "closed"),
        ("in_progress", "resolved"),
        ("in_progress", "closed"),
        ("resolved", "closed"),
    ])
    def test_valid_transitions(self, current, target):
        validate_transition(current, target, TICKET_STATUS_TRANSITIONS, "ticket")

    def test_closed_is_terminal(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_transition("closed", "open", TICKET_STATUS_TRANSITIONS, "ticket")
        assert exc_info.value.status_code == 409

    def test_cannot_reopen_resolved(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_transition("resolved", "open", TICKET_STATUS_TRANSITIONS, "ticket")
        assert exc_info.value.status_code == 409

    def test_cannot_skip_to_resolved_from_open(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_transition("open", "resolved", TICKET_STATUS_TRANSITIONS, "ticket")
        assert exc_info.value.status_code == 409


class TestEntityNameInErrors:
    """Error messages should include the entity name."""

    def test_entity_name_in_unknown_status(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_transition("bogus", "draft", INVOICE_STATUS_TRANSITIONS, "invoice")
        assert "invoice" in str(exc_info.value.detail)

    def test_entity_name_in_terminal(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_transition("paid", "draft", INVOICE_STATUS_TRANSITIONS, "invoice")
        assert "invoice" in str(exc_info.value.detail)

    def test_entity_name_in_invalid(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_transition("draft", "overdue", INVOICE_STATUS_TRANSITIONS, "invoice")
        assert "invoice" in str(exc_info.value.detail)
