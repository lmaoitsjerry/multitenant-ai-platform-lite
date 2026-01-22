# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-21)

**Core value:** Production-ready multi-tenant AI travel platform with secure tenant isolation
**Current focus:** v4.0 Test Coverage Push — 70% coverage target

## Current Position

Phase: 15 of 15 (Coverage Finalization)
Plan: 2 of 3 (Admin Knowledge Routes Coverage)
Status: Complete
Last activity: 2026-01-22 — Completed 15-02 (118 tests, 79% coverage)

Progress: [===============-----] 75% (v4.0: Phases 13-14 complete, 15-01-02 complete)

## Milestones

### v4.0: Test Coverage Push (ACTIVE)
- Goal: Achieve 70% test coverage
- Focus: External API mocking (BigQuery, Twilio, SendGrid, LLM agents)
- Started: 2026-01-21
- Current coverage: 54.5% (up from 44.9%)
- Target coverage: 70%
- Phase 13: Complete (BigQuery + SendGrid mocks, 136 new tests)
- Phase 14: Complete (AI agent mocks, 179 new tests, 96% agent coverage)

### v3.0: Production Hardening (COMPLETE)
- 4 phases (9-12), 24 plans executed
- Focus: Security vulnerabilities, scalability blockers, DevOps readiness
- Completed: 2026-01-21
- Coverage achieved: 44.9% (1,104 tests)
- Audit: .planning/milestones/v3.0-MILESTONE-AUDIT.md

### v2.0: Inbound Email & Helpdesk RAG (COMPLETE)
- 8 phases, 13 plans executed
- Focus: Fix broken email pipeline, enhance helpdesk quality
- Shipped: 2026-01-17

### v1.0: Bug Fixes & Optimizations (COMPLETE)
- Archived: .planning/milestones/v1.0-bug-fixes.md

## Performance Metrics

**Velocity:**
- Total plans completed: 29 (v2.0: 13, v3.0: 6, v3.1: 6, v3.2: 2, v3.3: 1, v3.4: 1)
- Average duration: ~15 min
- Total execution time: ~12 hours

**By Phase (v3.0 + v3.1 + v3.2 + v3.3):**

| Phase | Plans | Status |
|-------|-------|--------|
| 9 | 3/3 | Complete |
| 10 | 4/4 | Complete |
| 11 | 4/4 | Complete |
| 12 | 13/13 | Complete (9 extended) |

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

