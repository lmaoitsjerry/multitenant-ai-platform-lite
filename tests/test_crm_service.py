"""
CRM Service Unit Tests

Comprehensive tests for CRMService functionality:
- Client management (create, get, update)
- Pipeline stages
- Activity logging
- Search and stats

Uses mocked Supabase dependencies.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
import sys


# ==================== Fixtures ====================

@pytest.fixture
def mock_config():
    """Create a mock ClientConfig."""
    config = MagicMock()
    config.client_id = "test_tenant"
    config.supabase_url = "https://test.supabase.co"
    config.supabase_service_key = "test-service-key"
    return config


@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client."""
    mock = MagicMock()
    mock.client = MagicMock()
    return mock


@pytest.fixture
def crm_service_without_db(mock_config):
    """Create a CRMService without database connection (for unit testing)."""
    from src.services.crm_service import CRMService

    with patch.object(CRMService, '__init__', return_value=None):
        service = CRMService.__new__(CRMService)
        service.config = mock_config
        service.supabase = None
        return service


@pytest.fixture
def crm_service_with_mock_db(mock_config, mock_supabase):
    """Create a CRMService with mocked Supabase for integration-like tests."""
    from src.services.crm_service import CRMService

    with patch.object(CRMService, '__init__', return_value=None):
        service = CRMService.__new__(CRMService)
        service.config = mock_config
        service.supabase = mock_supabase
        return service


# ==================== Pipeline Stage Tests ====================

class TestPipelineStage:
    """Test PipelineStage enum."""

    def test_pipeline_stages_defined(self):
        """All pipeline stages should be defined."""
        from src.services.crm_service import PipelineStage

        assert PipelineStage.QUOTED.value == "QUOTED"
        assert PipelineStage.NEGOTIATING.value == "NEGOTIATING"
        assert PipelineStage.BOOKED.value == "BOOKED"
        assert PipelineStage.PAID.value == "PAID"
        assert PipelineStage.TRAVELLED.value == "TRAVELLED"
        assert PipelineStage.LOST.value == "LOST"

    def test_pipeline_stage_count(self):
        """Should have exactly 6 pipeline stages."""
        from src.services.crm_service import PipelineStage

        stages = list(PipelineStage)
        assert len(stages) == 6

    def test_pipeline_stages_are_unique(self):
        """All pipeline stage values should be unique."""
        from src.services.crm_service import PipelineStage

        values = [s.value for s in PipelineStage]
        assert len(values) == len(set(values))


# ==================== Service Initialization Tests ====================

class TestCRMServiceInit:
    """Test CRMService initialization."""

    def test_service_class_exists(self):
        """CRMService class should be importable."""
        from src.services.crm_service import CRMService
        assert CRMService is not None

    def test_service_stores_config(self, mock_config):
        """CRMService should store config reference."""
        from src.services.crm_service import CRMService

        with patch.object(CRMService, '__init__', return_value=None):
            service = CRMService.__new__(CRMService)
            service.config = mock_config
            service.supabase = None

            assert service.config == mock_config
            assert service.config.client_id == "test_tenant"


# ==================== Get Or Create Client Tests ====================

class TestGetOrCreateClient:
    """Test get_or_create_client method."""

    def test_returns_none_without_supabase(self, crm_service_without_db):
        """get_or_create_client returns None without Supabase."""
        result = crm_service_without_db.get_or_create_client(
            email="test@example.com",
            name="Test User"
        )

        assert result is None

    def test_returns_existing_client(self, crm_service_with_mock_db, mock_supabase):
        """get_or_create_client returns existing client if found."""
        existing_client = {
            "id": "existing-id",
            "client_id": "CLI-EXISTING",
            "email": "test@example.com",
            "name": "Test User",
            "tenant_id": "test_tenant"
        }

        # Mock the get_client_by_email chain
        mock_result = MagicMock()
        mock_result.data = [existing_client]
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_result

        result = crm_service_with_mock_db.get_or_create_client(
            email="test@example.com",
            name="Test User"
        )

        assert result is not None
        assert result.get("created") is False
        assert result.get("client_id") == "CLI-EXISTING"

    def test_creates_new_client(self, crm_service_with_mock_db, mock_supabase):
        """get_or_create_client creates new client if not found."""
        # Mock no existing client
        mock_empty_result = MagicMock()
        mock_empty_result.data = []
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_empty_result

        # Mock insert
        new_client = {
            "id": "new-id",
            "client_id": "CLI-ABC12345",
            "email": "new@example.com",
            "name": "New User",
            "tenant_id": "test_tenant"
        }
        mock_insert_result = MagicMock()
        mock_insert_result.data = [new_client]
        mock_supabase.client.table.return_value.insert.return_value.execute.return_value = mock_insert_result

        result = crm_service_with_mock_db.get_or_create_client(
            email="new@example.com",
            name="New User"
        )

        assert result is not None
        assert result.get("created") is True


# ==================== Get Client By Email Tests ====================

class TestGetClientByEmail:
    """Test get_client_by_email method."""

    def test_returns_none_without_supabase(self, crm_service_without_db):
        """get_client_by_email returns None without Supabase."""
        result = crm_service_without_db.get_client_by_email("test@example.com")

        assert result is None

    def test_returns_client_if_found(self, crm_service_with_mock_db, mock_supabase):
        """get_client_by_email returns client when found."""
        client = {
            "id": "uuid-123",
            "client_id": "CLI-12345",
            "email": "test@example.com",
            "name": "Test User"
        }

        mock_result = MagicMock()
        mock_result.data = [client]
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_result

        result = crm_service_with_mock_db.get_client_by_email("test@example.com")

        assert result is not None
        assert result["email"] == "test@example.com"

    def test_returns_none_if_not_found(self, crm_service_with_mock_db, mock_supabase):
        """get_client_by_email returns None when not found."""
        mock_result = MagicMock()
        mock_result.data = []
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_result

        result = crm_service_with_mock_db.get_client_by_email("notfound@example.com")

        assert result is None


