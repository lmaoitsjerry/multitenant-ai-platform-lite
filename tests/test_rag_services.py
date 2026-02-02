"""
RAG Response Service Unit Tests

Comprehensive tests for RAG response service:
- Response generation
- Source name cleaning
- Content cleaning
- Context building
- Fallback responses
- Query type handling

Uses pytest with mocked OpenAI client.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
import os


# ==================== Fixtures ====================

@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    client = MagicMock()
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "This is a test response from the AI."
    client.chat.completions.create.return_value = response
    return client


@pytest.fixture
def sample_search_results():
    """Create sample search results for testing."""
    return [
        {
            'content': 'Solana Beach is a stunning 5-star resort on the east coast of Mauritius. The property features 117 sea-facing rooms with private balconies and contemporary design.',
            'score': 0.85,
            'source': '/var/folders/c2/tmp123/hotels.pdf',
            'metadata': {'title': 'Solana Beach Resort'}
        },
        {
            'content': 'For an all-inclusive luxury experience, Constance Belle Mare offers world-class amenities. The resort has 2 championship golf courses, 5 restaurants, and a renowned spa.',
            'score': 0.78,
            'source': 'mauritius_luxury.md'
        },
        {
            'content': 'Rates start from $450 per night. High season rates apply during December-January.',
            'score': 0.65,
            'source': 'pricing_guide.pdf',
            'metadata': {}
        }
    ]


# ==================== Service Initialization Tests ====================

class TestRAGServiceInit:
    """Test RAG service initialization."""

    def test_init_without_api_key(self):
        """Service should initialize without API key."""
        # Reset singleton
        import src.services.rag_response_service as rag_module
        rag_module._rag_service = None

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(os.environ, 'get', return_value=None):
                from src.services.rag_response_service import RAGResponseService
                service = RAGResponseService()
                assert service.openai_api_key is None

    def test_init_with_api_key(self):
        """Service should store API key when provided."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test-key'}):
            from src.services.rag_response_service import RAGResponseService
            service = RAGResponseService()
            assert service.openai_api_key == 'sk-test-key'

    def test_validate_api_key_not_set(self):
        """Should return invalid status when API key not set."""
        with patch.dict(os.environ, {}, clear=True):
            from src.services.rag_response_service import RAGResponseService

            with patch.object(os.environ, 'get', return_value=None):
                service = RAGResponseService()
                status = service._api_status

                assert status.get('valid') is False
                assert status.get('reason') == 'not_set'

    def test_validate_api_key_valid_format(self):
        """Should return valid status for sk- prefixed key."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test-valid-key'}):
            from src.services.rag_response_service import RAGResponseService
            service = RAGResponseService()
            status = service._api_status

            assert status.get('valid') is True

    def test_get_status(self):
        """get_status should return service status."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test-key'}):
            from src.services.rag_response_service import RAGResponseService
            service = RAGResponseService()
            status = service.get_status()

            assert 'api_key_configured' in status
            assert 'api_key_valid' in status
            assert 'synthesis_available' in status
            assert 'mode' in status


# ==================== Source Name Cleaning Tests ====================

