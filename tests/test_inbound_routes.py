"""
Inbound Routes Unit Tests

Comprehensive tests for inbound ticket API routes:
- GET /api/v1/inbound/tickets - List tickets
- GET /api/v1/inbound/tickets/{id} - Get ticket details
- PATCH /api/v1/inbound/tickets/{id} - Update ticket status
- POST /api/v1/inbound/tickets/{id}/reply - Reply to ticket
- GET /api/v1/inbound/stats - Get ticket statistics

Uses pytest with mocked dependencies.
Note: These routes use X-Client-ID based routing, not JWT auth.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


# ==================== Fixtures ====================

@pytest.fixture
def mock_config():
    """Create a mock ClientConfig."""
    config = MagicMock()
    config.client_id = "test_tenant"
    config.supabase_url = "https://test.supabase.co"
    config.supabase_service_key = "test-service-key"
    config.supabase_anon_key = "test-anon-key"
    config.currency = "USD"
    return config


def create_chainable_mock(data=None):
    """Create a mock that supports method chaining for Supabase queries."""
    mock = MagicMock()
    mock.select.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.delete.return_value = mock
    mock.eq.return_value = mock
    mock.neq.return_value = mock
    mock.gt.return_value = mock
    mock.gte.return_value = mock
    mock.lt.return_value = mock
    mock.lte.return_value = mock
    mock.is_.return_value = mock
    mock.in_.return_value = mock
    mock.order.return_value = mock
    mock.limit.return_value = mock
    mock.range.return_value = mock
    mock.single.return_value = mock

    # Set execute result
    execute_result = MagicMock()
    execute_result.data = data if data is not None else []
    mock.execute.return_value = execute_result

    return mock


# ==================== Pydantic Model Tests ====================

class TestInboundModels:
    """Test Pydantic model validation."""

    def test_ticket_reply_requires_message(self):
        """TicketReply requires non-empty message."""
        from src.api.inbound_routes import TicketReply
        from pydantic import ValidationError

        # Empty message should fail
        with pytest.raises(ValidationError):
            TicketReply(message="")

        # Valid message should work
        reply = TicketReply(message="Thank you for your inquiry.")
        assert reply.message == "Thank you for your inquiry."

    def test_ticket_reply_with_long_message(self):
        """TicketReply accepts reasonably long messages."""
        from src.api.inbound_routes import TicketReply

        long_message = "A" * 5000
        reply = TicketReply(message=long_message)
        assert len(reply.message) == 5000

    def test_ticket_status_update_valid_status(self):
        """TicketStatusUpdate accepts valid status values."""
        from src.api.inbound_routes import TicketStatusUpdate

        for status in ["open", "in_progress", "resolved", "closed"]:
            update = TicketStatusUpdate(status=status)
            assert update.status == status

    def test_ticket_status_update_invalid_status(self):
        """TicketStatusUpdate rejects invalid status values."""
        from src.api.inbound_routes import TicketStatusUpdate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            TicketStatusUpdate(status="invalid_status")

        with pytest.raises(ValidationError):
            TicketStatusUpdate(status="pending")

        with pytest.raises(ValidationError):
            TicketStatusUpdate(status="")

    def test_ticket_status_update_optional_fields(self):
        """TicketStatusUpdate has optional assigned_to and notes."""
        from src.api.inbound_routes import TicketStatusUpdate

        # With all fields
        update = TicketStatusUpdate(
            status="in_progress",
            assigned_to="agent@example.com",
            notes="Taking over this ticket"
        )
        assert update.status == "in_progress"
        assert update.assigned_to == "agent@example.com"
        assert update.notes == "Taking over this ticket"

        # Without optional fields
        update = TicketStatusUpdate(status="open")
        assert update.assigned_to is None
        assert update.notes is None

    def test_ticket_status_update_case_sensitivity(self):
        """TicketStatusUpdate status must be lowercase."""
        from src.api.inbound_routes import TicketStatusUpdate
        from pydantic import ValidationError

        # Uppercase should fail
        with pytest.raises(ValidationError):
            TicketStatusUpdate(status="OPEN")

        with pytest.raises(ValidationError):
            TicketStatusUpdate(status="In_Progress")


# ==================== Route Structure Tests ====================

class TestInboundRouteStructure:
    """Test the structure of inbound routes."""

    def test_router_has_correct_prefix(self):
        """Router should have /api/v1/inbound prefix."""
        from src.api.inbound_routes import inbound_router
        assert inbound_router.prefix == "/api/v1/inbound"

    def test_router_has_correct_tags(self):
        """Router should have Inbound tag."""
        from src.api.inbound_routes import inbound_router
        assert "Inbound" in inbound_router.tags

    def test_tickets_endpoint_exists(self):
        """GET /tickets endpoint should exist."""
        from src.api.inbound_routes import inbound_router

        routes = [route.path for route in inbound_router.routes]
        # Routes include full path with prefix
        assert any("/tickets" in route and "{ticket_id}" not in route for route in routes)

    def test_ticket_detail_endpoint_exists(self):
        """GET /tickets/{ticket_id} endpoint should exist."""
        from src.api.inbound_routes import inbound_router

        routes = [route.path for route in inbound_router.routes]
        assert any("{ticket_id}" in route and "reply" not in route for route in routes)

    def test_ticket_reply_endpoint_exists(self):
        """POST /tickets/{ticket_id}/reply endpoint should exist."""
        from src.api.inbound_routes import inbound_router

        routes = [route.path for route in inbound_router.routes]
        assert any("reply" in route for route in routes)

    def test_stats_endpoint_exists(self):
        """GET /stats endpoint should exist."""
        from src.api.inbound_routes import inbound_router

        routes = [route.path for route in inbound_router.routes]
        assert any("/stats" in route for route in routes)

    def test_router_has_all_expected_routes(self):
        """Router should have all expected routes."""
        from src.api.inbound_routes import inbound_router

        routes = [route.path for route in inbound_router.routes]
        expected_patterns = ["/tickets", "ticket_id", "/reply", "/stats"]

        for pattern in expected_patterns:
            assert any(pattern in route for route in routes), f"Missing route with pattern: {pattern}"


# ==================== List Tickets Logic Tests ====================

class TestListTicketsLogic:
    """Test list_tickets endpoint logic with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_list_tickets_returns_tickets(self, mock_config):
        """list_tickets should return tickets from SupabaseTool."""
        from src.api.inbound_routes import list_tickets

        mock_tickets = [
            {"ticket_id": "TKT-001", "subject": "Test 1", "status": "open"},
            {"ticket_id": "TKT-002", "subject": "Test 2", "status": "resolved"},
        ]

        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.list_tickets.return_value = mock_tickets
            mock_supabase_class.return_value = mock_supabase

            result = await list_tickets(config=mock_config)

            assert result["success"] is True
            assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_list_tickets_with_status_filter(self, mock_config):
        """list_tickets should filter by status."""
        from src.api.inbound_routes import list_tickets

        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.list_tickets.return_value = []
            mock_supabase_class.return_value = mock_supabase

            await list_tickets(status="open", config=mock_config)

            # Verify list_tickets was called with status filter
            mock_supabase.list_tickets.assert_called_once()
            call_kwargs = mock_supabase.list_tickets.call_args.kwargs
            assert call_kwargs.get("status") == "open"

    @pytest.mark.asyncio
    async def test_list_tickets_calculates_stats(self, mock_config):
        """list_tickets should calculate stats from all tickets."""
        from src.api.inbound_routes import list_tickets

        mock_tickets = [
            {"ticket_id": "TKT-001", "status": "open"},
            {"ticket_id": "TKT-002", "status": "open"},
            {"ticket_id": "TKT-003", "status": "resolved"},
        ]

        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.list_tickets.return_value = mock_tickets
            mock_supabase_class.return_value = mock_supabase

            result = await list_tickets(config=mock_config)

            assert result["stats"]["open"] == 2
            assert result["stats"]["resolved"] == 1


