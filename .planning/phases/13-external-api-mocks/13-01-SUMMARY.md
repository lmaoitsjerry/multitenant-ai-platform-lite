---
phase: 13-external-api-mocks
plan: 01
subsystem: testing
tags: [bigquery, mock, pytest, fixtures, analytics]

# Dependency graph
requires:
  - phase: 08-security-hardening
    provides: analytics routes infrastructure
provides:
  - BigQuery mock infrastructure (MockBigQueryClient, MockBigQueryRow, MockBigQueryQueryJob)
  - Reusable data generators (quotes, invoices, calls, clients, activities)
  - Analytics routes test coverage at 66%
  - Shared fixtures in conftest.py
affects: [13-02-sendgrid-mocks, future-test-phases, analytics-maintenance]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Pattern-based query response matching for BigQuery mocks
    - Direct async handler testing bypassing HTTP auth middleware
    - Lazy import patching at source module location

key-files:
  created:
    - tests/fixtures/__init__.py
    - tests/fixtures/bigquery_fixtures.py
  modified:
    - tests/conftest.py
    - tests/test_analytics_routes.py

key-decisions:
  - "Mock BigQuery with pattern-matching for SQL query responses rather than exact string matching"
  - "Test route handlers directly with mocked dependencies to bypass auth middleware for coverage"
  - "Patch at source module location (src.tools.supabase_tool.SupabaseTool) not at usage location"

patterns-established:
  - "BigQuery mocks: Use MockBigQueryClient.set_response_for_pattern() for flexible query matching"
  - "Direct handler testing: Call async handlers directly instead of HTTP for coverage"
  - "Data generators: Stateful generators that cycle through statuses/stages for realistic test data"

# Metrics
duration: 35min
completed: 2026-01-21
---

# Phase 13 Plan 01: BigQuery Mock Infrastructure Summary

**Reusable BigQuery mock infrastructure with pattern-based query matching, achieving 66% analytics routes coverage through direct handler testing**

## Performance

- **Duration:** 35 min
- **Started:** 2026-01-21T20:00:00Z
- **Completed:** 2026-01-21T20:35:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Created comprehensive BigQuery mock infrastructure with MockBigQueryRow, MockBigQueryQueryJob, and MockBigQueryClient classes
- Built reusable data generators for quotes, invoices, call records, clients, activities, and pipeline summaries
- Added shared fixtures to conftest.py for BigQuery and Supabase analytics testing
- Achieved 66% test coverage on analytics_routes.py (exceeding 50% target) using direct handler testing

## Task Commits

Each task was committed atomically:

1. **Task 1: Create BigQuery mock fixtures module** - `64bf7fe` (feat)
2. **Task 2: Add shared fixtures to conftest.py** - `2e6ff4c` (feat)
3. **Task 3: Expand analytics routes test coverage** - `a74ed2e` (test)

## Files Created/Modified

- `tests/fixtures/__init__.py` - Package exports for all BigQuery mock classes and generators
- `tests/fixtures/bigquery_fixtures.py` - MockBigQueryRow, MockBigQueryQueryJob, MockBigQueryClient, and data generators
- `tests/conftest.py` - Shared fixtures: mock_bigquery_client, mock_bigquery_client_with_data, mock_supabase_for_analytics, mock_analytics_config
- `tests/test_analytics_routes.py` - Expanded from 34 to 73 tests with direct handler testing

## Decisions Made

1. **Pattern-based query matching over exact string matching**
   - Rationale: SQL queries vary in whitespace and column ordering; pattern matching ("hotel_count" in query) is more flexible
   - MockBigQueryClient.set_response_for_pattern() allows setting responses for queries containing specific patterns

2. **Direct handler testing to bypass auth middleware**
   - Rationale: HTTP tests hit 401 from auth middleware before reaching route handlers
   - Solution: Import and call async handlers directly with mocked dependencies
   - Achieved 66% coverage vs 9% with HTTP-only tests

3. **Patch at source module location**
   - Rationale: Routes use lazy imports inside functions (`from src.tools.supabase_tool import SupabaseTool`)
   - Solution: Patch at `src.tools.supabase_tool.SupabaseTool` not `src.api.analytics_routes.SupabaseTool`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

1. **Auth middleware blocking HTTP tests**
   - Problem: All HTTP endpoint tests returned 401 because auth middleware intercepts before route dependencies
   - Solution: Used direct async handler testing with mocked dependencies instead of HTTP TestClient for coverage tests
   - Result: Coverage increased from 9.4% to 66.4%

2. **Lazy import patching**
   - Problem: Patching `src.api.analytics_routes.SupabaseTool` failed because the import is inside the function
   - Solution: Patch at the source module where class is defined: `src.tools.supabase_tool.SupabaseTool`

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- BigQuery mock infrastructure ready for use in other test modules
- Pattern established for testing routes that have lazy imports
- Fixtures exportable via `from tests.fixtures import create_mock_bigquery_client, generate_quotes`

---
*Phase: 13-external-api-mocks*
*Completed: 2026-01-21*
