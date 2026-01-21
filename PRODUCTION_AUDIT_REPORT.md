# Production Readiness Audit Report

**Date:** January 15, 2026
**Auditor:** Claude Code
**Severity:** CRITICAL - Multiple blocking issues found

---

## Executive Summary

The multi-tenant platform uses a **hybrid file + database storage model** that is **NOT synchronized**. This creates a critical production blocker where:

1. **52 tenants exist as YAML files** but only **1 tenant (africastay)** has database records
2. **Database tables exist** (`tenant_settings`, `tenant_branding`) but are **never populated during onboarding**
3. The system "works" because APIs fall back to YAML files, but this is **inconsistent and fragile**

---

## Critical Issues Found

### Issue 1: Tenants Not Saved to Database (CRITICAL)

**Location:** `src/api/onboarding_routes.py` lines 575-582

**Problem:** During onboarding, tenant data is ONLY saved to:
- `clients/{tenant_id}/client.yaml` (file)
- `organization_users` table (for admin user only)

**NOT saved to:**
- `tenant_settings` table
- `tenant_branding` table
- No central `tenants` registry table

**Evidence:**
```
Found 52 tenant YAML files in clients/ folder
Found only 1 record in tenant_settings table (africastay)
Found only 1 record in tenant_branding table (africastay)
```

**Impact:**
- Settings changes via API write to empty database
- Branding reads return NULL from database
- No audit trail of when tenants were created
- Cannot query tenant list from database

---

### Issue 2: No Central Tenant Registry (HIGH)

**Problem:** There is no `tenants` table to track:
- When tenant was created
- Who created it
- Tenant status (active/suspended/deleted)
- Subscription plan/tier
- Usage quotas

**Impact:**
- Cannot list all tenants from database
- Cannot suspend or delete tenants cleanly
- No billing/subscription management possible
- Admin dashboard cannot show tenant analytics

---

### Issue 3: Infrastructure Credentials in Plain Text (MEDIUM)

**Location:** `clients/{tenant_id}/client.yaml`

**Problem:** Sensitive credentials stored in YAML files:
```yaml
infrastructure:
  supabase:
    url: "https://xxx.supabase.co"
    anon_key: "eyJ..."      # Exposed
    service_key: "eyJ..."   # Exposed - DANGEROUS
  sendgrid:
    api_key: "SG.xxx"       # Exposed
```

**Impact:**
- Security vulnerability if files are leaked
- No credential rotation without manual file updates
- Version control may expose secrets

---

### Issue 4: Authentication Flow Issues (HIGH)

**Location:** `src/services/auth_service.py`, `src/api/auth_routes.py`

**Problems Found:**
1. Login with existing email + different password fails silently
2. Auto-login after onboarding fails when email already exists
3. Error messages not displayed to users (fixed in this session)

**Root Cause:** Admin user creation during onboarding doesn't handle existing Supabase Auth users properly.

---

### Issue 5: Database Tables Exist But Unused (MEDIUM)

**Tables that exist but are never auto-populated:**

| Table | Created By | Populated During Onboarding? |
|-------|-----------|------------------------------|
| `organization_users` | Migration 001 | YES (admin user only) |
| `user_invitations` | Migration 001 | No (manual invite) |
| `tenant_branding` | Migration 003 | **NO** |
| `tenant_settings` | Migration 010 | **NO** |

---

## Current Data Flow (Broken)

