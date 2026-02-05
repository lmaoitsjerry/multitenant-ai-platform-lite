"""
Unit Tests for TenantConfigService

Tests cover:
- Database-backed config loading
- YAML fallback behavior
- Tenant isolation (critical for multi-tenant security)
- Cache behavior
- Secret handling (not stored in database)
"""

import os
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Import the service
from src.services.tenant_config_service import (
    TenantConfigService,
    get_tenant_config,
    list_all_tenants,
)


class TestTenantConfigService:
    """Test TenantConfigService core functionality"""

    def test_cache_prefix_defined(self):
        """Verify cache prefix is defined"""
        service = TenantConfigService()
        assert service.CACHE_PREFIX == "tenant_config:"
        assert service.CACHE_TTL == 300

    def test_cache_key_generation(self):
        """Test cache key generation"""
        service = TenantConfigService()
        key = service._cache_key("tn_123456")
        assert key == "tenant_config:tn_123456"

    def test_init_with_custom_base_path(self):
        """Test initialization with custom base path"""
        service = TenantConfigService(base_path="/custom/path")
        assert service.base_path == Path("/custom/path")

    def test_init_default_base_path(self):
        """Test default base path is set correctly"""
        service = TenantConfigService()
        assert service.base_path is not None
        assert isinstance(service.base_path, Path)


class TestTenantIsolation:
    """
    Critical tests for tenant isolation (TEST-03 requirement)

    These tests verify that one tenant cannot access another tenant's data.
    """

    def test_different_tenants_get_different_configs(self):
        """Each tenant must receive their own configuration"""
        service = TenantConfigService()

        tenant_a_config = {'client': {'id': 'tenant_a', 'name': 'Tenant A'}}
        tenant_b_config = {'client': {'id': 'tenant_b', 'name': 'Tenant B'}}

        with patch.object(service, '_get_from_cache', return_value=None):
            with patch.object(service, '_load_from_database') as mock_db:
                with patch.object(service, '_set_cache'):
                    # Return different configs for different tenants
                    mock_db.side_effect = lambda tid: tenant_a_config if tid == 'tenant_a' else tenant_b_config

                    config_a = service.get_config('tenant_a')
                    config_b = service.get_config('tenant_b')

                    assert config_a['client']['id'] == 'tenant_a'
                    assert config_b['client']['id'] == 'tenant_b'
                    assert config_a != config_b

    def test_tenant_id_in_database_query(self):
        """Verify tenant_id is used in database query"""
        service = TenantConfigService()

        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq = MagicMock()
        mock_single = MagicMock()

        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.single.return_value = mock_single
        mock_single.execute.return_value = MagicMock(data=None)

        with patch.object(service, '_get_supabase_client', return_value=mock_supabase):
            service._load_from_database('specific_tenant_123')

            # Verify the query filters by tenant_id
            mock_table.select.assert_called_with("*")
            mock_select.eq.assert_called_with("id", "specific_tenant_123")

    def test_cache_keys_are_tenant_specific(self):
        """Cache keys must include tenant_id to prevent cross-tenant leakage"""
        service = TenantConfigService()

        key_a = service._cache_key('tenant_a')
        key_b = service._cache_key('tenant_b')

        assert 'tenant_a' in key_a
        assert 'tenant_b' in key_b
        assert key_a != key_b

    def test_save_config_only_affects_specified_tenant(self):
        """save_config must only update the specified tenant"""
        service = TenantConfigService()

        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_upsert = MagicMock()

        mock_supabase.table.return_value = mock_table
        mock_table.upsert.return_value = mock_upsert
        mock_upsert.execute.return_value = MagicMock()

        with patch.object(service, '_get_supabase_client', return_value=mock_supabase):
            with patch.object(service, '_invalidate_cache'):
                service.save_config('target_tenant', {'client': {'id': 'target_tenant'}})

                # Verify upsert was called with correct tenant_id
                call_args = mock_table.upsert.call_args
                row_data = call_args[0][0]
                assert row_data['id'] == 'target_tenant'


