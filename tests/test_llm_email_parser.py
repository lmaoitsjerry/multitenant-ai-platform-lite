"""
LLM Email Parser Unit Tests

Tests for LLMEmailParser with mocked OpenAI calls.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


@pytest.fixture
def mock_config():
    """Create a mock ClientConfig."""
    config = MagicMock()
    config.destination_names = ["Zanzibar", "Mauritius", "Maldives", "Seychelles"]
    config.destinations = [
        {"name": "Zanzibar", "code": "zanzibar"},
        {"name": "Mauritius", "code": "mauritius"},
        {"name": "Maldives", "code": "maldives"},
        {"name": "Seychelles", "code": "seychelles"}
    ]
    return config


class TestLLMEmailParserInit:
    """Tests for LLMEmailParser initialization."""

    def test_stores_config(self, mock_config):
        """Should store config reference."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('src.agents.universal_email_parser.UniversalEmailParser'):
                from src.agents.llm_email_parser import LLMEmailParser

                parser = LLMEmailParser(mock_config)

                assert parser.config is mock_config

    def test_loads_destinations(self, mock_config):
        """Should load destinations from config."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('src.agents.universal_email_parser.UniversalEmailParser'):
                from src.agents.llm_email_parser import LLMEmailParser

                parser = LLMEmailParser(mock_config)

                assert parser.destinations == ["Zanzibar", "Mauritius", "Maldives", "Seychelles"]

    def test_creates_fallback_parser(self, mock_config):
        """Should create fallback parser."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('src.agents.universal_email_parser.UniversalEmailParser') as MockFallback:
                mock_fallback = MagicMock()
                MockFallback.return_value = mock_fallback

                from src.agents.llm_email_parser import LLMEmailParser

                parser = LLMEmailParser(mock_config)

                MockFallback.assert_called_once_with(mock_config)
                assert parser.fallback_parser is mock_fallback

    def test_reads_openai_api_key_from_env(self, mock_config):
        """Should read OPENAI_API_KEY from environment."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key-123'}):
            with patch('src.agents.universal_email_parser.UniversalEmailParser'):
                from src.agents.llm_email_parser import LLMEmailParser

                parser = LLMEmailParser(mock_config)

                assert parser.openai_api_key == 'test-key-123'

    def test_handles_missing_api_key(self, mock_config):
        """Should handle missing API key gracefully."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('src.agents.universal_email_parser.UniversalEmailParser'):
                from src.agents.llm_email_parser import LLMEmailParser

                parser = LLMEmailParser(mock_config)

                assert parser.openai_api_key is None


class TestLLMEmailParserParse:
    """Tests for parse method."""

    @pytest.fixture
    def parser(self, mock_config):
        """Create parser instance."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('src.agents.universal_email_parser.UniversalEmailParser') as MockFallback:
                mock_fallback = MagicMock()
                mock_fallback.parse.return_value = {
                    'destination': 'Zanzibar',
                    'adults': 2,
                    'children': 0,
                    'name': 'Test User',
                    'email': 'test@example.com'
                }
                MockFallback.return_value = mock_fallback

                from src.agents.llm_email_parser import LLMEmailParser

                return LLMEmailParser(mock_config)

    def test_parse_returns_dict(self, parser):
        """parse should always return a dict."""
        result = parser.parse("Hello world", "Test subject")

        assert isinstance(result, dict)

    def test_uses_fallback_when_no_api_key(self, parser):
        """Should use fallback parser when no API key."""
        result = parser.parse("Trip to Zanzibar", "Inquiry")

        assert result['parse_method'] == 'fallback'
        parser.fallback_parser.parse.assert_called_once()

    def test_uses_fallback_on_llm_failure(self, mock_config):
        """Should fall back when LLM parsing fails."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('src.agents.universal_email_parser.UniversalEmailParser') as MockFallback:
                mock_fallback = MagicMock()
                mock_fallback.parse.return_value = {'destination': 'Mauritius'}
                MockFallback.return_value = mock_fallback

                from src.agents.llm_email_parser import LLMEmailParser

                parser = LLMEmailParser(mock_config)
                parser._parse_with_llm = MagicMock(side_effect=Exception("LLM failed"))

                result = parser.parse("Test email", "Subject")

                assert result['parse_method'] == 'fallback'

    def test_uses_llm_when_available(self, mock_config):
        """Should use LLM when API key is set and call succeeds."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('src.agents.universal_email_parser.UniversalEmailParser'):
                from src.agents.llm_email_parser import LLMEmailParser

                parser = LLMEmailParser(mock_config)
                parser._parse_with_llm = MagicMock(return_value={
                    'destination': 'Mauritius',
                    'adults': 2,
                    'children': 1
                })

                result = parser.parse("Trip to Mauritius for 2 adults and 1 child", "Inquiry")

                assert result['parse_method'] == 'llm'
                assert result['destination'] == 'Mauritius'

    def test_falls_back_on_empty_llm_result(self, mock_config):
        """Should fall back when LLM returns empty destination."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('src.agents.universal_email_parser.UniversalEmailParser') as MockFallback:
                mock_fallback = MagicMock()
                mock_fallback.parse.return_value = {'destination': 'Zanzibar'}
                MockFallback.return_value = mock_fallback

                from src.agents.llm_email_parser import LLMEmailParser

                parser = LLMEmailParser(mock_config)
                parser._parse_with_llm = MagicMock(return_value={'destination': None})

                result = parser.parse("Vague email", "Subject")

                assert result['parse_method'] == 'fallback'


