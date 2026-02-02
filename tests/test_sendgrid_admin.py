"""
Tests for SendGrid Admin Service

Comprehensive tests covering:
- Service initialization with/without API key
- Subuser listing
- Subuser statistics retrieval
- Global statistics retrieval
- Subuser enable/disable operations
- Singleton pattern
- Error handling

Uses mocked SendGrid API client to avoid external dependencies.
"""

import pytest
import json
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.fixtures.sendgrid_fixtures import (
    MockSendGridResponse,
    generate_subusers,
    generate_subuser_stats,
    generate_global_stats,
    SUBUSER_LIST_RESPONSE,
    SUBUSER_STATS_RESPONSE,
    GLOBAL_STATS_RESPONSE,
)


# ==================== Fixtures ====================

@pytest.fixture
def mock_sendgrid_module():
    """Create a mock sendgrid module."""
    mock_module = MagicMock()
    mock_client = MagicMock()
    mock_module.SendGridAPIClient.return_value = mock_client
    return mock_module, mock_client


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton before each test."""
    import src.services.sendgrid_admin as sgadmin
    sgadmin._sendgrid_admin_service = None
    yield
    sgadmin._sendgrid_admin_service = None


# ==================== Initialization Tests ====================

class TestSendGridAdminServiceInit:
    """Test SendGridAdminService initialization."""

    def test_init_with_api_key(self, mock_sendgrid_module):
        """Should initialize with SendGrid when API key is provided."""
        mock_module, mock_client = mock_sendgrid_module

        with patch.dict(os.environ, {'SENDGRID_MASTER_API_KEY': 'SG.test-key'}, clear=True):
            with patch.dict('sys.modules', {'sendgrid': mock_module}):
                # Import fresh to pick up the mocked module
                from src.services.sendgrid_admin import SendGridAdminService
                service = SendGridAdminService()

                assert service.is_available() is True
                assert service.api_key == 'SG.test-key'
                mock_module.SendGridAPIClient.assert_called_once_with(api_key='SG.test-key')

    def test_init_without_api_key(self):
        """Should not be available when no API key is set."""
        env_without_key = {k: v for k, v in os.environ.items() if k != 'SENDGRID_MASTER_API_KEY'}
        with patch.dict(os.environ, env_without_key, clear=True):
            from src.services.sendgrid_admin import SendGridAdminService
            service = SendGridAdminService()

            assert service.is_available() is False
            assert service.sg is None

    def test_init_handles_import_error(self):
        """Should handle import error gracefully when sendgrid not installed."""
        with patch.dict(os.environ, {'SENDGRID_API_KEY': 'SG.test-key'}):
            # Make sendgrid import fail
            with patch.dict('sys.modules', {'sendgrid': None}):
                from src.services.sendgrid_admin import SendGridAdminService

                # Need to trigger the import inside __init__
                with patch('builtins.__import__', side_effect=ImportError("No module")):
                    service = SendGridAdminService()
                    # Should gracefully handle and set sg to None
                    assert service.sg is None

    def test_init_handles_client_error(self, mock_sendgrid_module):
        """Should handle client initialization error gracefully."""
        mock_module, _ = mock_sendgrid_module
        mock_module.SendGridAPIClient.side_effect = Exception("Client init failed")

        with patch.dict(os.environ, {'SENDGRID_API_KEY': 'SG.test-key'}):
            with patch.dict('sys.modules', {'sendgrid': mock_module}):
                from src.services.sendgrid_admin import SendGridAdminService
                service = SendGridAdminService()

                assert service.is_available() is False
                assert service.sg is None


# ==================== List Subusers Tests ====================

class TestListSubusers:
    """Test list_subusers method."""

    def test_list_subusers_success(self, mock_sendgrid_module):
        """Should return list of subusers on success."""
        mock_module, mock_client = mock_sendgrid_module
        subusers = generate_subusers(3)
        mock_response = MockSendGridResponse(200, json.dumps(subusers))
        mock_client.client.subusers.get.return_value = mock_response

        with patch.dict(os.environ, {'SENDGRID_API_KEY': 'SG.test-key'}):
            with patch.dict('sys.modules', {'sendgrid': mock_module}):
                from src.services.sendgrid_admin import SendGridAdminService
                service = SendGridAdminService()
                result = service.list_subusers()

                assert len(result) == 3
                assert result[0]['username'] == 'tenant_0'
                assert 'email' in result[0]
                assert 'disabled' in result[0]

    def test_list_subusers_empty(self, mock_sendgrid_module):
        """Should return empty list when no subusers exist."""
        mock_module, mock_client = mock_sendgrid_module
        mock_response = MockSendGridResponse(200, '[]')
        mock_client.client.subusers.get.return_value = mock_response

        with patch.dict(os.environ, {'SENDGRID_API_KEY': 'SG.test-key'}):
            with patch.dict('sys.modules', {'sendgrid': mock_module}):
                from src.services.sendgrid_admin import SendGridAdminService
                service = SendGridAdminService()
                result = service.list_subusers()

                assert result == []

    def test_list_subusers_not_available(self):
        """Should return empty list when service not available."""
        with patch.dict(os.environ, {}, clear=True):
            from src.services.sendgrid_admin import SendGridAdminService
            service = SendGridAdminService()
            result = service.list_subusers()

            assert result == []

    def test_list_subusers_api_error(self, mock_sendgrid_module):
        """Should return empty list on API error."""
        mock_module, mock_client = mock_sendgrid_module
        mock_response = MockSendGridResponse(500, '{"error": "Internal error"}')
        mock_client.client.subusers.get.return_value = mock_response

        with patch.dict(os.environ, {'SENDGRID_API_KEY': 'SG.test-key'}):
            with patch.dict('sys.modules', {'sendgrid': mock_module}):
                from src.services.sendgrid_admin import SendGridAdminService
                service = SendGridAdminService()
                result = service.list_subusers()

                assert result == []

    def test_list_subusers_exception(self, mock_sendgrid_module):
        """Should return empty list on exception."""
        mock_module, mock_client = mock_sendgrid_module
        mock_client.client.subusers.get.side_effect = Exception("Network error")

        with patch.dict(os.environ, {'SENDGRID_API_KEY': 'SG.test-key'}):
            with patch.dict('sys.modules', {'sendgrid': mock_module}):
                from src.services.sendgrid_admin import SendGridAdminService
                service = SendGridAdminService()
                result = service.list_subusers()

                assert result == []


# ==================== Get Subuser Stats Tests ====================

class TestGetSubuserStats:
    """Test get_subuser_stats method."""

    def test_get_subuser_stats_success(self, mock_sendgrid_module):
        """Should return stats with totals calculated."""
        mock_module, mock_client = mock_sendgrid_module
        stats_data = SUBUSER_STATS_RESPONSE
        mock_response = MockSendGridResponse(200, json.dumps(stats_data))

        # Set up the fluent API mock
        mock_subuser = MagicMock()
        mock_stats = MagicMock()
        mock_stats.get.return_value = mock_response
        mock_subuser.stats = mock_stats
        mock_client.client.subusers._.return_value = mock_subuser

        with patch.dict(os.environ, {'SENDGRID_API_KEY': 'SG.test-key'}):
            with patch.dict('sys.modules', {'sendgrid': mock_module}):
                from src.services.sendgrid_admin import SendGridAdminService
                service = SendGridAdminService()
                result = service.get_subuser_stats('test_user', days=30)

                assert 'username' in result
                assert result['username'] == 'test_user'
                assert 'totals' in result
                assert 'daily' in result
                # Check totals are summed from both days
                assert result['totals']['requests'] == 350  # 150 + 200
                assert result['totals']['delivered'] == 340  # 145 + 195

    def test_get_subuser_stats_calculates_rates(self, mock_sendgrid_module):
        """Should calculate open_rate, click_rate, bounce_rate correctly."""
        mock_module, mock_client = mock_sendgrid_module
        stats_data = SUBUSER_STATS_RESPONSE
        mock_response = MockSendGridResponse(200, json.dumps(stats_data))

        mock_subuser = MagicMock()
        mock_stats = MagicMock()
        mock_stats.get.return_value = mock_response
        mock_subuser.stats = mock_stats
        mock_client.client.subusers._.return_value = mock_subuser

        with patch.dict(os.environ, {'SENDGRID_API_KEY': 'SG.test-key'}):
            with patch.dict('sys.modules', {'sendgrid': mock_module}):
                from src.services.sendgrid_admin import SendGridAdminService
                service = SendGridAdminService()
                result = service.get_subuser_stats('test_user')

                # Totals: unique_opens=105, delivered=340
                # open_rate = (105/340) * 100 = 30.88%
                assert 'open_rate' in result['totals']
                assert result['totals']['open_rate'] > 0

                # click_rate = (unique_clicks / delivered) * 100
                assert 'click_rate' in result['totals']

                # bounce_rate = (bounces / requests) * 100
                # bounces=8, requests=350
                assert 'bounce_rate' in result['totals']

    def test_get_subuser_stats_handles_zero_delivered(self, mock_sendgrid_module):
        """Should return rates=0 when delivered is zero to avoid division error."""
        mock_module, mock_client = mock_sendgrid_module
        stats_data = [{
            'date': '2026-01-01',
            'stats': [{
                'metrics': {
                    'requests': 10,
                    'delivered': 0,
                    'opens': 0,
                    'unique_opens': 0,
                    'clicks': 0,
                    'unique_clicks': 0,
                    'bounces': 10,
                    'spam_reports': 0,
                    'unsubscribes': 0,
                    'blocks': 0,
                    'invalid_emails': 0
                }
            }]
        }]
        mock_response = MockSendGridResponse(200, json.dumps(stats_data))

        mock_subuser = MagicMock()
        mock_stats = MagicMock()
        mock_stats.get.return_value = mock_response
        mock_subuser.stats = mock_stats
        mock_client.client.subusers._.return_value = mock_subuser

        with patch.dict(os.environ, {'SENDGRID_API_KEY': 'SG.test-key'}):
            with patch.dict('sys.modules', {'sendgrid': mock_module}):
                from src.services.sendgrid_admin import SendGridAdminService
                service = SendGridAdminService()
                result = service.get_subuser_stats('test_user')

                assert result['totals']['open_rate'] == 0
                assert result['totals']['click_rate'] == 0

    def test_get_subuser_stats_not_available(self):
        """Should return error dict when service unavailable."""
        with patch.dict(os.environ, {}, clear=True):
            from src.services.sendgrid_admin import SendGridAdminService
            service = SendGridAdminService()
            result = service.get_subuser_stats('test_user')

            assert 'error' in result
            assert 'not configured' in result['error'].lower()

    def test_get_subuser_stats_api_error(self, mock_sendgrid_module):
        """Should return error dict on API error."""
        mock_module, mock_client = mock_sendgrid_module
        mock_response = MockSendGridResponse(404, '{"error": "User not found"}')

        mock_subuser = MagicMock()
        mock_stats = MagicMock()
        mock_stats.get.return_value = mock_response
        mock_subuser.stats = mock_stats
        mock_client.client.subusers._.return_value = mock_subuser

        with patch.dict(os.environ, {'SENDGRID_API_KEY': 'SG.test-key'}):
            with patch.dict('sys.modules', {'sendgrid': mock_module}):
                from src.services.sendgrid_admin import SendGridAdminService
                service = SendGridAdminService()
                result = service.get_subuser_stats('unknown_user')

                assert 'error' in result

    def test_get_subuser_stats_aggregates_daily(self, mock_sendgrid_module):
        """Should correctly sum stats across multiple days."""
        mock_module, mock_client = mock_sendgrid_module

        # Generate 5 days of stats with known values
        stats_data = []
        for i in range(5):
            stats_data.append({
                'date': f'2026-01-0{i+1}',
                'stats': [{
                    'metrics': {
                        'requests': 100,
                        'delivered': 95,
                        'opens': 30,
                        'unique_opens': 25,
                        'clicks': 10,
                        'unique_clicks': 8,
                        'bounces': 5,
                        'spam_reports': 0,
                        'unsubscribes': 0,
                        'blocks': 0,
                        'invalid_emails': 0
                    }
                }]
            })

        mock_response = MockSendGridResponse(200, json.dumps(stats_data))

        mock_subuser = MagicMock()
        mock_stats = MagicMock()
        mock_stats.get.return_value = mock_response
        mock_subuser.stats = mock_stats
        mock_client.client.subusers._.return_value = mock_subuser

        with patch.dict(os.environ, {'SENDGRID_API_KEY': 'SG.test-key'}):
            with patch.dict('sys.modules', {'sendgrid': mock_module}):
                from src.services.sendgrid_admin import SendGridAdminService
                service = SendGridAdminService()
                result = service.get_subuser_stats('test_user')

                # 5 days * 100 requests = 500
                assert result['totals']['requests'] == 500
                # 5 days * 95 delivered = 475
                assert result['totals']['delivered'] == 475
                # 5 daily records
                assert len(result['daily']) == 5


# ==================== Get Global Stats Tests ====================

class TestGetGlobalStats:
    """Test get_global_stats method."""

    def test_get_global_stats_success(self, mock_sendgrid_module):
        """Should return aggregated global stats."""
        mock_module, mock_client = mock_sendgrid_module
        stats_data = GLOBAL_STATS_RESPONSE
        mock_response = MockSendGridResponse(200, json.dumps(stats_data))
        mock_client.client.stats.get.return_value = mock_response

        with patch.dict(os.environ, {'SENDGRID_API_KEY': 'SG.test-key'}):
            with patch.dict('sys.modules', {'sendgrid': mock_module}):
                from src.services.sendgrid_admin import SendGridAdminService
                service = SendGridAdminService()
                result = service.get_global_stats(days=30)

                assert 'totals' in result
                assert 'period_days' in result
                # 5000 + 5500 = 10500
                assert result['totals']['requests'] == 10500
                # 4850 + 5350 = 10200
                assert result['totals']['delivered'] == 10200

    def test_get_global_stats_calculates_delivery_rate(self, mock_sendgrid_module):
        """Should calculate delivery_rate correctly."""
        mock_module, mock_client = mock_sendgrid_module
        stats_data = GLOBAL_STATS_RESPONSE
        mock_response = MockSendGridResponse(200, json.dumps(stats_data))
        mock_client.client.stats.get.return_value = mock_response

        with patch.dict(os.environ, {'SENDGRID_API_KEY': 'SG.test-key'}):
            with patch.dict('sys.modules', {'sendgrid': mock_module}):
                from src.services.sendgrid_admin import SendGridAdminService
                service = SendGridAdminService()
                result = service.get_global_stats()

                # delivery_rate = (delivered/requests) * 100
                # 10200/10500 * 100 = 97.14%
                assert 'delivery_rate' in result['totals']
                assert result['totals']['delivery_rate'] > 90

    def test_get_global_stats_handles_zero_requests(self, mock_sendgrid_module):
        """Should return rates=0 when requests is zero."""
        mock_module, mock_client = mock_sendgrid_module
        stats_data = [{
            'date': '2026-01-01',
            'stats': [{
                'metrics': {
                    'requests': 0,
                    'delivered': 0,
                    'opens': 0,
                    'unique_opens': 0,
                    'clicks': 0,
                    'unique_clicks': 0,
                    'bounces': 0,
                    'spam_reports': 0,
                    'unsubscribes': 0,
                    'blocks': 0
                }
            }]
        }]
        mock_response = MockSendGridResponse(200, json.dumps(stats_data))
        mock_client.client.stats.get.return_value = mock_response

        with patch.dict(os.environ, {'SENDGRID_API_KEY': 'SG.test-key'}):
            with patch.dict('sys.modules', {'sendgrid': mock_module}):
                from src.services.sendgrid_admin import SendGridAdminService
                service = SendGridAdminService()
                result = service.get_global_stats()

                assert result['totals']['bounce_rate'] == 0
                assert result['totals']['delivery_rate'] == 0

    def test_get_global_stats_not_available(self):
        """Should return error dict when service unavailable."""
        with patch.dict(os.environ, {}, clear=True):
            from src.services.sendgrid_admin import SendGridAdminService
            service = SendGridAdminService()
            result = service.get_global_stats()

            assert 'error' in result


# ==================== Disable Subuser Tests ====================

class TestDisableSubuser:
    """Test disable_subuser method."""

    def test_disable_subuser_success(self, mock_sendgrid_module):
        """Should return True on successful disable."""
        mock_module, mock_client = mock_sendgrid_module
        mock_response = MockSendGridResponse(204, '')

        mock_subuser = MagicMock()
        mock_subuser.patch.return_value = mock_response
        mock_client.client.subusers._.return_value = mock_subuser

        with patch.dict(os.environ, {'SENDGRID_API_KEY': 'SG.test-key'}):
            with patch.dict('sys.modules', {'sendgrid': mock_module}):
                from src.services.sendgrid_admin import SendGridAdminService
                service = SendGridAdminService()
                result = service.disable_subuser('test_user')

                assert result is True
                mock_subuser.patch.assert_called_once_with(request_body={'disabled': True})

    def test_disable_subuser_success_200(self, mock_sendgrid_module):
        """Should also accept 200 status as success."""
        mock_module, mock_client = mock_sendgrid_module
        mock_response = MockSendGridResponse(200, '{}')

        mock_subuser = MagicMock()
        mock_subuser.patch.return_value = mock_response
        mock_client.client.subusers._.return_value = mock_subuser

        with patch.dict(os.environ, {'SENDGRID_API_KEY': 'SG.test-key'}):
            with patch.dict('sys.modules', {'sendgrid': mock_module}):
                from src.services.sendgrid_admin import SendGridAdminService
                service = SendGridAdminService()
                result = service.disable_subuser('test_user')

                assert result is True

    def test_disable_subuser_not_available(self):
        """Should return False when service unavailable."""
        with patch.dict(os.environ, {}, clear=True):
            from src.services.sendgrid_admin import SendGridAdminService
            service = SendGridAdminService()
            result = service.disable_subuser('test_user')

            assert result is False

    def test_disable_subuser_api_error(self, mock_sendgrid_module):
        """Should return False on API error."""
        mock_module, mock_client = mock_sendgrid_module
        mock_response = MockSendGridResponse(400, '{"error": "Bad request"}')

        mock_subuser = MagicMock()
        mock_subuser.patch.return_value = mock_response
        mock_client.client.subusers._.return_value = mock_subuser

        with patch.dict(os.environ, {'SENDGRID_API_KEY': 'SG.test-key'}):
            with patch.dict('sys.modules', {'sendgrid': mock_module}):
                from src.services.sendgrid_admin import SendGridAdminService
                service = SendGridAdminService()
                result = service.disable_subuser('test_user')

                assert result is False

    def test_disable_subuser_exception(self, mock_sendgrid_module):
        """Should return False on exception."""
        mock_module, mock_client = mock_sendgrid_module

        mock_subuser = MagicMock()
        mock_subuser.patch.side_effect = Exception("Network error")
        mock_client.client.subusers._.return_value = mock_subuser

        with patch.dict(os.environ, {'SENDGRID_API_KEY': 'SG.test-key'}):
            with patch.dict('sys.modules', {'sendgrid': mock_module}):
                from src.services.sendgrid_admin import SendGridAdminService
                service = SendGridAdminService()
                result = service.disable_subuser('test_user')

                assert result is False


# ==================== Enable Subuser Tests ====================

class TestEnableSubuser:
    """Test enable_subuser method."""

    def test_enable_subuser_success(self, mock_sendgrid_module):
        """Should return True on successful enable."""
        mock_module, mock_client = mock_sendgrid_module
        mock_response = MockSendGridResponse(204, '')

        mock_subuser = MagicMock()
        mock_subuser.patch.return_value = mock_response
        mock_client.client.subusers._.return_value = mock_subuser

        with patch.dict(os.environ, {'SENDGRID_API_KEY': 'SG.test-key'}):
            with patch.dict('sys.modules', {'sendgrid': mock_module}):
                from src.services.sendgrid_admin import SendGridAdminService
                service = SendGridAdminService()
                result = service.enable_subuser('test_user')

                assert result is True
                mock_subuser.patch.assert_called_once_with(request_body={'disabled': False})

    def test_enable_subuser_not_available(self):
        """Should return False when service unavailable."""
        with patch.dict(os.environ, {}, clear=True):
            from src.services.sendgrid_admin import SendGridAdminService
            service = SendGridAdminService()
            result = service.enable_subuser('test_user')

            assert result is False

    def test_enable_subuser_api_error(self, mock_sendgrid_module):
        """Should return False on API error."""
        mock_module, mock_client = mock_sendgrid_module
        mock_response = MockSendGridResponse(404, '{"error": "Not found"}')

        mock_subuser = MagicMock()
        mock_subuser.patch.return_value = mock_response
        mock_client.client.subusers._.return_value = mock_subuser

        with patch.dict(os.environ, {'SENDGRID_API_KEY': 'SG.test-key'}):
            with patch.dict('sys.modules', {'sendgrid': mock_module}):
                from src.services.sendgrid_admin import SendGridAdminService
                service = SendGridAdminService()
                result = service.enable_subuser('unknown_user')

                assert result is False


# ==================== Singleton Tests ====================

class TestSingleton:
    """Test singleton pattern."""

    def test_get_sendgrid_admin_service_returns_singleton(self, mock_sendgrid_module):
        """Should return same instance on multiple calls."""
        mock_module, mock_client = mock_sendgrid_module

        with patch.dict(os.environ, {'SENDGRID_API_KEY': 'SG.test-key'}):
            with patch.dict('sys.modules', {'sendgrid': mock_module}):
                from src.services.sendgrid_admin import get_sendgrid_admin_service

                service1 = get_sendgrid_admin_service()
                service2 = get_sendgrid_admin_service()

                assert service1 is service2

    def test_singleton_can_be_reset(self, mock_sendgrid_module):
        """Should allow resetting singleton for testing."""
        mock_module, mock_client = mock_sendgrid_module

        with patch.dict(os.environ, {'SENDGRID_API_KEY': 'SG.test-key'}):
            with patch.dict('sys.modules', {'sendgrid': mock_module}):
                import src.services.sendgrid_admin as sgadmin
                from src.services.sendgrid_admin import get_sendgrid_admin_service

                service1 = get_sendgrid_admin_service()

                # Reset singleton
                sgadmin._sendgrid_admin_service = None

                service2 = get_sendgrid_admin_service()

                assert service1 is not service2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
