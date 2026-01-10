"""
Theme Presets for White-Labeling

Predefined theme configurations that tenants can select as starting points.
Each preset includes colors, fonts, and styling preferences.
"""

from typing import Dict, Any

THEME_PRESETS: Dict[str, Dict[str, Any]] = {
    "professional_blue": {
        "name": "Professional Blue",
        "description": "Clean, corporate aesthetic with blue tones",
        "colors": {
            "primary": "#2563EB",
            "primary_light": "#3B82F6",
            "primary_dark": "#1D4ED8",
            "secondary": "#64748B",
            "secondary_light": "#94A3B8",
            "secondary_dark": "#475569",
            "accent": "#0EA5E9",
            "success": "#22C55E",
            "warning": "#F59E0B",
            "error": "#EF4444",
            "background": "#F8FAFC",
            "surface": "#FFFFFF",
            "surface_elevated": "#FFFFFF",
            "text_primary": "#1E293B",
            "text_secondary": "#475569",
            "text_muted": "#94A3B8",
            "border": "#E2E8F0",
            "border_light": "#F1F5F9"
        },
        "fonts": {
            "heading": "Inter, system-ui, sans-serif",
            "body": "Inter, system-ui, sans-serif"
        },
        "preview_gradient": "linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)"
    },
    "vibrant_orange": {
        "name": "Vibrant Orange",
        "description": "Energetic and warm with orange accents",
        "colors": {
            "primary": "#EA580C",
            "primary_light": "#F97316",
            "primary_dark": "#C2410C",
            "secondary": "#78716C",
            "secondary_light": "#A8A29E",
            "secondary_dark": "#57534E",
            "accent": "#FBBF24",
            "success": "#22C55E",
            "warning": "#F59E0B",
            "error": "#EF4444",
            "background": "#FFFBEB",
            "surface": "#FFFFFF",
            "surface_elevated": "#FFFFFF",
            "text_primary": "#292524",
            "text_secondary": "#57534E",
            "text_muted": "#A8A29E",
            "border": "#FED7AA",
            "border_light": "#FFEDD5"
        },
        "fonts": {
            "heading": "Poppins, system-ui, sans-serif",
            "body": "Inter, system-ui, sans-serif"
        },
        "preview_gradient": "linear-gradient(135deg, #EA580C 0%, #C2410C 100%)"
    },
    "nature_green": {
        "name": "Nature Green",
        "description": "Fresh and eco-friendly green palette",
        "colors": {
            "primary": "#059669",
            "primary_light": "#10B981",
            "primary_dark": "#047857",
            "secondary": "#6B7280",
            "secondary_light": "#9CA3AF",
            "secondary_dark": "#4B5563",
            "accent": "#14B8A6",
            "success": "#22C55E",
            "warning": "#F59E0B",
            "error": "#EF4444",
            "background": "#F0FDF4",
            "surface": "#FFFFFF",
            "surface_elevated": "#FFFFFF",
            "text_primary": "#1F2937",
            "text_secondary": "#4B5563",
            "text_muted": "#9CA3AF",
            "border": "#D1FAE5",
            "border_light": "#ECFDF5"
        },
        "fonts": {
            "heading": "Nunito, system-ui, sans-serif",
            "body": "Open Sans, system-ui, sans-serif"
        },
        "preview_gradient": "linear-gradient(135deg, #059669 0%, #047857 100%)"
    },
    "elegant_purple": {
        "name": "Elegant Purple",
        "description": "Sophisticated purple with luxury feel",
        "colors": {
            "primary": "#7C3AED",
            "primary_light": "#8B5CF6",
            "primary_dark": "#6D28D9",
            "secondary": "#64748B",
            "secondary_light": "#94A3B8",
            "secondary_dark": "#475569",
            "accent": "#EC4899",
            "success": "#22C55E",
            "warning": "#F59E0B",
            "error": "#EF4444",
            "background": "#FAF5FF",
            "surface": "#FFFFFF",
            "surface_elevated": "#FFFFFF",
            "text_primary": "#1E1B4B",
            "text_secondary": "#4C1D95",
            "text_muted": "#A78BFA",
            "border": "#E9D5FF",
            "border_light": "#F3E8FF"
        },
        "fonts": {
            "heading": "Playfair Display, serif",
            "body": "Lato, system-ui, sans-serif"
        },
        "preview_gradient": "linear-gradient(135deg, #7C3AED 0%, #6D28D9 100%)"
    },
    "sunset_coral": {
        "name": "Sunset Coral",
        "description": "Warm coral tones perfect for travel brands",
        "colors": {
            "primary": "#F43F5E",
            "primary_light": "#FB7185",
            "primary_dark": "#E11D48",
            "secondary": "#71717A",
            "secondary_light": "#A1A1AA",
            "secondary_dark": "#52525B",
            "accent": "#F97316",
            "success": "#22C55E",
            "warning": "#F59E0B",
            "error": "#EF4444",
            "background": "#FFF1F2",
            "surface": "#FFFFFF",
            "surface_elevated": "#FFFFFF",
            "text_primary": "#18181B",
            "text_secondary": "#52525B",
            "text_muted": "#A1A1AA",
            "border": "#FECDD3",
            "border_light": "#FFE4E6"
        },
        "fonts": {
            "heading": "Montserrat, system-ui, sans-serif",
            "body": "Source Sans Pro, system-ui, sans-serif"
        },
        "preview_gradient": "linear-gradient(135deg, #F43F5E 0%, #E11D48 100%)"
    },
    "ocean_teal": {
        "name": "Ocean Teal",
        "description": "Calming teal for tropical destinations",
        "colors": {
            "primary": "#0D9488",
            "primary_light": "#14B8A6",
            "primary_dark": "#0F766E",
            "secondary": "#64748B",
            "secondary_light": "#94A3B8",
            "secondary_dark": "#475569",
            "accent": "#06B6D4",
            "success": "#22C55E",
            "warning": "#F59E0B",
            "error": "#EF4444",
            "background": "#F0FDFA",
            "surface": "#FFFFFF",
            "surface_elevated": "#FFFFFF",
            "text_primary": "#134E4A",
            "text_secondary": "#115E59",
            "text_muted": "#5EEAD4",
            "border": "#99F6E4",
            "border_light": "#CCFBF1"
        },
        "fonts": {
            "heading": "Quicksand, system-ui, sans-serif",
            "body": "Roboto, system-ui, sans-serif"
        },
        "preview_gradient": "linear-gradient(135deg, #0D9488 0%, #0F766E 100%)"
    }
}

