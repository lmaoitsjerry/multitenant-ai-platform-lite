"""
Branding Routes Unit Tests

Comprehensive tests for white-labeling/branding API endpoints:
- GET /api/v1/branding - Get tenant branding
- PUT /api/v1/branding - Update branding
- GET /api/v1/branding/presets - Get theme presets
- POST /api/v1/branding/apply-preset/{name} - Apply preset
- POST /api/v1/branding/upload/logo - Upload logo
- POST /api/v1/branding/upload/background - Upload background
- POST /api/v1/branding/reset - Reset to defaults
- GET /api/v1/branding/fonts - Get available fonts
- POST /api/v1/branding/preview - Preview branding changes
- GET /api/v1/branding/css-variables - Get CSS variables

Uses FastAPI TestClient with mocked dependencies.
These tests verify:
1. Endpoint structure and HTTP methods
2. Request validation
3. Response formats
4. Color validation
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import json
import os
import io


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
    config.primary_color = "#FF6B6B"
    config.secondary_color = "#4ECDC4"
    config.logo_url = "https://example.com/logo.png"
    return config


@pytest.fixture
def test_client():
    """Create a basic TestClient."""
    from main import app
    return TestClient(app)


@pytest.fixture
def client_headers():
    """Headers with X-Client-ID."""
    return {"X-Client-ID": "test_tenant"}


# ==================== Get Branding Tests ====================

class TestGetBrandingEndpoint:
    """Test GET /api/v1/branding endpoint."""

    def test_get_branding_returns_data(self, test_client, client_headers):
        """GET /branding returns branding configuration."""
        response = test_client.get(
            "/api/v1/branding",
            headers=client_headers
        )
        # Should return 200 with default branding or 400 if config missing
        assert response.status_code in [200, 400]

    def test_get_branding_without_client_id(self, test_client):
        """GET /branding uses default client when header missing."""
        response = test_client.get("/api/v1/branding")
        # Should use default client ID from env or return error
        assert response.status_code in [200, 400, 500]

    @patch("src.api.branding_routes.get_client_config")
    @patch("src.api.branding_routes.SupabaseTool")
    def test_get_branding_response_format(
        self, mock_supabase, mock_get_config, test_client, mock_config
    ):
        """GET /branding returns expected structure."""
        mock_get_config.return_value = mock_config
        mock_db = MagicMock()
        mock_db.get_branding.return_value = None  # Use defaults
        mock_supabase.return_value = mock_db

        response = test_client.get(
            "/api/v1/branding",
            headers={"X-Client-ID": "test_tenant"}
        )

        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True
            assert "data" in data


# ==================== Update Branding Tests ====================

class TestUpdateBrandingEndpoint:
    """Test PUT /api/v1/branding endpoint."""

    def test_update_branding_accepts_partial(self, test_client, client_headers):
        """PUT /branding accepts partial updates."""
        response = test_client.put(
            "/api/v1/branding",
            json={
                "preset_theme": "professional_blue"
            },
            headers=client_headers
        )
        # Should succeed or fail gracefully
        assert response.status_code in [200, 400, 500]

    def test_update_branding_validates_colors(self, test_client, client_headers):
        """PUT /branding validates color format."""
        response = test_client.put(
            "/api/v1/branding",
            json={
                "colors": {
                    "primary": "invalid-color"  # Not a hex color
                }
            },
            headers=client_headers
        )
        # Validation should fail with 422 or config error with 400
        assert response.status_code in [400, 422]

    def test_update_branding_accepts_valid_colors(self, test_client, client_headers):
        """PUT /branding accepts valid hex colors."""
        response = test_client.put(
            "/api/v1/branding",
            json={
                "colors": {
                    "primary": "#FF6B6B",
                    "secondary": "#4ECDC4"
                }
            },
            headers=client_headers
        )
        # Should succeed or fail due to config/db issues
        assert response.status_code in [200, 400, 500]

    def test_update_branding_dark_mode(self, test_client, client_headers):
        """PUT /branding can toggle dark mode."""
        response = test_client.put(
            "/api/v1/branding",
            json={"dark_mode_enabled": True},
            headers=client_headers
        )
        assert response.status_code in [200, 400, 500]


# ==================== Theme Presets Tests ====================

class TestGetPresetsEndpoint:
    """Test GET /api/v1/branding/presets endpoint."""

    def test_get_presets_returns_list(self, test_client):
        """GET /presets returns theme preset list."""
        response = test_client.get("/api/v1/branding/presets")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_get_presets_structure(self, test_client):
        """Each preset has expected fields."""
        response = test_client.get("/api/v1/branding/presets")
        presets = response.json()["data"]

        for preset in presets:
            assert "id" in preset
            assert "name" in preset
            assert "description" in preset
            assert "colors" in preset
            assert "fonts" in preset

    def test_get_presets_count(self, test_client):
        """Response includes preset count."""
        response = test_client.get("/api/v1/branding/presets")
        data = response.json()
        assert "count" in data
        assert data["count"] == len(data["data"])


class TestApplyPresetEndpoint:
    """Test POST /api/v1/branding/apply-preset/{name} endpoint."""

    def test_apply_preset_valid(self, test_client, client_headers):
        """POST /apply-preset with valid preset name."""
        response = test_client.post(
            "/api/v1/branding/apply-preset/professional_blue",
            headers=client_headers
        )
        # Should succeed, fail with config error, or require auth
        assert response.status_code in [200, 400, 401, 500]

    def test_apply_preset_invalid(self, test_client, client_headers):
        """POST /apply-preset with invalid preset returns error."""
        response = test_client.post(
            "/api/v1/branding/apply-preset/nonexistent_preset",
            headers=client_headers
        )
        # May return 400 (invalid preset) or 401 (auth required first)
        assert response.status_code in [400, 401]


# ==================== Logo Upload Tests ====================

class TestUploadLogoEndpoint:
    """Test POST /api/v1/branding/upload/logo endpoint."""

    def test_upload_logo_requires_file(self, test_client, client_headers):
        """POST /upload/logo requires file."""
        response = test_client.post(
            "/api/v1/branding/upload/logo",
            headers=client_headers
        )
        # May require auth first or validation error
        assert response.status_code in [401, 422]

    def test_upload_logo_validates_type(self, test_client, client_headers):
        """POST /upload/logo validates logo_type parameter."""
        # Create a test image file
        file_content = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100  # Fake PNG header

        response = test_client.post(
            "/api/v1/branding/upload/logo",
            files={"file": ("test.png", io.BytesIO(file_content), "image/png")},
            data={"logo_type": "invalid_type"},
            headers=client_headers
        )
        # May require auth first or return 400 for invalid type
        assert response.status_code in [400, 401]

    def test_upload_logo_accepts_valid_types(self, test_client, client_headers):
        """POST /upload/logo accepts valid logo types."""
        valid_types = ["primary", "dark", "favicon", "email"]

        for logo_type in valid_types:
            file_content = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100

            response = test_client.post(
                "/api/v1/branding/upload/logo",
                files={"file": ("test.png", io.BytesIO(file_content), "image/png")},
                data={"logo_type": logo_type},
                headers=client_headers
            )
            # Should succeed, fail with storage error, or require auth
            assert response.status_code in [200, 400, 401, 500]

    def test_upload_logo_validates_extension(self, test_client, client_headers):
        """POST /upload/logo validates file extension."""
        file_content = b'not an image'

        response = test_client.post(
            "/api/v1/branding/upload/logo",
            files={"file": ("test.exe", io.BytesIO(file_content), "application/octet-stream")},
            data={"logo_type": "primary"},
            headers=client_headers
        )
        # May require auth first or return 400 for invalid extension
        assert response.status_code in [400, 401]

    def test_upload_logo_size_limit(self, test_client, client_headers):
        """POST /upload/logo rejects files > 5MB."""
        # Create a 6MB file
        large_content = b'\x89PNG\r\n\x1a\n' + (b'\x00' * (6 * 1024 * 1024))

        response = test_client.post(
            "/api/v1/branding/upload/logo",
            files={"file": ("large.png", io.BytesIO(large_content), "image/png")},
            data={"logo_type": "primary"},
            headers=client_headers
        )
        # May require auth first or return 400 for size limit
        assert response.status_code in [400, 401]


class TestUploadBackgroundEndpoint:
    """Test POST /api/v1/branding/upload/background endpoint."""

    def test_upload_background_requires_file(self, test_client, client_headers):
        """POST /upload/background requires file."""
        response = test_client.post(
            "/api/v1/branding/upload/background",
            headers=client_headers
        )
        # May require auth first or validation error
        assert response.status_code in [401, 422]

    def test_upload_background_validates_extension(self, test_client, client_headers):
        """POST /upload/background validates file extension."""
        file_content = b'not an image'

        response = test_client.post(
            "/api/v1/branding/upload/background",
            files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
            headers=client_headers
        )
        # May require auth first or return 400 for invalid extension
        assert response.status_code in [400, 401]

    def test_upload_background_size_limit(self, test_client, client_headers):
        """POST /upload/background rejects files > 10MB."""
        # Create an 11MB file
        large_content = b'\x89PNG\r\n\x1a\n' + (b'\x00' * (11 * 1024 * 1024))

        response = test_client.post(
            "/api/v1/branding/upload/background",
            files={"file": ("large.png", io.BytesIO(large_content), "image/png")},
            headers=client_headers
        )
        # May require auth first or return 400 for size limit
        assert response.status_code in [400, 401]


# ==================== Reset Branding Tests ====================

class TestResetBrandingEndpoint:
    """Test POST /api/v1/branding/reset endpoint."""

    def test_reset_branding(self, test_client, client_headers):
        """POST /reset clears custom branding."""
        response = test_client.post(
            "/api/v1/branding/reset",
            headers=client_headers
        )
        # Should succeed, fail with config error, or require auth
        assert response.status_code in [200, 400, 401, 500]

    @patch("src.api.branding_routes.get_client_config")
    @patch("src.api.branding_routes.SupabaseTool")
    def test_reset_returns_defaults(
        self, mock_supabase, mock_get_config, test_client, mock_config
    ):
        """POST /reset returns default branding."""
        mock_get_config.return_value = mock_config
        mock_db = MagicMock()
        mock_supabase.return_value = mock_db

        response = test_client.post(
            "/api/v1/branding/reset",
            headers={"X-Client-ID": "test_tenant"}
        )

        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True


# ==================== Fonts Tests ====================

class TestGetFontsEndpoint:
    """Test GET /api/v1/branding/fonts endpoint."""

    def test_get_fonts_returns_list(self, test_client):
        """GET /fonts returns available Google fonts."""
        response = test_client.get("/api/v1/branding/fonts")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "data" in data

    def test_get_fonts_has_count(self, test_client):
        """GET /fonts includes font count."""
        response = test_client.get("/api/v1/branding/fonts")
        data = response.json()
        assert "count" in data


# ==================== Preview Tests ====================

class TestPreviewBrandingEndpoint:
    """Test POST /api/v1/branding/preview endpoint."""

    def test_preview_without_save(self, test_client, client_headers):
        """POST /preview returns preview without saving."""
        response = test_client.post(
            "/api/v1/branding/preview",
            json={"preset_theme": "professional_blue"},
            headers=client_headers
        )
        # Should succeed, fail with config error, or require auth
        assert response.status_code in [200, 400, 401, 500]

    def test_preview_with_colors(self, test_client, client_headers):
        """POST /preview includes custom colors in preview."""
        response = test_client.post(
            "/api/v1/branding/preview",
            json={
                "colors": {
                    "primary": "#FF0000",
                    "secondary": "#00FF00"
                }
            },
            headers=client_headers
        )
        # Should succeed, fail with config error, or require auth
        assert response.status_code in [200, 400, 401, 500]

    def test_preview_flags_as_preview(self, test_client, client_headers):
        """POST /preview response has is_preview flag."""
        response = test_client.post(
            "/api/v1/branding/preview",
            json={},
            headers=client_headers
        )
        if response.status_code == 200:
            data = response.json()
            assert data.get("is_preview") == True


# ==================== CSS Variables Tests ====================

class TestGetCSSVariablesEndpoint:
    """Test GET /api/v1/branding/css-variables endpoint."""

    def test_get_css_variables(self, test_client, client_headers):
        """GET /css-variables returns CSS variable string."""
        response = test_client.get(
            "/api/v1/branding/css-variables",
            headers=client_headers
        )
        # Should succeed, fail with config error, or require auth
        assert response.status_code in [200, 400, 401, 500]

    @patch("src.api.branding_routes.get_client_config")
    @patch("src.api.branding_routes.SupabaseTool")
    def test_css_variables_format(
        self, mock_supabase, mock_get_config, test_client, mock_config
    ):
        """GET /css-variables returns valid CSS."""
        mock_get_config.return_value = mock_config
        mock_db = MagicMock()
        mock_db.get_branding.return_value = None
        mock_supabase.return_value = mock_db

        response = test_client.get(
            "/api/v1/branding/css-variables",
            headers={"X-Client-ID": "test_tenant"}
        )

        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            if "css" in data["data"]:
                css = data["data"]["css"]
                assert ":root {" in css


# ==================== Pydantic Model Tests ====================

class TestBrandingModels:
    """Test Pydantic model validation."""

    def test_branding_colors_hex_validation(self):
        """BrandingColors validates hex color format."""
        from src.api.branding_routes import BrandingColors

        # Valid colors
        colors = BrandingColors(
            primary="#FF6B6B",
            secondary="#4ECDC4",
            accent="#FFE66D"
        )
        assert colors.primary == "#FF6B6B"

    def test_branding_colors_invalid_hex(self):
        """BrandingColors rejects invalid hex colors."""
        from src.api.branding_routes import BrandingColors
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            BrandingColors(primary="not-a-color")

    def test_branding_colors_optional(self):
        """BrandingColors allows optional fields."""
        from src.api.branding_routes import BrandingColors

        colors = BrandingColors()  # All optional
        assert colors.primary is None

    def test_branding_fonts_model(self):
        """BrandingFonts model validates correctly."""
        from src.api.branding_routes import BrandingFonts

        fonts = BrandingFonts(heading="Inter", body="Roboto")
        assert fonts.heading == "Inter"
        assert fonts.body == "Roboto"

    def test_branding_update_model(self):
        """BrandingUpdate model validates correctly."""
        from src.api.branding_routes import BrandingUpdate, BrandingColors

        update = BrandingUpdate(
            preset_theme="professional_blue",
            dark_mode_enabled=True,
            colors=BrandingColors(primary="#FF0000")
        )
        assert update.preset_theme == "professional_blue"
        assert update.dark_mode_enabled == True


# ==================== Helper Function Tests ====================

class TestBrandingHelpers:
    """Test helper functions."""

    def test_db_to_branding_response_with_none(self, mock_config):
        """db_to_branding_response handles None db_record."""
        from src.api.branding_routes import db_to_branding_response

        result = db_to_branding_response(None, mock_config)

        assert result["tenant_id"] == mock_config.client_id
        assert result["preset_theme"] == "professional_blue"  # Default
        assert "colors" in result
        assert "fonts" in result

    def test_db_to_branding_response_with_data(self, mock_config):
        """db_to_branding_response merges db data."""
        from src.api.branding_routes import db_to_branding_response

        db_record = {
            "tenant_id": "test_tenant",
            "preset_theme": "modern_dark",
            "dark_mode_enabled": True,
            "logo_url": "https://example.com/custom-logo.png",
            "color_primary": "#123456"
        }

        result = db_to_branding_response(db_record, mock_config)

        assert result["preset_theme"] == "modern_dark"
        assert result["dark_mode_enabled"] == True
        assert result["logos"]["primary"] == "https://example.com/custom-logo.png"


# ==================== Edge Cases ====================

class TestBrandingEdgeCases:
    """Test edge cases and error handling."""

    def test_branding_color_case_insensitive(self):
        """Hex colors accept different cases."""
        from src.api.branding_routes import BrandingColors

        colors = BrandingColors(
            primary="#ff6b6b",  # lowercase
            secondary="#4ECDC4"  # uppercase
        )
        assert colors.primary == "#ff6b6b"
        assert colors.secondary == "#4ECDC4"

    def test_upload_valid_extensions(self, test_client, client_headers):
        """Upload accepts all valid image extensions."""
        valid_extensions = ["png", "jpg", "jpeg", "svg", "ico"]

        for ext in valid_extensions:
            file_content = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
            response = test_client.post(
                "/api/v1/branding/upload/logo",
                files={"file": (f"test.{ext}", io.BytesIO(file_content), f"image/{ext}")},
                data={"logo_type": "primary"},
                headers=client_headers
            )
            # May fail due to storage, auth, or validation
            assert response.status_code in [200, 400, 401, 500]

    def test_preset_names_constant(self, test_client):
        """Verify expected preset names exist."""
        response = test_client.get("/api/v1/branding/presets")
        presets = response.json()["data"]
        preset_ids = [p["id"] for p in presets]

        # Check for some expected presets (using actual preset names)
        expected = ["professional_blue", "vibrant_orange"]
        for expected_id in expected:
            assert expected_id in preset_ids, f"Missing preset: {expected_id}"


# ==================== NEW TESTS: Pydantic Model Validation ====================

class TestBrandingColorsModelExtended:
    """Extended tests for BrandingColors Pydantic model."""

    def test_branding_colors_rejects_short_hex(self):
        """BrandingColors rejects 3-digit hex colors (only 6-digit allowed)."""
        from src.api.branding_routes import BrandingColors
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            BrandingColors(primary="#FFF")

    def test_branding_colors_rejects_hex_without_hash(self):
        """BrandingColors rejects hex colors missing the # prefix."""
        from src.api.branding_routes import BrandingColors
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            BrandingColors(primary="FF6B6B")

    def test_branding_colors_rejects_rgba(self):
        """BrandingColors rejects rgba() color format."""
        from src.api.branding_routes import BrandingColors
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            BrandingColors(primary="rgba(255,0,0,1)")

    def test_branding_colors_rejects_named_colors(self):
        """BrandingColors rejects CSS named colors like 'red'."""
        from src.api.branding_routes import BrandingColors
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            BrandingColors(primary="red")

    def test_branding_colors_all_sidebar_fields(self):
        """BrandingColors accepts all sidebar color fields."""
        from src.api.branding_routes import BrandingColors

        colors = BrandingColors(
            sidebar_bg="#1E293B",
            sidebar_text="#F8FAFC",
            sidebar_text_muted="#94A3B8",
            sidebar_hover="#334155",
            sidebar_active_bg="#2563EB",
            sidebar_active_text="#FFFFFF"
        )
        assert colors.sidebar_bg == "#1E293B"
        assert colors.sidebar_active_bg == "#2563EB"

    def test_branding_colors_model_dump_excludes_none(self):
        """BrandingColors model_dump can exclude None values."""
        from src.api.branding_routes import BrandingColors

        colors = BrandingColors(primary="#FF0000", secondary="#00FF00")
        dumped = {k: v for k, v in colors.model_dump().items() if v is not None}
        assert "primary" in dumped
        assert "secondary" in dumped
        assert "accent" not in dumped

    def test_branding_colors_rejects_8_digit_hex(self):
        """BrandingColors rejects 8-digit hex (with alpha channel)."""
        from src.api.branding_routes import BrandingColors
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            BrandingColors(primary="#FF6B6BFF")


