---
phase: 11-database-tenant-registry
plan: 02
subsystem: services
tags: [tenant-config, dual-mode, database, yaml, api]

dependency_graph:
  requires:
    - "11-01 (tenant_config JSONB schema migration)"
    - "config/loader.py (ClientConfig class)"
  provides:
    - "TenantConfigService with database-first, YAML-fallback operation"
    - "POST /api/v1/admin/tenants for tenant provisioning without YAML"
    - "config_source property for debugging config origin"
  affects:
    - "11-03: Migration script will use TenantConfigService.save_config()"
    - "11-04: Admin API will use TenantConfigService for CRUD"

tech_stack:
  added: []
  patterns:
    - "Dual-mode config: database-first with YAML fallback"
    - "Lazy imports to avoid circular dependencies"
    - "Singleton service pattern with reset capability"
    - "Secret stripping before database storage"

key_files:
  created:
    - "src/services/tenant_config_service.py"
  modified:
    - "config/loader.py"
    - "src/api/admin_tenants_routes.py"

decisions:
  - id: D-11-02-01
    decision: "Skip tn_* auto-generated test tenants (garbage data)"
    rationale: "User clarified only 4 real tenants to migrate: africastay, safariexplore-kvph, safarirun-t0vc, beachresorts"
  - id: D-11-02-02
    decision: "Use lazy imports in config/loader.py for TenantConfigService"
    rationale: "Avoids circular import: services/__init__.py -> crm_service -> config/loader -> tenant_config_service"
  - id: D-11-02-03
    decision: "Add config_source property to ClientConfig"
    rationale: "Enables debugging which source (database/yaml) provided the config"

metrics:
  duration: "~5.5 minutes"
  completed: "2026-01-21"
---

# Phase 11 Plan 02: Dual-Mode Config Loader Summary

**One-liner:** TenantConfigService with database-first lookup, YAML fallback, and tenant provisioning API

## What Was Built

### 1. TenantConfigService (src/services/tenant_config_service.py)

New service class providing dual-mode tenant configuration:

```python
from src.services.tenant_config_service import TenantConfigService, get_tenant_config

service = TenantConfigService()
config = service.get_config("africastay")  # Returns dict or None

# Or use convenience function
config = get_tenant_config("tenant_id")
```

**Key features:**
- **Database-first lookup:** Queries Supabase `tenants` table for `config_source='database'` rows
- **YAML fallback:** Falls back to `clients/{tenant_id}/client.yaml` for unmigrated tenants
- **tn_* filtering:** Auto-generated test tenants (tn_*) are completely ignored
- **Secret handling:** API keys resolved from environment variables at runtime, never stored in DB
- **save_config():** Strips secrets before storing to database
- **list_tenants():** Combines database and YAML tenants, excluding tn_*

**MIGRATED_TENANTS constant:**
```python
MIGRATED_TENANTS = {
    'africastay',
    'safariexplore-kvph',
    'safarirun-t0vc',
    'beachresorts',
}
```

### 2. Updated config/loader.py

Integrated TenantConfigService while maintaining full backward compatibility:

```python
from config.loader import ClientConfig, list_clients

config = ClientConfig('africastay')
print(config.name)           # Works exactly as before
print(config.config_source)  # NEW: 'database', 'yaml', or 'service'
```

**Changes:**
- `ClientConfig.__init__` tries TenantConfigService first, falls back to direct YAML
- Added `config_source` property for debugging
- `list_clients()` now uses TenantConfigService and skips tn_* tenants
- `clear_config_cache()` resets TenantConfigService singleton
- Lazy imports to avoid circular dependency with services module

### 3. Tenant Provisioning API Endpoint

New POST endpoint for creating tenants without YAML files:

```bash
curl -X POST http://localhost:8000/api/v1/admin/tenants \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "newclient",
    "company_name": "New Client Ltd",
    "admin_email": "admin@newclient.com",
    "plan": "standard"
  }'
```

**CreateTenantRequest fields:**
| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| tenant_id | Yes | - | Unique ID (lowercase, 3-50 chars, alphanumeric + _ -) |
| company_name | Yes | - | Display name (2-100 chars) |
| admin_email | Yes | - | Primary admin contact |
| timezone | No | Africa/Johannesburg | IANA timezone |
| currency | No | ZAR | ISO currency code |
| plan | No | lite | lite, standard, premium |
| logo_url | No | null | Brand logo URL |
| primary_color | No | #1a73e8 | Brand color hex |
| gcp_project_id | No | empty | GCP project for BigQuery |
| gcp_dataset | No | empty | BigQuery dataset name |

**Plan-based limits:**
| Plan | Max Users | Max Quotes/Month | Storage |
|------|-----------|------------------|---------|
| lite | 5 | 100 | 1 GB |
| standard | 20 | 1000 | 10 GB |
| premium | 20 | 1000 | 10 GB |

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| tn_* filtering | Ignore completely | User clarified these are auto-generated garbage data |
| Import strategy | Lazy imports | Avoids circular import chain |
| Config source tracking | _meta.source field | Enables debugging and gradual migration |
| Secret handling | os.getenv() at runtime | Never store secrets in database |

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 0bb0b97 | feat | Create TenantConfigService with dual-mode operation |
| 043b50d | feat | Integrate TenantConfigService into config/loader.py |
| 18de281 | feat | Add POST /api/v1/admin/tenants for tenant provisioning |

## Files Changed

```
src/services/tenant_config_service.py (created, 393 lines)
config/loader.py (modified, +97/-0 significant changes)
src/api/admin_tenants_routes.py (modified, +125 lines)
```

## Verification Results

- [x] src/services/tenant_config_service.py exists with TenantConfigService class
- [x] config/loader.py imports and uses TenantConfigService
- [x] Secrets resolved from environment variables, not stored in DB
- [x] Existing ClientConfig API unchanged (all properties work)
- [x] POST /api/v1/admin/tenants endpoint exists
- [x] list_clients() skips tn_* tenants (found 5 real tenants)
- [x] config_source property available for debugging

## Deviations from Plan

None - plan executed exactly as written.

## Next Steps

1. **11-03:** Create YAML-to-database migration script for 4 real tenants
2. **11-04:** Add tenant config update/delete endpoints
3. Run migration script to populate database with africastay, safariexplore-kvph, safarirun-t0vc, beachresorts configs
