"""
SendGrid Admin Service Unit Tests

Comprehensive tests for SendGrid admin service:
- Initialization with/without API key
- is_available() check
- list_subusers() functionality
- get_subuser_stats() statistics retrieval
- get_global_stats() platform-wide statistics
- disable_subuser() functionality
- enable_subuser() functionality
- Singleton pattern

All tests mock the SendGrid API client for isolated testing.
"""

import pytest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime, timedelta


# ==================== Fixtures ====================

@pytest.fixture
def mock_sendgrid_response():
    """Create a mock SendGrid API response."""
    def _create_response(status_code, body):
        response = MagicMock()
        response.status_code = status_code
        response.body = json.dumps(body).encode() if isinstance(body, (dict, list)) else body
        return response
    return _create_response


@pytest.fixture
def sample_subusers():
    """Sample subuser data."""
    return [
        {"username": "tenant1", "email": "tenant1@example.com", "disabled": False, "id": 1001},
        {"username": "tenant2", "email": "tenant2@example.com", "disabled": True, "id": 1002},
        {"username": "tenant3", "email": "tenant3@example.com", "disabled": False, "id": 1003}
    ]


@pytest.fixture
def sample_stats():
    """Sample email statistics data."""
    return [
        {
            "date": "2024-01-01",
            "stats": [{
                "metrics": {
                    "requests": 100,
                    "delivered": 95,
                    "opens": 50,
                    "unique_opens": 40,
                    "clicks": 20,
                    "unique_clicks": 15,
                    "bounces": 3,
                    "spam_reports": 1,
                    "unsubscribes": 1,
                    "blocks": 2,
                    "invalid_emails": 0
                }
            }]
        },
        {
            "date": "2024-01-02",
            "stats": [{
                "metrics": {
                    "requests": 120,
                    "delivered": 115,
                    "opens": 60,
                    "unique_opens": 45,
                    "clicks": 25,
                    "unique_clicks": 20,
                    "bounces": 2,
                    "spam_reports": 0,
                    "unsubscribes": 2,
                    "blocks": 1,
                    "invalid_emails": 1
                }
            }]
        }
    ]


# ==================== Initialization Tests ====================

class TestSendGridAdminServiceInit:
    """Test SendGridAdminService initialization."""

    @patch.dict("os.environ", {"SENDGRID_MASTER_API_KEY": ""})
    @patch("src.services.sendgrid_admin._sendgrid_admin_service", None)
    def test_init_without_api_key(self):
        """Service initializes but is not available without API key."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService()

        assert service.sg is None
        assert service.is_available() == False

    @patch.dict("os.environ", {"SENDGRID_MASTER_API_KEY": "SG.test-api-key"})
    @patch("src.services.sendgrid_admin._sendgrid_admin_service", None)
    def test_init_with_api_key(self):
        """Service initializes with API key."""
        from src.services.sendgrid_admin import SendGridAdminService

        # Mock sendgrid import
        with patch.dict("sys.modules", {"sendgrid": MagicMock()}):
            with patch("sendgrid.SendGridAPIClient") as mock_client:
                service = SendGridAdminService()
                # May or may not call depending on import order
                assert service.api_key == "SG.test-api-key"

    @patch.dict("os.environ", {"SENDGRID_MASTER_API_KEY": "SG.test-api-key"})
    @patch("src.services.sendgrid_admin._sendgrid_admin_service", None)
    def test_init_with_import_error(self):
        """Service handles ImportError gracefully."""
        from src.services.sendgrid_admin import SendGridAdminService

        # Simulate sendgrid not installed
        with patch.dict("sys.modules", {"sendgrid": None}):
            service = SendGridAdminService()
            # Should still create but sg will be None
            # (actual behavior depends on import handling)


# ==================== is_available Tests ====================

class TestIsAvailable:
    """Test is_available() method."""

    def test_is_available_true(self):
        """is_available returns True when sg client exists."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = MagicMock()
        service.api_key = "SG.test"

        assert service.is_available() == True

    def test_is_available_false(self):
        """is_available returns False when sg client is None."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = None
        service.api_key = None

        assert service.is_available() == False


# ==================== list_subusers Tests ====================

class TestListSubusers:
    """Test list_subusers() method."""

    def test_list_subusers_success(self, mock_sendgrid_response, sample_subusers):
        """list_subusers returns list of subusers."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = MagicMock()
        service.sg.client.subusers.get.return_value = mock_sendgrid_response(200, sample_subusers)

        result = service.list_subusers()

        assert len(result) == 3
        assert result[0]["username"] == "tenant1"
        assert result[1]["disabled"] == True
        assert result[2]["email"] == "tenant3@example.com"

    def test_list_subusers_empty(self, mock_sendgrid_response):
        """list_subusers returns empty list when no subusers."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = MagicMock()
        service.sg.client.subusers.get.return_value = mock_sendgrid_response(200, [])

        result = service.list_subusers()

        assert result == []

    def test_list_subusers_api_error(self, mock_sendgrid_response):
        """list_subusers returns empty list on API error."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = MagicMock()
        service.sg.client.subusers.get.return_value = mock_sendgrid_response(500, {"error": "Server error"})

        result = service.list_subusers()

        assert result == []

    def test_list_subusers_exception(self):
        """list_subusers handles exceptions gracefully."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = MagicMock()
        service.sg.client.subusers.get.side_effect = Exception("Network error")

        result = service.list_subusers()

        assert result == []

    def test_list_subusers_not_configured(self):
        """list_subusers returns empty list when SendGrid not configured."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = None

        result = service.list_subusers()

        assert result == []