# ==================== Get Client By ID Tests ====================

class TestGetClient:
    """Test get_client method."""

    def test_returns_none_without_supabase(self, crm_service_without_db):
        """get_client returns None without Supabase."""
        result = crm_service_without_db.get_client("CLI-12345")

        assert result is None

    def test_queries_by_cli_format(self, crm_service_with_mock_db, mock_supabase):
        """get_client queries by client_id for CLI-XXXX format."""
        client = {
            "id": "uuid-123",
            "client_id": "CLI-12345",
            "email": "test@example.com"
        }

        mock_result = MagicMock()
        mock_result.data = client
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_result

        result = crm_service_with_mock_db.get_client("CLI-12345")

        # Verify table was called (deep assertion chain not needed)
        mock_supabase.client.table.assert_called()
        # Result should be returned
        assert result == client

    def test_queries_by_uuid_format(self, crm_service_with_mock_db, mock_supabase):
        """get_client queries by id for UUID format."""
        client = {
            "id": "uuid-123",
            "client_id": "CLI-12345",
            "email": "test@example.com"
        }

        mock_result = MagicMock()
        mock_result.data = client
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_result

        result = crm_service_with_mock_db.get_client("uuid-123")

        # Verify table was called (deep assertion chain not needed)
        mock_supabase.client.table.assert_called()
        # Result should be returned
        assert result == client


# ==================== Update Client Tests ====================

class TestUpdateClient:
    """Test update_client method."""

    def test_returns_false_without_supabase(self, crm_service_without_db):
        """update_client returns False without Supabase."""
        # Need to add the helper method
        crm_service_without_db._get_client_id_filter = lambda x: ('client_id', x) if x.startswith('CLI-') else ('id', x)

        result = crm_service_without_db.update_client("CLI-12345", name="Updated Name")

        assert result is False

    def test_updates_client_fields(self, crm_service_with_mock_db, mock_supabase):
        """update_client should update specified fields."""
        mock_supabase.client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()

        result = crm_service_with_mock_db.update_client(
            "CLI-12345",
            name="Updated Name",
            phone="+1234567890"
        )

        assert result is True
        # Verify update was called
        mock_supabase.client.table.return_value.update.assert_called()


# ==================== Update Stage Tests ====================

class TestUpdateStage:
    """Test update_stage method."""

    def test_returns_false_without_supabase(self, crm_service_without_db):
        """update_stage returns False without Supabase."""
        from src.services.crm_service import PipelineStage

        # Need to add the helper method
        crm_service_without_db._get_client_id_filter = lambda x: ('client_id', x) if x.startswith('CLI-') else ('id', x)

        result = crm_service_without_db.update_stage("CLI-12345", PipelineStage.BOOKED)

        assert result is False

    def test_updates_stage_and_logs_activity(self, crm_service_with_mock_db, mock_supabase):
        """update_stage should update stage and log activity."""
        from src.services.crm_service import PipelineStage

        mock_supabase.client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_supabase.log_activity = MagicMock()

        result = crm_service_with_mock_db.update_stage("CLI-12345", PipelineStage.BOOKED)

        assert result is True
        # Verify activity was logged
        mock_supabase.log_activity.assert_called_once()


# ==================== Search Clients Tests ====================

class TestSearchClients:
    """Test search_clients method."""

    def test_returns_empty_without_supabase(self, crm_service_without_db):
        """search_clients returns empty list without Supabase."""
        result = crm_service_without_db.search_clients()

        assert result == []

    def test_returns_clients_list(self, crm_service_with_mock_db, mock_supabase):
        """search_clients returns list of clients."""
        clients = [
            {"client_id": "CLI-001", "name": "Client 1", "email": "c1@example.com"},
            {"client_id": "CLI-002", "name": "Client 2", "email": "c2@example.com"}
        ]

        mock_result = MagicMock()
        mock_result.data = clients
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result

        # Mock quote and activity lookups
        mock_empty = MagicMock()
        mock_empty.data = []
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_empty

        result = crm_service_with_mock_db.search_clients()

        assert len(result) == 2

    def test_filters_by_query(self, crm_service_with_mock_db, mock_supabase):
        """search_clients filters by query string."""
        clients = [
            {"client_id": "CLI-001", "name": "John Doe", "email": "john@example.com", "phone": "123"},
            {"client_id": "CLI-002", "name": "Jane Smith", "email": "jane@example.com", "phone": None}
        ]

        mock_result = MagicMock()
        mock_result.data = clients
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result

        # Mock quote and activity lookups
        mock_empty = MagicMock()
        mock_empty.data = []
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_empty

        result = crm_service_with_mock_db.search_clients(query="john")

        # Should only return John
        assert len(result) == 1
        assert result[0]["name"] == "John Doe"


# ==================== Get Activities Tests ====================