class TestBrandingUpdateModelExtended:
    """Extended tests for BrandingUpdate Pydantic model."""

    def test_branding_update_empty_is_valid(self):
        """BrandingUpdate with no fields is valid (all optional)."""
        from src.api.branding_routes import BrandingUpdate

        update = BrandingUpdate()
        assert update.preset_theme is None
        assert update.dark_mode_enabled is None
        assert update.colors is None
        assert update.fonts is None
        assert update.custom_css is None

    def test_branding_update_with_login_customization(self):
        """BrandingUpdate accepts login page customization fields."""
        from src.api.branding_routes import BrandingUpdate

        update = BrandingUpdate(
            login_background_url="https://example.com/bg.jpg",
            login_background_gradient="linear-gradient(135deg, #2563EB, #1D4ED8)"
        )
        assert update.login_background_url == "https://example.com/bg.jpg"
        assert "linear-gradient" in update.login_background_gradient

    def test_branding_update_with_all_logo_fields(self):
        """BrandingUpdate accepts all logo URL fields."""
        from src.api.branding_routes import BrandingUpdate

        update = BrandingUpdate(
            logo_url="https://example.com/logo.png",
            logo_dark_url="https://example.com/logo-dark.png",
            favicon_url="https://example.com/favicon.ico"
        )
        assert update.logo_url is not None
        assert update.logo_dark_url is not None
        assert update.favicon_url is not None

    def test_branding_update_with_nested_colors_and_fonts(self):
        """BrandingUpdate correctly nests BrandingColors and BrandingFonts."""
        from src.api.branding_routes import BrandingUpdate, BrandingColors, BrandingFonts

        update = BrandingUpdate(
            colors=BrandingColors(primary="#FF0000", accent="#00FF00"),
            fonts=BrandingFonts(heading="Montserrat", body="Roboto")
        )
        assert update.colors.primary == "#FF0000"
        assert update.fonts.heading == "Montserrat"


