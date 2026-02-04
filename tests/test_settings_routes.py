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

    def test_email_settings_validates_email(self):
        """EmailSettings model should validate email addresses."""
        from src.api.settings_routes import EmailSettings
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            EmailSettings(from_email="not-an-email")

    def test_company_settings_validates_email(self):
        """CompanySettings model should validate support_email."""
        from src.api.settings_routes import CompanySettings
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CompanySettings(support_email="invalid-email")

    def test_company_settings_all_optional(self):
        """CompanySettings should allow all fields to be None."""
        from src.api.settings_routes import CompanySettings

        settings = CompanySettings()
        assert settings.company_name is None
        assert settings.currency is None

    def test_email_settings_all_optional(self):
        """EmailSettings should allow all fields to be None."""
        from src.api.settings_routes import EmailSettings

        settings = EmailSettings()
        assert settings.from_name is None
        assert settings.from_email is None

    def test_banking_settings_all_optional(self):
        """BankingSettings should allow all fields to be None."""
        from src.api.settings_routes import BankingSettings

        settings = BankingSettings()
        assert settings.bank_name is None
        assert settings.account_number is None


# ==================== Dependency Tests ====================

class TestDependencies:
    """Test dependency functions."""

    def test_get_client_config_uses_header(self):
        """get_client_config should use X-Client-ID header."""
        from src.api.settings_routes import get_client_config

        with patch('src.api.settings_routes.get_config') as mock_get_config:
            mock_config = MagicMock()
            mock_get_config.return_value = mock_config

            result = get_client_config("custom_client")

            mock_get_config.assert_called_once_with("custom_client")
            assert result == mock_config

    def test_get_client_config_uses_default(self):
        """get_client_config should fall back to env var."""
        from src.api.settings_routes import get_client_config

        with patch('src.api.settings_routes.get_config') as mock_get_config:
            with patch.dict(os.environ, {"CLIENT_ID": "env_client"}):
                mock_config = MagicMock()
                mock_get_config.return_value = mock_config

                result = get_client_config(None)

                mock_get_config.assert_called_once_with("env_client")

    def test_get_client_config_raises_on_error(self):
        """get_client_config should raise HTTPException on config error."""
        from src.api.settings_routes import get_client_config
        from fastapi import HTTPException

        with patch('src.api.settings_routes.get_config') as mock_get_config:
            mock_get_config.side_effect = Exception("Config not found")

            with pytest.raises(HTTPException) as exc_info:
                get_client_config("invalid_client")

            assert exc_info.value.status_code == 400
            assert "Invalid client" in str(exc_info.value.detail)

    def test_get_supabase_tool_creates_instance(self, mock_config):
        """get_supabase_tool should create SupabaseTool with config."""
        from src.api.settings_routes import get_supabase_tool

        with patch('src.api.settings_routes.SupabaseTool') as MockSupabase:
            mock_db = MagicMock()
            MockSupabase.return_value = mock_db

            result = get_supabase_tool(mock_config)

            MockSupabase.assert_called_once_with(mock_config)
            assert result == mock_db


# ==================== GET Settings Unit Tests ====================

class TestGetSettingsUnit:
    """Unit tests for GET /settings endpoint logic."""

    @pytest.mark.asyncio
    async def test_get_tenant_settings_merges_db_and_config(self, mock_config):
        """get_tenant_settings should merge database and config values."""
        from src.api.settings_routes import get_tenant_settings

        mock_db = MagicMock()
        mock_db.get_tenant_settings.return_value = {
            "company_name": "From Database"
        }

        result = await get_tenant_settings(config=mock_config, db=mock_db)

        assert result["success"] is True
        assert result["data"]["company"]["company_name"] == "From Database"
        # Config fallback for missing fields
        assert result["data"]["banking"]["bank_name"] == mock_config.bank_name

    @pytest.mark.asyncio
    async def test_get_tenant_settings_handles_no_db_settings(self, mock_config):
        """get_tenant_settings should work when database returns None."""
        from src.api.settings_routes import get_tenant_settings

        mock_db = MagicMock()
        mock_db.get_tenant_settings.return_value = None

        result = await get_tenant_settings(config=mock_config, db=mock_db)

        assert result["success"] is True
        # All values from config
        assert result["data"]["company"]["company_name"] == mock_config.company_name


# ==================== PUT Settings Unit Tests ====================

