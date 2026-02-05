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


# ==================== Extended Property Tests ====================

class TestBrandingProperties:
    """Tests for branding property accessors."""

    @pytest.fixture
    def client_config(self):
        """Create a ClientConfig with full branding."""
        from config.loader import ClientConfig

        with patch('config.loader.get_config_service') as mock_service:
            mock_svc = MagicMock()
            mock_svc.get_config.return_value = {
                'client': {
                    'name': 'Test Travel',
                    'short_name': 'tt',
                    'timezone': 'UTC',
                    'currency': 'ZAR',
                },
                'branding': {
                    'company_name': 'Test Travel Co',
                    'logo_url': 'https://example.com/logo.png',
                    'primary_color': '#336699',
                    'secondary_color': '#99CCFF',
                    'email_signature': 'Kind regards,\nTest Team',
                    'phone': '+27123456789',
                    'website': 'https://testtravel.com',
                    'fax': '+27123456790',
                },
                'email': {
                    'primary': 'info@testtravel.com',
                    'sendgrid': {
                        'api_key': 'SG.test',
                        'from_email': 'noreply@testtravel.com',
                        'from_name': 'Test Travel',
                        'reply_to': 'support@testtravel.com',
                    },
                    'smtp': {
                        'host': 'smtp.example.com',
                        'port': 465,
                        'username': 'user@example.com',
                        'password': 'secret',
                    },
                    'imap': {
                        'host': 'imap.example.com',
                        'port': 993,
                    },
                },
                'banking': {
                    'bank_name': 'Test Bank',
                    'account_name': 'Test Travel Co',
                    'account_number': '123456789',
                    'branch_code': '250655',
                    'swift_code': 'TESTZA2X',
                    'reference_prefix': 'TT',
                },
                'destinations': [
                    {'name': 'Zanzibar', 'code': 'zanzibar', 'enabled': True, 'aliases': ['Unguja']},
                    {'name': 'Mauritius', 'code': 'mauritius', 'enabled': True},
                    {'name': 'Disabled Island', 'code': 'disabled', 'enabled': False},
                ],
                'infrastructure': {
                    'gcp': {
                        'project_id': 'test-project',
                        'region': 'us-central1',
                        'dataset': 'test_analytics',
                        'shared_pricing_dataset': 'shared_pricing',
                        'corpus_id': 'corpus-123',
                    },
                    'supabase': {
                        'url': 'https://test.supabase.co',
                        'anon_key': 'anon-key-123',
                        'service_key': 'service-key-456',
                    },
                    'openai': {
                        'api_key': 'sk-test',
                        'model': 'gpt-4o',
                    },
                    'vapi': {
                        'api_key': 'vapi-key',
                        'phone_number_id': 'phone-123',
                        'assistant_id': 'asst-inbound',
                        'outbound_assistant_id': 'asst-outbound',
                    },
                },
                'agents': {
                    'inbound': {'enabled': True, 'prompt_file': 'prompts/inbound.txt'},
                    'helpdesk': {'enabled': True},
                    'outbound': {'enabled': False},
                },
                'consultants': [
                    {'name': 'Alice', 'email': 'alice@test.com', 'active': True},
                    {'name': 'Bob', 'email': 'bob@test.com', 'active': False},
                ],
                '_meta': {'source': 'database'},
            }
            mock_service.return_value = mock_svc

            return ClientConfig('test-tenant')

    def test_logo_url(self, client_config):
        """Should return logo URL."""
        assert client_config.logo_url == 'https://example.com/logo.png'

    def test_primary_color(self, client_config):
        """Should return primary color."""
        assert client_config.primary_color == '#336699'

    def test_secondary_color(self, client_config):
        """Should return secondary color."""
        assert client_config.secondary_color == '#99CCFF'

    def test_email_signature(self, client_config):
        """Should return email signature."""
        assert 'Kind regards' in client_config.email_signature

    def test_support_phone(self, client_config):
        """Should return support phone."""
        assert client_config.support_phone == '+27123456789'

    def test_website(self, client_config):
        """Should return website."""
        assert client_config.website == 'https://testtravel.com'

    def test_fax_number(self, client_config):
        """Should return fax number."""
        assert client_config.fax_number == '+27123456790'


