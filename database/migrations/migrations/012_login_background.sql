-- ============================================
-- Login Background Customization
-- Run this in your Supabase SQL Editor
-- ============================================
-- Adds login page background customization columns to tenant_branding.

-- Add login background columns
ALTER TABLE tenant_branding
ADD COLUMN IF NOT EXISTS login_background_url TEXT,
ADD COLUMN IF NOT EXISTS login_background_gradient TEXT;

-- Verify columns were added
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'tenant_branding'
AND column_name LIKE 'login_background%'
ORDER BY column_name;
