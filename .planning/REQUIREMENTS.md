# Requirements

## Overview

Production hardening, security fixes, and scalability improvements for the Multi-Tenant AI Travel Platform based on comprehensive code review.

## Categories

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

### Out of Scope (v4+)

- Full TypeScript migration for frontends
- Real-time WebSocket features
- VAPI voice call integration
- Multi-GCP project consolidation (enterprise scale)
- Distributed tracing (OpenTelemetry)

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
| DEVOPS-01 | Phase 12 | Pending |
| DEVOPS-02 | Phase 12 | Pending |
| DEVOPS-03 | Phase 12 | Pending |
| TEST-01 | Phase 9 | ✓ Complete |
| TEST-02 | Phase 10 | ✓ Complete |
| TEST-03 | Phase 11 | ✓ Complete |
| TEST-04 | Phase 12 | Pending |

**Coverage:**
- v3 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0 ✓

---
*Last updated: 2026-01-21*
*Milestone: v3.0 - Production Hardening*