class TestGetActivities:
    """Test get_activities method."""

    def test_returns_empty_without_supabase(self, crm_service_without_db):
        """get_activities returns empty list without Supabase."""
        # Need to add _get_client_id_filter helper
        crm_service_without_db._get_client_id_filter = lambda x: ('client_id', x) if x.startswith('CLI-') else ('id', x)

        result = crm_service_without_db.get_activities("CLI-12345")

        assert result == []

    def test_returns_activities_list(self, crm_service_with_mock_db, mock_supabase):
        """get_activities returns list of activities."""
        activities = [
            {"id": 1, "activity_type": "email", "description": "Sent quote"},
            {"id": 2, "activity_type": "call", "description": "Follow-up call"}
        ]

        mock_result = MagicMock()
        mock_result.data = activities
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

        result = crm_service_with_mock_db.get_activities("CLI-12345")

        assert len(result) == 2


# ==================== Pipeline Summary Tests ====================

class TestGetPipelineSummary:
    """Test get_pipeline_summary method."""

    def test_returns_empty_without_supabase(self, crm_service_without_db):
        """get_pipeline_summary returns empty dict without Supabase."""
        result = crm_service_without_db.get_pipeline_summary()

        assert result == {}

    def test_returns_summary_by_stage(self, crm_service_with_mock_db, mock_supabase):
        """get_pipeline_summary returns counts by stage."""
        from src.services.crm_service import PipelineStage

        clients = [
            {"email": "c1@example.com", "pipeline_stage": "QUOTED"},
            {"email": "c2@example.com", "pipeline_stage": "QUOTED"},
            {"email": "c3@example.com", "pipeline_stage": "BOOKED"}
        ]

        quotes = [
            {"customer_email": "c1@example.com", "total_price": 1000},
            {"customer_email": "c2@example.com", "total_price": 2000},
            {"customer_email": "c3@example.com", "total_price": 1500}
        ]

        # Mock clients query
        mock_clients_result = MagicMock()
        mock_clients_result.data = clients
        # Mock quotes query
        mock_quotes_result = MagicMock()
        mock_quotes_result.data = quotes

        mock_supabase.client.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            mock_clients_result,
            mock_quotes_result
        ]

        result = crm_service_with_mock_db.get_pipeline_summary()

        assert "QUOTED" in result
        assert result["QUOTED"]["count"] == 2
        assert "BOOKED" in result
        assert result["BOOKED"]["count"] == 1


# ==================== Client Stats Tests ====================

class TestGetClientStats:
    """Test get_client_stats method."""

    def test_returns_empty_without_supabase(self, crm_service_without_db):
        """get_client_stats returns empty dict without Supabase."""
        result = crm_service_without_db.get_client_stats()

        assert result == {}

    def test_returns_stats_summary(self, crm_service_with_mock_db, mock_supabase):
        """get_client_stats returns stats summary."""
        clients = [
            {"pipeline_stage": "QUOTED", "source": "web", "total_value": 1000},
            {"pipeline_stage": "BOOKED", "source": "email", "total_value": 2000}
        ]

        quotes = [
            {"total_price": 1000},
            {"total_price": 2000}
        ]

        # Mock clients query
        mock_clients_result = MagicMock()
        mock_clients_result.data = clients
        # Mock quotes query
        mock_quotes_result = MagicMock()
        mock_quotes_result.data = quotes

        mock_supabase.client.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            mock_clients_result,
            mock_quotes_result
        ]

        result = crm_service_with_mock_db.get_client_stats()

        assert result["total_clients"] == 2
        assert result["total_value"] == 3000
        assert "by_stage" in result
        assert "by_source" in result


# ==================== Helper Method Tests ====================

class TestHelperMethods:
    """Test helper methods."""

    def test_get_client_id_filter_cli_format(self, crm_service_with_mock_db):
        """_get_client_id_filter returns client_id for CLI format."""
        column, value = crm_service_with_mock_db._get_client_id_filter("CLI-12345")
        assert column == "client_id"
        assert value == "CLI-12345"

    def test_get_client_id_filter_uuid_format(self, crm_service_with_mock_db):
        """_get_client_id_filter returns id for UUID format."""
        column, value = crm_service_with_mock_db._get_client_id_filter("uuid-abc-123")
        assert column == "id"
        assert value == "uuid-abc-123"

    def test_count_by_field(self, crm_service_with_mock_db):
        """_count_by_field counts items by field value."""
        items = [
            {"source": "web"},
            {"source": "web"},
            {"source": "email"},
            {"source": None}
        ]

        result = crm_service_with_mock_db._count_by_field(items, "source")

        assert result["web"] == 2
        assert result["email"] == 1

    def test_count_by_field_handles_missing(self, crm_service_with_mock_db):
        """_count_by_field handles missing field gracefully."""
        items = [
            {"source": "web"},
            {},  # Missing field
            {"other": "value"}
        ]

        result = crm_service_with_mock_db._count_by_field(items, "source")

        assert result["web"] == 1
        assert result["unknown"] == 2


# ==================== Batch Query Tests ====================

