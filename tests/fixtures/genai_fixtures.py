"""
Google GenAI (Gemini) Mock Infrastructure

Reusable mock classes for testing Google GenAI (Gemini) dependent code:
- MockGenAIResponse: Simulates genai response with .text attribute
- MockGenAIModel: Simulates model with generate_content method
- MockGenAIModels: Simulates client.models namespace
- MockGenAIClient: Full client mock with pattern-based response matching

Usage:
    from tests.fixtures.genai_fixtures import create_mock_genai_client, MockGenAIClient

    # Create mock client with default response
    mock_client = create_mock_genai_client()

    # Set specific response for content patterns
    mock_client.set_response_for_pattern("zanzibar", "Zanzibar is a beautiful island...")
    mock_client.set_response_for_pattern("maldives", "The Maldives offer pristine beaches...")

    # Use in tests with patch
    with patch('src.agents.inbound_agent.genai.Client', return_value=mock_client):
        agent = InboundAgent(config, 'session123')
        result = agent.chat('Tell me about Zanzibar')
"""

import re
from typing import Dict, List, Optional, Any
from unittest.mock import MagicMock


class MockGenAIResponse:
    """
    Simulates a Google GenAI response object.

    The response is returned by client.models.generate_content() and
    provides access to generated text via the .text attribute.

    Args:
        text: The generated text content
        candidates: Optional list of candidate responses (for advanced scenarios)
        prompt_feedback: Optional feedback about the prompt (for moderation scenarios)

    Attributes:
        text: The primary generated text (shortcut to first candidate)
        candidates: List of generation candidates
        prompt_feedback: Feedback about the prompt

    Example:
        response = MockGenAIResponse("Hello! How can I help you today?")
        assert response.text == "Hello! How can I help you today?"
    """

    def __init__(
        self,
        text: str,
        candidates: List[Dict] = None,
        prompt_feedback: Dict = None
    ):
        self._text = text
        self.candidates = candidates or [{"content": {"parts": [{"text": text}]}}]
        self.prompt_feedback = prompt_feedback

    @property
    def text(self) -> str:
        """Return the generated text content."""
        return self._text

    def __repr__(self) -> str:
        preview = self._text[:50] + "..." if len(self._text) > 50 else self._text
        return f"MockGenAIResponse(text='{preview}')"


class MockGenAIModel:
    """
    Simulates a Google GenAI model that can generate content.

    Supports pattern-based response matching for deterministic testing.
    If no pattern matches, returns a default response.

    Args:
        default_response: Text to return when no pattern matches
        pattern_responses: Dict of pattern -> response text

    Example:
        model = MockGenAIModel(default_response="I can help with that!")
        model.set_response_for_pattern("zanzibar", "Zanzibar has beautiful beaches...")

        response = model.generate_content("Tell me about Zanzibar")
        assert "beaches" in response.text
    """

    def __init__(
        self,
        default_response: str = "Thank you for your inquiry! How can I assist you with your travel plans today?",
        pattern_responses: Dict[str, str] = None
    ):
        self._default_response = default_response
        self._pattern_responses: Dict[str, str] = pattern_responses or {}
        self._call_history: List[str] = []

    def set_response_for_pattern(self, pattern: str, response_text: str) -> None:
        """
        Set a response for content matching a pattern.

        Args:
            pattern: String pattern to match in content (case-insensitive)
            response_text: Text to return when pattern matches
        """
        self._pattern_responses[pattern.lower()] = response_text

    def generate_content(self, contents: str) -> MockGenAIResponse:
        """
        Generate content based on input.

        Args:
            contents: The input prompt/content

        Returns:
            MockGenAIResponse with appropriate text
        """
        self._call_history.append(contents)
        contents_lower = contents.lower()

        # Find matching pattern
        for pattern, response_text in self._pattern_responses.items():
            if pattern in contents_lower:
                return MockGenAIResponse(response_text)

        # No match - return default
        return MockGenAIResponse(self._default_response)

    def get_call_history(self) -> List[str]:
        """Return list of all content passed to generate_content."""
        return self._call_history.copy()

    def clear_history(self) -> None:
        """Clear the call history."""
        self._call_history.clear()


