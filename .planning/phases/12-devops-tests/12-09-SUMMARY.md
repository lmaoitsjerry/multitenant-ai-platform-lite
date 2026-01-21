---
phase: 12
plan: 09
subsystem: testing
tags: [tests, email, pdf, webhook, coverage]

dependency-graph:
  requires: ["12-07"]
  provides: ["external-integration-tests"]
  affects: ["coverage-threshold"]

tech-stack:
  added: []
  patterns: ["mocked-external-apis", "pytest-fixtures"]

key-files:
  created:
    - tests/test_email_sender.py
    - tests/test_pdf_generator.py
  modified:
    - tests/test_email_webhook.py

decisions:
  - id: D-12-09-01
    decision: Mock SendGrid API via requests.post patching
    rationale: Avoid network calls while testing email construction logic

  - id: D-12-09-02
    decision: Skip PDF tests when libraries unavailable
    rationale: fpdf2/WeasyPrint may not be installed in all environments

  - id: D-12-09-03
    decision: Use sys.modules patching for dynamic imports
    rationale: NotificationService imported inside webhook handler

metrics:
  duration: "~15 minutes"
  completed: "2026-01-21"
  tests-added: 100
  lines-added: 2349
  coverage-increase: "~1%"
---

# Phase 12 Plan 09: External Integration Tests Summary

Added comprehensive tests for external integrations (SendGrid email, PDF generation, webhook processing) using mocked dependencies.

## One-Liner

Mocked tests for EmailSender, PDFGenerator, and email webhook totaling 100 tests across 2349 lines.

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create email sender tests | bc6ebeb | tests/test_email_sender.py |
| 2 | Create PDF generator tests | c7e2e27 | tests/test_pdf_generator.py |
| 3 | Expand email webhook tests | 1d6a0e9 | tests/test_email_webhook.py |

## Technical Decisions

### D-12-09-01: Mock SendGrid API via requests.post patching

**Context:** EmailSender uses requests library to call SendGrid API directly.

**Decision:** Patch `src.utils.email_sender.requests.post` to mock API responses.

**Rationale:**
- Allows testing email construction logic without network calls
- Can simulate various response codes (202, 401, 429, 500)
- Tests run fast and deterministically

### D-12-09-02: Skip PDF tests when libraries unavailable

**Context:** PDFGenerator supports both fpdf2 and WeasyPrint, but neither may be installed.

**Decision:** Use `pytest.skip()` when `FPDF_AVAILABLE` or `WEASYPRINT_AVAILABLE` is False.

**Rationale:**
- Tests pass in CI even without PDF libraries
- When libraries are installed, full test coverage applies
- Follows graceful degradation pattern of source code

### D-12-09-03: Use sys.modules patching for dynamic imports

**Context:** Email webhook handler imports NotificationService inside the function.

**Decision:** Use `patch.dict('sys.modules', {...})` instead of direct patching.

**Rationale:**
- Dynamic imports can't be patched at module level
- sys.modules patching works for any import location
- Cleaner than restructuring source code

## Test Coverage Results

| Test File | Tests | Lines | Status |
|-----------|-------|-------|--------|
| test_email_sender.py | 31 | 768 | Passing |
| test_pdf_generator.py | 30 | 805 | 7 pass, 23 skip (no fpdf2) |
| test_email_webhook.py | 39 | 776 | Passing |
| **Total** | **100** | **2349** | **Passing** |

### Coverage Areas

**Email Sender (92.9% coverage):**
- Initialization with SendGrid and SMTP configs
- Database settings priority over config file
- Email sending with CC/BCC/attachments
- Quote, invoice, and invitation emails
- Error handling (API failures, timeouts)

**PDF Generator (6.7% coverage - skip when unavailable):**
- Initialization and branding configuration
- Quote PDF generation with fpdf2
- Invoice PDF with Nova template layout
- Page break handling

**Email Webhook (67.5% coverage):**
- Tenant email caching and lookup
- Email routing strategies (support_email, sendgrid_email, plus addressing)
- Tenant extraction from subject/headers
- Webhook endpoint handlers

## Coverage Summary

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Overall | ~35% | 36.2% | +1.2% |
| email_sender.py | ~40% | 92.9% | +52.9% |
| email_webhook.py | ~55% | 67.5% | +12.5% |

## Deviations from Plan

None - plan executed exactly as written.

## Verification

```bash
# All tests pass
pytest tests/test_email_sender.py -v  # 31 passed
pytest tests/test_pdf_generator.py -v  # 7 passed, 23 skipped
pytest tests/test_email_webhook.py -v  # 39 passed

# Coverage threshold met
pytest tests/ --cov=src --cov-report=term
# Total coverage: 36.18% (threshold: 25%)
```

## Next Steps

1. Install fpdf2 in CI to run PDF tests
2. Consider adding tests for process_inbound_email background task
3. Add integration tests for actual SendGrid API (with sandbox account)
