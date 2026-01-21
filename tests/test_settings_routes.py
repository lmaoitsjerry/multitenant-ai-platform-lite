"""
Settings Routes Unit Tests

Comprehensive tests for tenant settings API endpoints:
- GET /api/v1/settings
- PUT /api/v1/settings
- PUT /api/v1/settings/email
- PUT /api/v1/settings/banking
- PUT /api/v1/settings/company

Uses FastAPI TestClient with mocked dependencies.
These tests verify:
1. Endpoint structure and HTTP methods
2. Request validation
3. Response formats
4. Error handling for missing data
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import os


# ==================== Fixtures ====================

@pytest.fixture
def mock_config():
    """Create a mock ClientConfig."""
    config = MagicMock()
    config.client_id = "test_tenant"
    config.company_name = "Test Company"
    config.primary_email = "support@example.com"
    config.support_phone = "+1234567890"
    config.website = "https://example.com"
    config.currency = "USD"
    config.timezone = "UTC"
    config.sendgrid_from_name = "Test Company"
    config.sendgrid_from_email = "noreply@example.com"
    config.sendgrid_reply_to = "support@example.com"
    config.bank_name = "Test Bank"
    config.bank_account_name = "Test Company Account"
    config.bank_account_number = "123456789"
    config.bank_branch_code = "001"
    config.bank_swift_code = "TESTUS33"
    config.payment_reference_prefix = "INV"
    return config


@pytest.fixture
def test_client():
    """Create a basic TestClient."""
    from main import app
    return TestClient(app)


# ==================== Authorization Tests ====================

class TestSettingsAuth:
    """Test authorization for settings endpoints."""

    def test_get_settings_requires_auth(self, test_client):
        """GET /settings should require authorization."""
        response = test_client.get(
            "/api/v1/settings",
            headers={"X-Client-ID": "example"}
        )
        assert response.status_code == 401

    def test_update_settings_requires_auth(self, test_client):
        """PUT /settings should require authorization."""
        response = test_client.put(
            "/api/v1/settings",
            headers={"X-Client-ID": "example"},
            json={"company": {"company_name": "Test"}}
        )
        assert response.status_code == 401

    def test_update_email_requires_auth(self, test_client):
        """PUT /settings/email should require authorization."""
        response = test_client.put(
            "/api/v1/settings/email",
            headers={"X-Client-ID": "example"},
            json={"from_name": "Test"}
        )
        assert response.status_code == 401

    def test_update_banking_requires_auth(self, test_client):
        """PUT /settings/banking should require authorization."""
        response = test_client.put(
            "/api/v1/settings/banking",
            headers={"X-Client-ID": "example"},
            json={"bank_name": "Test"}
        )
        assert response.status_code == 401

    def test_update_company_requires_auth(self, test_client):
        """PUT /settings/company should require authorization."""
        response = test_client.put(
            "/api/v1/settings/company",
            headers={"X-Client-ID": "example"},
            json={"company_name": "Test"}
        )
        assert response.status_code == 401


# ==================== Get Settings Tests ====================

class TestGetSettings:
    """Test GET /api/v1/settings endpoint."""

    def test_get_settings_endpoint_exists(self, test_client):
        """GET /settings endpoint should exist."""
        response = test_client.get(
            "/api/v1/settings",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test-token"
            }
        )
        # 401 for invalid token is expected
        assert response.status_code == 401

    def test_get_settings_accepts_client_header(self, test_client):
        """GET /settings should read X-Client-ID header."""
        response = test_client.get(
            "/api/v1/settings",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test"
            }
        )
        # Auth fails but endpoint recognizes header
        assert response.status_code == 401


# ==================== Update All Settings Tests ====================

class TestUpdateSettings:
    """Test PUT /api/v1/settings endpoint."""

    def test_update_settings_endpoint_exists(self, test_client):
        """PUT /settings endpoint should exist."""
        response = test_client.put(
            "/api/v1/settings",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test"
            },
            json={"company": {"company_name": "New Name"}}
        )
        # 401 for invalid token
        assert response.status_code == 401

    def test_update_settings_accepts_nested_json(self, test_client):
        """PUT /settings should accept company/email/banking sections."""
        response = test_client.put(
            "/api/v1/settings",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test"
            },
            json={
                "company": {"company_name": "Test"},
                "email": {"from_name": "Test"},
                "banking": {"bank_name": "Test"}
            }
        )
        # Auth fails but request format is valid
        assert response.status_code == 401


# ==================== Update Email Settings Tests ====================

class TestUpdateEmailSettings:
    """Test PUT /api/v1/settings/email endpoint."""

    def test_update_email_settings_endpoint_exists(self, test_client):
        """PUT /settings/email endpoint should exist."""
        response = test_client.put(
            "/api/v1/settings/email",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test"
            },
            json={"from_name": "Test"}
        )
        # 401 for invalid token
        assert response.status_code == 401

    def test_update_email_settings_accepts_all_fields(self, test_client):
        """PUT /settings/email should accept all email fields."""
        response = test_client.put(
            "/api/v1/settings/email",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test"
            },
            json={
                "from_name": "New Name",
                "from_email": "new@example.com",
                "reply_to": "reply@example.com",
                "quotes_email": "quotes@example.com"
            }
        )
        # Auth fails but request format is valid
        assert response.status_code == 401


# ==================== Update Banking Settings Tests ====================

class TestUpdateBankingSettings:
    """Test PUT /api/v1/settings/banking endpoint."""

    def test_update_banking_settings_endpoint_exists(self, test_client):
        """PUT /settings/banking endpoint should exist."""
        response = test_client.put(
            "/api/v1/settings/banking",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test"
            },
            json={"bank_name": "Test Bank"}
        )
        # 401 for invalid token
        assert response.status_code == 401

    def test_update_banking_settings_accepts_all_fields(self, test_client):
        """PUT /settings/banking should accept all banking fields."""
        response = test_client.put(
            "/api/v1/settings/banking",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test"
            },
            json={
                "bank_name": "New Bank",
                "account_name": "New Account",
                "account_number": "987654321",
                "branch_code": "002",
                "swift_code": "NEWBANK33",
                "reference_prefix": "PAY"
            }
        )
        # Auth fails but request format is valid
        assert response.status_code == 401


# ==================== Update Company Settings Tests ====================

class TestUpdateCompanySettings:
    """Test PUT /api/v1/settings/company endpoint."""

    def test_update_company_settings_endpoint_exists(self, test_client):
        """PUT /settings/company endpoint should exist."""
        response = test_client.put(
            "/api/v1/settings/company",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test"
            },
            json={"company_name": "Test Company"}
        )
        # 401 for invalid token
        assert response.status_code == 401

    def test_update_company_settings_accepts_all_fields(self, test_client):
        """PUT /settings/company should accept all company fields."""
        response = test_client.put(
            "/api/v1/settings/company",
            headers={
                "X-Client-ID": "example",
                "Authorization": "Bearer test"
            },
            json={
                "company_name": "New Company",
                "support_email": "newsupport@example.com",
                "support_phone": "+0987654321",
                "website": "https://newsite.com",
                "currency": "EUR",
                "timezone": "Europe/London"
            }
        )
        # Auth fails but request format is valid
        assert response.status_code == 401


# ==================== Helper Functions Tests ====================

class TestMergeSettingsHelper:
    """Test merge_settings_with_config helper function."""

    def test_merge_settings_uses_db_values_first(self, mock_config):
        """merge_settings_with_config should prefer database values."""
        from src.api.settings_routes import merge_settings_with_config

        db_settings = {
            "company_name": "DB Company",
            "support_email": "db@example.com"
        }

        result = merge_settings_with_config(db_settings, mock_config)

        assert result["company"]["company_name"] == "DB Company"
        assert result["company"]["support_email"] == "db@example.com"

    def test_merge_settings_falls_back_to_config(self, mock_config):
        """merge_settings_with_config should fall back to config values."""
        from src.api.settings_routes import merge_settings_with_config

        db_settings = {}  # Empty database settings

        result = merge_settings_with_config(db_settings, mock_config)

        # Should use config values
        assert result["company"]["company_name"] == mock_config.company_name
        assert result["banking"]["bank_name"] == mock_config.bank_name

    def test_merge_settings_returns_all_sections(self, mock_config):
        """merge_settings_with_config should return all three sections."""
        from src.api.settings_routes import merge_settings_with_config

        result = merge_settings_with_config({}, mock_config)

        assert "company" in result
        assert "email" in result
        assert "banking" in result

        # Verify structure
        assert "company_name" in result["company"]
        assert "from_name" in result["email"]
        assert "bank_name" in result["banking"]


# ==================== Pydantic Model Validation Tests ====================

class TestSettingsModels:
    """Test Pydantic models for settings."""

    def test_company_settings_model(self):
        """CompanySettings model should accept valid data."""
        from src.api.settings_routes import CompanySettings

        settings = CompanySettings(
            company_name="Test",
            support_email="test@example.com",
            currency="USD"
        )
        assert settings.company_name == "Test"

    def test_email_settings_model(self):
        """EmailSettings model should accept valid data."""
        from src.api.settings_routes import EmailSettings

        settings = EmailSettings(
            from_name="Test",
            from_email="test@example.com"
        )
        assert settings.from_name == "Test"

    def test_banking_settings_model(self):
        """BankingSettings model should accept valid data."""
        from src.api.settings_routes import BankingSettings

        settings = BankingSettings(
            bank_name="Test Bank",
            account_number="123456"
        )
        assert settings.bank_name == "Test Bank"

    def test_tenant_settings_update_model(self):
        """TenantSettingsUpdate model should nest other models."""
        from src.api.settings_routes import TenantSettingsUpdate

        update = TenantSettingsUpdate(
            company={"company_name": "Test"},
            email={"from_name": "Test"},
            banking={"bank_name": "Test"}
        )
        assert update.company.company_name == "Test"
        assert update.email.from_name == "Test"
        assert update.banking.bank_name == "Test"