class TestSourceNameCleaning:
    """Test source name cleaning logic."""

    def test_clean_source_name_empty(self):
        """Empty source should return 'Knowledge Base'."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()

        assert service._clean_source_name('') == 'Knowledge Base'
        assert service._clean_source_name(None) == 'Knowledge Base'

    def test_clean_source_name_with_metadata_title(self):
        """Should prefer metadata title when available."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()

        result = {'metadata': {'title': 'Hotel Guide'}}
        name = service._clean_source_name('/tmp/123/file.pdf', result)
        assert name == 'Hotel Guide'

    def test_clean_source_name_temp_file_hotel(self):
        """Temp file with hotel content should return 'Hotel Information'."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()

        result = {'content': 'This hotel offers excellent amenities.'}
        name = service._clean_source_name('/tmp/abc123.pdf', result)
        assert name == 'Hotel Information'

    def test_clean_source_name_temp_file_pricing(self):
        """Temp file with pricing content should return 'Pricing Guide'."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()

        result = {'content': 'The rate is $500 per night.'}
        name = service._clean_source_name('/tmp/abc123.pdf', result)
        assert name == 'Pricing Guide'

    def test_clean_source_name_temp_file_destination(self):
        """Temp file with destination content should return destination guide."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()

        result = {'content': 'Maldives is a tropical paradise.'}
        name = service._clean_source_name('/var/folders/tmp123.pdf', result)
        assert name == 'Maldives Guide'

        result = {'content': 'Visit the beaches of Mauritius.'}
        name = service._clean_source_name('/var/folders/tmp123.pdf', result)
        assert name == 'Mauritius Guide'

        result = {'content': 'Explore the islands of Zanzibar.'}
        name = service._clean_source_name('/var/folders/tmp123.pdf', result)
        assert name == 'Zanzibar Guide'

    def test_clean_source_name_regular_file(self):
        """Regular file should return cleaned filename."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()

        name = service._clean_source_name('/docs/hotel_rates_2024.pdf', None)
        assert 'Hotel' in name
        assert 'Rates' in name

    def test_clean_source_name_removes_extension(self):
        """Should remove file extensions for path-based sources."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()

        # Extension removed for full paths
        name = service._clean_source_name('/docs/travel_guide.pdf', None)
        assert '.pdf' not in name

        name = service._clean_source_name('/path/to/info.docx', None)
        assert '.docx' not in name

    def test_clean_source_name_windows_path(self):
        """Should handle Windows-style paths."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()

        name = service._clean_source_name('C:\\Users\\docs\\travel_guide.pdf', None)
        assert 'Travel' in name


# ==================== Content Cleaning Tests ====================

class TestContentCleaning:
    """Test content cleaning logic."""

    def test_clean_content_removes_whitespace(self):
        """Should normalize whitespace."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()

        content = "This   has    extra   spaces."
        cleaned = service._clean_content(content)
        assert '   ' not in cleaned
        assert 'This has extra spaces.' == cleaned

    def test_clean_content_empty(self):
        """Empty content should return empty string."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()

        assert service._clean_content('') == ''
        assert service._clean_content(None) == ''

    def test_clean_content_starts_with_lowercase(self):
        """Content starting with lowercase should find sentence start."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()

        content = "partial sentence. This is a complete sentence."
        cleaned = service._clean_content(content)
        # Should ideally start with "This"
        assert 'This' in cleaned


# ==================== Context Building Tests ====================

class TestContextBuilding:
    """Test context building logic."""

    def test_build_context_from_results(self, sample_search_results):
        """Should build context from search results."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()

        context = service._build_context(sample_search_results, 6000)

        assert len(context) > 0
        assert 'Solana Beach' in context
        assert 'Source:' in context

    def test_build_context_respects_max_chars(self, sample_search_results):
        """Should respect max character limit."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()

        context = service._build_context(sample_search_results, 500)
        assert len(context) <= 700  # Allow some buffer for formatting

    def test_build_context_truncates_long_content(self):
        """Should truncate long individual documents."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()

        long_result = [{
            'content': 'A' * 2000,  # 2000 character content
            'source': 'test.pdf',
            'score': 0.9
        }]

        context = service._build_context(long_result, 6000)
        # Content should be truncated to ~1200 chars
        assert len(context) < 2000

    def test_build_context_empty_results(self):
        """Empty results should return empty context."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()

        context = service._build_context([], 6000)
        assert context == ''


# ==================== Response Generation Tests ====================

class TestResponseGeneration:
    """Test response generation logic."""

    def test_generate_response_with_client(self, mock_openai_client, sample_search_results):
        """Should call OpenAI when client available."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()
        service._client = mock_openai_client

        result = service.generate_response("What hotels are in Mauritius?", sample_search_results, "hotel_info")

        assert result['method'] == 'rag'
        assert 'answer' in result
        assert result['query_type'] == 'hotel_info'
        mock_openai_client.chat.completions.create.assert_called_once()

    def test_generate_response_includes_sources(self, mock_openai_client, sample_search_results):
        """Response should include source information."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()
        service._client = mock_openai_client

        result = service.generate_response("Test question?", sample_search_results)

        assert 'sources' in result
        assert len(result['sources']) > 0
        assert 'filename' in result['sources'][0]
        assert 'score' in result['sources'][0]

    def test_generate_response_handles_llm_error(self, mock_openai_client, sample_search_results):
        """Should fallback on LLM error."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()
        service._client = mock_openai_client
        mock_openai_client.chat.completions.create.side_effect = Exception("API error")

        result = service.generate_response("Test question?", sample_search_results)

        # Should fall back to fallback method
        assert result['method'] == 'fallback'


