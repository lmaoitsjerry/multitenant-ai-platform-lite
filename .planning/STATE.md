# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-21)

**Core value:** Production-ready multi-tenant AI travel platform with secure tenant isolation
**Current focus:** Phase 12 Extended - Additional Test Coverage (v3.1) COMPLETE

## Current Position

Phase: 12 of 12 (DevOps & CI/CD)
Plan: 10 of 10 complete
Status: Complete - Extended Test Coverage Milestone
Last activity: 2026-01-21 - Completed 12-10-PLAN.md (Onboarding, Privacy, Branding & Provisioning Tests)

Progress: [================] 100% (v3.0) + 6/6 extended tests

## Milestones

### v3.1: Extended Test Coverage (COMPLETE)
- 6 extended plans (12-05 to 12-10) for additional coverage
- Focus: Analytics, helpdesk, crm, webhook, email, pdf, onboarding, privacy, branding, provisioning tests
- Completed: 2026-01-21
- Coverage achieved: 37.4%

### v3.0: Production Hardening (COMPLETE)
- 4 phases (9-12), 15 plans executed
- Focus: Security vulnerabilities, scalability blockers, DevOps readiness
- Completed: 2026-01-21
- Source: Comprehensive code review findings

### v2.0: Inbound Email & Helpdesk RAG (COMPLETE)
- 8 phases, 13 plans executed
- Focus: Fix broken email pipeline, enhance helpdesk quality
- Shipped: 2026-01-17

### v1.0: Bug Fixes & Optimizations (COMPLETE)
- Archived: .planning/milestones/v1.0-bug-fixes.md

## Performance Metrics

**Velocity:**
- Total plans completed: 25 (v2.0: 13, v3.0: 6, v3.1: 6)
- Average duration: ~15 min
- Total execution time: ~10.5 hours

**By Phase (v3.0 + v3.1):**

| Phase | Plans | Status |
|-------|-------|--------|
| 9 | 3/3 | Complete |
| 10 | 4/4 | Complete |
| 11 | 4/4 | Complete |
| 12 | 10/10 | Complete (6 extended) |

## Accumulated Context

### Code Review Findings (v3.0 Focus)

**Critical Security Issues:**
1. ADMIN_API_TOKEN bypass when not set (admin_routes.py)
2. ~~X-Client-ID not validated against user's actual tenant~~ FIXED (09-01)
3. ~~Hardcoded admin token in frontend (zorah-internal-admin-2024)~~ FIXED (09-02)

**Scalability Blockers:**
1. ~~File-based tenant config (YAML per tenant) won't scale~~ FIXED (11-02: TenantConfigService with DB backend)
2. ~~In-memory rate limiting won't work across instances~~ FIXED (10-03)
3. ~~No Redis caching~~ FIXED (11-04: TenantConfigService Redis caching)

**DevOps Gaps:**
1. ~~No CI/CD pipeline~~ FIXED (12-03: GitHub Actions CI/CD)
2. ~~Dockerfile runs as root~~ FIXED (12-01: Non-root user uid 1000)
3. ~~No structured logging/tracing~~ FIXED (12-02: JSON logging with request ID)
4. ~~No test coverage enforcement~~ FIXED (12-04: pytest-cov with CI threshold)

### Decisions (v3.0 + v3.1)

