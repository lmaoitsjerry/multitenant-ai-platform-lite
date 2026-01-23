# Requirements

## Overview

Production hardening, security fixes, scalability improvements, and comprehensive test coverage for the Multi-Tenant AI Travel Platform.

## Categories

### Coverage (COVER) - v4.0

| ID | Requirement | Version | Priority |
|----|-------------|---------|----------|
| COVER-01 | BigQuery analytics mock infrastructure with realistic query responses | v4 | High |
| COVER-02 | LLM agent test suite with OpenAI response mocking (helpdesk, inbound, quote) | v4 | High |
| COVER-03 | Twilio VAPI provisioner tests with API mocking | v4 | Medium |
| COVER-04 | SendGrid advanced scenarios (templates, dynamic content, subusers) | v4 | Medium |
| COVER-05 | File upload and RAG service integration tests | v4 | High |

### Security (SEC)

| ID | Requirement | Version | Priority |
|----|-------------|---------|----------|
| SEC-01 | Require ADMIN_API_TOKEN in production, fail startup if missing | v3 | Critical |
| SEC-02 | Validate X-Client-ID header against user's actual tenant_id from JWT | v3 | Critical |
| SEC-03 | Remove detail=str(e) from error responses, use generic messages | v3 | High |
| SEC-04 | Add security headers (CSP, X-Frame-Options, HSTS) | v3 | High |
| SEC-05 | Remove hardcoded admin token from frontend (zorah-internal-admin-2024) | v3 | Critical |

### Scalability (SCALE)

| ID | Requirement | Version | Priority |
|----|-------------|---------|----------|
| SCALE-01 | Move tenant config from YAML files to database-backed registry | v3 | Critical |
| SCALE-02 | Replace in-memory rate limiting with Redis backend | v3 | High |
| SCALE-03 | Add Redis caching for tenant configuration lookups | v3 | Medium |

### DevOps (DEVOPS)

| ID | Requirement | Version | Priority |
|----|-------------|---------|----------|
| DEVOPS-01 | Add non-root user to Dockerfile | v3 | Medium |
| DEVOPS-02 | Create CI/CD pipeline with GitHub Actions | v3 | High |
| DEVOPS-03 | Add structured logging with request tracing | v3 | Medium |

### Testing (TEST)

| ID | Requirement | Version | Priority |
|----|-------------|---------|----------|
| TEST-01 | Add unit tests for auth middleware (X-Client-ID validation) | v3 | High |
| TEST-02 | Add unit tests for rate limiting | v3 | High |
| TEST-03 | Add unit tests for tenant isolation | v3 | High |
| TEST-04 | Achieve 70% test coverage target | v3 | Medium |

### Completed (DONE)

| ID | Requirement | Status |
|----|-------------|--------|
| PERF-01 | Tenant dashboard loads in <2 seconds perceived | ✓ Complete (v1) |
| PERF-02 | Admin platform loads in <2 seconds perceived | ✓ Complete (v1) |
| PERF-03 | Reduce redundant API calls on page mount | ✓ Complete (v1) |
| DATA-01 | Invoice paid_at field set correctly when payment received | ✓ Complete (v1) |
| DATA-02 | Admin revenue dashboard shows accurate totals | ✓ Complete (v1) |
| HELP-01 | Helpdesk uses FAISS RAG search | ✓ Complete (v2) |
| EMAIL-01 through EMAIL-06 | Inbound email auto-quote pipeline | ✓ Complete (v2) |
| RAG-01 through RAG-04 | Helpdesk RAG natural responses | ✓ Complete (v2) |
| SEC-JWT | JWT signature verification enabled | ✓ Complete (v2.0 Phase 8) |
| SEC-RATE | Rate limiting on auth endpoints | ✓ Complete (v2.0 Phase 8) |

## Version Scope

### v3 (Current Sprint - Production Hardening)

**Critical (Must-Do Before Production):**
- SEC-01: Require ADMIN_API_TOKEN in production
- SEC-02: Validate X-Client-ID against user's tenant
- SEC-05: Remove hardcoded admin token from frontend
- SCALE-01: Database-backed tenant registry

**High Priority:**
- SEC-03: Sanitize error messages
- SEC-04: Add security headers
- SCALE-02: Redis rate limiting
- DEVOPS-02: CI/CD pipeline
- TEST-01, TEST-02, TEST-03: Core test coverage

**Medium Priority:**
- SCALE-03: Redis config caching
- DEVOPS-01: Non-root Dockerfile
- DEVOPS-03: Structured logging
- TEST-04: 70% coverage target

