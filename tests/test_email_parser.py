"""
Tests for email parsing - both LLM and rule-based

Tests cover:
- LLM parsing success
- Fallback on LLM failure
- Budget normalization
- Traveler extraction
- Empty/malformed email handling
- Long email handling
"""
import pytest
import unittest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.loader import ClientConfig


class MockConfig:
    """Mock ClientConfig for testing"""
    def __init__(self):
        self.client_id = 'test'
        self.destination_names = ['Zanzibar', 'Mauritius', 'Maldives', 'Seychelles', 'Bali']


class TestLLMEmailParser:
    """Test LLM email parser"""

    def test_parse_with_no_api_key_uses_fallback(self):
        """Should use fallback when no API key"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': ''}, clear=False):
            from src.agents.llm_email_parser import LLMEmailParser
            parser = LLMEmailParser(MockConfig())

            result = parser.parse("I want to go to Zanzibar", "Travel inquiry")

            assert result['parse_method'] == 'fallback'
            assert result['destination'] == 'Zanzibar'

    @patch('openai.OpenAI')
    def test_parse_with_llm_success(self, mock_openai):
        """Should parse successfully with LLM"""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            'destination': 'Zanzibar',
            'check_in': '2025-06-15',
            'check_out': '2025-06-22',
            'adults': 2,
            'children': 1,
            'children_ages': [5],
            'budget': 50000,
            'name': 'John Doe',
            'email': 'john@example.com',
            'is_travel_inquiry': True
        })
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}, clear=False):
            from src.agents.llm_email_parser import LLMEmailParser
            parser = LLMEmailParser(MockConfig())

            result = parser.parse("I want to go to Zanzibar in June", "Travel")

            assert result['parse_method'] == 'llm'
            assert result['destination'] == 'Zanzibar'
            assert result['adults'] == 2
            assert result['children'] == 1

    @patch('openai.OpenAI')
    def test_parse_llm_failure_uses_fallback(self, mock_openai):
        """Should use fallback when LLM fails"""
        mock_openai.return_value.chat.completions.create.side_effect = Exception("API Error")

        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}, clear=False):
            from src.agents.llm_email_parser import LLMEmailParser
            parser = LLMEmailParser(MockConfig())

            result = parser.parse("I want to go to Mauritius", "Travel inquiry")

            assert result['parse_method'] == 'fallback'
            # Fallback should still extract destination
            assert result['destination'] in ['Mauritius', 'Zanzibar']  # May match or default

    def test_normalize_budget_formats(self):
        """Should normalize various budget formats"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': ''}, clear=False):
            from src.agents.llm_email_parser import LLMEmailParser
            parser = LLMEmailParser(MockConfig())

            # Test budget normalization
            result1 = parser._normalize_llm_result({'budget': 'R50000'})
            assert result1['budget'] == 50000

            result2 = parser._normalize_llm_result({'budget': '50k'})
            assert result2['budget'] == 50000

            result3 = parser._normalize_llm_result({'budget': 50000})
            assert result3['budget'] == 50000

    def test_find_closest_destination(self):
        """Should find closest matching destination"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': ''}, clear=False):
            from src.agents.llm_email_parser import LLMEmailParser
            parser = LLMEmailParser(MockConfig())

            # Exact match
            assert parser._find_closest_destination('Zanzibar') == 'Zanzibar'

            # Close match
            assert parser._find_closest_destination('Zanziber') == 'Zanzibar'  # Typo

            # Different case
            assert parser._find_closest_destination('zanzibar') == 'Zanzibar'


class TestUniversalEmailParser:
    """Test rule-based fallback parser"""

    def test_extract_destination(self):
        """Should extract destination from text"""
        from src.agents.universal_email_parser import UniversalEmailParser
        parser = UniversalEmailParser(MockConfig())

        result = parser.parse("I want to visit Zanzibar in December", "Quote request")
        assert result['destination'] == 'Zanzibar'

    def test_extract_travelers(self):
        """Should extract adult and child counts"""
        from src.agents.universal_email_parser import UniversalEmailParser
        parser = UniversalEmailParser(MockConfig())

        result = parser.parse("Trip for 2 adults and 3 children", "Family holiday")
        assert result['adults'] == 2
        assert result['children'] == 3

    def test_default_values_for_malformed_email(self):
        """Should return defaults for malformed emails"""
        from src.agents.universal_email_parser import UniversalEmailParser
        parser = UniversalEmailParser(MockConfig())

        result = parser.parse("", "")  # Empty email
        assert result['adults'] == 2  # Default
        assert result['children'] == 0  # Default
        assert result['destination'] in parser.DESTINATIONS  # Some destination


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_body_and_subject(self):
        """Should handle empty email gracefully"""
        from src.agents.universal_email_parser import UniversalEmailParser
        parser = UniversalEmailParser(MockConfig())

        result = parser.parse("", "")
        assert result is not None
        assert 'destination' in result
        assert 'adults' in result

    def test_very_long_email(self):
        """Should handle very long emails"""
        from src.agents.universal_email_parser import UniversalEmailParser
        parser = UniversalEmailParser(MockConfig())

        long_body = "I want to go to Zanzibar. " * 1000
        result = parser.parse(long_body, "Quote")
        assert result['destination'] == 'Zanzibar'

    def test_special_characters_in_email(self):
        """Should handle special characters"""
        from src.agents.universal_email_parser import UniversalEmailParser
        parser = UniversalEmailParser(MockConfig())

        result = parser.parse(
            "Hello! I'd like to visit Zanzibar... budget ~R50,000???",
            "RE: FW: Quote"
        )
        assert result['destination'] == 'Zanzibar'

    def test_llm_parser_with_empty_input(self):
        """Should handle empty input gracefully in LLM parser"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': ''}, clear=False):
            from src.agents.llm_email_parser import LLMEmailParser
            parser = LLMEmailParser(MockConfig())

            result = parser.parse("", "")
            assert result is not None
            assert result['parse_method'] == 'fallback'


if __name__ == '__main__':
    # Run with pytest for new tests
    pytest.main([__file__, '-v'])
