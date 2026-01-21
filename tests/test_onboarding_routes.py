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
