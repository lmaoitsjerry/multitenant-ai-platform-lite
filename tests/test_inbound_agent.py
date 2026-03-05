"""
Tests for Inbound Agent - Customer-facing conversational AI

Tests cover:
- KnowledgeBaseRAG initialization and search
- InboundAgent initialization with GenAI client
- Chat functionality with and without GenAI
- Information extraction from customer messages
- Quote readiness checking
- Conversation management

Uses GenAI mock fixtures for deterministic testing without real API calls.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, mock_open
from typing import Dict, Any

# Import the module to test
from src.agents.inbound_agent import InboundAgent, KnowledgeBaseRAG

# Import GenAI fixtures
from tests.fixtures.genai_fixtures import (
    MockGenAIClient,
    MockGenAIResponse,
    create_mock_genai_client,
    TRAVEL_CONSULTANT_RESPONSES,
    FALLBACK_RESPONSE,
)


# ==================== Fixtures ====================

@pytest.fixture
def mock_config():
    """Create a mock ClientConfig for testing."""
    config = MagicMock()
    config.client_id = "test_tenant"
    config.company_name = "Test Travel Agency"
    config.destination_names = ["Zanzibar", "Maldives", "Mauritius", "Seychelles"]
    config.currency = "USD"
    config.timezone = "UTC"
    config.gcp_project_id = "test-project"
    config.gcp_region = "us-central1"

    # Mock get_prompt_path to return a non-existent path
    mock_path = MagicMock()
    mock_path.exists.return_value = False
    config.get_prompt_path.return_value = mock_path

    return config


@pytest.fixture
def mock_genai_client():
    """Create a configured mock GenAI client."""
    return create_mock_genai_client(
        responses=TRAVEL_CONSULTANT_RESPONSES,
        default_response=FALLBACK_RESPONSE
    )


@pytest.fixture
def sample_chunks():
    """Sample knowledge base chunks for testing."""
    return [
        {
            "content": "Zanzibar has beautiful white sand beaches and crystal clear waters.",
            "visibility": "public",
            "document_id": "doc1",
            "category": "destinations"
        },
        {
            "content": "Visa on arrival available for most nationalities visiting Tanzania.",
            "visibility": "public",
            "document_id": "doc2",
            "category": "travel_info"
        },
        {
            "content": "Internal pricing guide: markup 20% on all packages.",
            "visibility": "private",
            "document_id": "doc3",
            "category": "internal"
        }
    ]


# ==================== TestInboundAgentInit ====================

class TestInboundAgentInit:
    """Tests for InboundAgent initialization."""

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_init_with_config(self, mock_config):
        """Initializes with ClientConfig and session_id."""
        agent = InboundAgent(mock_config, "session123")

        assert agent.config == mock_config
        assert agent.session_id == "session123"
        assert agent.conversation_history == []
        assert agent.collected_info == {}
        assert agent.genai_client is None  # GENAI_AVAILABLE is False

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_init_creates_rag(self, mock_config):
        """RAG instance created with config.client_id."""
        agent = InboundAgent(mock_config, "session123")

        assert agent.rag is not None
        assert isinstance(agent.rag, KnowledgeBaseRAG)
        assert agent.rag.client_id == "test_tenant"

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', True)
    @patch('src.agents.inbound_agent.genai')
    def test_init_genai_client_success(self, mock_genai, mock_config):
        """GenAI client created when available."""
        mock_client = create_mock_genai_client()
        mock_genai.Client.return_value = mock_client

        agent = InboundAgent(mock_config, "session123")

        assert agent.genai_client is not None
        mock_genai.Client.assert_called_once_with(
            vertexai=True,
            project="test-project",
            location="us-central1"
        )

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', True)
    @patch('src.agents.inbound_agent.genai')
    def test_init_genai_client_failure(self, mock_genai, mock_config):
        """Handles GenAI init errors gracefully."""
        mock_genai.Client.side_effect = Exception("Connection failed")

        # Should not raise - just logs error
        agent = InboundAgent(mock_config, "session123")

        assert agent.genai_client is None

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_build_system_prompt(self, mock_config):
        """System prompt includes company name, destinations, currency."""
        agent = InboundAgent(mock_config, "session123")

        prompt = agent.system_prompt

        assert "Test Travel Agency" in prompt
        assert "Zanzibar" in prompt
        assert "Maldives" in prompt
        assert "USD" in prompt
        assert "UTC" in prompt


# ==================== TestInboundAgentChat ====================

class TestInboundAgentChat:
    """Tests for InboundAgent.chat() method."""

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', True)
    @patch('src.agents.inbound_agent.genai')
    def test_chat_with_genai(self, mock_genai, mock_config):
        """Normal conversation flow with GenAI."""
        mock_client = create_mock_genai_client(
            responses={"zanzibar": "Zanzibar is amazing for beach lovers!"}
        )
        mock_genai.Client.return_value = mock_client

        agent = InboundAgent(mock_config, "session123")
        result = agent.chat("Tell me about Zanzibar")

        assert result["success"] is True
        assert "response" in result
        assert "session_id" in result
        assert result["session_id"] == "session123"

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_chat_without_genai(self, mock_config):
        """Fallback response when GenAI unavailable."""
        agent = InboundAgent(mock_config, "session123")
        result = agent.chat("Hello")

        assert result["success"] is True
        assert "apologize" in result["response"].lower() or "email" in result["response"].lower()

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', True)
    @patch('src.agents.inbound_agent.genai')
    def test_chat_updates_history(self, mock_genai, mock_config):
        """Conversation history tracks messages."""
        mock_client = create_mock_genai_client()
        mock_genai.Client.return_value = mock_client

        agent = InboundAgent(mock_config, "session123")

        agent.chat("Hello")
        agent.chat("I want to visit Zanzibar")

        history = agent.get_conversation_history()

        # 2 user messages + 2 assistant responses
        assert len(history) == 4
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[1]["role"] == "assistant"
        assert history[2]["role"] == "user"
        assert history[2]["content"] == "I want to visit Zanzibar"

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', True)
    @patch('src.agents.inbound_agent.genai')
    def test_chat_with_customer_info(self, mock_genai, mock_config):
        """Pre-filled customer info is used."""
        mock_client = create_mock_genai_client()
        mock_genai.Client.return_value = mock_client

        agent = InboundAgent(mock_config, "session123")

        customer_info = {"name": "John", "email": "john@example.com"}
        agent.chat("Hello", customer_info=customer_info)

        collected = agent.get_collected_info()
        assert collected["name"] == "John"
        assert collected["email"] == "john@example.com"

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', True)
    @patch('src.agents.inbound_agent.genai')
    def test_chat_extracts_info(self, mock_genai, mock_config):
        """Info extracted from messages."""
        mock_client = create_mock_genai_client()
        mock_genai.Client.return_value = mock_client

        agent = InboundAgent(mock_config, "session123")
        agent.chat("I want to visit Zanzibar with 2 adults")

        collected = agent.get_collected_info()
        assert collected.get("destination") == "Zanzibar"
        assert collected.get("adults") == 2

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', True)
    @patch('src.agents.inbound_agent.genai')
    def test_chat_with_rag_context(self, mock_genai, mock_config):
        """RAG results injected into prompt."""
        mock_client = create_mock_genai_client()
        mock_genai.Client.return_value = mock_client

        agent = InboundAgent(mock_config, "session123")

        # Mock RAG search to return results
        agent.rag.search = MagicMock(return_value=[
            {"content": "Zanzibar beaches info", "score": 0.8, "document_id": "doc1", "category": "destinations"}
        ])

        agent.chat("Tell me about Zanzibar beaches")

        # Check that RAG search was called
        agent.rag.search.assert_called()

        # Check that the GenAI model was called (with RAG context in prompt)
        call_history = mock_client.get_call_history()
        assert len(call_history) > 0

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', True)
    @patch('src.agents.inbound_agent.genai')
    def test_chat_error_handling(self, mock_genai, mock_config):
        """Returns error response on exception."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API Error")
        mock_genai.Client.return_value = mock_client

        agent = InboundAgent(mock_config, "session123")
        result = agent.chat("Hello")

        assert result["success"] is False
        assert "error" in result
        assert "apologize" in result["response"].lower()