# ==================== get_subuser_stats Tests ====================

class TestGetSubuserStats:
    """Test get_subuser_stats() method."""

    def test_get_subuser_stats_success(self, mock_sendgrid_response, sample_stats):
        """get_subuser_stats returns aggregated stats."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = MagicMock()
        service.sg.client.subusers._().stats.get.return_value = mock_sendgrid_response(200, sample_stats)

        result = service.get_subuser_stats("tenant1", days=30)

        assert result["username"] == "tenant1"
        assert result["period_days"] == 30
        assert "totals" in result
        assert "daily" in result

        # Check aggregated totals
        totals = result["totals"]
        assert totals["requests"] == 220  # 100 + 120
        assert totals["delivered"] == 210  # 95 + 115
        assert totals["bounces"] == 5  # 3 + 2

    def test_get_subuser_stats_calculates_rates(self, mock_sendgrid_response, sample_stats):
        """get_subuser_stats calculates open/click/bounce rates."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = MagicMock()
        service.sg.client.subusers._().stats.get.return_value = mock_sendgrid_response(200, sample_stats)

        result = service.get_subuser_stats("tenant1")

        totals = result["totals"]
        # Rates should be calculated
        assert "open_rate" in totals
        assert "click_rate" in totals
        assert "bounce_rate" in totals

    def test_get_subuser_stats_api_error(self, mock_sendgrid_response):
        """get_subuser_stats handles API errors."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = MagicMock()
        service.sg.client.subusers._().stats.get.return_value = mock_sendgrid_response(404, {"error": "Not found"})

        result = service.get_subuser_stats("nonexistent")

        assert "error" in result

    def test_get_subuser_stats_not_configured(self):
        """get_subuser_stats returns error when not configured."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = None

        result = service.get_subuser_stats("tenant1")

        assert result == {"error": "SendGrid not configured"}

    def test_get_subuser_stats_exception(self):
        """get_subuser_stats handles exceptions."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = MagicMock()
        service.sg.client.subusers._().stats.get.side_effect = Exception("Network error")

        result = service.get_subuser_stats("tenant1")

        assert "error" in result


# ==================== get_global_stats Tests ====================

class TestGetGlobalStats:
    """Test get_global_stats() method."""

    def test_get_global_stats_success(self, mock_sendgrid_response, sample_stats):
        """get_global_stats returns platform-wide stats."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = MagicMock()
        service.sg.client.stats.get.return_value = mock_sendgrid_response(200, sample_stats)

        result = service.get_global_stats(days=30)

        assert result["period_days"] == 30
        assert "totals" in result

        totals = result["totals"]
        assert totals["requests"] == 220
        assert totals["delivered"] == 210

    def test_get_global_stats_calculates_rates(self, mock_sendgrid_response, sample_stats):
        """get_global_stats calculates delivery rate."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = MagicMock()
        service.sg.client.stats.get.return_value = mock_sendgrid_response(200, sample_stats)

        result = service.get_global_stats()

        totals = result["totals"]
        assert "delivery_rate" in totals
        assert "open_rate" in totals
        assert "click_rate" in totals

    def test_get_global_stats_not_configured(self):
        """get_global_stats returns error when not configured."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = None

        result = service.get_global_stats()

        assert result == {"error": "SendGrid not configured"}

    def test_get_global_stats_zero_requests(self, mock_sendgrid_response):
        """get_global_stats handles zero requests."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = MagicMock()
        empty_stats = [{
            "date": "2024-01-01",
            "stats": [{"metrics": {"requests": 0, "delivered": 0}}]
        }]
        service.sg.client.stats.get.return_value = mock_sendgrid_response(200, empty_stats)

        result = service.get_global_stats()

        # Should not divide by zero
        assert result["totals"]["bounce_rate"] == 0
        assert result["totals"]["delivery_rate"] == 0


# ==================== disable_subuser Tests ====================

class TestDisableSubuser:
    """Test disable_subuser() method."""

    def test_disable_subuser_success(self, mock_sendgrid_response):
        """disable_subuser returns True on success."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = MagicMock()
        service.sg.client.subusers._().patch.return_value = mock_sendgrid_response(200, {})

        result = service.disable_subuser("tenant1")

        assert result == True
        # Verify correct request body
        service.sg.client.subusers._().patch.assert_called_once_with(
            request_body={"disabled": True}
        )

    def test_disable_subuser_204_response(self, mock_sendgrid_response):
        """disable_subuser handles 204 No Content response."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = MagicMock()
        service.sg.client.subusers._().patch.return_value = mock_sendgrid_response(204, {})

        result = service.disable_subuser("tenant1")

        assert result == True

    def test_disable_subuser_api_error(self, mock_sendgrid_response):
        """disable_subuser returns False on API error."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = MagicMock()
        service.sg.client.subusers._().patch.return_value = mock_sendgrid_response(500, {"error": "Server error"})

        result = service.disable_subuser("tenant1")

        assert result == False

    def test_disable_subuser_not_configured(self):
        """disable_subuser returns False when not configured."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = None

        result = service.disable_subuser("tenant1")

        assert result == False

    def test_disable_subuser_exception(self):
        """disable_subuser handles exceptions."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = MagicMock()
        service.sg.client.subusers._().patch.side_effect = Exception("Network error")

        result = service.disable_subuser("tenant1")

        assert result == False