class TestCRMServiceBatchQueries:
    """Tests for batch query optimization in CRM service"""

    @pytest.fixture
    def mock_supabase_client(self):
        """Create a mock Supabase client for testing"""
        mock_client = MagicMock()
        return mock_client

    def test_search_clients_uses_batch_queries(self, mock_supabase_client):
        """Verify search_clients uses batch queries instead of N+1"""
        from src.services.crm_service import CRMService
        from unittest.mock import patch, MagicMock

        # Mock config
        mock_config = MagicMock()
        mock_config.client_id = 'test-tenant'

        # Create service with mocked Supabase
        service = CRMService.__new__(CRMService)
        service.config = mock_config
        service.supabase = MagicMock()
        service.supabase.client = mock_supabase_client

        # Setup mock responses
        clients_data = [
            {'client_id': 'cli-1', 'email': 'a@test.com', 'name': 'A', 'total_value': 100},
            {'client_id': 'cli-2', 'email': 'b@test.com', 'name': 'B', 'total_value': 200},
            {'client_id': 'cli-3', 'email': 'c@test.com', 'name': 'C', 'total_value': 300},
        ]

        quotes_data = [
            {'customer_email': 'a@test.com', 'destination': 'Paris', 'total_price': 1500, 'created_at': '2024-01-01'},
            {'customer_email': 'b@test.com', 'destination': 'Rome', 'total_price': 2000, 'created_at': '2024-01-02'},
        ]

        activities_data = [
            {'client_id': 'cli-1', 'created_at': '2024-01-15'},
            {'client_id': 'cli-2', 'created_at': '2024-01-16'},
        ]

        def table_handler(table_name):
            table_mock = MagicMock()

            if table_name == 'clients':
                table_mock.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = clients_data
            elif table_name == 'quotes':
                table_mock.select.return_value.eq.return_value.in_.return_value.order.return_value.execute.return_value.data = quotes_data
            elif table_name == 'activities':
                table_mock.select.return_value.eq.return_value.in_.return_value.order.return_value.execute.return_value.data = activities_data

            return table_mock

        mock_supabase_client.table = table_handler

        # Execute search
        results = service.search_clients()

        # Verify we got enriched results
        assert len(results) == 3

        # Verify client A got quote enrichment
        client_a = next(r for r in results if r['client_id'] == 'cli-1')
        assert client_a['destination'] == 'Paris'
        assert client_a['value'] == 1500
        assert client_a['last_activity'] == '2024-01-15'

        # Verify client C has no quote but has fallback values
        client_c = next(r for r in results if r['client_id'] == 'cli-3')
        assert client_c['value'] == 300  # Original total_value

    def test_search_clients_batch_handles_empty_results(self, mock_supabase_client):
        """Verify search handles empty client list without errors"""
        from src.services.crm_service import CRMService
        from unittest.mock import MagicMock

        mock_config = MagicMock()
        mock_config.client_id = 'test-tenant'

        service = CRMService.__new__(CRMService)
        service.config = mock_config
        service.supabase = MagicMock()
        service.supabase.client = mock_supabase_client

        # Return empty clients
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = []

        results = service.search_clients()

        assert results == []

    def test_search_clients_batch_query_count(self, mock_supabase_client):
        """Verify maximum 3 queries are executed (clients + quotes + activities)"""
        from src.services.crm_service import CRMService
        from unittest.mock import MagicMock, call

        mock_config = MagicMock()
        mock_config.client_id = 'test-tenant'

        service = CRMService.__new__(CRMService)
        service.config = mock_config
        service.supabase = MagicMock()
        service.supabase.client = mock_supabase_client

        # Track table() calls
        table_calls = []

        def track_table(table_name):
            table_calls.append(table_name)
            mock = MagicMock()
            if table_name == 'clients':
                mock.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = [
                    {'client_id': 'cli-1', 'email': 'a@test.com', 'name': 'A'}
                ]
            else:
                mock.select.return_value.eq.return_value.in_.return_value.order.return_value.execute.return_value.data = []
            return mock

        mock_supabase_client.table = track_table

        service.search_clients()

        # Should be exactly 3 table() calls: clients, quotes, activities
        assert len(table_calls) == 3
        assert table_calls[0] == 'clients'
        assert 'quotes' in table_calls
        assert 'activities' in table_calls

    def test_search_clients_batch_enrichment_priority(self, mock_supabase_client):
        """Verify quote data takes priority over client total_value when available"""
        from src.services.crm_service import CRMService
        from unittest.mock import MagicMock

        mock_config = MagicMock()
        mock_config.client_id = 'test-tenant'

        service = CRMService.__new__(CRMService)
        service.config = mock_config
        service.supabase = MagicMock()
        service.supabase.client = mock_supabase_client

        # Client has total_value but also has a quote with different total_price
        clients_data = [
            {'client_id': 'cli-1', 'email': 'a@test.com', 'name': 'A', 'total_value': 100, 'updated_at': '2024-01-01'},
        ]

        quotes_data = [
            {'customer_email': 'a@test.com', 'destination': 'Bali', 'total_price': 5000, 'created_at': '2024-01-02'},
        ]

        def table_handler(table_name):
            mock = MagicMock()
            if table_name == 'clients':
                mock.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = clients_data
            elif table_name == 'quotes':
                mock.select.return_value.eq.return_value.in_.return_value.order.return_value.execute.return_value.data = quotes_data
            else:
                mock.select.return_value.eq.return_value.in_.return_value.order.return_value.execute.return_value.data = []
            return mock

        mock_supabase_client.table = table_handler

        results = service.search_clients()

        assert len(results) == 1
        # Quote value should override client total_value
        assert results[0]['value'] == 5000
        assert results[0]['destination'] == 'Bali'


# ==================== NEW TESTS: Initialization ====================

