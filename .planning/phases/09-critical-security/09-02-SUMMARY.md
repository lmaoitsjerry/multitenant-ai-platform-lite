---
phase: 09-critical-security
plan: 02
subsystem: security
tags: [security, admin-panel, environment-variables, credential-management]
dependency-graph:
  requires: []
  provides: ["secure-admin-token-loading", "env-example-documentation"]
  affects: ["deployment-process", "developer-onboarding"]
tech-stack:
  added: []
  patterns: ["environment-variable-configuration", "fail-loudly-pattern"]
file-tracking:
  key-files:
    created:
      - frontend/internal-admin/.env.example
    modified:
      - frontend/internal-admin/src/services/api.js
decisions:
  - id: D-09-02-01
    decision: "Warn on missing token instead of throwing error"
    rationale: "App should load for non-admin pages; API calls will fail with 401"
metrics:
  duration: "~3 minutes"
  completed: "2026-01-21"
---

# Phase 9 Plan 2: Remove Hardcoded Admin Token Summary

**One-liner:** Removed hardcoded admin token fallback from internal-admin panel, enforcing VITE_ADMIN_TOKEN environment variable with clear error messages.

## What Was Done

### Task 1: Remove Hardcoded Admin Token from api.js

Modified `frontend/internal-admin/src/services/api.js`:

**Before:**
```javascript
const ADMIN_TOKEN = import.meta.env.VITE_ADMIN_TOKEN || 'zorah-internal-admin-2024';
```

**After:**
```javascript
const ADMIN_TOKEN = import.meta.env.VITE_ADMIN_TOKEN;

// Validate admin token is configured
if (!ADMIN_TOKEN) {
  console.error(
    'FATAL: VITE_ADMIN_TOKEN environment variable is not set. ' +
    'Admin API requests will fail. Set this in your .env file.'
  );
}
```

Also enhanced the axios response interceptor to provide a specific error message when 401 errors occur with a missing token:
```javascript
if (error.response?.status === 401 && !ADMIN_TOKEN) {
  console.error(
    'Admin authentication failed. Ensure VITE_ADMIN_TOKEN is set in your .env file.'
  );
}
```

**Commit:** `c0ddd3b`

### Task 2: Create .env.example Documentation

Created `frontend/internal-admin/.env.example` with:
- Documentation of required environment variables
- Security guidance for token generation
- Reminder to not commit real tokens to version control

**Commit:** `14b6af3`

## Verification Results

1. **Hardcoded token removed:** `grep 'zorah-internal-admin-2024' frontend/internal-admin/` returns NO results
2. **Environment variable only:** `ADMIN_TOKEN = import.meta.env.VITE_ADMIN_TOKEN` with no fallback
3. **Clear error messages:** Console error on load if token missing, specific 401 error guidance
4. **.env.example exists:** Documents both VITE_API_URL and VITE_ADMIN_TOKEN
5. **.gitignore configured:** Already excludes `.env` and `.env.*` but allows `.env.example`

## Security Impact

**Before:** Anyone with repository access or access to built JavaScript could extract the hardcoded token `zorah-internal-admin-2024` and use it to access admin endpoints.

**After:** Token must be provided via environment variable, which:
- Is not committed to version control
- Can be different per environment (dev/staging/prod)
- Can be rotated without code changes
- Is not exposed in built JavaScript bundles

## Deviations from Plan

None - plan executed exactly as written.

## Files Changed

| File | Change |
|------|--------|
| `frontend/internal-admin/src/services/api.js` | Removed hardcoded token, added validation and error messages |
| `frontend/internal-admin/.env.example` | Created with required environment variable documentation |

## Commits

| Hash | Type | Description |
|------|------|-------------|
| `c0ddd3b` | fix | Remove hardcoded admin token from internal-admin api.js |
| `14b6af3` | docs | Add .env.example for internal-admin panel |

## Next Phase Readiness

**Blockers:** None

**Ready for:** Plan 09-03 (or next security fix in Phase 9)

**Deployment note:** After deploying this change, ensure `VITE_ADMIN_TOKEN` is set in the build environment. The value must match `ADMIN_API_TOKEN` configured on the backend.
