"""
Theme Presets Unit Tests

Tests for theme presets and branding configurations.
"""

import pytest


class TestThemePresetsData:
    """Tests for THEME_PRESETS data structure."""

    def test_theme_presets_is_dict(self):
        """THEME_PRESETS should be a dictionary."""
        from src.constants.theme_presets import THEME_PRESETS

        assert isinstance(THEME_PRESETS, dict)

    def test_expected_presets_exist(self):
        """All expected presets should exist."""
        from src.constants.theme_presets import THEME_PRESETS

        expected = [
            "professional_blue",
            "vibrant_orange",
            "nature_green",
            "elegant_purple",
            "sunset_coral",
            "ocean_teal"
        ]

        for preset in expected:
            assert preset in THEME_PRESETS

    def test_preset_has_required_keys(self):
        """Each preset should have name, description, colors, fonts."""
        from src.constants.theme_presets import THEME_PRESETS

        for name, preset in THEME_PRESETS.items():
            assert "name" in preset, f"{name} missing 'name'"
            assert "description" in preset, f"{name} missing 'description'"
            assert "colors" in preset, f"{name} missing 'colors'"
            assert "fonts" in preset, f"{name} missing 'fonts'"
            assert "preview_gradient" in preset, f"{name} missing 'preview_gradient'"

    def test_colors_have_required_keys(self):
        """Each preset's colors should have standard keys."""
        from src.constants.theme_presets import THEME_PRESETS

        required_colors = [
            "primary", "secondary", "accent",
            "success", "warning", "error",
            "background", "surface",
            "text_primary", "text_secondary",
            "border"
        ]

        for name, preset in THEME_PRESETS.items():
            colors = preset["colors"]
            for color_key in required_colors:
                assert color_key in colors, f"{name} colors missing '{color_key}'"

    def test_colors_are_valid_hex(self):
        """All color values should be valid hex codes."""
        from src.constants.theme_presets import THEME_PRESETS
        import re

        hex_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')

        for name, preset in THEME_PRESETS.items():
            for color_key, color_value in preset["colors"].items():
                assert hex_pattern.match(color_value), \
                    f"{name}.colors.{color_key} = '{color_value}' is not valid hex"

    def test_fonts_have_heading_and_body(self):
        """Each preset should have heading and body fonts."""
        from src.constants.theme_presets import THEME_PRESETS

        for name, preset in THEME_PRESETS.items():
            fonts = preset["fonts"]
            assert "heading" in fonts, f"{name} fonts missing 'heading'"
            assert "body" in fonts, f"{name} fonts missing 'body'"


class TestDarkModeColors:
    """Tests for DARK_MODE_COLORS."""

    def test_dark_mode_colors_is_dict(self):
        """DARK_MODE_COLORS should be a dictionary."""
        from src.constants.theme_presets import DARK_MODE_COLORS

        assert isinstance(DARK_MODE_COLORS, dict)

    def test_dark_mode_has_background(self):
        """DARK_MODE_COLORS should have dark background."""
        from src.constants.theme_presets import DARK_MODE_COLORS

        assert "background" in DARK_MODE_COLORS
        # Should be a dark color (starts with low hex values)
        bg = DARK_MODE_COLORS["background"]
        assert bg.startswith("#0") or bg.startswith("#1") or bg.startswith("#2")

    def test_dark_mode_has_light_text(self):
        """DARK_MODE_COLORS should have light text colors."""
        from src.constants.theme_presets import DARK_MODE_COLORS

        assert "text_primary" in DARK_MODE_COLORS
        # Text should be light (starts with high hex values)
        text = DARK_MODE_COLORS["text_primary"]
        first_char = text[1].upper()
        assert first_char in "CDEF", f"text_primary {text} should be light color"


class TestGoogleFonts:
    """Tests for GOOGLE_FONTS list."""

    def test_google_fonts_is_list(self):
        """GOOGLE_FONTS should be a list."""
        from src.constants.theme_presets import GOOGLE_FONTS

        assert isinstance(GOOGLE_FONTS, list)

    def test_google_fonts_not_empty(self):
        """GOOGLE_FONTS should have items."""
        from src.constants.theme_presets import GOOGLE_FONTS

        assert len(GOOGLE_FONTS) > 0

    def test_font_entries_have_required_keys(self):
        """Each font entry should have name, value, category."""
        from src.constants.theme_presets import GOOGLE_FONTS

        for font in GOOGLE_FONTS:
            assert "name" in font
            assert "value" in font
            assert "category" in font

    def test_font_categories_valid(self):
        """Font categories should be valid CSS categories."""
        from src.constants.theme_presets import GOOGLE_FONTS

        valid_categories = ["sans-serif", "serif", "monospace", "display", "handwriting"]

        for font in GOOGLE_FONTS:
            assert font["category"] in valid_categories