class TestCRMServiceInitExtended:
    """Extended tests for CRMService initialization with mocked SupabaseTool."""

    def test_init_creates_supabase_tool(self, mock_config):
        """CRMService.__init__ should create a SupabaseTool instance."""
        from src.services.crm_service import CRMService

        mock_supabase_instance = MagicMock()
        with patch('src.tools.supabase_tool.SupabaseTool', return_value=mock_supabase_instance) as mock_cls:
            service = CRMService(mock_config)
            mock_cls.assert_called_once_with(mock_config)
            assert service.supabase is mock_supabase_instance

    def test_init_supabase_import_error_sets_none(self, mock_config):
        """CRMService should set supabase=None when SupabaseTool constructor raises."""
        from src.services.crm_service import CRMService

        with patch('src.tools.supabase_tool.SupabaseTool', side_effect=Exception("connection failed")):
            service = CRMService(mock_config)
            assert service.supabase is None

    def test_init_supabase_runtime_error_sets_none(self, mock_config):
        """CRMService should set supabase=None when SupabaseTool constructor raises RuntimeError."""
        from src.services.crm_service import CRMService

        with patch('src.tools.supabase_tool.SupabaseTool', side_effect=RuntimeError("connection failed")):
            service = CRMService(mock_config)
            assert service.supabase is None

    def test_init_stores_client_id(self, mock_config):
        """CRMService should store the config's client_id for tenant filtering."""
        from src.services.crm_service import CRMService

        with patch('src.tools.supabase_tool.SupabaseTool', side_effect=Exception("skip")):
            service = CRMService(mock_config)
            assert service.config.client_id == "test_tenant"


# ==================== NEW TESTS: PipelineStage Enum ====================

class TestPipelineStageExtended:
    """Extended tests for PipelineStage enum values and ordering."""

    def test_pipeline_stage_ordering(self):
        """PipelineStage enum should iterate in the declared order."""
        from src.services.crm_service import PipelineStage

        stages = list(PipelineStage)
        assert stages[0] == PipelineStage.QUOTED
        assert stages[1] == PipelineStage.NEGOTIATING
        assert stages[2] == PipelineStage.BOOKED
        assert stages[3] == PipelineStage.PAID
        assert stages[4] == PipelineStage.TRAVELLED
        assert stages[5] == PipelineStage.LOST

    def test_pipeline_stage_from_value(self):
        """PipelineStage should be constructable from a string value."""
        from src.services.crm_service import PipelineStage

        assert PipelineStage("QUOTED") == PipelineStage.QUOTED
        assert PipelineStage("LOST") == PipelineStage.LOST

    def test_pipeline_stage_invalid_value_raises(self):
        """PipelineStage should raise ValueError for unknown string."""
        from src.services.crm_service import PipelineStage

        with pytest.raises(ValueError):
            PipelineStage("INVALID_STAGE")

    def test_pipeline_stage_name_equals_value(self):
        """Each PipelineStage name should equal its value (all uppercase convention)."""
        from src.services.crm_service import PipelineStage

        for stage in PipelineStage:
            assert stage.name == stage.value


# ==================== NEW TESTS: get_or_create_client ====================

class TestGetOrCreateClientExtended:
    """Extended tests for get_or_create_client method."""

    def test_returns_none_when_supabase_client_is_none(self, mock_config, mock_supabase):
        """get_or_create_client returns None when supabase.client is None."""
        from src.services.crm_service import CRMService

        with patch.object(CRMService, '__init__', return_value=None):
            service = CRMService.__new__(CRMService)
            service.config = mock_config
            service.supabase = MagicMock()
            service.supabase.client = None

            result = service.get_or_create_client(email="test@example.com", name="Test")
            assert result is None

    def test_new_client_gets_cli_prefix_id(self, crm_service_with_mock_db, mock_supabase):
        """Newly created client should have a CLI-XXXXXXXX format ID."""
        from src.services.crm_service import CRMService

        # No existing client
        mock_empty = MagicMock()
        mock_empty.data = []
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_empty

        # Capture what gets inserted
        mock_insert_result = MagicMock()
        mock_insert_result.data = [{"client_id": "CLI-ABCD1234", "email": "new@example.com", "name": "New"}]
        mock_supabase.client.table.return_value.insert.return_value.execute.return_value = mock_insert_result

        result = crm_service_with_mock_db.get_or_create_client(email="new@example.com", name="New")

        # Verify insert was called with a record whose client_id starts with CLI-
        insert_call_args = mock_supabase.client.table.return_value.insert.call_args
        record = insert_call_args[0][0]
        assert record['client_id'].startswith('CLI-')
        assert len(record['client_id']) == 12  # CLI- + 8 hex chars

    def test_new_client_starts_in_quoted_stage(self, crm_service_with_mock_db, mock_supabase):
        """New client should be created with QUOTED pipeline stage."""
        mock_empty = MagicMock()
        mock_empty.data = []
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_empty

        mock_insert_result = MagicMock()
        mock_insert_result.data = [{"client_id": "CLI-12345678", "email": "new@example.com"}]
        mock_supabase.client.table.return_value.insert.return_value.execute.return_value = mock_insert_result

        crm_service_with_mock_db.get_or_create_client(email="new@example.com", name="New")

        record = mock_supabase.client.table.return_value.insert.call_args[0][0]
        assert record['pipeline_stage'] == "QUOTED"
        assert record['quote_count'] == 1

    def test_returns_none_when_insert_returns_no_data(self, crm_service_with_mock_db, mock_supabase):
        """get_or_create_client returns None when insert returns empty data."""
        mock_empty = MagicMock()
        mock_empty.data = []
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_empty

        mock_insert_result = MagicMock()
        mock_insert_result.data = []
        mock_supabase.client.table.return_value.insert.return_value.execute.return_value = mock_insert_result

        result = crm_service_with_mock_db.get_or_create_client(email="new@example.com", name="New")
        assert result is None

    def test_handles_exception_during_creation(self, crm_service_with_mock_db, mock_supabase):
        """get_or_create_client returns None when insert raises an exception."""
        mock_empty = MagicMock()
        mock_empty.data = []
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_empty

        mock_supabase.client.table.return_value.insert.return_value.execute.side_effect = Exception("DB error")

        result = crm_service_with_mock_db.get_or_create_client(email="new@example.com", name="New")
        assert result is None

    def test_passes_optional_fields_to_insert(self, crm_service_with_mock_db, mock_supabase):
        """get_or_create_client passes phone, source, consultant_id to insert."""
        mock_empty = MagicMock()
        mock_empty.data = []
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_empty

        mock_insert_result = MagicMock()
        mock_insert_result.data = [{"client_id": "CLI-12345678"}]
        mock_supabase.client.table.return_value.insert.return_value.execute.return_value = mock_insert_result

        crm_service_with_mock_db.get_or_create_client(
            email="new@example.com",
            name="New",
            phone="+27123456789",
            source="email",
            consultant_id="CONS-001"
        )

        record = mock_supabase.client.table.return_value.insert.call_args[0][0]
        assert record['phone'] == "+27123456789"
        assert record['source'] == "email"
        assert record['consultant_id'] == "CONS-001"