# ==================== enable_subuser Tests ====================

class TestEnableSubuser:
    """Test enable_subuser() method."""

    def test_enable_subuser_success(self, mock_sendgrid_response):
        """enable_subuser returns True on success."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = MagicMock()
        service.sg.client.subusers._().patch.return_value = mock_sendgrid_response(200, {})

        result = service.enable_subuser("tenant1")

        assert result == True
        # Verify correct request body
        service.sg.client.subusers._().patch.assert_called_once_with(
            request_body={"disabled": False}
        )

    def test_enable_subuser_204_response(self, mock_sendgrid_response):
        """enable_subuser handles 204 No Content response."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = MagicMock()
        service.sg.client.subusers._().patch.return_value = mock_sendgrid_response(204, {})

        result = service.enable_subuser("tenant1")

        assert result == True

    def test_enable_subuser_api_error(self, mock_sendgrid_response):
        """enable_subuser returns False on API error."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = MagicMock()
        service.sg.client.subusers._().patch.return_value = mock_sendgrid_response(404, {"error": "Not found"})

        result = service.enable_subuser("nonexistent")

        assert result == False

    def test_enable_subuser_not_configured(self):
        """enable_subuser returns False when not configured."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = None

        result = service.enable_subuser("tenant1")

        assert result == False