class TestSecretHandling:
    """Test that secrets are properly handled (not stored in DB)"""

    def test_strip_secrets_removes_api_keys(self):
        """Secrets should be stripped before database storage"""
        service = TenantConfigService()

        config = {
            'client': {'id': 'test'},
            'infrastructure': {
                'supabase': {'url': 'https://x.supabase.co', 'anon_key': 'secret123', 'service_key': 'secret456'},
                'vapi': {'api_key': 'vapi_secret', 'assistant_id': 'ast_123'},
                'openai': {'api_key': 'sk-secret', 'model': 'gpt-4o-mini'},
            },
            'email': {
                'primary': 'test@example.com',
                'sendgrid': {'api_key': 'SG.secret', 'from_email': 'noreply@example.com'},
                'smtp': {'host': 'smtp.example.com', 'password': 'smtp_secret'},
            },
        }

        stripped = service._strip_secrets(config)

        # Secrets should be removed
        assert 'anon_key' not in stripped.get('infrastructure', {}).get('supabase', {})
        assert 'service_key' not in stripped.get('infrastructure', {}).get('supabase', {})
        assert 'api_key' not in stripped.get('infrastructure', {}).get('vapi', {})
        assert 'api_key' not in stripped.get('infrastructure', {}).get('openai', {})
        assert 'api_key' not in stripped.get('email', {}).get('sendgrid', {})
        assert 'password' not in stripped.get('email', {}).get('smtp', {})

        # Non-secrets should remain
        assert stripped['infrastructure']['vapi']['assistant_id'] == 'ast_123'
        assert stripped['infrastructure']['openai']['model'] == 'gpt-4o-mini'
        assert stripped['email']['sendgrid']['from_email'] == 'noreply@example.com'

    def test_secrets_resolved_from_env_vars(self):
        """Secrets should be resolved from environment variables"""
        service = TenantConfigService()

        # Mock database row
        row = {
            'id': 'test_tenant',
            'name': 'Test Tenant',
            'config_source': 'database',
            'tenant_config': {
                'infrastructure': {
                    'openai': {'model': 'gpt-4o-mini'},
                    'vapi': {'assistant_id': 'ast_123'},
                },
            },
        }

        with patch.dict(os.environ, {'OPENAI_API_KEY': 'env_openai_key', 'VAPI_API_KEY': 'env_vapi_key'}):
            infra = service._build_infrastructure(row, row['tenant_config'])

            assert infra['openai']['api_key'] == 'env_openai_key'
            assert infra['vapi']['api_key'] == 'env_vapi_key'

    def test_strip_secrets_does_not_modify_original(self):
        """_strip_secrets should not modify the original config"""
        service = TenantConfigService()

        original = {
            'client': {'id': 'test'},
            'infrastructure': {
                'openai': {'api_key': 'secret', 'model': 'gpt-4'},
            },
        }

        stripped = service._strip_secrets(original)

        # Original should be unchanged
        assert original['infrastructure']['openai']['api_key'] == 'secret'


class TestCacheBehavior:
    """Test Redis cache behavior"""

    def test_cache_hit_skips_database(self):
        """When cache hit, database should not be queried"""
        service = TenantConfigService()

        cached_config = {'client': {'id': 'cached_tenant'}, '_meta': {'source': 'database'}}

        with patch.object(service, '_get_from_cache', return_value=cached_config):
            with patch.object(service, '_load_from_database') as mock_db:
                config = service.get_config('newclient')

                # Database should NOT be called on cache hit
                mock_db.assert_not_called()
                assert config == cached_config

    def test_cache_miss_queries_database(self):
        """When cache miss, database should be queried"""
        service = TenantConfigService()

        db_config = {'client': {'id': 'db_tenant'}}

        with patch.object(service, '_get_from_cache', return_value=None):
            with patch.object(service, '_load_from_database', return_value=db_config):
                with patch.object(service, '_set_cache') as mock_set:
                    config = service.get_config('newclient')

                    # Cache should be populated after DB hit
                    mock_set.assert_called_once_with('newclient', db_config)

    def test_save_invalidates_cache(self):
        """Saving config should invalidate cache"""
        service = TenantConfigService()

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.upsert.return_value.execute.return_value = MagicMock()

        with patch.object(service, '_get_supabase_client', return_value=mock_supabase):
            with patch.object(service, '_invalidate_cache') as mock_invalidate:
                service.save_config('tenant_x', {'client': {'id': 'tenant_x'}})

                mock_invalidate.assert_called_once_with('tenant_x')

    def test_graceful_fallback_when_redis_unavailable(self):
        """System should work when Redis is not available"""
        service = TenantConfigService()
        service._redis_available = False  # Simulate Redis unavailable

        with patch.object(service, '_load_from_database') as mock_db:
            with patch.object(service, '_set_cache') as mock_set:
                mock_db.return_value = {'client': {'id': 'test'}}

                config = service.get_config('newclient')

                # Should still work, just without caching
                assert config is not None

    def test_cache_info_when_redis_unavailable(self):
        """get_cache_info should return correct info when Redis unavailable"""
        service = TenantConfigService()
        service._redis_available = False

        info = service.get_cache_info()

        assert info['backend'] == 'none'
        assert info['available'] is False
        assert info['ttl_seconds'] == 300


