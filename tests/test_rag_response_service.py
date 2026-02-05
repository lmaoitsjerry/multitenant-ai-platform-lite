"""
RAG Response Service Unit Tests

Tests for RAGResponseService - natural language synthesis from search results.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


class TestIsRetryableOpenAIError:
    """Tests for _is_retryable_openai_error function."""

    def test_rate_limit_error_is_retryable(self):
        """RateLimitError should be retryable."""
        from src.services.rag_response_service import _is_retryable_openai_error
        import openai

        error = openai.RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(),
            body={}
        )
        assert _is_retryable_openai_error(error) is True

    def test_connection_error_is_retryable(self):
        """APIConnectionError should be retryable."""
        from src.services.rag_response_service import _is_retryable_openai_error
        import openai

        error = openai.APIConnectionError(request=MagicMock())
        assert _is_retryable_openai_error(error) is True

    def test_timeout_error_is_retryable(self):
        """APITimeoutError should be retryable."""
        from src.services.rag_response_service import _is_retryable_openai_error
        import openai

        error = openai.APITimeoutError(request=MagicMock())
        assert _is_retryable_openai_error(error) is True

    def test_internal_server_error_is_retryable(self):
        """InternalServerError should be retryable."""
        from src.services.rag_response_service import _is_retryable_openai_error
        import openai

        error = openai.InternalServerError(
            message="Internal error",
            response=MagicMock(),
            body={}
        )
        assert _is_retryable_openai_error(error) is True

    def test_generic_exception_not_retryable(self):
        """Generic exceptions should not be retryable."""
        from src.services.rag_response_service import _is_retryable_openai_error

        error = ValueError("Some error")
        assert _is_retryable_openai_error(error) is False


class TestRAGResponseServiceInit:
    """Tests for RAGResponseService initialization."""

    def test_reads_api_key_from_env(self):
        """Should read OPENAI_API_KEY from environment."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test123'}):
            from src.services.rag_response_service import RAGResponseService

            service = RAGResponseService()

            assert service.openai_api_key == 'sk-test123'

    def test_handles_missing_api_key(self):
        """Should handle missing API key gracefully."""
        with patch.dict('os.environ', {}, clear=True):
            from src.services.rag_response_service import RAGResponseService

            service = RAGResponseService()

            assert service.openai_api_key is None
            assert service._api_status['valid'] is False
            assert service._api_status['reason'] == 'not_set'

    def test_validates_api_key_format(self):
        """Should validate API key format."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-valid-key'}):
            from src.services.rag_response_service import RAGResponseService

            service = RAGResponseService()

            assert service._api_status['valid'] is True
            assert service._api_status['reason'] is None

    def test_warns_on_invalid_format(self):
        """Should warn on invalid API key format."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'invalid-format'}):
            from src.services.rag_response_service import RAGResponseService

            service = RAGResponseService()

            # Should still be valid (might be project key)
            assert service._api_status['valid'] is True
            assert service._api_status['reason'] == 'format_warning'


class TestRAGResponseServiceGetStatus:
    """Tests for get_status method."""

    def test_returns_status_dict(self):
        """Should return status dictionary."""
        with patch.dict('os.environ', {}, clear=True):
            from src.services.rag_response_service import RAGResponseService

            service = RAGResponseService()
            status = service.get_status()

            assert isinstance(status, dict)
            assert 'api_key_configured' in status
            assert 'api_key_valid' in status
            assert 'synthesis_available' in status
            assert 'mode' in status
            assert 'circuit_breaker' in status

    def test_mode_is_fallback_without_api_key(self):
        """Mode should be 'fallback' without API key."""
        with patch.dict('os.environ', {}, clear=True):
            from src.services.rag_response_service import RAGResponseService

            service = RAGResponseService()
            status = service.get_status()

            assert status['mode'] == 'fallback'
            assert status['api_key_configured'] is False


