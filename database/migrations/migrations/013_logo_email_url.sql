-- ============================================
-- Email Logo Column
-- Run this in your Supabase SQL Editor
-- ============================================
-- Adds logo_email_url column to tenant_branding table.
-- This column stores the URL for the logo used in email templates.

-- Add email logo column
ALTER TABLE tenant_branding
ADD COLUMN IF NOT EXISTS logo_email_url TEXT;

-- Verify column was added
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'tenant_branding'
AND column_name = 'logo_email_url';