class TestListTenants:
    """Test tenant listing functionality"""

    def test_list_tenants_with_active_only(self):
        """list_tenants should query for active tenants by default"""
        service = TenantConfigService()

        mock_supabase = MagicMock()
        mock_query = MagicMock()
        mock_eq = MagicMock()

        mock_supabase.table.return_value.select.return_value = mock_query
        mock_query.eq.return_value = mock_eq
        mock_eq.execute.return_value = MagicMock(data=[
            {'id': 'tenant_a'},
            {'id': 'tenant_b'},
        ])

        with patch.object(service, '_get_supabase_client', return_value=mock_supabase):
            result = service.list_tenants(active_only=True)

            mock_query.eq.assert_called_once_with("status", "active")
            assert result == ['tenant_a', 'tenant_b']

    def test_list_tenants_all_statuses(self):
        """list_tenants with active_only=False should not filter by status"""
        service = TenantConfigService()

        mock_supabase = MagicMock()
        mock_query = MagicMock()

        mock_supabase.table.return_value.select.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=[
            {'id': 'active_tenant'},
            {'id': 'suspended_tenant'},
        ])

        with patch.object(service, '_get_supabase_client', return_value=mock_supabase):
            result = service.list_tenants(active_only=False)

            mock_query.eq.assert_not_called()
            assert result == ['active_tenant', 'suspended_tenant']

    def test_list_tenants_returns_empty_when_no_supabase(self):
        """list_tenants should return empty list when Supabase is unavailable"""
        service = TenantConfigService()

        with patch.object(service, '_get_supabase_client', return_value=None):
            result = service.list_tenants()
            assert result == []

    def test_list_tenants_returns_empty_on_db_error(self):
        """list_tenants should return empty list on database error"""
        service = TenantConfigService()

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("DB error")

        with patch.object(service, '_get_supabase_client', return_value=mock_supabase):
            result = service.list_tenants()
            assert result == []

    def test_list_tenants_handles_none_data(self):
        """list_tenants should handle None data from database"""
        service = TenantConfigService()

        mock_supabase = MagicMock()
        mock_query = MagicMock()
        mock_eq = MagicMock()

        mock_supabase.table.return_value.select.return_value = mock_query
        mock_query.eq.return_value = mock_eq
        mock_eq.execute.return_value = MagicMock(data=None)

        with patch.object(service, '_get_supabase_client', return_value=mock_supabase):
            result = service.list_tenants(active_only=True)
            assert result == []


