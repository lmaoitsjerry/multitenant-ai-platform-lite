# Codebase Concerns

**Analysis Date:** 2025-01-23

## Tech Debt

**Duplicate Config Caching Patterns:**
- Issue: Multiple modules implement their own `_client_configs = {}` dict-based caching
- Files: `src/api/analytics_routes.py:33`, `src/api/helpdesk_routes.py:37`, `src/api/branding_routes.py`, `src/api/knowledge_routes.py`
- Impact: Inconsistent caching behavior; some use `lru_cache` (routes.py), others use plain dicts; memory leaks possible with unbounded dicts
- Fix approach: Consolidate to single cached dependency in `src/api/routes.py` using `lru_cache` pattern already established there

**FAISS Index Rebuild Not Implemented:**
- Issue: `rebuild_index` endpoint returns success but does not perform actual FAISS indexing
- Files: `src/api/admin_knowledge_routes.py:648` - has `# TODO: Implement actual FAISS indexing`
- Impact: Knowledge base documents marked as indexed but not actually searchable via FAISS
- Fix approach: Implement actual embedding generation and FAISS index creation using SentenceTransformer

**Privacy Data Export Incomplete:**
- Issue: DSAR data export generates data but does not upload to secure storage
- Files: `src/api/privacy_routes.py:782` - has `# TODO: Upload to Supabase Storage`
- Impact: GDPR compliance incomplete; users receive summary but not actual data file
- Fix approach: Implement Supabase Storage upload and generate secure time-limited download link

**Tenant Status Hardcoded:**
- Issue: Tenant status always returns "active" rather than checking database
- Files: `src/api/admin_tenants_routes.py:222` - has `status="active",  # TODO: Get from database`
- Impact: Cannot distinguish suspended/inactive tenants in admin views
- Fix approach: Add `status` column to tenant tracking table, query during list

**Admin Analytics TODOs:**
- Issue: Email and login tracking not implemented
- Files: `src/api/admin_analytics_routes.py:380-381` - `emails=0,  # TODO: Get from SendGrid` and `logins=0   # TODO: Track logins`
- Impact: Incomplete usage analytics for platform admin dashboard
- Fix approach: Integrate SendGrid stats API; implement login event tracking in auth_service

**Tenant Creation Date Tracking:**
- Issue: No proper tracking of when tenants were created
- Files: `src/api/admin_analytics_routes.py:517` - has `# TODO: Implement proper tracking`
- Impact: Cannot generate tenant growth reports or cohort analysis
- Fix approach: Add `created_at` to tenant config storage; backfill existing tenants

## Known Bugs

**None identified as critical** - v5.0 audit resolved major issues:
- Bare exception handlers fixed
- Async/sync mismatch resolved
- Circuit breaker added for OpenAI

## Security Considerations

**Debug Endpoint in Production:**
- Risk: `/webhooks/email/debug` endpoint logs all incoming data without processing
- Files: `src/webhooks/email_webhook.py:1127-1161`
- Current mitigation: None - endpoint is publicly accessible
- Recommendations: Add admin token requirement; disable in production via env flag; or remove entirely

**Public Helpdesk Endpoints:**
- Risk: Several helpdesk endpoints bypass JWT auth, relying only on X-Client-ID header
- Files: `src/middleware/auth_middleware.py:48-52` - PUBLIC_PATHS includes `/api/v1/helpdesk/ask`, `/api/v1/helpdesk/search`, etc.
- Current mitigation: Tenant isolation via X-Client-ID header
- Recommendations: Consider rate limiting per IP on these endpoints; monitor for abuse

**SUPABASE_JWT_SECRET Warning Ignored:**
- Risk: When JWT secret not set, verification is disabled with warning only
- Files: `src/services/auth_service.py:68-74` - uses dummy secret when env var missing
- Current mitigation: Warning logged
- Recommendations: Fail startup in production mode if JWT secret not configured

**Admin Token in Environment Only:**
- Risk: Single admin token for all admin operations
- Files: `src/api/admin_routes.py:72-82` - `verify_admin_token` checks ADMIN_API_TOKEN env var
- Current mitigation: Token validated on all admin routes
- Recommendations: Consider per-user admin auth; add token rotation capability; audit logging for admin actions

## Performance Bottlenecks