```
Onboarding Request
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                    WHAT ACTUALLY HAPPENS                     │
├─────────────────────────────────────────────────────────────┤
│ 1. Generate tenant_id (tn_xxx_yyy)                          │
│ 2. Create clients/{tenant_id}/client.yaml ✓                 │
│ 3. Create clients/{tenant_id}/prompts/inbound.txt ✓         │
│ 4. Create SendGrid subuser (if configured) ✓                │
│ 5. Create organization_users record ✓                       │
│ 6. Create tenant_settings record ✗ MISSING                  │
│ 7. Create tenant_branding record ✗ MISSING                  │
│ 8. Create tenants registry record ✗ TABLE DOESN'T EXIST     │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                    API READ OPERATIONS                       │
├─────────────────────────────────────────────────────────────┤
│ GET /api/v1/settings                                        │
│   1. Try database (tenant_settings) → NULL                  │
│   2. Fall back to YAML config → Works                       │
│                                                              │
│ GET /api/v1/branding                                        │
│   1. Try database (tenant_branding) → NULL                  │
│   2. Fall back to YAML + preset → Works                     │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                   API WRITE OPERATIONS                       │
├─────────────────────────────────────────────────────────────┤
│ PUT /api/v1/settings                                        │
│   1. Check if record exists → NO                            │
│   2. INSERT new record → Works (upsert logic exists)        │
│                                                              │
│ PUT /api/v1/branding                                        │
│   1. Check if record exists → NO                            │
│   2. INSERT new record → Works (upsert logic exists)        │
│                                                              │
│ PROBLEM: YAML file is never updated!                        │
│ Database and YAML become out of sync.                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Recommended Fixes

### Fix 1: Initialize Database During Onboarding (CRITICAL)

**File:** `src/api/onboarding_routes.py`

Add after line 582 (after `create_tenant_config`):

```python
# Step 2b: Initialize database records
logger.info(f"Initializing database records for {tenant_id}")
try:
    from src.tools.supabase_tool import SupabaseTool

    # Get fresh config
    config = get_config(tenant_id)
    db = SupabaseTool(config)

    # Create tenant_settings record
    db.update_tenant_settings(
        company_name=request.company.company_name,
        support_email=request.company.support_email,
        support_phone=request.company.support_phone,
        website=request.company.website_url,
        currency=request.company.currency,
        timezone=request.company.timezone,
        email_from_name=request.email.from_name,
        email_from_email=request.email.from_email or request.company.support_email,
    )

    # Create tenant_branding record
    db.create_branding(
        preset_theme=request.company.brand_theme.theme_id,
        colors={
            "primary": request.company.brand_theme.primary,
            "secondary": request.company.brand_theme.secondary,
            "accent": request.company.brand_theme.accent,
        }
    )

    resources["database_initialized"] = True
    logger.info(f"Database records created for {tenant_id}")

except Exception as e:
    logger.error(f"Failed to initialize database for {tenant_id}: {e}")
    errors.append(f"Database initialization: {str(e)}")
```

### Fix 2: Create Tenants Registry Table (HIGH)

**New migration file:** `database/migrations/011_tenants_registry.sql`

```sql
-- Central tenant registry
CREATE TABLE IF NOT EXISTS tenants (
    id VARCHAR(50) PRIMARY KEY,  -- e.g., tn_xxx_yyy
    name VARCHAR(255) NOT NULL,
    short_name VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active',  -- active, suspended, deleted
    plan VARCHAR(50) DEFAULT 'lite',      -- lite, pro, enterprise

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES organization_users(id),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    -- Quotas (can be moved to separate table)
    max_users INT DEFAULT 5,
    max_monthly_quotes INT DEFAULT 100,
    max_storage_gb INT DEFAULT 1
);

CREATE INDEX idx_tenants_status ON tenants(status);
CREATE INDEX idx_tenants_plan ON tenants(plan);

-- RLS
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access" ON tenants
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Users can view own tenant" ON tenants
    FOR SELECT USING (id = current_setting('app.tenant_id', true));
```

### Fix 3: Migrate Existing Tenants (CRITICAL)

Create a migration script to populate database from existing YAML files:

```python
# scripts/migrate_tenants_to_db.py
import os
import yaml
from pathlib import Path
from supabase import create_client

