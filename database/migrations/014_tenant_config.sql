-- ============================================
-- Tenant Configuration JSONB Extension
-- Migration 014: Extend tenants registry with full config
-- Run this in your Supabase SQL Editor
-- ============================================
--
-- Purpose: Enable storing complete tenant configuration in database
-- instead of YAML files. Uses hybrid approach: core fields in columns,
-- extended config in JSONB.
--
-- Depends on: 011_tenants_registry.sql (tenants table must exist)
-- ============================================

-- ============================================
-- 1. Add tenant_config JSONB column
-- ============================================
-- Stores complete tenant configuration including branding, destinations,
-- infrastructure refs, email settings, consultants, and agent config.
-- Note: API keys and secrets are NOT stored here - they use env var refs.

ALTER TABLE tenants
ADD COLUMN IF NOT EXISTS tenant_config JSONB DEFAULT '{}'::jsonb;

COMMENT ON COLUMN tenants.tenant_config IS 'Full tenant configuration (branding, destinations, infrastructure refs, email settings, consultants, agents). Secrets stored as env var references only.';

-- ============================================
-- 2. Add denormalized columns for common queries
-- ============================================
-- These columns duplicate data from tenant_config for faster queries
-- without JSONB parsing. Keep in sync via application layer.

ALTER TABLE tenants
ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'Africa/Johannesburg';

ALTER TABLE tenants
ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'ZAR';

ALTER TABLE tenants
ADD COLUMN IF NOT EXISTS primary_email VARCHAR(255);

ALTER TABLE tenants
ADD COLUMN IF NOT EXISTS gcp_project_id VARCHAR(100);

ALTER TABLE tenants
ADD COLUMN IF NOT EXISTS gcp_dataset VARCHAR(100);

COMMENT ON COLUMN tenants.timezone IS 'IANA timezone (e.g., Africa/Johannesburg). Denormalized from tenant_config for fast queries.';
COMMENT ON COLUMN tenants.currency IS 'ISO 4217 currency code (e.g., ZAR, USD). Denormalized from tenant_config.';
COMMENT ON COLUMN tenants.primary_email IS 'Primary contact/quotes email. Denormalized from tenant_config.email.primary.';
COMMENT ON COLUMN tenants.gcp_project_id IS 'GCP project ID for BigQuery/Vertex AI. Denormalized from tenant_config.infrastructure.gcp.project_id.';
COMMENT ON COLUMN tenants.gcp_dataset IS 'BigQuery dataset name. Denormalized from tenant_config.infrastructure.gcp.dataset.';

-- ============================================
-- 3. Add config_source column for dual-mode operation
-- ============================================
-- Enables gradual migration: existing tenants can remain on YAML while
-- new tenants use database config. Loader checks this to determine source.

ALTER TABLE tenants
ADD COLUMN IF NOT EXISTS config_source VARCHAR(20) DEFAULT 'database';

-- Add CHECK constraint if not exists (PostgreSQL 9.4+ pattern)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'tenants_config_source_check'
    ) THEN
        ALTER TABLE tenants
        ADD CONSTRAINT tenants_config_source_check
        CHECK (config_source IN ('yaml', 'database'));
    END IF;
END $$;

COMMENT ON COLUMN tenants.config_source IS 'Configuration source: yaml (legacy file-based) or database (new DB-backed). Default: database.';

-- ============================================
-- 4. Add suspension columns
-- ============================================
-- Allows suspending tenants with audit trail

ALTER TABLE tenants
ADD COLUMN IF NOT EXISTS suspended_at TIMESTAMPTZ;

ALTER TABLE tenants
ADD COLUMN IF NOT EXISTS suspended_reason TEXT;

COMMENT ON COLUMN tenants.suspended_at IS 'Timestamp when tenant was suspended (NULL if active).';
COMMENT ON COLUMN tenants.suspended_reason IS 'Reason for suspension (for audit/support).';

-- ============================================
-- 5. Create GIN index for JSONB queries
-- ============================================
-- Enables efficient queries like:
--   WHERE tenant_config @> '{"branding": {"company_name": "X"}}'
--   WHERE tenant_config -> 'destinations' @> '[{"code": "ZNZ"}]'

CREATE INDEX IF NOT EXISTS idx_tenants_tenant_config
ON tenants USING GIN (tenant_config);

-- Index on config_source for filtering
CREATE INDEX IF NOT EXISTS idx_tenants_config_source
ON tenants(config_source);