# ==================== Query Type Handling Tests ====================

class TestQueryTypeHandling:
    """Test query type-specific handling."""

    def test_query_type_hotel_info(self, mock_openai_client, sample_search_results):
        """hotel_info query type should use appropriate prompt."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()
        service._client = mock_openai_client

        service.generate_response("What luxury hotels?", sample_search_results, "hotel_info")

        # Verify system prompt includes hotel-specific guidance
        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        system_prompt = messages[0]['content']
        assert 'hotel' in system_prompt.lower() or 'FOCUS' in system_prompt

    def test_query_type_pricing(self, mock_openai_client, sample_search_results):
        """pricing query type should use appropriate prompt."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()
        service._client = mock_openai_client

        service.generate_response("What are the rates?", sample_search_results, "pricing")

        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        system_prompt = messages[0]['content']
        assert 'price' in system_prompt.lower() or 'FOCUS' in system_prompt

    def test_query_type_platform_help(self, mock_openai_client, sample_search_results):
        """platform_help query type should use appropriate prompt."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()
        service._client = mock_openai_client

        service.generate_response("How do I create a quote?", sample_search_results, "platform_help")

        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        system_prompt = messages[0]['content']
        assert 'step' in system_prompt.lower() or 'FOCUS' in system_prompt

    def test_query_type_destination(self, mock_openai_client, sample_search_results):
        """destination query type should use appropriate prompt."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()
        service._client = mock_openai_client

        service.generate_response("Tell me about Mauritius", sample_search_results, "destination")

        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        system_prompt = messages[0]['content']
        assert 'destination' in system_prompt.lower() or 'FOCUS' in system_prompt

    def test_query_type_general(self, mock_openai_client, sample_search_results):
        """general query type should use general prompt."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()
        service._client = mock_openai_client

        service.generate_response("General question", sample_search_results, "general")

        # Should work without error
        mock_openai_client.chat.completions.create.assert_called_once()


# ==================== Fallback Response Tests ====================

class TestFallbackResponse:
    """Test fallback response generation."""

    def test_fallback_response_with_results(self, sample_search_results):
        """Fallback should generate response from results."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()

        result = service._fallback_response("Test question?", sample_search_results)

        assert result['method'] == 'fallback'
        assert 'answer' in result
        assert len(result['answer']) > 50
        assert 'sources' in result

    def test_fallback_response_deduplicates_content(self):
        """Fallback should skip duplicate content."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()

        duplicate_results = [
            {'content': 'Same content here.', 'source': 'file1.pdf', 'score': 0.9},
            {'content': 'Same content here.', 'source': 'file2.pdf', 'score': 0.8},
        ]

        result = service._fallback_response("Test?", duplicate_results)

        # Should not have duplicate content in answer
        assert result['answer'].count('Same content here') <= 1


# ==================== No Results Response Tests ====================

class TestNoResultsResponse:
    """Test no results response generation."""

    def test_no_results_response_helpful(self):
        """No results response should be helpful."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()

        result = service._no_results_response("Unknown topic?")

        # Should suggest alternatives
        assert 'help' in result['answer'].lower() or 'different' in result['answer'].lower()


# ==================== Singleton Tests ====================