# ==================== TestInfoExtraction ====================

class TestInfoExtraction:
    """Tests for _extract_info_from_message method."""

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_extract_destination(self, mock_config):
        """Extracts destination from message."""
        agent = InboundAgent(mock_config, "session123")

        agent._extract_info_from_message("I want to go to Zanzibar")

        assert agent.collected_info.get("destination") == "Zanzibar"

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_extract_adults(self, mock_config):
        """Extracts number of adults."""
        agent = InboundAgent(mock_config, "session123")

        agent._extract_info_from_message("We are 3 adults")

        assert agent.collected_info.get("adults") == 3

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_extract_adults_with_people(self, mock_config):
        """Extracts adults from 'people' variant."""
        agent = InboundAgent(mock_config, "session123")

        agent._extract_info_from_message("There will be 4 people")

        assert agent.collected_info.get("adults") == 4

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_extract_children(self, mock_config):
        """Extracts number of children."""
        agent = InboundAgent(mock_config, "session123")

        agent._extract_info_from_message("We have 2 children")

        assert agent.collected_info.get("children") == 2

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_extract_children_with_kid(self, mock_config):
        """Extracts children from 'kid' variant."""
        agent = InboundAgent(mock_config, "session123")

        agent._extract_info_from_message("We have 1 kid")

        assert agent.collected_info.get("children") == 1

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_extract_email(self, mock_config):
        """Extracts email address."""
        agent = InboundAgent(mock_config, "session123")

        agent._extract_info_from_message("My email is john.doe@example.com")

        assert agent.collected_info.get("email") == "john.doe@example.com"

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_extract_name_my_name_is(self, mock_config):
        """Extracts name from 'my name is X' pattern."""
        agent = InboundAgent(mock_config, "session123")

        agent._extract_info_from_message("Hi, my name is John")

        assert agent.collected_info.get("name") == "John"

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_extract_name_im(self, mock_config):
        """Extracts name from 'I'm X' pattern."""
        agent = InboundAgent(mock_config, "session123")

        agent._extract_info_from_message("I'm Sarah and I want to book")

        assert agent.collected_info.get("name") == "Sarah"

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_extract_name_call_me(self, mock_config):
        """Extracts name from 'call me X' pattern."""
        agent = InboundAgent(mock_config, "session123")

        agent._extract_info_from_message("You can call me Mike")

        assert agent.collected_info.get("name") == "Mike"

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_extract_multiple_fields(self, mock_config):
        """Extracts multiple fields from one message."""
        agent = InboundAgent(mock_config, "session123")

        message = "I'm John, we are 2 adults with 1 child, email john@test.com, interested in Maldives"
        agent._extract_info_from_message(message)

        assert agent.collected_info.get("name") == "John"
        assert agent.collected_info.get("adults") == 2
        assert agent.collected_info.get("children") == 1
        assert agent.collected_info.get("email") == "john@test.com"
        assert agent.collected_info.get("destination") == "Maldives"

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_no_extraction_when_no_match(self, mock_config):
        """Doesn't extract when no patterns match."""
        agent = InboundAgent(mock_config, "session123")

        agent._extract_info_from_message("What are your opening hours?")

        assert agent.collected_info == {}


