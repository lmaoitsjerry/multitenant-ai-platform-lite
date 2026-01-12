-- Create tenant_settings table for storing company, email, and banking configuration
-- Run this in the Supabase SQL Editor

CREATE TABLE IF NOT EXISTS tenant_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL UNIQUE,

    -- Company Information
    company_name TEXT,
    support_email TEXT,
    support_phone TEXT,
    website TEXT,
    currency TEXT DEFAULT 'USD',
    timezone TEXT DEFAULT 'UTC',

    -- Email Configuration
    email_from_name TEXT,
    email_from_email TEXT,
    email_reply_to TEXT,
    quotes_email TEXT,

    -- Banking Details (for invoices)
    bank_name TEXT,
    bank_account_name TEXT,
    bank_account_number TEXT,
    bank_branch_code TEXT,
    bank_swift_code TEXT,
    payment_reference_prefix TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_tenant_settings_tenant_id ON tenant_settings(tenant_id);

-- Enable RLS
ALTER TABLE tenant_settings ENABLE ROW LEVEL SECURITY;

-- Policy: Service role has full access (used by backend)
CREATE POLICY "Service role has full access to tenant_settings" ON tenant_settings
    FOR ALL
    USING (auth.role() = 'service_role');

-- Policy: Users can only view their own tenant's settings (if using authenticated role)
CREATE POLICY "Users can view own tenant settings" ON tenant_settings
    FOR SELECT
    USING (tenant_id = current_setting('app.tenant_id', true));

-- Policy: Users can update their own tenant's settings
CREATE POLICY "Users can update own tenant settings" ON tenant_settings
    FOR UPDATE
    USING (tenant_id = current_setting('app.tenant_id', true));

-- Policy: Users can insert their own tenant's settings
CREATE POLICY "Users can insert own tenant settings" ON tenant_settings
    FOR INSERT
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- Grant permissions
GRANT ALL ON tenant_settings TO authenticated;
GRANT ALL ON tenant_settings TO service_role;

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_tenant_settings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_tenant_settings_updated_at
    BEFORE UPDATE ON tenant_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_tenant_settings_updated_at();
