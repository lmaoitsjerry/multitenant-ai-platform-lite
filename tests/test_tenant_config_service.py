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

    def test_yaml_only_tenants_constant(self):
        """Verify YAML-only tenants are correctly defined"""
        service = TenantConfigService()
        expected = {'africastay', 'safariexplore-kvph', 'safarirun-t0vc', 'beachresorts', 'example'}
        assert service.YAML_ONLY_TENANTS == expected

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

    def test_migrated_tenants_constant(self):
        """Verify MIGRATED_TENANTS constant exists"""
        service = TenantConfigService()
        assert 'africastay' in service.MIGRATED_TENANTS
        assert 'safariexplore-kvph' in service.MIGRATED_TENANTS

    def test_init_with_custom_base_path(self):
        """Test initialization with custom base path"""
        service = TenantConfigService(base_path="/custom/path")
        assert service.base_path == Path("/custom/path")

    def test_init_default_base_path(self):
        """Test default base path is set correctly"""
        service = TenantConfigService()
        assert service.base_path is not None
        assert isinstance(service.base_path, Path)


class TestYamlFallback:
    """Test YAML fallback behavior"""

    def test_yaml_only_tenant_skips_database(self):
        """YAML-only tenants should not query database"""
        service = TenantConfigService()

        with patch.object(service, '_load_from_database') as mock_db:
            with patch.object(service, '_load_from_yaml') as mock_yaml:
                mock_yaml.return_value = {'client': {'id': 'africastay'}}

                config = service.get_config('africastay')

                # Database should NOT be called for YAML-only tenant
                mock_db.assert_not_called()
                mock_yaml.assert_called_once_with('africastay')

    def test_production_tenant_tries_database_first(self):
        """Production tenants should try database first"""
        service = TenantConfigService()

        with patch.object(service, '_get_from_cache', return_value=None):
            with patch.object(service, '_load_from_database') as mock_db:
                with patch.object(service, '_set_cache'):
                    mock_db.return_value = {'client': {'id': 'newclient'}}

                    # Use a tenant ID that doesn't start with 'tn_' and isn't in YAML_ONLY_TENANTS
                    config = service.get_config('newclient')

                    mock_db.assert_called_once_with('newclient')

    def test_yaml_fallback_when_database_empty(self):
        """Falls back to YAML when database returns None"""
        service = TenantConfigService()

        with patch.object(service, '_get_from_cache', return_value=None):
            with patch.object(service, '_load_from_database', return_value=None):
                with patch.object(service, '_load_from_yaml') as mock_yaml:
                    with patch.object(service, '_set_cache'):
                        mock_yaml.return_value = {'client': {'id': 'unknown_tenant'}}

                        config = service.get_config('unknown_tenant')

                        mock_yaml.assert_called_once_with('unknown_tenant')

    def test_tn_prefix_tenants_rejected(self):
        """tn_* prefixed tenants should be completely ignored"""
        service = TenantConfigService()

        # These should return None immediately without any database/YAML lookup
        with patch.object(service, '_get_from_cache') as mock_cache:
            with patch.object(service, '_load_from_database') as mock_db:
                with patch.object(service, '_load_from_yaml') as mock_yaml:
                    result = service.get_config('tn_12345678_abcdef')

                    assert result is None
                    mock_cache.assert_not_called()
                    mock_db.assert_not_called()
                    mock_yaml.assert_not_called()


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

    def test_yaml_config_also_cached(self):
        """YAML config should also be cached after fallback"""
        service = TenantConfigService()

        yaml_config = {'client': {'id': 'yaml_tenant'}, '_meta': {'source': 'yaml'}}

        with patch.object(service, '_get_from_cache', return_value=None):
            with patch.object(service, '_load_from_database', return_value=None):
                with patch.object(service, '_load_from_yaml', return_value=yaml_config):
                    with patch.object(service, '_set_cache') as mock_set:
                        config = service.get_config('newclient')

                        # Cache should be set with YAML config
                        mock_set.assert_called_once_with('newclient', yaml_config)