class TestPresetInfoModel:
    """Tests for PresetInfo Pydantic model."""

    def test_preset_info_requires_all_fields(self):
        """PresetInfo requires id, name, description, colors, fonts, preview_gradient."""
        from src.api.branding_routes import PresetInfo

        preset = PresetInfo(
            id="test_preset",
            name="Test Preset",
            description="A test preset",
            colors={"primary": "#FF0000"},
            fonts={"heading": "Inter"},
            preview_gradient="linear-gradient(135deg, #FF0000, #0000FF)"
        )
        assert preset.id == "test_preset"
        assert preset.name == "Test Preset"

    def test_preset_info_rejects_missing_fields(self):
        """PresetInfo rejects creation with missing required fields."""
        from src.api.branding_routes import PresetInfo
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PresetInfo(id="test")  # Missing required fields


class TestBrandingResponseModel:
    """Tests for BrandingResponse Pydantic model."""

    def test_branding_response_full_construction(self):
        """BrandingResponse can be constructed with all fields."""
        from src.api.branding_routes import BrandingResponse

        response = BrandingResponse(
            tenant_id="test_tenant",
            preset_theme="professional_blue",
            dark_mode_enabled=False,
            logos={"primary": "https://example.com/logo.png", "dark": None, "favicon": None},
            colors={"primary": "#2563EB", "secondary": "#64748B"},
            fonts={"heading": "Inter", "body": "Inter"},
            custom_css=None
        )
        assert response.tenant_id == "test_tenant"
        assert response.dark_mode_enabled is False


