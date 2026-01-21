"""
Test Configuration and Fixtures

Central configuration for pytest including:
- Reusable fixtures for mocking dependencies
- Test client setup
- Authentication helpers
- Database mocks
- BigQuery mock infrastructure
- Analytics-specific fixtures

Usage:
    All fixtures defined here are automatically available to all tests.
    Import specific helpers from tests.utils if needed.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import os
import sys
from datetime import datetime, timedelta

# Ensure src is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== Configuration Fixtures ====================

@pytest.fixture
def mock_config():
    """Create a mock ClientConfig for testing.

    Returns:
        MagicMock: A mock configuration object with common attributes.
    """
    config = MagicMock()
    config.client_id = "test_tenant"
    config.supabase_url = "https://test.supabase.co"
    config.supabase_service_key = "test-service-key"
    config.supabase_anon_key = "test-anon-key"
    config.currency = "USD"
    config.company_name = "Test Company"
    config.company_email = "test@example.com"
    config.timezone = "UTC"
    return config


@pytest.fixture
def mock_env_vars():
    """Set up common environment variables for testing."""
    env_vars = {
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_SERVICE_KEY': 'test-service-key',
        'SUPABASE_ANON_KEY': 'test-anon-key',
        'SUPABASE_JWT_SECRET': 'test-jwt-secret-key',
        'OPENAI_API_KEY': 'test-openai-key',
        'SENDGRID_API_KEY': 'test-sendgrid-key',
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars


# ==================== User Fixtures ====================

@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    return {
        'id': 'user_123',
        'auth_user_id': 'auth_123',
        'email': 'test@example.com',
        'name': 'Test User',
        'role': 'admin',
        'tenant_id': 'test_tenant',
        'is_active': True
    }


@pytest.fixture
def mock_regular_user():
    """Create a mock regular (non-admin) user."""
    return {
        'id': 'user_456',
        'auth_user_id': 'auth_456',
        'email': 'user@example.com',
        'name': 'Regular User',
        'role': 'user',
        'tenant_id': 'test_tenant',
        'is_active': True
    }


# ==================== Database Fixtures ====================

def create_chainable_mock():
    """Create a mock that supports method chaining for Supabase queries.

    This creates a mock object that returns itself for all query builder
    methods like select(), eq(), insert(), etc., allowing tests to
    simulate the Supabase query builder pattern.

    Returns:
        MagicMock: A chainable mock for Supabase queries.
    """
    mock = MagicMock()
    mock.select.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.delete.return_value = mock
    mock.upsert.return_value = mock
    mock.eq.return_value = mock
    mock.neq.return_value = mock
    mock.gt.return_value = mock
    mock.gte.return_value = mock
    mock.lt.return_value = mock
    mock.lte.return_value = mock
    mock.is_.return_value = mock
    mock.in_.return_value = mock
    mock.like.return_value = mock
    mock.ilike.return_value = mock
    mock.or_.return_value = mock
    mock.order.return_value = mock
    mock.limit.return_value = mock
    mock.range.return_value = mock
    mock.single.return_value = mock
    mock.maybeSingle.return_value = mock
    return mock


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client.

    Returns:
        MagicMock: A mock Supabase client that returns chainable mocks
            for table operations.
    """
    client = MagicMock()
    client.table.return_value = create_chainable_mock()
    return client


@pytest.fixture
def mock_supabase_result():
    """Create a mock Supabase query result."""
    result = MagicMock()
    result.data = []
    return result


# ==================== Service Fixtures ====================

@pytest.fixture
def mock_auth_service():
    """Create a mock AuthService."""
    service = MagicMock()
    service.verify_jwt.return_value = (True, {'sub': 'user_123'})
    service.get_user_by_auth_id = AsyncMock(return_value={
        'id': 'user_123',
        'email': 'test@example.com',
        'role': 'admin',
        'tenant_id': 'test_tenant'
    })
    return service


@pytest.fixture
def mock_crm_service():
    """Create a mock CRMService."""
    service = MagicMock()
    service.get_client.return_value = None
    service.search_clients.return_value = []
    service.get_pipeline_summary.return_value = {}
    return service


@pytest.fixture
def mock_crm_service_for_analytics():
    """Create a mock CRMService with realistic pipeline data for analytics tests.

    Returns a CRMService mock with:
    - get_pipeline_summary() returning stage-by-stage counts and values
    - get_client_stats() returning overall client statistics
    """
    from tests.fixtures.bigquery_fixtures import generate_pipeline_summary

    service = MagicMock()

    # Pipeline summary with counts and values per stage
    pipeline_summary = generate_pipeline_summary()
    service.get_pipeline_summary.return_value = pipeline_summary

    # Client stats
    total_clients = sum(stage['count'] for stage in pipeline_summary.values())
    total_value = sum(stage['value'] for stage in pipeline_summary.values())

    service.get_client_stats.return_value = {
        'total_clients': total_clients,
        'total_value': total_value,
        'by_stage': {stage: data['count'] for stage, data in pipeline_summary.items()},
        'by_source': {
            'website': 20,
            'referral': 15,
            'social_media': 10,
            'phone': 8,
            'email': 5,
        }
    }

    return service