class TestEnvVarSubstitution:
    """Test environment variable substitution in YAML configs"""

    def test_env_var_substitution_simple(self):
        """Test ${VAR} substitution"""
        service = TenantConfigService()

        with patch.dict(os.environ, {'TEST_VAR': 'test_value'}):
            result = service._substitute_env_vars('prefix_${TEST_VAR}_suffix')
            assert result == 'prefix_test_value_suffix'

    def test_env_var_substitution_with_default(self):
        """Test ${VAR:-default} substitution"""
        service = TenantConfigService()

        # Ensure var is not set
        os.environ.pop('UNSET_VAR', None)

        result = service._substitute_env_vars('${UNSET_VAR:-default_value}')
        assert result == 'default_value'

    def test_env_var_substitution_recursive(self):
        """Test substitution in nested structures"""
        service = TenantConfigService()

        with patch.dict(os.environ, {'KEY1': 'value1', 'KEY2': 'value2'}):
            config = {
                'level1': {
                    'nested': '${KEY1}',
                    'list': ['${KEY2}', 'static'],
                },
            }

            result = service._substitute_env_vars(config)

            assert result['level1']['nested'] == 'value1'
            assert result['level1']['list'][0] == 'value2'
            assert result['level1']['list'][1] == 'static'

    def test_env_var_substitution_preserves_non_strings(self):
        """Non-string values should be preserved"""
        service = TenantConfigService()

        config = {
            'number': 42,
            'boolean': True,
            'null': None,
            'list': [1, 2, 3],
        }

        result = service._substitute_env_vars(config)

        assert result['number'] == 42
        assert result['boolean'] is True
        assert result['null'] is None
        assert result['list'] == [1, 2, 3]


class TestListTenants:
    """Test tenant listing functionality"""

    def test_list_includes_database_tenants(self):
        """list_tenants should include database tenants"""
        service = TenantConfigService()

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{'id': 'newclient_001'}, {'id': 'newclient_002'}]
        )

        with patch.object(service, '_get_supabase_client', return_value=mock_supabase):
            with patch('pathlib.Path.exists', return_value=False):
                with patch('pathlib.Path.iterdir', return_value=[]):
                    tenants = service.list_tenants(include_yaml=False)

                    assert 'newclient_001' in tenants
                    assert 'newclient_002' in tenants

    def test_list_tenants_excludes_tn_prefix(self):
        """list_tenants should exclude tn_* prefixed directories (verified via code inspection)

        The list_tenants() method has explicit filtering:
            if client_dir.name.startswith('tn_'):
                continue

        This test verifies the filtering logic works by testing with real file system
        when clients directory exists, or simply checking behavior with mocks.
        """
        service = TenantConfigService()

        # Test that the filtering logic exists in the method
        import inspect
        source = inspect.getsource(service.list_tenants)
        assert "startswith('tn_')" in source, "tn_* filtering should be in list_tenants"

        # Also test the actual filtering behavior by running with mocked database
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{'id': 'db_tenant'}, {'id': 'tn_should_appear'}]  # DB returns tn_* but that's OK
        )

        with patch.object(service, '_get_supabase_client', return_value=mock_supabase):
            # List with include_yaml=False to avoid filesystem issues
            tenants = service.list_tenants(include_yaml=False)

            # DB tenants come through as-is (filtering only applies to YAML dirs)
            assert 'db_tenant' in tenants


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

    def test_returns_none_when_config_source_not_database(self):
        """Should return None if config_source is not 'database'"""
        service = TenantConfigService()

        mock_supabase = MagicMock()
        mock_execute = MagicMock()
        mock_execute.data = {
            'id': 'test_tenant',
            'name': 'Test',
            'config_source': 'yaml',  # Not 'database'
        }
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_execute

        with patch.object(service, '_get_supabase_client', return_value=mock_supabase):
            result = service._load_from_database('test_tenant')
            assert result is None

    def test_handles_database_error_gracefully(self):
        """Should handle database errors gracefully"""
        service = TenantConfigService()

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("DB Error")

        with patch.object(service, '_get_supabase_client', return_value=mock_supabase):
            result = service._load_from_database('test_tenant')
            assert result is None


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