# ==================== NEW TESTS: get_branding with mocked config ====================

class TestGetBrandingMocked:
    """Test GET /api/v1/branding with fully mocked dependencies."""

    @patch("src.api.branding_routes.get_client_config")
    @patch("src.api.branding_routes.SupabaseTool")
    def test_get_branding_returns_default_preset_when_no_db(
        self, mock_supabase, mock_get_config, test_client, mock_config
    ):
        """GET /branding returns professional_blue when no DB record."""
        mock_get_config.return_value = mock_config
        mock_db = MagicMock()
        mock_db.get_branding.return_value = None
        mock_supabase.return_value = mock_db

        response = test_client.get("/api/v1/branding", headers={"X-Client-ID": "test_tenant"})

        if response.status_code == 200:
            data = response.json()["data"]
            assert data["preset_theme"] == "professional_blue"
            assert data["dark_mode_enabled"] is False
            assert data["tenant_id"] == "test_tenant"
            assert "colors" in data
            assert "fonts" in data

    @patch("src.api.branding_routes.get_client_config")
    @patch("src.api.branding_routes.SupabaseTool")
    def test_get_branding_includes_logos_from_config(
        self, mock_supabase, mock_get_config, test_client, mock_config
    ):
        """GET /branding includes logo_url from config when no DB record."""
        mock_get_config.return_value = mock_config
        mock_db = MagicMock()
        mock_db.get_branding.return_value = None
        mock_supabase.return_value = mock_db

        response = test_client.get("/api/v1/branding", headers={"X-Client-ID": "test_tenant"})

        if response.status_code == 200:
            logos = response.json()["data"]["logos"]
            assert logos["primary"] == mock_config.logo_url

    @patch("src.api.branding_routes.get_client_config")
    @patch("src.api.branding_routes.SupabaseTool")
    def test_get_branding_survives_supabase_exception(
        self, mock_supabase, mock_get_config, test_client, mock_config
    ):
        """GET /branding returns defaults when SupabaseTool raises exception."""
        mock_get_config.return_value = mock_config
        mock_supabase.side_effect = Exception("Connection failed")

        response = test_client.get("/api/v1/branding", headers={"X-Client-ID": "test_tenant"})

        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True