# ==================== TestQuoteReadiness ====================

class TestQuoteReadiness:
    """Tests for quote readiness checking."""

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_ready_for_quote_with_destination_and_email(self, mock_config):
        """True when required fields present."""
        agent = InboundAgent(mock_config, "session123")
        agent.collected_info = {
            "destination": "Zanzibar",
            "email": "test@example.com"
        }

        assert agent._check_ready_for_quote() is True

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_not_ready_missing_destination(self, mock_config):
        """False without destination."""
        agent = InboundAgent(mock_config, "session123")
        agent.collected_info = {
            "email": "test@example.com"
        }

        assert agent._check_ready_for_quote() is False

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_not_ready_missing_email(self, mock_config):
        """False without email."""
        agent = InboundAgent(mock_config, "session123")
        agent.collected_info = {
            "destination": "Zanzibar"
        }

        assert agent._check_ready_for_quote() is False

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_generate_quote_request(self, mock_config):
        """Returns formatted quote request dict."""
        agent = InboundAgent(mock_config, "session123")
        agent.collected_info = {
            "destination": "Maldives",
            "email": "customer@example.com",
            "name": "John Doe",
            "adults": 2,
            "children": 1,
            "children_ages": [5],
            "budget": "$5000"
        }

        quote_request = agent.generate_quote_request()

        assert quote_request is not None
        assert quote_request["destination"] == "Maldives"
        assert quote_request["email"] == "customer@example.com"
        assert quote_request["name"] == "John Doe"
        assert quote_request["adults"] == 2
        assert quote_request["children"] == 1
        assert quote_request["source"] == "chat"
        assert quote_request["session_id"] == "session123"

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_generate_quote_request_not_ready(self, mock_config):
        """Returns None when not ready."""
        agent = InboundAgent(mock_config, "session123")
        agent.collected_info = {
            "destination": "Zanzibar"
            # Missing email
        }

        quote_request = agent.generate_quote_request()

        assert quote_request is None

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_generate_quote_request_defaults(self, mock_config):
        """Uses default values for optional fields."""
        agent = InboundAgent(mock_config, "session123")
        agent.collected_info = {
            "destination": "Seychelles",
            "email": "test@example.com"
            # No name, adults, children
        }

        quote_request = agent.generate_quote_request()

        assert quote_request["name"] == "Customer"  # Default
        assert quote_request["adults"] == 2  # Default
        assert quote_request["children"] == 0  # Default


