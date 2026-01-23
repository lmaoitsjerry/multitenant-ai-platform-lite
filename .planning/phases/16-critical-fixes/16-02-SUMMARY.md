---
phase: 16
plan: 02
subsystem: security
tags: [timing-attack, hmac, admin-auth, security-fix]

dependency-graph:
  requires:
    - Admin routes with token verification
  provides:
    - Constant-time admin token comparison
    - Timing attack prevention
  affects:
    - All admin API endpoints

tech-stack:
  added: []
  patterns:
    - hmac.compare_digest for secret comparison
    - UTF-8 encoding for byte comparison

key-files:
  created: []
  modified:
    - src/api/admin_routes.py
    - tests/test_admin_routes.py

decisions:
  - id: D-16-02-01
    decision: Use hmac.compare_digest with UTF-8 encoding for token comparison
    date: 2026-01-23

metrics:
  duration: 5 min
  completed: 2026-01-23
---

# Phase 16 Plan 02: Fix Admin Token Timing Attack Summary

**One-liner:** Constant-time admin token verification using hmac.compare_digest to prevent timing attacks.

## What Was Done

### Task 1: Replace string comparison with hmac.compare_digest
- Added `import hmac` at top of admin_routes.py
- Replaced vulnerable `x_admin_token != admin_token` comparison
- Now uses `hmac.compare_digest(x_admin_token.encode('utf-8'), admin_token.encode('utf-8'))`
- Updated docstring to note timing-safe behavior

### Task 2: Add tests verifying timing-safe behavior
- Added `TestAdminTokenTimingSafety` test class with 5 tests:
  - `test_admin_token_uses_constant_time_comparison` - source code inspection
  - `test_admin_token_rejects_wrong_token_with_401` - security behavior
  - `test_admin_token_accepts_correct_token` - correct tokens work
  - `test_admin_token_handles_unicode` - unicode character support
  - `test_admin_token_no_vulnerable_comparison_in_source` - no direct != operator

## Security Fix Details

**Vulnerability:** Timing attack on admin token verification

**Attack Vector:**
1. Standard `!=` operator short-circuits on first mismatched character
2. Attacker measures response time for different token guesses
3. Longer response time indicates more matching prefix characters
4. Character-by-character enumeration reveals correct token

**Fix:**
- `hmac.compare_digest()` always compares all bytes
- Takes constant time regardless of which characters match
- Python standard library's recommended approach (PEP 466)

## Verification Results

```bash
# hmac.compare_digest is in source
$ grep -n "hmac.compare_digest" src/api/admin_routes.py
97:    if not hmac.compare_digest(x_admin_token.encode('utf-8'), admin_token.encode('utf-8')):

# Vulnerable pattern removed
$ grep "x_admin_token != admin_token" src/api/admin_routes.py
# (no output - pattern not found)

# All tests pass
$ pytest tests/test_admin_routes.py -v
27 passed, 3 skipped
```

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| 01aec40 | fix | Use hmac.compare_digest for constant-time token comparison |
| 941a921 | test | Add timing-safe admin token verification tests |

## Deviations from Plan

None - plan executed exactly as written.

## Files Modified

| File | Changes |
|------|---------|
| src/api/admin_routes.py | +5 lines (hmac import, constant-time comparison, docstring update) |
| tests/test_admin_routes.py | +63 lines (5 new timing safety tests) |

## Next Phase Readiness

- All critical security fixes in this plan complete
- Admin endpoints now resistant to timing attacks
- Ready for next plan (16-03)