class TestCleanSourceName:
    """Tests for _clean_source_name method."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        with patch.dict('os.environ', {}, clear=True):
            from src.services.rag_response_service import RAGResponseService
            return RAGResponseService()

    def test_returns_knowledge_base_for_empty(self, service):
        """Should return 'Knowledge Base' for empty source."""
        result = service._clean_source_name("", None)
        assert result == "Knowledge Base"

    def test_returns_knowledge_base_for_none(self, service):
        """Should return 'Knowledge Base' for None source."""
        result = service._clean_source_name(None, None)
        assert result == "Knowledge Base"

    def test_uses_metadata_title_if_present(self, service):
        """Should use metadata title if available."""
        result_dict = {'metadata': {'title': 'Hotel Guide'}}
        result = service._clean_source_name("/tmp/xyz123.pdf", result_dict)
        assert result == "Hotel Guide"

    def test_extracts_filename_from_path(self, service):
        """Should extract and format filename from path."""
        result = service._clean_source_name("/docs/mauritius_guide.pdf", None)
        assert result == "Mauritius Guide"

    def test_handles_windows_paths(self, service):
        """Should handle Windows-style paths."""
        result = service._clean_source_name("C:\\docs\\hotel_info.pdf", None)
        assert result == "Hotel Info"

    def test_detects_temp_files(self, service):
        """Should detect and replace temp file names."""
        result = service._clean_source_name("/tmp/xyz123.pdf", {'content': 'hotel info'})
        assert result == "Hotel Information"

    def test_temp_file_with_rate_content(self, service):
        """Should label temp file with rate content as Pricing Guide."""
        result = service._clean_source_name("/var/folders/tmp123.pdf", {'content': 'rates and prices'})
        assert result == "Pricing Guide"

    def test_temp_file_with_maldives_content(self, service):
        """Should label temp file with Maldives content."""
        # Note: 'resorts' would match 'resort' first, use content without hotel/resort keywords
        result = service._clean_source_name("/temp/doc.pdf", {'content': 'Beautiful Maldives beaches'})
        assert result == "Maldives Guide"

    def test_temp_file_with_mauritius_content(self, service):
        """Should label temp file with Mauritius content."""
        result = service._clean_source_name("/temp/doc.pdf", {'content': 'Visit Mauritius today'})
        assert result == "Mauritius Guide"

    def test_temp_file_with_zanzibar_content(self, service):
        """Should label temp file with Zanzibar content."""
        result = service._clean_source_name("/temp/doc.pdf", {'content': 'Zanzibar beaches'})
        assert result == "Zanzibar Guide"

    def test_removes_file_extension(self, service):
        """Should remove file extensions."""
        result = service._clean_source_name("/docs/guide.docx", None)
        assert "docx" not in result.lower()

    def test_converts_underscores_to_spaces(self, service):
        """Should convert underscores to spaces."""
        result = service._clean_source_name("/docs/hotel_rates_2024.pdf", None)
        assert "Hotel Rates 2024" == result

    def test_preserves_short_acronyms(self, service):
        """Should preserve short acronyms."""
        result = service._clean_source_name("/docs/FAQ_guide.pdf", None)
        assert "FAQ" in result


class TestCleanContent:
    """Tests for _clean_content method."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        with patch.dict('os.environ', {}, clear=True):
            from src.services.rag_response_service import RAGResponseService
            return RAGResponseService()

    def test_returns_empty_for_empty_input(self, service):
        """Should return empty string for empty input."""
        result = service._clean_content("")
        assert result == ""

    def test_removes_excessive_whitespace(self, service):
        """Should normalize whitespace."""
        result = service._clean_content("This   has    extra   spaces")
        assert result == "This has extra spaces"

    def test_removes_leading_newlines(self, service):
        """Should remove leading newlines."""
        result = service._clean_content("\n\nThis is text")
        assert result == "This is text"

    def test_handles_content_starting_lowercase(self, service):
        """Should try to find sentence start for lowercase content."""
        result = service._clean_content("partial sentence. This is complete.")
        # Should find the capital letter
        assert result.startswith("This") or result.startswith("partial")


