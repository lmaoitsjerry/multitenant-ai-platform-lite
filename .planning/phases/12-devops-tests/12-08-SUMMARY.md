---
phase: 12-devops-tests
plan: 08
status: superseded
completed: 2026-01-21
superseded_by: "12-13 + user decision"
---

# Plan 12-08: Finalize Coverage at 70% — SUPERSEDED

## Summary

This plan was designed to raise the coverage threshold to 70% after plans 05-07 added sufficient tests. However, after executing all test plans (05-13), coverage reached **44.9%** — short of the 70% target.

## User Decision

On 2026-01-21, the user approved setting **45%** as the v3.0 baseline instead of 70%:
- 70% requires ~20-25 additional hours of work
- Remaining gaps are external API mocking (Twilio, SendGrid, BigQuery, LLM agents)
- 45% threshold enforced in CI to prevent regression

## What Was Done Instead

The coverage threshold was set to **45%** (not 70%) in:
- `pyproject.toml`: `fail_under = 45`
- `.github/workflows/ci.yml`: `--cov-fail-under=45`

This was done in commit `4e83c51` as part of finalizing Phase 12.

## Outcome

- **Original goal:** 70% coverage threshold
- **Actual outcome:** 45% coverage threshold (user approved)
- **TEST-04 status:** Partial (45% achieved, 70% deferred to v4.0)

---

*Superseded: 2026-01-21*
*Reason: Coverage target adjusted from 70% to 45% based on user decision*