class TestEmailProperties:
    """Tests for email property accessors."""

    @pytest.fixture
    def client_config(self):
        from config.loader import ClientConfig
        with patch('config.loader.get_config_service') as mock_service:
            mock_svc = MagicMock()
            mock_svc.get_config.return_value = {
                'client': {'name': 'Test', 'short_name': 'tt', 'timezone': 'UTC'},
                'email': {
                    'primary': 'info@test.com',
                    'smtp': {'host': 'smtp.test.com', 'port': 465, 'username': 'user', 'password': 'pass'},
                    'imap': {'host': 'imap.test.com', 'port': 993},
                    'sendgrid': {
                        'api_key': 'SG.test', 'from_email': 'noreply@test.com',
                        'from_name': 'Test', 'reply_to': 'reply@test.com',
                    },
                },
                '_meta': {'source': 'database'},
            }
            mock_service.return_value = mock_svc
            return ClientConfig('test')

    def test_primary_email(self, client_config):
        """Should return primary email."""
        assert client_config.primary_email == 'info@test.com'

    def test_smtp_host(self, client_config):
        """Should return SMTP host."""
        assert client_config.smtp_host == 'smtp.test.com'

    def test_smtp_port(self, client_config):
        """Should return SMTP port."""
        assert client_config.smtp_port == 465

    def test_smtp_username(self, client_config):
        """Should return SMTP username."""
        assert client_config.smtp_username == 'user'

    def test_smtp_password(self, client_config):
        """Should return SMTP password."""
        assert client_config.smtp_password == 'pass'

    def test_imap_host(self, client_config):
        """Should return IMAP host."""
        assert client_config.imap_host == 'imap.test.com'

    def test_imap_port(self, client_config):
        """Should return IMAP port."""
        assert client_config.imap_port == 993

    def test_sendgrid_api_key(self, client_config):
        """Should return SendGrid API key."""
        assert client_config.sendgrid_api_key == 'SG.test'

    def test_sendgrid_from_email(self, client_config):
        """Should return SendGrid from email."""
        assert client_config.sendgrid_from_email == 'noreply@test.com'

    def test_sendgrid_from_name(self, client_config):
        """Should return SendGrid from name."""
        assert client_config.sendgrid_from_name == 'Test'

    def test_sendgrid_reply_to(self, client_config):
        """Should return SendGrid reply-to."""
        assert client_config.sendgrid_reply_to == 'reply@test.com'


class TestInfrastructureProperties:
    """Tests for infrastructure property accessors."""

    @pytest.fixture
    def client_config(self):
        from config.loader import ClientConfig
        with patch('config.loader.get_config_service') as mock_service:
            mock_svc = MagicMock()
            mock_svc.get_config.return_value = {
                'client': {'name': 'Test', 'short_name': 'tt', 'timezone': 'UTC'},
                'infrastructure': {
                    'gcp': {
                        'project_id': 'my-project',
                        'region': 'eu-west1',
                        'dataset': 'analytics_ds',
                        'shared_pricing_dataset': 'shared_ds',
                        'corpus_id': 'corpus-abc',
                    },
                    'supabase': {
                        'url': 'https://supabase.test.co',
                        'anon_key': 'anon-key',
                        'service_key': 'svc-key',
                    },
                    'openai': {
                        'api_key': 'sk-openai',
                        'model': 'gpt-4o-mini',
                    },
                    'vapi': {
                        'api_key': 'vapi-key',
                        'phone_number_id': 'phone-id',
                        'assistant_id': 'asst-id',
                        'outbound_assistant_id': 'out-asst-id',
                    },
                },
                '_meta': {'source': 'database'},
            }
            mock_service.return_value = mock_svc
            return ClientConfig('test')

    def test_gcp_project_id(self, client_config):
        assert client_config.gcp_project_id == 'my-project'

    def test_gcp_region(self, client_config):
        assert client_config.gcp_region == 'eu-west1'

    def test_dataset_name(self, client_config):
        assert client_config.dataset_name == 'analytics_ds'

    def test_shared_pricing_dataset(self, client_config):
        assert client_config.shared_pricing_dataset == 'shared_ds'

    def test_corpus_id(self, client_config):
        assert client_config.corpus_id == 'corpus-abc'

    def test_supabase_url(self, client_config):
        assert client_config.supabase_url == 'https://supabase.test.co'

    def test_supabase_anon_key(self, client_config):
        assert client_config.supabase_anon_key == 'anon-key'

    def test_supabase_service_key(self, client_config):
        assert client_config.supabase_service_key == 'svc-key'

    def test_openai_api_key(self, client_config):
        assert client_config.openai_api_key == 'sk-openai'

    def test_openai_model(self, client_config):
        assert client_config.openai_model == 'gpt-4o-mini'

    def test_vapi_api_key(self, client_config):
        assert client_config.vapi_api_key == 'vapi-key'

    def test_vapi_phone_number_id(self, client_config):
        assert client_config.vapi_phone_number_id == 'phone-id'

    def test_vapi_assistant_id(self, client_config):
        assert client_config.vapi_assistant_id == 'asst-id'

    def test_vapi_outbound_assistant_id(self, client_config):
        assert client_config.vapi_outbound_assistant_id == 'out-asst-id'