| ID | Decision | Date |
|----|----------|------|
| D-09-01-01 | Validate X-Client-ID only when explicitly provided | 2026-01-21 |
| D-09-02-01 | Warn on missing token instead of throwing error | 2026-01-21 |
| D-09-03-01 | Use pytest with pytest-asyncio for async middleware tests | 2026-01-21 |
| D-10-02-01 | HSTS only added in non-development environments | 2026-01-21 |
| D-10-02-02 | Default CSP restrictive with env var override | 2026-01-21 |
| D-10-03-01 | Use redis>=5.0.0 for async support and stability | 2026-01-21 |
| D-10-03-02 | Graceful fallback to in-memory when Redis unavailable | 2026-01-21 |
| D-10-01-01 | Generic 500 error messages for server errors | 2026-01-21 |
| D-10-01-02 | Full exception logged with exc_info=True for traceback | 2026-01-21 |
| D-10-04-01 | Skip Redis tests when module unavailable | 2026-01-21 |
| D-11-01-01 | Use 014_tenant_config.sql (migrations 012-013 already exist) | 2026-01-21 |
| D-11-02-01 | Skip tn_* auto-generated test tenants (garbage data) | 2026-01-21 |
| D-11-02-02 | Use lazy imports in config/loader.py for TenantConfigService | 2026-01-21 |
| D-11-02-03 | Add config_source property to ClientConfig | 2026-01-21 |
| D-11-03-01 | Only migrate 4 real tenants, delete 63 tn_* test directories | 2026-01-21 |
| D-11-03-02 | Keep 'example' directory as template for new tenant setup | 2026-01-21 |
| D-11-03-03 | Database migration requires SQL migration to be run first | 2026-01-21 |
| D-11-04-01 | Set cache TTL to 300 seconds (5 minutes) | 2026-01-21 |
| D-11-04-02 | Skip caching for YAML_ONLY_TENANTS | 2026-01-21 |
| D-11-04-03 | Use redis.from_url() for connection | 2026-01-21 |
| D-12-01-01 | Use uid/gid 1000 for appuser/appgroup | 2026-01-21 |
| D-12-01-02 | Install curl for health checks instead of Python | 2026-01-21 |
| D-12-01-03 | Use COPY --chown for application files | 2026-01-21 |
| D-12-02-01 | Use contextvars for request ID propagation | 2026-01-21 |
| D-12-02-02 | Add JSON_LOGS env var toggle (default true) | 2026-01-21 |
| D-12-02-03 | RequestIdMiddleware added last in chain (runs first) | 2026-01-21 |
| D-12-03-01 | Use workflow_run trigger for deploy after CI success | 2026-01-21 |
| D-12-03-02 | Use Workload Identity Federation (no service account keys) | 2026-01-21 |
| D-12-03-03 | Separate test and docker-build jobs (parallel execution) | 2026-01-21 |
| D-12-04-01 | Coverage baseline at 15% (prevents major regression) | 2026-01-21 |
| D-12-04-02 | 70% coverage target is aspirational | 2026-01-21 |
| D-12-04-03 | Added pytest-cov dependency for coverage reporting | 2026-01-21 |
| D-12-06-01 | Auth middleware runs before validation (401 not 422) | 2026-01-21 |
| D-12-06-02 | Reset singleton _instance in each test for isolation | 2026-01-21 |
| D-12-05-01 | Focus route tests on auth requirement verification | 2026-01-21 |
| D-12-05-02 | Create chainable mock pattern for Supabase queries | 2026-01-21 |
| D-12-07-01 | Mock SupabaseTool via __init__ patching for CRM tests | 2026-01-21 |
| D-12-07-02 | Use tmp_path fixture for FAISSIndexManager file tests | 2026-01-21 |
| D-12-09-01 | Mock SendGrid API via requests.post patching | 2026-01-21 |
| D-12-09-02 | Skip PDF tests when libraries unavailable | 2026-01-21 |
| D-12-09-03 | Use sys.modules patching for dynamic imports | 2026-01-21 |
| D-12-10-01 | Accept 400/401 for auth-required endpoints | 2026-01-21 |
| D-12-10-02 | Use tmp_path fixture for provisioning file tests | 2026-01-21 |
| D-12-10-03 | Test against actual preset names from theme_presets.py | 2026-01-21 |

### Decisions (v2.0 - Recent)

| ID | Decision | Date |
|----|----------|------|
| D-08-02-03 | 503 when ADMIN_API_TOKEN not configured | 2026-01-17 |
| D-08-02-04 | 401 when X-Admin-Token header missing | 2026-01-17 |
| D-08-01-01 | Use HS256 algorithm for JWT verification | 2026-01-17 |

### Pending Todos

- ~~Run 014_tenant_config.sql in Supabase SQL Editor~~ DONE
- ~~Re-run migration: `python scripts/migrate_tenants_to_db.py --force`~~ DONE (4 tenants migrated)
- Set REDIS_URL in production environment for caching
- Configure GitHub secrets for CI/CD: GCP_PROJECT_ID, WIF_PROVIDER, WIF_SERVICE_ACCOUNT
- Set up Workload Identity Federation in GCP (see .github/workflows/README.md)

### Test Coverage Summary

| Test File | Tests | Status |
|-----------|-------|--------|
| test_auth_middleware.py | 19 | Passing |
| test_rate_limiter.py | 44 | Passing |
| test_tenant_config_service.py | 34 | Passing |
| test_api_routes.py | 24 | Passing |
| test_services.py | 21 | Passing |
| test_analytics_routes.py | 34 | Passing |
| test_helpdesk_service.py | 29 | Passing |
| test_supabase_tool.py | 53 | Passing |
| test_core_routes.py | 47 | Passing |
| test_pricing_routes.py | 32 | Passing |
| test_knowledge_routes.py | 35 | Passing |
| test_crm_service.py | 31 | Passing |
| test_email_sender.py | 31 | Passing |
| test_pdf_generator.py | 30 | 7 pass, 23 skip |
| test_email_webhook.py | 39 | Passing |
| test_onboarding_routes.py | 27 | Passing |
| test_privacy_routes.py | 35 | Passing |
| test_branding_routes.py | 39 | Passing |
| test_provisioning_service.py | 24 | Passing |
| **Total** | **620+** | **Passing** |

Current coverage: 37.4% (baseline threshold: 25%)
Target coverage: 70% (aspirational)

### Blockers/Concerns

- Need Redis instance for Cloud Run (Memorystore or external)
- ~~Migration strategy for 60+ existing tenant YAML files~~ COMPLETE: 63 tn_* deleted, 4 real tenants ready
- Test coverage at 37.4% - exceeds target of 35%

## Session Continuity

Last session: 2026-01-21 18:20 UTC
Stopped at: Completed 12-10-PLAN.md (Onboarding, Privacy, Branding & Provisioning Tests)
Resume file: None (v3.1 milestone complete)