# Dark mode color adjustments - applied on top of any theme
DARK_MODE_COLORS: Dict[str, str] = {
    "background": "#0F172A",
    "surface": "#1E293B",
    "surface_elevated": "#334155",
    "text_primary": "#F8FAFC",
    "text_secondary": "#CBD5E1",
    "text_muted": "#64748B",
    "border": "#334155",
    "border_light": "#475569"
}

# Available Google Fonts for typography selection
GOOGLE_FONTS = [
    {"name": "Inter", "value": "Inter, system-ui, sans-serif", "category": "sans-serif"},
    {"name": "Poppins", "value": "Poppins, system-ui, sans-serif", "category": "sans-serif"},
    {"name": "Montserrat", "value": "Montserrat, system-ui, sans-serif", "category": "sans-serif"},
    {"name": "Open Sans", "value": "Open Sans, system-ui, sans-serif", "category": "sans-serif"},
    {"name": "Roboto", "value": "Roboto, system-ui, sans-serif", "category": "sans-serif"},
    {"name": "Lato", "value": "Lato, system-ui, sans-serif", "category": "sans-serif"},
    {"name": "Nunito", "value": "Nunito, system-ui, sans-serif", "category": "sans-serif"},
    {"name": "Quicksand", "value": "Quicksand, system-ui, sans-serif", "category": "sans-serif"},
    {"name": "Source Sans Pro", "value": "Source Sans Pro, system-ui, sans-serif", "category": "sans-serif"},
    {"name": "Raleway", "value": "Raleway, system-ui, sans-serif", "category": "sans-serif"},
    {"name": "Playfair Display", "value": "Playfair Display, serif", "category": "serif"},
    {"name": "Merriweather", "value": "Merriweather, serif", "category": "serif"},
    {"name": "Libre Baskerville", "value": "Libre Baskerville, serif", "category": "serif"},
]

# Default branding values
DEFAULT_BRANDING = {
    "preset_theme": "professional_blue",
    "dark_mode_enabled": False,
    "logo_url": None,
    "logo_dark_url": None,
    "favicon_url": None,
    "colors": THEME_PRESETS["professional_blue"]["colors"],
    "fonts": THEME_PRESETS["professional_blue"]["fonts"],
    "custom_css": None
}


def get_preset(preset_name: str) -> Dict[str, Any]:
    """Get a theme preset by name"""
    return THEME_PRESETS.get(preset_name, THEME_PRESETS["professional_blue"])


def get_all_presets() -> Dict[str, Dict[str, Any]]:
    """Get all available theme presets"""
    return THEME_PRESETS


def apply_dark_mode(colors: Dict[str, str]) -> Dict[str, str]:
    """Apply dark mode adjustments to a color palette"""
    dark_colors = colors.copy()
    dark_colors.update(DARK_MODE_COLORS)
    return dark_colors


def get_google_fonts():
    """Get available Google Fonts for selection"""
    return GOOGLE_FONTS