**Large File Sizes:**
- Problem: Several core files exceed 1000 lines, making them harder to maintain and test
- Files:
  - `src/tools/supabase_tool.py` (1757 lines)
  - `src/api/routes.py` (1450 lines)
  - `src/webhooks/email_webhook.py` (1162 lines)
  - `src/api/analytics_routes.py` (1161 lines)
- Cause: Monolithic service classes; all CRUD operations in single files
- Improvement path: Split into smaller focused modules (e.g., supabase_quotes.py, supabase_clients.py)

**In-Memory Rate Limit Store in Multi-Worker:**
- Problem: InMemoryRateLimitStore not shared across workers
- Files: `src/middleware/rate_limiter.py:46-88`
- Cause: Each worker has own dict; rate limits not effective with multiple processes
- Improvement path: Redis store already implemented; ensure REDIS_URL is set in production

**Global Singleton Pattern for Services:**
- Problem: Several services use global singletons that can't be reset in tests
- Files: `src/services/faiss_helpdesk_service.py:586-599` - `_faiss_service` global
- Cause: Performance optimization that complicates testing and hot-reload
- Improvement path: Use dependency injection; provide reset function (already exists for FAISS)

## Fragile Areas

**Email Webhook Tenant Resolution:**
- Files: `src/webhooks/email_webhook.py:196-286`
- Why fragile: Complex multi-strategy tenant lookup (6 different strategies); silent fallbacks; cache with TTL
- Safe modification: Add comprehensive logging; test each strategy independently; don't change order without testing all paths
- Test coverage: Has tests but edge cases around cache expiry, concurrent refresh need more coverage

**Quote Agent Hotel Calculation:**
- Files: `src/agents/quote_agent.py:410-459`
- Why fragile: Complex pricing logic with children ages, room types, meal plans
- Safe modification: Add unit tests for specific scenarios before changes; verify calculation against known quotes
- Test coverage: Basic tests exist; edge cases (single supplement, child sharing) need more

**CRM Client ID Formats:**
- Files: `src/services/crm_service.py:154-188`
- Why fragile: Supports both `CLI-XXXXXXXX` format and UUID format for backwards compatibility
- Safe modification: Document which format is preferred; add migration path to consolidate
- Test coverage: Tests exist for both formats

## Scaling Limits

**Tenant Email Cache:**
- Current capacity: All tenant emails cached in memory
- Limit: With 100+ tenants, cache refresh (every 5 minutes) queries all tenant configs
- Scaling path: Move to Redis cache; implement lazy loading per-tenant

**Supabase Client Cache:**
- Current capacity: One client per tenant cached in dict
- Limit: Unbounded growth with new tenants; no eviction policy
- Scaling path: Add LRU eviction; consider connection pooling

## Dependencies at Risk

**None Critical** - Recent audit ensured all dependencies are stable:
- Supabase Python client is maintained
- FastAPI/Pydantic actively developed
- OpenAI client updated with circuit breaker

## Missing Critical Features

**Audit Logging for Admin Actions:**
- Problem: Admin operations (tenant CRUD, user management) not logged
- Blocks: Compliance requirements; security incident investigation
- Priority: Medium - should implement before adding more admin capabilities

**Webhook Delivery Retry:**
- Problem: Outbound webhooks (if implemented) have no retry mechanism
- Blocks: Reliable event delivery to external systems
- Priority: Low - not currently using outbound webhooks

## Test Coverage Gaps

**Large Modules with Limited Coverage:**
- What's not tested: Deep paths in supabase_tool.py (1757 lines), error handling branches
- Files: `src/tools/supabase_tool.py`
- Risk: Database operation failures may not be handled correctly
- Priority: Medium

**Email Webhook Edge Cases:**
- What's not tested: Concurrent cache refresh race conditions; malformed email parsing; attachment handling failures
- Files: `src/webhooks/email_webhook.py`
- Risk: Production email processing failures hard to diagnose
- Priority: Medium

**Admin Analytics Aggregation:**
- What's not tested: Large dataset aggregation performance; edge cases with missing data
- Files: `src/api/admin_analytics_routes.py`
- Risk: Dashboard timeouts with large tenant counts
- Priority: Low

**PDF Generator Variations:**
- What's not tested: Multi-page quotes; currency formatting edge cases; logo missing scenarios
- Files: `src/utils/pdf_generator.py` (710 lines)
- Risk: Broken quote PDFs for certain data combinations
- Priority: Low

---

*Concerns audit: 2025-01-23 - Post v5.0 Production Readiness Audit*
