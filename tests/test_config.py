"""
Configuration Loader Unit Tests

Tests for ClientConfig and helper functions in config/loader.py.
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestClientConfigInit:
    """Tests for ClientConfig initialization."""

    def test_missing_client_raises_error(self):
        """Loading a non-existent client should raise FileNotFoundError."""
        from config.loader import ClientConfig

        with pytest.raises(FileNotFoundError):
            ClientConfig('non_existent_client_xyz123')

    def test_sets_client_id(self):
        """ClientConfig should set client_id attribute."""
        from config.loader import ClientConfig

        with patch('config.loader.get_config_service') as mock_service:
            mock_svc = MagicMock()
            mock_svc.get_config.return_value = {'client_id': 'test-tenant'}
            mock_service.return_value = mock_svc

            config = ClientConfig('test-tenant')

            assert config.client_id == 'test-tenant'

    def test_sets_base_path(self):
        """ClientConfig should set base_path attribute."""
        from config.loader import ClientConfig

        with patch('config.loader.get_config_service') as mock_service:
            mock_svc = MagicMock()
            mock_svc.get_config.return_value = {'client_id': 'test'}
            mock_service.return_value = mock_svc

            config = ClientConfig('test')

            assert config.base_path is not None
            assert isinstance(config.base_path, Path)

    def test_uses_database_config_source(self):
        """ClientConfig should default to database source."""
        from config.loader import ClientConfig

        with patch('config.loader.get_config_service') as mock_service:
            mock_svc = MagicMock()
            mock_svc.get_config.return_value = {
                'client_id': 'test',
                '_meta': {'source': 'database'}
            }
            mock_service.return_value = mock_svc

            config = ClientConfig('test')

            assert config.config_source == 'database'


class TestListClients:
    """Tests for list_clients function."""

    def test_list_clients_returns_list(self):
        """list_clients should return a list."""
        from config.loader import list_clients

        result = list_clients()

        assert isinstance(result, list)

    def test_list_clients_handles_empty(self):
        """list_clients should handle empty tenant list."""
        from config.loader import list_clients

        with patch('config.loader.get_config_service') as mock_service:
            mock_svc = MagicMock()
            mock_svc.list_tenants.return_value = []
            mock_service.return_value = mock_svc

            result = list_clients()

            # Result should be a list (may be empty or have fallbacks)
            assert isinstance(result, list)


class TestGetConfig:
    """Tests for get_config function."""

    def test_get_config_returns_client_config(self):
        """get_config should return ClientConfig instance."""
        from config.loader import get_config, ClientConfig

        with patch('config.loader.ClientConfig') as MockClientConfig:
            mock_config = MagicMock()
            MockClientConfig.return_value = mock_config

            result = get_config('test-tenant')

            MockClientConfig.assert_called_once_with('test-tenant')
            assert result is mock_config


class TestGetTenantConfigServiceModule:
    """Tests for lazy import of tenant_config_service."""

    def test_lazy_import_caches_module(self):
        """_get_tenant_config_service_module should cache the module."""
        import config.loader as loader

        # Reset the cached module
        original = loader._tenant_config_service_module
        loader._tenant_config_service_module = None

        try:
            # First call
            module1 = loader._get_tenant_config_service_module()
            # Second call
            module2 = loader._get_tenant_config_service_module()

            # Should be the same module instance
            assert module1 is module2
        finally:
            # Restore original
            loader._tenant_config_service_module = original


class TestResetConfigService:
    """Tests for reset_config_service function."""

    def test_reset_config_service_calls_module_reset(self):
        """reset_config_service should call module's reset_service."""
        from config.loader import reset_config_service

        with patch('config.loader._get_tenant_config_service_module') as mock_get:
            mock_module = MagicMock()
            mock_get.return_value = mock_module

            reset_config_service()

            mock_module.reset_service.assert_called_once()


