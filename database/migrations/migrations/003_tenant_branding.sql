-- Create tenant_branding table for storing theme customizations
-- Run this in the Supabase SQL Editor

CREATE TABLE IF NOT EXISTS tenant_branding (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL UNIQUE,
    preset_theme TEXT DEFAULT 'professional_blue',
    dark_mode_enabled BOOLEAN DEFAULT FALSE,

    -- Logos
    logo_url TEXT,
    logo_dark_url TEXT,
    favicon_url TEXT,

    -- Primary colors
    color_primary TEXT,
    color_primary_light TEXT,
    color_primary_dark TEXT,

    -- Secondary colors
    color_secondary TEXT,
    color_secondary_light TEXT,
    color_secondary_dark TEXT,

    -- Accent colors
    color_accent TEXT,
    color_success TEXT,
    color_warning TEXT,
    color_error TEXT,

    -- Background colors
    color_background TEXT,
    color_surface TEXT,
    color_surface_elevated TEXT,

    -- Text colors
    color_text_primary TEXT,
    color_text_secondary TEXT,
    color_text_muted TEXT,

    -- Border colors
    color_border TEXT,
    color_border_light TEXT,

    -- Fonts
    font_family_heading TEXT,
    font_family_body TEXT,

    -- Custom CSS
    custom_css TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_tenant_branding_tenant_id ON tenant_branding(tenant_id);

-- Enable RLS
ALTER TABLE tenant_branding ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own tenant's branding
CREATE POLICY "Users can view own tenant branding" ON tenant_branding
    FOR SELECT
    USING (tenant_id = current_setting('app.tenant_id', true));

-- Policy: Users can insert their own tenant's branding
CREATE POLICY "Users can insert own tenant branding" ON tenant_branding
    FOR INSERT
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- Policy: Users can update their own tenant's branding
CREATE POLICY "Users can update own tenant branding" ON tenant_branding
    FOR UPDATE
    USING (tenant_id = current_setting('app.tenant_id', true));

-- Policy: Users can delete their own tenant's branding
CREATE POLICY "Users can delete own tenant branding" ON tenant_branding
    FOR DELETE
    USING (tenant_id = current_setting('app.tenant_id', true));

-- For service role access (bypasses RLS)
CREATE POLICY "Service role has full access to tenant_branding" ON tenant_branding
    FOR ALL
    USING (auth.role() = 'service_role');

-- Grant permissions
GRANT ALL ON tenant_branding TO authenticated;
GRANT ALL ON tenant_branding TO service_role;