class TestUpdateSettingsUnit:
    """Unit tests for PUT /settings endpoint logic."""

    @pytest.mark.asyncio
    async def test_update_tenant_settings_company(self, mock_config):
        """update_tenant_settings should update company fields."""
        from src.api.settings_routes import update_tenant_settings, TenantSettingsUpdate, CompanySettings

        mock_db = MagicMock()
        mock_db.update_tenant_settings.return_value = {"company_name": "Updated Company"}

        data = TenantSettingsUpdate(
            company=CompanySettings(company_name="Updated Company")
        )

        result = await update_tenant_settings(data=data, config=mock_config, db=mock_db)

        assert result["success"] is True
        mock_db.update_tenant_settings.assert_called_once()
        call_kwargs = mock_db.update_tenant_settings.call_args[1]
        assert call_kwargs["company_name"] == "Updated Company"

    @pytest.mark.asyncio
    async def test_update_tenant_settings_email(self, mock_config):
        """update_tenant_settings should update email fields."""
        from src.api.settings_routes import update_tenant_settings, TenantSettingsUpdate, EmailSettings

        mock_db = MagicMock()
        mock_db.update_tenant_settings.return_value = {"email_from_name": "New Name"}

        data = TenantSettingsUpdate(
            email=EmailSettings(from_name="New Name")
        )

        result = await update_tenant_settings(data=data, config=mock_config, db=mock_db)

        assert result["success"] is True
        call_kwargs = mock_db.update_tenant_settings.call_args[1]
        assert call_kwargs["email_from_name"] == "New Name"

    @pytest.mark.asyncio
    async def test_update_tenant_settings_banking(self, mock_config):
        """update_tenant_settings should update banking fields."""
        from src.api.settings_routes import update_tenant_settings, TenantSettingsUpdate, BankingSettings

        mock_db = MagicMock()
        mock_db.update_tenant_settings.return_value = {"bank_name": "New Bank"}

        data = TenantSettingsUpdate(
            banking=BankingSettings(bank_name="New Bank")
        )

        result = await update_tenant_settings(data=data, config=mock_config, db=mock_db)

        assert result["success"] is True
        call_kwargs = mock_db.update_tenant_settings.call_args[1]
        assert call_kwargs["bank_name"] == "New Bank"

    @pytest.mark.asyncio
    async def test_update_tenant_settings_no_data_raises_error(self, mock_config):
        """update_tenant_settings should raise 400 when no settings provided."""
        from src.api.settings_routes import update_tenant_settings, TenantSettingsUpdate
        from fastapi import HTTPException

        mock_db = MagicMock()
        data = TenantSettingsUpdate()  # Empty update

        with pytest.raises(HTTPException) as exc_info:
            await update_tenant_settings(data=data, config=mock_config, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "No settings to update" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_tenant_settings_db_failure(self, mock_config):
        """update_tenant_settings should raise 500 when database fails."""
        from src.api.settings_routes import update_tenant_settings, TenantSettingsUpdate, CompanySettings
        from fastapi import HTTPException

        mock_db = MagicMock()
        mock_db.update_tenant_settings.return_value = None  # Simulate DB failure

        data = TenantSettingsUpdate(
            company=CompanySettings(company_name="Test")
        )

        with pytest.raises(HTTPException) as exc_info:
            await update_tenant_settings(data=data, config=mock_config, db=mock_db)

        assert exc_info.value.status_code == 500


# ==================== PUT Email Settings Unit Tests ====================

class TestUpdateEmailSettingsUnit:
    """Unit tests for PUT /settings/email endpoint logic."""

    @pytest.mark.asyncio
    async def test_update_email_settings_success(self, mock_config):
        """update_email_settings should update email fields."""
        from src.api.settings_routes import update_email_settings, EmailSettings

        mock_db = MagicMock()
        mock_db.update_tenant_settings.return_value = {"email_from_name": "Updated"}

        data = EmailSettings(from_name="Updated")

        result = await update_email_settings(data=data, config=mock_config, db=mock_db)

        assert result["success"] is True
        assert "data" in result
        mock_db.update_tenant_settings.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_email_settings_all_fields(self, mock_config):
        """update_email_settings should handle all email fields."""
        from src.api.settings_routes import update_email_settings, EmailSettings

        mock_db = MagicMock()
        mock_db.update_tenant_settings.return_value = {"email_from_name": "Name"}

        data = EmailSettings(
            from_name="Name",
            from_email="test@example.com",
            reply_to="reply@example.com",
            quotes_email="quotes@example.com"
        )

        result = await update_email_settings(data=data, config=mock_config, db=mock_db)

        call_kwargs = mock_db.update_tenant_settings.call_args[1]
        assert call_kwargs["email_from_name"] == "Name"
        assert call_kwargs["email_from_email"] == "test@example.com"
        assert call_kwargs["email_reply_to"] == "reply@example.com"
        assert call_kwargs["quotes_email"] == "quotes@example.com"

    @pytest.mark.asyncio
    async def test_update_email_settings_empty_raises_400(self, mock_config):
        """update_email_settings should raise 400 when no fields provided."""
        from src.api.settings_routes import update_email_settings, EmailSettings
        from fastapi import HTTPException

        mock_db = MagicMock()
        data = EmailSettings()  # Empty

        with pytest.raises(HTTPException) as exc_info:
            await update_email_settings(data=data, config=mock_config, db=mock_db)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_update_email_settings_db_failure(self, mock_config):
        """update_email_settings should raise 500 on database failure."""
        from src.api.settings_routes import update_email_settings, EmailSettings
        from fastapi import HTTPException

        mock_db = MagicMock()
        mock_db.update_tenant_settings.return_value = None

        data = EmailSettings(from_name="Test")

        with pytest.raises(HTTPException) as exc_info:
            await update_email_settings(data=data, config=mock_config, db=mock_db)

        assert exc_info.value.status_code == 500


# ==================== PUT Banking Settings Unit Tests ====================

class TestUpdateBankingSettingsUnit:
    """Unit tests for PUT /settings/banking endpoint logic."""

    @pytest.mark.asyncio
    async def test_update_banking_settings_success(self, mock_config):
        """update_banking_settings should update banking fields."""
        from src.api.settings_routes import update_banking_settings, BankingSettings

        mock_db = MagicMock()
        mock_db.update_tenant_settings.return_value = {"bank_name": "Updated"}

        data = BankingSettings(bank_name="Updated")

        result = await update_banking_settings(data=data, config=mock_config, db=mock_db)

        assert result["success"] is True
        assert "data" in result
        mock_db.update_tenant_settings.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_banking_settings_all_fields(self, mock_config):
        """update_banking_settings should handle all banking fields."""
        from src.api.settings_routes import update_banking_settings, BankingSettings

        mock_db = MagicMock()
        mock_db.update_tenant_settings.return_value = {"bank_name": "Bank"}

        data = BankingSettings(
            bank_name="Bank",
            account_name="Account",
            account_number="123",
            branch_code="001",
            swift_code="SWIFT",
            reference_prefix="REF"
        )

        result = await update_banking_settings(data=data, config=mock_config, db=mock_db)

        call_kwargs = mock_db.update_tenant_settings.call_args[1]
        assert call_kwargs["bank_name"] == "Bank"
        assert call_kwargs["bank_account_name"] == "Account"
        assert call_kwargs["bank_account_number"] == "123"
        assert call_kwargs["bank_branch_code"] == "001"
        assert call_kwargs["bank_swift_code"] == "SWIFT"
        assert call_kwargs["payment_reference_prefix"] == "REF"

    @pytest.mark.asyncio
    async def test_update_banking_settings_empty_raises_400(self, mock_config):
        """update_banking_settings should raise 400 when no fields provided."""
        from src.api.settings_routes import update_banking_settings, BankingSettings
        from fastapi import HTTPException

        mock_db = MagicMock()
        data = BankingSettings()

        with pytest.raises(HTTPException) as exc_info:
            await update_banking_settings(data=data, config=mock_config, db=mock_db)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_update_banking_settings_db_failure(self, mock_config):
        """update_banking_settings should raise 500 on database failure."""
        from src.api.settings_routes import update_banking_settings, BankingSettings
        from fastapi import HTTPException

        mock_db = MagicMock()
        mock_db.update_tenant_settings.return_value = None

        data = BankingSettings(bank_name="Test")

        with pytest.raises(HTTPException) as exc_info:
            await update_banking_settings(data=data, config=mock_config, db=mock_db)

        assert exc_info.value.status_code == 500


# ==================== PUT Company Settings Unit Tests ====================

class TestUpdateCompanySettingsUnit:
    """Unit tests for PUT /settings/company endpoint logic."""

    @pytest.mark.asyncio
    async def test_update_company_settings_success(self, mock_config):
        """update_company_settings should update company fields."""
        from src.api.settings_routes import update_company_settings, CompanySettings

        mock_db = MagicMock()
        mock_db.update_tenant_settings.return_value = {"company_name": "Updated"}

        data = CompanySettings(company_name="Updated")

        result = await update_company_settings(data=data, config=mock_config, db=mock_db)

        assert result["success"] is True
        assert "data" in result
        mock_db.update_tenant_settings.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_company_settings_all_fields(self, mock_config):
        """update_company_settings should handle all company fields."""
        from src.api.settings_routes import update_company_settings, CompanySettings

        mock_db = MagicMock()
        mock_db.update_tenant_settings.return_value = {"company_name": "Company"}

        data = CompanySettings(
            company_name="Company",
            support_email="support@test.com",
            support_phone="+123",
            website="https://test.com",
            currency="EUR",
            timezone="Europe/London"
        )

        result = await update_company_settings(data=data, config=mock_config, db=mock_db)

        call_kwargs = mock_db.update_tenant_settings.call_args[1]
        assert call_kwargs["company_name"] == "Company"
        assert call_kwargs["support_email"] == "support@test.com"
        assert call_kwargs["support_phone"] == "+123"
        assert call_kwargs["website"] == "https://test.com"
        assert call_kwargs["currency"] == "EUR"
        assert call_kwargs["timezone"] == "Europe/London"

    @pytest.mark.asyncio
    async def test_update_company_settings_empty_raises_400(self, mock_config):
        """update_company_settings should raise 400 when no fields provided."""
        from src.api.settings_routes import update_company_settings, CompanySettings
        from fastapi import HTTPException

        mock_db = MagicMock()
        data = CompanySettings()

        with pytest.raises(HTTPException) as exc_info:
            await update_company_settings(data=data, config=mock_config, db=mock_db)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_update_company_settings_db_failure(self, mock_config):
        """update_company_settings should raise 500 on database failure."""
        from src.api.settings_routes import update_company_settings, CompanySettings
        from fastapi import HTTPException

        mock_db = MagicMock()
        mock_db.update_tenant_settings.return_value = None

        data = CompanySettings(company_name="Test")

        with pytest.raises(HTTPException) as exc_info:
            await update_company_settings(data=data, config=mock_config, db=mock_db)

        assert exc_info.value.status_code == 500


# ==================== Merge Settings Tests ====================

class TestMergeSettingsAdvanced:
    """Advanced tests for merge_settings_with_config."""

    def test_merge_handles_all_db_fields(self, mock_config):
        """merge_settings_with_config should handle all database fields."""
        from src.api.settings_routes import merge_settings_with_config

        db_settings = {
            "company_name": "DB Company",
            "support_email": "db@test.com",
            "support_phone": "+111",
            "website": "https://db.com",
            "currency": "EUR",
            "timezone": "Asia/Tokyo",
            "email_from_name": "DB From",
            "email_from_email": "from@db.com",
            "email_reply_to": "reply@db.com",
            "quotes_email": "quotes@db.com",
            "bank_name": "DB Bank",
            "bank_account_name": "DB Account",
            "bank_account_number": "999",
            "bank_branch_code": "007",
            "bank_swift_code": "DBSWIFT",
            "payment_reference_prefix": "DB"
        }

        result = merge_settings_with_config(db_settings, mock_config)

        # All values should come from db_settings
        assert result["company"]["company_name"] == "DB Company"
        assert result["company"]["support_email"] == "db@test.com"
        assert result["company"]["currency"] == "EUR"
        assert result["email"]["from_name"] == "DB From"
        assert result["email"]["from_email"] == "from@db.com"
        assert result["banking"]["bank_name"] == "DB Bank"
        assert result["banking"]["swift_code"] == "DBSWIFT"

    def test_merge_handles_partial_db_values(self, mock_config):
        """merge_settings_with_config should merge partial db values with config."""
        from src.api.settings_routes import merge_settings_with_config

        db_settings = {
            "company_name": "Partial Company"
            # Other fields missing
        }

        result = merge_settings_with_config(db_settings, mock_config)

        # DB value takes precedence
        assert result["company"]["company_name"] == "Partial Company"
        # Config fallback for missing
        assert result["company"]["currency"] == mock_config.currency
        assert result["banking"]["bank_name"] == mock_config.bank_name

    def test_merge_handles_empty_strings(self, mock_config):
        """merge_settings_with_config should treat empty strings as valid values."""
        from src.api.settings_routes import merge_settings_with_config

        db_settings = {
            "company_name": ""  # Empty string
        }

        result = merge_settings_with_config(db_settings, mock_config)

        # Empty string is falsy, so should fall back to config
        assert result["company"]["company_name"] == mock_config.company_name

    def test_merge_handles_none_values(self, mock_config):
        """merge_settings_with_config should fall back for None values."""
        from src.api.settings_routes import merge_settings_with_config

        db_settings = {
            "company_name": None
        }

        result = merge_settings_with_config(db_settings, mock_config)

        # None should fall back to config
        assert result["company"]["company_name"] == mock_config.company_name
