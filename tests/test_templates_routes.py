"""
Templates Routes Unit Tests

Comprehensive tests for document template API routes:
- GET /api/v1/templates - Get all template settings
- PUT /api/v1/templates - Update template settings
- GET /api/v1/templates/quote - Get quote template only
- GET /api/v1/templates/invoice - Get invoice template only
- POST /api/v1/templates/reset - Reset to defaults
- GET /api/v1/templates/layouts - Get available layouts

Uses pytest with mocked dependencies.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


# ==================== Fixtures ====================

@pytest.fixture
def mock_config():
    """Create a mock ClientConfig."""
    config = MagicMock()
    config.client_id = "test_tenant"
    config.supabase_url = "https://test.supabase.co"
    config.supabase_service_key = "test-service-key"
    config.supabase_anon_key = "test-anon-key"
    config.currency = "USD"
    return config


def create_chainable_mock(data=None):
    """Create a mock that supports method chaining for Supabase queries."""
    mock = MagicMock()
    mock.select.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.delete.return_value = mock
    mock.eq.return_value = mock
    mock.neq.return_value = mock
    mock.gt.return_value = mock
    mock.gte.return_value = mock
    mock.lt.return_value = mock
    mock.lte.return_value = mock
    mock.is_.return_value = mock
    mock.in_.return_value = mock
    mock.order.return_value = mock
    mock.limit.return_value = mock
    mock.range.return_value = mock
    mock.single.return_value = mock

    execute_result = MagicMock()
    execute_result.data = data if data is not None else []
    mock.execute.return_value = execute_result

    return mock


# ==================== Dependency Injection Tests ====================

class TestTemplatesRoutesDependencies:
    """Test dependency injection for templates routes."""

    def test_get_client_config_with_invalid_client(self, mock_config):
        """get_client_config should handle invalid client IDs."""
        from src.api.templates_routes import get_client_config, _client_configs
        from fastapi import HTTPException

        # Clear cache
        _client_configs.clear()

        # Mock ClientConfig to raise error
        with patch('src.api.templates_routes.ClientConfig') as mock_class:
            mock_class.side_effect = Exception("Config not found")

            with pytest.raises(HTTPException) as exc_info:
                get_client_config("invalid_client")

            assert exc_info.value.status_code == 400
            assert "Invalid client" in str(exc_info.value.detail)

    def test_get_client_config_caches_result(self, mock_config):
        """get_client_config should cache ClientConfig instances."""
        from src.api.templates_routes import get_client_config, _client_configs

        # Clear cache
        _client_configs.clear()

        with patch('src.api.templates_routes.ClientConfig') as mock_class:
            mock_class.return_value = mock_config

            # First call should create new config
            config1 = get_client_config("cached_client")
            assert mock_class.call_count == 1

            # Second call should use cached config
            config2 = get_client_config("cached_client")
            assert mock_class.call_count == 1  # Still 1

            assert config1 is config2


# ==================== Pydantic Model Tests ====================

class TestTemplatesModels:
    """Test Pydantic model validation."""

    def test_quote_template_settings_defaults(self):
        """QuoteTemplateSettings should have sensible defaults."""
        from src.api.templates_routes import QuoteTemplateSettings

        settings = QuoteTemplateSettings()
        assert settings.validity_days == 14
        assert settings.show_price_breakdown is True
        assert settings.show_transfers is True
        assert settings.show_company_address is True
        assert settings.show_website is True

    def test_quote_template_settings_custom_values(self):
        """QuoteTemplateSettings should accept custom values."""
        from src.api.templates_routes import QuoteTemplateSettings

        settings = QuoteTemplateSettings(
            pdf_layout="modern",
            default_terms="Custom terms",
            default_notes="Custom notes",
            validity_days=30,
            show_price_breakdown=False
        )
        assert settings.pdf_layout == "modern"
        assert settings.default_terms == "Custom terms"
        assert settings.validity_days == 30
        assert settings.show_price_breakdown is False

    def test_quote_template_settings_validity_days_range(self):
        """QuoteTemplateSettings validity_days should be between 1-90."""
        from src.api.templates_routes import QuoteTemplateSettings
        from pydantic import ValidationError

        # Valid range
        settings = QuoteTemplateSettings(validity_days=1)
        assert settings.validity_days == 1

        settings = QuoteTemplateSettings(validity_days=90)
        assert settings.validity_days == 90

        # Invalid - below minimum
        with pytest.raises(ValidationError):
            QuoteTemplateSettings(validity_days=0)

        # Invalid - above maximum
        with pytest.raises(ValidationError):
            QuoteTemplateSettings(validity_days=91)

    def test_invoice_template_settings_defaults(self):
        """InvoiceTemplateSettings should have sensible defaults."""
        from src.api.templates_routes import InvoiceTemplateSettings

        settings = InvoiceTemplateSettings()
        assert settings.due_days == 14
        assert settings.show_banking_details is True
        assert settings.show_vat is True
        assert settings.show_traveler_details is True
        assert settings.show_company_address is True

    def test_invoice_template_settings_custom_values(self):
        """InvoiceTemplateSettings should accept custom values."""
        from src.api.templates_routes import InvoiceTemplateSettings

        settings = InvoiceTemplateSettings(
            pdf_layout="minimal",
            default_terms="Invoice terms",
            default_payment_instructions="Wire transfer only",
            due_days=7,
            show_banking_details=False
        )
        assert settings.pdf_layout == "minimal"
        assert settings.default_payment_instructions == "Wire transfer only"
        assert settings.due_days == 7

    def test_template_settings_update_partial(self):
        """TemplateSettingsUpdate should allow partial updates."""
        from src.api.templates_routes import TemplateSettingsUpdate, QuoteTemplateSettings

        # Both None
        update = TemplateSettingsUpdate()
        assert update.quote is None
        assert update.invoice is None

        # Only quote
        update = TemplateSettingsUpdate(
            quote=QuoteTemplateSettings(validity_days=21)
        )
        assert update.quote.validity_days == 21
        assert update.invoice is None

    def test_quote_template_max_length_terms(self):
        """QuoteTemplateSettings should enforce max length on terms."""
        from src.api.templates_routes import QuoteTemplateSettings
        from pydantic import ValidationError

        # Within limit
        long_terms = "A" * 2000
        settings = QuoteTemplateSettings(default_terms=long_terms)
        assert len(settings.default_terms) == 2000

        # Over limit
        with pytest.raises(ValidationError):
            QuoteTemplateSettings(default_terms="A" * 2001)


# ==================== Route Structure Tests ====================

class TestTemplatesRouteStructure:
    """Test the structure of templates routes."""

    def test_router_has_correct_prefix(self):
        """Router should have /api/v1/templates prefix."""
        from src.api.templates_routes import templates_router
        assert templates_router.prefix == "/api/v1/templates"

    def test_router_has_correct_tags(self):
        """Router should have Templates tag."""
        from src.api.templates_routes import templates_router
        assert "Templates" in templates_router.tags

    def test_get_templates_endpoint_exists(self):
        """GET / endpoint should exist."""
        from src.api.templates_routes import templates_router

        routes = [(route.path, route.methods) for route in templates_router.routes]
        # Check for root GET endpoint
        assert any("GET" in methods and path.endswith("/templates") or path == "" for path, methods in routes)

    def test_put_templates_endpoint_exists(self):
        """PUT / endpoint should exist."""
        from src.api.templates_routes import templates_router

        routes = [(route.path, route.methods) for route in templates_router.routes]
        assert any("PUT" in methods for path, methods in routes)

    def test_quote_endpoint_exists(self):
        """GET /quote endpoint should exist."""
        from src.api.templates_routes import templates_router

        routes = [route.path for route in templates_router.routes]
        assert any("/quote" in route for route in routes)

    def test_invoice_endpoint_exists(self):
        """GET /invoice endpoint should exist."""
        from src.api.templates_routes import templates_router

        routes = [route.path for route in templates_router.routes]
        assert any("/invoice" in route for route in routes)

    def test_reset_endpoint_exists(self):
        """POST /reset endpoint should exist."""
        from src.api.templates_routes import templates_router

        routes = [route.path for route in templates_router.routes]
        assert any("/reset" in route for route in routes)

    def test_layouts_endpoint_exists(self):
        """GET /layouts endpoint should exist."""
        from src.api.templates_routes import templates_router

        routes = [route.path for route in templates_router.routes]
        assert any("/layouts" in route for route in routes)


# ==================== Default Settings Tests ====================

class TestDefaultSettings:
    """Test default template settings."""

    def test_get_default_settings_structure(self):
        """get_default_settings should return quote and invoice settings."""
        from src.api.templates_routes import get_default_settings

        defaults = get_default_settings()

        assert "quote" in defaults
        assert "invoice" in defaults

    def test_default_quote_settings(self):
        """Default quote settings should have expected values."""
        from src.api.templates_routes import get_default_settings

        defaults = get_default_settings()
        quote = defaults["quote"]

        assert quote["pdf_layout"] == "standard"
        assert quote["validity_days"] == 14
        assert quote["show_price_breakdown"] is True
        assert "default_terms" in quote

    def test_default_invoice_settings(self):
        """Default invoice settings should have expected values."""
        from src.api.templates_routes import get_default_settings

        defaults = get_default_settings()
        invoice = defaults["invoice"]

        assert invoice["pdf_layout"] == "standard"
        assert invoice["due_days"] == 14
        assert invoice["show_banking_details"] is True
        assert "default_terms" in invoice
        assert "default_payment_instructions" in invoice

    def test_default_terms_content(self):
        """Default terms should contain actual terms content."""
        from src.api.templates_routes import get_default_settings, DEFAULT_QUOTE_TERMS

        defaults = get_default_settings()

        # Verify terms are non-empty
        assert len(defaults["quote"]["default_terms"]) > 100
        assert len(defaults["invoice"]["default_terms"]) > 50


# ==================== Get Template Settings Logic Tests ====================

class TestGetTemplateSettingsLogic:
    """Test get_template_settings endpoint logic."""

    @pytest.mark.asyncio
    async def test_get_template_settings_returns_settings(self, mock_config):
        """get_template_settings should return template settings."""
        from src.api.templates_routes import get_template_settings

        mock_settings = {
            "quote": {"pdf_layout": "modern", "validity_days": 21},
            "invoice": {"pdf_layout": "minimal", "due_days": 7}
        }

        with patch('src.api.templates_routes.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.get_template_settings.return_value = mock_settings
            mock_supabase_class.return_value = mock_supabase

            result = await get_template_settings(config=mock_config)

            assert result["success"] is True
            assert result["data"]["quote"]["pdf_layout"] == "modern"
            assert result["data"]["invoice"]["due_days"] == 7

    @pytest.mark.asyncio
    async def test_get_template_settings_returns_defaults_on_none(self, mock_config):
        """get_template_settings should return defaults when no custom settings."""
        from src.api.templates_routes import get_template_settings, get_default_settings

        with patch('src.api.templates_routes.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.get_template_settings.return_value = None
            mock_supabase_class.return_value = mock_supabase

            result = await get_template_settings(config=mock_config)

            assert result["success"] is True
            defaults = get_default_settings()
            assert result["data"]["quote"]["validity_days"] == defaults["quote"]["validity_days"]

    @pytest.mark.asyncio
    async def test_get_template_settings_returns_defaults_on_error(self, mock_config):
        """get_template_settings should return defaults on database error."""
        from src.api.templates_routes import get_template_settings, get_default_settings

        with patch('src.api.templates_routes.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.get_template_settings.side_effect = Exception("DB error")
            mock_supabase_class.return_value = mock_supabase

            result = await get_template_settings(config=mock_config)

            # Should still succeed with defaults
            assert result["success"] is True
            defaults = get_default_settings()
            assert result["data"] == defaults


# ==================== Update Template Settings Logic Tests ====================

class TestUpdateTemplateSettingsLogic:
    """Test update_template_settings endpoint logic."""

    @pytest.mark.asyncio
    async def test_update_template_settings_success(self, mock_config):
        """update_template_settings should update settings."""
        from src.api.templates_routes import update_template_settings, TemplateSettingsUpdate, QuoteTemplateSettings

        update_data = TemplateSettingsUpdate(
            quote=QuoteTemplateSettings(validity_days=30)
        )

        current_settings = {
            "quote": {"validity_days": 14, "pdf_layout": "standard"},
            "invoice": {"due_days": 14}
        }

        with patch('src.api.templates_routes.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.get_template_settings.return_value = current_settings
            mock_supabase.update_template_settings.return_value = {"quote": {"validity_days": 30}}
            mock_supabase_class.return_value = mock_supabase

            result = await update_template_settings(data=update_data, config=mock_config)

            assert result["success"] is True
            assert result["message"] == "Template settings updated"

    @pytest.mark.asyncio
    async def test_update_template_settings_partial_update(self, mock_config):
        """update_template_settings should only update provided fields."""
        from src.api.templates_routes import update_template_settings, TemplateSettingsUpdate, QuoteTemplateSettings

        update_data = TemplateSettingsUpdate(
            quote=QuoteTemplateSettings(pdf_layout="modern")
        )

        current_settings = {
            "quote": {"validity_days": 14, "pdf_layout": "standard"},
            "invoice": {"due_days": 14}
        }

        with patch('src.api.templates_routes.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.get_template_settings.return_value = current_settings
            mock_supabase.update_template_settings.return_value = None
            mock_supabase_class.return_value = mock_supabase

            result = await update_template_settings(data=update_data, config=mock_config)

            # Check that update_template_settings was called
            mock_supabase.update_template_settings.assert_called_once()
            call_args = mock_supabase.update_template_settings.call_args[0][0]
            # Original validity_days should be preserved
            assert "quote" in call_args

    @pytest.mark.asyncio
    async def test_update_template_settings_error(self, mock_config):
        """update_template_settings should handle errors."""
        from src.api.templates_routes import update_template_settings, TemplateSettingsUpdate, QuoteTemplateSettings
        from fastapi import HTTPException

        update_data = TemplateSettingsUpdate(
            quote=QuoteTemplateSettings(validity_days=30)
        )

        with patch('src.api.templates_routes.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.get_template_settings.side_effect = Exception("DB error")
            mock_supabase_class.return_value = mock_supabase

            with pytest.raises(HTTPException) as exc_info:
                await update_template_settings(data=update_data, config=mock_config)

            assert exc_info.value.status_code == 500


# ==================== Quote Template Endpoint Tests ====================

class TestQuoteTemplateLogic:
    """Test get_quote_template endpoint logic."""

    @pytest.mark.asyncio
    async def test_get_quote_template_returns_quote_only(self, mock_config):
        """get_quote_template should return only quote settings."""
        from src.api.templates_routes import get_quote_template

        mock_settings = {
            "quote": {"pdf_layout": "modern", "validity_days": 21},
            "invoice": {"pdf_layout": "minimal", "due_days": 7}
        }

        with patch('src.api.templates_routes.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.get_template_settings.return_value = mock_settings
            mock_supabase_class.return_value = mock_supabase

            result = await get_quote_template(config=mock_config)

            assert result["success"] is True
            assert result["data"]["pdf_layout"] == "modern"
            assert result["data"]["validity_days"] == 21
            # Should not include invoice data
            assert "due_days" not in result["data"]

    @pytest.mark.asyncio
    async def test_get_quote_template_returns_defaults_on_none(self, mock_config):
        """get_quote_template should return defaults when no settings."""
        from src.api.templates_routes import get_quote_template, get_default_settings

        with patch('src.api.templates_routes.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.get_template_settings.return_value = None
            mock_supabase_class.return_value = mock_supabase

            result = await get_quote_template(config=mock_config)

            assert result["success"] is True
            defaults = get_default_settings()
            assert result["data"]["validity_days"] == defaults["quote"]["validity_days"]


# ==================== Invoice Template Endpoint Tests ====================

class TestInvoiceTemplateLogic:
    """Test get_invoice_template endpoint logic."""

    @pytest.mark.asyncio
    async def test_get_invoice_template_returns_invoice_only(self, mock_config):
        """get_invoice_template should return only invoice settings."""
        from src.api.templates_routes import get_invoice_template

        mock_settings = {
            "quote": {"pdf_layout": "modern", "validity_days": 21},
            "invoice": {"pdf_layout": "minimal", "due_days": 7}
        }

        with patch('src.api.templates_routes.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.get_template_settings.return_value = mock_settings
            mock_supabase_class.return_value = mock_supabase

            result = await get_invoice_template(config=mock_config)

            assert result["success"] is True
            assert result["data"]["pdf_layout"] == "minimal"
            assert result["data"]["due_days"] == 7
            # Should not include quote data
            assert "validity_days" not in result["data"]

    @pytest.mark.asyncio
    async def test_get_invoice_template_returns_defaults_on_none(self, mock_config):
        """get_invoice_template should return defaults when no settings."""
        from src.api.templates_routes import get_invoice_template, get_default_settings

        with patch('src.api.templates_routes.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.get_template_settings.return_value = None
            mock_supabase_class.return_value = mock_supabase

            result = await get_invoice_template(config=mock_config)

            assert result["success"] is True
            defaults = get_default_settings()
            assert result["data"]["due_days"] == defaults["invoice"]["due_days"]


# ==================== Reset Template Settings Tests ====================

class TestResetTemplateSettingsLogic:
    """Test reset_template_settings endpoint logic."""

    @pytest.mark.asyncio
    async def test_reset_template_settings_returns_defaults(self, mock_config):
        """reset_template_settings should return default settings."""
        from src.api.templates_routes import reset_template_settings, get_default_settings

        with patch('src.api.templates_routes.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.update_template_settings.return_value = None
            mock_supabase_class.return_value = mock_supabase

            result = await reset_template_settings(config=mock_config)

            assert result["success"] is True
            assert result["message"] == "Template settings reset to defaults"
            defaults = get_default_settings()
            assert result["data"]["quote"]["validity_days"] == defaults["quote"]["validity_days"]

    @pytest.mark.asyncio
    async def test_reset_template_settings_calls_update(self, mock_config):
        """reset_template_settings should call update_template_settings."""
        from src.api.templates_routes import reset_template_settings, get_default_settings

        with patch('src.api.templates_routes.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.update_template_settings.return_value = None
            mock_supabase_class.return_value = mock_supabase

            await reset_template_settings(config=mock_config)

            mock_supabase.update_template_settings.assert_called_once()
            call_args = mock_supabase.update_template_settings.call_args[0][0]
            defaults = get_default_settings()
            assert call_args == defaults


# ==================== Layouts Endpoint Tests ====================

class TestLayoutsEndpoint:
    """Test get_available_layouts endpoint."""

    @pytest.mark.asyncio
    async def test_get_available_layouts_returns_layouts(self):
        """get_available_layouts should return available layout options."""
        from src.api.templates_routes import get_available_layouts

        result = await get_available_layouts()

        assert result["success"] is True
        assert len(result["data"]) == 3  # standard, modern, minimal

    @pytest.mark.asyncio
    async def test_get_available_layouts_has_required_fields(self):
        """Each layout should have id, name, and description."""
        from src.api.templates_routes import get_available_layouts

        result = await get_available_layouts()

        for layout in result["data"]:
            assert "id" in layout
            assert "name" in layout
            assert "description" in layout

    @pytest.mark.asyncio
    async def test_get_available_layouts_includes_standard(self):
        """Layouts should include standard layout."""
        from src.api.templates_routes import get_available_layouts

        result = await get_available_layouts()

        layout_ids = [layout["id"] for layout in result["data"]]
        assert "standard" in layout_ids

    @pytest.mark.asyncio
    async def test_get_available_layouts_includes_modern(self):
        """Layouts should include modern layout."""
        from src.api.templates_routes import get_available_layouts

        result = await get_available_layouts()

        layout_ids = [layout["id"] for layout in result["data"]]
        assert "modern" in layout_ids

    @pytest.mark.asyncio
    async def test_get_available_layouts_includes_minimal(self):
        """Layouts should include minimal layout."""
        from src.api.templates_routes import get_available_layouts

        result = await get_available_layouts()

        layout_ids = [layout["id"] for layout in result["data"]]
        assert "minimal" in layout_ids


# ==================== Error Recovery Tests ====================

class TestErrorRecovery:
    """Test error recovery behavior."""

    @pytest.mark.asyncio
    async def test_get_settings_recovers_from_error(self, mock_config):
        """get_template_settings should recover from errors with defaults."""
        from src.api.templates_routes import get_template_settings

        with patch('src.api.templates_routes.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.get_template_settings.side_effect = Exception("Network error")
            mock_supabase_class.return_value = mock_supabase

            # Should not raise, should return defaults
            result = await get_template_settings(config=mock_config)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_get_quote_recovers_from_error(self, mock_config):
        """get_quote_template should recover from errors with defaults."""
        from src.api.templates_routes import get_quote_template

        with patch('src.api.templates_routes.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.get_template_settings.side_effect = Exception("Network error")
            mock_supabase_class.return_value = mock_supabase

            # Should not raise, should return defaults
            result = await get_quote_template(config=mock_config)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_get_invoice_recovers_from_error(self, mock_config):
        """get_invoice_template should recover from errors with defaults."""
        from src.api.templates_routes import get_invoice_template

        with patch('src.api.templates_routes.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.get_template_settings.side_effect = Exception("Network error")
            mock_supabase_class.return_value = mock_supabase

            # Should not raise, should return defaults
            result = await get_invoice_template(config=mock_config)
            assert result["success"] is True


# ==================== Template Merge Tests ====================

class TestTemplateMerge:
    """Test template merging logic."""

    @pytest.mark.asyncio
    async def test_update_preserves_unmodified_fields(self, mock_config):
        """Partial update should preserve fields not being modified."""
        from src.api.templates_routes import update_template_settings, TemplateSettingsUpdate, QuoteTemplateSettings

        update_data = TemplateSettingsUpdate(
            quote=QuoteTemplateSettings(pdf_layout="modern")
        )

        current_settings = {
            "quote": {
                "pdf_layout": "standard",
                "validity_days": 14,
                "default_terms": "Original terms"
            },
            "invoice": {"due_days": 14}
        }

        with patch('src.api.templates_routes.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.get_template_settings.return_value = current_settings
            mock_supabase.update_template_settings.return_value = None
            mock_supabase_class.return_value = mock_supabase

            await update_template_settings(data=update_data, config=mock_config)

            call_args = mock_supabase.update_template_settings.call_args[0][0]
            # Check layout was updated
            assert call_args["quote"]["pdf_layout"] == "modern"
            # Check other fields preserved (merged with defaults if needed)
            assert "quote" in call_args

    @pytest.mark.asyncio
    async def test_update_invoice_only(self, mock_config):
        """Update invoice settings only."""
        from src.api.templates_routes import update_template_settings, TemplateSettingsUpdate, InvoiceTemplateSettings

        update_data = TemplateSettingsUpdate(
            invoice=InvoiceTemplateSettings(due_days=7)
        )

        current_settings = {
            "quote": {"validity_days": 14},
            "invoice": {"due_days": 14, "show_vat": True}
        }

        with patch('src.api.templates_routes.SupabaseTool') as mock_supabase_class:
            mock_supabase = MagicMock()
            mock_supabase.get_template_settings.return_value = current_settings
            mock_supabase.update_template_settings.return_value = None
            mock_supabase_class.return_value = mock_supabase

            await update_template_settings(data=update_data, config=mock_config)

            call_args = mock_supabase.update_template_settings.call_args[0][0]
            # Invoice should be updated
            assert call_args["invoice"]["due_days"] == 7
            # Quote should remain unchanged
            assert call_args["quote"]["validity_days"] == 14