### Production Readiness (PROD) - v5.0

**Blocking (Must Fix Before Production):**

| ID | Requirement | Priority |
|----|-------------|----------|
| PROD-01 | Fix race condition in DI caching (`routes.py:132-150`) | Critical |
| PROD-02 | Fix admin token timing attack vulnerability | Critical |
| PROD-03 | Fix N+1 queries in CRM search (`crm_service.py:290-334`) | Critical |
| PROD-04 | Add circuit breaker + retry for OpenAI API | Critical |
| PROD-05 | Remove 15 bare exception handlers (swallowing errors) | Critical |
| PROD-06 | Add database indexes for common query patterns | Critical |
| PROD-07 | Fix FAISS singleton thread safety | Critical |
| PROD-08 | Implement deletion operations in provisioning service | High |

**High Priority:**

| ID | Requirement | Priority |
|----|-------------|----------|
| PROD-09 | Standardize error handling on `safe_error_response()` | High |
| PROD-10 | Remove unused `logger.py`, use structured_logger | High |
| PROD-11 | Fix async/sync mismatch in `admin_tenants_routes.py` | High |
| PROD-12 | Add type hints to all public functions | Medium |
| PROD-13 | Replace pipeline_summary with database aggregation | High |
| PROD-14 | Add Redis caching for expensive operations (60s TTL) | High |
| PROD-15 | Add timeouts to all Supabase queries (5-10s) | High |
| PROD-16 | Add bounds checking to all array/dict accesses | High |
| PROD-17 | Implement graceful degradation when OpenAI unavailable | High |
| PROD-18 | Add retry logic for GCS downloads | High |

**Medium Priority:**

| ID | Requirement | Priority |
|----|-------------|----------|
| PROD-19 | Standardize response format across all endpoints | Medium |
| PROD-20 | Deduplicate PDF building code (3 locations) | Medium |
| PROD-21 | Centralize table name constants | Medium |
| PROD-22 | Add cache TTL to config/agent/service caches | Medium |
| PROD-23 | Optimize MMR search O(n²) complexity | Medium |
| PROD-24 | Move CORS origins to environment variables | Medium |

### Out of Scope (v6+)

- Full TypeScript migration for frontends
- Real-time WebSocket features
- Multi-GCP project consolidation (enterprise scale)
- Distributed tracing (OpenTelemetry)
- Fixing broken email pipeline (address after v5.0)
- Helpdesk RAG quality improvements (address after v5.0)

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SEC-01 | Phase 9 | ✓ Complete |
| SEC-02 | Phase 9 | ✓ Complete |
| SEC-05 | Phase 9 | ✓ Complete |
| SEC-03 | Phase 10 | ✓ Complete |
| SEC-04 | Phase 10 | ✓ Complete |
| SCALE-01 | Phase 11 | ✓ Complete |
| SCALE-02 | Phase 10 | ✓ Complete |
| SCALE-03 | Phase 11 | ✓ Complete |
| DEVOPS-01 | Phase 12 | ✓ Complete |
| DEVOPS-02 | Phase 12 | ✓ Complete |
| DEVOPS-03 | Phase 12 | ✓ Complete |
| TEST-01 | Phase 9 | ✓ Complete |
| TEST-02 | Phase 10 | ✓ Complete |
| TEST-03 | Phase 11 | ✓ Complete |
| TEST-04 | Phase 12 | ✓ Partial (45%, 70% deferred to v4) |
| COVER-01 | Phase 13 | ✓ Complete |
| COVER-02 | Phase 14 | ✓ Complete |
| COVER-03 | Phase 14 | ✓ Complete |
| COVER-04 | Phase 13 | ✓ Complete |
| COVER-05 | Phase 15 | ✓ Complete |
| TEST-04 | Phase 15 | ✓ Complete (57.5% achieved) |
| PROD-01, PROD-02, PROD-03, PROD-06, PROD-07 | Phase 16 | ✓ Complete |
| PROD-04, PROD-05, PROD-08 | Phase 17 | Pending |
| PROD-09 to PROD-18 | Phase 17 | Pending |
| PROD-19 to PROD-24 | Phase 18 | Pending |

**Coverage:**
- v3 requirements: 14 total (14 complete)
- v4 requirements: 6 total (6 complete)
- v5 requirements: 24 total (24 pending)
- Unmapped: 0 ✓

---
*Last updated: 2026-01-23*
*Milestone: v5.0 - Production Readiness Audit*