class TestModuleLevelFunctions:
    """Test module-level convenience functions"""

    def test_get_tenant_config_uses_singleton(self):
        """get_tenant_config should use singleton service"""
        with patch('src.services.tenant_config_service.get_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_config.return_value = {'client': {'id': 'test'}}
            mock_get_service.return_value = mock_service

            config = get_tenant_config('test_tenant')

            mock_service.get_config.assert_called_once_with('test_tenant')

    def test_list_all_tenants_uses_singleton(self):
        """list_all_tenants should use singleton service"""
        with patch('src.services.tenant_config_service.get_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.list_tenants.return_value = ['tenant_a', 'tenant_b']
            mock_get_service.return_value = mock_service

            tenants = list_all_tenants()

            mock_service.list_tenants.assert_called_once()
            assert tenants == ['tenant_a', 'tenant_b']


class TestDatabaseLoadBehavior:
    """Test _load_from_database behavior"""

    def test_returns_none_when_no_supabase_client(self):
        """Should return None when Supabase client not available"""
        service = TenantConfigService()

        with patch.object(service, '_get_supabase_client', return_value=None):
            result = service._load_from_database('any_tenant')
            assert result is None

    def test_handles_database_error_gracefully(self):
        """Should handle database errors gracefully"""
        service = TenantConfigService()

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("DB Error")

        with patch.object(service, '_get_supabase_client', return_value=mock_supabase):
            result = service._load_from_database('test_tenant')
            assert result is None


# ==================================================================
# NEW TESTS: _build_config / _build_client_info / _build_branding
# ==================================================================

class TestBuildConfig:
    """Test _build_client_info and _build_branding methods"""

    def _make_service(self):
        return TenantConfigService()

    def _make_row(self, **overrides):
        row = {
            'id': 'test_tenant',
            'name': 'Test Tenant',
            'short_name': 'TT',
            'timezone': 'Africa/Johannesburg',
            'currency': 'ZAR',
            'primary_email': 'hello@test.com',
            'gcp_project_id': 'proj-123',
            'gcp_dataset': 'ds_test',
            'status': 'active',
            'plan': 'pro',
            'features_enabled': {'helpdesk': True},
            'tenant_config': {},
        }
        row.update(overrides)
        return row

    def test_build_client_info_from_row(self):
        """_build_client_info should pull fields from the database row"""
        service = self._make_service()
        row = self._make_row()

        result = service._build_client_info(row, {})

        assert result['id'] == 'test_tenant'
        assert result['name'] == 'Test Tenant'
        assert result['short_name'] == 'TT'
        assert result['timezone'] == 'Africa/Johannesburg'
        assert result['currency'] == 'ZAR'

    def test_build_client_info_falls_back_to_tenant_config(self):
        """_build_client_info should fall back to tenant_config when row columns are empty"""
        service = self._make_service()
        row = self._make_row(name=None, short_name=None, timezone=None, currency=None)
        tenant_config = {
            'client': {
                'name': 'Config Name',
                'short_name': 'CN',
                'timezone': 'UTC',
                'currency': 'USD',
            }
        }

        result = service._build_client_info(row, tenant_config)

        assert result['name'] == 'Config Name'
        assert result['short_name'] == 'CN'
        assert result['timezone'] == 'UTC'
        assert result['currency'] == 'USD'

    def test_build_client_info_uses_defaults_when_everything_empty(self):
        """_build_client_info should use sensible defaults when all sources are empty"""
        service = self._make_service()
        row = self._make_row(name=None, short_name=None, timezone=None, currency=None)

        result = service._build_client_info(row, {})

        # Should fall back to id-based defaults
        assert result['id'] == 'test_tenant'
        assert result['name'] == 'test_tenant'  # Falls back to row['id']
        assert result['timezone'] == 'Africa/Johannesburg'  # Default
        assert result['currency'] == 'ZAR'  # Default

    def test_build_branding_with_full_config(self):
        """_build_branding should use branding from tenant_config"""
        service = self._make_service()
        row = self._make_row()
        tenant_config = {
            'branding': {
                'company_name': 'My Travel Co',
                'logo_url': 'https://example.com/logo.png',
                'primary_color': '#FF0000',
                'secondary_color': '#00FF00',
                'accent_color': '#0000FF',
                'theme_id': 'ocean',
                'email_signature': 'Cheers!',
            }
        }

        result = service._build_branding(row, tenant_config)

        assert result['company_name'] == 'My Travel Co'
        assert result['logo_url'] == 'https://example.com/logo.png'
        assert result['primary_color'] == '#FF0000'
        assert result['secondary_color'] == '#00FF00'
        assert result['accent_color'] == '#0000FF'
        assert result['theme_id'] == 'ocean'
        assert result['email_signature'] == 'Cheers!'

    def test_build_branding_defaults(self):
        """_build_branding should use default colors when branding not set"""
        service = self._make_service()
        row = self._make_row()

        result = service._build_branding(row, {})

        assert result['company_name'] == 'Test Tenant'
        assert result['primary_color'] == '#2E86AB'
        assert result['secondary_color'] == '#4ECDC4'
        assert result['logo_url'] is None
        assert 'Test Tenant Team' in result['email_signature']


class TestBuildInfrastructure:
    """Test _build_infrastructure method with various env vars"""

    def _make_service(self):
        return TenantConfigService()

    def _make_row(self, tenant_id='test_tenant', **overrides):
        row = {
            'id': tenant_id,
            'name': 'Test Tenant',
            'gcp_project_id': 'my-gcp-project',
            'gcp_dataset': 'my_dataset',
            'tenant_config': {},
        }
        row.update(overrides)
        return row

    def test_infrastructure_supabase_from_env(self):
        """Supabase config should always come from env vars"""
        service = self._make_service()
        row = self._make_row()

        env = {
            'SUPABASE_URL': 'https://abc.supabase.co',
            'SUPABASE_ANON_KEY': 'anon_123',
            'SUPABASE_SERVICE_KEY': 'svc_456',
        }

        with patch.dict(os.environ, env, clear=False):
            result = service._build_infrastructure(row, {})

        assert result['supabase']['url'] == 'https://abc.supabase.co'
        assert result['supabase']['anon_key'] == 'anon_123'
        assert result['supabase']['service_key'] == 'svc_456'

    def test_infrastructure_gcp_from_row(self):
        """GCP config should prefer row columns"""
        service = self._make_service()
        row = self._make_row(gcp_project_id='row-project', gcp_dataset='row_dataset')

        result = service._build_infrastructure(row, {})

        assert result['gcp']['project_id'] == 'row-project'
        assert result['gcp']['dataset'] == 'row_dataset'
        assert result['gcp']['region'] == 'us-central1'

    def test_infrastructure_gcp_falls_back_to_env(self):
        """GCP project_id should fall back to env var"""
        service = self._make_service()
        row = self._make_row(gcp_project_id=None)

        with patch.dict(os.environ, {'GCP_PROJECT_ID': 'env-project'}, clear=False):
            result = service._build_infrastructure(row, {})

        assert result['gcp']['project_id'] == 'env-project'

    def test_infrastructure_vapi_tenant_specific_key(self):
        """VAPI should try tenant-specific env var first"""
        service = self._make_service()
        row = self._make_row(tenant_id='my-client')

        env = {
            'MY_CLIENT_VAPI_API_KEY': 'tenant_specific_key',
            'VAPI_API_KEY': 'shared_key',
        }

        with patch.dict(os.environ, env, clear=False):
            result = service._build_infrastructure(row, {})

        assert result['vapi']['api_key'] == 'tenant_specific_key'

    def test_infrastructure_vapi_falls_back_to_shared_key(self):
        """VAPI should fall back to shared VAPI_API_KEY when no tenant-specific key"""
        service = self._make_service()
        row = self._make_row(tenant_id='my-client')

        env = {
            'VAPI_API_KEY': 'shared_key_value',
        }

        with patch.dict(os.environ, env, clear=False):
            result = service._build_infrastructure(row, {})

        assert result['vapi']['api_key'] == 'shared_key_value'

    def test_infrastructure_openai_model_from_tenant_config(self):
        """OpenAI model should be configurable per tenant"""
        service = self._make_service()
        row = self._make_row()
        tenant_config = {
            'infrastructure': {
                'openai': {'model': 'gpt-4o'},
            }
        }

        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test'}, clear=False):
            result = service._build_infrastructure(row, tenant_config)

        assert result['openai']['model'] == 'gpt-4o'
        assert result['openai']['api_key'] == 'sk-test'

    def test_infrastructure_openai_default_model(self):
        """OpenAI should default to gpt-4o-mini"""
        service = self._make_service()
        row = self._make_row()

        result = service._build_infrastructure(row, {})

        assert result['openai']['model'] == 'gpt-4o-mini'

    def test_infrastructure_empty_env_vars(self):
        """Infrastructure should not crash with empty env vars"""
        service = self._make_service()
        row = self._make_row(gcp_project_id=None)

        with patch.dict(os.environ, {}, clear=True):
            result = service._build_infrastructure(row, {})

        assert result['supabase']['url'] == ''
        assert result['openai']['api_key'] == ''
        assert result['vapi']['api_key'] == ''


class TestBuildEmailConfig:
    """Test _build_email_config method"""

    def _make_service(self):
        return TenantConfigService()

    def _make_row(self, **overrides):
        row = {
            'id': 'test_tenant',
            'name': 'Test Tenant',
            'primary_email': 'hello@test.com',
            'tenant_config': {},
        }
        row.update(overrides)
        return row

    def test_email_primary_from_row(self):
        """Primary email should come from row column first"""
        service = self._make_service()
        row = self._make_row(primary_email='row@test.com')

        result = service._build_email_config(row, {})

        assert result['primary'] == 'row@test.com'

    def test_email_primary_falls_back_to_tenant_config(self):
        """Primary email should fall back to tenant_config"""
        service = self._make_service()
        row = self._make_row(primary_email=None)
        tenant_config = {
            'email': {
                'primary': 'config@test.com',
            }
        }

        result = service._build_email_config(row, tenant_config)

        assert result['primary'] == 'config@test.com'

    def test_email_sendgrid_api_key_from_env(self):
        """SendGrid API key should come from environment"""
        service = self._make_service()
        row = self._make_row()

        with patch.dict(os.environ, {'SENDGRID_MASTER_API_KEY': 'SG.master_key'}, clear=False):
            result = service._build_email_config(row, {})

        assert result['sendgrid']['api_key'] == 'SG.master_key'

    def test_email_sendgrid_from_name(self):
        """SendGrid from_name should default to tenant name"""
        service = self._make_service()
        row = self._make_row(name='Beach Resort')

        result = service._build_email_config(row, {})

        assert result['sendgrid']['from_name'] == 'Beach Resort'

    def test_email_smtp_password_from_env(self):
        """SMTP password should come from environment"""
        service = self._make_service()
        row = self._make_row()

        with patch.dict(os.environ, {'SMTP_PASSWORD': 'smtp_pass_123'}, clear=False):
            result = service._build_email_config(row, {})

        assert result['smtp']['password'] == 'smtp_pass_123'

    def test_email_smtp_tenant_specific_password(self):
        """SMTP should try tenant-specific env var first"""
        service = self._make_service()
        row = self._make_row()

        env = {
            'TEST_TENANT_SMTP_PASSWORD': 'tenant_smtp_pass',
            'SMTP_PASSWORD': 'shared_smtp_pass',
        }

        with patch.dict(os.environ, env, clear=False):
            result = service._build_email_config(row, {})

        assert result['smtp']['password'] == 'tenant_smtp_pass'

    def test_email_smtp_defaults(self):
        """SMTP should have sensible defaults"""
        service = self._make_service()
        row = self._make_row()

        result = service._build_email_config(row, {})

        assert result['smtp']['host'] == ''
        assert result['smtp']['port'] == 465
        assert result['smtp']['username'] == ''

    def test_email_imap_defaults(self):
        """IMAP should have sensible defaults"""
        service = self._make_service()
        row = self._make_row()

        result = service._build_email_config(row, {})

        assert result['imap']['host'] == ''
        assert result['imap']['port'] == 993

    def test_email_full_config_from_tenant_config(self):
        """Full email config should be buildable from tenant_config"""
        service = self._make_service()
        row = self._make_row()
        tenant_config = {
            'email': {
                'primary': 'primary@resort.com',
                'sendgrid': {
                    'from_email': 'noreply@resort.com',
                    'from_name': 'Resort Team',
                    'reply_to': 'support@resort.com',
                },
                'smtp': {
                    'host': 'smtp.resort.com',
                    'port': 587,
                    'username': 'smtp_user',
                },
                'imap': {
                    'host': 'imap.resort.com',
                    'port': 143,
                },
            }
        }

        result = service._build_email_config(row, tenant_config)

        assert result['sendgrid']['from_email'] == 'noreply@resort.com'
        assert result['sendgrid']['reply_to'] == 'support@resort.com'
        assert result['smtp']['host'] == 'smtp.resort.com'
        assert result['smtp']['port'] == 587
        assert result['imap']['host'] == 'imap.resort.com'
        assert result['imap']['port'] == 143


class TestRedisOperations:
    """Test _get_from_cache, _set_cache, and _invalidate_cache with mock Redis"""

    def _make_service_with_redis(self):
        service = TenantConfigService()
        mock_redis = MagicMock()
        service._redis = mock_redis
        service._redis_available = True
        return service, mock_redis

    def test_get_from_cache_returns_deserialized_json(self):
        """_get_from_cache should deserialize JSON from Redis"""
        service, mock_redis = self._make_service_with_redis()
        config = {'client': {'id': 'test'}}
        mock_redis.get.return_value = json.dumps(config).encode()

        result = service._get_from_cache('test_tenant')

        assert result == config
        mock_redis.get.assert_called_once_with('tenant_config:test_tenant')

    def test_get_from_cache_returns_none_on_miss(self):
        """_get_from_cache should return None on cache miss"""
        service, mock_redis = self._make_service_with_redis()
        mock_redis.get.return_value = None

        result = service._get_from_cache('nonexistent')

        assert result is None

    def test_get_from_cache_returns_none_on_redis_error(self):
        """_get_from_cache should return None on Redis error"""
        service, mock_redis = self._make_service_with_redis()
        mock_redis.get.side_effect = Exception("Connection refused")

        result = service._get_from_cache('test_tenant')

        assert result is None

    def test_get_from_cache_returns_none_when_redis_unavailable(self):
        """_get_from_cache should return None when Redis is not available"""
        service = TenantConfigService()
        service._redis_available = False

        result = service._get_from_cache('test_tenant')

        assert result is None

    def test_set_cache_stores_with_ttl(self):
        """_set_cache should store JSON with configured TTL"""
        service, mock_redis = self._make_service_with_redis()
        config = {'client': {'id': 'test'}}

        service._set_cache('test_tenant', config)

        mock_redis.setex.assert_called_once_with(
            'tenant_config:test_tenant',
            300,
            json.dumps(config)
        )

    def test_set_cache_does_nothing_when_redis_unavailable(self):
        """_set_cache should silently skip when Redis unavailable"""
        service = TenantConfigService()
        service._redis_available = False

        # Should not raise
        service._set_cache('test_tenant', {'client': {'id': 'test'}})

    def test_set_cache_handles_redis_error(self):
        """_set_cache should handle Redis write errors gracefully"""
        service, mock_redis = self._make_service_with_redis()
        mock_redis.setex.side_effect = Exception("Redis write error")

        # Should not raise
        service._set_cache('test_tenant', {'client': {'id': 'test'}})

    def test_invalidate_cache_deletes_key(self):
        """_invalidate_cache should delete the tenant key from Redis"""
        service, mock_redis = self._make_service_with_redis()

        service._invalidate_cache('test_tenant')

        mock_redis.delete.assert_called_once_with('tenant_config:test_tenant')

    def test_invalidate_cache_does_nothing_when_redis_unavailable(self):
        """_invalidate_cache should silently skip when Redis unavailable"""
        service = TenantConfigService()
        service._redis_available = False

        # Should not raise
        service._invalidate_cache('test_tenant')

    def test_invalidate_cache_handles_redis_error(self):
        """_invalidate_cache should handle Redis errors gracefully"""
        service, mock_redis = self._make_service_with_redis()
        mock_redis.delete.side_effect = Exception("Redis delete error")

        # Should not raise
        service._invalidate_cache('test_tenant')


class TestGetServiceSingleton:
    """Test get_service singleton behavior"""

    def test_get_service_returns_same_instance(self):
        """get_service should return the same instance on repeated calls"""
        from src.services.tenant_config_service import get_service, reset_service

        reset_service()
        first = get_service()
        second = get_service()

        assert first is second

    def test_get_service_returns_tenant_config_service(self):
        """get_service should return a TenantConfigService instance"""
        from src.services.tenant_config_service import get_service, reset_service

        reset_service()
        instance = get_service()

        assert isinstance(instance, TenantConfigService)

    def test_reset_service_clears_singleton(self):
        """reset_service should allow creating a new instance"""
        from src.services.tenant_config_service import get_service, reset_service

        reset_service()
        first = get_service()
        reset_service()
        second = get_service()

        assert first is not second


class TestEdgeCases:
    """Test edge cases: empty config, missing fields, malformed data"""

    def test_get_config_returns_none_when_not_found(self):
        """get_config should return None when tenant not in database"""
        service = TenantConfigService()

        with patch.object(service, '_get_from_cache', return_value=None):
            with patch.object(service, '_load_from_database', return_value=None):
                result = service.get_config('nonexistent_tenant')
                assert result is None

    def test_get_config_does_not_cache_none(self):
        """get_config should NOT cache None (tenant not found)"""
        service = TenantConfigService()

        with patch.object(service, '_get_from_cache', return_value=None):
            with patch.object(service, '_load_from_database', return_value=None):
                with patch.object(service, '_set_cache') as mock_set:
                    service.get_config('nonexistent')
                    mock_set.assert_not_called()

    def test_strip_secrets_handles_empty_config(self):
        """_strip_secrets should handle empty config gracefully"""
        service = TenantConfigService()

        result = service._strip_secrets({})
        assert isinstance(result, dict)

    def test_strip_secrets_handles_missing_sections(self):
        """_strip_secrets should handle config with missing infrastructure/email"""
        service = TenantConfigService()

        config = {'client': {'id': 'test'}, 'destinations': []}
        result = service._strip_secrets(config)

        assert 'client' not in result  # client is stripped (stored in columns)
        assert 'destinations' in result

    def test_build_infrastructure_with_empty_tenant_config(self):
        """_build_infrastructure should not crash with completely empty tenant_config"""
        service = TenantConfigService()
        row = {'id': 'test', 'gcp_project_id': None, 'gcp_dataset': None}

        with patch.dict(os.environ, {}, clear=True):
            result = service._build_infrastructure(row, {})

        assert 'gcp' in result
        assert 'supabase' in result
        assert 'vapi' in result
        assert 'openai' in result

    def test_build_email_config_with_empty_tenant_config(self):
        """_build_email_config should not crash with completely empty tenant_config"""
        service = TenantConfigService()
        row = {'id': 'test', 'name': 'Test', 'primary_email': None}

        result = service._build_email_config(row, {})

        assert 'sendgrid' in result
        assert 'smtp' in result
        assert 'imap' in result
        assert result['primary'] == ''

    def test_build_client_info_with_long_id_short_name(self):
        """Short name should be truncated from id when not provided"""
        service = TenantConfigService()
        long_id = 'this-is-a-really-long-tenant-identifier-name'
        row = {'id': long_id, 'name': None, 'short_name': None, 'timezone': None, 'currency': None}

        result = service._build_client_info(row, {})

        assert len(result['short_name']) <= 20

    def test_save_config_returns_false_when_no_supabase(self):
        """save_config should return False when Supabase is unavailable"""
        service = TenantConfigService()

        with patch.object(service, '_get_supabase_client', return_value=None):
            result = service.save_config('test', {'client': {'id': 'test'}})
            assert result is False

    def test_save_config_returns_false_on_db_error(self):
        """save_config should return False on database error"""
        service = TenantConfigService()

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.upsert.return_value.execute.side_effect = Exception("Upsert failed")

        with patch.object(service, '_get_supabase_client', return_value=mock_supabase):
            result = service.save_config('test', {'client': {'id': 'test'}})
            assert result is False

    def test_tenant_exists_returns_false_when_no_supabase(self):
        """tenant_exists should return False when Supabase is unavailable"""
        service = TenantConfigService()

        with patch.object(service, '_get_supabase_client', return_value=None):
            assert service.tenant_exists('any') is False

    def test_tenant_exists_returns_true_when_found(self):
        """tenant_exists should return True when tenant found in DB"""
        service = TenantConfigService()

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={'id': 'found'})

        with patch.object(service, '_get_supabase_client', return_value=mock_supabase):
            assert service.tenant_exists('found') is True

    def test_tenant_exists_returns_false_on_exception(self):
        """tenant_exists should return False on database exception"""
        service = TenantConfigService()

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("Not found")

        with patch.object(service, '_get_supabase_client', return_value=mock_supabase):
            assert service.tenant_exists('missing') is False

    def test_get_tenant_status_returns_unknown_when_no_supabase(self):
        """get_tenant_status should return 'unknown' when Supabase is unavailable"""
        service = TenantConfigService()

        with patch.object(service, '_get_supabase_client', return_value=None):
            assert service.get_tenant_status('any') == 'unknown'

    def test_get_tenant_status_returns_status_from_db(self):
        """get_tenant_status should return status from DB row"""
        service = TenantConfigService()

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={'status': 'suspended'})

        with patch.object(service, '_get_supabase_client', return_value=mock_supabase):
            assert service.get_tenant_status('test') == 'suspended'