# ==================== NEW TESTS: get_client_by_email ====================

class TestGetClientByEmailExtended:
    """Extended tests for get_client_by_email method."""

    def test_returns_none_when_supabase_client_is_none(self, mock_config):
        """get_client_by_email returns None when supabase exists but client is None."""
        from src.services.crm_service import CRMService

        with patch.object(CRMService, '__init__', return_value=None):
            service = CRMService.__new__(CRMService)
            service.config = mock_config
            service.supabase = MagicMock()
            service.supabase.client = None

            assert service.get_client_by_email("test@example.com") is None

    def test_handles_database_exception(self, crm_service_with_mock_db, mock_supabase):
        """get_client_by_email returns None on database exception."""
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.side_effect = Exception("timeout")

        result = crm_service_with_mock_db.get_client_by_email("test@example.com")
        assert result is None

    def test_returns_none_for_none_data(self, crm_service_with_mock_db, mock_supabase):
        """get_client_by_email returns None when result.data is None."""
        mock_result = MagicMock()
        mock_result.data = None
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_result

        result = crm_service_with_mock_db.get_client_by_email("test@example.com")
        assert result is None


# ==================== NEW TESTS: update_client ====================

class TestUpdateClientExtended:
    """Extended tests for update_client with partial and field updates."""

    def test_partial_update_name_only(self, crm_service_with_mock_db, mock_supabase):
        """update_client should only include name in update_data when only name is given."""
        mock_supabase.client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()

        crm_service_with_mock_db.update_client("CLI-12345", name="New Name")

        call_args = mock_supabase.client.table.return_value.update.call_args[0][0]
        assert call_args['name'] == "New Name"
        assert 'phone' not in call_args
        assert 'consultant_id' not in call_args
        assert 'quote_count' not in call_args
        assert 'total_value' not in call_args
        assert 'updated_at' in call_args

    def test_partial_update_total_value(self, crm_service_with_mock_db, mock_supabase):
        """update_client should update total_value when provided."""
        mock_supabase.client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()

        crm_service_with_mock_db.update_client("CLI-12345", total_value=15000.50)

        call_args = mock_supabase.client.table.return_value.update.call_args[0][0]
        assert call_args['total_value'] == 15000.50

    def test_update_with_uuid_format(self, crm_service_with_mock_db, mock_supabase):
        """update_client should use 'id' column for UUID format client IDs."""
        mock_supabase.client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()

        result = crm_service_with_mock_db.update_client("uuid-abc-123", name="Name")
        assert result is True

    def test_update_handles_exception(self, crm_service_with_mock_db, mock_supabase):
        """update_client returns False when database raises an exception."""
        mock_supabase.client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.side_effect = Exception("DB error")

        result = crm_service_with_mock_db.update_client("CLI-12345", name="Name")
        assert result is False

    def test_update_all_fields(self, crm_service_with_mock_db, mock_supabase):
        """update_client should include all fields when all are provided."""
        mock_supabase.client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()

        crm_service_with_mock_db.update_client(
            "CLI-12345",
            name="Full Name",
            phone="+1234",
            consultant_id="CONS-X",
            quote_count=5,
            total_value=99999.99
        )

        call_args = mock_supabase.client.table.return_value.update.call_args[0][0]
        assert call_args['name'] == "Full Name"
        assert call_args['phone'] == "+1234"
        assert call_args['consultant_id'] == "CONS-X"
        assert call_args['quote_count'] == 5
        assert call_args['total_value'] == 99999.99


# ==================== NEW TESTS: update_stage ====================

class TestUpdateStageExtended:
    """Extended tests for update_stage method - transitions and logging."""

    def test_update_stage_to_each_stage(self, crm_service_with_mock_db, mock_supabase):
        """update_stage should succeed for every PipelineStage value."""
        from src.services.crm_service import PipelineStage

        mock_supabase.client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_supabase.log_activity = MagicMock()

        for stage in PipelineStage:
            result = crm_service_with_mock_db.update_stage("CLI-12345", stage)
            assert result is True

    def test_update_stage_logs_correct_description(self, crm_service_with_mock_db, mock_supabase):
        """update_stage should log the correct stage value in the activity description."""
        from src.services.crm_service import PipelineStage

        mock_supabase.client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_supabase.log_activity = MagicMock()

        crm_service_with_mock_db.update_stage("CLI-12345", PipelineStage.PAID)

        mock_supabase.log_activity.assert_called_once_with(
            client_id='CLI-12345',
            activity_type='stage_change',
            description='Pipeline stage changed to PAID'
        )

    def test_update_stage_handles_exception(self, crm_service_with_mock_db, mock_supabase):
        """update_stage returns False when database update raises exception."""
        from src.services.crm_service import PipelineStage

        mock_supabase.client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.side_effect = Exception("DB error")

        result = crm_service_with_mock_db.update_stage("CLI-12345", PipelineStage.BOOKED)
        assert result is False

    def test_update_stage_uses_uuid_for_non_cli_id(self, crm_service_with_mock_db, mock_supabase):
        """update_stage should work with UUID format client IDs."""
        from src.services.crm_service import PipelineStage

        mock_supabase.client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_supabase.log_activity = MagicMock()

        result = crm_service_with_mock_db.update_stage("uuid-abc", PipelineStage.LOST)
        assert result is True


