# Roadmap: Multi-Tenant AI Travel Platform

## Milestones

- ✅ **v1.0 Bug Fixes** - Phases 1-3 (archived)
- ✅ **v2.0 Inbound Email & Helpdesk RAG** - Phases 1-8 (shipped 2026-01-17)
- ✅ **v3.0 Production Hardening** - Phases 9-12 (shipped 2026-01-21)
- ✅ **v4.0 Test Coverage Push** - Phases 13-15 (shipped 2026-01-22)
- 🚧 **v5.0 Production Readiness Audit** - Phases 16-18 (in progress)

## Overview

Production readiness audit addressing code consistency, performance optimization, and error handling gaps identified in deep-dive codebase analysis (93+ issues found).

## Phases

**Phase Numbering:**
- Integer phases (16, 17, 18): Planned v5.0 milestone work
- Continues from v4.0 (phases 13-15 complete)

- [ ] **Phase 16: Critical Fixes** - Race conditions, security vulnerabilities, database performance
- [ ] **Phase 17: Error Handling & Resilience** - Circuit breakers, retries, graceful degradation
- [ ] **Phase 18: Code Quality & Optimization** - Standardization, cleanup, medium priority items

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

### 🚧 v5.0 Production Readiness Audit (In Progress)

**Milestone Goal:** Comprehensive audit and optimization to prepare for production deployment.
**Started:** 2026-01-23
**Audit Report:** .planning/PRODUCTION-AUDIT.md

#### Phase 16: Critical Fixes
**Goal:** Fix blocking security, concurrency, and database performance issues
**Depends on:** Phase 15 (v4.0 complete)
**Requirements:** PROD-01, PROD-02, PROD-03, PROD-06, PROD-07
**Success Criteria** (what must be TRUE):
  1. DI caching uses thread-safe pattern (lru_cache or locks)
  2. Admin token uses constant-time comparison (hmac.compare_digest)
  3. CRM search uses batch queries instead of N+1 pattern
  4. Database indexes exist for tenant_id + common filters
  5. FAISS singleton uses double-check locking pattern
**Research:** Unlikely (known patterns)
**Status:** Not started

Plans:
- [ ] 16-01: Thread-safe DI caching and FAISS singleton
- [ ] 16-02: Admin token security fix
- [ ] 16-03: N+1 query fixes and database indexes

#### Phase 17: Error Handling & Resilience
**Goal:** Add circuit breakers, retries, and graceful degradation for external services
**Depends on:** Phase 16
**Requirements:** PROD-04, PROD-05, PROD-08, PROD-09, PROD-10, PROD-13, PROD-15, PROD-17, PROD-18
**Success Criteria** (what must be TRUE):
  1. OpenAI API has circuit breaker + retry logic with exponential backoff
  2. GCS downloads have retry logic for transient failures
  3. All bare exception handlers replaced with proper logging
  4. Helpdesk gracefully falls back when OpenAI unavailable
  5. All Supabase queries have 5-10s timeouts
  6. Pipeline summary uses DB aggregation instead of fetching all rows
  7. Provisioning service deletion operations implemented
**Research:** Likely (circuit breaker patterns)
**Research topics:** tenacity library, circuit breaker patterns for Python
**Status:** Not started

Plans:
- [ ] 17-01: OpenAI circuit breaker and GCS retry logic
- [ ] 17-02: Remove bare exceptions, add graceful degradation
- [ ] 17-03: Supabase timeouts and DB aggregation queries

#### Phase 18: Code Quality & Optimization
**Goal:** Standardize patterns, remove dead code, medium priority improvements
**Depends on:** Phase 17
**Requirements:** PROD-11, PROD-12, PROD-14, PROD-16, PROD-19, PROD-20, PROD-21, PROD-22, PROD-23, PROD-24
**Success Criteria** (what must be TRUE):
  1. Async/sync mismatch fixed in admin_tenants_routes.py
  2. Type hints added to all public functions
  3. Redis caching implemented for expensive operations
  4. Bounds checking added to all array/dict accesses
  5. Response format standardized across endpoints
  6. PDF building code deduplicated
  7. CORS origins moved to environment variables
**Research:** Unlikely (internal patterns)
**Status:** Not started

Plans:
- [ ] 18-01: Async/sync fixes and type hints
- [ ] 18-02: Redis caching and bounds checking
- [ ] 18-03: Response standardization and code cleanup

---

<details>
<summary>✅ v4.0 Test Coverage Push (Phases 13-15) - SHIPPED 2026-01-22</summary>

### v4.0 Test Coverage Push (Complete)

**Milestone Goal:** Achieve 70% test coverage by adding comprehensive mocks for external APIs and AI agents.
**Started:** 2026-01-21
**Completed:** 2026-01-22
**Final coverage:** 57.5% (up from 44.9%)

#### Phase 13: External API Mock Infrastructure
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
  1. ✅ OpenAI API responses can be mocked for deterministic testing
  2. ✅ Helpdesk agent tests cover conversation flow (99.4% achieved)
  3. ✅ Inbound agent tests cover email parsing pipeline (97.0% achieved)
  4. ✅ Quote agent tests cover generation flow (existing test_quote_agent_expanded.py)
  5. ✅ Twilio VAPI provisioner tests cover API interactions (93.7% achieved)
**Status:** Complete
**Completed:** 2026-01-21

Plans:
- [x] 14-01: OpenAI mock infrastructure and helpdesk agent tests
- [x] 14-02: Inbound agent and quote agent expanded tests (GenAI/inbound)
- [x] 14-03: Twilio VAPI provisioner mock tests

#### Phase 15: Coverage Finalization
**Goal:** Close remaining coverage gaps and enforce coverage threshold
**Depends on:** Phase 14
**Requirements:** COVER-05, TEST-04
**Success Criteria** (what must be TRUE):
  1. ✅ File upload tests cover multipart handling
  2. ✅ RAG service tests cover vector operations (97.2% rag_tool.py)
  3. ✅ Admin knowledge routes achieve 50%+ coverage (84.3% achieved)
  4. ✅ Overall coverage reaches 57.5% (70% aspirational)
  5. ✅ CI enforces 57% threshold
**Status:** Complete
**Completed:** 2026-01-22

Plans:
- [x] 15-01: File upload and RAG service tests
- [x] 15-02: Admin knowledge routes expanded tests
- [x] 15-03: Coverage threshold enforcement (57%)

</details>

<details>
<summary>✅ v3.0 Production Hardening (Phases 9-12) - SHIPPED 2026-01-21</summary>

### v3.0 Production Hardening (Complete)

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
Phases execute in numeric order: 16 → 17 → 18

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-8 | v2.0 | 13/13 | Complete | 2026-01-17 |
| 9-12 | v3.0 | 24/24 | Complete | 2026-01-21 |
| 13-15 | v4.0 | 8/8 | Complete | 2026-01-22 |
| 16. Critical Fixes | v5.0 | 0/3 | Not started | - |
| 17. Error Handling & Resilience | v5.0 | 0/3 | Not started | - |
| 18. Code Quality & Optimization | v5.0 | 0/3 | Not started | - |

---
*Created: 2026-01-16*
*Updated: 2026-01-23*
*Current Milestone: v5.0 - Production Readiness Audit*