class TestSubstituteEnvVars:
    """Test _substitute_env_vars helper function"""

    def test_substitute_simple_var(self):
        """Should substitute ${VAR} with env value"""
        from src.services.tenant_config_service import _substitute_env_vars

        with patch.dict(os.environ, {'MY_VAR': 'hello'}, clear=False):
            result = _substitute_env_vars('value is ${MY_VAR}')
            assert result == 'value is hello'

    def test_substitute_with_default(self):
        """Should use default when env var not set"""
        from src.services.tenant_config_service import _substitute_env_vars

        with patch.dict(os.environ, {}, clear=True):
            result = _substitute_env_vars('${MISSING_VAR:-fallback}')
            assert result == 'fallback'

    def test_substitute_in_dict(self):
        """Should recursively substitute in dicts"""
        from src.services.tenant_config_service import _substitute_env_vars

        with patch.dict(os.environ, {'TEST_KEY': 'resolved'}, clear=False):
            result = _substitute_env_vars({'key': '${TEST_KEY}'})
            assert result == {'key': 'resolved'}

    def test_substitute_in_list(self):
        """Should recursively substitute in lists"""
        from src.services.tenant_config_service import _substitute_env_vars

        with patch.dict(os.environ, {'LIST_VAL': 'item'}, clear=False):
            result = _substitute_env_vars(['${LIST_VAL}', 'static'])
            assert result == ['item', 'static']

    def test_substitute_leaves_non_strings_alone(self):
        """Should leave ints, bools, etc. unchanged"""
        from src.services.tenant_config_service import _substitute_env_vars

        assert _substitute_env_vars(42) == 42
        assert _substitute_env_vars(True) is True
        assert _substitute_env_vars(None) is None


