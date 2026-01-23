---
phase: 16-critical-fixes
plan: 01
subsystem: core-infrastructure
tags: [thread-safety, di-caching, singleton, lru_cache, threading]

dependency_graph:
  requires: []
  provides: ["thread-safe-di-caching", "thread-safe-faiss-singleton"]
  affects: ["concurrent-request-handling", "worker-initialization"]

tech_stack:
  added: []
  patterns: ["lru_cache-for-thread-safe-caching", "double-check-locking-singleton"]

key_files:
  created:
    - tests/test_thread_safety.py
  modified:
    - src/api/routes.py
    - src/services/faiss_helpdesk_service.py

decisions:
  - id: D-16-01-01
    decision: Use lru_cache(maxsize=100) for DI caching instead of unbounded cache
    rationale: Limits memory usage while allowing caching for expected number of tenants
  - id: D-16-01-02
    decision: Use double-check locking pattern for FAISS singleton
    rationale: Fast path optimization - avoids lock acquisition for already-initialized case

metrics:
  duration: 7m17s
  completed: 2026-01-23
---

# Phase 16 Plan 01: Thread-Safety Fixes Summary

**One-liner:** Thread-safe DI caching with lru_cache and FAISS singleton with double-check locking

## What Was Done

### Task 1: Replace dict-based DI caching with thread-safe lru_cache
- Removed global dicts: `_client_configs`, `_quote_agents`, `_crm_services`
- Added `@lru_cache(maxsize=100)` decorators for thread-safe caching
- Created internal cached functions: `_get_cached_config`, `_get_cached_quote_agent`, `_get_cached_crm_service`
- Public functions now delegate to cached internal functions
- Commit: `8bd4d7b`

### Task 2: Add double-check locking to FAISS singleton
- Added `threading` import
- Added class-level `_lock = threading.Lock()`
- Implemented double-check locking pattern in `__new__`:
  - First check (outside lock): Fast path for already-initialized case
  - Second check (inside lock): Prevents race condition during initialization
- Updated docstring to document thread-safety
- Commit: `096846c`

### Task 3: Add unit tests for thread-safety
- Created `tests/test_thread_safety.py` with 5 tests:
  - `test_lru_cache_returns_same_config`: Verify caching behavior
  - `test_concurrent_config_access`: 20 concurrent threads test
  - `test_singleton_returns_same_instance`: Basic singleton test
  - `test_concurrent_singleton_creation`: 20 concurrent threads test
  - `test_double_check_locking_exists`: Verify lock mechanism exists
- All tests pass
- Commit: `8e06cc5`

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| D-16-01-01 | Use lru_cache(maxsize=100) | Limits memory while allowing expected tenant count |
| D-16-01-02 | Double-check locking pattern | Fast path optimization for already-initialized case |

## Verification Results

| Check | Result |
|-------|--------|
| DI caching uses @lru_cache | 3 decorators in routes.py |
| FAISS uses threading.Lock | Double-check pattern implemented |
| No global dict caches | _client_configs/_quote_agents/_crm_services removed |
| Thread-safety tests pass | 5/5 tests pass with 20 concurrent threads |
| Existing tests pass | 1563 passed, 53 skipped |

## Test Coverage Impact

| File | Before | After |
|------|--------|-------|
| tests/test_thread_safety.py | N/A | 5 tests (new) |
| Total tests | 1554 | 1559 |

## Technical Notes

### Why lru_cache is Thread-Safe
- Python's lru_cache uses the GIL (Global Interpreter Lock) for atomic operations
- Cache operations are protected by internal locking
- maxsize=100 limits memory usage for multi-tenant scenario

### Why Double-Check Locking
- First check avoids lock acquisition overhead for common case (already initialized)
- Lock ensures only one thread can initialize
- Second check inside lock prevents race where multiple threads passed first check

## Files Changed

| File | Change |
|------|--------|
| src/api/routes.py | +29/-22 lines: lru_cache caching pattern |
| src/services/faiss_helpdesk_service.py | +9/-3 lines: double-check locking |
| tests/test_thread_safety.py | +111 lines: new test file |

## Next Phase Readiness

No blockers. Thread-safety fixes are self-contained and do not affect other phases.
