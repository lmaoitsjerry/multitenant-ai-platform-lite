"""
Template Renderer Unit Tests

Tests for Jinja2 template rendering with client branding.
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


@pytest.fixture
def mock_config():
    """Create a mock ClientConfig."""
    config = MagicMock()
    config.client_id = "test_client"
    config.name = "Test Client"
    config.short_name = "TC"
    config.timezone = "Africa/Johannesburg"
    config.company_name = "Test Travel Co"
    config.logo_url = "https://example.com/logo.png"
    config.primary_color = "#FF6B6B"
    config.secondary_color = "#4ECDC4"
    config.email_signature = "Best regards,\nTest Team"
    config.primary_email = "info@testtravel.com"
    config.destinations = ["Zanzibar", "Mauritius"]
    return config


class TestTemplateRendererInit:
    """Tests for TemplateRenderer initialization."""

    def test_init_creates_jinja_environment(self, mock_config):
        """Should create Jinja2 environment."""
        from src.utils.template_renderer import TemplateRenderer

        renderer = TemplateRenderer(mock_config)

        assert renderer.env is not None

    def test_init_builds_base_context(self, mock_config):
        """Should build base context with client info."""
        from src.utils.template_renderer import TemplateRenderer

        renderer = TemplateRenderer(mock_config)

        assert "client" in renderer.base_context
        assert "branding" in renderer.base_context
        assert "email" in renderer.base_context
        assert "destinations" in renderer.base_context

    def test_base_context_has_client_info(self, mock_config):
        """Base context should have client details."""
        from src.utils.template_renderer import TemplateRenderer

        renderer = TemplateRenderer(mock_config)

        assert renderer.base_context["client"]["name"] == "Test Client"
        assert renderer.base_context["client"]["short_name"] == "TC"

    def test_base_context_has_branding(self, mock_config):
        """Base context should have branding details."""
        from src.utils.template_renderer import TemplateRenderer

        renderer = TemplateRenderer(mock_config)

        branding = renderer.base_context["branding"]
        assert branding["company_name"] == "Test Travel Co"
        assert branding["primary_color"] == "#FF6B6B"
        assert branding["logo_url"] == "https://example.com/logo.png"


class TestRenderTemplate:
    """Tests for render_template method."""

    def test_render_template_merges_context(self, mock_config):
        """render_template should merge base and provided context."""
        from src.utils.template_renderer import TemplateRenderer

        renderer = TemplateRenderer(mock_config)

        # Mock the template loading
        mock_template = MagicMock()
        mock_template.render.return_value = "rendered"
        renderer.env.get_template = MagicMock(return_value=mock_template)

        renderer.render_template("test.html", {"custom_var": "value"})

        # Check that render was called with merged context
        call_kwargs = mock_template.render.call_args[1]
        assert "client" in call_kwargs  # Base context
        assert "custom_var" in call_kwargs  # Provided context

    def test_render_template_without_context(self, mock_config):
        """render_template should work without additional context."""
        from src.utils.template_renderer import TemplateRenderer

        renderer = TemplateRenderer(mock_config)

        mock_template = MagicMock()
        mock_template.render.return_value = "rendered"
        renderer.env.get_template = MagicMock(return_value=mock_template)

        result = renderer.render_template("test.html")

        assert result == "rendered"

    def test_render_template_handles_error(self, mock_config):
        """render_template should raise on template error."""
        from src.utils.template_renderer import TemplateRenderer

        renderer = TemplateRenderer(mock_config)
        renderer.env.get_template = MagicMock(side_effect=Exception("Template not found"))

        with pytest.raises(Exception):
            renderer.render_template("nonexistent.html")


class TestRenderString:
    """Tests for render_string method."""

    def test_render_string_simple(self, mock_config):
        """render_string should render template from string."""
        from src.utils.template_renderer import TemplateRenderer

        renderer = TemplateRenderer(mock_config)

        template_str = "Hello {{ name }}!"
        result = renderer.render_string(template_str, {"name": "World"})

        assert result == "Hello World!"

    def test_render_string_with_base_context(self, mock_config):
        """render_string should have access to base context."""
        from src.utils.template_renderer import TemplateRenderer

        renderer = TemplateRenderer(mock_config)

        template_str = "Company: {{ branding.company_name }}"
        result = renderer.render_string(template_str)

        assert result == "Company: Test Travel Co"

    def test_render_string_without_context(self, mock_config):
        """render_string should work without additional context."""
        from src.utils.template_renderer import TemplateRenderer

        renderer = TemplateRenderer(mock_config)

        template_str = "Static content"
        result = renderer.render_string(template_str)

        assert result == "Static content"

    def test_render_string_handles_error(self, mock_config):
        """render_string should raise on syntax error."""
        from src.utils.template_renderer import TemplateRenderer

        renderer = TemplateRenderer(mock_config)

        template_str = "{{ invalid syntax {% %}"

        with pytest.raises(Exception):
            renderer.render_string(template_str)


class TestRenderAgentPrompt:
    """Tests for render_agent_prompt method."""

    def test_render_agent_prompt_loads_file(self, mock_config, tmp_path):
        """render_agent_prompt should load prompt from file."""
        from src.utils.template_renderer import TemplateRenderer

        # Create temp prompt file
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("Hello {{ branding.company_name }}!")

        mock_config.get_prompt_path = MagicMock(return_value=str(prompt_file))

        renderer = TemplateRenderer(mock_config)
        result = renderer.render_agent_prompt("inbound")

        assert result == "Hello Test Travel Co!"

    def test_render_agent_prompt_with_context(self, mock_config, tmp_path):
        """render_agent_prompt should merge additional context."""
        from src.utils.template_renderer import TemplateRenderer

        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("Destination: {{ destination }}")

        mock_config.get_prompt_path = MagicMock(return_value=str(prompt_file))

        renderer = TemplateRenderer(mock_config)
        result = renderer.render_agent_prompt("helpdesk", {"destination": "Zanzibar"})

        assert result == "Destination: Zanzibar"

    def test_render_agent_prompt_handles_error(self, mock_config):
        """render_agent_prompt should raise on file error."""
        from src.utils.template_renderer import TemplateRenderer

        mock_config.get_prompt_path = MagicMock(return_value="/nonexistent/path.txt")

        renderer = TemplateRenderer(mock_config)

        with pytest.raises(Exception):
            renderer.render_agent_prompt("inbound")


class TestContextOverriding:
    """Tests for context override behavior."""

    def test_provided_context_overrides_base(self, mock_config):
        """Provided context should override base context values."""
        from src.utils.template_renderer import TemplateRenderer

        renderer = TemplateRenderer(mock_config)

        template_str = "{{ branding.company_name }}"

        # Override company name
        result = renderer.render_string(
            template_str,
            {"branding": {"company_name": "Override Co"}}
        )

        assert result == "Override Co"

    def test_base_context_not_mutated(self, mock_config):
        """Base context should not be mutated by render calls."""
        from src.utils.template_renderer import TemplateRenderer

        renderer = TemplateRenderer(mock_config)
        original_name = renderer.base_context["branding"]["company_name"]

        renderer.render_string(
            "{{ branding.company_name }}",
            {"branding": {"company_name": "Override"}}
        )

        # Base context should be unchanged
        assert renderer.base_context["branding"]["company_name"] == original_name
