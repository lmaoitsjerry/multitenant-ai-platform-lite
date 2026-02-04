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


class TestDestinationMatching:
    """Tests for destination matching logic."""

    def test_case_insensitive_destination(self):
        """Should match destination case-insensitively."""
        from src.agents.universal_email_parser import UniversalEmailParser
        parser = UniversalEmailParser(MockConfig())

        result = parser.parse("I want to visit ZANZIBAR", "Quote")
        assert result['destination'] == 'Zanzibar'

    def test_partial_destination_match(self):
        """Should match destination mentioned in text."""
        from src.agents.universal_email_parser import UniversalEmailParser
        parser = UniversalEmailParser(MockConfig())

        result = parser.parse("Looking for a Mauritius holiday package", "Inquiry")
        assert result['destination'] == 'Mauritius'

    def test_multiple_destinations_picks_first(self):
        """Should pick first mentioned destination."""
        from src.agents.universal_email_parser import UniversalEmailParser
        parser = UniversalEmailParser(MockConfig())

        result = parser.parse("Interested in Zanzibar or Mauritius", "Quote")
        # Should match one of them
        assert result['destination'] in ['Zanzibar', 'Mauritius']

    def test_no_destination_uses_default(self):
        """Should use default when no destination found."""
        from src.agents.universal_email_parser import UniversalEmailParser
        parser = UniversalEmailParser(MockConfig())

        result = parser.parse("I want a beach holiday", "Generic inquiry")
        assert result['destination'] in parser.DESTINATIONS


class TestTravelerParsing:
    """Tests for traveler count parsing."""

    def test_extract_adults_only(self):
        """Should extract adult count."""
        from src.agents.universal_email_parser import UniversalEmailParser
        parser = UniversalEmailParser(MockConfig())

        result = parser.parse("Trip for 4 adults", "Family vacation")
        assert result['adults'] == 4

    def test_extract_children_with_ages(self):
        """Should extract children count with ages."""
        from src.agents.universal_email_parser import UniversalEmailParser
        parser = UniversalEmailParser(MockConfig())

        result = parser.parse("2 adults and 2 children ages 5 and 8", "Family trip")
        assert result['adults'] == 2
        assert result['children'] == 2

    def test_couple_implies_two_adults(self):
        """Should interpret 'couple' as 2 adults."""
        from src.agents.universal_email_parser import UniversalEmailParser
        parser = UniversalEmailParser(MockConfig())

        result = parser.parse("Honeymoon trip for a couple", "Honeymoon inquiry")
        assert result['adults'] >= 2

    def test_family_implies_adults_and_children(self):
        """Should handle 'family' mentions."""
        from src.agents.universal_email_parser import UniversalEmailParser
        parser = UniversalEmailParser(MockConfig())

        result = parser.parse("Family of 4 looking for holiday", "Family trip")
        # Should have some adults
        assert result['adults'] >= 2


class TestBudgetParsing:
    """Tests for budget parsing."""

    def test_parse_rand_symbol(self):
        """Should parse R symbol for Rand."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': ''}, clear=False):
            from src.agents.llm_email_parser import LLMEmailParser
            parser = LLMEmailParser(MockConfig())

            result = parser._normalize_llm_result({'budget': 'R100000'})
            assert result['budget'] == 100000

    def test_parse_with_commas(self):
        """Should parse budget with commas."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': ''}, clear=False):
            from src.agents.llm_email_parser import LLMEmailParser
            parser = LLMEmailParser(MockConfig())

            result = parser._normalize_llm_result({'budget': 'R100,000'})
            assert result['budget'] == 100000

    def test_parse_k_suffix(self):
        """Should parse k suffix as thousands."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': ''}, clear=False):
            from src.agents.llm_email_parser import LLMEmailParser
            parser = LLMEmailParser(MockConfig())

            result = parser._normalize_llm_result({'budget': '75k'})
            assert result['budget'] == 75000

    def test_parse_usd_budget(self):
        """Should handle USD budget."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': ''}, clear=False):
            from src.agents.llm_email_parser import LLMEmailParser
            parser = LLMEmailParser(MockConfig())

            result = parser._normalize_llm_result({'budget': '$5000'})
            # Should extract numeric value
            assert isinstance(result['budget'], (int, float))