class TestBuildContext:
    """Tests for _build_context method."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        with patch.dict('os.environ', {}, clear=True):
            from src.services.rag_response_service import RAGResponseService
            return RAGResponseService()

    def test_builds_context_from_results(self, service):
        """Should build context from search results."""
        results = [
            {'content': 'First result content.', 'source': 'doc1.pdf'},
            {'content': 'Second result content.', 'source': 'doc2.pdf'}
        ]

        context = service._build_context(results, max_chars=10000)

        assert 'First result content' in context
        assert 'Second result content' in context

    def test_respects_max_chars(self, service):
        """Should respect max_chars limit."""
        results = [
            {'content': 'A' * 5000, 'source': 'doc1.pdf'},
            {'content': 'B' * 5000, 'source': 'doc2.pdf'}
        ]

        context = service._build_context(results, max_chars=3000)

        assert len(context) <= 3000

    def test_truncates_long_documents(self, service):
        """Should truncate individual long documents."""
        results = [
            {'content': 'X' * 2000, 'source': 'doc.pdf'}
        ]

        context = service._build_context(results, max_chars=10000)

        # Individual docs truncated to ~1200 chars
        assert len(context) < 2000

    def test_includes_source_labels(self, service):
        """Should include source labels in context."""
        results = [
            {'content': 'Some content.', 'source': 'guide.pdf'}
        ]

        context = service._build_context(results, max_chars=10000)

        assert '[Source:' in context

    def test_skips_empty_content(self, service):
        """Should skip results with empty content."""
        results = [
            {'content': '', 'source': 'empty.pdf'},
            {'content': 'Valid content.', 'source': 'valid.pdf'}
        ]

        context = service._build_context(results, max_chars=10000)

        assert 'Valid content' in context
        assert context.count('[Source:') == 1


class TestGenerateResponse:
    """Tests for generate_response method."""

    @pytest.fixture
    def service(self):
        """Create service instance without API key."""
        with patch.dict('os.environ', {}, clear=True):
            from src.services.rag_response_service import RAGResponseService
            return RAGResponseService()

    def test_returns_dict(self, service):
        """Should return a dictionary."""
        result = service.generate_response("Test question", [])
        assert isinstance(result, dict)

    def test_has_required_keys(self, service):
        """Should have required response keys."""
        result = service.generate_response("Test question", [])

        assert 'answer' in result
        assert 'sources' in result
        assert 'method' in result

    def test_uses_fallback_without_client(self, service):
        """Should use fallback when no OpenAI client."""
        results = [{'content': 'Test content.', 'source': 'doc.pdf', 'score': 0.8}]
        result = service.generate_response("Test question", results)

        assert result['method'] == 'fallback'

    def test_handles_empty_results(self, service):
        """Should handle empty search results."""
        result = service.generate_response("Test question", [])

        assert result['method'] == 'no_results'
        assert result['sources'] == []


class TestFallbackResponse:
    """Tests for _fallback_response method."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        with patch.dict('os.environ', {}, clear=True):
            from src.services.rag_response_service import RAGResponseService
            return RAGResponseService()

    def test_returns_structured_response(self, service):
        """Should return structured response."""
        results = [
            {'content': 'Hotel information here.', 'source': 'hotels.pdf', 'score': 0.9}
        ]

        response = service._fallback_response("What hotels?", results)

        assert 'answer' in response
        assert 'sources' in response
        assert response['method'] == 'fallback'

    def test_includes_content_from_results(self, service):
        """Should include content from top results."""
        results = [
            {'content': 'Luxury resort details.', 'source': 'doc.pdf', 'score': 0.9}
        ]

        response = service._fallback_response("Question", results)

        assert 'Luxury resort details' in response['answer']

    def test_deduplicates_similar_content(self, service):
        """Should skip duplicate content."""
        results = [
            {'content': 'Same content here.', 'source': 'doc1.pdf', 'score': 0.9},
            {'content': 'Same content here.', 'source': 'doc2.pdf', 'score': 0.8}
        ]

        response = service._fallback_response("Question", results)

        # Should only appear once
        assert response['answer'].count('Same content here') == 1

    def test_limits_to_three_results(self, service):
        """Should use at most 3 results."""
        results = [
            {'content': f'Content {i}.', 'source': f'doc{i}.pdf', 'score': 0.9 - i * 0.1}
            for i in range(5)
        ]

        response = service._fallback_response("Question", results)

        assert len(response['sources']) <= 3

    def test_handles_empty_results(self, service):
        """Should handle empty results gracefully."""
        response = service._fallback_response("Question", [])

        assert response['method'] == 'no_results'