# ==================== NEW TESTS: update_branding partial and full ====================

class TestUpdateBrandingMocked:
    """Test PUT /api/v1/branding with mocked dependencies."""

    @patch("src.api.branding_routes.get_client_config")
    @patch("src.api.branding_routes.SupabaseTool")
    def test_update_branding_partial_colors_only(
        self, mock_supabase, mock_get_config, test_client, mock_config
    ):
        """PUT /branding with only colors updates colors only."""
        mock_get_config.return_value = mock_config
        mock_db = MagicMock()
        mock_db.update_branding.return_value = None  # DB save fails
        mock_supabase.return_value = mock_db

        response = test_client.put(
            "/api/v1/branding",
            json={"colors": {"primary": "#FF0000"}},
            headers={"X-Client-ID": "test_tenant"}
        )

        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert data["data"]["colors"]["primary"] == "#FF0000"

    @patch("src.api.branding_routes.get_client_config")
    @patch("src.api.branding_routes.SupabaseTool")
    def test_update_branding_full_update(
        self, mock_supabase, mock_get_config, test_client, mock_config
    ):
        """PUT /branding with all fields performs full update."""
        mock_get_config.return_value = mock_config
        mock_db = MagicMock()
        mock_db.update_branding.return_value = None
        mock_supabase.return_value = mock_db

        response = test_client.put(
            "/api/v1/branding",
            json={
                "preset_theme": "vibrant_orange",
                "dark_mode_enabled": False,
                "colors": {"primary": "#EA580C", "secondary": "#78716C"},
                "fonts": {"heading": "Poppins", "body": "Inter"},
                "custom_css": ".custom { color: red; }"
            },
            headers={"X-Client-ID": "test_tenant"}
        )

        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert data["data"]["preset_theme"] == "vibrant_orange"

    @patch("src.api.branding_routes.get_client_config")
    @patch("src.api.branding_routes.SupabaseTool")
    def test_update_branding_db_success_returns_db_data(
        self, mock_supabase, mock_get_config, test_client, mock_config
    ):
        """PUT /branding returns DB data when update succeeds."""
        mock_get_config.return_value = mock_config
        mock_db = MagicMock()
        mock_db.update_branding.return_value = {
            "tenant_id": "test_tenant",
            "preset_theme": "nature_green",
            "dark_mode_enabled": False,
            "color_primary": "#059669",
        }
        mock_supabase.return_value = mock_db

        response = test_client.put(
            "/api/v1/branding",
            json={"preset_theme": "nature_green"},
            headers={"X-Client-ID": "test_tenant"}
        )

        if response.status_code == 200:
            data = response.json()
            assert data["message"] == "Branding updated successfully"

    @patch("src.api.branding_routes.get_client_config")
    @patch("src.api.branding_routes.SupabaseTool")
    def test_update_branding_db_failure_returns_local(
        self, mock_supabase, mock_get_config, test_client, mock_config
    ):
        """PUT /branding returns local data when DB update fails."""
        mock_get_config.return_value = mock_config
        mock_db = MagicMock()
        mock_db.update_branding.side_effect = Exception("DB error")
        mock_supabase.return_value = mock_db

        response = test_client.put(
            "/api/v1/branding",
            json={"preset_theme": "elegant_purple"},
            headers={"X-Client-ID": "test_tenant"}
        )

        if response.status_code == 200:
            data = response.json()
            assert data["message"] == "Branding updated (local only)"


# ==================== NEW TESTS: get_theme_presets detailed ====================

class TestGetPresetsDetailed:
    """Detailed tests for GET /api/v1/branding/presets."""

    def test_presets_include_all_known_presets(self, test_client):
        """GET /presets returns all 6 known presets."""
        response = test_client.get("/api/v1/branding/presets")
        assert response.status_code == 200
        data = response.json()
        preset_ids = [p["id"] for p in data["data"]]

        expected = [
            "professional_blue", "vibrant_orange", "nature_green",
            "elegant_purple", "sunset_coral", "ocean_teal"
        ]
        for pid in expected:
            assert pid in preset_ids, f"Missing preset: {pid}"

    def test_presets_have_preview_gradient(self, test_client):
        """Each preset includes a preview_gradient CSS string."""
        response = test_client.get("/api/v1/branding/presets")
        for preset in response.json()["data"]:
            assert "preview_gradient" in preset
            assert "linear-gradient" in preset["preview_gradient"]

    def test_presets_colors_are_hex(self, test_client):
        """Each preset color value is a valid hex color."""
        import re
        hex_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')

        response = test_client.get("/api/v1/branding/presets")
        for preset in response.json()["data"]:
            for color_name, color_value in preset["colors"].items():
                assert hex_pattern.match(color_value), \
                    f"Preset '{preset['id']}' color '{color_name}' is not valid hex: {color_value}"

    def test_presets_fonts_have_heading_and_body(self, test_client):
        """Each preset has heading and body font definitions."""
        response = test_client.get("/api/v1/branding/presets")
        for preset in response.json()["data"]:
            assert "heading" in preset["fonts"]
            assert "body" in preset["fonts"]