@pytest.fixture
def mock_quote_agent():
    """Create a mock QuoteAgent."""
    agent = MagicMock()
    agent.list_quotes.return_value = []
    agent.get_quote.return_value = None
    agent.generate_quote = AsyncMock(return_value={'quote_id': 'QT-001'})
    return agent


# ==================== Tool Fixtures ====================

@pytest.fixture
def mock_supabase_tool(mock_config, mock_supabase_client):
    """Create a mock SupabaseTool with mocked client."""
    with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
        mock_get_client.return_value = mock_supabase_client

        from src.tools.supabase_tool import SupabaseTool
        tool = SupabaseTool(mock_config)
        yield tool


# ==================== BigQuery Fixtures ====================

@pytest.fixture
def mock_bigquery_client():
    """Create a mock BigQuery client using the fixtures module.

    Returns:
        MockBigQueryClient: A configurable BigQuery client mock that supports
        pattern-based response matching.

    Usage:
        def test_example(mock_bigquery_client):
            mock_bigquery_client.set_response_for_pattern(
                "hotel_rates",
                [{'hotel_count': 100, 'dest_count': 20}]
            )
    """
    from tests.fixtures.bigquery_fixtures import create_mock_bigquery_client
    return create_mock_bigquery_client()


@pytest.fixture
def mock_bigquery_client_with_data():
    """Create a BigQuery client mock pre-configured with common responses.

    Pre-configures responses for:
    - hotel_count queries: Returns hotel and destination counts
    - hotel_rates queries: Returns sample hotel rate data

    Usage:
        def test_dashboard(mock_bigquery_client_with_data):
            # Client already has hotel/destination counts configured
            result = await get_dashboard_all(config)
    """
    from tests.fixtures.bigquery_fixtures import (
        create_mock_bigquery_client,
        generate_hotel_rates,
    )

    client = create_mock_bigquery_client()

    # Pre-configure common responses
    client.set_response_for_pattern(
        "hotel_count",
        [{'hotel_count': 150, 'dest_count': 25}]
    )
    client.set_response_for_pattern(
        "hotel_rates",
        generate_hotel_rates(10)
    )

    return client


# ==================== Supabase Analytics Fixtures ====================

def create_analytics_chainable_mock(table_data: dict = None):
    """Create a chainable mock for Supabase that returns specific data per table.

    Args:
        table_data: Dict mapping table names to response data

    Returns:
        MagicMock: A mock client where client.table('name') returns appropriate data
    """
    table_data = table_data or {}

    def table_factory(table_name):
        mock = MagicMock()
        # Set up chainable methods
        mock.select.return_value = mock
        mock.insert.return_value = mock
        mock.update.return_value = mock
        mock.delete.return_value = mock
        mock.upsert.return_value = mock
        mock.eq.return_value = mock
        mock.neq.return_value = mock
        mock.gt.return_value = mock
        mock.gte.return_value = mock
        mock.lt.return_value = mock
        mock.lte.return_value = mock
        mock.is_.return_value = mock
        mock.in_.return_value = mock
        mock.like.return_value = mock
        mock.ilike.return_value = mock
        mock.or_.return_value = mock
        mock.order.return_value = mock
        mock.limit.return_value = mock
        mock.range.return_value = mock
        mock.single.return_value = mock
        mock.maybeSingle.return_value = mock

        # Set execute result based on table name
        data = table_data.get(table_name, [])
        result = MagicMock()
        result.data = data
        result.count = len(data)
        mock.execute.return_value = result

        return mock

    client = MagicMock()
    client.table.side_effect = table_factory
    return client


@pytest.fixture
def mock_supabase_for_analytics():
    """Create a SupabaseTool mock pre-configured with analytics test data.

    Configures mock responses for:
    - quotes table
    - invoices table
    - clients table
    - call_records table
    - outbound_call_queue table
    - activities table

    Usage:
        @patch('src.api.analytics_routes.SupabaseTool')
        def test_dashboard_stats(mock_supabase_class, mock_supabase_for_analytics):
            mock_supabase_class.return_value = mock_supabase_for_analytics
            # Test code here
    """
    from tests.fixtures.bigquery_fixtures import (
        generate_quotes,
        generate_invoices,
        generate_call_records,
        generate_call_queue,
        generate_clients,
        generate_activities,
    )

    # Generate test data
    table_data = {
        'quotes': generate_quotes(10, statuses=['accepted', 'sent', 'draft', 'accepted', 'sent']),
        'invoices': generate_invoices(8, statuses=['paid', 'sent', 'draft', 'paid']),
        'clients': generate_clients(15),
        'call_records': generate_call_records(12),
        'outbound_call_queue': generate_call_queue(5),
        'activities': generate_activities(10),
    }

    mock_tool = MagicMock()
    mock_tool.client = create_analytics_chainable_mock(table_data)

    return mock_tool