# ==================== TestConversationManagement ====================

class TestConversationManagement:
    """Tests for conversation and info management methods."""

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_get_collected_info(self, mock_config):
        """Returns copy of collected info."""
        agent = InboundAgent(mock_config, "session123")
        agent.collected_info = {"destination": "Bali", "adults": 2}

        info = agent.get_collected_info()

        assert info == {"destination": "Bali", "adults": 2}
        # Verify it's a copy
        info["destination"] = "Modified"
        assert agent.collected_info["destination"] == "Bali"

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_set_customer_info(self, mock_config):
        """Updates collected info."""
        agent = InboundAgent(mock_config, "session123")
        agent.collected_info = {"destination": "Zanzibar"}

        agent.set_customer_info({"name": "Jane", "email": "jane@example.com"})

        assert agent.collected_info["destination"] == "Zanzibar"
        assert agent.collected_info["name"] == "Jane"
        assert agent.collected_info["email"] == "jane@example.com"

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_get_conversation_history(self, mock_config):
        """Returns copy of history."""
        agent = InboundAgent(mock_config, "session123")
        agent.conversation_history = [
            {"role": "user", "content": "Hello", "timestamp": "2026-01-21T10:00:00"}
        ]

        history = agent.get_conversation_history()

        assert len(history) == 1
        assert history[0]["role"] == "user"
        # Verify it's a copy
        history.append({"role": "assistant", "content": "Hi"})
        assert len(agent.conversation_history) == 1


# ==================== TestSystemPrompt ====================

class TestSystemPrompt:
    """Additional tests for system prompt building."""

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_default_prompt_when_template_missing(self, mock_config):
        """Uses default prompt when template file not found."""
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_config.get_prompt_path.return_value = mock_path

        agent = InboundAgent(mock_config, "session123")

        # Should use default prompt
        assert "Test Travel Agency" in agent.system_prompt
        assert "friendly and professional travel consultant" in agent.system_prompt

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_prompt_includes_all_destinations(self, mock_config):
        """System prompt includes all destination names."""
        mock_config.destination_names = ["Zanzibar", "Maldives", "Mauritius", "Seychelles", "Bali"]

        agent = InboundAgent(mock_config, "session123")

        for dest in mock_config.destination_names:
            assert dest in agent.system_prompt

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_prompt_loads_from_file(self, mock_config, tmp_path):
        """Loads custom prompt from template file."""
        # Create a custom prompt file
        prompt_file = tmp_path / "inbound_prompt.txt"
        prompt_file.write_text("Custom travel agent prompt for {company_name}")

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = "Custom travel agent prompt for {company_name}"
        mock_config.get_prompt_path.return_value = mock_path

        agent = InboundAgent(mock_config, "session123")

        assert "Custom travel agent prompt" in agent.system_prompt


# ==================== TestChatGenAI ====================

class TestChatGenAI:
    """Tests for _chat_genai internal method."""

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', True)
    @patch('src.agents.inbound_agent.genai')
    def test_chat_genai_includes_system_prompt(self, mock_genai, mock_config):
        """Conversation starts with system prompt."""
        mock_client = create_mock_genai_client()
        mock_genai.Client.return_value = mock_client

        agent = InboundAgent(mock_config, "session123")
        agent.chat("Hello")

        call_history = mock_client.get_call_history()
        assert len(call_history) == 1
        # System prompt should be at the start
        assert "Test Travel Agency" in call_history[0]

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', True)
    @patch('src.agents.inbound_agent.genai')
    def test_chat_genai_includes_collected_info(self, mock_genai, mock_config):
        """Collected info added to conversation context."""
        mock_client = create_mock_genai_client()
        mock_genai.Client.return_value = mock_client

        agent = InboundAgent(mock_config, "session123")
        agent.collected_info = {"destination": "Zanzibar", "adults": 2}
        agent.chat("What's the price?")

        call_history = mock_client.get_call_history()
        assert "Zanzibar" in call_history[0] or "destination" in call_history[0]

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', True)
    @patch('src.agents.inbound_agent.genai')
    def test_chat_genai_limits_history(self, mock_genai, mock_config):
        """Only last 10 messages included in context."""
        mock_client = create_mock_genai_client()
        mock_genai.Client.return_value = mock_client

        agent = InboundAgent(mock_config, "session123")

        # Add 15 messages to history with unique identifiers
        for i in range(15):
            agent.conversation_history.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"HistoryMsg_{i}",  # Use unique prefix to avoid false matches
                "timestamp": datetime.now().isoformat()
            })

        agent.chat("Final message")

        call_history = mock_client.get_call_history()
        # Should not include first 5 messages (HistoryMsg_0 through HistoryMsg_4)
        # because we have 15 history items and only last 10 are included
        # After adding "Final message", history is 16, but _chat_genai only uses last 10
        assert "HistoryMsg_0" not in call_history[0]
        assert "HistoryMsg_4" not in call_history[0]
        # Should include later messages
        assert "HistoryMsg_14" in call_history[0]


