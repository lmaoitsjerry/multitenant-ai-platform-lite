---
phase: 17-error-handling-resilience
plan: 02
subsystem: error-handling
tags: [bare-exceptions, logging, debugging, code-quality]

dependency-graph:
  requires:
    - "Phase 12 (structured logging infrastructure)"
  provides:
    - "Proper exception handling with logging across codebase"
    - "Removed unused logger.py"
  affects:
    - "All exception handlers now log with context"
    - "Debugging production issues will be easier"

tech-stack:
  patterns:
    - "Use specific exception types (ValueError, TypeError, json.JSONDecodeError)"
    - "Debug logging for expected failures (config lookups)"
    - "Warning logging for unexpected failures (usage stats, storage)"

key-files:
  modified:
    - src/webhooks/email_webhook.py
    - src/api/analytics_routes.py
    - src/tools/supabase_tool.py
    - src/agents/quote_agent.py
    - src/api/routes.py
    - src/services/auth_service.py
  deleted:
    - src/utils/logger.py

decisions:
  D-17-02-01:
    description: "Use debug logging for expected config lookup failures"
    date: 2026-01-23
  D-17-02-02:
    description: "Use (ValueError, TypeError) for date parsing exceptions"
    date: 2026-01-23
  D-17-02-03:
    description: "Use warning logging for unexpected operational failures"
    date: 2026-01-23

metrics:
  duration: "11 minutes"
  completed: "2026-01-23"
  bare_exceptions_fixed: 20
  files_modified: 6
  files_deleted: 1
---

# Phase 17 Plan 02: Bare Exception Handlers and Error Logging Summary

Replaced all bare `except:` clauses with proper exception handling and logging, deleted unused logger.py.

## Tasks Completed

### Task 1: Fix bare exceptions in email_webhook.py
**Commit:** 50572f1

Fixed 8 bare exception handlers:
- Config lookup for local part (line 320): `except Exception as e` with debug logging
- Plus addressing config lookup (line 334): `except Exception as e` with debug logging
- X-Tenant-ID header config lookup (line 349): `except Exception as e` with debug logging
- Subject pattern config lookup (line 368): `except Exception as e` with debug logging
- JSON envelope parsing (line 422): `except json.JSONDecodeError as e` with debug logging
- Tenant email lookup (line 761): `except Exception as e` with debug logging
- Tenant config validation in receive_tenant_email (line 936): `except Exception as e` with warning logging
- Tenant lookup in test endpoint (line 1007): `except Exception as e` with warning logging

### Task 2: Fix bare exceptions in analytics_routes.py
**Commit:** 8de0b90

Fixed 7 bare exception handlers:
- Dashboard stats due_date parsing (line 175): `except (ValueError, TypeError) as e` with debug logging
- Quote analytics trend date parsing (line 447): `except (ValueError, TypeError) as e` with debug logging
- Invoice analytics aging date parsing (line 562): `except (ValueError, TypeError) as e` with debug logging
- Invoice analytics trend date parsing (line 599): `except (ValueError, TypeError) as e` with debug logging
- Call analytics trend date parsing (line 740): `except (ValueError, TypeError) as e` with debug logging
- Call analytics trend processing (line 742): `except Exception as e` with debug logging
- Usage stats fetch (line 883): `except Exception as e` with warning logging

### Task 3: Fix remaining bare exceptions and delete logger.py
**Commit:** f8ed0b8

Fixed 5 bare exception handlers across 4 files:
- supabase_tool.py line 1123: Storage duplicate file fallback with warning logging
- quote_agent.py line 647: Timezone parsing (first location) with debug logging
- quote_agent.py line 682: Timezone parsing (second location) with debug logging
- routes.py line 742: Hotels JSON parsing with debug logging
- auth_service.py line 359: User sign-out cleanup with debug logging

Deleted unused file:
- src/utils/logger.py - Conflicts with structured_logger.py which is the correct implementation

## Verification Results

1. **No bare exceptions remain:** `grep -rn "except:\s*$" src/ --include="*.py" | wc -l` returns 0
2. **logger.py deleted:** File no longer exists
3. **Tests pass:** 112 tests pass (test_email_webhook.py + test_analytics_routes.py)
4. **Imports work:** All affected modules import successfully

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| D-17-02-01 | Use debug logging for expected config lookup failures | These are normal flow - tenant may not exist, no need to warn |
| D-17-02-02 | Use (ValueError, TypeError) for date parsing exceptions | More specific than catching all exceptions |
| D-17-02-03 | Use warning logging for unexpected operational failures | Usage stats failures, storage issues warrant visibility |

## Deviations from Plan

None - plan executed exactly as written.

## Files Changed

| File | Changes |
|------|---------|
| src/webhooks/email_webhook.py | 8 bare exceptions replaced with proper handling and logging |
| src/api/analytics_routes.py | 7 bare exceptions replaced with proper handling and logging |
| src/tools/supabase_tool.py | 1 bare exception replaced with proper handling and logging |
| src/agents/quote_agent.py | 2 bare exceptions replaced with proper handling and logging |
| src/api/routes.py | 1 bare exception replaced with proper handling and logging |
| src/services/auth_service.py | 1 bare exception replaced with proper handling and logging |
| src/utils/logger.py | DELETED |

## Next Phase Readiness

- All bare exception handlers now have proper logging
- Debugging production issues will be easier with contextual error messages
- logger.py removal cleans up code confusion (structured_logger.py is authoritative)
- Ready to proceed with 17-03 (if not already complete)