def migrate_tenants():
    clients_dir = Path("clients")
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY")
    )

    for tenant_dir in clients_dir.iterdir():
        if not tenant_dir.is_dir():
            continue

        config_file = tenant_dir / "client.yaml"
        if not config_file.exists():
            continue

        tenant_id = tenant_dir.name

        with open(config_file) as f:
            config = yaml.safe_load(f)

        # Insert into tenants table
        supabase.table("tenants").upsert({
            "id": tenant_id,
            "name": config.get("client", {}).get("name", tenant_id),
            "short_name": config.get("client", {}).get("short_name"),
            "status": "active",
            "plan": "lite"
        }).execute()

        # Insert into tenant_settings
        branding = config.get("branding", {})
        email_config = config.get("email", {})

        supabase.table("tenant_settings").upsert({
            "tenant_id": tenant_id,
            "company_name": branding.get("company_name"),
            "support_email": email_config.get("primary"),
            "currency": config.get("client", {}).get("currency", "USD"),
            "timezone": config.get("client", {}).get("timezone", "UTC"),
            "email_from_name": email_config.get("sendgrid", {}).get("from_name"),
            "email_from_email": email_config.get("sendgrid", {}).get("from_email"),
        }).execute()

        # Insert into tenant_branding
        supabase.table("tenant_branding").upsert({
            "tenant_id": tenant_id,
            "preset_theme": branding.get("theme_id", "professional_blue"),
            "logo_url": branding.get("logo_url"),
            "color_primary": branding.get("primary_color"),
            "color_secondary": branding.get("secondary_color"),
            "color_accent": branding.get("accent_color"),
        }).execute()

        print(f"Migrated: {tenant_id}")

if __name__ == "__main__":
    migrate_tenants()
```

### Fix 4: Move Credentials to Environment Variables (MEDIUM)

Update `create_tenant_config` to use environment variable references:

```yaml
infrastructure:
  supabase:
    url: "${SUPABASE_URL}"
    anon_key: "${SUPABASE_ANON_KEY}"
    service_key: "${SUPABASE_SERVICE_KEY}"
```

---

## Testing Checklist

After implementing fixes:

- [ ] New tenant onboarding creates records in:
  - [ ] `tenants` table
  - [ ] `tenant_settings` table
  - [ ] `tenant_branding` table
  - [ ] `organization_users` table
  - [ ] YAML config file

- [ ] Existing tenants migrated to database
- [ ] Settings changes persist after refresh
- [ ] Branding changes persist after refresh
- [ ] Admin can list all tenants from database
- [ ] Login works for newly onboarded users

---

## Files Modified in This Session

1. `frontend/tenant-dashboard/src/pages/Login.jsx` - Fixed error display visibility
2. `frontend/tenant-dashboard/src/pages/admin/TenantOnboarding.jsx` - Added email-exists error handling
3. `src/api/onboarding_routes.py` - **FIXED**: Now initializes database records during onboarding
4. `database/migrations/011_tenants_registry.sql` - **NEW**: Central tenant registry table
5. `scripts/migrate_tenants_to_db.py` - **NEW**: Migration script for existing tenants

---

## How to Apply Fixes

### Step 1: Run the Tenants Registry Migration in Supabase

1. Go to Supabase Dashboard > SQL Editor
2. Copy and paste contents of `database/migrations/011_tenants_registry.sql`
3. Click "Run"

### Step 2: Migrate Existing Tenants

```powershell
cd C:\Users\jerry\Documents\multitenant-ai-platform-lite
python scripts/migrate_tenants_to_db.py
```

This will populate:
- `tenants` table (registry)
- `tenant_settings` table
- `tenant_branding` table

### Step 3: Verify Migration

Check Supabase Dashboard > Table Editor:
- `tenants` should have ~52 records
- `tenant_settings` should have ~52 records
- `tenant_branding` should have ~52 records

---

## Priority Order for Fixes

1. **CRITICAL:** Fix onboarding to initialize database records
2. **CRITICAL:** Run migration script for existing 52 tenants
3. **HIGH:** Create tenants registry table and populate it
4. **MEDIUM:** Move credentials to environment variables
5. **LOW:** Add audit logging for tenant changes

---

## Conclusion

The platform is **NOT production-ready** due to the file/database synchronization issue. The core functionality works because of fallback logic, but data consistency is not guaranteed.

Estimated effort to fix: **4-8 hours** for critical issues.
