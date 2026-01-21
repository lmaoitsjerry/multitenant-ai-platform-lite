"""
OpenAI Mock Infrastructure

Reusable mock classes and helpers for testing OpenAI-dependent code:
- MockToolCall - Simulates function/tool call objects
- MockOpenAIMessage - Simulates response.choices[0].message structure
- MockOpenAIChoice - Simulates a completion choice
- MockOpenAIResponse - Simulates client.chat.completions.create() response
- MockOpenAIClient - Full client mock with pattern-based responses
- Factory functions and preset generators

Usage:
    from tests.fixtures.openai_fixtures import (
        create_mock_openai_client,
        create_direct_response,
        create_tool_call_response,
        MockOpenAIClient,
    )

    # Create mock client with pattern-based responses
    mock_client = create_mock_openai_client()
    mock_client.set_response_for_pattern("mauritius", create_search_response("mauritius hotels"))
    mock_client.set_response_for_pattern("quote", create_quote_response("Maldives"))

    # Use in tests with patch
    with patch('src.agents.helpdesk_agent.openai.OpenAI', return_value=mock_client):
        agent = HelpdeskAgent()
        result = agent.chat("Tell me about Mauritius hotels")
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from unittest.mock import MagicMock


# ==================== Mock Classes ====================

class MockToolFunction:
    """
    Simulates the function object within a tool call.

    Attributes:
        name: Name of the function to call
        arguments: JSON string of function arguments

    Example:
        func = MockToolFunction("search_knowledge_base", {"query": "hotels"})
        assert func.name == "search_knowledge_base"
        assert json.loads(func.arguments) == {"query": "hotels"}
    """

    def __init__(self, name: str, arguments: Union[Dict, str]):
        self.name = name
        # Store arguments as JSON string (how OpenAI returns them)
        if isinstance(arguments, dict):
            self.arguments = json.dumps(arguments)
        else:
            self.arguments = arguments

    def __repr__(self) -> str:
        return f"MockToolFunction(name={self.name!r}, arguments={self.arguments!r})"


class MockToolCall:
    """
    Simulates a tool/function call from OpenAI response.

    OpenAI returns tool calls with structure:
        tool_call.id - Unique identifier
        tool_call.type - Always "function"
        tool_call.function.name - Function name
        tool_call.function.arguments - JSON string of args

    Example:
        tool_call = MockToolCall(
            id="call_abc123",
            function_name="search_knowledge_base",
            arguments={"query": "mauritius hotels"}
        )
        assert tool_call.function.name == "search_knowledge_base"
    """

    def __init__(
        self,
        id: str = None,
        function_name: str = "",
        arguments: Union[Dict, str] = None,
        type: str = "function"
    ):
        self.id = id or f"call_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        self.type = type
        self.function = MockToolFunction(function_name, arguments or {})

    def __repr__(self) -> str:
        return f"MockToolCall(id={self.id!r}, function={self.function.name!r})"


class MockOpenAIMessage:
    """
    Simulates response.choices[0].message structure.

    OpenAI chat completion messages have:
        - role: "assistant" (for responses)
        - content: Text content (may be None if tool_calls present)
        - tool_calls: List of tool calls (or None)

    Example:
        # Direct response (no tools)
        msg = MockOpenAIMessage(content="Hello! How can I help?")
        assert msg.content == "Hello! How can I help?"
        assert msg.tool_calls is None

        # Tool call response
        msg = MockOpenAIMessage(tool_calls=[
            MockToolCall(function_name="search_knowledge_base", arguments={"query": "hotels"})
        ])
        assert msg.content is None
        assert len(msg.tool_calls) == 1
    """

    def __init__(
        self,
        content: Optional[str] = None,
        role: str = "assistant",
        tool_calls: Optional[List[MockToolCall]] = None
    ):
        self.content = content
        self.role = role
        self.tool_calls = tool_calls

    def __repr__(self) -> str:
        if self.tool_calls:
            tools = [tc.function.name for tc in self.tool_calls]
            return f"MockOpenAIMessage(role={self.role!r}, tool_calls={tools})"
        return f"MockOpenAIMessage(role={self.role!r}, content={self.content[:50] if self.content else None!r}...)"


class MockOpenAIChoice:
    """
    Simulates a completion choice from OpenAI response.

    Each response has choices[] with:
        - index: Position in choices list
        - message: The assistant message
        - finish_reason: "stop", "tool_calls", etc.

    Example:
        choice = MockOpenAIChoice(
            message=MockOpenAIMessage(content="Hello!"),
            finish_reason="stop"
        )
        assert choice.message.content == "Hello!"
    """

    def __init__(
        self,
        message: MockOpenAIMessage = None,
        index: int = 0,
        finish_reason: str = "stop"
    ):
        self.index = index
        self.message = message or MockOpenAIMessage()
        self.finish_reason = finish_reason


class MockOpenAIUsage:
    """
    Simulates token usage in OpenAI response.

    Attributes:
        prompt_tokens: Tokens in the input
        completion_tokens: Tokens in the output
        total_tokens: Sum of prompt + completion
    """

    def __init__(
        self,
        prompt_tokens: int = 100,
        completion_tokens: int = 50,
        total_tokens: int = None
    ):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens or (prompt_tokens + completion_tokens)


class MockOpenAIResponse:
    """
    Simulates client.chat.completions.create() response.

    Full OpenAI chat completion response with:
        - id: Unique response identifier
        - model: Model used (e.g., "gpt-4o-mini")
        - choices: List of completion choices
        - usage: Token usage statistics

    Example:
        response = MockOpenAIResponse(
            content="Hello! I'm Zara from Zorah Travel.",
            model="gpt-4o-mini"
        )
        assert response.choices[0].message.content == "Hello! I'm Zara from Zorah Travel."
    """

    def __init__(
        self,
        content: Optional[str] = None,
        tool_calls: Optional[List[MockToolCall]] = None,
        model: str = "gpt-4o-mini",
        id: str = None,
        finish_reason: str = None,
        usage: MockOpenAIUsage = None
    ):
        self.id = id or f"chatcmpl-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        self.model = model
        self.object = "chat.completion"
        self.created = int(datetime.now().timestamp())

        # Determine finish reason
        if finish_reason:
            _finish_reason = finish_reason
        elif tool_calls:
            _finish_reason = "tool_calls"
        else:
            _finish_reason = "stop"

        # Build message
        message = MockOpenAIMessage(
            content=content,
            tool_calls=tool_calls
        )

        self.choices = [
            MockOpenAIChoice(
                message=message,
                index=0,
                finish_reason=_finish_reason
            )
        ]

        self.usage = usage or MockOpenAIUsage()


class MockChatCompletions:
    """
    Simulates client.chat.completions with create() method.

    Supports pattern-based response matching:
    - Examines message content for keyword patterns
    - Returns matching response or default

    Example:
        completions = MockChatCompletions()
        completions.set_response_for_pattern("mauritius", create_search_response("mauritius"))
        response = completions.create(messages=[{"role": "user", "content": "hotels in mauritius"}])
    """

    def __init__(self, default_response: MockOpenAIResponse = None):
        self._default_response = default_response or MockOpenAIResponse(
            content="I'm here to help! What would you like to know?"
        )
        self._pattern_responses: Dict[str, MockOpenAIResponse] = {}
        self._call_history: List[Dict[str, Any]] = []
        self._error_on_next_call: Optional[Exception] = None

    def set_response_for_pattern(self, pattern: str, response: MockOpenAIResponse) -> None:
        """
        Set response for messages matching a pattern.

        Args:
            pattern: String pattern to match in message content (case-insensitive)
            response: MockOpenAIResponse to return when pattern matches
        """
        self._pattern_responses[pattern.lower()] = response

    def set_error_on_next_call(self, error: Exception) -> None:
        """
        Make the next create() call raise an error.

        Args:
            error: Exception to raise on next call
        """
        self._error_on_next_call = error

    def create(
        self,
        model: str = "gpt-4o-mini",
        messages: List[Dict] = None,
        tools: List[Dict] = None,
        tool_choice: str = "auto",
        temperature: float = 0.7,
        max_tokens: int = 800,
        **kwargs
    ) -> MockOpenAIResponse:
        """
        Simulate chat.completions.create() call.

        Records call parameters and returns appropriate mock response.
        """
        # Record the call
        self._call_history.append({
            "model": model,
            "messages": messages,
            "tools": tools,
            "tool_choice": tool_choice,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timestamp": datetime.now().isoformat()
        })

        # Check for programmed error
        if self._error_on_next_call:
            error = self._error_on_next_call
            self._error_on_next_call = None
            raise error

        # Extract message content to match patterns
        messages = messages or []
        all_content = " ".join(
            m.get("content", "") for m in messages
            if isinstance(m.get("content"), str)
        ).lower()

        # Find matching pattern
        for pattern, response in self._pattern_responses.items():
            if pattern in all_content:
                return response

        # Return default response
        return self._default_response

    def get_call_history(self) -> List[Dict[str, Any]]:
        """Return list of all create() calls made."""
        return self._call_history.copy()

    def get_last_call(self) -> Optional[Dict[str, Any]]:
        """Return the most recent create() call."""
        return self._call_history[-1] if self._call_history else None

    def clear_history(self) -> None:
        """Clear call history."""
        self._call_history.clear()


class MockChat:
    """Wrapper to provide client.chat.completions structure."""

    def __init__(self, completions: MockChatCompletions = None):
        self.completions = completions or MockChatCompletions()


class MockOpenAIClient:
    """
    Full mock of openai.OpenAI client.

    Supports:
    - client.chat.completions.create() method signature
    - Pattern-based response matching
    - Call history tracking for assertions
    - Error injection for testing error handling

    Example:
        client = MockOpenAIClient()
        client.chat.completions.set_response_for_pattern(
            "mauritius",
            create_search_response("mauritius hotels")
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "hotels in mauritius"}]
        )
        assert response.choices[0].message.tool_calls[0].function.name == "search_knowledge_base"
    """

    def __init__(self, default_response: MockOpenAIResponse = None, api_key: str = None):
        self._completions = MockChatCompletions(default_response)
        self.chat = MockChat(self._completions)
        self.api_key = api_key

    def set_response_for_pattern(self, pattern: str, response: MockOpenAIResponse) -> None:
        """Convenience method to set pattern response."""
        self._completions.set_response_for_pattern(pattern, response)

    def set_error_on_next_call(self, error: Exception) -> None:
        """Convenience method to inject error."""
        self._completions.set_error_on_next_call(error)

    def get_call_history(self) -> List[Dict[str, Any]]:
        """Get history of all API calls."""
        return self._completions.get_call_history()


# ==================== Factory Functions ====================

def create_mock_openai_client(
    default_response: MockOpenAIResponse = None,
    preset_patterns: Dict[str, MockOpenAIResponse] = None,
    api_key: str = "test-openai-key"
) -> MockOpenAIClient:
    """
    Create a configured MockOpenAIClient.

    Args:
        default_response: Default response for unmatched patterns
        preset_patterns: Dict of pattern -> response to pre-configure
        api_key: API key value (for testing key validation)

    Returns:
        Configured MockOpenAIClient instance

    Example:
        # Basic client
        client = create_mock_openai_client()

        # Client with pre-configured patterns
        client = create_mock_openai_client(
            preset_patterns={
                "mauritius": create_search_response("mauritius hotels"),
                "quote": create_quote_response("Maldives"),
            }
        )
    """
    client = MockOpenAIClient(default_response, api_key=api_key)

    if preset_patterns:
        for pattern, response in preset_patterns.items():
            client.set_response_for_pattern(pattern, response)

    return client


# ==================== Response Generators ====================

def create_direct_response(content: str, model: str = "gpt-4o-mini") -> MockOpenAIResponse:
    """
    Create a response with direct text content (no tool calls).

    Args:
        content: Text content for the assistant response
        model: Model name to include in response

    Returns:
        MockOpenAIResponse with text content, no tool_calls

    Example:
        response = create_direct_response("Hello! I'm Zara, how can I help?")
        assert response.choices[0].message.content == "Hello! I'm Zara, how can I help?"
        assert response.choices[0].message.tool_calls is None
    """
    return MockOpenAIResponse(content=content, model=model)


def create_tool_call_response(
    tool_name: str,
    arguments: Dict[str, Any],
    tool_id: str = None,
    model: str = "gpt-4o-mini"
) -> MockOpenAIResponse:
    """
    Create a response that triggers a tool/function call.

    Args:
        tool_name: Name of the function to call
        arguments: Dictionary of function arguments
        tool_id: Optional specific tool call ID
        model: Model name to include in response

    Returns:
        MockOpenAIResponse with tool_calls, no direct content

    Example:
        response = create_tool_call_response(
            "search_knowledge_base",
            {"query": "mauritius hotels", "query_type": "hotel_info"}
        )
        assert response.choices[0].message.tool_calls[0].function.name == "search_knowledge_base"
    """
    tool_call = MockToolCall(
        id=tool_id,
        function_name=tool_name,
        arguments=arguments
    )

    return MockOpenAIResponse(
        tool_calls=[tool_call],
        model=model
    )


def create_search_response(query: str, query_type: str = "general") -> MockOpenAIResponse:
    """
    Create a preset response for search_knowledge_base tool.

    Args:
        query: The search query
        query_type: Type of query (hotel_info, pricing, destination, comparison, general)

    Returns:
        MockOpenAIResponse that triggers search_knowledge_base tool

    Example:
        response = create_search_response("mauritius hotels", "hotel_info")
    """
    return create_tool_call_response(
        "search_knowledge_base",
        {"query": query, "query_type": query_type}
    )


def create_quote_response(
    destination: str,
    check_in: str = None,
    check_out: str = None,
    adults: int = 2,
    children: int = 0
) -> MockOpenAIResponse:
    """
    Create a preset response for start_quote tool.

    Args:
        destination: Travel destination
        check_in: Optional check-in date (YYYY-MM-DD)
        check_out: Optional check-out date (YYYY-MM-DD)
        adults: Number of adults (default: 2)
        children: Number of children (default: 0)

    Returns:
        MockOpenAIResponse that triggers start_quote tool

    Example:
        response = create_quote_response("Maldives", "2026-03-01", "2026-03-08")
    """
    args = {
        "destination": destination,
        "adults": adults,
        "children": children
    }
    if check_in:
        args["check_in"] = check_in
    if check_out:
        args["check_out"] = check_out

    return create_tool_call_response("start_quote", args)


def create_platform_help_response(topic: str, question: str = None) -> MockOpenAIResponse:
    """
    Create a preset response for platform_help tool.

    Args:
        topic: Platform topic (quotes, invoices, crm, pipeline, clients, settings, pricing, general)
        question: Optional specific question

    Returns:
        MockOpenAIResponse that triggers platform_help tool

    Example:
        response = create_platform_help_response("quotes", "How do I create a quote?")
    """
    args = {"topic": topic}
    if question:
        args["question"] = question

    return create_tool_call_response("platform_help", args)


def create_route_to_human_response(
    reason: str,
    priority: str = "medium",
    context: str = None
) -> MockOpenAIResponse:
    """
    Create a preset response for route_to_human tool.

    Args:
        reason: Why human support is needed
        priority: Priority level (low, medium, high)
        context: Optional conversation context summary

    Returns:
        MockOpenAIResponse that triggers route_to_human tool

    Example:
        response = create_route_to_human_response("Customer complaint about billing", "high")
    """
    args = {
        "reason": reason,
        "priority": priority
    }
    if context:
        args["context"] = context

    return create_tool_call_response("route_to_human", args)


# ==================== Error Generators ====================

def create_openai_api_error(
    message: str = "API Error",
    error_type: str = "APIError"
) -> Exception:
    """
    Create an exception simulating OpenAI API errors.

    Args:
        message: Error message
        error_type: Type of error

    Returns:
        Exception that can be used with set_error_on_next_call()

    Example:
        client = create_mock_openai_client()
        client.set_error_on_next_call(create_openai_api_error("Rate limit exceeded"))
    """
    error = Exception(message)
    error.type = error_type
    return error


def create_rate_limit_error() -> Exception:
    """Create a rate limit exceeded error."""
    return create_openai_api_error(
        "Rate limit exceeded. Please try again later.",
        "RateLimitError"
    )


def create_invalid_api_key_error() -> Exception:
    """Create an invalid API key error."""
    return create_openai_api_error(
        "Incorrect API key provided",
        "AuthenticationError"
    )


# ==================== Multi-turn Conversation Helpers ====================

class MockConversationClient(MockOpenAIClient):
    """
    Extended mock client for multi-turn conversation testing.

    Supports sequential responses for conversation flows:
    - First call returns response A
    - Second call returns response B
    - etc.

    Example:
        client = MockConversationClient([
            create_direct_response("Hello! Where would you like to travel?"),
            create_quote_response("Mauritius"),
            create_direct_response("Great! I've started your quote.")
        ])
    """

    def __init__(self, responses: List[MockOpenAIResponse] = None):
        super().__init__()
        self._sequential_responses = responses or []
        self._call_index = 0

        # Override the completions create method
        original_create = self._completions.create

        def sequential_create(*args, **kwargs):
            # Record the call
            original_create(*args, **kwargs)  # Just for history recording

            if self._call_index < len(self._sequential_responses):
                response = self._sequential_responses[self._call_index]
                self._call_index += 1
                return response

            # Fall back to pattern matching if we've exhausted sequential responses
            return original_create(*args, **kwargs)

        self._completions.create = sequential_create

    def reset_sequence(self) -> None:
        """Reset the conversation sequence to the beginning."""
        self._call_index = 0
