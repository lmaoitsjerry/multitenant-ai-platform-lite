# Codebase Concerns

**Analysis Date:** 2026-01-16

## Tech Debt

**FAISS Indexing Not Implemented:**
- Issue: The rebuild FAISS index endpoint is stubbed - it only marks documents as indexed without actual indexing
- Files: `src/api/admin_knowledge_routes.py` lines 640-672
- Impact: Knowledge base search may not reflect document changes; rebuild operation has no effect
- Fix approach: Implement actual FAISS index rebuild using OpenAI embeddings and faiss library

**TODOs Scattered Throughout Codebase:**
- Issue: Multiple unimplemented features marked with TODO comments
- Files:
  - `src/api/admin_analytics_routes.py:380` - TODO: Get emails from SendGrid
  - `src/api/admin_analytics_routes.py:381` - TODO: Track logins
  - `src/api/admin_analytics_routes.py:519` - TODO: Track tenant creation dates
  - `src/api/admin_tenants_routes.py:191` - TODO: Get status from database
  - `src/api/privacy_routes.py:789` - TODO: Upload to Supabase Storage
  - `src/services/provisioning_service.py:735-737` - TODO: Implement tenant deletion
- Impact: Features appear complete but are missing functionality
- Fix approach: Audit all TODO comments and either implement or remove with documented decision

**Rate Limiter Uses Abstract Base Class Without Implementation:**
- Issue: `RateLimitStore` base class has `NotImplementedError` methods at lines 37, 40, 43
- Files: `src/middleware/rate_limiter.py` lines 33-43
- Impact: If base class is instantiated directly, it will crash
- Fix approach: Add `abc.ABC` and `@abstractmethod` decorators for proper Python abstract class

**Provisioning Service Deletion Not Implemented:**
- Issue: `deprovision_tenant` method has TODO stubs for critical cleanup operations
- Files: `src/services/provisioning_service.py` lines 735-737
- Impact: Tenant deletion leaves orphaned SendGrid subusers, BigQuery datasets, and client directories
- Fix approach: Implement SendGrid subuser deletion, BigQuery dataset cleanup, and file removal

## Known Bugs

**Hybrid File/Database Storage Desync:**
- Symptoms: Settings changes made via API don't persist across server restarts
- Files: `src/api/onboarding_routes.py`, `config/loader.py`
- Trigger: Update settings via API then restart server - YAML file not updated
- Workaround: Database records now created during onboarding (recently fixed)
- Status: Partially fixed - onboarding now creates DB records, but YAML and DB can still diverge

**Silent Exception Swallowing:**
- Symptoms: Operations fail silently without user feedback
- Files: Multiple files with `except: pass` or `except Exception: return None`
  - `src/webhooks/email_webhook.py` lines 73, 83, 94, 112
  - `src/tools/supabase_tool.py` line 1084
  - `src/api/routes.py` line 693
- Trigger: Any exception in these code paths
- Workaround: None - failures are invisible
- Fix approach: Add proper logging before silent returns; consider raising or returning error info

## Security Considerations

**Admin Endpoints Unprotected in Dev Mode:**
- Risk: If `ADMIN_API_TOKEN` env var is not set, all admin endpoints are accessible without authentication
- Files: `src/api/admin_routes.py` lines 70-77
- Current mitigation: Warning logged, but access is still granted
- Recommendations: Fail closed - require token even in dev, or use a dev-specific bypass flag

**Credentials Stored in Plain Text YAML Files:**
- Risk: Supabase service keys, SendGrid API keys, and other secrets are stored in `clients/{tenant_id}/client.yaml`
- Files: All files matching `clients/*/client.yaml`
- Current mitigation: None - files are in .gitignore but still on disk
- Recommendations: Use environment variables with references like `${SUPABASE_SERVICE_KEY}` in YAML; rotate credentials regularly

**JWT Secret Fallback to Supabase Key:**
- Risk: JWT verification uses Supabase key as fallback secret if `SUPABASE_JWT_SECRET` not set
- Files: `src/services/auth_service.py` line 62
- Current mitigation: Works but reduces security separation
- Recommendations: Always require explicit JWT secret configuration

**Public Paths Include Sensitive Endpoints:**
- Risk: Some endpoints bypass authentication that may need protection
- Files: `src/middleware/auth_middleware.py` lines 25-64
- Current mitigation: Individual endpoint validation where needed
- Recommendations: Audit PUBLIC_PREFIXES list - `/api/v1/onboarding/` allows unauthenticated tenant creation

**No CORS Configuration Visible:**
- Risk: Cross-origin requests may be unrestricted
- Files: `main.py` (not fully audited)
- Recommendations: Verify CORS middleware with explicit allowed origins

## Performance Bottlenecks

**Large Files Without Pagination:**
- Problem: Several services fetch all records without pagination
- Files:
  - `src/tools/supabase_tool.py` - 1683 lines, many select-all queries
  - `src/services/crm_service.py` - pipeline calculations load all clients
- Cause: Missing LIMIT/OFFSET on database queries
- Improvement path: Add pagination parameters to list endpoints; use cursor-based pagination