class TestNormalizeLLMResult:
    """Tests for _normalize_llm_result method."""

    @pytest.fixture
    def parser(self, mock_config):
        """Create parser instance."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('src.agents.universal_email_parser.UniversalEmailParser'):
                from src.agents.llm_email_parser import LLMEmailParser

                return LLMEmailParser(mock_config)

    def test_normalizes_basic_result(self, parser):
        """Should normalize basic LLM result."""
        llm_result = {
            'destination': 'Zanzibar',
            'adults': 2,
            'children': 0,
            'name': 'John Doe',
            'email': 'john@example.com'
        }

        result = parser._normalize_llm_result(llm_result)

        assert result['destination'] == 'Zanzibar'
        assert result['adults'] == 2
        assert result['children'] == 0
        assert result['name'] == 'John Doe'

    def test_defaults_missing_fields(self, parser):
        """Should provide defaults for missing fields."""
        llm_result = {}

        result = parser._normalize_llm_result(llm_result)

        assert result['adults'] == 2
        assert result['children'] == 0
        assert result['name'] == 'Valued Customer'
        assert result['is_travel_inquiry'] is True

    def test_converts_budget_string_with_r_prefix(self, parser):
        """Should convert budget string with R prefix."""
        llm_result = {'destination': 'Zanzibar', 'budget': 'R50000'}

        result = parser._normalize_llm_result(llm_result)

        assert result['budget'] == 50000

    def test_converts_budget_with_k_suffix(self, parser):
        """Should convert budget with k suffix."""
        llm_result = {'destination': 'Zanzibar', 'budget': '50k'}

        result = parser._normalize_llm_result(llm_result)

        assert result['budget'] == 50000

    def test_converts_budget_with_commas(self, parser):
        """Should handle budget with commas."""
        llm_result = {'destination': 'Zanzibar', 'budget': 'R50,000'}

        result = parser._normalize_llm_result(llm_result)

        assert result['budget'] == 50000

    def test_handles_invalid_budget_gracefully(self, parser):
        """Should handle invalid budget values."""
        llm_result = {'destination': 'Zanzibar', 'budget': 'expensive'}

        result = parser._normalize_llm_result(llm_result)

        assert result['budget'] is None

    def test_handles_numeric_budget(self, parser):
        """Should handle numeric budget values."""
        llm_result = {'destination': 'Zanzibar', 'budget': 75000}

        result = parser._normalize_llm_result(llm_result)

        assert result['budget'] == 75000

    def test_sets_total_budget_when_budget_present(self, parser):
        """Should set total_budget for compatibility."""
        llm_result = {'destination': 'Zanzibar', 'budget': 50000}

        result = parser._normalize_llm_result(llm_result)

        assert result['total_budget'] == 50000

    def test_maps_non_matching_destination(self, parser):
        """Should map non-matching destination to closest."""
        llm_result = {'destination': 'Zanzbar'}  # Typo

        result = parser._normalize_llm_result(llm_result)

        # Should find closest match
        assert result['destination'] in parser.destinations

    def test_preserves_children_ages(self, parser):
        """Should preserve children_ages array."""
        llm_result = {
            'destination': 'Mauritius',
            'children': 2,
            'children_ages': [5, 8]
        }

        result = parser._normalize_llm_result(llm_result)

        assert result['children_ages'] == [5, 8]

    def test_converts_adults_to_int(self, parser):
        """Should convert adults to int."""
        llm_result = {'destination': 'Zanzibar', 'adults': '3'}

        result = parser._normalize_llm_result(llm_result)

        assert result['adults'] == 3
        assert isinstance(result['adults'], int)


class TestFindClosestDestination:
    """Tests for _find_closest_destination method."""

    @pytest.fixture
    def parser(self, mock_config):
        """Create parser instance."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('src.agents.universal_email_parser.UniversalEmailParser'):
                from src.agents.llm_email_parser import LLMEmailParser

                return LLMEmailParser(mock_config)

    def test_exact_match(self, parser):
        """Should return exact match."""
        result = parser._find_closest_destination("Zanzibar")

        assert result == "Zanzibar"

    def test_case_insensitive_match(self, parser):
        """Should match case-insensitively."""
        result = parser._find_closest_destination("zanzibar")

        assert result == "Zanzibar"

    def test_typo_correction(self, parser):
        """Should correct minor typos."""
        result = parser._find_closest_destination("Zanzbar")

        assert result == "Zanzibar"

    def test_partial_match(self, parser):
        """Should match partial destinations."""
        result = parser._find_closest_destination("Mauritius Island")

        assert result == "Mauritius"

    def test_returns_first_destination_for_no_match(self, parser):
        """Should return first destination when no good match."""
        result = parser._find_closest_destination("Paris")

        assert result == parser.destinations[0]

    def test_handles_empty_input(self, parser):
        """Should handle empty input."""
        result = parser._find_closest_destination("")

        assert result == parser.destinations[0]

    def test_handles_none_input(self, parser):
        """Should handle None input."""
        result = parser._find_closest_destination(None)

        assert result == parser.destinations[0]

    def test_handles_empty_destinations(self, mock_config):
        """Should handle empty destinations list."""
        mock_config.destination_names = []
        mock_config.destinations = []

        with patch.dict('os.environ', {}, clear=True):
            with patch('src.agents.universal_email_parser.UniversalEmailParser'):
                from src.agents.llm_email_parser import LLMEmailParser

                parser = LLMEmailParser(mock_config)
                result = parser._find_closest_destination("Zanzibar")

                assert result == "Unknown"


