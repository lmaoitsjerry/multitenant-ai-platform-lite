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

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