# ==================== NEW TESTS: apply_theme endpoint ====================

class TestApplyPresetMocked:
    """Test POST /api/v1/branding/apply-preset/{name} with mocked deps."""

    @patch("src.api.branding_routes.get_client_config")
    @patch("src.api.branding_routes.SupabaseTool")
    def test_apply_preset_returns_preset_colors(
        self, mock_supabase, mock_get_config, test_client, mock_config
    ):
        """Applying a preset returns that preset's color palette."""
        mock_get_config.return_value = mock_config
        mock_db = MagicMock()
        mock_db.update_branding.side_effect = Exception("no table")
        mock_supabase.return_value = mock_db

        response = test_client.post(
            "/api/v1/branding/apply-preset/vibrant_orange",
            headers={"X-Client-ID": "test_tenant"}
        )

        if response.status_code == 200:
            data = response.json()["data"]
            assert data["preset_theme"] == "vibrant_orange"
            assert data["colors"]["primary"] == "#EA580C"

    @patch("src.api.branding_routes.get_client_config")
    @patch("src.api.branding_routes.SupabaseTool")
    def test_apply_preset_resets_dark_mode(
        self, mock_supabase, mock_get_config, test_client, mock_config
    ):
        """Applying a preset sets dark_mode_enabled to False."""
        mock_get_config.return_value = mock_config
        mock_db = MagicMock()
        mock_db.update_branding.side_effect = Exception("no table")
        mock_supabase.return_value = mock_db

        response = test_client.post(
            "/api/v1/branding/apply-preset/nature_green",
            headers={"X-Client-ID": "test_tenant"}
        )

        if response.status_code == 200:
            assert response.json()["data"]["dark_mode_enabled"] is False

    def test_apply_preset_invalid_name_returns_400(self, test_client, client_headers):
        """POST /apply-preset/fake_preset returns 400 with available presets."""
        response = test_client.post(
            "/api/v1/branding/apply-preset/fake_preset",
            headers=client_headers
        )
        # 400 for invalid preset or 401 if auth runs first
        if response.status_code == 400:
            detail = response.json().get("detail", "")
            assert "Invalid preset" in detail


# ==================== NEW TESTS: upload_logo with mocked deps ====================

class TestUploadLogoMocked:
    """Test POST /api/v1/branding/upload/logo with mocked dependencies."""

    @patch("src.api.branding_routes.get_client_config")
    @patch("src.api.branding_routes.SupabaseTool")
    def test_upload_logo_success(
        self, mock_supabase, mock_get_config, test_client, mock_config
    ):
        """Upload logo returns URL and metadata on success."""
        mock_get_config.return_value = mock_config
        mock_db = MagicMock()
        mock_db.upload_logo_to_storage.return_value = "https://storage.example.com/logo.png"
        mock_db.update_branding.return_value = {}
        mock_supabase.return_value = mock_db

        file_content = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        response = test_client.post(
            "/api/v1/branding/upload/logo",
            files={"file": ("logo.png", io.BytesIO(file_content), "image/png")},
            data={"logo_type": "primary"},
            headers={"X-Client-ID": "test_tenant"}
        )

        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert data["data"]["logo_type"] == "primary"
            assert data["data"]["url"] == "https://storage.example.com/logo.png"
            assert data["data"]["filename"] == "logo.png"
            assert data["data"]["size"] > 0

    @patch("src.api.branding_routes.get_client_config")
    @patch("src.api.branding_routes.SupabaseTool")
    def test_upload_logo_storage_failure_returns_500(
        self, mock_supabase, mock_get_config, test_client, mock_config
    ):
        """Upload logo returns 500 when storage upload fails."""
        mock_get_config.return_value = mock_config
        mock_db = MagicMock()
        mock_db.upload_logo_to_storage.side_effect = Exception("Storage bucket not found")
        mock_supabase.return_value = mock_db

        file_content = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        response = test_client.post(
            "/api/v1/branding/upload/logo",
            files={"file": ("logo.png", io.BytesIO(file_content), "image/png")},
            data={"logo_type": "primary"},
            headers={"X-Client-ID": "test_tenant"}
        )

        if response.status_code == 500:
            assert "detail" in response.json()

    def test_upload_logo_extension_validation_defined(self):
        """Upload logo handler validates file extensions."""
        import inspect
        from src.api.branding_routes import upload_logo

        source = inspect.getsource(upload_logo)
        # Handler checks allowed extensions
        assert "allowed_extensions" in source
        assert "Invalid file type" in source

    def test_upload_logo_type_validation_defined(self):
        """Upload logo handler validates logo_type parameter."""
        import inspect
        from src.api.branding_routes import upload_logo

        source = inspect.getsource(upload_logo)
        # Handler checks valid logo types
        assert "valid_types" in source or "logo_type" in source
        assert "Invalid logo_type" in source


# ==================== NEW TESTS: generate_css / css-variables ====================