**No Database Connection Pooling:**
- Problem: Supabase clients are cached per tenant but may create many connections
- Files: `src/tools/supabase_tool.py` lines 64-84, `src/services/auth_service.py` lines 18-35
- Cause: Each tenant gets a separate cached client
- Improvement path: Consider shared connection pool with RLS context switching

**In-Memory Cache Without Eviction:**
- Problem: Caches grow unbounded in long-running processes
- Files:
  - `src/api/admin_knowledge_routes.py` lines 39-74 - `_knowledge_cache`
  - `src/services/auth_service.py` lines 23-25 - `_user_cache`
  - `config/loader.py` - `_config_cache` (likely)
- Cause: No max size or LRU eviction
- Improvement path: Use `functools.lru_cache` with maxsize or implement cache eviction

**BigQuery Tool Fetches Large Result Sets:**
- Problem: Hotel searches can return large datasets
- Files: `src/tools/bigquery_tool.py` - 621 lines
- Cause: No result limits on some queries
- Improvement path: Add configurable LIMIT to all BigQuery queries; implement pagination

## Fragile Areas

**Email Webhook Tenant Detection:**
- Files: `src/webhooks/email_webhook.py` lines 47-113
- Why fragile: Multiple fallback strategies for tenant detection can fail silently
- Safe modification: Add comprehensive logging; return explicit "tenant not found" errors
- Test coverage: No dedicated test files found in project

**Configuration Loading:**
- Files: `config/loader.py`, `config/schema.json`
- Why fragile: Environment variable substitution regex at line 70 may miss edge cases
- Safe modification: Add unit tests for env var patterns; validate schema on startup
- Test coverage: No tests found

**Multi-Tenant Context Propagation:**
- Files: `src/middleware/auth_middleware.py`, `src/tools/supabase_tool.py`
- Why fragile: Tenant context passed via X-Client-ID header and stored in request.state
- Safe modification: Verify tenant context at service layer, not just middleware
- Test coverage: No integration tests for cross-tenant isolation

## Scaling Limits

**In-Memory Rate Limiting:**
- Current capacity: Single-server only
- Limit: Rate limits reset if server restarts; not shared across instances
- Scaling path: Enable Redis backend (code exists at `src/middleware/rate_limiter.py` lines 90-124)

**FAISS Index in Memory:**
- Current capacity: Loads entire index into RAM
- Limit: Large knowledge bases will exhaust memory
- Scaling path: Implement FAISS index sharding or use managed vector database

**Client YAML Files:**
- Current capacity: 52 tenants currently
- Limit: File system operations become slow with thousands of tenants
- Scaling path: Complete migration to database-only tenant storage

## Dependencies at Risk

**WeasyPrint for PDF Generation:**
- Risk: Complex native dependencies (Cairo, Pango, GDK-PixBuf)
- Impact: PDF generation fails on systems without proper native libs
- Migration plan: Fallback to ReportLab (already partially implemented in `src/utils/pdf_generator.py`)

**SendGrid Dependency:**
- Risk: Tight coupling to SendGrid for email
- Impact: No fallback if SendGrid has outages
- Migration plan: Abstract email sender interface; add secondary provider

**Supabase as Primary Database:**
- Risk: Single-vendor dependency for auth + database
- Impact: Migration would require significant refactoring
- Migration plan: Use ORM layer (SQLAlchemy) for portability; abstract auth service

## Missing Critical Features

**No Test Suite:**
- Problem: No `tests/` directory found; no unit or integration tests
- Blocks: Safe refactoring; CI/CD pipeline; regression detection
- Files: Project root - no `tests/`, `test_*.py`, or `*_test.py` files

**No API Rate Limit Visibility:**
- Problem: Users can't see their current rate limit usage
- Blocks: Self-service usage monitoring
- Files: `src/middleware/rate_limiter.py` has `/api/v1/usage/limits` endpoint but not documented

**No Audit Logging:**
- Problem: No trail of who made what changes when
- Blocks: Compliance requirements; debugging production issues
- Files: No audit log service found

**No Backup/Restore for Tenant Data:**
- Problem: No mechanism to backup or restore individual tenant data
- Blocks: Disaster recovery; tenant data portability

## Test Coverage Gaps

**Backend Python Code (0% Coverage):**
- What's not tested: All 41 Python files in `src/` directory
- Files: `src/api/*.py`, `src/services/*.py`, `src/tools/*.py`, `src/middleware/*.py`
- Risk: Any change may break existing functionality without warning
- Priority: High - add tests for auth, CRM service, and core API routes first

**Frontend React Components (Unknown Coverage):**
- What's not tested: No `*.test.jsx` files found in `frontend/tenant-dashboard/src/`
- Files: `frontend/tenant-dashboard/src/pages/*.jsx`, `frontend/tenant-dashboard/src/context/*.jsx`
- Risk: UI regressions go unnoticed
- Priority: Medium - add tests for critical flows (Login, Dashboard, Quotes)

**Database Migrations:**
- What's not tested: SQL migrations not validated against schema
- Files: `database/migrations/*.sql`
- Risk: Migrations may fail in production or cause data loss
- Priority: Medium - add migration tests with test database

---

*Concerns audit: 2026-01-16*
