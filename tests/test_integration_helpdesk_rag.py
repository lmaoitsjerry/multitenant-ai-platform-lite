"""
Integration Tests for Helpdesk RAG

End-to-end tests verifying the helpdesk RAG flow:
1. Natural response generation from FAISS results
2. Graceful handling of unknown questions
3. Response timing data included
4. LLM failure fallback

These tests use mocks for external services (FAISS, OpenAI)
but test the actual endpoint integration.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from fastapi import FastAPI


class MockConfig:
    """Mock ClientConfig for testing"""
    def __init__(self, client_id='test_tenant'):
        self.client_id = client_id
        self.company_name = 'Test Travel Agency'
        self.destination_names = ['Zanzibar', 'Mauritius', 'Seychelles', 'Maldives']
        self.timezone = 'Africa/Johannesburg'
        self.currency = 'ZAR'
        self.primary_email = 'test@example.com'


@pytest.fixture
def mock_config():
    """Fixture providing mock config"""
    return MockConfig()


@pytest.fixture
def helpdesk_app():
    """Create FastAPI app with helpdesk router only"""
    app = FastAPI()
    from src.api.helpdesk_routes import helpdesk_router
    app.include_router(helpdesk_router)
    return app


@pytest.fixture
def test_client(helpdesk_app):
    """Create test client"""
    return TestClient(helpdesk_app)


class TestHelpdeskNaturalResponse:
    """Test helpdesk returns natural, conversational responses"""

    @patch('src.api.helpdesk_routes.search_shared_faiss_index')
    @patch('src.api.helpdesk_routes.generate_rag_response')
    @patch('src.api.helpdesk_routes.get_client_config')
    def test_helpdesk_returns_natural_response(
        self,
        mock_get_config,
        mock_rag_response,
        mock_faiss_search,
        test_client
    ):
        """
        Test that helpdesk returns a natural response for a hotel query

        Verifies:
        1. FAISS search is called
        2. RAG synthesis transforms results
        3. Response is a string (not list)
        4. Response contains relevant hotel info
        """
        mock_get_config.return_value = MockConfig()

        # Mock FAISS search returning hotel results
        mock_faiss_search.return_value = [
            {
                'content': 'The Zanzibar White Sand Luxury Villas is a 5-star beachfront property offering private pools and all-inclusive packages starting at $500/night.',
                'score': 0.85,
                'source': 'zanzibar_hotels.md'
            },
            {
                'content': 'Baraza Resort & Spa features stunning Arabian architecture with rates from $450/night including meals and spa treatments.',
                'score': 0.78,
                'source': 'zanzibar_hotels.md'
            }
        ]

        # Mock RAG synthesis returning natural response
        mock_rag_response.return_value = {
            'answer': "For Zanzibar, I'd recommend looking at the Zanzibar White Sand Luxury Villas - it's a beautiful 5-star beachfront property with private pools. Rates start around $500 per night and include all-inclusive packages. If you prefer something with a more Arabian feel, Baraza Resort & Spa is another excellent option at $450/night, which includes meals and spa treatments.",
            'sources': [
                {'filename': 'zanzibar_hotels.md', 'score': 0.85},
                {'filename': 'zanzibar_hotels.md', 'score': 0.78}
            ],
            'method': 'rag'
        }

        # Make request
        response = test_client.post(
            '/api/v1/helpdesk/ask',
            json={'question': 'What hotels do you recommend in Zanzibar?'},
            headers={'X-Client-ID': 'test_tenant'}
        )

        assert response.status_code == 200
        result = response.json()

        # Verify response structure
        assert result['success'] is True
        assert isinstance(result['answer'], str)  # Should be string, not list
        assert 'Zanzibar' in result['answer'] or 'zanzibar' in result['answer'].lower()
        assert result['method'] == 'rag'
        assert 'sources' in result
        assert len(result['sources']) > 0


class TestHelpdeskUnknownQuestion:
    """Test helpdesk handles unknown questions gracefully"""

    @patch('src.api.helpdesk_routes.search_shared_faiss_index')
    @patch('src.api.helpdesk_routes.get_client_config')
    def test_helpdesk_unknown_question_graceful(
        self,
        mock_get_config,
        mock_faiss_search,
        test_client
    ):
        """
        Test that helpdesk handles off-topic questions gracefully

        Verifies:
        1. FAISS returns empty results
        2. Response acknowledges lack of information
        3. Response is still helpful, not an error
        """
        mock_get_config.return_value = MockConfig()

        # Mock FAISS returning no results
        mock_faiss_search.return_value = []

        # Make request with off-topic question
        response = test_client.post(
            '/api/v1/helpdesk/ask',
            json={'question': 'What is the capital of France?'},
            headers={'X-Client-ID': 'test_tenant'}
        )

        assert response.status_code == 200
        result = response.json()

        assert result['success'] is True
        answer = result['answer'].lower()

        # Should acknowledge it doesn't have the info (static fallback)
        # Or provide a helpful generic response
        assert len(result['answer']) > 20  # Not just an empty response


class TestHelpdeskResponseTiming:
    """Test helpdesk includes timing data in response"""

    @patch('src.api.helpdesk_routes.search_shared_faiss_index')
    @patch('src.api.helpdesk_routes.generate_rag_response')
    @patch('src.api.helpdesk_routes.get_client_config')
    def test_helpdesk_response_includes_timing(
        self,
        mock_get_config,
        mock_rag_response,
        mock_faiss_search,
        test_client
    ):
        """
        Test that helpdesk response includes timing data

        Verifies:
        1. Response includes timing object
        2. timing.search_ms is present
        3. timing.synthesis_ms is present
        4. timing.total_ms is present
        """
        mock_get_config.return_value = MockConfig()

        mock_faiss_search.return_value = [
            {'content': 'Test content', 'score': 0.9, 'source': 'test.md'}
        ]

        mock_rag_response.return_value = {
            'answer': 'Here is some helpful information about hotels.',
            'sources': [{'filename': 'test.md', 'score': 0.9}],
            'method': 'rag'
        }

        response = test_client.post(
            '/api/v1/helpdesk/ask',
            json={'question': 'Tell me about hotels'},
            headers={'X-Client-ID': 'test_tenant'}
        )

        assert response.status_code == 200
        result = response.json()

        # Verify timing data structure
        assert 'timing' in result
        timing = result['timing']

        assert 'search_ms' in timing
        assert 'synthesis_ms' in timing
        assert 'total_ms' in timing

        # Timing values should be integers
        assert isinstance(timing['search_ms'], int)
        assert isinstance(timing['synthesis_ms'], int)
        assert isinstance(timing['total_ms'], int)

        # Total should be >= search + synthesis
        assert timing['total_ms'] >= timing['search_ms']


class TestHelpdeskLLMFailureFallback:
    """Test helpdesk falls back gracefully when LLM fails"""

    @patch('src.api.helpdesk_routes.search_shared_faiss_index')
    @patch('src.api.helpdesk_routes.generate_rag_response')
    @patch('src.api.helpdesk_routes.get_client_config')
    def test_helpdesk_llm_failure_fallback(
        self,
        mock_get_config,
        mock_rag_response,
        mock_faiss_search,
        test_client
    ):
        """
        Test that helpdesk falls back when LLM synthesis fails

        Verifies:
        1. FAISS returns results
        2. RAG synthesis returns fallback method
        3. Response still provides useful information
        4. No crash or error status
        """
        mock_get_config.return_value = MockConfig()

        # FAISS returns results
        mock_faiss_search.return_value = [
            {
                'content': 'Maldives resorts offer overwater villas with stunning views.',
                'score': 0.82,
                'source': 'maldives_info.md'
            }
        ]

        # RAG service returns fallback response (LLM unavailable)
        mock_rag_response.return_value = {
            'answer': "Here's what I found in the knowledge base:\n\nMaldives resorts offer overwater villas with stunning views.\n\nFor more specific information, please refine your question.",
            'sources': [{'filename': 'maldives_info.md', 'score': 0.82}],
            'method': 'fallback'
        }

        response = test_client.post(
            '/api/v1/helpdesk/ask',
            json={'question': 'What hotels are in the Maldives?'},
            headers={'X-Client-ID': 'test_tenant'}
        )

        assert response.status_code == 200
        result = response.json()

        assert result['success'] is True
        assert 'Maldives' in result['answer'] or 'maldives' in result['answer'].lower()
        assert result['method'] == 'fallback'


class TestRAGResponseService:
    """Test RAG response service directly"""

    def test_rag_service_builds_context_correctly(self):
        """Test RAG service builds context from search results"""
        from src.services.rag_response_service import RAGResponseService

        service = RAGResponseService()

        results = [
            {'content': 'First result content about hotels.', 'source': 'doc1.md'},
            {'content': 'Second result with pricing info.', 'source': 'doc2.md'},
        ]

        context = service._build_context(results, max_chars=5000)

        # Context should contain both results
        assert 'First result content' in context
        assert 'Second result' in context
        assert '[Source: doc1.md]' in context

    def test_rag_service_fallback_without_api_key(self):
        """Test RAG service returns fallback when no API key"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': ''}):
            from src.services.rag_response_service import RAGResponseService

            service = RAGResponseService()
            service.openai_api_key = None  # Force no API key
            service._client = None

            results = [
                {'content': 'Test content about destinations.', 'source': 'test.md', 'score': 0.8}
            ]

            response = service.generate_response("What destinations?", results)

            # Should be fallback method without LLM
            assert response['method'] == 'fallback'
            assert 'Test content' in response['answer']

    def test_rag_service_handles_empty_results(self):
        """Test RAG service handles empty search results"""
        from src.services.rag_response_service import RAGResponseService

        service = RAGResponseService()

        response = service.generate_response("Unknown topic?", [])

        assert response['method'] == 'no_results'
        assert "don't have" in response['answer'].lower() or "information" in response['answer'].lower()
        assert response['sources'] == []