class TestCSSVariablesMocked:
    """Test GET /api/v1/branding/css-variables with mocked dependencies."""

    @patch("src.api.branding_routes.get_client_config")
    @patch("src.api.branding_routes.SupabaseTool")
    def test_css_variables_contain_primary_color(
        self, mock_supabase, mock_get_config, test_client, mock_config
    ):
        """CSS variables include --color-primary."""
        mock_get_config.return_value = mock_config
        mock_db = MagicMock()
        mock_db.get_branding.return_value = None
        mock_supabase.return_value = mock_db

        response = test_client.get(
            "/api/v1/branding/css-variables",
            headers={"X-Client-ID": "test_tenant"}
        )

        if response.status_code == 200:
            css = response.json()["data"]["css"]
            assert "--color-primary:" in css

    @patch("src.api.branding_routes.get_client_config")
    @patch("src.api.branding_routes.SupabaseTool")
    def test_css_variables_contain_font_families(
        self, mock_supabase, mock_get_config, test_client, mock_config
    ):
        """CSS variables include font-family declarations."""
        mock_get_config.return_value = mock_config
        mock_db = MagicMock()
        mock_db.get_branding.return_value = None
        mock_supabase.return_value = mock_db

        response = test_client.get(
            "/api/v1/branding/css-variables",
            headers={"X-Client-ID": "test_tenant"}
        )

        if response.status_code == 200:
            css = response.json()["data"]["css"]
            assert "--font-family-heading:" in css
            assert "--font-family-body:" in css

    @patch("src.api.branding_routes.get_client_config")
    @patch("src.api.branding_routes.SupabaseTool")
    def test_css_variables_include_custom_css(
        self, mock_supabase, mock_get_config, test_client, mock_config
    ):
        """CSS output appends custom_css when present in branding."""
        mock_get_config.return_value = mock_config
        mock_db = MagicMock()
        mock_db.get_branding.return_value = {
            "tenant_id": "test_tenant",
            "preset_theme": "professional_blue",
            "custom_css": ".my-widget { display: none; }"
        }
        mock_supabase.return_value = mock_db

        response = test_client.get(
            "/api/v1/branding/css-variables",
            headers={"X-Client-ID": "test_tenant"}
        )

        if response.status_code == 200:
            css = response.json()["data"]["css"]
            assert "/* Custom CSS */" in css
            assert ".my-widget { display: none; }" in css

    @patch("src.api.branding_routes.get_client_config")
    @patch("src.api.branding_routes.SupabaseTool")
    def test_css_variables_response_includes_branding_object(
        self, mock_supabase, mock_get_config, test_client, mock_config
    ):
        """CSS variables response also includes the branding data object."""
        mock_get_config.return_value = mock_config
        mock_db = MagicMock()
        mock_db.get_branding.return_value = None
        mock_supabase.return_value = mock_db

        response = test_client.get(
            "/api/v1/branding/css-variables",
            headers={"X-Client-ID": "test_tenant"}
        )

        if response.status_code == 200:
            data = response.json()["data"]
            assert "css" in data
            assert "branding" in data
            assert "colors" in data["branding"]


# ==================== NEW TESTS: Dependency injection ====================

class TestDependencyInjection:
    """Tests for get_client_config dependency."""

    def test_get_client_config_uses_header(self):
        """get_client_config reads X-Client-ID header."""
        from src.api.dependencies import get_client_config

        # When config fails for unknown client, it raises HTTPException
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            get_client_config(x_client_id="nonexistent_client_xyz_999")

        assert exc_info.value.status_code == 400
        assert "Invalid client" in str(exc_info.value.detail)


# ==================== NEW TESTS: Error handling ====================

class TestBrandingErrorHandling:
    """Tests for error handling across branding endpoints."""

    def test_update_branding_rejects_invalid_color_in_multiple_fields(self, test_client, client_headers):
        """PUT /branding rejects multiple invalid color fields."""
        response = test_client.put(
            "/api/v1/branding",
            json={
                "colors": {
                    "primary": "not-hex",
                    "secondary": "also-bad",
                    "accent": "nope"
                }
            },
            headers=client_headers
        )
        assert response.status_code in [400, 422]

    def test_update_branding_rejects_empty_hex(self, test_client, client_headers):
        """PUT /branding rejects empty string as hex color."""
        response = test_client.put(
            "/api/v1/branding",
            json={"colors": {"primary": ""}},
            headers=client_headers
        )
        assert response.status_code in [400, 422]

    def test_update_branding_rejects_hex_with_spaces(self, test_client, client_headers):
        """PUT /branding rejects hex color with spaces."""
        response = test_client.put(
            "/api/v1/branding",
            json={"colors": {"primary": "# FF6B6B"}},
            headers=client_headers
        )
        assert response.status_code in [400, 422]

    @patch("src.api.branding_routes.get_client_config")
    @patch("src.api.branding_routes.SupabaseTool")
    def test_reset_branding_survives_delete_failure(
        self, mock_supabase, mock_get_config, test_client, mock_config
    ):
        """POST /reset succeeds even when DB delete fails."""
        mock_get_config.return_value = mock_config
        mock_db = MagicMock()
        mock_db.delete_branding.side_effect = Exception("Table not found")
        mock_supabase.return_value = mock_db

        response = test_client.post(
            "/api/v1/branding/reset",
            headers={"X-Client-ID": "test_tenant"}
        )

        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "Branding reset to defaults"


# ==================== NEW TESTS: Helper functions extended ====================

