---
phase: 17-error-handling-resilience
plan: 03
subsystem: data-layer
tags: [supabase, timeout, aggregation, deprovisioning]
dependencies:
  requires: []
  provides: [query-timeout-wrapper, optimized-pipeline-summary, tenant-deprovisioning]
  affects: [crm-routes, admin-routes, provisioning-api]
tech-stack:
  added: []
  patterns: [timeout-protection, batch-queries, graceful-degradation]
key-files:
  created: []
  modified:
    - src/tools/supabase_tool.py
    - src/services/crm_service.py
    - src/services/provisioning_service.py
decisions:
  - id: D-17-03-01
    description: Use ThreadPoolExecutor with 10s default timeout for Supabase queries
  - id: D-17-03-02
    description: Only fetch active pipeline stages for value calculations (skip LOST/TRAVELLED)
  - id: D-17-03-03
    description: Delete tables in dependency order during deprovisioning
metrics:
  duration: 5m 25s
  completed: 2026-01-23
---

# Phase 17 Plan 03: Supabase Query Timeouts & Provisioning Cleanup Summary

**One-liner:** Supabase queries protected with 10s timeout wrapper, pipeline summary optimized with batch queries, and tenant deprovisioning fully implemented

## What Was Done

### Task 1: Supabase Query Timeout Wrapper
- Added `DEFAULT_QUERY_TIMEOUT = 10` constant for configurable timeout
- Added `ThreadPoolExecutor(max_workers=4)` for parallel query execution
- Implemented `execute_with_timeout()` method:
  - Configurable timeout (default 10 seconds)
  - Logs slow queries (>3 seconds) as warnings
  - Raises `TimeoutError` with descriptive message on timeout
  - Logs all query failures for debugging
- Added `query_with_timeout()` convenience method for simple select queries

### Task 2: Pipeline Summary Database Aggregation
- Rewrote `get_pipeline_summary()` to use optimized queries:
  - Query 1: Get client counts (only `pipeline_stage` column)
  - Query 2: Get active clients with emails (only QUOTED, NEGOTIATING, BOOKED, PAID)
  - Query 3: Batch fetch quotes using `in_()` for active clients only
- Benefits:
  - Reduces data transfer by selecting only needed columns
  - Skips LOST/TRAVELLED stages in value calculations
  - Uses `in_()` batch queries instead of fetching all quotes
  - Scales to thousands of clients without timeout issues

### Task 3: Provisioning Deletion Operations
- Implemented `_delete_sendgrid_subuser()`:
  - Looks up subuser name from tenant settings
  - Deletes via SendGrid API
  - Handles missing library gracefully
  - Treats 404 as success (already deleted)
- Implemented `_delete_tenant_data()`:
  - Deletes tables in dependency order: activities, notifications, quotes, invoices, clients, tenant_settings
  - Continues on errors (some tables may not exist)
  - Logs each table deletion
- Implemented `_delete_client_directory()`:
  - Removes `clients/{client_id}/` directory
  - Safety check to prevent deleting files
  - Handles already-removed directories
- Updated `deprovision_tenant()` to call all three helpers

## Commits

| Hash | Message |
|------|---------|
| 512554e | feat(17-03): add timeout wrapper to Supabase queries |
| e09643a | feat(17-03): implement database aggregation for pipeline summary |
| 4625618 | feat(17-03): implement provisioning service deletion operations |

## Verification Results

1. **Timeout wrapper**: `SupabaseTool.execute_with_timeout` exists with 10s default
2. **Pipeline summary**: Uses `in_()` batch queries for active clients only
3. **Deletion operations**: All three helper methods implemented
4. **Tests**: 59/59 tests pass (35 CRM + 24 provisioning)

## Deviations from Plan

None - plan executed exactly as written.

## Success Criteria Met

- [x] SupabaseTool has execute_with_timeout method with 10s default timeout
- [x] CRM pipeline_summary uses database-side aggregation (not fetching all rows)
- [x] ProvisioningService has _delete_sendgrid_subuser, _delete_tenant_data, _delete_client_directory methods
- [x] deprovision_tenant calls all three deletion helpers
- [x] Existing tests pass (59/59)

## Next Phase Readiness

No blockers. Plan 17-03 complete.
