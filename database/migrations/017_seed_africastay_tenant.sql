-- ============================================
-- Seed AfricaStay Demo Tenant
-- Migration 017: Create africastay tenant record
-- Run this in your Supabase SQL Editor
-- ============================================
--
-- This creates the africastay demo tenant that is required
-- for the platform to function. Without this record, all
-- authenticated API requests will fail with 400 errors.
--
-- Depends on:
--   011_tenants_registry.sql (tenants table)
--   014_tenant_config.sql (tenant_config column)
-- ============================================

-- Insert africastay tenant (or update if exists)
INSERT INTO tenants (
    id,
    name,
    short_name,
    status,
    plan,
    admin_email,
    support_email,
    max_users,
    max_monthly_quotes,
    max_storage_gb,
    features_enabled,
    timezone,
    currency,
    primary_email,
    gcp_project_id,
    gcp_dataset,
    config_source,
    tenant_config
) VALUES (
    'africastay',
    'AfricaStay',
    'africastay',
    'active',
    'pro',
    'demo@africastay.com',
    'support@africastay.com',
    50,
    10000,
    10,
    '{"ai_helpdesk": true, "email_quotes": true, "voice_calls": true, "analytics": true, "crm": true}'::jsonb,
    'Africa/Johannesburg',
    'ZAR',
    'quotes@africastay.com',
    NULL,  -- Set from env: GCP_PROJECT_ID
    NULL,  -- Set from env: GCP_DATASET or default to tenant_id
    'database',
    '{
        "branding": {
            "company_name": "AfricaStay",
            "primary_color": "#2E86AB",
            "secondary_color": "#4ECDC4",
            "accent_color": "#FFE66D",
            "email_signature": "Best regards,\nThe AfricaStay Team"
        },
        "destinations": [
            {"name": "Zanzibar", "code": "ZNZ", "enabled": true, "aliases": ["Stone Town", "Unguja"]},
            {"name": "Maldives", "code": "MLE", "enabled": true},
            {"name": "Mauritius", "code": "MRU", "enabled": true},
            {"name": "Seychelles", "code": "SEZ", "enabled": true},
            {"name": "Cape Town", "code": "CPT", "enabled": true},
            {"name": "Kruger National Park", "code": "KNP", "enabled": true},
            {"name": "Victoria Falls", "code": "VFA", "enabled": true}
        ],
        "infrastructure": {
            "gcp": {
                "region": "us-central1",
                "shared_pricing_dataset": "africastay_analytics"
            },
            "vapi": {},
            "openai": {
                "model": "gpt-4o-mini"
            }
        },
        "email": {
            "sendgrid": {
                "from_email": "quotes@africastay.com",
                "from_name": "AfricaStay",
                "reply_to": "quotes@africastay.com"
            }
        },
        "banking": {
            "bank_name": "First National Bank",
            "account_name": "AfricaStay Tours",
            "account_number": "123456789",
            "branch_code": "250655",
            "swift_code": "FIRNZAJJ",
            "reference_prefix": "AS"
        },
        "quotes": {
            "auto_send": true,
            "validity_days": 14,
            "follow_up_days": 3
        },
        "agents": {
            "inbound": {"enabled": true},
            "helpdesk": {"enabled": true},
            "outbound": {"enabled": false}
        },
        "pricing": {
            "currency_margin_pct": 5.0,
            "display_currency": "ZAR"
        }
    }'::jsonb
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    short_name = EXCLUDED.short_name,
    status = EXCLUDED.status,
    plan = EXCLUDED.plan,
    admin_email = EXCLUDED.admin_email,
    support_email = EXCLUDED.support_email,
    max_users = EXCLUDED.max_users,
    max_monthly_quotes = EXCLUDED.max_monthly_quotes,
    max_storage_gb = EXCLUDED.max_storage_gb,
    features_enabled = EXCLUDED.features_enabled,
    timezone = EXCLUDED.timezone,
    currency = EXCLUDED.currency,
    primary_email = EXCLUDED.primary_email,
    config_source = EXCLUDED.config_source,
    tenant_config = EXCLUDED.tenant_config,
    updated_at = NOW();

-- Verify the tenant was created/updated
SELECT id, name, status, plan, config_source, created_at, updated_at
FROM tenants
WHERE id = 'africastay';

/*
============================================
After running this migration:
============================================

1. The africastay tenant will exist in the database
2. All API requests with X-Client-ID: africastay will work
3. The demo@africastay.com user can log in and access the dashboard

To add more tenants, copy this pattern and change:
- id: unique tenant identifier
- name: display name
- tenant_config: customize branding, destinations, etc.

Note: API keys and secrets are resolved from environment variables:
- OPENAI_API_KEY
- SENDGRID_MASTER_API_KEY (or AFRICASTAY_SENDGRID_API_KEY)
- SUPABASE_URL, SUPABASE_SERVICE_KEY
- GCP_PROJECT_ID
============================================
*/