class TestNoResultsResponse:
    """Tests for _no_results_response method."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        with patch.dict('os.environ', {}, clear=True):
            from src.services.rag_response_service import RAGResponseService
            return RAGResponseService()

    def test_returns_helpful_message(self, service):
        """Should return helpful message."""
        response = service._no_results_response("What is X?")

        assert 'answer' in response
        assert len(response['answer']) > 0

    def test_sources_empty(self, service):
        """Sources should be empty."""
        response = service._no_results_response("Question")

        assert response['sources'] == []

    def test_method_is_no_results(self, service):
        """Method should be 'no_results' without LLM."""
        response = service._no_results_response("Question")

        assert response['method'] == 'no_results'


class TestGetRAGService:
    """Tests for get_rag_service singleton function."""

    def test_returns_service_instance(self):
        """Should return RAGResponseService instance."""
        # Reset singleton for test
        import src.services.rag_response_service as module
        module._rag_service = None

        with patch.dict('os.environ', {}, clear=True):
            from src.services.rag_response_service import get_rag_service, RAGResponseService

            service = get_rag_service()

            assert isinstance(service, RAGResponseService)

    def test_returns_same_instance(self):
        """Should return same instance on multiple calls."""
        import src.services.rag_response_service as module
        module._rag_service = None

        with patch.dict('os.environ', {}, clear=True):
            from src.services.rag_response_service import get_rag_service

            service1 = get_rag_service()
            service2 = get_rag_service()

            assert service1 is service2


class TestGenerateRAGResponse:
    """Tests for generate_rag_response convenience function."""

    def test_calls_service(self):
        """Should call service.generate_response."""
        import src.services.rag_response_service as module
        module._rag_service = None

        with patch.dict('os.environ', {}, clear=True):
            from src.services.rag_response_service import generate_rag_response

            result = generate_rag_response("Question", [], "general")

            assert isinstance(result, dict)
            assert 'answer' in result

    def test_passes_query_type(self):
        """Should pass query_type to service."""
        import src.services.rag_response_service as module
        module._rag_service = None

        with patch.dict('os.environ', {}, clear=True):
            from src.services.rag_response_service import generate_rag_response

            results = [{'content': 'Test.', 'source': 'doc.pdf', 'score': 0.9}]
            result = generate_rag_response("Question", results, "hotel_info")

            assert isinstance(result, dict)


class TestQueryTypePrompts:
    """Tests for QUERY_TYPE_PROMPTS constant."""

    def test_has_all_query_types(self):
        """Should have all expected query types."""
        from src.services.rag_response_service import QUERY_TYPE_PROMPTS

        expected_types = [
            "hotel_info",
            "pricing",
            "platform_help",
            "destination",
            "comparison",
            "general"
        ]

        for query_type in expected_types:
            assert query_type in QUERY_TYPE_PROMPTS

    def test_prompts_are_strings(self):
        """All prompts should be strings."""
        from src.services.rag_response_service import QUERY_TYPE_PROMPTS

        for prompt in QUERY_TYPE_PROMPTS.values():
            assert isinstance(prompt, str)
            assert len(prompt) > 0


class TestSystemPrompt:
    """Tests for SYSTEM_PROMPT constant."""

    def test_system_prompt_exists(self):
        """SYSTEM_PROMPT should be defined."""
        from src.services.rag_response_service import SYSTEM_PROMPT

        assert isinstance(SYSTEM_PROMPT, str)
        assert len(SYSTEM_PROMPT) > 100

    def test_includes_personality(self):
        """SYSTEM_PROMPT should include personality guidance."""
        from src.services.rag_response_service import SYSTEM_PROMPT

        assert "Zara" in SYSTEM_PROMPT

    def test_includes_response_style(self):
        """SYSTEM_PROMPT should include response style guidance."""
        from src.services.rag_response_service import SYSTEM_PROMPT

        assert "RESPONSE STYLE" in SYSTEM_PROMPT


class TestCircuitBreakerIntegration:
    """Tests for circuit breaker integration."""

    def test_circuit_breaker_exists(self):
        """Module should have circuit breaker."""
        from src.services.rag_response_service import _openai_circuit_breaker

        assert _openai_circuit_breaker is not None
        assert _openai_circuit_breaker.name == "openai"

    def test_circuit_breaker_in_status(self):
        """Circuit breaker status should be in get_status."""
        with patch.dict('os.environ', {}, clear=True):
            from src.services.rag_response_service import RAGResponseService

            service = RAGResponseService()
            status = service.get_status()

            assert 'circuit_breaker' in status


# ==================== NEW TESTS: Response Generation with Mocked LLM ====================

class TestResponseGenerationWithLLM:
    """Tests for generate_response when LLM client is available (mocked)."""

    @pytest.fixture
    def service_with_client(self):
        """Create service with a mocked OpenAI client."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test-key'}):
            from src.services.rag_response_service import RAGResponseService
            service = RAGResponseService()

            mock_client = MagicMock()
            mock_completion = MagicMock()
            mock_completion.choices = [MagicMock()]
            mock_completion.choices[0].message.content = "Great question! Here is the answer."
            mock_client.chat.completions.create.return_value = mock_completion
            service._client = mock_client

            return service

    def test_generate_response_uses_llm_when_available(self, service_with_client):
        """Should use LLM and return method='rag' when client is available."""
        from src.services.rag_response_service import _openai_circuit_breaker
        _openai_circuit_breaker.state = "closed"
        _openai_circuit_breaker.failures = 0

        results = [{'content': 'Hotel info here.', 'source': 'hotels.pdf', 'score': 0.9}]
        response = service_with_client.generate_response("What hotels?", results, "hotel_info")

        assert response['method'] == 'rag'
        assert response['answer'] == "Great question! Here is the answer."
        assert len(response['sources']) == 1

    def test_generate_response_includes_query_type(self, service_with_client):
        """Response should include the query_type used."""
        from src.services.rag_response_service import _openai_circuit_breaker
        _openai_circuit_breaker.state = "closed"
        _openai_circuit_breaker.failures = 0

        results = [{'content': 'Pricing data.', 'source': 'prices.pdf', 'score': 0.85}]
        response = service_with_client.generate_response("What are the prices?", results, "pricing")

        assert response['query_type'] == 'pricing'

    def test_generate_response_limits_sources_to_five(self, service_with_client):
        """Sources should be limited to top 5."""
        from src.services.rag_response_service import _openai_circuit_breaker
        _openai_circuit_breaker.state = "closed"
        _openai_circuit_breaker.failures = 0

        results = [
            {'content': f'Content {i}', 'source': f'doc{i}.pdf', 'score': 0.9 - i * 0.05}
            for i in range(8)
        ]
        response = service_with_client.generate_response("query", results)

        assert len(response['sources']) <= 5

    def test_generate_response_falls_back_on_llm_failure(self, service_with_client):
        """Should fall back gracefully if LLM call raises an exception."""
        from src.services.rag_response_service import _openai_circuit_breaker
        _openai_circuit_breaker.state = "closed"
        _openai_circuit_breaker.failures = 0

        # Make LLM call raise
        service_with_client._client.chat.completions.create.side_effect = Exception("API down")

        results = [{'content': 'Fallback content here.', 'source': 'doc.pdf', 'score': 0.8}]
        response = service_with_client.generate_response("question", results)

        assert response['method'] == 'fallback'
        assert 'Fallback content' in response['answer']


