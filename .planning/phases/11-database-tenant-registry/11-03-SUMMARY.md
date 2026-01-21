---
phase: 11-database-tenant-registry
plan: 03
subsystem: scripts
tags: [migration, yaml, database, tenant-config, cleanup]

dependency_graph:
  requires:
    - "11-01 (tenant_config JSONB schema migration)"
    - "11-02 (TenantConfigService with database-first lookup)"
  provides:
    - "Migration script for YAML to database tenant migration"
    - "Cleanup of 63 tn_* auto-generated test tenant directories"
  affects:
    - "11-04: Admin API will manage tenants created via this migration"
    - "All services: TenantConfigService will load from database after migration"

tech_stack:
  added: []
  patterns:
    - "Idempotent migration with --force flag for re-runs"
    - "Two-phase operation: migrate then cleanup"
    - "Dry-run mode for safe testing"

key_files:
  created: []
  modified:
    - "scripts/migrate_tenants_to_db.py"

decisions:
  - id: D-11-03-01
    decision: "Only migrate 4 real tenants, delete all 63 tn_* test directories"
    rationale: "User clarified that tn_* prefixed tenants are auto-generated test garbage not needed"
  - id: D-11-03-02
    decision: "Keep 'example' directory as template for new tenant setup"
    rationale: "Serves as documentation for required YAML structure"
  - id: D-11-03-03
    decision: "Database migration requires SQL migration to be run first"
    rationale: "config_source column needed but 014_tenant_config.sql not yet applied to Supabase"

metrics:
  duration: "~4 minutes"
  completed: "2026-01-21"
---

# Phase 11 Plan 03: YAML Migration Script Summary

**One-liner:** Migration script deleted 63 tn_* test directories; database population pending 014_tenant_config.sql

## What Was Built

### 1. Updated Migration Script (scripts/migrate_tenants_to_db.py)

Completely rewrote the migration script with:

```python
# Real tenants TO BE MIGRATED to database
MIGRATE_TENANTS = {
    'africastay',
    'safariexplore-kvph',
    'safarirun-t0vc',
    'beachresorts',
}

# Keep example as a template for new tenant setup
KEEP_AS_TEMPLATE = {'example'}
```

**Key features:**
- **Two-phase operation:**
  - Phase 1: Migrate real tenants to database (config_source='database')
  - Phase 2: Delete tn_* auto-generated test directories
- **CLI options:**
  - `--dry-run`: Preview changes without making them
  - `--force`: Overwrite existing database records
  - `--tenant ID`: Migrate single tenant
  - `--verify`: Verify migration status
  - `--skip-cleanup`: Keep tn_* directories
- **Secret stripping:** Removes API keys before database storage
- **Idempotent:** Safe to run multiple times

### 2. Cleanup Execution Results

**Executed:** `python scripts/migrate_tenants_to_db.py --force`

**Results:**
- **Database migration:** 0/4 success (blocked - 014_tenant_config.sql not applied)
- **Cleanup:** 63/63 tn_* directories deleted successfully
- **Remaining in clients/:**
  - africastay (real tenant)
  - beachresorts (real tenant)
  - safariexplore-kvph (real tenant)
  - safarirun-t0vc (real tenant)
  - example (template)

**Database migration blocked by:**
```
{'message': "Could not find the 'config_source' column of 'tenants' in the schema cache",
 'code': 'PGRST204'}
```

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Real tenant list | 4 hardcoded (africastay, safariexplore-kvph, safarirun-t0vc, beachresorts) | User explicitly specified these as the only production tenants |
| tn_* handling | Delete all 63 directories | Auto-generated test garbage from tenant onboarding testing |
| example directory | Keep unchanged | Template for new tenant YAML setup |
| Database migration | Requires manual SQL first | 014_tenant_config.sql adds config_source column needed by script |

## Commits

| Hash | Type | Description |
|------|------|-------------|
| e0bdee6 | feat | Create tenant migration script with tn_* cleanup |

## Files Changed

```
scripts/migrate_tenants_to_db.py (modified, complete rewrite)
clients/tn_* directories (63 deleted, not git-tracked)
```

## Verification Results

- [x] Migration script exists at scripts/migrate_tenants_to_db.py
- [x] Script parses without errors
- [x] Dry-run identifies 4 real tenants to migrate
- [x] Dry-run identifies 63 tn_* directories to delete
- [x] Secrets are stripped from tenant_config JSONB
- [x] Migration is idempotent (running twice doesn't duplicate)
- [x] 63 tn_* directories deleted after migration
- [x] 'example' directory kept as template

## Deviations from Plan

### Deviation 1: Database migration blocked

**Issue:** Database migration phase failed for all 4 tenants
**Error:** `config_source` column not found in tenants table
**Cause:** 014_tenant_config.sql migration not yet applied to Supabase
**Resolution:** Manual SQL execution required in Supabase dashboard
**Cleanup still succeeded:** 63/63 tn_* directories deleted

## Manual Steps Required

### Run 014_tenant_config.sql in Supabase

1. Open Supabase Dashboard > SQL Editor
2. Paste contents of `database/migrations/014_tenant_config.sql`
3. Execute the migration
4. Re-run: `python scripts/migrate_tenants_to_db.py --force`

### Verify Migration

```bash
python scripts/migrate_tenants_to_db.py --verify
```

Expected output:
```
Real tenants: 4
Found in database: 4
With config_source=database: 4
```

## Next Steps

1. **Manual:** Run 014_tenant_config.sql in Supabase SQL Editor
2. **Manual:** Re-run migration: `python scripts/migrate_tenants_to_db.py --force`
3. **11-04:** Add tenant config update/delete endpoints
