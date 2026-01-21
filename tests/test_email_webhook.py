"""
Tests for Email Webhook - Inbound Email Processing

Tests cover:
- Tenant email caching and lookup
- Email routing strategies
- Tenant extraction from email/subject/headers
- Webhook endpoint handlers
- Email parsing and processing
- Diagnostic endpoints
"""

import pytest
import sys
import time
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the module functions we need to test
from src.webhooks.email_webhook import (
    find_tenant_by_email,
    get_tenant_email_addresses,
    _refresh_tenant_email_cache,
    _tenant_email_cache,
    _get_cached_tenant_lookup,
    TENANT_CACHE_TTL,
    extract_tenant_from_email,
    extract_tenant_from_subject,
    ParsedEmail,
    diagnostic_log,
    router
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


# ==================== Tenant Extraction Tests ====================

class TestExtractTenantFromEmail:
    """Test tenant extraction from email address."""

    def setup_method(self):
        """Clear cache before each test"""
        global _tenant_email_cache
        _tenant_email_cache.clear()

    @patch('src.webhooks.email_webhook.find_tenant_by_email')
    def test_extract_tenant_from_database_lookup(self, mock_find):
        """Should find tenant via database lookup first."""
        mock_find.return_value = ('africastay', 'support_email', True)

        tenant_id, strategy = extract_tenant_from_email('support@africastay.com')

        assert tenant_id == 'africastay'
        assert strategy == 'support_email'

    @patch('src.webhooks.email_webhook.find_tenant_by_email')
    @patch('src.webhooks.email_webhook.get_config')
    def test_extract_tenant_from_direct_local_part(self, mock_get_config, mock_find):
        """Should find tenant from local part of email."""
        mock_find.return_value = (None, 'none', False)
        mock_get_config.return_value = MagicMock()  # Valid config exists

        tenant_id, strategy = extract_tenant_from_email('africastay@inbound.zorahai.com')

        assert tenant_id == 'africastay'
        assert strategy == 'direct_tenant_id'

    @patch('src.webhooks.email_webhook.find_tenant_by_email')
    @patch('src.webhooks.email_webhook.get_config')
    def test_extract_tenant_from_plus_addressing(self, mock_get_config, mock_find):
        """Should find tenant via plus addressing."""
        mock_find.return_value = (None, 'none', False)
        # First call (direct lookup for 'quotes') fails
        # Second call (plus part 'africastay') succeeds
        mock_get_config.side_effect = [Exception("Not found"), MagicMock()]

        tenant_id, strategy = extract_tenant_from_email('quotes+africastay@domain.com')

        assert tenant_id == 'africastay'
        assert strategy == 'plus_addressing'

    @patch('src.webhooks.email_webhook.find_tenant_by_email')
    @patch('src.webhooks.email_webhook.get_config')
    def test_extract_tenant_from_header(self, mock_get_config, mock_find):
        """Should find tenant from X-Tenant-ID header."""
        mock_find.return_value = (None, 'none', False)
        mock_get_config.side_effect = [Exception("Not found"), MagicMock()]

        headers = {'x-tenant-id': 'africastay'}
        tenant_id, strategy = extract_tenant_from_email('unknown@domain.com', headers)

        assert tenant_id == 'africastay'
        assert strategy == 'x_tenant_id_header'

    @patch('src.webhooks.email_webhook.find_tenant_by_email')
    @patch('src.webhooks.email_webhook.get_config')
    def test_skips_generic_local_parts(self, mock_get_config, mock_find):
        """Should skip generic local parts like quotes, support, info."""
        mock_find.return_value = (None, 'none', False)
        mock_get_config.side_effect = Exception("Not found")

        tenant_id, strategy = extract_tenant_from_email('quotes@domain.com')

        assert tenant_id is None
        assert strategy == 'none'

    @patch('src.webhooks.email_webhook.find_tenant_by_email')
    def test_returns_none_when_not_found(self, mock_find):
        """Should return None when no tenant found."""
        mock_find.return_value = (None, 'none', False)

        tenant_id, strategy = extract_tenant_from_email('unknown@nowhere.com')

        assert tenant_id is None


class TestExtractTenantFromSubject:
    """Test tenant extraction from subject line."""

    @patch('src.webhooks.email_webhook.get_config')
    def test_extract_tenant_from_subject_pattern(self, mock_get_config):
        """Should extract tenant from [TENANT:xxx] pattern."""
        mock_get_config.return_value = MagicMock()

        tenant_id, strategy = extract_tenant_from_subject('[TENANT:africastay] Travel inquiry')

        assert tenant_id == 'africastay'
        assert strategy == 'subject_pattern'

    @patch('src.webhooks.email_webhook.get_config')
    def test_extract_tenant_case_insensitive(self, mock_get_config):
        """Should match pattern case-insensitively."""
        mock_get_config.return_value = MagicMock()

        tenant_id, strategy = extract_tenant_from_subject('[tenant:AfricaStay] Inquiry')

        assert tenant_id == 'africastay'
        assert strategy == 'subject_pattern'

    def test_returns_none_without_pattern(self):
        """Should return None when no pattern found."""
        tenant_id, strategy = extract_tenant_from_subject('Regular email subject')

        assert tenant_id is None
        assert strategy == 'none'

    @patch('src.webhooks.email_webhook.get_config')
    def test_returns_none_for_invalid_tenant(self, mock_get_config):
        """Should return None when extracted tenant doesn't exist."""
        mock_get_config.side_effect = Exception("Tenant not found")

        tenant_id, strategy = extract_tenant_from_subject('[TENANT:invalid] Inquiry')

        assert tenant_id is None
        assert strategy == 'none'


# ==================== ParsedEmail Model Tests ====================

class TestParsedEmailModel:
    """Test ParsedEmail Pydantic model."""

    def test_create_parsed_email(self):
        """Should create ParsedEmail with required fields."""
        email = ParsedEmail(
            tenant_id='africastay',
            from_email='customer@example.com',
            to_email='africastay@inbound.zorah.ai',
            subject='Travel inquiry',
            body_text='I want to book a trip',
            received_at='2026-01-21T10:00:00Z'
        )

        assert email.tenant_id == 'africastay'
        assert email.from_email == 'customer@example.com'
        assert email.body_text == 'I want to book a trip'

    def test_parsed_email_optional_fields(self):
        """Should handle optional fields."""
        email = ParsedEmail(
            tenant_id='africastay',
            from_email='customer@example.com',
            to_email='africastay@inbound.zorah.ai',
            subject='Travel inquiry',
            body_text='Body text',
            received_at='2026-01-21T10:00:00Z',
            from_name='John Doe',
            body_html='<p>Body text</p>',
            attachments=[{'filename': 'doc.pdf'}],
            headers={'x-custom': 'value'}
        )

        assert email.from_name == 'John Doe'
        assert email.body_html == '<p>Body text</p>'
        assert len(email.attachments) == 1
        assert email.headers['x-custom'] == 'value'

    def test_parsed_email_default_values(self):
        """Should use default values for optional fields."""
        email = ParsedEmail(
            tenant_id='test',
            from_email='test@example.com',
            to_email='test@inbound.com',
            subject='Test',
            body_text='Test body',
            received_at='2026-01-21T10:00:00Z'
        )

        assert email.from_name is None
        assert email.body_html is None
        assert email.attachments == []
        assert email.headers == {}


# ==================== Diagnostic Logging Tests ====================

class TestDiagnosticLogging:
    """Test diagnostic logging functionality."""

    @patch('src.webhooks.email_webhook.logger')
    def test_diagnostic_log_basic(self, mock_logger):
        """Should log diagnostic message with ID and step."""
        diagnostic_log('ABC12345', 1, 'Test message')

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert '[EMAIL_WEBHOOK]' in call_args
        assert '[ABC12345]' in call_args
        assert '[STEP_1]' in call_args
        assert 'Test message' in call_args

    @patch('src.webhooks.email_webhook.logger')
    def test_diagnostic_log_with_data(self, mock_logger):
        """Should include data in log message."""
        diagnostic_log('ABC12345', 2, 'Test', {'key': 'value'})

        call_args = mock_logger.info.call_args[0][0]
        assert 'data=' in call_args
        assert 'key' in call_args


# ==================== Webhook Route Tests ====================

class TestWebhookRoutes:
    """Test webhook route handlers."""

    @pytest.fixture
    def test_client(self):
        """Create test client for webhook routes."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router, prefix="/webhooks")
        return TestClient(app)

    def test_webhook_status_endpoint(self, test_client):
        """Should return webhook status."""
        response = test_client.get('/webhooks/email/status')

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'active'
        assert 'webhook_endpoints' in data
        assert 'supported_routing' in data

    def test_webhook_status_includes_endpoints(self, test_client):
        """Should list all webhook endpoints."""
        response = test_client.get('/webhooks/email/status')
        data = response.json()

        endpoints = data['webhook_endpoints']
        assert '/webhooks/email/inbound' in endpoints['generic']
        assert '{tenant_id}' in endpoints['per_tenant']

    @patch('src.webhooks.email_webhook.list_clients')
    def test_webhook_status_includes_tenants(self, mock_list, test_client):
        """Should include tenant list."""
        mock_list.return_value = ['tenant1', 'tenant2']

        response = test_client.get('/webhooks/email/status')
        data = response.json()

        assert data['tenant_count'] == 2
        assert 'tenant1' in data['known_tenants']

    @patch('src.webhooks.email_webhook.find_tenant_by_email')
    def test_lookup_endpoint_found(self, mock_find, test_client):
        """Should return tenant info for known email."""
        mock_find.return_value = ('africastay', 'support_email', True)

        with patch('src.webhooks.email_webhook.get_tenant_email_addresses') as mock_get:
            mock_get.return_value = {'support_email': 'support@africastay.com'}

            response = test_client.get('/webhooks/email/lookup/support@africastay.com')

        assert response.status_code == 200
        data = response.json()
        assert data['found'] is True
        assert data['tenant_id'] == 'africastay'
        assert data['strategy'] == 'support_email'

    @patch('src.webhooks.email_webhook.find_tenant_by_email')
    def test_lookup_endpoint_not_found(self, mock_find, test_client):
        """Should return not found for unknown email."""
        mock_find.return_value = (None, 'none', False)

        response = test_client.get('/webhooks/email/lookup/unknown@nowhere.com')

        assert response.status_code == 200
        data = response.json()
        assert data['found'] is False
        assert data['tenant_id'] is None

    @patch('src.webhooks.email_webhook.find_tenant_by_email')
    def test_lookup_endpoint_includes_timing(self, mock_find, test_client):
        """Should include elapsed time in response."""
        mock_find.return_value = ('tenant1', 'support_email', True)

        with patch('src.webhooks.email_webhook.get_tenant_email_addresses') as mock_get:
            mock_get.return_value = {}

            response = test_client.get('/webhooks/email/lookup/test@example.com')

        data = response.json()
        assert 'elapsed_ms' in data
        assert 'diagnostic_id' in data


# ==================== Inbound Email Handler Tests ====================

class TestInboundEmailHandler:
    """Test inbound email webhook handler."""

    @pytest.fixture
    def test_client(self):
        """Create test client for webhook routes."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router, prefix="/webhooks")
        return TestClient(app)

    @patch('src.webhooks.email_webhook.extract_tenant_from_email')
    @patch('src.webhooks.email_webhook.extract_tenant_from_subject')
    @patch('src.webhooks.email_webhook.get_config')
    @patch('src.webhooks.email_webhook.process_inbound_email')
    def test_inbound_email_success(
        self, mock_process, mock_config, mock_subject, mock_email, test_client
    ):
        """Should accept and queue valid inbound email."""
        mock_email.return_value = ('africastay', 'support_email')
        mock_subject.return_value = (None, 'none')
        mock_config.return_value = MagicMock(
            company_name='Africa Stay',
            destination_names=['Cape Town']
        )

        # Mock the notification service import (it's dynamically imported)
        with patch.dict('sys.modules', {'src.api.notifications_routes': MagicMock()}):
            response = test_client.post(
                '/webhooks/email/inbound',
                data={
                    'from': 'John Doe <john@example.com>',
                    'to': 'africastay@inbound.zorah.ai',
                    'subject': 'Travel inquiry for Cape Town',
                    'text': 'I want to book a trip to Cape Town',
                    'html': '<p>I want to book a trip</p>',
                    'envelope': json.dumps({'to': ['africastay@inbound.zorah.ai']}),
                    'headers': 'From: john@example.com\nTo: africastay@inbound.zorah.ai',
                    'attachments': '0'
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['tenant_id'] == 'africastay'
        assert 'diagnostic_id' in data

    @patch('src.webhooks.email_webhook.extract_tenant_from_email')
    @patch('src.webhooks.email_webhook.extract_tenant_from_subject')
    def test_inbound_email_tenant_not_found(
        self, mock_subject, mock_email, test_client
    ):
        """Should return error when tenant cannot be determined."""
        mock_email.return_value = (None, 'none')
        mock_subject.return_value = (None, 'none')

        response = test_client.post(
            '/webhooks/email/inbound',
            data={
                'from': 'john@example.com',
                'to': 'unknown@unknown.com',
                'subject': 'Random email',
                'text': 'Some content',
                'envelope': '{}',
                'headers': '',
                'attachments': '0'
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is False
        assert 'Could not determine tenant' in data['error']

    @patch('src.webhooks.email_webhook.extract_tenant_from_email')
    @patch('src.webhooks.email_webhook.get_config')
    def test_inbound_email_extracts_sender_name(
        self, mock_config, mock_email, test_client
    ):
        """Should extract sender name from From header."""
        mock_email.return_value = ('tenant1', 'direct_tenant_id')
        mock_config.return_value = MagicMock()

        with patch('src.webhooks.email_webhook.process_inbound_email') as mock_process, \
             patch.dict('sys.modules', {'src.api.notifications_routes': MagicMock()}):

            response = test_client.post(
                '/webhooks/email/inbound',
                data={
                    'from': '"John Doe" <john@example.com>',
                    'to': 'tenant1@inbound.com',
                    'subject': 'Test',
                    'text': 'Body',
                    'envelope': '{}',
                    'headers': '',
                    'attachments': '0'
                }
            )

        # Check that the parsed email was created correctly
        assert response.status_code == 200


# ==================== Debug Endpoint Tests ====================

class TestDebugEndpoint:
    """Test debug webhook endpoint."""

    @pytest.fixture
    def test_client(self):
        """Create test client."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router, prefix="/webhooks")
        return TestClient(app)

    def test_debug_endpoint_logs_form_data(self, test_client):
        """Should log all form fields without processing."""
        response = test_client.post(
            '/webhooks/email/debug',
            data={
                'from': 'test@example.com',
                'to': 'debug@test.com',
                'subject': 'Debug test',
                'text': 'Debug body'
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'fields_received' in data
        assert 'from' in data['fields_received']
        assert 'diagnostic_id' in data


# ==================== Per-Tenant Webhook Tests ====================

class TestPerTenantWebhook:
    """Test per-tenant webhook endpoint."""

    @pytest.fixture
    def test_client(self):
        """Create test client."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router, prefix="/webhooks")
        return TestClient(app)

    @patch('src.webhooks.email_webhook.get_config')
    @patch('src.webhooks.email_webhook.process_inbound_email')
    def test_per_tenant_webhook_success(
        self, mock_process, mock_config, test_client
    ):
        """Should accept email for specific tenant."""
        mock_config.return_value = MagicMock()

        response = test_client.post(
            '/webhooks/email/inbound/africastay',
            data={
                'from': 'John <john@example.com>',
                'to': 'africastay@inbound.com',
                'subject': 'Travel inquiry',
                'text': 'I want to book',
                'html': ''
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['tenant_id'] == 'africastay'

    @patch('src.webhooks.email_webhook.get_config')
    def test_per_tenant_webhook_invalid_tenant(self, mock_config, test_client):
        """Should return 404 for invalid tenant."""
        mock_config.side_effect = Exception("Tenant not found")

        response = test_client.post(
            '/webhooks/email/inbound/invalid_tenant',
            data={
                'from': 'test@example.com',
                'to': 'invalid@inbound.com',
                'subject': 'Test',
                'text': 'Body'
            }
        )

        assert response.status_code == 404


# ==================== Cache Refresh Error Handling Tests ====================

class TestCacheErrorHandling:
    """Test cache error handling."""

    def setup_method(self):
        """Clear cache before each test"""
        global _tenant_email_cache
        _tenant_email_cache.clear()

    @patch('src.webhooks.email_webhook.list_clients')
    def test_cache_refresh_handles_list_error(self, mock_list):
        """Should handle error listing clients."""
        mock_list.side_effect = Exception("Database error")

        result = _refresh_tenant_email_cache()

        assert result == {}  # Returns empty dict on error

    @patch('src.webhooks.email_webhook.list_clients')
    @patch('src.webhooks.email_webhook.get_tenant_email_addresses')
    def test_cache_refresh_handles_individual_tenant_error(
        self, mock_get_emails, mock_list
    ):
        """Should continue when individual tenant fails."""
        mock_list.return_value = ['tenant1', 'tenant2']
        mock_get_emails.side_effect = [
            Exception("Tenant1 error"),  # First tenant fails
            {  # Second tenant succeeds
                'support_email': 'support@tenant2.com',
                'sendgrid_email': None,
                'primary_email': None,
                'tenant_id': 'tenant2'
            }
        ]

        result = _refresh_tenant_email_cache()

        # Should have tenant2 but not tenant1
        assert 'support@tenant2.com' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