# ==================== TestRAGIntegration ====================

class TestRAGIntegration:
    """Tests for RAG context injection in chat."""

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', True)
    @patch('src.agents.inbound_agent.genai')
    def test_rag_context_formatting(self, mock_genai, mock_config):
        """RAG results formatted correctly in prompt."""
        mock_client = create_mock_genai_client()
        mock_genai.Client.return_value = mock_client

        agent = InboundAgent(mock_config, "session123")

        # Mock RAG to return results
        agent.rag.search = MagicMock(return_value=[
            {"content": "Zanzibar has Stone Town, a UNESCO site.", "score": 0.85, "document_id": "doc1", "category": "culture"},
            {"content": "Best time to visit is June-October.", "score": 0.75, "document_id": "doc2", "category": "weather"}
        ])

        agent.chat("Tell me about Zanzibar culture")

        call_history = mock_client.get_call_history()
        # Check RAG context is included
        assert "KNOWLEDGE BASE" in call_history[0] or "Stone Town" in call_history[0]

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', True)
    @patch('src.agents.inbound_agent.genai')
    def test_no_rag_context_when_empty(self, mock_genai, mock_config):
        """No RAG section when search returns empty."""
        mock_client = create_mock_genai_client()
        mock_genai.Client.return_value = mock_client

        agent = InboundAgent(mock_config, "session123")

        # Mock RAG to return empty
        agent.rag.search = MagicMock(return_value=[])

        agent.chat("Random question")

        call_history = mock_client.get_call_history()
        # Should not include RAG header
        assert "RELEVANT KNOWLEDGE BASE INFORMATION" not in call_history[0]


# ==================== TestEdgeCases ====================

class TestEdgeCases:
    """Edge case tests for robustness."""

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_empty_message(self, mock_config):
        """Handles empty message gracefully."""
        agent = InboundAgent(mock_config, "session123")
        result = agent.chat("")

        assert result["success"] is True
        assert "response" in result

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_special_characters_in_message(self, mock_config):
        """Handles special characters in message."""
        agent = InboundAgent(mock_config, "session123")
        result = agent.chat("What about prices? $$$! @#%^&*()")

        assert result["success"] is True

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_unicode_message(self, mock_config):
        """Handles unicode characters."""
        agent = InboundAgent(mock_config, "session123")
        result = agent.chat("Hello! I want to visit Zanzibar")

        assert result["success"] is True

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_very_long_message(self, mock_config):
        """Handles very long messages."""
        agent = InboundAgent(mock_config, "session123")
        long_message = "I want to travel " * 1000
        result = agent.chat(long_message)

        assert result["success"] is True

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_destination_case_insensitive(self, mock_config):
        """Destination extraction is case-insensitive."""
        agent = InboundAgent(mock_config, "session123")

        agent._extract_info_from_message("I want to visit ZANZIBAR")

        assert agent.collected_info.get("destination") == "Zanzibar"

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_multiple_destinations_first_wins(self, mock_config):
        """When multiple destinations mentioned, first one wins."""
        agent = InboundAgent(mock_config, "session123")

        agent._extract_info_from_message("I'm choosing between Zanzibar and Maldives")

        # Zanzibar comes first in destination_names list, and is mentioned first
        assert agent.collected_info.get("destination") == "Zanzibar"

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_email_extraction_various_formats(self, mock_config):
        """Extracts various email formats."""
        agent = InboundAgent(mock_config, "session123")

        test_cases = [
            ("Contact me at user@domain.com", "user@domain.com"),
            ("Email: test.user@company.co.uk", "test.user@company.co.uk"),
            ("user123@test-domain.org is my email", "user123@test-domain.org"),
        ]

        for message, expected_email in test_cases:
            agent.collected_info = {}  # Reset
            agent._extract_info_from_message(message)
            assert agent.collected_info.get("email") == expected_email, f"Failed for: {message}"