class TestBankingProperties:
    """Tests for banking property accessors."""

    @pytest.fixture
    def client_config(self):
        from config.loader import ClientConfig
        with patch('config.loader.get_config_service') as mock_service:
            mock_svc = MagicMock()
            mock_svc.get_config.return_value = {
                'client': {'name': 'Test', 'short_name': 'tt', 'timezone': 'UTC'},
                'banking': {
                    'bank_name': 'FNB',
                    'account_name': 'Test Travel',
                    'account_number': '62123456789',
                    'branch_code': '250655',
                    'swift_code': 'FIRNZAJJ',
                    'reference_prefix': 'TT',
                },
                '_meta': {'source': 'database'},
            }
            mock_service.return_value = mock_svc
            return ClientConfig('test')

    def test_banking_dict(self, client_config):
        assert isinstance(client_config.banking, dict)

    def test_bank_name(self, client_config):
        assert client_config.bank_name == 'FNB'

    def test_bank_account_name(self, client_config):
        assert client_config.bank_account_name == 'Test Travel'

    def test_bank_account_number(self, client_config):
        assert client_config.bank_account_number == '62123456789'

    def test_bank_branch_code(self, client_config):
        assert client_config.bank_branch_code == '250655'

    def test_bank_swift_code(self, client_config):
        assert client_config.bank_swift_code == 'FIRNZAJJ'

    def test_payment_reference_prefix(self, client_config):
        assert client_config.payment_reference_prefix == 'TT'


class TestDestinationMethods:
    """Tests for destination-related methods."""

    @pytest.fixture
    def client_config(self):
        from config.loader import ClientConfig
        with patch('config.loader.get_config_service') as mock_service:
            mock_svc = MagicMock()
            mock_svc.get_config.return_value = {
                'client': {'name': 'Test', 'short_name': 'tt', 'timezone': 'UTC'},
                'destinations': [
                    {'name': 'Zanzibar', 'code': 'zanzibar', 'enabled': True, 'aliases': ['Unguja', 'Stone Town']},
                    {'name': 'Mauritius', 'code': 'mauritius', 'enabled': True},
                    {'name': 'Disabled', 'code': 'disabled', 'enabled': False},
                ],
                '_meta': {'source': 'database'},
            }
            mock_service.return_value = mock_svc
            return ClientConfig('test')

    def test_destinations_filters_disabled(self, client_config):
        """Should filter out disabled destinations."""
        assert len(client_config.destinations) == 2
        names = [d['name'] for d in client_config.destinations]
        assert 'Disabled' not in names

    def test_destination_names(self, client_config):
        assert client_config.destination_names == ['Zanzibar', 'Mauritius']

    def test_destination_codes(self, client_config):
        assert client_config.destination_codes == ['zanzibar', 'mauritius']

    def test_get_destination_search_terms(self, client_config):
        """Should return aliases for destination."""
        terms = client_config.get_destination_search_terms('Zanzibar')
        assert 'Zanzibar' in terms
        assert 'Unguja' in terms
        assert 'Stone Town' in terms

    def test_search_terms_case_insensitive(self, client_config):
        """Should match destination case-insensitively."""
        terms = client_config.get_destination_search_terms('zanzibar')
        assert 'Zanzibar' in terms

    def test_search_terms_unknown_destination(self, client_config):
        """Should return original name for unknown destination."""
        terms = client_config.get_destination_search_terms('Unknown')
        assert terms == ['Unknown']


class TestAgentMethods:
    """Tests for agent-related methods."""

    @pytest.fixture
    def client_config(self):
        from config.loader import ClientConfig
        with patch('config.loader.get_config_service') as mock_service:
            mock_svc = MagicMock()
            mock_svc.get_config.return_value = {
                'client': {'name': 'Test', 'short_name': 'tt', 'timezone': 'UTC'},
                'agents': {
                    'inbound': {'enabled': True, 'prompt_file': 'prompts/inbound.txt'},
                    'helpdesk': {'enabled': True},
                    'outbound': {'enabled': False},
                },
                '_meta': {'source': 'database'},
            }
            mock_service.return_value = mock_svc
            return ClientConfig('test')

    def test_get_agent_config(self, client_config):
        config = client_config.get_agent_config('inbound')
        assert config['enabled'] is True

    def test_is_agent_enabled_true(self, client_config):
        assert client_config.is_agent_enabled('inbound') is True

    def test_is_agent_enabled_false(self, client_config):
        assert client_config.is_agent_enabled('outbound') is False

    def test_unknown_agent_defaults_enabled(self, client_config):
        assert client_config.is_agent_enabled('unknown') is True

    def test_get_prompt_path(self, client_config):
        path = client_config.get_prompt_path('inbound')
        assert 'inbound.txt' in str(path)


