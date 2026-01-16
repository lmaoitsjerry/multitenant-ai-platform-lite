"""
Tests for email webhook tenant lookup functionality.

Tests the caching and lookup mechanisms for tenant resolution.
"""

import pytest
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the module functions we need to test
from src.webhooks.email_webhook import (
    find_tenant_by_email,
    get_tenant_email_addresses,
    _refresh_tenant_email_cache,
    _tenant_email_cache,
    _get_cached_tenant_lookup,
    TENANT_CACHE_TTL
)


class TestTenantEmailCache:
    """Test tenant email caching functionality"""

    def setup_method(self):
        """Clear cache before each test"""
        global _tenant_email_cache
        _tenant_email_cache.clear()

    @patch('src.webhooks.email_webhook.list_clients')
    @patch('src.webhooks.email_webhook.get_tenant_email_addresses')
    def test_cache_refresh_builds_email_mapping(self, mock_get_emails, mock_list):
        """Should build email->tenant mapping on cache refresh"""
        mock_list.return_value = ['tenant1', 'tenant2']
        mock_get_emails.side_effect = [
            {
                'support_email': 'support@company1.com',
                'sendgrid_email': 'tenant1@zorah.ai',
                'primary_email': 'admin@company1.com',
                'tenant_id': 'tenant1'
            },
            {
                'support_email': 'support@company2.com',
                'sendgrid_email': 'tenant2@zorah.ai',
                'primary_email': None,
                'tenant_id': 'tenant2'
            }
        ]

        result = _refresh_tenant_email_cache()

        assert 'support@company1.com' in result
        assert 'tenant1@zorah.ai' in result
        assert 'support@company2.com' in result
        assert 'tenant2@zorah.ai' in result

    @patch('src.webhooks.email_webhook.list_clients')
    @patch('src.webhooks.email_webhook.get_tenant_email_addresses')
    def test_cache_stores_strategy_with_tenant(self, mock_get_emails, mock_list):
        """Should store both tenant_id and strategy in cache"""
        mock_list.return_value = ['tenant1']
        mock_get_emails.return_value = {
            'support_email': 'support@company.com',
            'sendgrid_email': 'final-itc@zorah.ai',
            'primary_email': None,
            'tenant_id': 'tenant1'
        }

        result = _refresh_tenant_email_cache()

        assert result['support@company.com']['tenant_id'] == 'tenant1'
        assert result['support@company.com']['strategy'] == 'support_email'
        assert result['final-itc@zorah.ai']['strategy'] == 'sendgrid_email'


