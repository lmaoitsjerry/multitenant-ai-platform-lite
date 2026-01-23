# Codebase Concerns

**Analysis Date:** 2026-01-23

## Tech Debt

**Bare Exception Handlers in Email Webhook:**
- Issue: Multiple bare `except:` clauses swallow all exceptions without logging
- Files: `src/webhooks/email_webhook.py` (lines 320, 334, 349, 368, 422, 761, 936, 1007)
- Impact: Silent failures make debugging tenant lookup issues nearly impossible
- Fix approach: Replace bare `except:` with `except Exception as e:` and add debug logging

**Incomplete Tenant Deprovisioning:**
- Issue: `deprovision_tenant()` method has three unimplemented TODOs
- Files: `src/services/provisioning_service.py` (lines 735-737)
- Impact: Cannot safely remove tenants; orphaned SendGrid subusers and BigQuery datasets accumulate
- Fix approach: Implement SendGrid subuser deletion, BigQuery dataset deletion, and client directory cleanup

**FAISS Index Rebuild is a Stub:**
- Issue: `rebuild_faiss_index` endpoint marks documents as indexed but doesn't actually rebuild the index
- Files: `src/api/admin_knowledge_routes.py` (lines 648-656)
- Impact: Knowledge base updates don't reflect in search until manual intervention
- Fix approach: Integrate with `src/services/faiss_helpdesk_service.py` to trigger actual index rebuild

**Data Export Stores in DSAR Record (Not Downloadable):**
- Issue: Privacy data export doesn't upload to storage; data sits in database record
- Files: `src/api/privacy_routes.py` (lines 778-779)
- Impact: GDPR data portability compliance incomplete; users can't download their data
- Fix approach: Implement Supabase Storage upload and generate time-limited download URLs

**Global Caches Without Invalidation:**
- Issue: Route-level caches (`_client_configs`, `_quote_agents`, `_crm_services`) never invalidated
- Files: `src/api/routes.py` (lines 132-134)
- Impact: Config changes require server restart to take effect
- Fix approach: Add cache invalidation endpoints or implement TTL-based expiry

**Supabase Tool Returns None on All Errors:**
- Issue: 80+ methods return `None` or `[]` on any exception, losing error context
- Files: `src/tools/supabase_tool.py` (extensive - see lines 149, 170, 174, 179, etc.)
- Impact: Callers can't distinguish between "no data" and "query failed"; silent data loss
- Fix approach: Implement a Result type pattern or raise specific exceptions

## Known Bugs

**None identified during analysis**

## Security Considerations

**Admin Routes Bypass JWT Authentication:**
- Risk: Admin endpoints use separate X-Admin-Token, skipping JWT middleware entirely
- Files: `src/middleware/auth_middleware.py` (line 61), `src/api/admin_routes.py` (line 71)
- Current mitigation: Admin token must be set via environment variable; 503 if missing
- Recommendations: Consider requiring both JWT (for audit trail) and admin token; add rate limiting

**Onboarding Routes Fully Public:**
- Risk: Tenant onboarding endpoints require no authentication
- Files: `src/middleware/auth_middleware.py` (line 62)
- Current mitigation: Some endpoints verify email domain; reCAPTCHA could be added
- Recommendations: Implement CAPTCHA; rate limit by IP; add email verification step

**Helpdesk Endpoints Publicly Accessible:**
- Risk: Search, ask, and topic endpoints have no authentication
- Files: `src/middleware/auth_middleware.py` (lines 48-52)
- Current mitigation: Uses X-Client-ID header for tenant context
- Recommendations: Consider requiring at least API key for external access; add rate limits

**Passwords in Memory During Provisioning:**
- Risk: Auto-generated SendGrid passwords stored in result dict, logged at info level
- Files: `src/services/provisioning_service.py` (lines 119-120)
- Current mitigation: Passwords only in return value, not persisted
- Recommendations: Return password once then discard; never log credentials

## Performance Bottlenecks

**Supabase Client Per-Request Pattern:**
- Problem: Although cached, client initialization still happens per-tenant-per-restart
- Files: `src/tools/supabase_tool.py` (lines 69-84)
- Cause: Cache keyed by `client_id:url[:20]`, so different URLs create new clients
- Improvement path: Pool connections; use singleton per-tenant client with connection reuse