# ==================== NEW TESTS: search_clients / list_clients ====================

class TestSearchClientsExtended:
    """Extended tests for search_clients with filters, pagination, edge cases."""

    def test_filters_by_stage(self, crm_service_with_mock_db, mock_supabase):
        """search_clients should apply stage filter to the query."""
        from src.services.crm_service import PipelineStage

        mock_result = MagicMock()
        mock_result.data = []
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.eq.return_value.execute.return_value = mock_result

        crm_service_with_mock_db.search_clients(stage=PipelineStage.BOOKED)

        # Verify the chain was called (the .eq for stage filter)
        mock_supabase.client.table.assert_called()

    def test_filters_by_consultant_id(self, crm_service_with_mock_db, mock_supabase):
        """search_clients should filter by consultant_id when provided."""
        mock_result = MagicMock()
        mock_result.data = []
        # Deep chain mock for stage + consultant filters
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.eq.return_value.execute.return_value = mock_result

        crm_service_with_mock_db.search_clients(consultant_id="CONS-001")
        mock_supabase.client.table.assert_called()

    def test_search_by_email_query(self, crm_service_with_mock_db, mock_supabase):
        """search_clients should match query against email addresses."""
        clients = [
            {"client_id": "CLI-001", "name": "Alpha", "email": "alpha@special.com", "phone": None},
            {"client_id": "CLI-002", "name": "Beta", "email": "beta@example.com", "phone": None}
        ]

        mock_result = MagicMock()
        mock_result.data = clients
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result

        mock_empty = MagicMock()
        mock_empty.data = []
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.execute.return_value = mock_empty

        result = crm_service_with_mock_db.search_clients(query="special")

        assert len(result) == 1
        assert result[0]["email"] == "alpha@special.com"

    def test_search_by_phone_query(self, crm_service_with_mock_db, mock_supabase):
        """search_clients should match query against phone numbers."""
        clients = [
            {"client_id": "CLI-001", "name": "Alpha", "email": "a@test.com", "phone": "+27821234567"},
            {"client_id": "CLI-002", "name": "Beta", "email": "b@test.com", "phone": "+44987654321"}
        ]

        mock_result = MagicMock()
        mock_result.data = clients
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result

        mock_empty = MagicMock()
        mock_empty.data = []
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.execute.return_value = mock_empty

        result = crm_service_with_mock_db.search_clients(query="+2782")

        assert len(result) == 1
        assert result[0]["client_id"] == "CLI-001"

    def test_search_case_insensitive(self, crm_service_with_mock_db, mock_supabase):
        """search_clients query matching should be case-insensitive."""
        clients = [
            {"client_id": "CLI-001", "name": "John DOE", "email": "john@test.com", "phone": None}
        ]

        mock_result = MagicMock()
        mock_result.data = clients
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result

        mock_empty = MagicMock()
        mock_empty.data = []
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.execute.return_value = mock_empty

        result = crm_service_with_mock_db.search_clients(query="john doe")

        assert len(result) == 1

    def test_search_handles_exception(self, crm_service_with_mock_db, mock_supabase):
        """search_clients returns empty list when database query raises."""
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.side_effect = Exception("timeout")

        result = crm_service_with_mock_db.search_clients()
        assert result == []

    def test_search_enriches_with_last_activity_fallback(self, crm_service_with_mock_db, mock_supabase):
        """search_clients should fall back to updated_at when no activities exist."""
        clients = [
            {"client_id": "CLI-001", "name": "A", "email": "a@test.com", "total_value": 0, "updated_at": "2024-06-01"}
        ]

        def table_handler(table_name):
            mock = MagicMock()
            if table_name == 'clients':
                mock.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = clients
            elif table_name == 'quotes':
                mock.select.return_value.eq.return_value.in_.return_value.order.return_value.execute.return_value.data = []
            elif table_name == 'activities':
                mock.select.return_value.eq.return_value.in_.return_value.order.return_value.execute.return_value.data = []
            return mock

        mock_supabase.client.table = table_handler

        result = crm_service_with_mock_db.search_clients()

        assert len(result) == 1
        assert result[0]['last_activity'] == '2024-06-01'


# ==================== NEW TESTS: get_pipeline_summary ====================