### Decisions (v3.0 + v3.1 + v3.2)

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
| D-12-12-01 | Use X-Client-ID routing tests instead of JWT auth | 2026-01-21 |
| D-12-12-02 | Mock SupabaseTool via src.tools.supabase_tool patching | 2026-01-21 |
| D-12-12-03 | Test route structure with router.routes inspection | 2026-01-21 |
| D-12-12-04 | Test BigQuery client initialization failures gracefully | 2026-01-21 |
| D-12-11-01 | Skip tests for missing modules (VAPIProvisioner, SupabaseService) | 2026-01-21 |
| D-12-11-02 | Focus on auth-requirement verification for protected endpoints | 2026-01-21 |
| D-12-11-03 | Test Pydantic models directly in addition to endpoint tests | 2026-01-21 |
| D-12-13-01 | Coverage target of 70% not reached due to external API dependencies | 2026-01-21 |
| D-12-13-02 | Estimated 20-25 hours needed to reach 70% coverage | 2026-01-21 |
| D-12-13-03 | Largest gaps: analytics_routes, admin_knowledge_routes, agents | 2026-01-21 |
| D-13-02-01 | Use MockSendGridResponse class with status_code and body attributes | 2026-01-21 |
| D-13-02-02 | Implement fluent interface via MockSendGridClientEndpoint class | 2026-01-21 |
| D-13-02-03 | Patch SupabaseTool at src.tools.supabase_tool for inline imports | 2026-01-21 |
| D-13-01-01 | Mock BigQuery with pattern-matching for SQL query responses | 2026-01-21 |
| D-13-01-02 | Test route handlers directly to bypass auth middleware for coverage | 2026-01-21 |
| D-13-01-03 | Patch at source module location for lazy imports | 2026-01-21 |
| D-14-03-01 | Use MockHTTPResponse class matching requests.Response interface | 2026-01-21 |
| D-14-03-02 | Create factory classes for Twilio and VAPI response generation | 2026-01-21 |
| D-14-03-03 | Support pattern-based URL matching for flexible mock configuration | 2026-01-21 |
| D-14-01-01 | Use direct _client injection instead of patching inline imports | 2026-01-21 |
| D-14-01-02 | Create MockConversationClient for sequential response testing | 2026-01-21 |
| D-14-01-03 | Patch FAISS service at source module for inline imports | 2026-01-21 |
| D-14-02-01 | Mock FAISS by pre-setting _index and _chunks instead of patching import | 2026-01-21 |
| D-15-01-01 | Pre-inject mocks into sys.modules before Vertex AI import | 2026-01-22 |
| D-15-01-02 | Support dict, list, and LangChain docstore formats in tests | 2026-01-22 |
| D-15-02-01 | Skip TestClient auth tests due to FAISS/GCS initialization hangs | 2026-01-22 |
| D-15-02-02 | Test endpoint functions directly with mocked dependencies | 2026-01-22 |

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
| test_analytics_routes.py | 73 | Passing (66% coverage) |
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
| test_inbound_routes.py | 41 | Passing |
| test_templates_routes.py | 43 | Passing |
| test_rag_services.py | 48 | Passing |
| test_bigquery_tool.py | 40 | Passing |
| test_admin_routes.py | 25 | 22 pass, 3 skip |
| test_notifications_routes.py | 22 | Passing |
| test_settings_routes.py | 22 | Passing |
| test_users_routes.py | 32 | Passing |
| test_leaderboard_routes.py | 43 | Passing |
| test_middleware_integration.py | 39 | Passing |
| test_quote_agent_expanded.py | 42 | Passing |
| test_performance_service_expanded.py | 35 | Passing |
| test_sendgrid_admin.py | 29 | Passing |
| test_admin_sendgrid_routes.py | 34 | Passing |
| test_twilio_vapi_provisioner.py | 58 | Passing (93.7% coverage) |
| test_helpdesk_agent.py | 58 | Passing (99.4% coverage) |
| test_inbound_agent.py | 63 | Passing (97% coverage) |
| test_rag_tool.py | 30 | Passing (new) |
| test_faiss_service.py | 33 | Passing (new) |
| test_admin_knowledge_routes.py | 118 | 103 pass, 15 skip (79% coverage) |
| **Total** | **1551** | **Passing** |

Current coverage: ~55% (measured with pytest-cov)
Target coverage: 70% (aspirational - requires continued mocking work)

### Blockers/Concerns

- Need Redis instance for Cloud Run (Memorystore or external)
- ~~Migration strategy for 60+ existing tenant YAML files~~ COMPLETE: 63 tn_* deleted, 4 real tenants ready
- Test coverage at 44.9% (70% target requires BigQuery/Twilio/SendGrid mocking)

### Coverage Gap Analysis

| Module | Coverage | Reason Not Higher |
|--------|----------|-------------------|
| analytics_routes.py | 66% | BigQuery/Supabase mocked via direct handler tests |
| admin_knowledge_routes.py | 79.0% | Direct function testing achieved |
| helpdesk_agent.py | 99.4% | Fully mocked with OpenAI fixtures |
| inbound_agent.py | 97.0% | Fully mocked with GenAI fixtures |
| twilio_vapi_provisioner.py | 93.7% | Fully mocked with fixtures |

## Session Continuity

Last session: 2026-01-22
Stopped at: Completed 15-02-PLAN.md
Resume file: None — ready for 15-03-PLAN.md
