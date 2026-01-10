"""
Constants module for the multi-tenant platform
"""

from .theme_presets import (
    THEME_PRESETS,
    DARK_MODE_COLORS,
    GOOGLE_FONTS,
    DEFAULT_BRANDING,
    get_preset,
    get_all_presets,
    apply_dark_mode,
    get_google_fonts
)

__all__ = [
    "THEME_PRESETS",
    "DARK_MODE_COLORS",
    "GOOGLE_FONTS",
    "DEFAULT_BRANDING",
    "get_preset",
    "get_all_presets",
    "apply_dark_mode",
    "get_google_fonts"
]
