"""
Branding API Routes

Handles white-labeling and branding customization for tenants:
- Theme presets selection
- Color customization
- Logo and favicon upload
- Typography settings
- Dark mode toggle
- Custom CSS

All endpoints support tenant isolation via X-Client-ID header.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Header, File, UploadFile, Form
from pydantic import BaseModel, Field

from config.loader import ClientConfig
from src.constants.theme_presets import (
    THEME_PRESETS,
    DARK_MODE_COLORS,
    GOOGLE_FONTS,
    DEFAULT_BRANDING,
    get_preset,
    get_all_presets,
    apply_dark_mode
)
from src.tools.supabase_tool import SupabaseTool
from src.utils.error_handler import log_and_raise

logger = logging.getLogger(__name__)

branding_router = APIRouter(prefix="/api/v1/branding", tags=["Branding"])

# ==================== Dependency ====================

_client_configs = {}


def get_client_config(x_client_id: str = Header(None, alias="X-Client-ID")) -> ClientConfig:
    """Get client configuration from header"""
    client_id = x_client_id or os.getenv("CLIENT_ID", "example")

    if client_id not in _client_configs:
        try:
            _client_configs[client_id] = ClientConfig(client_id)
            logger.info(f"Loaded configuration for client: {client_id}")
        except Exception as e:
            logger.error(f"Failed to load config for {client_id}: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid client: {client_id}")

    return _client_configs[client_id]


# ==================== Pydantic Models ====================

class BrandingColors(BaseModel):
    """Color configuration model"""
    primary: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    primary_light: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    primary_dark: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    secondary: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    secondary_light: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    secondary_dark: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    accent: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    success: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    warning: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    error: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    background: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    surface: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    surface_elevated: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    text_primary: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    text_secondary: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    text_muted: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    border: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    border_light: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    # Sidebar colors - whitelabel customization
    sidebar_bg: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    sidebar_text: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    sidebar_text_muted: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    sidebar_hover: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    sidebar_active_bg: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    sidebar_active_text: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')


class BrandingFonts(BaseModel):
    """Font configuration model"""
    heading: Optional[str] = None
    body: Optional[str] = None


class BrandingUpdate(BaseModel):
    """Branding update request model"""
    preset_theme: Optional[str] = None
    dark_mode_enabled: Optional[bool] = None
    logo_url: Optional[str] = None
    logo_dark_url: Optional[str] = None
    favicon_url: Optional[str] = None
    colors: Optional[BrandingColors] = None
    fonts: Optional[BrandingFonts] = None
    custom_css: Optional[str] = None
    # Login page customization
    login_background_url: Optional[str] = None
    login_background_gradient: Optional[str] = None


class PresetInfo(BaseModel):
    """Theme preset information"""
    id: str
    name: str
    description: str
    colors: Dict[str, str]
    fonts: Dict[str, str]
    preview_gradient: str


class BrandingResponse(BaseModel):
    """Full branding configuration response"""
    tenant_id: str
    preset_theme: str
    dark_mode_enabled: bool
    logos: Dict[str, Optional[str]]
    colors: Dict[str, str]
    fonts: Dict[str, str]
    custom_css: Optional[str]


# ==================== Helper Functions ====================

def db_to_branding_response(db_record: Dict[str, Any], config: ClientConfig) -> Dict[str, Any]:
    """Convert database record to branding response format"""
    if not db_record:
        # Return defaults from config + preset
        preset = get_preset("professional_blue")
        return {
            "tenant_id": config.client_id,
            "preset_theme": "professional_blue",
            "dark_mode_enabled": False,
            "logos": {
                "primary": config.logo_url,
                "dark": None,
                "favicon": None
            },
            "colors": {
                **preset["colors"],
                # Override with config values if present
                "primary": config.primary_color or preset["colors"]["primary"],
                "secondary": config.secondary_color or preset["colors"]["secondary"]
            },
            "fonts": preset["fonts"],
            "custom_css": None,
            "login_background_url": None,
            "login_background_gradient": None
        }

    # Build colors from db fields
    colors = {}
    preset = get_preset(db_record.get("preset_theme", "professional_blue"))

    # Start with preset colors as defaults
    colors = preset["colors"].copy()

    # Override with any custom colors from db
    color_fields = [
        "primary", "primary_light", "primary_dark",
        "secondary", "secondary_light", "secondary_dark",
        "accent", "success", "warning", "error",
        "background", "surface", "surface_elevated",
        "text_primary", "text_secondary", "text_muted",
        "border", "border_light",
        # Sidebar colors
        "sidebar_bg", "sidebar_text", "sidebar_text_muted",
        "sidebar_hover", "sidebar_active_bg", "sidebar_active_text"
    ]

    for field in color_fields:
        db_key = f"color_{field}"
        if db_record.get(db_key):
            colors[field] = db_record[db_key]

    # Apply dark mode if enabled
    if db_record.get("dark_mode_enabled"):
        colors = apply_dark_mode(colors)

    # Build fonts
    fonts = preset["fonts"].copy()
    if db_record.get("font_family_heading"):
        fonts["heading"] = db_record["font_family_heading"]
    if db_record.get("font_family_body"):
        fonts["body"] = db_record["font_family_body"]

    return {
        "tenant_id": db_record["tenant_id"],
        "preset_theme": db_record.get("preset_theme", "professional_blue"),
        "dark_mode_enabled": db_record.get("dark_mode_enabled", False),
        "logos": {
            "primary": db_record.get("logo_url") or config.logo_url,
            "dark": db_record.get("logo_dark_url"),
            "favicon": db_record.get("favicon_url")
        },
        "colors": colors,
        "fonts": fonts,
        "custom_css": db_record.get("custom_css"),
        # Login page customization
        "login_background_url": db_record.get("login_background_url"),
        "login_background_gradient": db_record.get("login_background_gradient")
    }


# ==================== Endpoints ====================

@branding_router.get("")
async def get_branding(config: ClientConfig = Depends(get_client_config)):
    """
    Get tenant branding configuration

    Returns merged branding from database + config defaults + preset defaults.
    """
    db_branding = None
    try:
        supabase = SupabaseTool(config)
        db_branding = supabase.get_branding()
    except Exception as e:
        logger.warning(f"Could not fetch branding from database: {e}")

    # Always return valid branding (from DB or defaults)
    branding = db_to_branding_response(db_branding, config)

    return {
        "success": True,
        "data": branding
    }


@branding_router.put("")
async def update_branding(
    data: BrandingUpdate,
    config: ClientConfig = Depends(get_client_config)
):
    """
    Update tenant branding configuration

    Supports partial updates - only specified fields are changed.
    """
    # Convert colors to dict if provided
    colors_dict = None
    if data.colors:
        colors_dict = {k: v for k, v in data.colors.model_dump().items() if v is not None}

    # Convert fonts to dict if provided
    fonts_dict = None
    if data.fonts:
        fonts_dict = {k: v for k, v in data.fonts.model_dump().items() if v is not None}

    result = None
    try:
        supabase = SupabaseTool(config)
        result = supabase.update_branding(
            preset_theme=data.preset_theme,
            colors=colors_dict,
            fonts=fonts_dict,
            logo_url=data.logo_url,
            logo_dark_url=data.logo_dark_url,
            favicon_url=data.favicon_url,
            dark_mode_enabled=data.dark_mode_enabled,
            custom_css=data.custom_css,
            login_background_url=data.login_background_url,
            login_background_gradient=data.login_background_gradient
        )
    except Exception as e:
        logger.warning(f"Database branding update failed: {e}")

    if result:
        branding = db_to_branding_response(result, config)
        return {
            "success": True,
            "data": branding,
            "message": "Branding updated successfully"
        }

    # Return updated branding based on request even if DB save failed
    preset = get_preset(data.preset_theme or "professional_blue")
    branding = {
        "tenant_id": config.client_id,
        "preset_theme": data.preset_theme or "professional_blue",
        "dark_mode_enabled": data.dark_mode_enabled or False,
        "logos": {
            "primary": data.logo_url or config.logo_url,
            "dark": data.logo_dark_url,
            "favicon": data.favicon_url
        },
        "colors": {**preset["colors"], **(colors_dict or {})},
        "fonts": {**preset["fonts"], **(fonts_dict or {})},
        "custom_css": data.custom_css
    }

    return {
        "success": True,
        "data": branding,
        "message": "Branding updated (local only)"
    }


@branding_router.get("/presets")
async def get_theme_presets():
    """
    Get available theme presets

    Returns all predefined themes that tenants can choose from.
    """
    presets = []

    for preset_id, preset_data in get_all_presets().items():
        presets.append({
            "id": preset_id,
            "name": preset_data["name"],
            "description": preset_data["description"],
            "colors": preset_data["colors"],
            "fonts": preset_data["fonts"],
            "preview_gradient": preset_data["preview_gradient"]
        })

    return {
        "success": True,
        "data": presets,
        "count": len(presets)
    }


@branding_router.post("/apply-preset/{preset_name}")
async def apply_preset(
    preset_name: str,
    config: ClientConfig = Depends(get_client_config)
):
    """
    Apply a theme preset

    Resets all color and font customizations to the preset values.
    """
    if preset_name not in THEME_PRESETS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid preset. Available: {', '.join(THEME_PRESETS.keys())}"
        )

    preset = get_preset(preset_name)

    try:
        supabase = SupabaseTool(config)
        result = supabase.update_branding(
            preset_theme=preset_name,
            colors=preset["colors"],
            fonts=preset["fonts"]
        )

        if result:
            branding = db_to_branding_response(result, config)
            return {
                "success": True,
                "data": branding,
                "message": f"Applied '{preset['name']}' theme"
            }
    except Exception as e:
        logger.warning(f"Database branding update failed (table may not exist): {e}")

    # Return preset as branding even if DB save failed
    # This allows the frontend to work without a branding table
    branding = {
        "tenant_id": config.client_id,
        "preset_theme": preset_name,
        "dark_mode_enabled": False,
        "logos": {
            "primary": config.logo_url,
            "dark": None,
            "favicon": None
        },
        "colors": preset["colors"],
        "fonts": preset["fonts"],
        "custom_css": None
    }

    return {
        "success": True,
        "data": branding,
        "message": f"Applied '{preset['name']}' theme (local only)"
    }


@branding_router.post("/upload/logo")
async def upload_logo(
    file: UploadFile = File(...),
    logo_type: str = Form(default="primary"),
    config: ClientConfig = Depends(get_client_config)
):
    """
    Upload logo or favicon

    Args:
        file: Image file (PNG, JPG, JPEG, SVG, ICO)
        logo_type: Type of logo (primary, dark, favicon)
    """
    # Validate logo type
    valid_types = ["primary", "dark", "favicon", "email"]
    if logo_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid logo_type. Must be one of: {', '.join(valid_types)}"
        )

    # Validate file type
    allowed_extensions = ["png", "jpg", "jpeg", "svg", "ico"]
    ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )

    # Validate file size (max 5MB)
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 5MB.")

    try:
        supabase = SupabaseTool(config)

        # Upload to storage (will raise exception with details on failure)
        public_url = supabase.upload_logo_to_storage(
            file_content=content,
            file_name=file.filename,
            logo_type=logo_type
        )

        # Update branding with new URL
        update_field = {
            "primary": "logo_url",
            "dark": "logo_dark_url",
            "favicon": "favicon_url",
            "email": "logo_email_url"
        }[logo_type]

        result = supabase.update_branding(**{update_field: public_url})

        return {
            "success": True,
            "data": {
                "logo_type": logo_type,
                "url": public_url,
                "filename": file.filename,
                "size": len(content)
            },
            "message": f"{logo_type.title()} logo uploaded successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "uploading logo", e, logger)


@branding_router.post("/upload/background")
async def upload_login_background(
    file: UploadFile = File(...),
    config: ClientConfig = Depends(get_client_config)
):
    """
    Upload login page background image

    Args:
        file: Image file (PNG, JPG, JPEG, WEBP)
    """
    # Validate file type
    allowed_extensions = ["png", "jpg", "jpeg", "webp"]
    ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )

    # Validate file size (max 10MB for backgrounds)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 10MB.")

    try:
        supabase = SupabaseTool(config)

        # Upload to storage with login-background path
        storage_path = f"branding/{config.client_id}/login-background.{ext}"
        bucket = supabase.client.storage.from_("tenant-assets")

        # Try to remove existing file first
        try:
            bucket.remove([storage_path])
        except Exception:
            pass

        # Upload new file
        bucket.upload(
            path=storage_path,
            file=content,
            file_options={"content-type": f"image/{ext}"}
        )

        # Get public URL
        public_url = bucket.get_public_url(storage_path)

        # Update branding with new URL
        result = supabase.update_branding(login_background_url=public_url)

        return {
            "success": True,
            "data": {
                "url": public_url,
                "filename": file.filename,
                "size": len(content)
            },
            "message": "Login background uploaded successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "uploading login background", e, logger)


@branding_router.post("/reset")
async def reset_branding(config: ClientConfig = Depends(get_client_config)):
    """
    Reset branding to defaults

    Deletes custom branding and reverts to config.yaml + default preset values.
    """
    try:
        supabase = SupabaseTool(config)
        supabase.delete_branding()
    except Exception as e:
        logger.warning(f"Failed to delete branding from DB (may not exist): {e}")

    # Always return default branding
    branding = db_to_branding_response(None, config)

    return {
        "success": True,
        "data": branding,
        "message": "Branding reset to defaults"
    }


@branding_router.get("/fonts")
async def get_available_fonts():
    """
    Get available Google Fonts for selection

    Returns list of fonts that can be used for headings and body text.
    """
    return {
        "success": True,
        "data": GOOGLE_FONTS,
        "count": len(GOOGLE_FONTS)
    }


@branding_router.post("/preview")
async def preview_branding(
    data: BrandingUpdate,
    config: ClientConfig = Depends(get_client_config)
):
    """
    Generate preview branding without saving

    Returns what the branding would look like with the given changes.
    Useful for live preview in the settings UI.
    """
    current = None
    try:
        supabase = SupabaseTool(config)
        current = supabase.get_branding()
    except Exception as e:
        logger.warning(f"Could not fetch current branding: {e}")

    # Start with current or defaults
    preview = db_to_branding_response(current, config)

    # Apply preview changes
    if data.preset_theme:
        preset = get_preset(data.preset_theme)
        preview["preset_theme"] = data.preset_theme
        preview["colors"] = preset["colors"].copy()
        preview["fonts"] = preset["fonts"].copy()

    if data.dark_mode_enabled is not None:
        preview["dark_mode_enabled"] = data.dark_mode_enabled
        if data.dark_mode_enabled:
            preview["colors"] = apply_dark_mode(preview["colors"])

    if data.colors:
        for key, value in data.colors.model_dump().items():
            if value:
                preview["colors"][key] = value

    if data.fonts:
        if data.fonts.heading:
            preview["fonts"]["heading"] = data.fonts.heading
        if data.fonts.body:
            preview["fonts"]["body"] = data.fonts.body

    if data.logo_url:
        preview["logos"]["primary"] = data.logo_url
    if data.logo_dark_url:
        preview["logos"]["dark"] = data.logo_dark_url
    if data.favicon_url:
        preview["logos"]["favicon"] = data.favicon_url
    if data.custom_css:
        preview["custom_css"] = data.custom_css

    return {
        "success": True,
        "data": preview,
        "is_preview": True
    }


@branding_router.get("/css-variables")
async def get_css_variables(config: ClientConfig = Depends(get_client_config)):
    """
    Get CSS variables for current branding

    Returns CSS variable definitions that can be injected into the page.
    """
    db_branding = None
    try:
        supabase = SupabaseTool(config)
        db_branding = supabase.get_branding()
    except Exception as e:
        logger.warning(f"Could not fetch branding from DB: {e}")

    branding = db_to_branding_response(db_branding, config)

    # Build CSS variable string
    css_vars = []
    css_vars.append(":root {")

    # Colors
    color_map = {
        "primary": "--color-primary",
        "primary_light": "--color-primary-light",
        "primary_dark": "--color-primary-dark",
        "secondary": "--color-secondary",
        "secondary_light": "--color-secondary-light",
        "secondary_dark": "--color-secondary-dark",
        "accent": "--color-accent",
        "success": "--color-success",
        "warning": "--color-warning",
        "error": "--color-error",
        "background": "--color-background",
        "surface": "--color-surface",
        "surface_elevated": "--color-surface-elevated",
        "text_primary": "--color-text-primary",
        "text_secondary": "--color-text-secondary",
        "text_muted": "--color-text-muted",
        "border": "--color-border",
        "border_light": "--color-border-light"
    }

    for key, css_var in color_map.items():
        if key in branding["colors"]:
            css_vars.append(f"  {css_var}: {branding['colors'][key]};")

    # Fonts
    if branding["fonts"].get("heading"):
        css_vars.append(f"  --font-family-heading: {branding['fonts']['heading']};")
    if branding["fonts"].get("body"):
        css_vars.append(f"  --font-family-body: {branding['fonts']['body']};")

    css_vars.append("}")

    # Add custom CSS if present
    if branding.get("custom_css"):
        css_vars.append("")
        css_vars.append("/* Custom CSS */")
        css_vars.append(branding["custom_css"])

    css_string = "\n".join(css_vars)

    return {
        "success": True,
        "data": {
            "css": css_string,
            "branding": branding
        }
    }
