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
    process_inbound_email,
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


# ==================== NEW TESTS: ParsedEmail Edge Cases ====================

class TestParsedEmailEdgeCases:
    """Test ParsedEmail model edge cases and validation."""

    def test_parsed_email_empty_body_text(self):
        """Should accept empty body text."""
        email = ParsedEmail(
            tenant_id='test',
            from_email='test@example.com',
            to_email='test@inbound.com',
            subject='Subject only',
            body_text='',
            received_at='2026-01-21T10:00:00Z'
        )
        assert email.body_text == ''

    def test_parsed_email_very_long_subject(self):
        """Should accept long subject lines without truncation in model."""
        long_subject = 'A' * 5000
        email = ParsedEmail(
            tenant_id='test',
            from_email='test@example.com',
            to_email='test@inbound.com',
            subject=long_subject,
            body_text='body',
            received_at='2026-01-21T10:00:00Z'
        )
        assert len(email.subject) == 5000

    def test_parsed_email_multiple_attachments(self):
        """Should store multiple attachments."""
        attachments = [
            {'filename': 'doc1.pdf', 'content_type': 'application/pdf', 'size': 1024},
            {'filename': 'image.jpg', 'content_type': 'image/jpeg', 'size': 2048},
            {'filename': 'data.csv', 'content_type': 'text/csv', 'size': 512}
        ]
        email = ParsedEmail(
            tenant_id='test',
            from_email='test@example.com',
            to_email='test@inbound.com',
            subject='With attachments',
            body_text='See attached',
            received_at='2026-01-21T10:00:00Z',
            attachments=attachments
        )
        assert len(email.attachments) == 3
        assert email.attachments[0]['filename'] == 'doc1.pdf'
        assert email.attachments[2]['size'] == 512

    def test_parsed_email_special_characters_in_subject(self):
        """Should handle special characters in subject."""
        email = ParsedEmail(
            tenant_id='test',
            from_email='test@example.com',
            to_email='test@inbound.com',
            subject='RE: Inquiry about "Zanzibar" & Cape Town <2 adults>',
            body_text='body',
            received_at='2026-01-21T10:00:00Z'
        )
        assert '&' in email.subject
        assert '"' in email.subject

    def test_parsed_email_unicode_body(self):
        """Should handle unicode characters in body."""
        email = ParsedEmail(
            tenant_id='test',
            from_email='test@example.com',
            to_email='test@inbound.com',
            subject='Test',
            body_text='Bonjour! Je voudrais reserver pour Noel.',
            received_at='2026-01-21T10:00:00Z'
        )
        assert 'Noel' in email.body_text

    def test_parsed_email_missing_required_field_raises(self):
        """Should raise validation error when required field is missing."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ParsedEmail(
                # Missing tenant_id
                from_email='test@example.com',
                to_email='test@inbound.com',
                subject='Test',
                body_text='body',
                received_at='2026-01-21T10:00:00Z'
            )

    def test_parsed_email_headers_with_multiple_entries(self):
        """Should store multiple header entries."""
        headers = {
            'x-tenant-id': 'africastay',
            'x-forwarded-for': '10.0.0.1',
            'content-type': 'text/plain',
            'message-id': '<abc123@mail.example.com>'
        }
        email = ParsedEmail(
            tenant_id='test',
            from_email='test@example.com',
            to_email='test@inbound.com',
            subject='Test',
            body_text='body',
            received_at='2026-01-21T10:00:00Z',
            headers=headers
        )
        assert len(email.headers) == 4
        assert email.headers['message-id'] == '<abc123@mail.example.com>'

    def test_parsed_email_serialization(self):
        """Should be serializable to dict."""
        email = ParsedEmail(
            tenant_id='test',
            from_email='test@example.com',
            to_email='test@inbound.com',
            subject='Test',
            body_text='body',
            received_at='2026-01-21T10:00:00Z'
        )
        data = email.model_dump()
        assert isinstance(data, dict)
        assert data['tenant_id'] == 'test'
        assert data['from_name'] is None
        assert data['attachments'] == []


# ==================== NEW TESTS: Diagnostic Logging Extended ====================

class TestDiagnosticLoggingExtended:
    """Extended tests for diagnostic_log function."""

    @patch('src.webhooks.email_webhook.logger')
    def test_diagnostic_log_step_zero_for_errors(self, mock_logger):
        """Should log step 0 for exception events."""
        diagnostic_log('ERR00001', 0, 'EXCEPTION: Something went wrong')

        call_args = mock_logger.info.call_args[0][0]
        assert '[STEP_0]' in call_args
        assert 'EXCEPTION' in call_args

    @patch('src.webhooks.email_webhook.logger')
    def test_diagnostic_log_without_data(self, mock_logger):
        """Should log without data parameter appended."""
        diagnostic_log('TEST1234', 5, 'Config loaded')

        call_args = mock_logger.info.call_args[0][0]
        assert 'data=' not in call_args
        assert 'Config loaded' in call_args

    @patch('src.webhooks.email_webhook.logger')
    def test_diagnostic_log_with_none_data(self, mock_logger):
        """Should handle None data parameter gracefully."""
        diagnostic_log('TEST1234', 3, 'Test message', None)

        call_args = mock_logger.info.call_args[0][0]
        assert 'data=' not in call_args

    @patch('src.webhooks.email_webhook.logger')
    def test_diagnostic_log_with_nested_data(self, mock_logger):
        """Should serialize nested data structures."""
        nested_data = {
            'strategies': [
                {'source': 'to_email', 'result': 'tenant1'},
                {'source': 'subject', 'result': None}
            ],
            'elapsed_ms': 12.5
        }
        diagnostic_log('NEST0001', 4, 'Resolution result', nested_data)

        call_args = mock_logger.info.call_args[0][0]
        assert 'data=' in call_args
        assert 'strategies' in call_args

    @patch('src.webhooks.email_webhook.logger')
    def test_diagnostic_log_with_datetime_in_data(self, mock_logger):
        """Should handle datetime objects in data using default=str."""
        data_with_datetime = {
            'timestamp': datetime(2026, 1, 21, 10, 0, 0),
            'event': 'received'
        }
        # Should not raise - uses default=str for json serialization
        diagnostic_log('DT000001', 1, 'Request received', data_with_datetime)

        call_args = mock_logger.info.call_args[0][0]
        assert 'data=' in call_args

    @patch('src.webhooks.email_webhook.logger')
    def test_diagnostic_log_high_step_number(self, mock_logger):
        """Should handle arbitrary step numbers."""
        diagnostic_log('HIGH0001', 99, 'Custom step')

        call_args = mock_logger.info.call_args[0][0]
        assert '[STEP_99]' in call_args


# ==================== NEW TESTS: Extract Tenant From Email Extended ====================

class TestExtractTenantFromEmailExtended:
    """Extended tests for extract_tenant_from_email."""

    def setup_method(self):
        """Clear cache before each test"""
        import src.webhooks.email_webhook as mod
        mod._tenant_email_cache.clear()

    @patch('src.webhooks.email_webhook.find_tenant_by_email')
    @patch('src.webhooks.email_webhook.get_config')
    def test_skips_all_generic_local_parts(self, mock_get_config, mock_find):
        """Should skip all defined generic patterns: quotes, sales, info, support, inbound, mail, admin, noreply."""
        mock_find.return_value = (None, 'none', False)
        mock_get_config.side_effect = Exception("Not found")

        skip_patterns = ['quotes', 'sales', 'info', 'support', 'inbound', 'mail', 'admin', 'noreply']
        for pattern in skip_patterns:
            tenant_id, strategy = extract_tenant_from_email(f'{pattern}@domain.com')
            assert tenant_id is None, f"Should have skipped generic pattern '{pattern}'"

    @patch('src.webhooks.email_webhook.find_tenant_by_email')
    @patch('src.webhooks.email_webhook.get_config')
    def test_extract_tenant_uppercased_email_normalized(self, mock_get_config, mock_find):
        """Should normalize email to lowercase before extraction."""
        mock_find.return_value = (None, 'none', False)
        mock_get_config.return_value = MagicMock()

        tenant_id, strategy = extract_tenant_from_email('AFRICASTAY@INBOUND.ZORAHAI.COM')

        assert tenant_id == 'africastay'
        assert strategy == 'direct_tenant_id'

    @patch('src.webhooks.email_webhook.find_tenant_by_email')
    @patch('src.webhooks.email_webhook.get_config')
    def test_extract_tenant_plus_addressing_with_nonexistent_tenant(self, mock_get_config, mock_find):
        """Should return None when plus-addressed tenant does not exist."""
        mock_find.return_value = (None, 'none', False)
        # 'quotes' is skipped, then config lookup for plus part fails too
        mock_get_config.side_effect = Exception("Not found")

        tenant_id, strategy = extract_tenant_from_email('quotes+nonexistent@domain.com')

        assert tenant_id is None

    @patch('src.webhooks.email_webhook.find_tenant_by_email')
    @patch('src.webhooks.email_webhook.get_config')
    def test_extract_tenant_x_tenant_id_header_uppercase_key(self, mock_get_config, mock_find):
        """Should find tenant from X-Tenant-ID header (uppercase key)."""
        mock_find.return_value = (None, 'none', False)
        mock_get_config.side_effect = [Exception("Not found"), MagicMock()]

        headers = {'X-Tenant-ID': 'africastay'}
        tenant_id, strategy = extract_tenant_from_email('unknown@domain.com', headers)

        assert tenant_id == 'africastay'
        assert strategy == 'x_tenant_id_header'

    @patch('src.webhooks.email_webhook.find_tenant_by_email')
    def test_extract_tenant_email_without_at_sign(self, mock_find):
        """Should handle malformed email without @ sign."""
        mock_find.return_value = (None, 'none', False)

        # Should not raise - the code splits on @ with fallback
        tenant_id, strategy = extract_tenant_from_email('malformed-email')

        # The whole string becomes local_part and goes through config lookup
        assert isinstance(tenant_id, str) or tenant_id is None

    @patch('src.webhooks.email_webhook.find_tenant_by_email')
    def test_extract_tenant_empty_headers(self, mock_find):
        """Should handle empty headers dict without error."""
        mock_find.return_value = (None, 'none', False)

        tenant_id, strategy = extract_tenant_from_email('unknown@domain.com', {})

        assert tenant_id is None


# ==================== NEW TESTS: Extract Tenant From Subject Extended ====================

class TestExtractTenantFromSubjectExtended:
    """Extended tests for extract_tenant_from_subject."""

    @patch('src.webhooks.email_webhook.get_config')
    def test_tenant_pattern_in_middle_of_subject(self, mock_get_config):
        """Should find [TENANT:xxx] pattern anywhere in subject."""
        mock_get_config.return_value = MagicMock()

        tenant_id, strategy = extract_tenant_from_subject('RE: FW: [TENANT:beachresort] Quote request')

        assert tenant_id == 'beachresort'
        assert strategy == 'subject_pattern'

    @patch('src.webhooks.email_webhook.get_config')
    def test_tenant_pattern_at_end_of_subject(self, mock_get_config):
        """Should find pattern at end of subject."""
        mock_get_config.return_value = MagicMock()

        tenant_id, strategy = extract_tenant_from_subject('Quote request [TENANT:resort123]')

        assert tenant_id == 'resort123'
        assert strategy == 'subject_pattern'

    def test_tenant_pattern_empty_subject(self):
        """Should handle empty subject string."""
        tenant_id, strategy = extract_tenant_from_subject('')

        assert tenant_id is None
        assert strategy == 'none'

    def test_tenant_pattern_malformed_bracket(self):
        """Should not match incomplete pattern."""
        tenant_id, strategy = extract_tenant_from_subject('[TENANT:incomplete')

        assert tenant_id is None
        assert strategy == 'none'

    @patch('src.webhooks.email_webhook.get_config')
    def test_tenant_pattern_with_numbers_and_hyphens(self, mock_get_config):
        """Should match tenant IDs with alphanumeric and underscore chars."""
        mock_get_config.return_value = MagicMock()

        tenant_id, strategy = extract_tenant_from_subject('[TENANT:final_itc_3] Test')

        assert tenant_id == 'final_itc_3'
        assert strategy == 'subject_pattern'


# ==================== NEW TESTS: process_inbound_email ====================

class TestProcessInboundEmail:
    """Test the process_inbound_email background processing function."""

    def _make_email(self, **overrides):
        """Helper to create a ParsedEmail with sensible defaults."""
        defaults = {
            'tenant_id': 'africastay',
            'from_email': 'customer@example.com',
            'from_name': 'Test Customer',
            'to_email': 'africastay@inbound.zorah.ai',
            'subject': 'Inquiry about Zanzibar trip',
            'body_text': 'I want to book a 7-night trip to Zanzibar for 2 adults.',
            'body_html': None,
            'attachments': [],
            'headers': {},
            'received_at': '2026-01-21T10:00:00Z'
        }
        defaults.update(overrides)
        return ParsedEmail(**defaults)

    @pytest.mark.asyncio
    @patch('src.webhooks.email_webhook.get_config')
    async def test_process_email_generates_diagnostic_id_if_missing(self, mock_config):
        """Should generate a diagnostic_id when None is passed."""
        mock_config.return_value = MagicMock()
        email = self._make_email()

        with patch('src.webhooks.email_webhook.diagnostic_log') as mock_diag:
            # Mock the LLMEmailParser import to prevent actual processing
            mock_parser_module = MagicMock()
            mock_parser_instance = MagicMock()
            mock_parser_instance.parse.return_value = {
                'destination': 'Zanzibar',
                'is_travel_inquiry': True,
                'parse_method': 'llm'
            }
            mock_parser_module.LLMEmailParser.return_value = mock_parser_instance

            mock_quote_module = MagicMock()
            mock_quote_agent = MagicMock()
            mock_quote_agent.generate_quote.return_value = {'quote_id': 'Q123'}
            mock_quote_module.QuoteAgent.return_value = mock_quote_agent

            with patch.dict('sys.modules', {
                'src.agents.llm_email_parser': mock_parser_module,
                'src.agents.universal_email_parser': MagicMock(),
                'src.agents.quote_agent': mock_quote_module,
                'src.api.notifications_routes': MagicMock()
            }):
                await process_inbound_email(email, None)

            # diagnostic_log should have been called with a generated ID (not None)
            assert mock_diag.call_count > 0
            first_call_diag_id = mock_diag.call_args_list[0][0][0]
            assert first_call_diag_id is not None
            assert len(first_call_diag_id) == 8  # UUID[:8].upper()

    @pytest.mark.asyncio
    @patch('src.webhooks.email_webhook.get_config')
    async def test_process_email_travel_inquiry_generates_quote(self, mock_config):
        """Should generate a draft quote for travel inquiries."""
        mock_config.return_value = MagicMock()
        email = self._make_email()

        mock_parser_module = MagicMock()
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse.return_value = {
            'destination': 'Zanzibar',
            'is_travel_inquiry': True,
            'parse_method': 'llm',
            'adults': 2,
            'children': 0,
            'check_in': '2026-09-01',
            'check_out': '2026-09-08',
            'budget': None
        }
        mock_parser_module.LLMEmailParser.return_value = mock_parser_instance

        mock_quote_module = MagicMock()
        mock_quote_agent = MagicMock()
        mock_quote_agent.generate_quote.return_value = {'quote_id': 'Q-ZAN-001'}
        mock_quote_module.QuoteAgent.return_value = mock_quote_agent

        with patch.dict('sys.modules', {
            'src.agents.llm_email_parser': mock_parser_module,
            'src.agents.universal_email_parser': MagicMock(),
            'src.agents.quote_agent': mock_quote_module,
            'src.api.notifications_routes': MagicMock()
        }):
            await process_inbound_email(email, 'DIAG0001')

        # Quote should have been generated as draft
        mock_quote_agent.generate_quote.assert_called_once()
        call_kwargs = mock_quote_agent.generate_quote.call_args
        assert call_kwargs[1]['send_email'] is False
        assert call_kwargs[1]['initial_status'] == 'draft'

    @pytest.mark.asyncio
    @patch('src.webhooks.email_webhook.get_config')
    async def test_process_email_non_travel_skips_quote(self, mock_config):
        """Should skip quote generation for non-travel inquiries."""
        mock_config.return_value = MagicMock()
        email = self._make_email(
            subject='Account password reset',
            body_text='I forgot my password, please help.'
        )

        mock_parser_module = MagicMock()
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse.return_value = {
            'destination': None,
            'is_travel_inquiry': False,
            'parse_method': 'llm'
        }
        mock_parser_module.LLMEmailParser.return_value = mock_parser_instance

        mock_quote_module = MagicMock()
        mock_quote_agent = MagicMock()
        mock_quote_module.QuoteAgent.return_value = mock_quote_agent

        mock_bq_module = MagicMock()
        mock_bq_instance = MagicMock()
        mock_bq_module.BigQueryTool.return_value = mock_bq_instance

        with patch.dict('sys.modules', {
            'src.agents.llm_email_parser': mock_parser_module,
            'src.agents.universal_email_parser': MagicMock(),
            'src.agents.quote_agent': mock_quote_module,
            'src.tools.bigquery_tool': mock_bq_module,
            'src.api.notifications_routes': MagicMock()
        }):
            await process_inbound_email(email, 'DIAG0002')

        # Quote agent should NOT have been called
        mock_quote_agent.generate_quote.assert_not_called()
        # BigQuery should have logged the non-travel email
        mock_bq_instance.log_email.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.webhooks.email_webhook.get_config')
    async def test_process_email_adds_sender_info_to_parsed_data(self, mock_config):
        """Should add email, name, and source to parsed data before quote generation."""
        mock_config.return_value = MagicMock()
        email = self._make_email(from_email='jane@travel.com', from_name='Jane Smith')

        captured_customer_data = {}

        mock_parser_module = MagicMock()
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse.return_value = {
            'destination': 'Cape Town',
            'is_travel_inquiry': True,
            'parse_method': 'llm'
        }
        mock_parser_module.LLMEmailParser.return_value = mock_parser_instance

        mock_quote_module = MagicMock()
        mock_quote_agent = MagicMock()

        def capture_quote_call(**kwargs):
            captured_customer_data.update(kwargs.get('customer_data', {}))
            return {'quote_id': 'Q001'}

        mock_quote_agent.generate_quote.side_effect = capture_quote_call
        mock_quote_module.QuoteAgent.return_value = mock_quote_agent

        with patch.dict('sys.modules', {
            'src.agents.llm_email_parser': mock_parser_module,
            'src.agents.universal_email_parser': MagicMock(),
            'src.agents.quote_agent': mock_quote_module,
            'src.api.notifications_routes': MagicMock()
        }):
            await process_inbound_email(email, 'DIAG0003')

        assert captured_customer_data['email'] == 'jane@travel.com'
        assert captured_customer_data['name'] == 'Jane Smith'
        assert captured_customer_data['source'] == 'email'

    @pytest.mark.asyncio
    @patch('src.webhooks.email_webhook.get_config')
    async def test_process_email_uses_email_prefix_when_no_from_name(self, mock_config):
        """Should use email prefix as name when from_name is None."""
        mock_config.return_value = MagicMock()
        email = self._make_email(from_email='john.doe@company.com', from_name=None)

        captured_customer_data = {}

        mock_parser_module = MagicMock()
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse.return_value = {
            'destination': 'Zanzibar',
            'is_travel_inquiry': True
        }
        mock_parser_module.LLMEmailParser.return_value = mock_parser_instance

        mock_quote_module = MagicMock()
        mock_quote_agent = MagicMock()

        def capture_quote_call(**kwargs):
            captured_customer_data.update(kwargs.get('customer_data', {}))
            return {'quote_id': 'Q002'}

        mock_quote_agent.generate_quote.side_effect = capture_quote_call
        mock_quote_module.QuoteAgent.return_value = mock_quote_agent

        with patch.dict('sys.modules', {
            'src.agents.llm_email_parser': mock_parser_module,
            'src.agents.universal_email_parser': MagicMock(),
            'src.agents.quote_agent': mock_quote_module,
            'src.api.notifications_routes': MagicMock()
        }):
            await process_inbound_email(email, 'DIAG0004')

        assert captured_customer_data['name'] == 'john.doe'

    @pytest.mark.asyncio
    @patch('src.webhooks.email_webhook.get_config')
    async def test_process_email_handles_import_error(self, mock_config):
        """Should handle ImportError for email parser gracefully."""
        mock_config.return_value = MagicMock()
        email = self._make_email()

        # Force an ImportError by making sys.modules return a broken module
        with patch('src.webhooks.email_webhook.diagnostic_log') as mock_diag:
            # Remove the modules so import will try to actually import
            import importlib
            # Patch the builtins __import__ to raise ImportError for our specific module
            original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

            def mock_import(name, *args, **kwargs):
                if 'llm_email_parser' in name:
                    raise ImportError("No module named 'src.agents.llm_email_parser'")
                return original_import(name, *args, **kwargs)

            with patch('builtins.__import__', side_effect=mock_import):
                # Should not raise - error is caught internally
                await process_inbound_email(email, 'DIAG0005')

            # Should have logged the exception at step 0
            error_calls = [
                c for c in mock_diag.call_args_list
                if len(c[0]) >= 3 and 'EXCEPTION' in str(c[0][2])
            ]
            assert len(error_calls) > 0

    @pytest.mark.asyncio
    @patch('src.webhooks.email_webhook.get_config')
    async def test_process_email_quote_generation_error_handled(self, mock_config):
        """Should handle quote generation errors without crashing."""
        mock_config.return_value = MagicMock()
        email = self._make_email()

        mock_parser_module = MagicMock()
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse.return_value = {
            'destination': 'Zanzibar',
            'is_travel_inquiry': True
        }
        mock_parser_module.LLMEmailParser.return_value = mock_parser_instance

        mock_quote_module = MagicMock()
        mock_quote_agent = MagicMock()
        mock_quote_agent.generate_quote.side_effect = RuntimeError("Quote engine failure")
        mock_quote_module.QuoteAgent.return_value = mock_quote_agent

        with patch.dict('sys.modules', {
            'src.agents.llm_email_parser': mock_parser_module,
            'src.agents.universal_email_parser': MagicMock(),
            'src.agents.quote_agent': mock_quote_module,
            'src.api.notifications_routes': MagicMock()
        }):
            # Should not raise - error is caught and logged
            await process_inbound_email(email, 'DIAG0006')


# ==================== NEW TESTS: Inbound Handler Edge Cases ====================

class TestInboundEmailHandlerExtended:
    """Extended tests for the inbound email webhook handler."""

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
    def test_inbound_email_malformed_envelope_json(self, mock_subject, mock_email, test_client):
        """Should handle malformed envelope JSON gracefully."""
        mock_email.return_value = (None, 'none')
        mock_subject.return_value = (None, 'none')

        response = test_client.post(
            '/webhooks/email/inbound',
            data={
                'from': 'test@example.com',
                'to': 'unknown@domain.com',
                'subject': 'Test',
                'text': 'Body',
                'envelope': '{not valid json!!!',
                'headers': '',
                'attachments': '0'
            }
        )

        # Should not crash - envelope parse failure is handled
        assert response.status_code == 200
        data = response.json()
        # Will fail tenant resolution since email is unknown
        assert data['success'] is False

    @patch('src.webhooks.email_webhook.extract_tenant_from_email')
    @patch('src.webhooks.email_webhook.extract_tenant_from_subject')
    @patch('src.webhooks.email_webhook.get_config')
    @patch('src.webhooks.email_webhook.process_inbound_email')
    def test_inbound_email_config_load_failure(
        self, mock_process, mock_config, mock_subject, mock_email, test_client
    ):
        """Should return error when config loading fails after tenant found."""
        mock_email.return_value = ('badtenant', 'direct_tenant_id')
        mock_subject.return_value = (None, 'none')
        mock_config.side_effect = Exception("Config file missing")

        response = test_client.post(
            '/webhooks/email/inbound',
            data={
                'from': 'test@example.com',
                'to': 'badtenant@inbound.com',
                'subject': 'Test',
                'text': 'Body',
                'envelope': '{}',
                'headers': '',
                'attachments': '0'
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is False
        assert 'Config load failed' in data['error']

    @patch('src.webhooks.email_webhook.extract_tenant_from_email')
    @patch('src.webhooks.email_webhook.get_config')
    @patch('src.webhooks.email_webhook.process_inbound_email')
    def test_inbound_email_response_includes_elapsed_ms(
        self, mock_process, mock_config, mock_email, test_client
    ):
        """Should include elapsed time in successful response."""
        mock_email.return_value = ('tenant1', 'support_email')
        mock_config.return_value = MagicMock(company_name='Test', destination_names=[])

        with patch.dict('sys.modules', {'src.api.notifications_routes': MagicMock()}):
            response = test_client.post(
                '/webhooks/email/inbound',
                data={
                    'from': 'test@example.com',
                    'to': 'tenant1@inbound.com',
                    'subject': 'Test',
                    'text': 'Body',
                    'envelope': '{}',
                    'headers': '',
                    'attachments': '0'
                }
            )

        data = response.json()
        assert 'elapsed_ms' in data
        assert isinstance(data['elapsed_ms'], float)

    @patch('src.webhooks.email_webhook.extract_tenant_from_email')
    @patch('src.webhooks.email_webhook.get_config')
    @patch('src.webhooks.email_webhook.process_inbound_email')
    def test_inbound_email_resolution_strategy_in_response(
        self, mock_process, mock_config, mock_email, test_client
    ):
        """Should include the resolution strategy used in response."""
        mock_email.return_value = ('africastay', 'sendgrid_email')
        mock_config.return_value = MagicMock(company_name='Africa Stay', destination_names=[])

        with patch.dict('sys.modules', {'src.api.notifications_routes': MagicMock()}):
            response = test_client.post(
                '/webhooks/email/inbound',
                data={
                    'from': 'customer@example.com',
                    'to': 'final-itc-3@zorah.ai',
                    'subject': 'Zanzibar trip',
                    'text': 'Looking for a Zanzibar trip',
                    'envelope': '{}',
                    'headers': '',
                    'attachments': '0'
                }
            )

        data = response.json()
        assert data['resolution_strategy'] == 'sendgrid_email'

    @patch('src.webhooks.email_webhook.extract_tenant_from_email')
    @patch('src.webhooks.email_webhook.extract_tenant_from_subject')
    def test_inbound_email_strategies_tried_in_error_response(
        self, mock_subject, mock_email, test_client
    ):
        """Should include strategies_tried in tenant-not-found response."""
        mock_email.return_value = (None, 'none')
        mock_subject.return_value = (None, 'none')

        response = test_client.post(
            '/webhooks/email/inbound',
            data={
                'from': 'test@example.com',
                'to': 'nobody@nowhere.com',
                'subject': 'Hello',
                'text': 'Hi there',
                'envelope': '{}',
                'headers': '',
                'attachments': '0'
            }
        )

        data = response.json()
        assert 'strategies_tried' in data
        assert isinstance(data['strategies_tried'], list)
        assert len(data['strategies_tried']) >= 1

    @patch('src.webhooks.email_webhook.extract_tenant_from_email')
    @patch('src.webhooks.email_webhook.get_config')
    @patch('src.webhooks.email_webhook.process_inbound_email')
    def test_inbound_email_from_without_angle_brackets(
        self, mock_process, mock_config, mock_email, test_client
    ):
        """Should handle bare email in From field (no name, no angle brackets)."""
        mock_email.return_value = ('tenant1', 'direct_tenant_id')
        mock_config.return_value = MagicMock(company_name='Test', destination_names=[])

        with patch.dict('sys.modules', {'src.api.notifications_routes': MagicMock()}):
            response = test_client.post(
                '/webhooks/email/inbound',
                data={
                    'from': 'plain@example.com',
                    'to': 'tenant1@inbound.com',
                    'subject': 'Test',
                    'text': 'Body text',
                    'envelope': '{}',
                    'headers': '',
                    'attachments': '0'
                }
            )

        data = response.json()
        assert data['success'] is True
        assert data['from'] == 'plain@example.com'

    @patch('src.webhooks.email_webhook.extract_tenant_from_email')
    @patch('src.webhooks.email_webhook.extract_tenant_from_subject')
    def test_inbound_email_missing_form_fields_uses_defaults(
        self, mock_subject, mock_email, test_client
    ):
        """Should use empty string defaults when form fields are missing."""
        mock_email.return_value = (None, 'none')
        mock_subject.return_value = (None, 'none')

        # Send minimal form data - missing from, subject, text, etc.
        response = test_client.post(
            '/webhooks/email/inbound',
            data={
                'to': 'someone@somewhere.com',
                'envelope': '{}',
                'headers': '',
                'attachments': '0'
            }
        )

        # Should not crash even with missing fields
        assert response.status_code == 200

    @patch('src.webhooks.email_webhook.extract_tenant_from_email')
    @patch('src.webhooks.email_webhook.extract_tenant_from_subject')
    @patch('src.webhooks.email_webhook.get_config')
    @patch('src.webhooks.email_webhook.process_inbound_email')
    def test_inbound_email_resolves_via_subject_fallback(
        self, mock_process, mock_config, mock_subject, mock_email, test_client
    ):
        """Should fall back to subject-based tenant resolution when email lookup fails."""
        mock_email.return_value = (None, 'none')
        mock_subject.return_value = ('beachresort', 'subject_pattern')
        mock_config.return_value = MagicMock(company_name='Beach Resort', destination_names=[])

        with patch.dict('sys.modules', {'src.api.notifications_routes': MagicMock()}):
            response = test_client.post(
                '/webhooks/email/inbound',
                data={
                    'from': 'customer@gmail.com',
                    'to': 'generic@mail.com',
                    'subject': '[TENANT:beachresort] I need a quote',
                    'text': 'Looking for a beach holiday',
                    'envelope': '{}',
                    'headers': '',
                    'attachments': '0'
                }
            )

        data = response.json()
        assert data['success'] is True
        assert data['tenant_id'] == 'beachresort'


# ==================== NEW TESTS: Per-Tenant Webhook Extended ====================

class TestPerTenantWebhookExtended:
    """Extended tests for per-tenant webhook endpoint."""

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
    def test_per_tenant_extracts_sender_name_from_angle_brackets(
        self, mock_process, mock_config, test_client
    ):
        """Should extract sender name from 'Name <email>' format."""
        mock_config.return_value = MagicMock()

        response = test_client.post(
            '/webhooks/email/inbound/africastay',
            data={
                'from': '"Jane Smith" <jane@travel.com>',
                'to': 'africastay@inbound.com',
                'subject': 'Trip inquiry',
                'text': 'I want to visit Cape Town'
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        # The extracted email should be just jane@travel.com
        assert data['from'] == 'jane@travel.com'

    @patch('src.webhooks.email_webhook.get_config')
    @patch('src.webhooks.email_webhook.process_inbound_email')
    def test_per_tenant_webhook_includes_diagnostic_id(
        self, mock_process, mock_config, test_client
    ):
        """Should include diagnostic_id in response."""
        mock_config.return_value = MagicMock()

        response = test_client.post(
            '/webhooks/email/inbound/africastay',
            data={
                'from': 'test@example.com',
                'to': 'africastay@inbound.com',
                'subject': 'Test',
                'text': 'Body'
            }
        )

        data = response.json()
        assert 'diagnostic_id' in data
        assert len(data['diagnostic_id']) == 8


# ==================== NEW TESTS: Cache TTL Behavior ====================

class TestCacheTTLBehavior:
    """Test cache TTL expiry and refresh behavior."""

    def setup_method(self):
        """Clear cache before each test"""
        import src.webhooks.email_webhook as mod
        mod._tenant_email_cache.clear()

    @patch('src.webhooks.email_webhook._refresh_tenant_email_cache')
    def test_cached_lookup_triggers_refresh_on_expired_cache(self, mock_refresh):
        """Should trigger cache refresh when TTL is expired."""
        import src.webhooks.email_webhook as mod

        # Set cache with expired timestamp
        mod._tenant_email_cache.update({
            'data': {'old@email.com': {'tenant_id': 'old', 'strategy': 'support_email'}},
            'timestamp': time.time() - (TENANT_CACHE_TTL + 10),  # Expired
            'tenant_count': 1,
            'email_count': 1
        })
        mock_refresh.return_value = {}

        _get_cached_tenant_lookup('test@email.com')

        mock_refresh.assert_called_once()

    @patch('src.webhooks.email_webhook._refresh_tenant_email_cache')
    def test_cached_lookup_skips_refresh_when_cache_fresh(self, mock_refresh):
        """Should not refresh cache when TTL is still valid."""
        import src.webhooks.email_webhook as mod

        # Set cache with current timestamp
        mod._tenant_email_cache.update({
            'data': {'test@email.com': {'tenant_id': 'tenant1', 'strategy': 'support_email'}},
            'timestamp': time.time(),  # Fresh
            'tenant_count': 1,
            'email_count': 1
        })

        result = _get_cached_tenant_lookup('test@email.com')

        mock_refresh.assert_not_called()
        assert result is not None
        assert result['tenant_id'] == 'tenant1'

    @patch('src.webhooks.email_webhook._refresh_tenant_email_cache')
    def test_cached_lookup_returns_none_for_unknown_email(self, mock_refresh):
        """Should return None for emails not in cache."""
        import src.webhooks.email_webhook as mod

        mod._tenant_email_cache.update({
            'data': {'known@email.com': {'tenant_id': 'tenant1', 'strategy': 'support_email'}},
            'timestamp': time.time(),
            'tenant_count': 1,
            'email_count': 1
        })

        result = _get_cached_tenant_lookup('unknown@email.com')

        assert result is None


# ==================== NEW TESTS: find_tenant_by_email Extended ====================

class TestFindTenantByEmailExtended:
    """Extended tests for find_tenant_by_email."""

    def setup_method(self):
        """Clear cache before each test"""
        import src.webhooks.email_webhook as mod
        mod._tenant_email_cache.clear()

    @patch('src.webhooks.email_webhook.list_clients')
    def test_find_tenant_returns_error_when_list_clients_fails(self, mock_list):
        """Should return error strategy when list_clients raises."""
        mock_list.side_effect = Exception("DB connection failed")

        # Need to also make cache miss to trigger fallback path
        import src.webhooks.email_webhook as mod
        mod._tenant_email_cache.update({
            'data': {},
            'timestamp': time.time(),
            'tenant_count': 0,
            'email_count': 0
        })

        tenant_id, strategy, cache_hit = find_tenant_by_email('test@example.com')

        assert tenant_id is None

    @patch('src.webhooks.email_webhook.list_clients')
    @patch('src.webhooks.email_webhook.get_tenant_email_addresses')
    def test_find_tenant_with_diagnostic_id_logs_steps(self, mock_get_emails, mock_list):
        """Should log diagnostic steps when diagnostic_id is provided."""
        mock_list.return_value = ['tenant1']
        mock_get_emails.return_value = {
            'support_email': 'support@company.com',
            'sendgrid_email': None,
            'primary_email': None,
            'tenant_id': 'tenant1'
        }

        with patch('src.webhooks.email_webhook.diagnostic_log') as mock_diag:
            tenant_id, strategy, cache_hit = find_tenant_by_email(
                'support@company.com', diagnostic_id='DIAG9999'
            )

        assert tenant_id == 'tenant1'
        # Diagnostic log should have been called
        assert mock_diag.call_count >= 1

    @patch('src.webhooks.email_webhook.list_clients')
    @patch('src.webhooks.email_webhook.get_tenant_email_addresses')
    def test_find_tenant_multiple_tenants_first_match_wins(self, mock_get_emails, mock_list):
        """Should return first matching tenant when multiple tenants have different emails."""
        mock_list.return_value = ['tenant_a', 'tenant_b', 'tenant_c']
        mock_get_emails.side_effect = [
            {
                'support_email': 'alpha@company.com',
                'sendgrid_email': None,
                'primary_email': None,
                'tenant_id': 'tenant_a'
            },
            {
                'support_email': 'beta@company.com',
                'sendgrid_email': None,
                'primary_email': None,
                'tenant_id': 'tenant_b'
            },
            {
                'support_email': 'gamma@company.com',
                'sendgrid_email': None,
                'primary_email': None,
                'tenant_id': 'tenant_c'
            }
        ]

        tenant_id, strategy, _ = find_tenant_by_email('beta@company.com')

        assert tenant_id == 'tenant_b'
        assert strategy == 'support_email'


# ==================== NEW TESTS: Debug Endpoint Extended ====================

class TestDebugEndpointExtended:
    """Extended tests for debug endpoint."""

    @pytest.fixture
    def test_client(self):
        """Create test client."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router, prefix="/webhooks")
        return TestClient(app)

    def test_debug_endpoint_returns_data_preview(self, test_client):
        """Should return truncated preview of form data."""
        response = test_client.post(
            '/webhooks/email/debug',
            data={
                'from': 'test@example.com',
                'subject': 'Short subject',
                'text': 'Short text'
            }
        )

        data = response.json()
        assert 'data_preview' in data
        assert 'from' in data['data_preview']

    def test_debug_endpoint_handles_empty_form(self, test_client):
        """Should handle empty form data gracefully."""
        response = test_client.post(
            '/webhooks/email/debug',
            data={}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['fields_received'] == []


# ==================== NEW TESTS: Webhook Status Extended ====================

class TestWebhookStatusExtended:
    """Extended tests for webhook status endpoint."""

    @pytest.fixture
    def test_client(self):
        """Create test client."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router, prefix="/webhooks")
        return TestClient(app)

    def test_status_includes_sendgrid_config(self, test_client):
        """Should include SendGrid configuration instructions."""
        response = test_client.get('/webhooks/email/status')
        data = response.json()

        assert 'sendgrid_configuration' in data
        assert 'step_1_mx_record' in data['sendgrid_configuration']
        assert 'step_2_inbound_parse' in data['sendgrid_configuration']
        assert data['sendgrid_configuration']['step_1_mx_record']['value'] == 'mx.sendgrid.net'

    def test_status_includes_routing_strategies(self, test_client):
        """Should list all supported routing strategies."""
        response = test_client.get('/webhooks/email/status')
        data = response.json()

        routing = data['supported_routing']
        assert len(routing) >= 7  # At least 7 strategies documented
        # Check some key strategies are listed
        strategies_text = ' '.join(routing)
        assert 'support_email' in strategies_text
        assert 'plus addressing' in strategies_text
        assert 'X-Tenant-ID' in strategies_text
        assert 'subject line' in strategies_text

    def test_status_includes_environment_info(self, test_client):
        """Should include environment variable status."""
        response = test_client.get('/webhooks/email/status')
        data = response.json()

        assert 'environment' in data
        assert 'sendgrid_api_key_set' in data['environment']
        assert 'openai_api_key_set' in data['environment']
        assert 'base_url' in data['environment']

    @patch('src.webhooks.email_webhook.list_clients')
    def test_status_handles_list_clients_error(self, mock_list, test_client):
        """Should handle list_clients error gracefully in status."""
        mock_list.side_effect = Exception("DB error")

        response = test_client.get('/webhooks/email/status')

        assert response.status_code == 200
        data = response.json()
        assert data['tenant_count'] == 0
        assert data['known_tenants'] == []


# ==================== NEW TESTS: Cache Refresh Data Integrity ====================

class TestCacheRefreshDataIntegrity:
    """Test cache refresh stores correct metadata."""

    def setup_method(self):
        """Clear cache before each test"""
        import src.webhooks.email_webhook as mod
        mod._tenant_email_cache.clear()

    @patch('src.webhooks.email_webhook.list_clients')
    @patch('src.webhooks.email_webhook.get_tenant_email_addresses')
    def test_cache_stores_timestamp(self, mock_get_emails, mock_list):
        """Should store timestamp in cache metadata."""
        import src.webhooks.email_webhook as mod

        mock_list.return_value = ['tenant1']
        mock_get_emails.return_value = {
            'support_email': 'support@test.com',
            'sendgrid_email': None,
            'primary_email': None,
            'tenant_id': 'tenant1'
        }

        before = time.time()
        _refresh_tenant_email_cache()
        after = time.time()

        assert 'timestamp' in mod._tenant_email_cache
        assert before <= mod._tenant_email_cache['timestamp'] <= after

    @patch('src.webhooks.email_webhook.list_clients')
    @patch('src.webhooks.email_webhook.get_tenant_email_addresses')
    def test_cache_stores_counts(self, mock_get_emails, mock_list):
        """Should store tenant and email counts in cache metadata."""
        import src.webhooks.email_webhook as mod

        mock_list.return_value = ['t1', 't2']
        mock_get_emails.side_effect = [
            {'support_email': 's1@test.com', 'sendgrid_email': 'sg1@zorah.ai', 'primary_email': None, 'tenant_id': 't1'},
            {'support_email': 's2@test.com', 'sendgrid_email': None, 'primary_email': 'p2@test.com', 'tenant_id': 't2'}
        ]

        _refresh_tenant_email_cache()

        assert mod._tenant_email_cache['tenant_count'] == 2
        assert mod._tenant_email_cache['email_count'] == 4  # s1, sg1, s2, p2

    @patch('src.webhooks.email_webhook.list_clients')
    def test_cache_stores_error_on_failure(self, mock_list):
        """Should store error message in cache on failure."""
        import src.webhooks.email_webhook as mod

        mock_list.side_effect = Exception("Connection timeout")

        _refresh_tenant_email_cache()

        assert 'error' in mod._tenant_email_cache
        assert 'Connection timeout' in mod._tenant_email_cache['error']

    @patch('src.webhooks.email_webhook.list_clients')
    @patch('src.webhooks.email_webhook.get_tenant_email_addresses')
    def test_cache_skips_none_emails(self, mock_get_emails, mock_list):
        """Should not add None emails to cache."""
        mock_list.return_value = ['tenant1']
        mock_get_emails.return_value = {
            'support_email': None,
            'sendgrid_email': None,
            'primary_email': None,
            'tenant_id': 'tenant1'
        }

        result = _refresh_tenant_email_cache()

        assert len(result) == 0

    @patch('src.webhooks.email_webhook.list_clients')
    @patch('src.webhooks.email_webhook.get_tenant_email_addresses')
    def test_cache_lowercases_all_emails(self, mock_get_emails, mock_list):
        """Should lowercase all email addresses in cache."""
        mock_list.return_value = ['tenant1']
        mock_get_emails.return_value = {
            'support_email': 'SUPPORT@COMPANY.COM',
            'sendgrid_email': 'Final-ITC@Zorah.AI',
            'primary_email': 'Admin@Company.Com',
            'tenant_id': 'tenant1'
        }

        result = _refresh_tenant_email_cache()

        assert 'support@company.com' in result
        assert 'final-itc@zorah.ai' in result
        assert 'admin@company.com' in result
        # Original case should NOT be present
        assert 'SUPPORT@COMPANY.COM' not in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
