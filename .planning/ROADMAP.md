# Roadmap: Multi-Tenant AI Travel Platform

## Milestones

- ✅ **v1.0 Bug Fixes** - Phases 1-3 (archived)
- ✅ **v2.0 Inbound Email & Helpdesk RAG** - Phases 1-8 (shipped 2026-01-17)
- ✅ **v3.0 Production Hardening** - Phases 9-12 (shipped 2026-01-21)
- 🚧 **v4.0 Test Coverage Push** - Phases 13-15 (in progress)

## Overview

Comprehensive test coverage push to reach 70% coverage target. Focus on external API mocking (BigQuery, OpenAI, Twilio, SendGrid) and AI agent testing (helpdesk, inbound, quote agents).

## Phases

**Phase Numbering:**
- Integer phases (13, 14, 15): Planned v4.0 milestone work
- Continues from v3.0 (phases 9-12 complete)

- [x] **Phase 13: External API Mock Infrastructure** - BigQuery mocking, SendGrid advanced scenarios
- [ ] **Phase 14: AI Agent Test Suite** - Helpdesk, inbound, quote agents + Twilio VAPI
- [ ] **Phase 15: Coverage Finalization** - RAG services, admin knowledge routes, 70% threshold

<details>
<summary>✅ v2.0 Inbound Email & Helpdesk RAG (Phases 1-8) - SHIPPED 2026-01-17</summary>

### Phase 1: Diagnostics & Logging
**Status:** Complete
**Plans:** 1/1 complete

### Phase 2: Tenant Lookup & Email Parsing
**Status:** Complete
**Plans:** 2/2 complete

### Phase 3: Quote Generation Pipeline
**Status:** Complete
**Plans:** 1/1 complete

### Phase 4: Email Sending & Notifications
**Status:** Complete
**Plans:** 1/1 complete

### Phase 5: Helpdesk RAG Enhancement
**Status:** Complete
**Plans:** 2/2 complete

### Phase 6: Integration Testing
**Status:** Complete
**Plans:** 2/2 complete

### Phase 7: Login Fix
**Status:** Complete
**Plans:** 1/1 complete

### Phase 8: Security Hardening & Bug Fixes
**Status:** Complete
**Plans:** 3/3 complete

</details>

## Phase Details

### 🚧 v4.0 Test Coverage Push (In Progress)

**Milestone Goal:** Achieve 70% test coverage by adding comprehensive mocks for external APIs and AI agents.
**Started:** 2026-01-21
**Current coverage:** 44.9% → Target: 70%

#### Phase 13: External API Mock Infrastructure ✅
**Goal:** Create reusable mock infrastructure for BigQuery and SendGrid
**Depends on:** Phase 12 (v3.0 complete)
**Requirements:** COVER-01, COVER-04
**Success Criteria** (what must be TRUE):
  1. ✅ BigQuery client can be mocked with realistic query responses
  2. ✅ Analytics routes tests achieve 50%+ coverage (66.4% achieved, up from 9.4%)
  3. ✅ SendGrid template and subuser tests cover advanced scenarios (87.5% coverage)
  4. ✅ Mock fixtures are reusable across test files
**Status:** Complete
**Completed:** 2026-01-21

Plans:
- [x] 13-01: BigQuery mock infrastructure and analytics route tests
- [x] 13-02: SendGrid advanced scenario tests (templates, subusers)

#### Phase 14: AI Agent Test Suite
**Goal:** Test AI agents with mocked LLM responses
**Depends on:** Phase 13
**Requirements:** COVER-02, COVER-03
**Success Criteria** (what must be TRUE):
  1. OpenAI API responses can be mocked for deterministic testing
  2. Helpdesk agent tests cover conversation flow (0% → 50%+)
  3. Inbound agent tests cover email parsing pipeline (0% → 50%+)
  4. Quote agent tests cover generation flow (existing + expanded)
  5. Twilio VAPI provisioner tests cover API interactions (0% → 50%+)
**Research:** Unlikely (OpenAI mocking patterns well-documented)
**Status:** Not started

Plans:
- [ ] 14-01: OpenAI mock infrastructure and helpdesk agent tests
- [ ] 14-02: Inbound agent and quote agent expanded tests
- [ ] 14-03: Twilio VAPI provisioner mock tests

#### Phase 15: Coverage Finalization
**Goal:** Close remaining coverage gaps and enforce 70% threshold
**Depends on:** Phase 14
**Requirements:** COVER-05, TEST-04
**Success Criteria** (what must be TRUE):
  1. File upload tests cover multipart handling
  2. RAG service tests cover vector operations (rag_tool.py)
  3. Admin knowledge routes achieve 50%+ coverage (up from 17.9%)
  4. Overall coverage reaches 70%
  5. CI enforces 70% threshold (update pyproject.toml + ci.yml)
**Research:** Unlikely (internal patterns)
**Status:** Not started

Plans:
- [ ] 15-01: File upload and RAG service tests
- [ ] 15-02: Admin knowledge routes expanded tests
- [ ] 15-03: Coverage threshold enforcement (70%)

<details>
<summary>✅ v3.0 Production Hardening (Phases 9-12) - SHIPPED 2026-01-21</summary>

### ✅ v3.0 Production Hardening (Complete)

**Milestone Goal:** Address critical security vulnerabilities and scalability blockers identified in code review. Make the platform production-ready for current scale (5-50 tenants).
**Shipped:** 2026-01-21