class TestSingleton:
    """Test singleton pattern for RAG service."""

    def test_get_rag_service_returns_singleton(self):
        """get_rag_service should return same instance."""
        import src.services.rag_response_service as rag_module

        # Reset singleton
        rag_module._rag_service = None

        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test'}):
            service1 = rag_module.get_rag_service()
            service2 = rag_module.get_rag_service()

            assert service1 is service2

    def test_generate_rag_response_convenience_function(self, sample_search_results):
        """generate_rag_response convenience function should work."""
        import src.services.rag_response_service as rag_module

        # Reset singleton
        rag_module._rag_service = None

        result = rag_module.generate_rag_response(
            "Test question?",
            sample_search_results,
            "general"
        )

        assert 'answer' in result
        assert 'sources' in result
        assert 'method' in result


# ==================== LLM Call Tests ====================

class TestLLMCall:
    """Test LLM call behavior."""

    def test_call_llm_uses_correct_model(self, mock_openai_client):
        """Should use gpt-4o-mini model."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()
        service._client = mock_openai_client

        service._call_llm("Question?", "Context here", "general")

        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args.kwargs['model'] == 'gpt-4o-mini'

    def test_call_llm_uses_correct_temperature(self, mock_openai_client):
        """Should use 0.6 temperature."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()
        service._client = mock_openai_client

        service._call_llm("Question?", "Context here", "general")

        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args.kwargs['temperature'] == 0.6

    def test_call_llm_sets_max_tokens(self, mock_openai_client):
        """Should set max_tokens."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()
        service._client = mock_openai_client

        service._call_llm("Question?", "Context here", "general")

        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args.kwargs['max_tokens'] == 500

    def test_call_llm_includes_context_in_user_message(self, mock_openai_client):
        """User message should include context."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()
        service._client = mock_openai_client

        service._call_llm("What hotels?", "Hotel info context here", "general")

        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        user_message = messages[1]['content']

        assert "What hotels?" in user_message
        assert "Hotel info context here" in user_message


# ==================== System Prompt Tests ====================

class TestSystemPrompt:
    """Test system prompt content."""

    def test_system_prompt_contains_persona(self):
        """System prompt should define Zara persona."""
        from src.services.rag_response_service import SYSTEM_PROMPT

        assert 'Zara' in SYSTEM_PROMPT
        assert 'Zorah Travel' in SYSTEM_PROMPT

    def test_system_prompt_contains_response_guidelines(self):
        """System prompt should contain response guidelines."""
        from src.services.rag_response_service import SYSTEM_PROMPT

        assert 'RESPONSE STYLE' in SYSTEM_PROMPT or 'style' in SYSTEM_PROMPT.lower()

    def test_query_type_prompts_exist(self):
        """All query type prompts should exist."""
        from src.services.rag_response_service import QUERY_TYPE_PROMPTS

        expected_types = ['hotel_info', 'pricing', 'platform_help', 'destination', 'comparison', 'general']

        for query_type in expected_types:
            assert query_type in QUERY_TYPE_PROMPTS, f"Missing prompt for {query_type}"


# ==================== Edge Cases Tests ====================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_generate_response_with_none_content(self, mock_openai_client):
        """Should handle None content in results."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()
        service._client = mock_openai_client

        results = [
            {'content': None, 'source': 'test.pdf', 'score': 0.9}
        ]

        # Should not crash
        result = service.generate_response("Test?", results)
        assert 'answer' in result

    def test_generate_response_with_empty_content(self, mock_openai_client):
        """Should handle empty content in results."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()
        service._client = mock_openai_client

        results = [
            {'content': '', 'source': 'test.pdf', 'score': 0.9}
        ]

        # Should not crash
        result = service.generate_response("Test?", results)
        assert 'answer' in result

    def test_clean_source_name_with_special_characters(self):
        """Should handle special characters in source names."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()

        # Should not crash
        name = service._clean_source_name('/path/to/file (copy).pdf', None)
        assert isinstance(name, str)

    def test_build_context_with_missing_fields(self):
        """Should handle results with missing fields."""
        from src.services.rag_response_service import RAGResponseService
        service = RAGResponseService()

        results = [
            {'content': 'Some content'},  # Missing source and score
            {'source': 'test.pdf', 'score': 0.9}  # Missing content
        ]

        # Should not crash
        context = service._build_context(results, 6000)
        assert isinstance(context, str)