@pytest.fixture
def mock_supabase_empty():
    """Create a SupabaseTool mock that returns empty data for all tables.

    Useful for testing edge cases when database is empty.
    """
    mock_tool = MagicMock()
    mock_tool.client = create_analytics_chainable_mock({})
    return mock_tool


@pytest.fixture
def mock_supabase_no_client():
    """Create a SupabaseTool mock with no database client (None).

    Useful for testing graceful degradation when Supabase is unavailable.
    """
    mock_tool = MagicMock()
    mock_tool.client = None
    return mock_tool


# ==================== Analytics Config Fixture ====================

@pytest.fixture
def mock_analytics_config():
    """Create a mock ClientConfig specifically for analytics testing.

    Includes BigQuery-related configuration attributes.
    """
    config = MagicMock()
    config.client_id = "test_tenant"
    config.currency = "USD"
    config.company_name = "Test Travel Company"
    config.gcp_project_id = "test-project"
    config.shared_pricing_dataset = "pricing"
    config.timezone = "UTC"
    return config


# ==================== HTTP Client Fixtures ====================

@pytest.fixture
def test_client():
    """Create a FastAPI TestClient.

    Returns:
        TestClient: A test client for the application.
    """
    from fastapi.testclient import TestClient
    from main import app
    return TestClient(app)


@pytest.fixture
def authenticated_headers():
    """Return headers for authenticated requests."""
    return {
        'Authorization': 'Bearer test-jwt-token',
        'X-Client-ID': 'test_tenant',
        'Content-Type': 'application/json'
    }


@pytest.fixture
def admin_headers():
    """Return headers for admin API requests."""
    return {
        'X-Admin-Token': 'test-admin-token',
        'Content-Type': 'application/json'
    }


# ==================== Data Fixtures ====================

@pytest.fixture
def sample_quote():
    """Return sample quote data."""
    return {
        'quote_id': 'QT-20260121-ABC123',
        'tenant_id': 'test_tenant',
        'customer_name': 'John Doe',
        'customer_email': 'john@example.com',
        'destination': 'Cape Town',
        'start_date': '2026-03-01',
        'end_date': '2026-03-07',
        'guests': 2,
        'total_amount': 5000.00,
        'currency': 'USD',
        'status': 'draft',
        'items': [
            {'description': 'Hotel Accommodation', 'amount': 3500},
            {'description': 'Safari Tour', 'amount': 1500}
        ]
    }


@pytest.fixture
def sample_invoice():
    """Return sample invoice data."""
    return {
        'invoice_id': 'INV-20260121-XYZ789',
        'tenant_id': 'test_tenant',
        'customer_name': 'Jane Smith',
        'customer_email': 'jane@example.com',
        'total_amount': 2500.00,
        'currency': 'USD',
        'status': 'draft',
        'items': [
            {'description': 'Travel Package', 'amount': 2500}
        ]
    }


@pytest.fixture
def sample_client():
    """Return sample CRM client data."""
    return {
        'client_id': 'client_123',
        'tenant_id': 'test_tenant',
        'name': 'John Doe',
        'email': 'john@example.com',
        'phone': '+1234567890',
        'pipeline_stage': 'QUOTED',
        'source': 'website',
        'created_at': '2026-01-01T00:00:00Z'
    }


@pytest.fixture
def sample_ticket():
    """Return sample helpdesk ticket data."""
    return {
        'ticket_id': 'TKT-20260121-DEF456',
        'tenant_id': 'test_tenant',
        'customer_name': 'Bob Wilson',
        'customer_email': 'bob@example.com',
        'subject': 'Question about booking',
        'message': 'I have a question about my booking.',
        'status': 'open',
        'priority': 'normal'
    }


# ==================== Async Fixtures ====================

@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ==================== Cleanup Fixtures ====================

@pytest.fixture(autouse=True)
def reset_caches():
    """Reset any caches between tests."""
    yield
    # Clear auth service user cache
    try:
        from src.services.auth_service import _user_cache
        _user_cache.clear()
    except ImportError:
        pass

    # Clear tenant config cache
    try:
        from src.services.tenant_config_service import TenantConfigService
        if hasattr(TenantConfigService, '_instance'):
            TenantConfigService._instance = None
    except ImportError:
        pass


# ==================== Pytest Configuration ====================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    for item in items:
        # Mark integration tests
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        # Mark slow tests
        if "slow" in item.nodeid or "test_integration" in item.nodeid:
            item.add_marker(pytest.mark.slow)