**PDF Generation Low Coverage (6.7%):**
- Problem: `pdf_generator.py` has 438 lines but only ~30 are covered by tests
- Files: `src/utils/pdf_generator.py`
- Cause: WeasyPrint/fpdf2 fallback logic untested; complex HTML rendering
- Improvement path: Add unit tests with mocked PDF libraries; test both code paths

**Template Renderer Low Coverage (31.4%):**
- Problem: Template loading and agent prompt rendering untested
- Files: `src/utils/template_renderer.py`
- Cause: File I/O operations and Jinja2 integration need fixtures
- Improvement path: Add tests with mock file system; test error paths

**ReRanker Service Low Coverage (16.5%):**
- Problem: Cross-encoder model loading/inference almost entirely untested
- Files: `src/services/reranker_service.py`
- Cause: Requires sentence-transformers model download at test time
- Improvement path: Mock CrossEncoder class; test fallback behavior

## Fragile Areas

**Tenant Lookup in Email Webhook:**
- Files: `src/webhooks/email_webhook.py` (lines 290-370)
- Why fragile: 5 different lookup strategies with bare exception handlers; silent failures
- Safe modification: Add comprehensive logging before any changes; test all strategies
- Test coverage: ~67.5% - critical paths around line 314-370 need more tests

**Config Loading Multi-Source:**
- Files: `config/loader.py`, `src/services/tenant_config_service.py`
- Why fragile: Config comes from YAML files, database, and environment variables with fallback chains
- Safe modification: Always test with both database-backed and YAML-only tenants
- Test coverage: 65.6% for tenant_config_service - cache invalidation paths untested

**Quote Agent Orchestration:**
- Files: `src/agents/quote_agent.py` (962 lines)
- Why fragile: Coordinates 7 services (BigQuery, PDF, Email, Supabase, CRM, etc.)
- Safe modification: Test with all services mocked; verify error handling for each failure mode
- Test coverage: Check `test_quote_agent_expanded.py` for coverage gaps

## Scaling Limits

**In-Memory Knowledge Cache:**
- Current capacity: All documents stored in `_knowledge_cache` dict
- Limit: Process memory; ~1000 documents before significant memory pressure
- Scaling path: Move to Redis cache; implement LRU eviction

**Single-Process Architecture:**
- Current capacity: Single FastAPI process handles all requests
- Limit: ~500 concurrent requests before degradation
- Scaling path: Horizontal scaling with Kubernetes; add Redis for shared state

**BigQuery Rate Limits:**
- Current capacity: Default BigQuery quotas (100 concurrent queries)
- Limit: High-traffic quote generation could hit quota
- Scaling path: Implement query caching; batch rate lookups; use slots

## Dependencies at Risk

**No Critical Dependency Issues Identified**

All major dependencies (FastAPI, Supabase, BigQuery, SendGrid) are actively maintained.

## Missing Critical Features

**No Rate Limiting on Public Endpoints:**
- Problem: Helpdesk search, onboarding endpoints have no rate limiting
- Blocks: Production deployment without DDoS protection
- Note: `src/middleware/rate_limiter.py` exists but abstract methods unimplemented

**No Automated Backup/Recovery:**
- Problem: No database backup orchestration
- Blocks: Disaster recovery capability

**No Metrics/APM Integration:**
- Problem: Only logging; no structured metrics export
- Blocks: Proactive performance monitoring

## Test Coverage Gaps

**Email Webhook Critical Paths:**
- What's not tested: Lines 164-193 (tenant settings loading), 757-913 (diagnostic endpoints)
- Files: `src/webhooks/email_webhook.py`
- Risk: Tenant lookup failures could go undetected
- Priority: High

**Supabase Tool (58.6% coverage):**
- What's not tested: User management (lines 1266-1600), template settings, many error paths
- Files: `src/tools/supabase_tool.py`
- Risk: Data operations could fail silently
- Priority: High

**PDF Generator (6.7% coverage):**
- What's not tested: WeasyPrint path (lines 90-236), fpdf path (lines 289-697)
- Files: `src/utils/pdf_generator.py`
- Risk: Quote PDFs could generate incorrectly
- Priority: Medium

**Logger Module (0% coverage):**
- What's not tested: All lines (3-11)
- Files: `src/utils/logger.py`
- Risk: Low - simple config module
- Priority: Low

**Tenant Config Service (65.6% coverage):**
- What's not tested: Database sync (lines 268-295), secret stripping (lines 444-476)
- Files: `src/services/tenant_config_service.py`
- Risk: Config updates could corrupt tenant settings
- Priority: High

---

*Concerns audit: 2026-01-23*
