-- Organization User Management Tables
-- Run this in your Supabase SQL Editor

-- ============================================
-- Table: organization_users
-- Links Supabase Auth users to tenant organizations
-- ============================================
CREATE TABLE IF NOT EXISTS organization_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(50) NOT NULL,
    auth_user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    is_active BOOLEAN DEFAULT true,
    invited_by UUID REFERENCES organization_users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    UNIQUE(tenant_id, email)
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_org_users_tenant ON organization_users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_org_users_auth_id ON organization_users(auth_user_id);
CREATE INDEX IF NOT EXISTS idx_org_users_email ON organization_users(email);

-- ============================================
-- Table: user_invitations
-- Tracks pending user invitations
-- ============================================
CREATE TABLE IF NOT EXISTS user_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(50) NOT NULL,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    token VARCHAR(64) NOT NULL UNIQUE,
    invited_by UUID REFERENCES organization_users(id),
    expires_at TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, email)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_invitations_token ON user_invitations(token);
CREATE INDEX IF NOT EXISTS idx_invitations_tenant ON user_invitations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_invitations_email ON user_invitations(email);

-- ============================================
-- Row Level Security (RLS)
-- ============================================

-- Enable RLS
ALTER TABLE organization_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_invitations ENABLE ROW LEVEL SECURITY;

-- Policy: Service role can do everything (for backend API)
CREATE POLICY "Service role full access to organization_users" ON organization_users
    FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access to user_invitations" ON user_invitations
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- ============================================
-- Updated_at trigger
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_organization_users_updated_at
    BEFORE UPDATE ON organization_users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Helper function: Get user by auth ID
-- ============================================
CREATE OR REPLACE FUNCTION get_user_by_auth_id(p_auth_user_id UUID)
RETURNS TABLE (
    id UUID,
    tenant_id VARCHAR,
    email VARCHAR,
    name VARCHAR,
    role VARCHAR,
    is_active BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ou.id,
        ou.tenant_id,
        ou.email,
        ou.name,
        ou.role,
        ou.is_active
    FROM organization_users ou
    WHERE ou.auth_user_id = p_auth_user_id
    AND ou.is_active = true;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