# ==================== NEW TESTS: Context Injection & Prompt Construction ====================

class TestContextInjectionAndPrompts:
    """Tests for _build_context and prompt construction details."""

    @pytest.fixture
    def service(self):
        with patch.dict('os.environ', {}, clear=True):
            from src.services.rag_response_service import RAGResponseService
            return RAGResponseService()

    def test_build_context_separates_results_with_divider(self, service):
        """Results should be separated with '---' divider."""
        results = [
            {'content': 'First document.', 'source': 'doc1.pdf'},
            {'content': 'Second document.', 'source': 'doc2.pdf'}
        ]
        context = service._build_context(results, max_chars=10000)

        assert '---' in context

    def test_build_context_truncates_at_sentence_boundary(self, service):
        """Long documents should be truncated at sentence boundaries when possible."""
        long_content = "Short sentence. " * 100  # Well over 1200 chars
        results = [{'content': long_content, 'source': 'doc.pdf'}]

        context = service._build_context(results, max_chars=10000)

        # Should end with a period (sentence boundary)
        source_content = context.split('\n', 1)[-1].strip()
        assert source_content.endswith('.')

    def test_build_context_appends_ellipsis_when_no_sentence_break(self, service):
        """Should append '...' when truncation can't find a sentence boundary."""
        # No periods = no sentence boundary
        long_content = "x " * 1000
        results = [{'content': long_content, 'source': 'doc.pdf'}]

        context = service._build_context(results, max_chars=10000)

        assert '...' in context

    def test_build_context_empty_results(self, service):
        """Empty results list should produce empty context."""
        context = service._build_context([], max_chars=10000)
        assert context == ""

    def test_query_type_prompt_appended_to_system_prompt(self):
        """Query-type specific guidance should exist for each type."""
        from src.services.rag_response_service import QUERY_TYPE_PROMPTS, SYSTEM_PROMPT

        for query_type, guidance in QUERY_TYPE_PROMPTS.items():
            full = SYSTEM_PROMPT + "\n" + guidance
            assert "FOCUS FOR THIS QUERY" in full


