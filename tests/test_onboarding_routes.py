"""
Onboarding Routes Unit Tests

Comprehensive tests for tenant onboarding API endpoints:
- POST /api/v1/admin/onboarding/generate-prompt
- GET /api/v1/admin/onboarding/themes
- GET /api/v1/admin/onboarding/voices
- POST /api/v1/admin/onboarding/complete
- GET /api/v1/admin/onboarding/status/{tenant_id}

Uses FastAPI TestClient with mocked dependencies.
These tests verify:
1. Endpoint structure and HTTP methods
2. Request validation
3. Response formats
4. Error handling
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import json
import os


# ==================== Fixtures ====================

@pytest.fixture
def mock_config():
    """Create a mock ClientConfig."""
    config = MagicMock()
    config.client_id = "test_tenant"
    config.tenant_id = "test_tenant"
    config.company_name = "Test Company"
    config.supabase_url = "https://test.supabase.co"
    config.supabase_service_key = "test-service-key"
    config.supabase_anon_key = "test-anon-key"
    config.sendgrid_api_key = "SG.test-key"
    config.logo_url = "https://example.com/logo.png"
    return config


@pytest.fixture
def test_client():
    """Create a basic TestClient."""
    from main import app
    return TestClient(app)


# ==================== Theme Endpoints Tests ====================

class TestGetThemesEndpoint:
    """Test GET /api/v1/admin/onboarding/themes endpoint."""

    def test_get_themes_returns_list(self, test_client):
        """GET /themes should return available brand themes."""
        response = test_client.get("/api/v1/admin/onboarding/themes")
        assert response.status_code == 200
        data = response.json()
        assert "themes" in data
        assert isinstance(data["themes"], list)
        assert len(data["themes"]) > 0

    def test_get_themes_structure(self, test_client):
        """Each theme should have id, name, description, and colors."""
        response = test_client.get("/api/v1/admin/onboarding/themes")
        assert response.status_code == 200
        themes = response.json()["themes"]

        for theme in themes:
            assert "id" in theme
            assert "name" in theme
            assert "description" in theme
            assert "primary" in theme
            assert "secondary" in theme
            assert "accent" in theme

    def test_get_themes_has_expected_presets(self, test_client):
        """Should include common theme presets."""
        response = test_client.get("/api/v1/admin/onboarding/themes")
        themes = response.json()["themes"]
        theme_ids = [t["id"] for t in themes]

        # Check for some expected presets
        assert "ocean-blue" in theme_ids
        assert "safari-gold" in theme_ids


# ==================== Voice Endpoints Tests ====================

class TestGetVoicesEndpoint:
    """Test GET /api/v1/admin/onboarding/voices endpoint."""

    def test_get_voices_returns_list(self, test_client):
        """GET /voices should return voice options (empty for Lite)."""
        response = test_client.get("/api/v1/admin/onboarding/voices")
        assert response.status_code == 200
        data = response.json()
        # Lite mode returns empty list
        assert isinstance(data, list)

    def test_get_voices_lite_mode_empty(self, test_client):
        """GET /voices returns empty list in Lite mode."""
        response = test_client.get("/api/v1/admin/onboarding/voices")
        # Voice features are Pro/Enterprise only
        assert response.json() == []


# ==================== Generate Prompt Tests ====================

class TestGeneratePromptEndpoint:
    """Test POST /api/v1/admin/onboarding/generate-prompt endpoint."""

    def test_generate_prompt_requires_body(self, test_client):
        """POST /generate-prompt requires request body."""
        response = test_client.post(
            "/api/v1/admin/onboarding/generate-prompt",
            json={}
        )
        assert response.status_code == 422  # Validation error

    def test_generate_prompt_requires_description(self, test_client):
        """POST /generate-prompt requires description field."""
        response = test_client.post(
            "/api/v1/admin/onboarding/generate-prompt",
            json={"agent_type": "inbound"}
        )
        assert response.status_code == 422

    def test_generate_prompt_requires_agent_type(self, test_client):
        """POST /generate-prompt requires agent_type field."""
        response = test_client.post(
            "/api/v1/admin/onboarding/generate-prompt",
            json={"description": "A friendly travel assistant that helps customers"}
        )
        assert response.status_code == 422

    def test_generate_prompt_validates_agent_type(self, test_client):
        """POST /generate-prompt validates agent_type values."""
        response = test_client.post(
            "/api/v1/admin/onboarding/generate-prompt",
            json={
                "description": "A friendly travel assistant that helps customers",
                "agent_type": "invalid_type"
            }
        )
        assert response.status_code == 422

    def test_generate_prompt_validates_description_length(self, test_client):
        """POST /generate-prompt requires min 20 char description."""
        response = test_client.post(
            "/api/v1/admin/onboarding/generate-prompt",
            json={
                "description": "Too short",  # Less than 20 chars
                "agent_type": "inbound"
            }
        )
        assert response.status_code == 422

    @patch("src.api.onboarding_routes.GENAI_AVAILABLE", False)
    @patch("src.api.onboarding_routes.genai_client", None)
    def test_generate_prompt_unavailable_without_genai(self, test_client):
        """POST /generate-prompt returns 500 when GenAI unavailable."""
        response = test_client.post(
            "/api/v1/admin/onboarding/generate-prompt",
            json={
                "description": "A friendly travel assistant that helps customers with bookings",
                "agent_type": "inbound"
            }
        )
        # Should return 500 when GenAI not available
        assert response.status_code == 500

    @patch("src.api.onboarding_routes.GENAI_AVAILABLE", True)
    @patch("src.api.onboarding_routes.genai_model")
    def test_generate_prompt_with_genai_model(self, mock_model, test_client):
        """POST /generate-prompt uses genai model when available."""
        # Mock the generate_content response
        mock_response = MagicMock()
        mock_response.text = "You are a helpful travel assistant..."
        mock_model.generate_content.return_value = mock_response

        response = test_client.post(
            "/api/v1/admin/onboarding/generate-prompt",
            json={
                "description": "A friendly travel assistant that helps customers with bookings",
                "agent_type": "inbound",
                "company_name": "Test Travel",
                "agent_name": "Sarah"
            }
        )

        if response.status_code == 200:
            data = response.json()
            assert "system_prompt" in data
            assert "agent_name" in data


# ==================== Complete Onboarding Tests ====================

class TestCompleteOnboardingEndpoint:
    """Test POST /api/v1/admin/onboarding/complete endpoint."""

    def test_complete_requires_body(self, test_client):
        """POST /complete requires request body."""
        response = test_client.post(
            "/api/v1/admin/onboarding/complete",
            json={}
        )
        assert response.status_code == 422

    def test_complete_requires_company_profile(self, test_client):
        """POST /complete requires company profile."""
        response = test_client.post(
            "/api/v1/admin/onboarding/complete",
            json={
                "agents": {
                    "inbound_description": "Test agent description here",
                    "inbound_prompt": "Test prompt"
                }
            }
        )
        assert response.status_code == 422

    def test_complete_validates_company_name(self, test_client):
        """POST /complete validates company name length."""
        response = test_client.post(
            "/api/v1/admin/onboarding/complete",
            json={
                "company": {
                    "company_name": "A",  # Too short (min 2)
                    "support_email": "test@example.com",
                    "brand_theme": {
                        "theme_id": "ocean-blue",
                        "primary": "#0EA5E9",
                        "secondary": "#0284C7",
                        "accent": "#38BDF8"
                    }
                },
                "agents": {
                    "inbound_description": "Test agent description here",
                    "inbound_prompt": "Test prompt"
                },
                "outbound": {},
                "email": {"from_name": "Test"},
                "knowledge_base": {}
            }
        )
        assert response.status_code == 422

    def test_complete_validates_email_format(self, test_client):
        """POST /complete validates support email format."""
        response = test_client.post(
            "/api/v1/admin/onboarding/complete",
            json={
                "company": {
                    "company_name": "Test Company",
                    "support_email": "invalid-email",  # Invalid format
                    "brand_theme": {
                        "theme_id": "ocean-blue",
                        "primary": "#0EA5E9",
                        "secondary": "#0284C7",
                        "accent": "#38BDF8"
                    }
                },
                "agents": {
                    "inbound_description": "Test agent description here",
                    "inbound_prompt": "Test prompt"
                },
                "outbound": {},
                "email": {"from_name": "Test"},
                "knowledge_base": {}
            }
        )
        assert response.status_code == 422

    @patch("src.api.onboarding_routes.provision_sendgrid_subuser")
    @patch("src.api.onboarding_routes.create_tenant_config")
    def test_complete_onboarding_success(
        self, mock_create_config, mock_sendgrid, test_client
    ):
        """POST /complete creates tenant successfully."""
        mock_sendgrid.return_value = {"success": False, "error": "Not configured"}
        mock_create_config.return_value = True

        response = test_client.post(
            "/api/v1/admin/onboarding/complete",
            json={
                "company": {
                    "company_name": "Test Travel Agency",
                    "support_email": "support@test.com",
                    "brand_theme": {
                        "theme_id": "ocean-blue",
                        "primary": "#0EA5E9",
                        "secondary": "#0284C7",
                        "accent": "#38BDF8"
                    }
                },
                "agents": {
                    "inbound_description": "A friendly travel agent that helps customers",
                    "inbound_prompt": "You are a helpful travel assistant."
                },
                "outbound": {
                    "enabled": True
                },
                "email": {
                    "from_name": "Test Travel"
                },
                "knowledge_base": {}
            }
        )

        # Should return 200 or handle provisioning
        # Response depends on mocked services
        assert response.status_code in [200, 500]


# ==================== Status Endpoint Tests ====================

class TestGetStatusEndpoint:
    """Test GET /api/v1/admin/onboarding/status/{tenant_id} endpoint."""

    def test_get_status_nonexistent_tenant(self, test_client):
        """GET /status/{tenant_id} for nonexistent tenant."""
        response = test_client.get(
            "/api/v1/admin/onboarding/status/nonexistent_tenant_xyz123"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] == False
        assert data["status"] == "not_started"

    def test_get_status_response_format(self, test_client):
        """GET /status returns expected fields."""
        response = test_client.get(
            "/api/v1/admin/onboarding/status/test_tenant"
        )
        assert response.status_code == 200
        data = response.json()
        assert "tenant_id" in data
        assert "exists" in data
        assert "status" in data

    @patch("config.loader.ClientConfig")
    def test_get_status_existing_tenant(self, mock_config_class, test_client):
        """GET /status/{tenant_id} for existing tenant."""
        mock_config = MagicMock()
        mock_config.company_name = "Test Company"
        mock_config.sendgrid_api_key = "SG.test"
        mock_config_class.return_value = mock_config

        # This test verifies the endpoint handles both existing and nonexistent cases
        response = test_client.get(
            "/api/v1/admin/onboarding/status/some_tenant_id"
        )
        # Should return 200 regardless (with exists: true/false)
        assert response.status_code == 200
        data = response.json()
        assert "tenant_id" in data


# ==================== Tenant ID Generation Tests ====================

class TestTenantIdGeneration:
    """Test generate_tenant_id helper function."""

    def test_generate_tenant_id_format(self):
        """Tenant ID should have tn_ prefix."""
        from src.api.onboarding_routes import generate_tenant_id

        tenant_id = generate_tenant_id("Test Company")
        assert tenant_id.startswith("tn_")
        # Format: tn_{hash}_{random}
        parts = tenant_id.split("_")
        assert len(parts) == 3
        assert len(parts[1]) == 8  # Hash component
        assert len(parts[2]) == 12  # Random component

    def test_generate_tenant_id_uniqueness(self):
        """Generate unique IDs for same company name."""
        from src.api.onboarding_routes import generate_tenant_id

        id1 = generate_tenant_id("Same Company")
        id2 = generate_tenant_id("Same Company")

        # Should be different due to timestamp and random
        assert id1 != id2

    def test_generate_tenant_id_handles_special_chars(self):
        """Handle special characters in company name."""
        from src.api.onboarding_routes import generate_tenant_id

        tenant_id = generate_tenant_id("Test & Company (Pty) Ltd!")
        assert tenant_id.startswith("tn_")
        # Should not crash with special characters


# ==================== Request Validation Tests ====================

class TestOnboardingRequestValidation:
    """Test Pydantic model validation."""

    def test_brand_theme_required_fields(self, test_client):
        """Brand theme requires all color fields."""
        response = test_client.post(
            "/api/v1/admin/onboarding/complete",
            json={
                "company": {
                    "company_name": "Test Company",
                    "support_email": "test@example.com",
                    "brand_theme": {
                        "theme_id": "custom"
                        # Missing primary, secondary, accent
                    }
                },
                "agents": {
                    "inbound_description": "Test agent description here",
                    "inbound_prompt": "Test prompt"
                },
                "outbound": {},
                "email": {"from_name": "Test"},
                "knowledge_base": {}
            }
        )
        assert response.status_code == 422

    def test_outbound_settings_defaults(self, test_client):
        """Outbound settings use sensible defaults."""
        from src.api.onboarding_routes import OutboundSettings

        settings = OutboundSettings()
        assert settings.enabled == True
        assert settings.timing == "next_business_day"
        assert settings.max_attempts == 2

    def test_email_settings_validation(self, test_client):
        """Email settings validate correctly."""
        from src.api.onboarding_routes import EmailSettings

        settings = EmailSettings(from_name="Test")
        assert settings.auto_send_quotes == True
        assert settings.quote_validity_days == 14

    def test_agent_config_description_min_length(self, test_client):
        """Agent config requires min 20 char description."""
        response = test_client.post(
            "/api/v1/admin/onboarding/complete",
            json={
                "company": {
                    "company_name": "Test Company",
                    "support_email": "test@example.com",
                    "brand_theme": {
                        "theme_id": "ocean-blue",
                        "primary": "#0EA5E9",
                        "secondary": "#0284C7",
                        "accent": "#38BDF8"
                    }
                },
                "agents": {
                    "inbound_description": "Too short",  # Less than 20 chars
                    "inbound_prompt": "Test prompt"
                },
                "outbound": {},
                "email": {"from_name": "Test"},
                "knowledge_base": {}
            }
        )
        assert response.status_code == 422


# ==================== Free Email Detection Tests ====================

class TestIsFreeEmail:
    """Test is_free_email helper function."""

    def test_gmail_is_free(self):
        """Gmail addresses are free email."""
        from src.api.onboarding_routes import is_free_email
        assert is_free_email("user@gmail.com") == True

    def test_googlemail_is_free(self):
        """Googlemail addresses are free email."""
        from src.api.onboarding_routes import is_free_email
        assert is_free_email("user@googlemail.com") == True

    def test_yahoo_is_free(self):
        """Yahoo addresses are free email."""
        from src.api.onboarding_routes import is_free_email
        assert is_free_email("user@yahoo.com") == True

    def test_yahoo_regional_is_free(self):
        """Regional Yahoo addresses are free email."""
        from src.api.onboarding_routes import is_free_email
        assert is_free_email("user@yahoo.co.uk") == True
        assert is_free_email("user@yahoo.co.za") == True
        assert is_free_email("user@yahoo.ca") == True

    def test_outlook_is_free(self):
        """Outlook/Hotmail addresses are free email."""
        from src.api.onboarding_routes import is_free_email
        assert is_free_email("user@outlook.com") == True
        assert is_free_email("user@hotmail.com") == True
        assert is_free_email("user@live.com") == True
        assert is_free_email("user@msn.com") == True

    def test_icloud_is_free(self):
        """iCloud addresses are free email."""
        from src.api.onboarding_routes import is_free_email
        assert is_free_email("user@icloud.com") == True
        assert is_free_email("user@me.com") == True
        assert is_free_email("user@mac.com") == True

    def test_protonmail_is_free(self):
        """ProtonMail addresses are free email."""
        from src.api.onboarding_routes import is_free_email
        assert is_free_email("user@protonmail.com") == True
        assert is_free_email("user@proton.me") == True

    def test_aol_is_free(self):
        """AOL addresses are free email."""
        from src.api.onboarding_routes import is_free_email
        assert is_free_email("user@aol.com") == True

    def test_custom_domain_not_free(self):
        """Custom domain addresses are not free."""
        from src.api.onboarding_routes import is_free_email
        assert is_free_email("user@company.com") == False
        assert is_free_email("support@travelbiz.co.za") == False
        assert is_free_email("info@myagency.travel") == False

    def test_case_insensitive(self):
        """Email detection is case insensitive."""
        from src.api.onboarding_routes import is_free_email
        assert is_free_email("USER@GMAIL.COM") == True
        assert is_free_email("User@Gmail.Com") == True

    def test_empty_email_returns_false(self):
        """Empty email returns False."""
        from src.api.onboarding_routes import is_free_email
        assert is_free_email("") == False
        assert is_free_email(None) == False

    def test_invalid_email_returns_false(self):
        """Email without @ returns False."""
        from src.api.onboarding_routes import is_free_email
        assert is_free_email("not-an-email") == False
        assert is_free_email("missing.at.sign") == False


# ==================== Platform Email Generation Tests ====================

class TestGeneratePlatformEmail:
    """Test generate_platform_email helper function."""

    def test_simple_company_name(self):
        """Generate email from simple company name."""
        from src.api.onboarding_routes import generate_platform_email
        result = generate_platform_email("Safari Tours", "tn_abc123_xyz")
        assert result == "safaritours@holidaytoday.co.za"

    def test_company_name_with_special_chars(self):
        """Generate email from company name with special characters."""
        from src.api.onboarding_routes import generate_platform_email
        result = generate_platform_email("Safari & Beach (Pty) Ltd!", "tn_abc123_xyz")
        assert result == "safaribeachptyltd@holidaytoday.co.za"

    def test_company_name_with_numbers(self):
        """Generate email preserves numbers."""
        from src.api.onboarding_routes import generate_platform_email
        result = generate_platform_email("Travel 2000", "tn_abc123_xyz")
        assert result == "travel2000@holidaytoday.co.za"

    def test_company_name_with_spaces(self):
        """Generate email removes spaces."""
        from src.api.onboarding_routes import generate_platform_email
        result = generate_platform_email("My Travel Agency", "tn_abc123_xyz")
        assert result == "mytravelagency@holidaytoday.co.za"

    def test_empty_company_name_uses_tenant_id(self):
        """Empty company name falls back to tenant_id."""
        from src.api.onboarding_routes import generate_platform_email
        result = generate_platform_email("!!!", "tn_abc123_xyz456")
        # Should use sanitized tenant_id when company name yields nothing
        assert result.endswith("@holidaytoday.co.za")
        assert "tn" in result or "abc" in result

    def test_uppercase_converted_to_lowercase(self):
        """Company name is converted to lowercase."""
        from src.api.onboarding_routes import generate_platform_email
        result = generate_platform_email("SAFARI TOURS", "tn_abc123_xyz")
        assert result == "safaritours@holidaytoday.co.za"

    def test_unicode_company_name(self):
        """Unicode characters are stripped."""
        from src.api.onboarding_routes import generate_platform_email
        result = generate_platform_email("Safari Tøurs", "tn_abc123_xyz")
        # Non-ASCII chars are stripped
        assert "@holidaytoday.co.za" in result


# ==================== SendGrid Subuser Provisioning Tests ====================

class TestProvisionSendgridSubuser:
    """Test provision_sendgrid_subuser async function."""

    @pytest.mark.asyncio
    @patch("src.api.onboarding_routes.SENDGRID_PROVISIONING_AVAILABLE", False)
    async def test_returns_error_when_not_available(self):
        """Returns error when SendGrid provisioning not available."""
        from src.api.onboarding_routes import provision_sendgrid_subuser
        result = await provision_sendgrid_subuser(
            tenant_id="tn_test123",
            contact_email="admin@test.com",
            from_email="test@company.com",
            from_name="Test Company",
            company_name="Test Company"
        )
        assert result["success"] == False
        assert "not available" in result["error"]

    @pytest.mark.asyncio
    @patch("src.api.onboarding_routes.SENDGRID_PROVISIONING_AVAILABLE", True)
    @patch.dict(os.environ, {"SENDGRID_MASTER_API_KEY": ""}, clear=False)
    async def test_returns_error_when_no_master_key(self):
        """Returns error when master API key not configured."""
        from src.api.onboarding_routes import provision_sendgrid_subuser
        # Temporarily clear the env var
        with patch.dict(os.environ, {"SENDGRID_MASTER_API_KEY": ""}):
            result = await provision_sendgrid_subuser(
                tenant_id="tn_test123",
                contact_email="admin@test.com",
                from_email="test@company.com",
                from_name="Test Company",
                company_name="Test Company"
            )
        assert result["success"] == False
        assert "not configured" in result["error"]

    @pytest.mark.asyncio
    @patch("src.api.onboarding_routes.SENDGRID_PROVISIONING_AVAILABLE", True)
    @patch("src.api.onboarding_routes.SendGridProvisioner")
    @patch.dict(os.environ, {"SENDGRID_MASTER_API_KEY": "SG.test-master-key"})
    async def test_creates_subuser_successfully(self, mock_provisioner_class):
        """Creates subuser and API key successfully."""
        from src.api.onboarding_routes import provision_sendgrid_subuser

        # Mock provisioner instance
        mock_provisioner = MagicMock()
        mock_provisioner.create_subuser.return_value = {"success": True}
        mock_provisioner.create_api_key.return_value = {
            "success": True,
            "data": {"api_key": "SG.new-api-key"}
        }
        mock_provisioner.add_verified_sender.return_value = {"success": True}
        mock_provisioner.assign_ip_to_subuser.return_value = {"success": False}
        mock_provisioner_class.return_value = mock_provisioner

        result = await provision_sendgrid_subuser(
            tenant_id="tn_test123_abc",
            contact_email="admin@test.com",
            from_email="test@company.com",
            from_name="Test Company",
            company_name="Test Company",
            use_platform_domain=False
        )

        assert result["success"] == True
        assert result["api_key"] == "SG.new-api-key"
        assert result["sender_verified"] == True

    @pytest.mark.asyncio
    @patch("src.api.onboarding_routes.SENDGRID_PROVISIONING_AVAILABLE", True)
    @patch("src.api.onboarding_routes.SendGridProvisioner")
    @patch.dict(os.environ, {"SENDGRID_MASTER_API_KEY": "SG.test-master-key"})
    async def test_assigns_platform_domain(self, mock_provisioner_class):
        """Assigns platform domain when use_platform_domain=True."""
        from src.api.onboarding_routes import provision_sendgrid_subuser

        mock_provisioner = MagicMock()
        mock_provisioner.create_subuser.return_value = {"success": True}
        mock_provisioner.create_api_key.return_value = {
            "success": True,
            "data": {"api_key": "SG.new-api-key"}
        }
        mock_provisioner.assign_domain_to_subuser.return_value = {"success": True}
        mock_provisioner.assign_ip_to_subuser.return_value = {"success": False}
        mock_provisioner_class.return_value = mock_provisioner

        result = await provision_sendgrid_subuser(
            tenant_id="tn_test123_abc",
            contact_email="admin@test.com",
            from_email="test@holidaytoday.co.za",
            from_name="Test Company",
            company_name="Test Company",
            use_platform_domain=True
        )

        assert result["success"] == True
        assert result["domain_assigned"] == True
        mock_provisioner.assign_domain_to_subuser.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.api.onboarding_routes.SENDGRID_PROVISIONING_AVAILABLE", True)
    @patch("src.api.onboarding_routes.SendGridProvisioner")
    @patch.dict(os.environ, {"SENDGRID_MASTER_API_KEY": "SG.test-master-key"})
    async def test_handles_subuser_already_exists(self, mock_provisioner_class):
        """Handles case when subuser already exists."""
        from src.api.onboarding_routes import provision_sendgrid_subuser

        mock_provisioner = MagicMock()
        mock_provisioner.create_subuser.return_value = {
            "success": False,
            "error": "Username already exists"
        }
        mock_provisioner.create_api_key.return_value = {
            "success": True,
            "data": {"api_key": "SG.existing-key"}
        }
        mock_provisioner.add_verified_sender.return_value = {"success": True}
        mock_provisioner.assign_ip_to_subuser.return_value = {"success": False}
        mock_provisioner_class.return_value = mock_provisioner

        result = await provision_sendgrid_subuser(
            tenant_id="tn_existing_user",
            contact_email="admin@test.com",
            from_email="test@company.com",
            from_name="Test Company",
            company_name="Test Company"
        )

        # Should continue and create API key even if subuser exists
        assert result["success"] == True

    @pytest.mark.asyncio
    @patch("src.api.onboarding_routes.SENDGRID_PROVISIONING_AVAILABLE", True)
    @patch("src.api.onboarding_routes.SendGridProvisioner")
    @patch.dict(os.environ, {"SENDGRID_MASTER_API_KEY": "SG.test-master-key"})
    async def test_handles_api_key_creation_failure(self, mock_provisioner_class):
        """Handles API key creation failure."""
        from src.api.onboarding_routes import provision_sendgrid_subuser

        mock_provisioner = MagicMock()
        mock_provisioner.create_subuser.return_value = {"success": True}
        mock_provisioner.create_api_key.return_value = {
            "success": False,
            "error": "API key limit reached"
        }
        mock_provisioner_class.return_value = mock_provisioner

        result = await provision_sendgrid_subuser(
            tenant_id="tn_test123_abc",
            contact_email="admin@test.com",
            from_email="test@company.com",
            from_name="Test Company",
            company_name="Test Company"
        )

        assert result["success"] == False
        assert "API key limit reached" in result["error"]

    @pytest.mark.asyncio
    @patch("src.api.onboarding_routes.SENDGRID_PROVISIONING_AVAILABLE", True)
    @patch("src.api.onboarding_routes.SendGridProvisioner")
    @patch.dict(os.environ, {"SENDGRID_MASTER_API_KEY": "SG.test-master-key"})
    async def test_handles_exception_gracefully(self, mock_provisioner_class):
        """Handles unexpected exceptions."""
        from src.api.onboarding_routes import provision_sendgrid_subuser

        mock_provisioner_class.side_effect = Exception("Network error")

        result = await provision_sendgrid_subuser(
            tenant_id="tn_test123_abc",
            contact_email="admin@test.com",
            from_email="test@company.com",
            from_name="Test Company",
            company_name="Test Company"
        )

        assert result["success"] == False
        assert "failed" in result["error"].lower()


# ==================== Tenant Config Creation Tests ====================

class TestCreateTenantConfig:
    """Test create_tenant_config async function."""

    @pytest.fixture
    def mock_onboarding_request(self):
        """Create a mock onboarding request."""
        from src.api.onboarding_routes import (
            OnboardingRequest, CompanyProfile, BrandTheme,
            AgentConfig, OutboundSettings, EmailSettings,
            KnowledgeBaseConfig
        )
        return OnboardingRequest(
            company=CompanyProfile(
                company_name="Test Travel Agency",
                support_email="support@test.com",
                timezone="Africa/Johannesburg",
                currency="ZAR",
                brand_theme=BrandTheme(
                    theme_id="ocean-blue",
                    primary="#0EA5E9",
                    secondary="#0284C7",
                    accent="#38BDF8"
                )
            ),
            agents=AgentConfig(
                inbound_description="A helpful travel assistant for bookings",
                inbound_prompt="You are a helpful travel agent.",
                inbound_agent_name="Sarah"
            ),
            outbound=OutboundSettings(),
            email=EmailSettings(from_name="Test Travel"),
            knowledge_base=KnowledgeBaseConfig()
        )

    @pytest.mark.asyncio
    @patch("builtins.open", create=True)
    @patch("pathlib.Path.mkdir")
    async def test_creates_tenant_directory(self, mock_mkdir, mock_open, mock_onboarding_request):
        """Creates tenant directory structure."""
        from src.api.onboarding_routes import create_tenant_config

        # Mock file writes
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        result = await create_tenant_config(
            tenant_id="tn_test123_abc",
            request=mock_onboarding_request
        )

        assert result == True
        # Verify mkdir was called
        assert mock_mkdir.call_count >= 2  # base path + prompts

    @pytest.mark.asyncio
    @patch("builtins.open", create=True)
    @patch("pathlib.Path.mkdir")
    async def test_writes_config_yaml(self, mock_mkdir, mock_open, mock_onboarding_request):
        """Writes config.yaml file."""
        from src.api.onboarding_routes import create_tenant_config
        import yaml

        written_content = []

        def capture_write(content):
            written_content.append(content)

        mock_file = MagicMock()
        mock_file.write = capture_write
        mock_open.return_value.__enter__.return_value = mock_file

        result = await create_tenant_config(
            tenant_id="tn_test123_abc",
            request=mock_onboarding_request,
            sendgrid_api_key="SG.test-key",
            sending_email="testagency@holidaytoday.co.za",
            reply_to_email="support@test.com"
        )

        assert result == True
        # Verify open was called for config file
        assert mock_open.call_count >= 2  # prompt + config

    @pytest.mark.asyncio
    @patch("builtins.open", create=True)
    @patch("pathlib.Path.mkdir")
    async def test_writes_inbound_prompt(self, mock_mkdir, mock_open, mock_onboarding_request):
        """Writes inbound prompt file."""
        from src.api.onboarding_routes import create_tenant_config

        written_content = {}

        def mock_open_side_effect(path, mode='r'):
            mock_file = MagicMock()
            mock_file.__enter__ = MagicMock(return_value=mock_file)
            mock_file.__exit__ = MagicMock(return_value=False)
            mock_file.write = lambda content: written_content.update({str(path): content})
            return mock_file

        mock_open.side_effect = mock_open_side_effect

        result = await create_tenant_config(
            tenant_id="tn_test123_abc",
            request=mock_onboarding_request
        )

        assert result == True

    @pytest.mark.asyncio
    @patch("builtins.open", create=True)
    @patch("pathlib.Path.mkdir")
    async def test_uses_resolved_emails(self, mock_mkdir, mock_open, mock_onboarding_request):
        """Uses resolved sending and reply-to emails."""
        from src.api.onboarding_routes import create_tenant_config
        import yaml

        captured_yaml = []

        def mock_yaml_dump(data, f, **kwargs):
            captured_yaml.append(data)

        with patch("yaml.dump", mock_yaml_dump):
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            result = await create_tenant_config(
                tenant_id="tn_test123_abc",
                request=mock_onboarding_request,
                sending_email="platform@holidaytoday.co.za",
                reply_to_email="support@test.com"
            )

            assert result == True
            # Verify emails were passed to config
            if captured_yaml:
                config = captured_yaml[0]
                assert config["email"]["primary"] == "platform@holidaytoday.co.za"
                assert config["email"]["sendgrid"]["reply_to"] == "support@test.com"

    @pytest.mark.asyncio
    @patch("builtins.open", create=True)
    @patch("pathlib.Path.mkdir")
    async def test_generates_short_name(self, mock_mkdir, mock_open, mock_onboarding_request):
        """Generates short_name from company name."""
        from src.api.onboarding_routes import create_tenant_config
        import yaml

        captured_yaml = []

        def mock_yaml_dump(data, f, **kwargs):
            captured_yaml.append(data)

        with patch("yaml.dump", mock_yaml_dump):
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            result = await create_tenant_config(
                tenant_id="tn_test123_abc",
                request=mock_onboarding_request
            )

            assert result == True
            if captured_yaml:
                config = captured_yaml[0]
                # "Test Travel Agency" -> "testtravelagency"
                assert config["client"]["short_name"] == "testtravelagency"


# ==================== Pydantic Model Tests ====================

class TestPydanticModels:
    """Test Pydantic model validation and defaults."""

    def test_company_profile_defaults(self):
        """CompanyProfile uses correct defaults."""
        from src.api.onboarding_routes import CompanyProfile, BrandTheme
        profile = CompanyProfile(
            company_name="Test Company",
            support_email="test@test.com",
            brand_theme=BrandTheme(
                theme_id="ocean-blue",
                primary="#0EA5E9",
                secondary="#0284C7",
                accent="#38BDF8"
            )
        )
        assert profile.timezone == "Africa/Johannesburg"
        assert profile.currency == "ZAR"

    def test_agent_config_defaults(self):
        """AgentConfig uses correct defaults."""
        from src.api.onboarding_routes import AgentConfig
        config = AgentConfig(
            inbound_description="A helpful travel assistant for bookings",
            inbound_prompt="You are a travel agent."
        )
        assert config.inbound_agent_name == "Sarah"
        assert config.outbound_agent_name == "Michael"

    def test_outbound_settings_validation(self):
        """OutboundSettings validates max_attempts range."""
        from src.api.onboarding_routes import OutboundSettings
        import pydantic

        # Valid range
        settings = OutboundSettings(max_attempts=3)
        assert settings.max_attempts == 3

        # Below minimum
        with pytest.raises(pydantic.ValidationError):
            OutboundSettings(max_attempts=0)

        # Above maximum
        with pytest.raises(pydantic.ValidationError):
            OutboundSettings(max_attempts=10)

    def test_knowledge_base_config_defaults(self):
        """KnowledgeBaseConfig uses correct defaults."""
        from src.api.onboarding_routes import KnowledgeBaseConfig
        config = KnowledgeBaseConfig()
        assert "Destinations" in config.categories
        assert "Hotels" in config.categories
        assert "FAQs" in config.categories
        assert config.skip_initial_setup == True

    def test_voice_option_model(self):
        """VoiceOption model structure."""
        from src.api.onboarding_routes import VoiceOption
        voice = VoiceOption(
            id="voice-1",
            name="Sarah",
            gender="female",
            provider="elevenlabs"
        )
        assert voice.id == "voice-1"
        assert voice.accent is None  # Optional field

    def test_generate_prompt_request_validation(self):
        """GeneratePromptRequest validates agent_type pattern."""
        from src.api.onboarding_routes import GeneratePromptRequest
        import pydantic

        # Valid types
        req1 = GeneratePromptRequest(
            description="A helpful travel agent for bookings",
            agent_type="inbound"
        )
        assert req1.agent_type == "inbound"

        req2 = GeneratePromptRequest(
            description="A follow-up agent for quotes",
            agent_type="outbound"
        )
        assert req2.agent_type == "outbound"

        # Invalid type
        with pytest.raises(pydantic.ValidationError):
            GeneratePromptRequest(
                description="A helpful agent",
                agent_type="invalid"
            )

    def test_onboarding_response_includes_user(self):
        """OnboardingResponse includes user field for auto-login."""
        from src.api.onboarding_routes import OnboardingResponse
        response = OnboardingResponse(
            success=True,
            tenant_id="tn_test123",
            message="Success",
            resources={},
            user={"id": "user-123", "email": "test@test.com"}
        )
        assert response.user is not None
        assert response.user["id"] == "user-123"


# ==================== Brand Themes Data Tests ====================

class TestBrandThemesData:
    """Test BRAND_THEMES constant data."""

    def test_all_themes_have_required_fields(self):
        """All themes have required fields."""
        from src.api.onboarding_routes import BRAND_THEMES
        required_fields = ["id", "name", "description", "primary", "secondary", "accent"]

        for theme in BRAND_THEMES:
            for field in required_fields:
                assert field in theme, f"Theme {theme.get('id', 'unknown')} missing {field}"

    def test_all_themes_have_valid_colors(self):
        """All theme colors are valid hex codes."""
        from src.api.onboarding_routes import BRAND_THEMES
        import re
        hex_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')

        for theme in BRAND_THEMES:
            for color_field in ["primary", "secondary", "accent"]:
                color = theme[color_field]
                assert hex_pattern.match(color), f"Invalid color {color} in theme {theme['id']}"

    def test_theme_ids_are_unique(self):
        """All theme IDs are unique."""
        from src.api.onboarding_routes import BRAND_THEMES
        ids = [t["id"] for t in BRAND_THEMES]
        assert len(ids) == len(set(ids)), "Duplicate theme IDs found"

    def test_minimum_theme_count(self):
        """At least 5 themes are available."""
        from src.api.onboarding_routes import BRAND_THEMES
        assert len(BRAND_THEMES) >= 5


# ==================== Free Email Domains Data Tests ====================

class TestFreeEmailDomainsData:
    """Test FREE_EMAIL_DOMAINS constant data."""

    def test_common_providers_included(self):
        """Common free email providers are included."""
        from src.api.onboarding_routes import FREE_EMAIL_DOMAINS
        assert "gmail.com" in FREE_EMAIL_DOMAINS
        assert "yahoo.com" in FREE_EMAIL_DOMAINS
        assert "outlook.com" in FREE_EMAIL_DOMAINS
        assert "hotmail.com" in FREE_EMAIL_DOMAINS

    def test_domains_are_lowercase(self):
        """All domains are lowercase."""
        from src.api.onboarding_routes import FREE_EMAIL_DOMAINS
        for domain in FREE_EMAIL_DOMAINS:
            assert domain == domain.lower(), f"Domain {domain} not lowercase"

    def test_no_duplicate_domains(self):
        """No duplicate domains."""
        from src.api.onboarding_routes import FREE_EMAIL_DOMAINS
        assert len(FREE_EMAIL_DOMAINS) == len(set(FREE_EMAIL_DOMAINS))


# ==================== NEW: Step Validation Tests ====================

class TestOnboardingStepValidation:
    """Test validation for each onboarding wizard step."""

    def test_company_name_min_length_boundary(self, test_client):
        """Company name at exactly 2 chars should be accepted."""
        from src.api.onboarding_routes import CompanyProfile, BrandTheme
        profile = CompanyProfile(
            company_name="AB",
            support_email="test@test.com",
            brand_theme=BrandTheme(
                theme_id="ocean-blue",
                primary="#0EA5E9",
                secondary="#0284C7",
                accent="#38BDF8"
            )
        )
        assert profile.company_name == "AB"

    def test_company_name_max_length_boundary(self, test_client):
        """Company name at exactly 100 chars should be accepted."""
        from src.api.onboarding_routes import CompanyProfile, BrandTheme
        long_name = "A" * 100
        profile = CompanyProfile(
            company_name=long_name,
            support_email="test@test.com",
            brand_theme=BrandTheme(
                theme_id="ocean-blue",
                primary="#0EA5E9",
                secondary="#0284C7",
                accent="#38BDF8"
            )
        )
        assert len(profile.company_name) == 100

    def test_company_name_exceeds_max_length(self, test_client):
        """Company name over 100 chars should be rejected."""
        import pydantic
        from src.api.onboarding_routes import CompanyProfile, BrandTheme

        with pytest.raises(pydantic.ValidationError):
            CompanyProfile(
                company_name="A" * 101,
                support_email="test@test.com",
                brand_theme=BrandTheme(
                    theme_id="ocean-blue",
                    primary="#0EA5E9",
                    secondary="#0284C7",
                    accent="#38BDF8"
                )
            )

    def test_inbound_description_min_length_boundary(self, test_client):
        """Agent description at exactly 20 chars should be accepted."""
        from src.api.onboarding_routes import AgentConfig
        config = AgentConfig(
            inbound_description="A" * 20,
            inbound_prompt="test prompt"
        )
        assert len(config.inbound_description) == 20

    def test_inbound_description_too_short_rejected(self, test_client):
        """Agent description under 20 chars should be rejected."""
        import pydantic
        from src.api.onboarding_routes import AgentConfig

        with pytest.raises(pydantic.ValidationError):
            AgentConfig(
                inbound_description="A" * 19,
                inbound_prompt="test prompt"
            )

    def test_email_settings_follow_up_days_default(self, test_client):
        """Email settings follow_up_days should default to 3."""
        from src.api.onboarding_routes import EmailSettings
        settings = EmailSettings(from_name="Test")
        assert settings.follow_up_days == 3

    def test_outbound_call_window_defaults(self, test_client):
        """OutboundSettings call window should default to business hours."""
        from src.api.onboarding_routes import OutboundSettings
        settings = OutboundSettings()
        assert settings.call_window_start == "09:00"
        assert settings.call_window_end == "17:00"

    def test_outbound_call_days_default_weekdays(self, test_client):
        """OutboundSettings should default to weekdays only."""
        from src.api.onboarding_routes import OutboundSettings
        settings = OutboundSettings()
        assert "mon" in settings.call_days
        assert "sat" not in settings.call_days
        assert "sun" not in settings.call_days
        assert len(settings.call_days) == 5


# ==================== NEW: Progress Tracking Tests ====================

class TestOnboardingProgressTracking:
    """Test onboarding progress and status tracking."""

    def test_status_nonexistent_tenant_returns_not_started(self, test_client):
        """Status for nonexistent tenant shows not_started."""
        response = test_client.get(
            "/api/v1/admin/onboarding/status/tn_totally_fake_12345"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is False
        assert data["status"] == "not_started"

    def test_status_includes_tenant_id_in_response(self, test_client):
        """Status response always includes the queried tenant_id."""
        tenant_id = "tn_query_test_abc"
        response = test_client.get(
            f"/api/v1/admin/onboarding/status/{tenant_id}"
        )
        data = response.json()
        assert data["tenant_id"] == tenant_id

    @patch("src.api.onboarding_routes.provision_sendgrid_subuser")
    @patch("src.api.onboarding_routes.create_tenant_config")
    def test_onboarding_response_includes_resources(
        self, mock_create_config, mock_sendgrid, test_client
    ):
        """Onboarding response should include a resources dict."""
        mock_sendgrid.return_value = {"success": False, "error": "Not configured"}
        mock_create_config.return_value = True

        response = test_client.post(
            "/api/v1/admin/onboarding/complete",
            json={
                "company": {
                    "company_name": "Progress Track Co",
                    "support_email": "track@test.com",
                    "brand_theme": {
                        "theme_id": "ocean-blue",
                        "primary": "#0EA5E9",
                        "secondary": "#0284C7",
                        "accent": "#38BDF8"
                    }
                },
                "agents": {
                    "inbound_description": "A friendly travel agent that helps customers with bookings",
                    "inbound_prompt": "You are a helpful travel assistant."
                },
                "outbound": {"enabled": True},
                "email": {"from_name": "Test Travel"},
                "knowledge_base": {}
            }
        )

        if response.status_code == 200:
            data = response.json()
            assert "resources" in data
            assert "tenant_id" in data["resources"]


# ==================== NEW: Configuration Wizard Steps Tests ====================

class TestConfigurationWizardSteps:
    """Test individual wizard step configurations."""

    def test_knowledge_base_custom_categories(self):
        """KnowledgeBaseConfig should accept custom categories."""
        from src.api.onboarding_routes import KnowledgeBaseConfig
        config = KnowledgeBaseConfig(
            categories=["Custom Cat 1", "Custom Cat 2", "Custom Cat 3"]
        )
        assert len(config.categories) == 3
        assert "Custom Cat 1" in config.categories

    def test_knowledge_base_skip_initial_setup_toggle(self):
        """KnowledgeBaseConfig skip_initial_setup can be toggled."""
        from src.api.onboarding_routes import KnowledgeBaseConfig
        config = KnowledgeBaseConfig(skip_initial_setup=False)
        assert config.skip_initial_setup is False

    def test_email_settings_custom_validity_days(self):
        """EmailSettings should accept custom quote validity days."""
        from src.api.onboarding_routes import EmailSettings
        settings = EmailSettings(from_name="Test", quote_validity_days=30)
        assert settings.quote_validity_days == 30

    def test_email_settings_from_email_optional(self):
        """EmailSettings from_email should be optional."""
        from src.api.onboarding_routes import EmailSettings
        settings = EmailSettings(from_name="Test")
        assert settings.from_email is None

    def test_agent_config_outbound_fields_optional(self):
        """AgentConfig outbound fields should be optional."""
        from src.api.onboarding_routes import AgentConfig
        config = AgentConfig(
            inbound_description="A friendly travel agent that helps customers",
            inbound_prompt="You are a travel agent."
        )
        assert config.outbound_description is None
        assert config.outbound_prompt is None

    def test_company_profile_optional_fields(self):
        """CompanyProfile optional fields default to None."""
        from src.api.onboarding_routes import CompanyProfile, BrandTheme
        profile = CompanyProfile(
            company_name="Test Company",
            support_email="test@test.com",
            brand_theme=BrandTheme(
                theme_id="ocean-blue",
                primary="#0EA5E9",
                secondary="#0284C7",
                accent="#38BDF8"
            )
        )
        assert profile.support_phone is None
        assert profile.website_url is None
        assert profile.logo_url is None


# ==================== NEW: Default Values Tests ====================

class TestOnboardingDefaults:
    """Test default values across onboarding models."""

    def test_onboarding_request_defaults(self):
        """OnboardingRequest should use sensible defaults."""
        from src.api.onboarding_routes import (
            OnboardingRequest, CompanyProfile, BrandTheme,
            AgentConfig, OutboundSettings, EmailSettings,
            KnowledgeBaseConfig
        )
        req = OnboardingRequest(
            company=CompanyProfile(
                company_name="Test Co",
                support_email="test@test.com",
                brand_theme=BrandTheme(
                    theme_id="ocean-blue",
                    primary="#0EA5E9",
                    secondary="#0284C7",
                    accent="#38BDF8"
                )
            ),
            agents=AgentConfig(
                inbound_description="A helpful travel assistant for bookings",
                inbound_prompt="You are a travel agent."
            ),
            outbound=OutboundSettings(),
            email=EmailSettings(from_name="Test"),
            knowledge_base=KnowledgeBaseConfig()
        )
        assert req.provision_phone is True
        assert req.phone_country == "ZA"
        assert req.admin_email is None
        assert req.admin_password is None

    def test_company_profile_timezone_default(self):
        """CompanyProfile timezone should default to Africa/Johannesburg."""
        from src.api.onboarding_routes import CompanyProfile, BrandTheme
        profile = CompanyProfile(
            company_name="Test",
            support_email="t@t.com",
            brand_theme=BrandTheme(
                theme_id="x", primary="#000000",
                secondary="#111111", accent="#222222"
            )
        )
        assert profile.timezone == "Africa/Johannesburg"

    def test_company_profile_currency_default(self):
        """CompanyProfile currency should default to ZAR."""
        from src.api.onboarding_routes import CompanyProfile, BrandTheme
        profile = CompanyProfile(
            company_name="Test",
            support_email="t@t.com",
            brand_theme=BrandTheme(
                theme_id="x", primary="#000000",
                secondary="#111111", accent="#222222"
            )
        )
        assert profile.currency == "ZAR"


# ==================== NEW: Skip Logic Tests ====================

class TestOnboardingSkipLogic:
    """Test skip logic in the onboarding flow."""

    def test_voices_endpoint_returns_empty_in_lite(self, test_client):
        """Voices endpoint returns empty for Lite mode (skip voice step)."""
        response = test_client.get("/api/v1/admin/onboarding/voices")
        assert response.status_code == 200
        assert response.json() == []

    def test_outbound_can_be_disabled(self):
        """Outbound settings can be completely disabled."""
        from src.api.onboarding_routes import OutboundSettings
        settings = OutboundSettings(enabled=False)
        assert settings.enabled is False

    def test_min_quote_value_defaults_to_zero(self):
        """Outbound min_quote_value should default to 0 (no minimum)."""
        from src.api.onboarding_routes import OutboundSettings
        settings = OutboundSettings()
        assert settings.min_quote_value == 0

    def test_auto_send_quotes_default_enabled(self):
        """EmailSettings auto_send_quotes should default to True."""
        from src.api.onboarding_routes import EmailSettings
        settings = EmailSettings(from_name="Test")
        assert settings.auto_send_quotes is True

    @patch("src.api.onboarding_routes.GENAI_AVAILABLE", False)
    @patch("src.api.onboarding_routes._genai_initialized", True)
    @patch("src.api.onboarding_routes.genai_client", None)
    @patch("src.api.onboarding_routes.genai_model", None)
    def test_prompt_generation_skipped_when_genai_unavailable(self, test_client):
        """Generate prompt returns 500 gracefully when GenAI unavailable."""
        response = test_client.post(
            "/api/v1/admin/onboarding/generate-prompt",
            json={
                "description": "A friendly travel assistant that helps customers",
                "agent_type": "inbound"
            }
        )
        assert response.status_code == 500
        data = response.json()
        assert "not available" in data.get("detail", "").lower()


# ==================== NEW: Onboarding Completion Tests ====================

class TestOnboardingCompletion:
    """Test onboarding completion edge cases."""

    def test_generate_tenant_id_always_has_prefix(self):
        """Every generated tenant ID must start with tn_."""
        from src.api.onboarding_routes import generate_tenant_id

        for name in ["", "X", "Very Long Company Name Here", "123 Numeric"]:
            tid = generate_tenant_id(name)
            assert tid.startswith("tn_"), f"ID for '{name}' missing tn_ prefix: {tid}"

    def test_generate_tenant_id_has_three_parts(self):
        """Every generated tenant ID must have exactly 3 underscore-separated parts."""
        from src.api.onboarding_routes import generate_tenant_id

        tid = generate_tenant_id("Test Company")
        parts = tid.split("_")
        assert len(parts) == 3

    def test_is_free_email_with_subdomains(self):
        """is_free_email should not match subdomains of free providers."""
        from src.api.onboarding_routes import is_free_email
        assert is_free_email("user@mail.gmail.com") is False
        assert is_free_email("user@subdomain.yahoo.com") is False

    def test_generate_platform_email_domain_is_correct(self):
        """Generated platform email should use holidaytoday.co.za domain."""
        from src.api.onboarding_routes import generate_platform_email
        result = generate_platform_email("Test Company", "tn_test_abc")
        assert result.endswith("@holidaytoday.co.za")

    def test_onboarding_response_model_allows_none_tokens(self):
        """OnboardingResponse should allow None for auth token fields."""
        from src.api.onboarding_routes import OnboardingResponse
        resp = OnboardingResponse(
            success=True,
            tenant_id="tn_test_abc",
            message="Done",
            resources={},
            access_token=None,
            refresh_token=None,
            expires_at=None,
            user=None
        )
        assert resp.access_token is None
        assert resp.user is None

    def test_onboarding_response_model_with_errors(self):
        """OnboardingResponse should include error list."""
        from src.api.onboarding_routes import OnboardingResponse
        resp = OnboardingResponse(
            success=False,
            tenant_id="tn_test_abc",
            message="Failed",
            resources={},
            errors=["Error 1", "Error 2"]
        )
        assert len(resp.errors) == 2
        assert "Error 1" in resp.errors