class TestTenantLookup:
    """Test tenant email lookup functionality"""

    def setup_method(self):
        """Clear cache before each test"""
        global _tenant_email_cache
        _tenant_email_cache.clear()

    @patch('src.webhooks.email_webhook.list_clients')
    @patch('src.webhooks.email_webhook.get_tenant_email_addresses')
    def test_find_tenant_by_support_email(self, mock_get_emails, mock_list):
        """Should find tenant by support_email"""
        mock_list.return_value = ['tenant1']
        mock_get_emails.return_value = {
            'support_email': 'support@company.com',
            'sendgrid_email': None,
            'primary_email': None,
            'tenant_id': 'tenant1'
        }

        tenant_id, strategy, cache_hit = find_tenant_by_email('support@company.com')

        assert tenant_id == 'tenant1'
        assert strategy == 'support_email'

    @patch('src.webhooks.email_webhook.list_clients')
    @patch('src.webhooks.email_webhook.get_tenant_email_addresses')
    def test_find_tenant_by_sendgrid_email(self, mock_get_emails, mock_list):
        """Should find tenant by sendgrid_username@zorah.ai"""
        mock_list.return_value = ['africastay']
        mock_get_emails.return_value = {
            'support_email': None,
            'sendgrid_email': 'final-itc-3@zorah.ai',
            'primary_email': None,
            'tenant_id': 'africastay'
        }

        tenant_id, strategy, cache_hit = find_tenant_by_email('final-itc-3@zorah.ai')

        assert tenant_id == 'africastay'
        assert strategy == 'sendgrid_email'

    @patch('src.webhooks.email_webhook.list_clients')
    @patch('src.webhooks.email_webhook.get_tenant_email_addresses')
    def test_find_tenant_by_primary_email(self, mock_get_emails, mock_list):
        """Should find tenant by primary_email"""
        mock_list.return_value = ['tenant1']
        mock_get_emails.return_value = {
            'support_email': None,
            'sendgrid_email': None,
            'primary_email': 'owner@company.com',
            'tenant_id': 'tenant1'
        }

        tenant_id, strategy, cache_hit = find_tenant_by_email('owner@company.com')

        assert tenant_id == 'tenant1'
        assert strategy == 'primary_email'

    @patch('src.webhooks.email_webhook.list_clients')
    @patch('src.webhooks.email_webhook.get_tenant_email_addresses')
    def test_find_tenant_case_insensitive(self, mock_get_emails, mock_list):
        """Should match emails case-insensitively"""
        mock_list.return_value = ['tenant1']
        mock_get_emails.return_value = {
            'support_email': 'Support@Company.COM',
            'sendgrid_email': None,
            'primary_email': None,
            'tenant_id': 'tenant1'
        }

        tenant_id, strategy, cache_hit = find_tenant_by_email('SUPPORT@company.com')

        assert tenant_id == 'tenant1'
        assert strategy == 'support_email'

    @patch('src.webhooks.email_webhook.list_clients')
    @patch('src.webhooks.email_webhook.get_tenant_email_addresses')
    def test_not_found_returns_none(self, mock_get_emails, mock_list):
        """Should return None for unknown emails"""
        mock_list.return_value = ['tenant1']
        mock_get_emails.return_value = {
            'support_email': 'other@company.com',
            'sendgrid_email': None,
            'primary_email': None,
            'tenant_id': 'tenant1'
        }

        tenant_id, strategy, cache_hit = find_tenant_by_email('unknown@nowhere.com')

        assert tenant_id is None
        assert strategy == 'none'

    @patch('src.webhooks.email_webhook.list_clients')
    @patch('src.webhooks.email_webhook.get_tenant_email_addresses')
    def test_cache_hit_on_second_lookup(self, mock_get_emails, mock_list):
        """Should use cache on second lookup"""
        mock_list.return_value = ['tenant1']
        mock_get_emails.return_value = {
            'support_email': 'support@company.com',
            'sendgrid_email': None,
            'primary_email': None,
            'tenant_id': 'tenant1'
        }

        # First lookup - builds cache
        tenant_id1, strategy1, cache_hit1 = find_tenant_by_email('support@company.com')

        # Reset mocks to track if they're called again
        mock_list.reset_mock()
        mock_get_emails.reset_mock()

        # Second lookup - should use cache
        tenant_id2, strategy2, cache_hit2 = find_tenant_by_email('support@company.com')

        assert tenant_id2 == 'tenant1'
        assert cache_hit2 is True
        # list_clients should not be called again (cache hit path)
        mock_list.assert_not_called()

    @patch('src.webhooks.email_webhook.list_clients')
    @patch('src.webhooks.email_webhook.get_tenant_email_addresses')
    def test_email_with_whitespace_stripped(self, mock_get_emails, mock_list):
        """Should strip whitespace from email addresses"""
        mock_list.return_value = ['tenant1']
        mock_get_emails.return_value = {
            'support_email': 'support@company.com',
            'sendgrid_email': None,
            'primary_email': None,
            'tenant_id': 'tenant1'
        }

        tenant_id, strategy, cache_hit = find_tenant_by_email('  support@company.com  ')

        assert tenant_id == 'tenant1'


class TestCacheTTL:
    """Test cache TTL behavior"""

    def test_cache_ttl_constant_exists(self):
        """Should have cache TTL constant defined"""
        assert TENANT_CACHE_TTL == 300  # 5 minutes


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