class TestSearchExceptions:
    """Tests for exception handling in search."""

    def test_search_exception_handling(self, sample_chunks):
        """Handles exceptions during search gracefully."""
        import numpy as np

        rag = KnowledgeBaseRAG("test")

        # Mock index to raise exception during search
        mock_index = MagicMock()
        mock_index.search.side_effect = Exception("FAISS search failed")
        rag._index = mock_index
        rag._chunks = sample_chunks

        # Mock embeddings
        mock_embeddings = MagicMock()
        mock_embeddings.encode.return_value = np.array([[0.1] * 384], dtype=np.float32)
        rag._embeddings = mock_embeddings

        # Should return empty list on exception
        results = rag.search("test query")
        assert results == []

    def test_search_invalid_index(self, sample_chunks):
        """Handles invalid indices from FAISS search."""
        import numpy as np

        rag = KnowledgeBaseRAG("test")

        # Mock index to return invalid indices
        mock_index = MagicMock()
        mock_index.search.return_value = (
            np.array([[0.5, 1.0]]),
            np.array([[-1, 100]])  # Invalid indices
        )
        rag._index = mock_index
        rag._chunks = sample_chunks  # Only 3 chunks

        mock_embeddings = MagicMock()
        mock_embeddings.encode.return_value = np.array([[0.1] * 384], dtype=np.float32)
        rag._embeddings = mock_embeddings

        results = rag.search("test", visibility="public")
        # Should skip invalid indices
        assert len(results) == 0


class TestPromptExceptions:
    """Tests for exception handling in prompt building."""

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_prompt_path_exception(self, mock_config):
        """Handles exception when getting prompt path."""
        mock_config.get_prompt_path.side_effect = Exception("Path error")

        agent = InboundAgent(mock_config, "session123")

        # Should use default prompt
        assert "travel consultant" in agent.system_prompt.lower()


class TestRAGKnowledgeFormatting:
    """Tests for RAG context formatting edge cases."""

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', True)
    @patch('src.agents.inbound_agent.genai')
    def test_rag_context_with_multiple_results(self, mock_genai, mock_config):
        """Formats multiple RAG results correctly."""
        mock_client = create_mock_genai_client()
        mock_genai.Client.return_value = mock_client

        agent = InboundAgent(mock_config, "session123")

        # Mock RAG to return multiple results
        agent.rag.search = MagicMock(return_value=[
            {"content": "Result 1 content", "score": 0.95, "document_id": "doc1", "category": "info"},
            {"content": "Result 2 content", "score": 0.85, "document_id": "doc2", "category": "info"},
            {"content": "Result 3 content", "score": 0.75, "document_id": "doc3", "category": "info"},
        ])

        agent.chat("Tell me about destinations")

        call_history = mock_client.get_call_history()
        # Should include source numbers
        assert "[Source 1]" in call_history[0] or "Result 1" in call_history[0]

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', True)
    @patch('src.agents.inbound_agent.genai')
    def test_rag_content_truncation(self, mock_genai, mock_config):
        """Truncates very long RAG content."""
        mock_client = create_mock_genai_client()
        mock_genai.Client.return_value = mock_client

        agent = InboundAgent(mock_config, "session123")

        # Mock RAG with very long content (>800 chars)
        long_content = "A" * 1000
        agent.rag.search = MagicMock(return_value=[
            {"content": long_content, "score": 0.9, "document_id": "doc1", "category": "info"}
        ])

        agent.chat("Query")

        call_history = mock_client.get_call_history()
        # Content should be truncated
        assert long_content not in call_history[0]


class TestSearchKnowledgeBase:
    """Tests for _search_knowledge_base method."""

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_search_knowledge_base_no_results(self, mock_config):
        """Returns empty string when no results."""
        agent = InboundAgent(mock_config, "session123")

        agent.rag.search = MagicMock(return_value=[])

        result = agent._search_knowledge_base("query")
        assert result == ""

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_search_knowledge_base_with_results(self, mock_config):
        """Returns formatted context string."""
        agent = InboundAgent(mock_config, "session123")

        agent.rag.search = MagicMock(return_value=[
            {"content": "Zanzibar info", "score": 0.8, "document_id": "doc1", "category": "dest"}
        ])

        result = agent._search_knowledge_base("zanzibar")

        assert "KNOWLEDGE BASE" in result
        assert "Zanzibar info" in result
        assert "0.8" in result


# ==================== NEW TESTS: Classification, Auto-Reply, Routing, Context ====================