class TestCacheInfoWithRedis:
    """Test get_cache_info with mock Redis"""

    def test_cache_info_with_redis_available(self):
        """get_cache_info should return Redis info when available"""
        service = TenantConfigService()
        mock_redis = MagicMock()
        mock_redis.scan.return_value = (0, [b'tenant_config:a', b'tenant_config:b'])
        service._redis = mock_redis
        service._redis_available = True

        info = service.get_cache_info()

        assert info['backend'] == 'redis'
        assert info['available'] is True
        assert info['cached_tenants'] == 2

    def test_cache_info_redis_error(self):
        """get_cache_info should handle Redis errors gracefully"""
        service = TenantConfigService()
        mock_redis = MagicMock()
        mock_redis.scan.side_effect = Exception("Connection lost")
        service._redis = mock_redis
        service._redis_available = True

        info = service.get_cache_info()

        assert info['backend'] == 'redis'
        assert info['available'] is False


class TestInvalidateAllCache:
    """Test invalidate_all_cache method"""

    def test_invalidate_all_cache_scans_and_deletes(self):
        """invalidate_all_cache should scan and delete all tenant keys"""
        service = TenantConfigService()
        mock_redis = MagicMock()
        mock_redis.scan.return_value = (0, [b'tenant_config:a', b'tenant_config:b'])
        service._redis = mock_redis
        service._redis_available = True

        service.invalidate_all_cache()

        mock_redis.delete.assert_called_once_with(b'tenant_config:a', b'tenant_config:b')

    def test_invalidate_all_cache_handles_no_keys(self):
        """invalidate_all_cache should handle case with no cached keys"""
        service = TenantConfigService()
        mock_redis = MagicMock()
        mock_redis.scan.return_value = (0, [])
        service._redis = mock_redis
        service._redis_available = True

        # Should not raise and should not call delete
        service.invalidate_all_cache()
        mock_redis.delete.assert_not_called()

    def test_invalidate_all_cache_does_nothing_when_redis_unavailable(self):
        """invalidate_all_cache should skip when Redis unavailable"""
        service = TenantConfigService()
        service._redis_available = False

        # Should not raise
        service.invalidate_all_cache()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