# ==================== Get Ticket Details Logic Tests ====================

class TestGetTicketLogic:
    """Test get_ticket endpoint logic with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_get_ticket_returns_ticket(self, mock_config):
        """get_ticket should return ticket details."""
        from src.api.inbound_routes import get_ticket

        mock_ticket = {
            "ticket_id": "TKT-001",
            "subject": "Test Ticket",
            "status": "open",
            "conversation": [{"role": "customer", "content": "Help me"}]
        }

        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            table_mock = create_chainable_mock(mock_ticket)
            mock_supabase.client.table.return_value = table_mock
            mock_supabase.TABLE_TICKETS = "inbound_tickets"
            mock_supabase_class.return_value = mock_supabase

            result = await get_ticket(ticket_id="TKT-001", config=mock_config)

            assert result["success"] is True
            assert result["data"]["ticket_id"] == "TKT-001"

    @pytest.mark.asyncio
    async def test_get_ticket_not_found(self, mock_config):
        """get_ticket should raise 404 when ticket not found."""
        from src.api.inbound_routes import get_ticket
        from fastapi import HTTPException

        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            table_mock = create_chainable_mock(None)
            mock_supabase.client.table.return_value = table_mock
            mock_supabase.TABLE_TICKETS = "inbound_tickets"
            mock_supabase_class.return_value = mock_supabase

            with pytest.raises(HTTPException) as exc_info:
                await get_ticket(ticket_id="NONEXISTENT", config=mock_config)

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_ticket_no_database(self, mock_config):
        """get_ticket should raise 500 when database unavailable."""
        from src.api.inbound_routes import get_ticket
        from fastapi import HTTPException

        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.client = None
            mock_supabase_class.return_value = mock_supabase

            with pytest.raises(HTTPException) as exc_info:
                await get_ticket(ticket_id="TKT-001", config=mock_config)

            assert exc_info.value.status_code == 500


# ==================== Update Ticket Logic Tests ====================

class TestUpdateTicketLogic:
    """Test update_ticket endpoint logic with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_update_ticket_success(self, mock_config):
        """update_ticket should update ticket status."""
        from src.api.inbound_routes import update_ticket, TicketStatusUpdate

        update_data = TicketStatusUpdate(status="resolved")

        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.update_ticket.return_value = True
            table_mock = create_chainable_mock({"ticket_id": "TKT-001", "status": "resolved"})
            mock_supabase.client.table.return_value = table_mock
            mock_supabase.TABLE_TICKETS = "inbound_tickets"
            mock_supabase_class.return_value = mock_supabase

            result = await update_ticket(
                ticket_id="TKT-001",
                update=update_data,
                config=mock_config
            )

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_update_ticket_with_assignment(self, mock_config):
        """update_ticket should update assignment."""
        from src.api.inbound_routes import update_ticket, TicketStatusUpdate

        update_data = TicketStatusUpdate(
            status="in_progress",
            assigned_to="agent@example.com",
            notes="Working on it"
        )

        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.update_ticket.return_value = True
            table_mock = create_chainable_mock({"ticket_id": "TKT-001"})
            mock_supabase.client.table.return_value = table_mock
            mock_supabase.TABLE_TICKETS = "inbound_tickets"
            mock_supabase_class.return_value = mock_supabase

            await update_ticket(
                ticket_id="TKT-001",
                update=update_data,
                config=mock_config
            )

            mock_supabase.update_ticket.assert_called_with(
                ticket_id="TKT-001",
                status="in_progress",
                assigned_to="agent@example.com",
                notes="Working on it"
            )

    @pytest.mark.asyncio
    async def test_update_ticket_failure(self, mock_config):
        """update_ticket should raise 500 on failure."""
        from src.api.inbound_routes import update_ticket, TicketStatusUpdate
        from fastapi import HTTPException

        update_data = TicketStatusUpdate(status="resolved")

        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.update_ticket.return_value = False
            mock_supabase_class.return_value = mock_supabase

            with pytest.raises(HTTPException) as exc_info:
                await update_ticket(
                    ticket_id="TKT-001",
                    update=update_data,
                    config=mock_config
                )

            assert exc_info.value.status_code == 500