class TestDefaultBranding:
    """Tests for DEFAULT_BRANDING."""

    def test_default_branding_is_dict(self):
        """DEFAULT_BRANDING should be a dictionary."""
        from src.constants.theme_presets import DEFAULT_BRANDING

        assert isinstance(DEFAULT_BRANDING, dict)

    def test_default_branding_has_preset_theme(self):
        """DEFAULT_BRANDING should reference a valid preset."""
        from src.constants.theme_presets import DEFAULT_BRANDING, THEME_PRESETS

        preset = DEFAULT_BRANDING["preset_theme"]
        assert preset in THEME_PRESETS

    def test_default_branding_has_colors(self):
        """DEFAULT_BRANDING should have colors from preset."""
        from src.constants.theme_presets import DEFAULT_BRANDING

        assert "colors" in DEFAULT_BRANDING
        assert "primary" in DEFAULT_BRANDING["colors"]

    def test_default_dark_mode_disabled(self):
        """DEFAULT_BRANDING should have dark_mode_enabled = False."""
        from src.constants.theme_presets import DEFAULT_BRANDING

        assert DEFAULT_BRANDING["dark_mode_enabled"] is False


class TestGetPreset:
    """Tests for get_preset function."""

    def test_get_preset_returns_preset(self):
        """get_preset should return requested preset."""
        from src.constants.theme_presets import get_preset

        preset = get_preset("professional_blue")

        assert preset["name"] == "Professional Blue"

    def test_get_preset_invalid_returns_default(self):
        """get_preset should return professional_blue for invalid name."""
        from src.constants.theme_presets import get_preset

        preset = get_preset("nonexistent_theme")

        assert preset["name"] == "Professional Blue"

    def test_get_preset_all_presets_work(self):
        """get_preset should work for all preset names."""
        from src.constants.theme_presets import get_preset, THEME_PRESETS

        for name in THEME_PRESETS.keys():
            preset = get_preset(name)
            assert preset is not None
            assert "colors" in preset


class TestGetAllPresets:
    """Tests for get_all_presets function."""

    def test_get_all_presets_returns_dict(self):
        """get_all_presets should return dictionary."""
        from src.constants.theme_presets import get_all_presets

        presets = get_all_presets()

        assert isinstance(presets, dict)

    def test_get_all_presets_returns_all(self):
        """get_all_presets should return all presets."""
        from src.constants.theme_presets import get_all_presets, THEME_PRESETS

        presets = get_all_presets()

        assert len(presets) == len(THEME_PRESETS)


class TestApplyDarkMode:
    """Tests for apply_dark_mode function."""

    def test_apply_dark_mode_returns_dict(self):
        """apply_dark_mode should return dictionary."""
        from src.constants.theme_presets import apply_dark_mode

        colors = {"primary": "#FF0000", "background": "#FFFFFF"}
        result = apply_dark_mode(colors)

        assert isinstance(result, dict)

    def test_apply_dark_mode_preserves_primary(self):
        """apply_dark_mode should preserve primary color."""
        from src.constants.theme_presets import apply_dark_mode

        colors = {"primary": "#FF0000", "background": "#FFFFFF"}
        result = apply_dark_mode(colors)

        assert result["primary"] == "#FF0000"

    def test_apply_dark_mode_changes_background(self):
        """apply_dark_mode should override background."""
        from src.constants.theme_presets import apply_dark_mode, DARK_MODE_COLORS

        colors = {"primary": "#FF0000", "background": "#FFFFFF"}
        result = apply_dark_mode(colors)

        assert result["background"] == DARK_MODE_COLORS["background"]

    def test_apply_dark_mode_does_not_modify_input(self):
        """apply_dark_mode should not modify input dict."""
        from src.constants.theme_presets import apply_dark_mode

        colors = {"primary": "#FF0000", "background": "#FFFFFF"}
        apply_dark_mode(colors)

        assert colors["background"] == "#FFFFFF"


class TestGetGoogleFonts:
    """Tests for get_google_fonts function."""

    def test_get_google_fonts_returns_list(self):
        """get_google_fonts should return list."""
        from src.constants.theme_presets import get_google_fonts

        fonts = get_google_fonts()

        assert isinstance(fonts, list)

    def test_get_google_fonts_same_as_constant(self):
        """get_google_fonts should return GOOGLE_FONTS."""
        from src.constants.theme_presets import get_google_fonts, GOOGLE_FONTS

        fonts = get_google_fonts()

        assert fonts is GOOGLE_FONTS
