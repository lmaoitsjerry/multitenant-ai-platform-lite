-- Central tenant registry table
-- This table provides a single source of truth for all tenants in the system
-- Run this in the Supabase SQL Editor

-- Create tenants table
CREATE TABLE IF NOT EXISTS tenants (
    id VARCHAR(50) PRIMARY KEY,  -- e.g., tn_xxx_yyy or legacy names like 'africastay'
    name VARCHAR(255) NOT NULL,
    short_name VARCHAR(50),

    -- Status and plan
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'deleted')),
    plan VARCHAR(50) DEFAULT 'lite' CHECK (plan IN ('lite', 'pro', 'enterprise')),

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID,  -- References organization_users(id) but not enforced for migration flexibility
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    -- Contact info (denormalized for quick access)
    admin_email VARCHAR(255),
    support_email VARCHAR(255),

    -- Quotas
    max_users INT DEFAULT 5,
    max_monthly_quotes INT DEFAULT 100,
    max_storage_gb INT DEFAULT 1,

    -- Feature flags
    features_enabled JSONB DEFAULT '{"ai_helpdesk": true, "email_quotes": true, "voice_calls": false}'::jsonb
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants(status);
CREATE INDEX IF NOT EXISTS idx_tenants_plan ON tenants(plan);
CREATE INDEX IF NOT EXISTS idx_tenants_created_at ON tenants(created_at);
CREATE INDEX IF NOT EXISTS idx_tenants_admin_email ON tenants(admin_email);

-- Enable RLS
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;

-- Policy: Service role has full access (used by backend)
CREATE POLICY "Service role has full access to tenants" ON tenants
    FOR ALL
    USING (auth.role() = 'service_role');

-- Policy: Users can only view their own tenant
CREATE POLICY "Users can view own tenant" ON tenants
    FOR SELECT
    USING (id = current_setting('app.tenant_id', true));

-- Grant permissions
GRANT ALL ON tenants TO authenticated;
GRANT ALL ON tenants TO service_role;

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_tenants_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW
    EXECUTE FUNCTION update_tenants_updated_at();

-- Add comment for documentation
COMMENT ON TABLE tenants IS 'Central registry of all tenants in the multi-tenant platform';
COMMENT ON COLUMN tenants.id IS 'Unique tenant identifier (e.g., tn_xxx_yyy)';
COMMENT ON COLUMN tenants.status IS 'Tenant status: active, suspended, or deleted';
COMMENT ON COLUMN tenants.plan IS 'Subscription plan: lite, pro, or enterprise';