class TestEmailClassificationExtraction:
    """Tests for classifying/extracting intent from customer messages."""

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_extract_destination_maldives(self, mock_config):
        """Should extract Maldives destination."""
        agent = InboundAgent(mock_config, "session123")
        agent._extract_info_from_message("I want to visit the Maldives please")
        assert agent.collected_info.get("destination") == "Maldives"

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_extract_destination_mauritius(self, mock_config):
        """Should extract Mauritius destination."""
        agent = InboundAgent(mock_config, "session123")
        agent._extract_info_from_message("Tell me about Mauritius holidays")
        assert agent.collected_info.get("destination") == "Mauritius"

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_extract_destination_seychelles(self, mock_config):
        """Should extract Seychelles destination."""
        agent = InboundAgent(mock_config, "session123")
        agent._extract_info_from_message("We dream of Seychelles")
        assert agent.collected_info.get("destination") == "Seychelles"

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_extract_pax_keyword(self, mock_config):
        """Should extract adults count from 'pax' keyword."""
        agent = InboundAgent(mock_config, "session123")
        agent._extract_info_from_message("Booking for 5 pax")
        assert agent.collected_info.get("adults") == 5

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_extract_name_i_am_pattern(self, mock_config):
        """Should extract name from 'I am X' pattern."""
        agent = InboundAgent(mock_config, "session123")
        agent._extract_info_from_message("I am David and I need a quote")
        assert agent.collected_info.get("name") == "David"

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_extract_name_this_is_pattern(self, mock_config):
        """Should extract name from 'this is X' pattern."""
        agent = InboundAgent(mock_config, "session123")
        agent._extract_info_from_message("Hello, this is Emma calling about a trip")
        assert agent.collected_info.get("name") == "Emma"

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_extract_no_destination_for_unknown(self, mock_config):
        """Should not extract destination for unlisted locations."""
        agent = InboundAgent(mock_config, "session123")
        agent._extract_info_from_message("I want to visit Paris")
        assert agent.collected_info.get("destination") is None