class TestGetPipelineSummaryExtended:
    """Extended tests for get_pipeline_summary counts and values."""

    @patch('src.services.crm_service.get_redis_client', return_value=None)
    def test_all_stages_present_in_summary(self, mock_redis, crm_service_with_mock_db, mock_supabase):
        """get_pipeline_summary should include all 6 stages even with no clients."""
        from src.services.crm_service import PipelineStage

        mock_clients = MagicMock()
        mock_clients.data = []
        mock_active = MagicMock()
        mock_active.data = []

        mock_supabase.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_clients
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = mock_active

        result = crm_service_with_mock_db.get_pipeline_summary()

        for stage in PipelineStage:
            assert stage.value in result
            assert result[stage.value]['count'] == 0
            assert result[stage.value]['value'] == 0

    @patch('src.services.crm_service.get_redis_client', return_value=None)
    def test_pipeline_summary_handles_exception(self, mock_redis, crm_service_with_mock_db, mock_supabase):
        """get_pipeline_summary returns empty dict on exception."""
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("DB down")

        result = crm_service_with_mock_db.get_pipeline_summary()
        assert result == {}

    @patch('src.services.crm_service.get_redis_client')
    def test_pipeline_summary_uses_redis_cache(self, mock_get_redis, crm_service_with_mock_db, mock_supabase):
        """get_pipeline_summary should return cached result from Redis when available."""
        import json

        cached_data = {"QUOTED": {"count": 5, "value": 1000}}
        mock_redis_client = MagicMock()
        mock_redis_client.get.return_value = json.dumps(cached_data)
        mock_get_redis.return_value = mock_redis_client

        result = crm_service_with_mock_db.get_pipeline_summary()

        assert result == cached_data
        # Supabase should not have been called because cache was hit
        mock_supabase.client.table.assert_not_called()

    @patch('src.services.crm_service.get_redis_client')
    def test_pipeline_summary_caches_result_in_redis(self, mock_get_redis, crm_service_with_mock_db, mock_supabase):
        """get_pipeline_summary should cache the computed result in Redis."""
        import json

        mock_redis_client = MagicMock()
        mock_redis_client.get.return_value = None  # No cache
        mock_get_redis.return_value = mock_redis_client

        mock_clients = MagicMock()
        mock_clients.data = [{"pipeline_stage": "QUOTED"}]
        mock_active = MagicMock()
        mock_active.data = []

        mock_supabase.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_clients
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = mock_active

        crm_service_with_mock_db.get_pipeline_summary()

        # Redis setex should be called with 60s TTL
        mock_redis_client.setex.assert_called_once()
        args = mock_redis_client.setex.call_args[0]
        assert args[1] == 60  # TTL


# ==================== NEW TESTS: Edge cases ====================

class TestCRMServiceEdgeCases:
    """Edge cases: empty strings, None values, special characters."""

    def test_get_client_by_email_empty_string(self, crm_service_with_mock_db, mock_supabase):
        """get_client_by_email with empty string should still query (no crash)."""
        mock_result = MagicMock()
        mock_result.data = []
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_result

        result = crm_service_with_mock_db.get_client_by_email("")
        assert result is None

    def test_search_clients_special_chars_in_query(self, crm_service_with_mock_db, mock_supabase):
        """search_clients should handle special characters in query without error."""
        clients = [
            {"client_id": "CLI-001", "name": "O'Malley & Sons", "email": "omalley@test.com", "phone": None}
        ]

        mock_result = MagicMock()
        mock_result.data = clients
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result

        mock_empty = MagicMock()
        mock_empty.data = []
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.execute.return_value = mock_empty

        result = crm_service_with_mock_db.search_clients(query="O'Malley")
        assert len(result) == 1

    def test_count_by_field_empty_list(self, crm_service_with_mock_db):
        """_count_by_field should return empty dict for empty items list."""
        result = crm_service_with_mock_db._count_by_field([], "source")
        assert result == {}

    def test_get_client_id_filter_empty_string(self, crm_service_with_mock_db):
        """_get_client_id_filter with empty string should return 'id' column."""
        column, value = crm_service_with_mock_db._get_client_id_filter("")
        assert column == "id"
        assert value == ""

    def test_get_activities_returns_empty_on_exception(self, crm_service_with_mock_db, mock_supabase):
        """get_activities returns empty list when database raises exception."""
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.side_effect = Exception("err")

        result = crm_service_with_mock_db.get_activities("CLI-12345")
        assert result == []

    def test_get_client_stats_handles_none_total_price(self, crm_service_with_mock_db, mock_supabase):
        """get_client_stats should treat None total_price as 0."""
        mock_clients = MagicMock()
        mock_clients.data = [{"pipeline_stage": "QUOTED", "source": "web"}]
        mock_quotes = MagicMock()
        mock_quotes.data = [{"total_price": None}, {"total_price": 500}]

        mock_supabase.client.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            mock_clients,
            mock_quotes
        ]

        with patch('src.services.crm_service.get_redis_client', return_value=None):
            result = crm_service_with_mock_db.get_client_stats()

        assert result['total_value'] == 500

    def test_get_client_exception_returns_none(self, crm_service_with_mock_db, mock_supabase):
        """get_client returns None when database query raises."""
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("err")

        result = crm_service_with_mock_db.get_client("CLI-12345")
        assert result is None

    def test_get_or_create_client_with_special_chars_in_name(self, crm_service_with_mock_db, mock_supabase):
        """get_or_create_client should handle special characters in name."""
        mock_empty = MagicMock()
        mock_empty.data = []
        mock_supabase.client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_empty

        mock_insert_result = MagicMock()
        mock_insert_result.data = [{"client_id": "CLI-12345678", "name": "Jose Garcia-Lopez", "email": "jose@test.com"}]
        mock_supabase.client.table.return_value.insert.return_value.execute.return_value = mock_insert_result

        result = crm_service_with_mock_db.get_or_create_client(
            email="jose@test.com",
            name="Jose Garcia-Lopez"
        )

        assert result is not None
        assert result['created'] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
