-- ============================================
-- Sidebar Branding Colors
-- Run this in your Supabase SQL Editor
-- ============================================
-- Adds sidebar-specific color columns to tenant_branding
-- for whitelabel sidebar customization.

-- Add sidebar color columns to existing table
ALTER TABLE tenant_branding
ADD COLUMN IF NOT EXISTS color_sidebar_bg TEXT,
ADD COLUMN IF NOT EXISTS color_sidebar_text TEXT,
ADD COLUMN IF NOT EXISTS color_sidebar_text_muted TEXT,
ADD COLUMN IF NOT EXISTS color_sidebar_hover TEXT,
ADD COLUMN IF NOT EXISTS color_sidebar_active_bg TEXT,
ADD COLUMN IF NOT EXISTS color_sidebar_active_text TEXT;

-- Verify columns were added
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'tenant_branding'
AND column_name LIKE 'color_sidebar%'
ORDER BY column_name;