-- Index on primary_email for lookups
CREATE INDEX IF NOT EXISTS idx_tenants_primary_email
ON tenants(primary_email)
WHERE primary_email IS NOT NULL;

-- ============================================
-- 6. Verify migration
-- ============================================
-- Returns the new columns to confirm they were added

SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'tenants'
AND column_name IN (
    'tenant_config',
    'timezone',
    'currency',
    'primary_email',
    'gcp_project_id',
    'gcp_dataset',
    'config_source',
    'suspended_at',
    'suspended_reason'
)
ORDER BY ordinal_position;

/*
============================================
tenant_config JSONB Structure
============================================

The tenant_config column stores the complete tenant configuration
as a JSONB document. Structure:

{
  "branding": {
    "company_name": "string",
    "logo_url": "string|null",
    "primary_color": "#hex",
    "secondary_color": "#hex",
    "accent_color": "#hex|null",
    "theme_id": "string|null",
    "email_signature": "string"
  },
  "destinations": [
    {
      "name": "string",
      "code": "ABC",
      "enabled": true,
      "aliases": ["string"] (optional)
    }
  ],
  "infrastructure": {
    "gcp": {
      "project_id": "string (also in column)",
      "region": "string",
      "dataset": "string (also in column)",
      "shared_pricing_dataset": "string|null",
      "corpus_id": "string|null"
    },
    "supabase": {
      "url": "string"
    },
    "vapi": {
      "phone_number_id": "string|null",
      "assistant_id": "string|null",
      "outbound_assistant_id": "string|null"
    },
    "openai": {
      "model": "gpt-4o-mini"
    }
  },
  "email": {
    "primary": "email@domain.com (also in column)",
    "sendgrid": {
      "from_email": "string",
      "from_name": "string",
      "reply_to": "string"
    },
    "smtp": {
      "host": "string",
      "port": 465,
      "username": "string"
    },
    "imap": {
      "host": "string",
      "port": 993
    }
  },
  "banking": {
    "bank_name": "string",
    "account_name": "string",
    "account_number": "string",
    "branch_code": "string",
    "swift_code": "string",
    "reference_prefix": "XX"
  },
  "outbound": {
    "enabled": true,
    "timing": "string|null",
    "call_window": {...},
    "call_days": [...],
    "max_attempts": 3,
    "min_quote_value": 0
  },
  "quotes": {
    "auto_send": true,
    "validity_days": 14,
    "follow_up_days": 3
  },
  "consultants": [
    {
      "id": "string",
      "name": "string",
      "email": "string",
      "active": true
    }
  ],
  "agents": {
    "inbound": {
      "enabled": true,
      "name": "string|null",
      "voice_id": "string|null",
      "prompt_file": "string|null"
    },
    "helpdesk": {
      "enabled": true,
      "prompt_file": "string|null"
    },
    "outbound": {
      "enabled": true,
      "name": "string|null",
      "voice_id": "string|null",
      "prompt_file": "string|null"
    }
  },
  "knowledge_base": {
    "categories": ["string"]
  }
}

============================================
IMPORTANT: Secret Handling
============================================

API keys and secrets are NOT stored in tenant_config.
They are resolved at runtime from environment variables:

- SENDGRID_API_KEY or {TENANT_ID}_SENDGRID_API_KEY
  Example: AFRICASTAY_SENDGRID_API_KEY

- OPENAI_API_KEY (shared across tenants)

- VAPI_API_KEY or {TENANT_ID}_VAPI_API_KEY
  Example: AFRICASTAY_VAPI_API_KEY

- Supabase service key: SUPABASE_SERVICE_KEY (shared, from env)

- SMTP passwords: Referenced via env var in YAML, same pattern
  for database config

The tenant_config.infrastructure sections only store:
- Non-sensitive IDs (project_id, phone_number_id, assistant_id)
- Hostnames and URLs (supabase.url, smtp.host)
- Configuration values (region, model name)

Never store:
- API keys
- Service account keys
- Passwords
- Private keys
- Tokens

============================================
Migration from YAML
============================================

To migrate a tenant from YAML to database:

1. Set config_source = 'yaml' initially (loader reads YAML file)
2. Populate tenant_config from YAML content (via migration script)
3. Verify tenant_config is complete and correct
4. Set config_source = 'database' (loader reads from DB)
5. Archive YAML file (keep for rollback)

The config_source column enables this gradual migration:
- 'yaml': Loader reads from clients/{tenant_id}/client.yaml
- 'database': Loader reads from tenants.tenant_config

============================================
*/