class MockGenAIModels:
    """
    Simulates the client.models namespace of Google GenAI.

    Provides the generate_content method that takes a model name and contents.

    Args:
        model: The MockGenAIModel to delegate to

    Example:
        models = MockGenAIModels()
        response = models.generate_content(model="gemini-2.0-flash-001", contents="Hello")
        assert response.text  # Has generated content
    """

    def __init__(self, model: MockGenAIModel = None):
        self._model = model or MockGenAIModel()
        self._model_calls: Dict[str, List[str]] = {}

    def generate_content(self, model: str, contents: str) -> MockGenAIResponse:
        """
        Generate content using specified model.

        Args:
            model: Model name (e.g., "gemini-2.0-flash-001")
            contents: The input prompt/content

        Returns:
            MockGenAIResponse with generated text
        """
        # Track which models are being called
        if model not in self._model_calls:
            self._model_calls[model] = []
        self._model_calls[model].append(contents)

        return self._model.generate_content(contents)

    def get_model_calls(self, model: str = None) -> Dict[str, List[str]]:
        """
        Get call history, optionally filtered by model.

        Args:
            model: If provided, only return calls for this model

        Returns:
            Dict of model name -> list of content strings
        """
        if model:
            return {model: self._model_calls.get(model, [])}
        return self._model_calls.copy()


class MockGenAIClient:
    """
    Full mock of google.genai.Client.

    Simulates:
    - genai.Client(vertexai=True, project=..., location=...)
    - client.models.generate_content(model=..., contents=...)

    Args:
        project: GCP project ID (stored but not used)
        location: GCP region (stored but not used)
        vertexai: Whether using Vertex AI (stored but not used)
        default_response: Default text for unmatched patterns

    Example:
        client = MockGenAIClient(project="my-project", location="us-central1")
        client.set_response_for_pattern("zanzibar", "Zanzibar is amazing!")

        response = client.models.generate_content(
            model="gemini-2.0-flash-001",
            contents="Tell me about Zanzibar"
        )
        assert "amazing" in response.text
    """

    def __init__(
        self,
        project: str = "test-project",
        location: str = "us-central1",
        vertexai: bool = True,
        default_response: str = None
    ):
        self.project = project
        self.location = location
        self.vertexai = vertexai

        # Create underlying model with default response
        self._model = MockGenAIModel(
            default_response=default_response or "Thank you for your inquiry! How can I assist you with your travel plans today?"
        )

        # Create models namespace
        self.models = MockGenAIModels(self._model)

    def set_response_for_pattern(self, pattern: str, response_text: str) -> None:
        """
        Set a response for content matching a pattern.

        Args:
            pattern: String pattern to match (case-insensitive)
            response_text: Text to return when pattern matches

        Example:
            client.set_response_for_pattern("zanzibar", "Zanzibar is beautiful...")
            client.set_response_for_pattern("quote", "I can prepare a quote for you!")
        """
        self._model.set_response_for_pattern(pattern, response_text)

    def get_call_history(self) -> List[str]:
        """Return list of all prompts sent to the model."""
        return self._model.get_call_history()

    def clear_history(self) -> None:
        """Clear all call history."""
        self._model.clear_history()


# ==================== Factory Functions ====================

def create_mock_genai_client(
    responses: Dict[str, str] = None,
    default_response: str = None,
    project: str = "test-project",
    location: str = "us-central1"
) -> MockGenAIClient:
    """
    Create a configured MockGenAIClient.

    Args:
        responses: Dict of pattern -> response text to pre-configure
        default_response: Default response when no pattern matches
        project: GCP project ID
        location: GCP region

    Returns:
        Configured MockGenAIClient instance

    Example:
        # Basic client
        client = create_mock_genai_client()

        # Client with pre-configured responses
        client = create_mock_genai_client(
            responses={
                "zanzibar": "Zanzibar is a tropical paradise...",
                "maldives": "The Maldives offer luxury overwater villas...",
                "quote": "I can prepare a personalized quote for you!",
            },
            default_response="How can I help with your travel plans?"
        )
    """
    client = MockGenAIClient(
        project=project,
        location=location,
        default_response=default_response
    )

    if responses:
        for pattern, response_text in responses.items():
            client.set_response_for_pattern(pattern, response_text)

    return client


# ==================== Response Helper Generators ====================

def create_travel_inquiry_response(destination: str) -> str:
    """
    Generate a response for destination inquiries.

    Args:
        destination: The destination name

    Returns:
        A realistic travel consultant response about the destination

    Example:
        response = create_travel_inquiry_response("Zanzibar")
        # Returns: "Zanzibar is a wonderful choice! The island offers..."
    """
    responses = {
        "zanzibar": f"{destination} is a wonderful choice! The island offers pristine beaches, rich Swahili culture, and incredible spice tours. When are you thinking of visiting?",
        "maldives": f"The {destination} are truly paradise on Earth! Crystal clear waters, overwater bungalows, and world-class snorkeling. How many travelers will be in your party?",
        "mauritius": f"{destination} combines stunning beaches with lush mountains and rich cultural heritage. It's perfect for honeymooners and families alike. What dates are you considering?",
        "seychelles": f"The {destination} offer some of the world's most beautiful beaches and unique wildlife. Would you like to explore multiple islands or stay at one resort?",
        "bali": f"{destination} is magical! From ancient temples to rice terraces and beautiful beaches. Are you interested in cultural experiences or beach relaxation?",
    }

    # Check if we have a specific response
    dest_lower = destination.lower()
    for key, response in responses.items():
        if key in dest_lower:
            return response

    # Generic response for unknown destinations
    return f"{destination} sounds exciting! I'd love to help you plan your trip there. Could you tell me more about what you're looking for?"