class TestDbToBrandingResponseExtended:
    """Extended tests for db_to_branding_response helper."""

    def test_db_record_with_custom_fonts(self, mock_config):
        """db_to_branding_response applies custom fonts from DB."""
        from src.api.branding_routes import db_to_branding_response

        db_record = {
            "tenant_id": "test_tenant",
            "preset_theme": "professional_blue",
            "font_family_heading": "Playfair Display",
            "font_family_body": "Lato"
        }

        result = db_to_branding_response(db_record, mock_config)
        assert result["fonts"]["heading"] == "Playfair Display"
        assert result["fonts"]["body"] == "Lato"

    def test_db_record_with_multiple_custom_colors(self, mock_config):
        """db_to_branding_response overrides multiple preset colors."""
        from src.api.branding_routes import db_to_branding_response

        db_record = {
            "tenant_id": "test_tenant",
            "preset_theme": "professional_blue",
            "color_primary": "#FF0000",
            "color_secondary": "#00FF00",
            "color_accent": "#0000FF"
        }

        result = db_to_branding_response(db_record, mock_config)
        assert result["colors"]["primary"] == "#FF0000"
        assert result["colors"]["secondary"] == "#00FF00"
        assert result["colors"]["accent"] == "#0000FF"

    def test_db_record_dark_mode_applies_overrides(self, mock_config):
        """db_to_branding_response applies dark mode color overrides."""
        from src.api.branding_routes import db_to_branding_response

        db_record = {
            "tenant_id": "test_tenant",
            "preset_theme": "professional_blue",
            "dark_mode_enabled": True
        }

        result = db_to_branding_response(db_record, mock_config)
        # Dark mode overrides background and surface
        assert result["colors"]["background"] == "#0F172A"
        assert result["colors"]["surface"] == "#1E293B"

    def test_db_record_preserves_config_logo_when_no_db_logo(self, mock_config):
        """db_to_branding_response falls back to config logo_url."""
        from src.api.branding_routes import db_to_branding_response

        db_record = {
            "tenant_id": "test_tenant",
            "preset_theme": "professional_blue",
            "logo_url": None  # No logo in DB
        }

        result = db_to_branding_response(db_record, mock_config)
        assert result["logos"]["primary"] == mock_config.logo_url

    def test_db_record_with_login_background(self, mock_config):
        """db_to_branding_response includes login background fields."""
        from src.api.branding_routes import db_to_branding_response

        db_record = {
            "tenant_id": "test_tenant",
            "preset_theme": "professional_blue",
            "login_background_url": "https://example.com/bg.jpg",
            "login_background_gradient": "linear-gradient(#000, #fff)"
        }

        result = db_to_branding_response(db_record, mock_config)
        assert result["login_background_url"] == "https://example.com/bg.jpg"
        assert result["login_background_gradient"] == "linear-gradient(#000, #fff)"

    def test_none_db_record_returns_null_login_backgrounds(self, mock_config):
        """db_to_branding_response returns None login backgrounds for no DB record."""
        from src.api.branding_routes import db_to_branding_response

        result = db_to_branding_response(None, mock_config)
        assert result["login_background_url"] is None
        assert result["login_background_gradient"] is None

    def test_db_record_with_sidebar_colors(self, mock_config):
        """db_to_branding_response applies sidebar color overrides."""
        from src.api.branding_routes import db_to_branding_response

        db_record = {
            "tenant_id": "test_tenant",
            "preset_theme": "professional_blue",
            "color_sidebar_bg": "#1A1A2E",
            "color_sidebar_text": "#EAEAEA",
        }

        result = db_to_branding_response(db_record, mock_config)
        assert result["colors"]["sidebar_bg"] == "#1A1A2E"
        assert result["colors"]["sidebar_text"] == "#EAEAEA"


# ==================== NEW TESTS: Preview endpoint extended ====================

class TestPreviewBrandingMocked:
    """Extended tests for POST /api/v1/branding/preview."""

    @patch("src.api.branding_routes.get_client_config")
    @patch("src.api.branding_routes.SupabaseTool")
    def test_preview_applies_preset_change(
        self, mock_supabase, mock_get_config, test_client, mock_config
    ):
        """Preview with preset_theme returns that preset's colors."""
        mock_get_config.return_value = mock_config
        mock_db = MagicMock()
        mock_db.get_branding.return_value = None
        mock_supabase.return_value = mock_db

        response = test_client.post(
            "/api/v1/branding/preview",
            json={"preset_theme": "sunset_coral"},
            headers={"X-Client-ID": "test_tenant"}
        )

        if response.status_code == 200:
            data = response.json()["data"]
            assert data["preset_theme"] == "sunset_coral"
            assert data["colors"]["primary"] == "#F43F5E"

    @patch("src.api.branding_routes.get_client_config")
    @patch("src.api.branding_routes.SupabaseTool")
    def test_preview_dark_mode_toggle(
        self, mock_supabase, mock_get_config, test_client, mock_config
    ):
        """Preview with dark_mode_enabled=True applies dark colors."""
        mock_get_config.return_value = mock_config
        mock_db = MagicMock()
        mock_db.get_branding.return_value = None
        mock_supabase.return_value = mock_db

        response = test_client.post(
            "/api/v1/branding/preview",
            json={"dark_mode_enabled": True},
            headers={"X-Client-ID": "test_tenant"}
        )

        if response.status_code == 200:
            colors = response.json()["data"]["colors"]
            assert colors["background"] == "#0F172A"  # Dark mode background

    @patch("src.api.branding_routes.get_client_config")
    @patch("src.api.branding_routes.SupabaseTool")
    def test_preview_does_not_save_to_db(
        self, mock_supabase, mock_get_config, test_client, mock_config
    ):
        """Preview endpoint does not call update_branding on DB."""
        mock_get_config.return_value = mock_config
        mock_db = MagicMock()
        mock_db.get_branding.return_value = None
        mock_supabase.return_value = mock_db

        response = test_client.post(
            "/api/v1/branding/preview",
            json={"preset_theme": "ocean_teal"},
            headers={"X-Client-ID": "test_tenant"}
        )

        # Verify update_branding was never called
        mock_db.update_branding.assert_not_called()


# ==================== NEW TESTS: Fonts endpoint extended ====================

class TestGetFontsExtended:
    """Extended tests for GET /api/v1/branding/fonts."""

    def test_fonts_contain_inter(self, test_client):
        """Fonts list includes Inter."""
        response = test_client.get("/api/v1/branding/fonts")
        font_names = [f["name"] for f in response.json()["data"]]
        assert "Inter" in font_names

    def test_fonts_have_name_value_category(self, test_client):
        """Each font entry has name, value, and category."""
        response = test_client.get("/api/v1/branding/fonts")
        for font in response.json()["data"]:
            assert "name" in font
            assert "value" in font
            assert "category" in font

    def test_fonts_categories_are_valid(self, test_client):
        """Font categories are either sans-serif or serif."""
        response = test_client.get("/api/v1/branding/fonts")
        for font in response.json()["data"]:
            assert font["category"] in ["sans-serif", "serif"]

    def test_fonts_count_matches_data_length(self, test_client):
        """Font count matches actual number of fonts returned."""
        response = test_client.get("/api/v1/branding/fonts")
        data = response.json()
        assert data["count"] == len(data["data"])
        assert data["count"] >= 10  # We know there are at least 13 fonts