class TestConsultantProperty:
    """Tests for consultant property."""

    @pytest.fixture
    def client_config(self):
        from config.loader import ClientConfig
        with patch('config.loader.get_config_service') as mock_service:
            mock_svc = MagicMock()
            mock_svc.get_config.return_value = {
                'client': {'name': 'Test', 'short_name': 'tt', 'timezone': 'UTC'},
                'consultants': [
                    {'name': 'Alice', 'email': 'alice@test.com', 'active': True},
                    {'name': 'Bob', 'email': 'bob@test.com', 'active': False},
                    {'name': 'Charlie', 'email': 'charlie@test.com', 'active': True},
                ],
                '_meta': {'source': 'database'},
            }
            mock_service.return_value = mock_svc
            return ClientConfig('test')

    def test_consultants_filters_inactive(self, client_config):
        assert len(client_config.consultants) == 2

    def test_consultants_names(self, client_config):
        names = [c['name'] for c in client_config.consultants]
        assert 'Alice' in names
        assert 'Charlie' in names
        assert 'Bob' not in names


class TestHelperMethods:
    """Tests for helper methods."""

    @pytest.fixture
    def client_config(self):
        from config.loader import ClientConfig
        with patch('config.loader.get_config_service') as mock_service:
            mock_svc = MagicMock()
            mock_svc.get_config.return_value = {
                'client': {'name': 'Test Company', 'short_name': 'tt', 'timezone': 'UTC'},
                'infrastructure': {
                    'gcp': {'project_id': 'proj-1', 'dataset': 'ds_1'},
                },
                '_meta': {'source': 'database'},
            }
            mock_service.return_value = mock_svc
            return ClientConfig('test')

    def test_get_table_name(self, client_config):
        table = client_config.get_table_name('hotel_rates')
        assert table == 'proj-1.ds_1.hotel_rates'

    def test_to_dict(self, client_config):
        d = client_config.to_dict()
        assert isinstance(d, dict)
        assert 'client' in d

    def test_repr(self, client_config):
        r = repr(client_config)
        assert 'test' in r
        assert 'Test Company' in r


class TestSubstituteEnvVars:
    """Tests for _substitute_env_vars method."""

    @pytest.fixture
    def client_config(self):
        from config.loader import ClientConfig
        with patch('config.loader.get_config_service') as mock_service:
            mock_svc = MagicMock()
            mock_svc.get_config.return_value = {
                'client': {'name': 'Test', 'short_name': 'tt', 'timezone': 'UTC'},
                '_meta': {'source': 'database'},
            }
            mock_service.return_value = mock_svc
            return ClientConfig('test')

    def test_substitutes_env_var(self, client_config):
        with patch.dict('os.environ', {'MY_VAR': 'my_value'}):
            result = client_config._substitute_env_vars('${MY_VAR}')
            assert result == 'my_value'

    def test_substitutes_with_default(self, client_config):
        with patch.dict('os.environ', {}, clear=True):
            result = client_config._substitute_env_vars('${UNSET_VAR:-default_val}')
            assert result == 'default_val'

    def test_substitutes_in_dict(self, client_config):
        with patch.dict('os.environ', {'KEY': 'val'}):
            result = client_config._substitute_env_vars({'a': '${KEY}'})
            assert result == {'a': 'val'}

    def test_substitutes_in_list(self, client_config):
        with patch.dict('os.environ', {'KEY': 'val'}):
            result = client_config._substitute_env_vars(['${KEY}', 'static'])
            assert result == ['val', 'static']

    def test_non_string_passthrough(self, client_config):
        assert client_config._substitute_env_vars(42) == 42
        assert client_config._substitute_env_vars(True) is True
        assert client_config._substitute_env_vars(None) is None

    def test_missing_env_var_empty_string(self, client_config):
        with patch.dict('os.environ', {}, clear=True):
            result = client_config._substitute_env_vars('${MISSING_VAR}')
            assert result == ''