def create_quote_ready_response(info: Dict[str, Any]) -> str:
    """
    Generate a response when quote info is complete.

    Args:
        info: Dict with destination, adults, children, email, etc.

    Returns:
        Response confirming readiness to generate quote

    Example:
        response = create_quote_ready_response({
            "destination": "Maldives",
            "adults": 2,
            "email": "customer@example.com"
        })
        # Returns: "Perfect! I have all the details I need..."
    """
    destination = info.get("destination", "your destination")
    adults = info.get("adults", 2)
    children = info.get("children", 0)
    email = info.get("email", "")

    travelers = f"{adults} adult{'s' if adults > 1 else ''}"
    if children:
        travelers += f" and {children} child{'ren' if children > 1 else ''}"

    return (
        f"Perfect! I have all the details I need to prepare your personalized quote for {destination}. "
        f"That's {travelers}. I'll send the quote to {email} within the next 24 hours. "
        f"Is there anything specific you'd like me to include - perhaps special requests or budget preferences?"
    )


def create_clarification_response(missing_field: str) -> str:
    """
    Generate a response asking for missing information.

    Args:
        missing_field: The field that's missing (destination, email, dates, etc.)

    Returns:
        Friendly question asking for the missing information

    Example:
        response = create_clarification_response("email")
        # Returns: "To send you a personalized quote, may I have your email address?"
    """
    clarifications = {
        "destination": "Which destination are you interested in? We specialize in African and Indian Ocean islands like Zanzibar, Mauritius, the Maldives, and more!",
        "email": "To send you a personalized quote, may I have your email address?",
        "dates": "When are you thinking of traveling? Even approximate dates help us find the best options.",
        "adults": "How many adults will be traveling?",
        "children": "Will any children be joining? If so, what are their ages?",
        "budget": "Do you have a budget range in mind? This helps us tailor the perfect options for you.",
        "name": "May I have your name for the quote?",
    }

    return clarifications.get(
        missing_field.lower(),
        f"Could you please provide your {missing_field}? This will help me create the perfect travel package for you."
    )


def create_greeting_response(company_name: str = "our travel agency") -> str:
    """
    Generate a greeting response for new conversations.

    Args:
        company_name: The travel company name

    Returns:
        Warm greeting to start the conversation

    Example:
        response = create_greeting_response("Safari Dreams")
        # Returns: "Hello! Welcome to Safari Dreams. I'm here to help..."
    """
    return (
        f"Hello! Welcome to {company_name}. I'm here to help you plan an unforgettable journey "
        f"to some of the world's most beautiful destinations. "
        f"Where are you dreaming of traveling to?"
    )


# ==================== Pre-built Response Sets ====================

TRAVEL_CONSULTANT_RESPONSES = {
    "hello": "Hello! Welcome to our travel agency. I'm excited to help you plan your dream vacation! Where are you interested in traveling?",
    "hi": "Hi there! Thanks for reaching out. I'd love to help you discover amazing destinations. What kind of trip are you dreaming of?",
    "zanzibar": "Zanzibar is absolutely magical! Crystal-clear waters, white sandy beaches, and rich Swahili culture. When are you thinking of visiting?",
    "maldives": "The Maldives is pure paradise! Overwater villas, incredible marine life, and ultimate relaxation. How many travelers will be joining?",
    "mauritius": "Mauritius is stunning - beautiful beaches, lush mountains, and wonderful hospitality. It's perfect for couples and families. What dates work for you?",
    "seychelles": "The Seychelles offer pristine nature and some of the world's best beaches! Are you looking for island hopping or a single resort experience?",
    "quote": "I'd be happy to prepare a personalized quote for you! Just need a few details - your email address and preferred travel dates.",
    "price": "Our packages vary based on the resort, room type, and season. To give you accurate pricing, could you share your preferred dates and destination?",
    "thank": "You're very welcome! It's my pleasure to help you plan this trip. Is there anything else you'd like to know?",
    "email": "Great! I'll note that down. Once I have your destination and dates, I'll send a detailed quote to your inbox.",
}

FALLBACK_RESPONSE = (
    "Thank you for your message! I'm here to help you plan an amazing trip. "
    "Could you tell me more about what you're looking for? "
    "I specialize in destinations like Zanzibar, Mauritius, the Maldives, and Seychelles."
)