class TestAutoReplyGeneration:
    """Tests for auto-reply generation behavior without GenAI."""

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_fallback_response_without_genai(self, mock_config):
        """Without GenAI, should return polite fallback message."""
        agent = InboundAgent(mock_config, "session123")
        result = agent.chat("I want to book a trip")

        assert result["success"] is True
        assert len(result["response"]) > 0
        # Should suggest alternative contact
        assert "email" in result["response"].lower() or "call" in result["response"].lower()

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', True)
    @patch('src.agents.inbound_agent.genai')
    def test_genai_error_returns_apology(self, mock_genai, mock_config):
        """GenAI API error should return apology response."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("Service down")
        mock_genai.Client.return_value = mock_client

        agent = InboundAgent(mock_config, "session123")
        result = agent.chat("Hello there")

        assert result["success"] is False
        assert "apologize" in result["response"].lower() or "inconvenience" in result["response"].lower()

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', True)
    @patch('src.agents.inbound_agent.genai')
    def test_chat_returns_collected_info(self, mock_genai, mock_config):
        """Chat result should include collected_info dict."""
        mock_client = create_mock_genai_client()
        mock_genai.Client.return_value = mock_client

        agent = InboundAgent(mock_config, "session123")
        agent.collected_info = {"destination": "Zanzibar"}
        result = agent.chat("What hotels do you have?")

        assert "collected_info" in result
        assert result["collected_info"]["destination"] == "Zanzibar"


class TestRoutingDecisions:
    """Tests for routing decisions (ready_for_quote, quote request generation)."""

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_ready_for_quote_returned_in_chat(self, mock_config):
        """Chat response should include ready_for_quote flag."""
        agent = InboundAgent(mock_config, "session123")
        agent.collected_info = {
            "destination": "Zanzibar",
            "email": "test@example.com"
        }
        result = agent.chat("Please send me a quote")

        assert "ready_for_quote" in result
        assert result["ready_for_quote"] is True

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_not_ready_for_quote_returned_in_chat(self, mock_config):
        """Chat should indicate not ready when required fields are missing."""
        agent = InboundAgent(mock_config, "session123")
        result = agent.chat("Hello I need info")

        assert result["ready_for_quote"] is False

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_generate_quote_request_includes_phone(self, mock_config):
        """Quote request should include phone when provided."""
        agent = InboundAgent(mock_config, "session123")
        agent.collected_info = {
            "destination": "Maldives",
            "email": "test@example.com",
            "phone": "+1234567890"
        }

        quote = agent.generate_quote_request()
        assert quote is not None
        assert quote["phone"] == "+1234567890"

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_generate_quote_request_includes_special_requests(self, mock_config):
        """Quote request should include special_requests as message."""
        agent = InboundAgent(mock_config, "session123")
        agent.collected_info = {
            "destination": "Mauritius",
            "email": "test@example.com",
            "special_requests": "Honeymoon package"
        }

        quote = agent.generate_quote_request()
        assert quote is not None
        assert quote["message"] == "Honeymoon package"

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_generate_quote_includes_children_ages(self, mock_config):
        """Quote request should include children_ages list."""
        agent = InboundAgent(mock_config, "session123")
        agent.collected_info = {
            "destination": "Seychelles",
            "email": "test@example.com",
            "children": 2,
            "children_ages": [4, 7]
        }

        quote = agent.generate_quote_request()
        assert quote["children_ages"] == [4, 7]


class TestContextExtraction:
    """Tests for context extraction from multi-turn conversations."""

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', True)
    @patch('src.agents.inbound_agent.genai')
    def test_info_accumulates_across_messages(self, mock_genai, mock_config):
        """Collected info should accumulate across multiple chat messages."""
        mock_client = create_mock_genai_client()
        mock_genai.Client.return_value = mock_client

        agent = InboundAgent(mock_config, "session123")

        agent.chat("I want to visit Zanzibar")
        assert agent.collected_info.get("destination") == "Zanzibar"

        agent.chat("We are 2 adults")
        assert agent.collected_info.get("adults") == 2
        assert agent.collected_info.get("destination") == "Zanzibar"  # Still there

        agent.chat("My email is traveler@test.com")
        assert agent.collected_info.get("email") == "traveler@test.com"
        assert agent.collected_info.get("destination") == "Zanzibar"
        assert agent.collected_info.get("adults") == 2

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_set_customer_info_merges(self, mock_config):
        """set_customer_info should merge without overwriting existing keys."""
        agent = InboundAgent(mock_config, "session123")
        agent.collected_info = {"destination": "Zanzibar"}
        agent.set_customer_info({"email": "crm@example.com", "name": "CRM User"})

        assert agent.collected_info["destination"] == "Zanzibar"
        assert agent.collected_info["email"] == "crm@example.com"
        assert agent.collected_info["name"] == "CRM User"

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', False)
    def test_set_customer_info_overwrites_existing(self, mock_config):
        """set_customer_info should overwrite keys when provided."""
        agent = InboundAgent(mock_config, "session123")
        agent.collected_info = {"name": "Old Name"}
        agent.set_customer_info({"name": "New Name"})

        assert agent.collected_info["name"] == "New Name"

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', True)
    @patch('src.agents.inbound_agent.genai')
    def test_conversation_history_has_timestamps(self, mock_genai, mock_config):
        """Each history entry should have a timestamp."""
        mock_client = create_mock_genai_client()
        mock_genai.Client.return_value = mock_client

        agent = InboundAgent(mock_config, "session123")
        agent.chat("Hello")

        history = agent.get_conversation_history()
        for entry in history:
            assert "timestamp" in entry
            # Verify it parses as ISO format
            datetime.fromisoformat(entry["timestamp"])

    @patch('src.agents.inbound_agent.GENAI_AVAILABLE', True)
    @patch('src.agents.inbound_agent.genai')
    def test_customer_info_passed_to_chat_merged(self, mock_genai, mock_config):
        """customer_info passed to chat() should merge into collected_info."""
        mock_client = create_mock_genai_client()
        mock_genai.Client.return_value = mock_client

        agent = InboundAgent(mock_config, "session123")
        agent.chat("Hello", customer_info={"name": "Prefilled", "budget": "$3000"})

        assert agent.collected_info["name"] == "Prefilled"
        assert agent.collected_info["budget"] == "$3000"


class TestKnowledgeBaseRAGStub:
    """Tests for KnowledgeBaseRAG stub behavior (local index removed)."""

    def test_rag_search_always_returns_empty(self):
        """Stub RAG should always return empty list."""
        rag = KnowledgeBaseRAG("any_tenant")
        result = rag.search("any query", top_k=10, visibility="public")
        assert result == []

    def test_rag_search_with_different_params(self):
        """Stub RAG should return empty regardless of parameters."""
        rag = KnowledgeBaseRAG("test")
        result = rag.search("test", top_k=1, visibility="private", min_score=0.0)
        assert result == []

    def test_rag_client_id_stored(self):
        """RAG should store client_id."""
        rag = KnowledgeBaseRAG("my_tenant")
        assert rag.client_id == "my_tenant"
