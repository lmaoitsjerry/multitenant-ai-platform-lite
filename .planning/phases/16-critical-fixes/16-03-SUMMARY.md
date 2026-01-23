---
phase: 16-critical-fixes
plan: 03
subsystem: database
tags: [performance, sql, batch-queries, n+1, indexes]
dependency-graph:
  requires:
    - "Phase 10 (Supabase infrastructure)"
  provides:
    - "Batch query pattern for CRM enrichment"
    - "Production indexes for common query patterns"
  affects:
    - "Future phases requiring CRM performance"
    - "Database query optimization patterns"
tech-stack:
  added: []
  patterns:
    - "Batch queries with in_() filter"
    - "Dictionary-based result grouping for O(1) lookup"
    - "Composite indexes with DESC ordering"
key-files:
  created:
    - "database/migrations/015_production_indexes.sql"
  modified:
    - "src/services/crm_service.py"
    - "tests/test_crm_service.py"
decisions:
  - id: "D-16-03-01"
    decision: "Use in_() batch queries instead of N+1 per-client queries"
    rationale: "Reduces query count from 1+2*N to maximum 3 queries"
  - id: "D-16-03-02"
    decision: "Group batch results by key (email/client_id) for O(1) enrichment"
    rationale: "Efficient lookup during client enrichment loop"
  - id: "D-16-03-03"
    decision: "Use CONCURRENTLY for index creation"
    rationale: "Allows reads/writes during indexing without locking tables"
metrics:
  duration: "~8 minutes"
  completed: "2026-01-23"
---

# Phase 16 Plan 03: CRM N+1 Query Fix Summary

**One-liner:** Batch query optimization reducing CRM search from O(n) to O(1) database calls plus composite indexes for production patterns.

## What Was Done

### Task 1: Replace N+1 queries with batch queries in search_clients

Refactored the `search_clients` method (lines 250-340) to eliminate N+1 query performance issue:

**Before (N+1 pattern):**
- 1 query for clients
- N queries for quotes (one per client)
- N queries for activities (one per client)
- Total: 1 + 2*N queries

**After (batch pattern):**
- 1 query for clients
- 1 batch query for all quotes using `in_('customer_email', client_emails)`
- 1 batch query for all activities using `in_('client_id', client_ids)`
- Total: 3 queries maximum

Key implementation details:
- Collect all emails and client_ids before enrichment
- Use `in_()` filter for batch queries
- Group results by key in dictionaries for O(1) lookup
- Preserve fallback behavior (total_value when no quote, updated_at when no activity)

### Task 2: Create database migration for production indexes

Created `database/migrations/015_production_indexes.sql` with composite indexes:

| Index Name | Table | Columns | Purpose |
|------------|-------|---------|---------|
| idx_quotes_tenant_customer_email | quotes | tenant_id, customer_email, created_at DESC | CRM batch quote lookup |
| idx_activities_tenant_client_created | activities | tenant_id, client_id, created_at DESC | CRM batch activity lookup |
| idx_clients_tenant_email | clients | tenant_id, email | CRM deduplication |
| idx_invoices_tenant_status_created | invoices | tenant_id, status, created_at DESC | Financial reports |

Uses `CREATE INDEX CONCURRENTLY` to avoid locking tables during creation.

### Task 3: Add tests verifying batch query behavior

Added 4 new tests to `tests/test_crm_service.py`:

| Test | Verifies |
|------|----------|
| test_search_clients_uses_batch_queries | Full enrichment with batch results |
| test_search_clients_batch_handles_empty_results | Empty client list returns early |
| test_search_clients_batch_query_count | Exactly 3 table() calls |
| test_search_clients_batch_enrichment_priority | Quote value overrides total_value |

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 77713a4 | perf(16-03): replace N+1 queries with batch queries |
| 2 | 464e000 | chore(16-03): add production indexes migration |
| 3 | 91d3117 | test(16-03): add batch query tests |

## Verification Results

1. **CRM service import:** `python -c "from src.services.crm_service import CRMService; print('Import successful')"` - PASSED
2. **Batch query tests:** `pytest tests/test_crm_service.py -v -k "batch"` - 4/4 PASSED
3. **All CRM tests:** `pytest tests/test_crm_service.py -v` - 35/35 PASSED
4. **No N+1 in enrichment loop:** Only final enrichment loop exists, no nested queries

## Success Criteria Verification

- [x] search_clients method uses `in_()` for batch queries
- [x] Maximum 3 database queries per search (clients + quotes + activities)
- [x] New migration file 015_production_indexes.sql exists
- [x] Migration includes idx_quotes_tenant_customer_email index
- [x] Migration includes idx_activities_tenant_client_created index
- [x] Batch query tests pass
- [x] Existing CRM tests still pass

## Deviations from Plan

None - plan executed exactly as written.

## User Action Required

Run the migration manually in Supabase:

```
1. Open Supabase Dashboard
2. Go to SQL Editor
3. Create new query
4. Paste contents of database/migrations/015_production_indexes.sql
5. Run the query
```

## Next Phase Readiness

- CRM batch query pattern established for future optimization
- Index migration ready for production deployment
- All tests passing, no blockers