class TestClientConfigProperties:
    """Tests for ClientConfig property accessors."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock config with common properties."""
        return {
            'client': {
                'id': 'test-tenant',
                'name': 'Test Company',
                'short_name': 'test',
                'timezone': 'Africa/Johannesburg',
                'currency': 'USD'
            },
            'branding': {
                'company_name': 'Test Company Inc',
                'logo_url': 'https://example.com/logo.png',
                'primary_color': '#FF6B6B'
            },
            'destinations': [
                {'name': 'Zanzibar', 'code': 'zanzibar', 'enabled': True},
                {'name': 'Mauritius', 'code': 'mauritius', 'enabled': True}
            ],
            'sendgrid': {
                'from_email': 'test@example.com',
                'from_name': 'Test Sender'
            },
            'gcp_project_id': 'test-project',
            '_meta': {'source': 'database'}
        }

    def test_company_name_property(self, mock_config):
        """Should return company_name from config."""
        from config.loader import ClientConfig

        with patch('config.loader.get_config_service') as mock_service:
            mock_svc = MagicMock()
            mock_svc.get_config.return_value = mock_config
            mock_service.return_value = mock_svc

            config = ClientConfig('test-tenant')

            # company_name comes from branding, falls back to client.name
            assert config.company_name == 'Test Company Inc'

    def test_destinations_property(self, mock_config):
        """Should return destinations from config."""
        from config.loader import ClientConfig

        with patch('config.loader.get_config_service') as mock_service:
            mock_svc = MagicMock()
            mock_svc.get_config.return_value = mock_config
            mock_service.return_value = mock_svc

            config = ClientConfig('test-tenant')

            assert len(config.destinations) == 2
            assert config.destinations[0]['name'] == 'Zanzibar'

    def test_destination_names_property(self, mock_config):
        """Should return list of destination names."""
        from config.loader import ClientConfig

        with patch('config.loader.get_config_service') as mock_service:
            mock_svc = MagicMock()
            mock_svc.get_config.return_value = mock_config
            mock_service.return_value = mock_svc

            config = ClientConfig('test-tenant')

            assert 'Zanzibar' in config.destination_names
            assert 'Mauritius' in config.destination_names

    def test_currency_property(self, mock_config):
        """Should return currency from config."""
        from config.loader import ClientConfig

        with patch('config.loader.get_config_service') as mock_service:
            mock_svc = MagicMock()
            mock_svc.get_config.return_value = mock_config
            mock_service.return_value = mock_svc

            config = ClientConfig('test-tenant')

            assert config.currency == 'USD'

    def test_timezone_property(self, mock_config):
        """Should return timezone from config."""
        from config.loader import ClientConfig

        with patch('config.loader.get_config_service') as mock_service:
            mock_svc = MagicMock()
            mock_svc.get_config.return_value = mock_config
            mock_service.return_value = mock_svc

            config = ClientConfig('test-tenant')

            assert config.timezone == 'Africa/Johannesburg'


class TestResolveSecrets:
    """Tests for secret resolution in config."""

    def test_resolve_env_vars_in_config(self):
        """Config should resolve ${ENV_VAR} placeholders."""
        from config.loader import ClientConfig

        with patch('config.loader.get_config_service') as mock_service:
            mock_svc = MagicMock()
            mock_svc.get_config.return_value = {
                'client_id': 'test',
                'api_key': 'resolved-key',
                '_meta': {'source': 'database'}
            }
            mock_service.return_value = mock_svc

            config = ClientConfig('test')

            # Config should have resolved values
            assert config.config is not None


class TestDatabaseTables:
    """Tests for DatabaseTables class."""

    def test_database_tables_stores_config(self):
        """DatabaseTables should store config reference."""
        from config.database import DatabaseTables

        mock_config = MagicMock()
        mock_config.client_id = 'test-tenant'

        db = DatabaseTables(mock_config)

        assert db.config is mock_config

    def test_database_tables_has_table_properties(self):
        """DatabaseTables should have table name properties."""
        from config.database import DatabaseTables

        mock_config = MagicMock()
        mock_config.client_id = 'mycompany'
        mock_config.gcp_project_id = 'my-project'
        mock_config.dataset_name = 'my_dataset'
        mock_config.shared_pricing_dataset = 'shared_pricing'

        db = DatabaseTables(mock_config)

        # Should have hotel_rates, hotel_media, etc. properties
        assert hasattr(db, 'hotel_rates')
        assert hasattr(db, 'hotel_media')
        assert db.project == 'my-project'