class TestConfigCache:
    """Tests for config caching functions."""

    def test_get_config_caches(self):
        """get_config should cache ClientConfig instances."""
        from config.loader import get_config, clear_config_cache, _config_cache

        clear_config_cache()

        with patch('config.loader.ClientConfig') as MockConfig:
            mock = MagicMock()
            MockConfig.return_value = mock

            result1 = get_config('cache-test')
            result2 = get_config('cache-test')

            assert result1 is result2
            MockConfig.assert_called_once()

        clear_config_cache()

    def test_clear_config_cache_all(self):
        """clear_config_cache() should clear all entries."""
        from config.loader import clear_config_cache, _config_cache

        with patch('config.loader.reset_config_service'):
            _config_cache['a'] = 'x'
            _config_cache['b'] = 'y'

            clear_config_cache()

        from config.loader import _config_cache as cache
        assert len(cache) == 0

    def test_clear_config_cache_specific(self):
        """clear_config_cache(id) should clear only that entry."""
        from config.loader import clear_config_cache, _config_cache

        with patch('config.loader.reset_config_service'):
            _config_cache['keep'] = 'x'
            _config_cache['remove'] = 'y'

            clear_config_cache('remove')

        from config.loader import _config_cache as cache
        assert 'keep' in cache
        assert 'remove' not in cache

        clear_config_cache()

    def test_get_client_config_returns_dict(self):
        """get_client_config should return dict."""
        from config.loader import get_client_config, clear_config_cache

        clear_config_cache()

        with patch('config.loader.get_config') as mock_get:
            mock_cfg = MagicMock()
            mock_cfg.to_dict.return_value = {'key': 'val'}
            mock_get.return_value = mock_cfg

            result = get_client_config('test')

            assert result == {'key': 'val'}

        clear_config_cache()

    def test_get_client_config_not_found(self):
        """get_client_config should return None for missing tenant."""
        from config.loader import get_client_config, clear_config_cache

        clear_config_cache()

        with patch('config.loader.get_config', side_effect=FileNotFoundError):
            result = get_client_config('missing')

            assert result is None

        clear_config_cache()


class TestDefaultValues:
    """Tests for default property values when config keys are missing."""

    @pytest.fixture
    def minimal_config(self):
        from config.loader import ClientConfig
        with patch('config.loader.get_config_service') as mock_service:
            mock_svc = MagicMock()
            mock_svc.get_config.return_value = {
                'client': {'name': 'Minimal', 'short_name': 'min', 'timezone': 'UTC'},
                'infrastructure': {
                    'gcp': {'project_id': 'p', 'dataset': 'd'},
                    'supabase': {'url': 'u', 'anon_key': 'k'},
                    'openai': {'api_key': 'k'},
                },
                'email': {'primary': 'e@e.com'},
                '_meta': {'source': 'database'},
            }
            mock_service.return_value = mock_svc
            return ClientConfig('test')

    def test_default_currency(self, minimal_config):
        assert minimal_config.currency == 'USD'

    def test_default_primary_color(self, minimal_config):
        assert minimal_config.primary_color == '#FF6B6B'

    def test_default_secondary_color(self, minimal_config):
        assert minimal_config.secondary_color == '#4ECDC4'

    def test_default_openai_model(self, minimal_config):
        assert minimal_config.openai_model == 'gpt-4o-mini'

    def test_default_gcp_region(self, minimal_config):
        assert minimal_config.gcp_region == 'us-central1'

    def test_default_smtp_port(self, minimal_config):
        assert minimal_config.smtp_port == 465

    def test_default_imap_port(self, minimal_config):
        assert minimal_config.imap_port == 993

    def test_none_logo_url(self, minimal_config):
        assert minimal_config.logo_url is None

    def test_none_vapi_api_key(self, minimal_config):
        assert minimal_config.vapi_api_key is None

    def test_none_corpus_id(self, minimal_config):
        assert minimal_config.corpus_id is None

    def test_none_sendgrid_api_key(self, minimal_config):
        assert minimal_config.sendgrid_api_key is None

    def test_empty_destinations(self, minimal_config):
        assert minimal_config.destinations == []

    def test_empty_consultants(self, minimal_config):
        assert minimal_config.consultants == []

    def test_company_name_falls_back(self, minimal_config):
        """company_name should fall back to client.name."""
        assert minimal_config.company_name == 'Minimal'

    def test_default_email_signature(self, minimal_config):
        """Email signature should fall back to default."""
        assert 'Minimal' in minimal_config.email_signature