# ==================== NEW TESTS: Source Attribution Edge Cases ====================

class TestSourceAttributionEdgeCases:
    """Tests for _clean_source_name edge cases."""

    @pytest.fixture
    def service(self):
        with patch.dict('os.environ', {}, clear=True):
            from src.services.rag_response_service import RAGResponseService
            return RAGResponseService()

    def test_metadata_name_field_used_when_no_title(self, service):
        """Should use metadata 'name' if 'title' is absent."""
        result_dict = {'metadata': {'name': 'Resort Catalog'}}
        result = service._clean_source_name("/tmp/xyz.pdf", result_dict)
        assert result == "Resort Catalog"

    def test_metadata_with_tmp_title_ignored(self, service):
        """Metadata title starting with 'tmp' should be ignored."""
        result_dict = {'metadata': {'title': 'tmp12345'}}
        result = service._clean_source_name("/docs/file.pdf", result_dict)
        # Should fall through to filename extraction, not use 'tmp12345'
        assert result != 'tmp12345'

    def test_macos_temp_path_detected(self, service):
        """macOS temp path (/var/folders/) should be detected as temp."""
        result = service._clean_source_name(
            "/var/folders/c2/abc123/T/uploaded.pdf",
            {'content': 'General travel guide content'}
        )
        assert result == "Travel Guide"

    def test_windows_temp_path_detected(self, service):
        """Windows temp path (AppData\\Local\\Temp) should be detected."""
        result = service._clean_source_name(
            "C:\\Users\\user\\AppData\\Local\\Temp\\file.pdf",
            {'content': 'General travel information'}
        )
        assert result == "Travel Guide"

    def test_simple_source_string_returned_as_is(self, service):
        """Simple source string without path separators returned as-is."""
        result = service._clean_source_name("my_document", None)
        assert result == "my_document"

    def test_template_keyword_not_treated_as_temp(self, service):
        """Files with 'template' in path should not be flagged as temp."""
        result = service._clean_source_name("/docs/email_template_guide.pdf", None)
        assert "Template" in result or "template" in result.lower()
        assert result != "Travel Guide"


# ==================== NEW TESTS: Fallback Response Truncation ====================

class TestFallbackResponseTruncation:
    """Tests for content truncation in fallback responses."""

    @pytest.fixture
    def service(self):
        with patch.dict('os.environ', {}, clear=True):
            from src.services.rag_response_service import RAGResponseService
            return RAGResponseService()

    def test_fallback_truncates_long_content_at_sentence(self, service):
        """Fallback should truncate long content at sentence boundary."""
        long_content = "This is a sentence. " * 50  # ~1000 chars
        results = [{'content': long_content, 'source': 'doc.pdf', 'score': 0.9}]

        response = service._fallback_response("question", results)

        # The answer should not contain the full 1000 chars of raw content
        assert len(response['answer']) < len(long_content) + 100

    def test_fallback_with_only_empty_content(self, service):
        """Fallback with results that have empty content should return no_results."""
        results = [
            {'content': '', 'source': 'empty1.pdf', 'score': 0.9},
            {'content': '   ', 'source': 'empty2.pdf', 'score': 0.8}
        ]
        response = service._fallback_response("question", results)

        assert response['method'] == 'no_results'

    def test_fallback_includes_helpful_suffix(self, service):
        """Fallback response should include a helpful follow-up offer."""
        results = [{'content': 'Some hotel info.', 'source': 'doc.pdf', 'score': 0.9}]
        response = service._fallback_response("question", results)

        assert 'dig deeper' in response['answer'].lower() or 'help' in response['answer'].lower()


