-- Migration: Rename 'user' role to 'consultant' and add consultant tracking to invoices
-- Date: 2025-01-04
-- Description:
--   1. Renames the 'user' role to 'consultant' across all tables
--   2. Updates constraints to reflect new role naming
--   3. Adds consultant_id to invoices table for performance tracking

-- =====================================================
-- PART 1: Rename 'user' role to 'consultant'
-- =====================================================

-- Update existing users with 'user' role to 'consultant'
UPDATE organization_users SET role = 'consultant' WHERE role = 'user';
UPDATE user_invitations SET role = 'consultant' WHERE role = 'user';

-- Drop existing CHECK constraints
ALTER TABLE organization_users DROP CONSTRAINT IF EXISTS organization_users_role_check;
ALTER TABLE user_invitations DROP CONSTRAINT IF EXISTS user_invitations_role_check;

-- Add new CHECK constraints with 'consultant' instead of 'user'
ALTER TABLE organization_users
    ADD CONSTRAINT organization_users_role_check
    CHECK (role IN ('admin', 'consultant'));

ALTER TABLE user_invitations
    ADD CONSTRAINT user_invitations_role_check
    CHECK (role IN ('admin', 'consultant'));

-- Update default values
ALTER TABLE organization_users ALTER COLUMN role SET DEFAULT 'consultant';
ALTER TABLE user_invitations ALTER COLUMN role SET DEFAULT 'consultant';

-- =====================================================
-- PART 2: Add consultant_id to invoices table
-- =====================================================

-- Add consultant_id column to invoices (references the consultant who created/owns the invoice)
ALTER TABLE invoices
    ADD COLUMN IF NOT EXISTS consultant_id UUID REFERENCES organization_users(id);

-- Create index for performance when querying by consultant
CREATE INDEX IF NOT EXISTS idx_invoices_consultant ON invoices(consultant_id);

-- =====================================================
-- PART 3: Add consultant_id to quotes table (if not exists)
-- =====================================================

-- Ensure quotes table has consultant_id (may already exist)
ALTER TABLE quotes
    ADD COLUMN IF NOT EXISTS consultant_id UUID REFERENCES organization_users(id);

-- Create index for performance when querying by consultant
CREATE INDEX IF NOT EXISTS idx_quotes_consultant ON quotes(consultant_id);

-- =====================================================
-- VERIFICATION QUERIES (run these to confirm migration)
-- =====================================================
-- SELECT DISTINCT role FROM organization_users;  -- Should show 'admin', 'consultant'
-- SELECT DISTINCT role FROM user_invitations;    -- Should show 'admin', 'consultant'
-- SELECT column_name FROM information_schema.columns WHERE table_name = 'invoices' AND column_name = 'consultant_id';
-- SELECT column_name FROM information_schema.columns WHERE table_name = 'quotes' AND column_name = 'consultant_id';