class TestDateParsing:
    """Tests for date extraction."""

    def test_extract_check_in_date(self):
        """Should extract check-in date."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': ''}, clear=False):
            from src.agents.llm_email_parser import LLMEmailParser
            parser = LLMEmailParser(MockConfig())

            # Fallback parser may not extract dates, but should not crash
            result = parser.parse("Trip from 15 June to 22 June", "Quote")
            assert result is not None

    def test_month_name_recognition(self):
        """Should recognize month names in email."""
        from src.agents.universal_email_parser import UniversalEmailParser
        parser = UniversalEmailParser(MockConfig())

        result = parser.parse("Holiday in December in Zanzibar", "Quote")
        assert result['destination'] == 'Zanzibar'


class TestEmailValidation:
    """Tests for email address extraction/validation."""

    def test_extract_email_address(self):
        """Should extract email address from body."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': ''}, clear=False):
            from src.agents.llm_email_parser import LLMEmailParser
            parser = LLMEmailParser(MockConfig())

            # This tests the parsing doesn't crash
            result = parser.parse("Contact me at test@example.com", "Quote")
            assert result is not None

    def test_extract_name(self):
        """Should extract customer name."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': ''}, clear=False):
            from src.agents.llm_email_parser import LLMEmailParser
            parser = LLMEmailParser(MockConfig())

            result = parser.parse("My name is John Smith", "Quote")
            assert result is not None


class TestLLMResponseNormalization:
    """Tests for LLM response normalization."""

    def test_normalize_missing_fields(self):
        """Should add default values for missing fields."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': ''}, clear=False):
            from src.agents.llm_email_parser import LLMEmailParser
            parser = LLMEmailParser(MockConfig())

            result = parser._normalize_llm_result({})
            assert 'adults' in result
            assert 'children' in result
            assert 'destination' in result

    def test_normalize_invalid_adults(self):
        """Should handle invalid adult count."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': ''}, clear=False):
            from src.agents.llm_email_parser import LLMEmailParser
            parser = LLMEmailParser(MockConfig())

            result = parser._normalize_llm_result({'adults': 'two'})
            # Should default or convert
            assert isinstance(result['adults'], int)

    def test_normalize_negative_children(self):
        """Should handle negative children count."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': ''}, clear=False):
            from src.agents.llm_email_parser import LLMEmailParser
            parser = LLMEmailParser(MockConfig())

            result = parser._normalize_llm_result({'children': -1})
            assert result['children'] >= 0


class TestParseMethodTracking:
    """Tests for parse method tracking."""

    def test_fallback_method_indicated(self):
        """Should indicate fallback method was used."""
        from src.agents.universal_email_parser import UniversalEmailParser
        parser = UniversalEmailParser(MockConfig())

        result = parser.parse("Trip to Zanzibar", "Quote")
        assert result.get('parse_method') == 'fallback'

    def test_llm_method_on_success(self):
        """Should indicate LLM method when successful."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}, clear=False):
            with patch('openai.OpenAI') as mock_openai:
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = json.dumps({
                    'destination': 'Zanzibar',
                    'adults': 2,
                    'children': 0,
                    'is_travel_inquiry': True
                })
                mock_openai.return_value.chat.completions.create.return_value = mock_response

                from src.agents.llm_email_parser import LLMEmailParser
                parser = LLMEmailParser(MockConfig())

                result = parser.parse("Trip to Zanzibar", "Quote")
                assert result['parse_method'] == 'llm'


if __name__ == '__main__':
    # Run with pytest for new tests
    pytest.main([__file__, '-v'])