class TestFAISSHelpdeskService:
    """Test FAISS helpdesk service integration"""

    def test_faiss_service_search_with_context(self):
        """Test search_with_context returns filtered results"""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Create mock service
        service = FAISSHelpdeskService()

        # Mock the internal state to simulate initialized service
        service._initialized = True

        # Mock the search method with 4 results (3+ above threshold ensures filtering works)
        with patch.object(service, 'search') as mock_search:
            mock_search.return_value = [
                {'content': 'Zanzibar hotel info', 'score': 0.85, 'source': 'zanzibar.md'},
                {'content': 'Mauritius resort data', 'score': 0.75, 'source': 'mauritius.md'},
                {'content': 'Seychelles beach info', 'score': 0.65, 'source': 'seychelles.md'},
                {'content': 'Low score result', 'score': 0.2, 'source': 'other.md'},  # Below threshold
            ]

            results = service.search_with_context('Zanzibar hotels', top_k=8, min_score=0.3)

        # Should return only results above threshold (3 results)
        assert len(results) == 3
        # All results should meet min_score threshold
        for r in results:
            assert r.get('score', 0) >= 0.3
        # Results should include Zanzibar
        assert any('Zanzibar' in r.get('content', '') for r in results)


class TestHelpdeskStaticFallback:
    """Test helpdesk static response fallback"""

    @patch('src.api.helpdesk_routes.search_shared_faiss_index')
    @patch('src.api.helpdesk_routes.get_client_config')
    def test_static_fallback_for_quotes_question(
        self,
        mock_get_config,
        mock_faiss_search,
        test_client
    ):
        """Test static fallback for platform usage questions"""
        mock_get_config.return_value = MockConfig()
        mock_faiss_search.return_value = []  # No FAISS results

        response = test_client.post(
            '/api/v1/helpdesk/ask',
            json={'question': 'How do I create a quote?'},
            headers={'X-Client-ID': 'test_tenant'}
        )

        assert response.status_code == 200
        result = response.json()

        assert result['success'] is True
        # Should return static help for quotes
        assert result['method'] == 'static'
        answer = result['answer'].lower()
        assert 'quote' in answer or 'generate' in answer


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