#### Phase 9: Critical Security Fixes ✅
**Goal:** Fix authentication vulnerabilities that could allow unauthorized access
**Depends on:** Phase 8 (v2.0 complete)
**Requirements:** SEC-01, SEC-02, SEC-05, TEST-01
**Success Criteria** (what must be TRUE):
  1. ✅ Admin endpoints fail with 503 if ADMIN_API_TOKEN not set (already implemented)
  2. ✅ X-Client-ID header validated against user's actual tenant_id from JWT claims
  3. ✅ Frontend admin panel uses environment variable for admin token, not hardcoded
  4. ✅ Unit tests verify auth middleware rejects tenant spoofing attempts (19 tests passing)
**Status:** Complete
**Completed:** 2026-01-21

Plans:
- [x] 09-01: X-Client-ID tenant validation (SEC-02 verified)
- [x] 09-02: Remove hardcoded admin token from frontend (SEC-05)
- [x] 09-03: Auth middleware unit tests (TEST-01)

#### Phase 10: Security Hardening ✅
**Goal:** Harden the application against common web vulnerabilities and prepare for scale
**Depends on:** Phase 9
**Requirements:** SEC-03, SEC-04, SCALE-02, TEST-02
**Success Criteria** (what must be TRUE):
  1. ✅ Error responses use generic messages, no detail=str(e) exposing internals
  2. ✅ Security headers (CSP, X-Frame-Options, HSTS, X-Content-Type-Options) on all responses
  3. ✅ Rate limiting uses Redis backend (works across multiple instances)
  4. ✅ Unit tests verify rate limiting behavior (44 tests, 36 passing)
**Status:** Complete
**Completed:** 2026-01-21

Plans:
- [x] 10-01: Sanitize error messages across all routes (93 instances replaced)
- [x] 10-02: Add security headers middleware (7 headers)
- [x] 10-03: Redis-backed rate limiting with fallback
- [x] 10-04: Rate limiting unit tests

#### Phase 11: Database-Backed Tenant Registry ✅
**Goal:** Replace file-based tenant config with database for dynamic tenant management
**Depends on:** Phase 10
**Requirements:** SCALE-01, SCALE-03, TEST-03
**Success Criteria** (what must be TRUE):
  1. ✅ Tenant configuration stored in database table (tenant_config JSONB column)
  2. ✅ Tenant provisioning API creates database records (POST /api/v1/admin/tenants)
  3. ✅ Redis caching for tenant config lookups with TTL (5 min TTL)
  4. ✅ Existing tenants migrated from YAML to database (4 real tenants, 63 tn_* deleted)
  5. ✅ Unit tests verify tenant isolation at database level (34 tests passing)
**Status:** Complete
**Completed:** 2026-01-21

Plans:
- [x] 11-01: Tenant config JSONB schema extension (014_tenant_config.sql)
- [x] 11-02: TenantConfigService with database backend + provisioning API
- [x] 11-03: Migrate 4 real tenants, delete 63 tn_* test directories
- [x] 11-04: Redis caching + tenant isolation unit tests

#### Phase 12: DevOps & Test Coverage ✅
**Goal:** Production-ready deployment with CI/CD and comprehensive tests
**Depends on:** Phase 11
**Requirements:** DEVOPS-01, DEVOPS-02, DEVOPS-03, TEST-04
**Success Criteria** (what must be TRUE):
  1. ✅ Dockerfile runs as non-root user (uid 1000, appuser)
  2. ✅ GitHub Actions CI/CD pipeline runs tests and deploys (ci.yml + deploy.yml)
  3. ✅ Structured logging with request IDs for tracing (JSON format, X-Request-ID header)
  4. ✅ Test coverage baseline established (45% achieved, 70% deferred to v4.0)
**Status:** Complete
**Completed:** 2026-01-21

Plans:
- [x] 12-01: Dockerfile hardening (non-root user)
- [x] 12-02: Structured logging with request tracing
- [x] 12-03: GitHub Actions CI/CD pipeline
- [x] 12-04: Test coverage baseline (pyproject.toml + ci.yml)
- [x] 12-05: SupabaseTool & core routes tests
- [x] 12-06: Analytics & helpdesk tests
- [x] 12-07: Pricing, knowledge & CRM tests
- [x] 12-08: (merged into 12-13)
- [x] 12-09: External integration tests (email, PDF, webhook)
- [x] 12-10: Onboarding, privacy, branding & provisioning tests
- [x] 12-11: Admin, notifications, settings & users tests
- [x] 12-12: Inbound, templates, RAG & BigQuery tests
- [x] 12-13: Final coverage push (leaderboard, middleware, quote agent)

</details>

## Progress

**Execution Order:**
Phases execute in numeric order: 13 → 14 → 15

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-8 | v2.0 | 13/13 | Complete | 2026-01-17 |
| 9-12 | v3.0 | 24/24 | Complete | 2026-01-21 |
| 13. External API Mocks | v4.0 | 2/2 | Complete | 2026-01-21 |
| 14. AI Agent Tests | v4.0 | 0/3 | Not started | - |
| 15. Coverage Finalization | v4.0 | 0/3 | Not started | - |

---
*Created: 2026-01-16*
*Updated: 2026-01-21*
*Current Milestone: v4.0 - Test Coverage Push (in progress)*