# ==================== Reply to Ticket Logic Tests ====================

class TestReplyToTicketLogic:
    """Test reply_to_ticket endpoint logic with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_reply_to_ticket_success(self, mock_config):
        """reply_to_ticket should add reply to conversation."""
        from src.api.inbound_routes import reply_to_ticket, TicketReply

        reply = TicketReply(message="Thank you for your inquiry.")

        existing_ticket = {
            "ticket_id": "TKT-001",
            "status": "open",
            "conversation": [{"role": "customer", "content": "Help me"}]
        }

        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            table_mock = create_chainable_mock(existing_ticket)
            mock_supabase.client.table.return_value = table_mock
            mock_supabase.TABLE_TICKETS = "inbound_tickets"
            mock_supabase_class.return_value = mock_supabase

            result = await reply_to_ticket(
                ticket_id="TKT-001",
                reply=reply,
                config=mock_config
            )

            assert result["success"] is True
            assert result["message"] == "Reply added"
            # Conversation should have 2 items now
            assert len(result["conversation"]) == 2

    @pytest.mark.asyncio
    async def test_reply_to_ticket_not_found(self, mock_config):
        """reply_to_ticket should raise 404 when ticket not found."""
        from src.api.inbound_routes import reply_to_ticket, TicketReply
        from fastapi import HTTPException

        reply = TicketReply(message="Thank you")

        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            table_mock = create_chainable_mock(None)
            mock_supabase.client.table.return_value = table_mock
            mock_supabase.TABLE_TICKETS = "inbound_tickets"
            mock_supabase_class.return_value = mock_supabase

            with pytest.raises(HTTPException) as exc_info:
                await reply_to_ticket(
                    ticket_id="NONEXISTENT",
                    reply=reply,
                    config=mock_config
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_reply_updates_status_to_in_progress(self, mock_config):
        """reply_to_ticket should update status from open to in_progress."""
        from src.api.inbound_routes import reply_to_ticket, TicketReply

        reply = TicketReply(message="Working on it")

        existing_ticket = {
            "ticket_id": "TKT-001",
            "status": "open",
            "conversation": []
        }

        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            table_mock = create_chainable_mock(existing_ticket)
            mock_supabase.client.table.return_value = table_mock
            mock_supabase.TABLE_TICKETS = "inbound_tickets"
            mock_supabase_class.return_value = mock_supabase

            await reply_to_ticket(
                ticket_id="TKT-001",
                reply=reply,
                config=mock_config
            )

            # Check that update was called with in_progress status
            update_calls = table_mock.update.call_args_list
            assert len(update_calls) > 0


# ==================== Stats Endpoint Logic Tests ====================

class TestInboundStatsLogic:
    """Test get_inbound_stats endpoint logic with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_get_stats_returns_stats(self, mock_config):
        """get_inbound_stats should return calculated stats."""
        from src.api.inbound_routes import get_inbound_stats

        mock_tickets = [
            {"status": "open"},
            {"status": "open"},
            {"status": "in_progress"},
            {"status": "resolved"},
            {"status": "closed"},
        ]

        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            table_mock = create_chainable_mock(mock_tickets)
            mock_supabase.client.table.return_value = table_mock
            mock_supabase.TABLE_TICKETS = "inbound_tickets"
            mock_supabase_class.return_value = mock_supabase

            result = await get_inbound_stats(config=mock_config)

            assert result["success"] is True
            assert result["data"]["total"] == 5
            assert result["data"]["open"] == 2
            assert result["data"]["in_progress"] == 1
            assert result["data"]["resolved"] == 1
            assert result["data"]["closed"] == 1

    @pytest.mark.asyncio
    async def test_get_stats_empty_when_no_database(self, mock_config):
        """get_inbound_stats should return zeros when database unavailable."""
        from src.api.inbound_routes import get_inbound_stats

        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.client = None
            mock_supabase_class.return_value = mock_supabase

            result = await get_inbound_stats(config=mock_config)

            assert result["success"] is True
            assert result["data"]["total"] == 0
            assert result["data"]["open"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_empty_tickets(self, mock_config):
        """get_inbound_stats should handle empty ticket list."""
        from src.api.inbound_routes import get_inbound_stats

        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            table_mock = create_chainable_mock([])
            mock_supabase.client.table.return_value = table_mock
            mock_supabase.TABLE_TICKETS = "inbound_tickets"
            mock_supabase_class.return_value = mock_supabase

            result = await get_inbound_stats(config=mock_config)

            assert result["success"] is True
            assert result["data"]["total"] == 0


# ==================== Tenant Isolation Tests ====================

class TestTenantIsolation:
    """Test tenant isolation in inbound routes."""

    @pytest.mark.asyncio
    async def test_get_ticket_filters_by_tenant(self, mock_config):
        """get_ticket should filter by tenant_id."""
        from src.api.inbound_routes import get_ticket

        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            table_mock = create_chainable_mock({"ticket_id": "TKT-001"})
            mock_supabase.client.table.return_value = table_mock
            mock_supabase.TABLE_TICKETS = "inbound_tickets"
            mock_supabase_class.return_value = mock_supabase

            await get_ticket(ticket_id="TKT-001", config=mock_config)

            # Verify eq was called with tenant_id
            eq_calls = table_mock.eq.call_args_list
            tenant_filter_found = any(
                call.args == ('tenant_id', 'test_tenant')
                for call in eq_calls
            )
            assert tenant_filter_found, "Tenant ID filter not applied"

    @pytest.mark.asyncio
    async def test_update_ticket_filters_by_tenant(self, mock_config):
        """update_ticket should filter by tenant_id."""
        from src.api.inbound_routes import update_ticket, TicketStatusUpdate

        update_data = TicketStatusUpdate(status="resolved")

        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.update_ticket.return_value = True
            table_mock = create_chainable_mock({"ticket_id": "TKT-001"})
            mock_supabase.client.table.return_value = table_mock
            mock_supabase.TABLE_TICKETS = "inbound_tickets"
            mock_supabase_class.return_value = mock_supabase

            await update_ticket(
                ticket_id="TKT-001",
                update=update_data,
                config=mock_config
            )

            # Verify eq was called with tenant_id
            eq_calls = table_mock.eq.call_args_list
            tenant_filter_found = any(
                call.args == ('tenant_id', 'test_tenant')
                for call in eq_calls
            )
            assert tenant_filter_found, "Tenant ID filter not applied"

    @pytest.mark.asyncio
    async def test_get_stats_filters_by_tenant(self, mock_config):
        """get_inbound_stats should filter by tenant_id."""
        from src.api.inbound_routes import get_inbound_stats

        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            table_mock = create_chainable_mock([])
            mock_supabase.client.table.return_value = table_mock
            mock_supabase.TABLE_TICKETS = "inbound_tickets"
            mock_supabase_class.return_value = mock_supabase

            await get_inbound_stats(config=mock_config)

            # Verify eq was called with tenant_id
            eq_calls = table_mock.eq.call_args_list
            tenant_filter_found = any(
                call.args == ('tenant_id', 'test_tenant')
                for call in eq_calls
            )
            assert tenant_filter_found, "Tenant ID filter not applied"


# ==================== Error Handling Tests ====================

class TestErrorHandling:
    """Test error handling in inbound routes."""

    @pytest.mark.asyncio
    async def test_list_tickets_handles_exception(self, mock_config):
        """list_tickets should handle exceptions gracefully."""
        from src.api.inbound_routes import list_tickets
        from fastapi import HTTPException

        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.list_tickets.side_effect = Exception("Database error")
            mock_supabase_class.return_value = mock_supabase

            with pytest.raises(HTTPException) as exc_info:
                await list_tickets(config=mock_config)

            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_get_ticket_handles_exception(self, mock_config):
        """get_ticket should handle exceptions gracefully."""
        from src.api.inbound_routes import get_ticket
        from fastapi import HTTPException

        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.client.table.side_effect = Exception("Database error")
            mock_supabase_class.return_value = mock_supabase

            with pytest.raises(HTTPException) as exc_info:
                await get_ticket(ticket_id="TKT-001", config=mock_config)

            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_reply_no_database(self, mock_config):
        """reply_to_ticket should raise 500 when database unavailable."""
        from src.api.inbound_routes import reply_to_ticket, TicketReply
        from fastapi import HTTPException

        reply = TicketReply(message="Thank you")

        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.client = None
            mock_supabase_class.return_value = mock_supabase

            with pytest.raises(HTTPException) as exc_info:
                await reply_to_ticket(
                    ticket_id="TKT-001",
                    reply=reply,
                    config=mock_config
                )

            assert exc_info.value.status_code == 500


# ==================== Conversation Tests ====================

class TestConversationHandling:
    """Test conversation handling in ticket operations."""

    @pytest.mark.asyncio
    async def test_reply_adds_agent_role(self, mock_config):
        """reply_to_ticket should add reply with agent role."""
        from src.api.inbound_routes import reply_to_ticket, TicketReply

        reply = TicketReply(message="Agent response")

        existing_ticket = {
            "ticket_id": "TKT-001",
            "status": "open",
            "conversation": []
        }

        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            table_mock = create_chainable_mock(existing_ticket)
            mock_supabase.client.table.return_value = table_mock
            mock_supabase.TABLE_TICKETS = "inbound_tickets"
            mock_supabase_class.return_value = mock_supabase

            result = await reply_to_ticket(
                ticket_id="TKT-001",
                reply=reply,
                config=mock_config
            )

            # Check conversation has agent role
            assert result["conversation"][0]["role"] == "agent"
            assert result["conversation"][0]["content"] == "Agent response"

    @pytest.mark.asyncio
    async def test_get_ticket_includes_conversation(self, mock_config):
        """get_ticket should include conversation history."""
        from src.api.inbound_routes import get_ticket

        mock_ticket = {
            "ticket_id": "TKT-001",
            "subject": "Test",
            "status": "open",
            "conversation": [
                {"role": "customer", "content": "Help"},
                {"role": "agent", "content": "Sure"}
            ]
        }

        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            table_mock = create_chainable_mock(mock_ticket)
            mock_supabase.client.table.return_value = table_mock
            mock_supabase.TABLE_TICKETS = "inbound_tickets"
            mock_supabase_class.return_value = mock_supabase

            result = await get_ticket(ticket_id="TKT-001", config=mock_config)

            assert "conversation" in result["data"]
            assert len(result["data"]["conversation"]) == 2

    @pytest.mark.asyncio
    async def test_conversation_from_metadata_fallback(self, mock_config):
        """get_ticket should fallback to metadata.conversation."""
        from src.api.inbound_routes import get_ticket

        mock_ticket = {
            "ticket_id": "TKT-001",
            "subject": "Test",
            "status": "open",
            "conversation": None,
            "metadata": {
                "conversation": [{"role": "customer", "content": "Help"}]
            }
        }

        with patch('src.tools.supabase_tool.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            table_mock = create_chainable_mock(mock_ticket)
            mock_supabase.client.table.return_value = table_mock
            mock_supabase.TABLE_TICKETS = "inbound_tickets"
            mock_supabase_class.return_value = mock_supabase

            result = await get_ticket(ticket_id="TKT-001", config=mock_config)

            assert len(result["data"]["conversation"]) == 1
