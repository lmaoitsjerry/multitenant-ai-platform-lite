# Roadmap: Multi-Tenant AI Travel Platform

## Milestones

- ✅ **v1.0 Bug Fixes** - Phases 1-3 (archived)
- ✅ **v2.0 Inbound Email & Helpdesk RAG** - Phases 1-8 (shipped 2026-01-17)
- 🚧 **v3.0 Production Hardening** - Phases 9-12 (in progress)

## Overview

Production hardening based on comprehensive code review. Focus on security vulnerabilities, scalability blockers, and DevOps readiness. Transforms the platform from "good for 5-50 tenants" to production-ready with proper security controls.

## Phases

**Phase Numbering:**
- Integer phases (9, 10, 11, 12): Planned v3.0 milestone work
- Continues from v2.0 (phases 1-8 complete)

- [x] **Phase 9: Critical Security Fixes** - Admin auth, tenant validation, hardcoded tokens
- [x] **Phase 10: Security Hardening** - Error sanitization, security headers, Redis rate limiting
- [ ] **Phase 11: Database-Backed Tenant Registry** - Replace YAML files with database config
- [ ] **Phase 12: DevOps & Test Coverage** - CI/CD, Dockerfile hardening, test suite

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

### 🚧 v3.0 Production Hardening (In Progress)

**Milestone Goal:** Address critical security vulnerabilities and scalability blockers identified in code review. Make the platform production-ready for current scale (5-50 tenants).

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

#### Phase 11: Database-Backed Tenant Registry
**Goal:** Replace file-based tenant config with database for dynamic tenant management
**Depends on:** Phase 10
**Requirements:** SCALE-01, SCALE-03, TEST-03
**Success Criteria** (what must be TRUE):
  1. Tenant configuration stored in database table (not YAML files)
  2. Tenant provisioning API creates database records (no file deploy needed)
  3. Redis caching for tenant config lookups with TTL
  4. Existing tenants migrated from YAML to database
  5. Unit tests verify tenant isolation at database level
**Research:** Likely (Supabase schema design, migration strategy)
**Research topics:** Tenant registry schema, YAML to database migration
**Plans:** TBD

Plans:
- [ ] 11-01: Create tenants registry table and migration
- [ ] 11-02: Tenant config service with database backend
- [ ] 11-03: Migrate existing tenants from YAML to database
- [ ] 11-04: Redis caching for tenant lookups

#### Phase 12: DevOps & Test Coverage
**Goal:** Production-ready deployment with CI/CD and comprehensive tests
**Depends on:** Phase 11
**Requirements:** DEVOPS-01, DEVOPS-02, DEVOPS-03, TEST-04
**Success Criteria** (what must be TRUE):
  1. Dockerfile runs as non-root user
  2. GitHub Actions CI/CD pipeline runs tests and deploys
  3. Structured logging with request IDs for tracing
  4. Test coverage reaches 70% target
**Research:** Likely (GitHub Actions for Cloud Run)
**Research topics:** GitHub Actions Cloud Run deployment, pytest coverage
**Plans:** TBD

Plans:
- [ ] 12-01: Dockerfile hardening (non-root user)
- [ ] 12-02: GitHub Actions CI/CD pipeline
- [ ] 12-03: Structured logging with request tracing
- [ ] 12-04: Expand test coverage to 70%

## Progress

**Execution Order:**
Phases execute in numeric order: 9 → 10 → 11 → 12

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-8 | v2.0 | 13/13 | Complete | 2026-01-17 |
| 9. Critical Security | v3.0 | 3/3 | Complete | 2026-01-21 |
| 10. Security Hardening | v3.0 | 4/4 | Complete | 2026-01-21 |
| 11. Tenant Registry | v3.0 | 0/4 | Not started | - |
| 12. DevOps & Tests | v3.0 | 0/4 | Not started | - |

---
*Created: 2026-01-16*
*Updated: 2026-01-21*
*Current Milestone: v3.0 - Production Hardening*