class TestParseWithLLM:
    """Tests for _parse_with_llm method."""

    @pytest.fixture
    def parser_with_key(self, mock_config):
        """Create parser with API key."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('src.agents.universal_email_parser.UniversalEmailParser'):
                from src.agents.llm_email_parser import LLMEmailParser

                return LLMEmailParser(mock_config)

    def test_returns_none_on_api_error(self, parser_with_key):
        """Should return None on API error."""
        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = Exception("API Error")
            mock_openai_class.return_value = mock_client

            result = parser_with_key._parse_with_llm("Test email")

            assert result is None

    def test_returns_none_on_invalid_json(self, parser_with_key):
        """Should return None on invalid JSON response."""
        with patch('openai.OpenAI') as mock_openai_class:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "not valid json"

            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_class.return_value = mock_client

            result = parser_with_key._parse_with_llm("Test email")

            assert result is None

    def test_normalizes_successful_response(self, parser_with_key):
        """Should normalize successful LLM response."""
        with patch('openai.OpenAI') as mock_openai_class:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"destination": "Mauritius", "adults": 2}'

            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_class.return_value = mock_client

            result = parser_with_key._parse_with_llm("Test email")

            assert result is not None
            assert result['destination'] == 'Mauritius'

    def test_truncates_long_input(self, parser_with_key):
        """Should truncate long input to 4000 chars."""
        with patch('openai.OpenAI') as mock_openai_class:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"destination": "Zanzibar"}'

            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_class.return_value = mock_client

            long_text = "x" * 5000
            parser_with_key._parse_with_llm(long_text)

            # Check that the user message was truncated
            call_args = mock_client.chat.completions.create.call_args
            messages = call_args.kwargs['messages']
            user_content = messages[1]['content']
            assert len(user_content) <= 4000