# ==================== NEW TESTS: Token Limits & max_context_chars ====================

class TestTokenLimits:
    """Tests for max_context_chars parameter handling."""

    @pytest.fixture
    def service(self):
        with patch.dict('os.environ', {}, clear=True):
            from src.services.rag_response_service import RAGResponseService
            return RAGResponseService()

    def test_very_small_max_chars_limits_context(self, service):
        """Very small max_context_chars should limit context to few chars."""
        results = [
            {'content': 'A' * 500, 'source': 'doc1.pdf'},
            {'content': 'B' * 500, 'source': 'doc2.pdf'}
        ]
        context = service._build_context(results, max_chars=100)

        # Should be very short (only what fits)
        assert len(context) <= 200  # Some overhead for source label

    def test_zero_max_chars_produces_empty_context(self, service):
        """max_chars=0 should produce empty context."""
        results = [{'content': 'Content.', 'source': 'doc.pdf'}]
        context = service._build_context(results, max_chars=0)

        assert context == ""

    def test_default_max_context_chars_is_6000(self):
        """Default max_context_chars should be 6000."""
        import inspect
        from src.services.rag_response_service import RAGResponseService
        sig = inspect.signature(RAGResponseService.generate_response)
        default = sig.parameters['max_context_chars'].default
        assert default == 6000


# ==================== NEW TESTS: No Results with LLM ====================

class TestNoResultsWithLLM:
    """Tests for _no_results_response when LLM is available."""

    def test_no_results_uses_llm_when_available(self):
        """Should use LLM to generate a conversational no-results response."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test'}):
            from src.services.rag_response_service import RAGResponseService
            service = RAGResponseService()

            mock_client = MagicMock()
            mock_completion = MagicMock()
            mock_completion.choices = [MagicMock()]
            mock_completion.choices[0].message.content = "I don't have that info, but I can help!"
            mock_client.chat.completions.create.return_value = mock_completion
            service._client = mock_client

            response = service._no_results_response("Where is Atlantis?")

            assert response['method'] == 'llm_no_context'
            assert response['answer'] == "I don't have that info, but I can help!"
            assert response['sources'] == []

    def test_no_results_falls_back_when_llm_fails(self):
        """Should use static fallback when LLM fails on no-results."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test'}):
            from src.services.rag_response_service import RAGResponseService
            service = RAGResponseService()

            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = Exception("LLM down")
            service._client = mock_client

            response = service._no_results_response("Where is Atlantis?")

            assert response['method'] == 'no_results'
            assert 'rephrasing' in response['answer'].lower() or "help" in response['answer'].lower()


# ==================== NEW TESTS: Clean Content Edge Cases ====================

class TestCleanContentEdgeCases:
    """Additional edge cases for _clean_content method."""

    @pytest.fixture
    def service(self):
        with patch.dict('os.environ', {}, clear=True):
            from src.services.rag_response_service import RAGResponseService
            return RAGResponseService()

    def test_clean_content_handles_none(self, service):
        """Should handle None input gracefully."""
        result = service._clean_content(None)
        assert result == ""

    def test_clean_content_preserves_sentence_starting_with_capital(self, service):
        """Content starting with capital should be preserved as-is."""
        result = service._clean_content("Hotels in Mauritius are beautiful.")
        assert result == "Hotels in Mauritius are beautiful."

    def test_clean_content_strips_surrounding_whitespace(self, service):
        """Should strip leading/trailing whitespace."""
        result = service._clean_content("   Hello world   ")
        assert result == "Hello world"

    def test_clean_content_collapses_tabs_and_newlines(self, service):
        """Tabs and newlines should be collapsed to single spaces."""
        result = service._clean_content("Hello\t\tworld\n\nnew line")
        assert result == "Hello world new line"