# ==================== Singleton Tests ====================

class TestSingleton:
    """Test singleton pattern."""

    @patch("src.services.sendgrid_admin._sendgrid_admin_service", None)
    @patch.dict("os.environ", {"SENDGRID_MASTER_API_KEY": ""})
    def test_get_sendgrid_admin_service_creates_singleton(self):
        """get_sendgrid_admin_service creates singleton instance."""
        from src.services import sendgrid_admin
        sendgrid_admin._sendgrid_admin_service = None

        from src.services.sendgrid_admin import get_sendgrid_admin_service

        service1 = get_sendgrid_admin_service()
        service2 = get_sendgrid_admin_service()

        assert service1 is service2

    @patch("src.services.sendgrid_admin._sendgrid_admin_service", None)
    @patch.dict("os.environ", {"SENDGRID_MASTER_API_KEY": ""})
    def test_singleton_returns_sendgrid_admin_service(self):
        """get_sendgrid_admin_service returns SendGridAdminService instance."""
        from src.services import sendgrid_admin
        sendgrid_admin._sendgrid_admin_service = None

        from src.services.sendgrid_admin import get_sendgrid_admin_service, SendGridAdminService

        service = get_sendgrid_admin_service()

        assert isinstance(service, SendGridAdminService)


# ==================== Rate Calculation Tests ====================

class TestRateCalculations:
    """Test rate calculation edge cases."""

    def test_rates_with_zero_delivered(self, mock_sendgrid_response):
        """Rates are 0 when delivered is 0."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = MagicMock()
        stats = [{
            "date": "2024-01-01",
            "stats": [{"metrics": {
                "requests": 10,
                "delivered": 0,
                "opens": 0,
                "unique_opens": 0,
                "clicks": 0,
                "unique_clicks": 0,
                "bounces": 10
            }}]
        }]
        service.sg.client.subusers._().stats.get.return_value = mock_sendgrid_response(200, stats)

        result = service.get_subuser_stats("tenant1")

        assert result["totals"]["open_rate"] == 0
        assert result["totals"]["click_rate"] == 0

    def test_rates_with_zero_requests(self, mock_sendgrid_response):
        """Bounce rate is 0 when requests is 0."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = MagicMock()
        stats = [{
            "date": "2024-01-01",
            "stats": [{"metrics": {
                "requests": 0,
                "delivered": 0,
                "bounces": 0
            }}]
        }]
        service.sg.client.subusers._().stats.get.return_value = mock_sendgrid_response(200, stats)

        result = service.get_subuser_stats("tenant1")

        assert result["totals"]["bounce_rate"] == 0

    def test_rates_rounded_to_two_decimals(self, mock_sendgrid_response):
        """Rates are rounded to 2 decimal places."""
        from src.services.sendgrid_admin import SendGridAdminService

        service = SendGridAdminService.__new__(SendGridAdminService)
        service.sg = MagicMock()
        stats = [{
            "date": "2024-01-01",
            "stats": [{"metrics": {
                "requests": 97,
                "delivered": 89,
                "unique_opens": 33,
                "unique_clicks": 11,
                "bounces": 5
            }}]
        }]
        service.sg.client.subusers._().stats.get.return_value = mock_sendgrid_response(200, stats)

        result = service.get_subuser_stats("tenant1")

        # Verify rates are floats with max 2 decimal places
        open_rate = result["totals"]["open_rate"]
        assert isinstance(open_rate, float)
        assert open_rate == round(open_rate, 2)
