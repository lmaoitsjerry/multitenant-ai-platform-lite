---
phase: 11-database-tenant-registry
plan: 01
subsystem: database
tags: [postgresql, jsonb, migration, tenant-config, supabase]

dependency_graph:
  requires:
    - "011_tenants_registry.sql (base tenants table)"
  provides:
    - "tenant_config JSONB column for full configuration storage"
    - "Denormalized query columns (timezone, currency, primary_email, gcp_project_id, gcp_dataset)"
    - "config_source column for yaml/database dual-mode operation"
    - "GIN index for efficient JSONB queries"
  affects:
    - "11-02: Config loader will read from tenants.tenant_config"
    - "11-03: YAML migration script will populate tenant_config"
    - "11-04: Admin API will CRUD tenant_config"

tech_stack:
  added: []
  patterns:
    - "JSONB for flexible schema with denormalized columns for common queries"
    - "config_source dual-mode for gradual migration"
    - "GIN index for JSONB containment queries"

key_files:
  created:
    - "database/migrations/014_tenant_config.sql"
  modified: []

decisions:
  - id: D-11-01-01
    decision: "Use 014_tenant_config.sql instead of 012 (migrations 012-013 already exist)"
    rationale: "Avoid migration number conflicts with existing schema"

metrics:
  duration: "~2 minutes"
  completed: "2026-01-21"
---

# Phase 11 Plan 01: Tenant Config JSONB Schema Summary

**One-liner:** JSONB tenant_config column with GIN index and dual-mode config_source for yaml/database migration

## What Was Built

Extended the `tenants` table (from 011_tenants_registry.sql) with:

1. **tenant_config JSONB column** - Stores complete tenant configuration:
   - branding (company_name, logo_url, colors, email_signature)
   - destinations array (name, code, enabled, aliases)
   - infrastructure refs (gcp, supabase URLs, vapi IDs, openai model)
   - email settings (primary, sendgrid, smtp, imap - non-secret values only)
   - banking details (for invoices)
   - consultants array
   - agents config (inbound, helpdesk, outbound)

2. **Denormalized query columns** - For fast lookups without JSONB parsing:
   - timezone (VARCHAR, default 'Africa/Johannesburg')
   - currency (VARCHAR, default 'ZAR')
   - primary_email (VARCHAR)
   - gcp_project_id (VARCHAR)
   - gcp_dataset (VARCHAR)

3. **config_source column** - Enables dual-mode operation:
   - 'yaml' = loader reads from clients/{tenant_id}/client.yaml
   - 'database' = loader reads from tenants.tenant_config
   - CHECK constraint enforces valid values

4. **Suspension columns**:
   - suspended_at (TIMESTAMPTZ)
   - suspended_reason (TEXT)

5. **Indexes**:
   - idx_tenants_tenant_config (GIN) for JSONB containment queries
   - idx_tenants_config_source (B-tree) for filtering
   - idx_tenants_primary_email (partial) for email lookups

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Migration number | 014 (not 012) | 012-013 already exist in codebase |
| Secret handling | Env var references only | Never store API keys in tenant_config |
| Dual-mode approach | config_source column | Enables gradual migration from YAML |
| Index strategy | GIN for JSONB, B-tree for scalars | Optimal query performance |

## Commits

| Hash | Type | Description |
|------|------|-------------|
| e720023 | feat | Add tenant_config JSONB schema extension migration |

## Files Changed

```
database/migrations/014_tenant_config.sql (created, 295 lines)
```

## Verification Results

- [x] Migration file exists at database/migrations/014_tenant_config.sql
- [x] SQL syntax valid (standard PostgreSQL ALTER TABLE, CREATE INDEX)
- [x] Migration idempotent (IF NOT EXISTS, DO $$ conditional constraint)
- [x] GIN index created for tenant_config JSONB
- [x] config_source column enables dual-mode operation
- [x] Documentation explains structure and secret handling

## Deviations from Plan

### Deviation 1: Migration file number changed

**Plan specified:** database/migrations/012_tenant_config.sql
**Actual:** database/migrations/014_tenant_config.sql
**Reason:** Migrations 012 (012_login_background.sql) and 013 (013_logo_email_url.sql) already exist.
**Impact:** None - migration still extends tenants table correctly.

## Next Steps

1. **11-02:** Create dual-mode config loader that reads from yaml or database based on config_source
2. **11-03:** Create YAML-to-database migration script for existing 60+ tenants
3. **11-04:** Create admin API endpoints for tenant_config CRUD
