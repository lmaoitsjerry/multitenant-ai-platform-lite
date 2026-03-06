# Launch Readiness Audit — 1,000-3,000 Concurrent Users

**Platform:** Zorah ITC / Holiday Today
**Date:** 2026-03-06
**Auditor:** Claude (automated codebase analysis)

---

## Executive Summary

**Overall Score: 7.2/10 — Conditionally Ready**

The platform has strong security foundations (8.7/10), good observability infrastructure (8.5/10), and solid test coverage (109 test files). However, **scalability is the primary risk** (5.8/10) — in-memory caches that break across multiple Cloud Run instances, single Uvicorn worker, no database connection pooling, and a thread pool bottleneck will cause issues under concurrent load.

**Critical blockers for launch:** 3 items
**Important fixes:** 8 items
**Nice-to-have:** 6 items
**Estimated total effort:** ~3-4 weeks

---

## A. Scalability

### Standard for 1-3K Users
- Auto-scaling to 20+ instances with Cloud Run concurrency of 80-250 per instance
- Database connection pooling (pgBouncer or Supabase pooler mode)
- All in-process caches moved to shared store (Redis)
- Stateless architecture (any instance can serve any request)
- Multiple Uvicorn workers per instance (match CPU count)

### Current State

**Cloud Run Configuration** (`deploy.yml:103-109`):
| Setting | Value | Verdict |
|---------|-------|---------|
| Memory | 2 Gi | OK |
| CPU | 2 | OK |
| Min instances | 0 | **Cold start risk** |
| Max instances | 10 | OK for 1-3K |
| Timeout | 300s | OK |
| Concurrency | Default (80) | OK |

**Uvicorn** (`Dockerfile:48`):
```
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT}
```
Single worker — only using 1 of 2 allocated CPUs.

**Database Connection Pooling**: None found. Supabase client is cached per `(URL, key)` in `src/tools/supabase_tool.py:_supabase_client_cache` and `src/services/auth_service.py:_auth_client_cache`, but no `pool_size` or `max_connections` configuration. Supabase sync SDK wrapped in `ThreadPoolExecutor(max_workers=8)`.

**In-Memory Caches** (break with multiple instances):

| Cache | File | TTL | Impact |
|-------|------|-----|--------|
| Flight search | `travel_services_routes.py:38` | 5 min | Different instances return different results |
| Dashboard analytics | `analytics_routes.py` | 1 min | Stale data across instances |
| Admin analytics | `admin_analytics_routes.py:32` | 1 min | Same |
| Admin knowledge | `admin_knowledge_routes.py:43` | 2 min | Same |
| Pricing stats | `analytics_routes.py` | varies | Same |
| Tenant status | `auth_middleware.py` | 5 min | Suspension delay |
| User cache | `auth_service.py` | 60s | Profile changes missed |
| Email webhook | `email_webhook.py` | varies | Stale tenant config |

**Rate Limiter** (`rate_limiter.py:90-107`): Supports Redis, falls back to in-memory. Good design.

### Gaps
1. **CRITICAL**: 8+ in-memory caches → inconsistent data across instances
2. **CRITICAL**: Single Uvicorn worker wastes 50% of CPU allocation
3. **HIGH**: No DB connection pooling → Supabase connection exhaustion at scale
4. **HIGH**: `min-instances=0` → cold start latency (5-15s) for first users
5. **MEDIUM**: ThreadPoolExecutor limited to 8 workers → bottleneck under load

### Priority Fixes

| # | Fix | Effort | Priority |
|---|-----|--------|----------|
| 1 | Add `--workers 2` to Uvicorn CMD in Dockerfile | 5 min | **CRITICAL** |
| 2 | Set `min-instances=1` in deploy.yml | 5 min | **CRITICAL** |
| 3 | Deploy Redis (Cloud Memorystore) and move all caches to Redis | 2-3 days | **CRITICAL** |
| 4 | Use Supabase connection pooler URL (port 6543) instead of direct (port 5432) | 1 hour | **HIGH** |
| 5 | Increase ThreadPoolExecutor to `max_workers=16` | 5 min | **HIGH** |
| 6 | Consider `max-instances=25` for headroom | 5 min | MEDIUM |

### Risk if Not Fixed
At 1,000+ concurrent users with 10 instances: each instance has independent caches — same user gets different flight results on refresh. Supabase free tier (60 connections) or Pro (200) gets exhausted by 10 instances × ~20 connections each. Single worker can't handle bursts beyond ~100 concurrent requests per instance.

---

## B. Performance

### Standard for 1-3K Users
- P95 API response time < 500ms for CRUD endpoints
- Search/aggregation endpoints < 3s
- Frontend initial load < 3s (LCP)
- Database queries indexed for common access patterns
- Caching for expensive/frequently-accessed data
- No N+1 query patterns

### Current State

**Slow Endpoints Identified:**

| Endpoint | Response Time | Root Cause | File |
|----------|---------------|-----------|------|
| `POST /api/v1/rates/hotels/search` | 30-60s | Multi-provider aggregation + per-hotel currency conversion in loop | `rates_routes.py:215` |
| `POST /api/v1/rates/flights/search` | 5-10s | RTTC aggregation + response transformation | `travel_services_routes.py:275` |
| `GET /api/v1/dashboard/all` | 2-5s | 6 parallel Supabase queries via asyncio.gather | `analytics_routes.py:1003` |
| `POST /api/v1/knowledge/*` | up to 120s | Document indexing with chunking | `knowledge_routes.py:30` |

**Currency Conversion Bottleneck** (`rates_routes.py:126-179`):
```python
for hotel in hotels:
    hotel["price"] = currency_svc.convert(...)  # Called per hotel × per rate
```
With 50 hotels × 2-4 rates each = 100-200 individual conversion calls per search.

**Admin Analytics** (`admin_analytics_routes.py:191-207`):
```python
# Fetches ALL invoices then filters in Python
result = client.table("invoices").select("*").execute()
paid = [i for i in result.data if i.get("status") == "paid"]
```
Should use `.eq("status", "paid")` in the query.

**Frontend Bundle**: Excellent. 1.5 MB total JS across 59 code-split chunks. All 22+ routes use `lazy()` imports. Largest chunk is 22 KB. CSS is 90 KB (single file).

**Database Indexes** (`database/performance_indexes.sql`): 24 indexes covering common queries. Composite indexes on `(tenant_id, created_at)`, partial indexes on `status = 'paid'`. Full-text search indexes commented out (lines 90-94).

**Good Patterns Found:**
- `asyncio.gather()` for parallel DB queries in dashboard
- Flight search deduplication with asyncio.Lock (single-flight pattern)
- Dashboard caching with 30s TTL
- `CacheWarmer` component in frontend pre-fetches dashboard data

### Gaps
1. **HIGH**: Per-hotel currency conversion loop (100-200 API calls per search)
2. **HIGH**: Admin analytics filters in Python instead of SQL
3. **MEDIUM**: Full-text search indexes disabled (linear scans for knowledge/client search)
4. **MEDIUM**: No Vite `manualChunks` config (vendor libs could be split better)
5. **LOW**: Cache dicts have no cleanup — unbounded memory growth

### Priority Fixes

| # | Fix | Effort | Priority |
|---|-----|--------|----------|
| 1 | Batch currency conversion (single API call for all rates) | 1 day | **HIGH** |
| 2 | Add `.eq("status", "paid")` to admin invoice queries | 30 min | **HIGH** |
| 3 | Enable pg_trgm + full-text search indexes | 2 hours | **MEDIUM** |
| 4 | Add max-size cleanup to manual cache dicts | 2 hours | **MEDIUM** |
| 5 | Add Vite manualChunks for vendor splitting | 1 hour | LOW |

### Risk if Not Fixed
Hotel search already takes 30-60s. With 100 concurrent hotel searches, the currency conversion service becomes the bottleneck (10,000-20,000 API calls). Admin analytics loading all invoices into memory will OOM with growth.

---

## C. Reliability

### Standard for 1-3K Users
- Global exception handlers (no unhandled crashes)
- Health checks for load balancer and readiness
- Retry logic with exponential backoff for all external APIs
- Circuit breakers for cascading failure prevention
- Graceful degradation when dependencies are down
- Request timeouts on all external calls

### Current State

**Error Handling** (`main.py:360-372`): Global exception handler catches all unhandled exceptions, returns generic 500 (no stack trace leakage), logs full details.

**Health Checks** (`main.py:209-297`):
| Endpoint | Checks | Status Codes |
|----------|--------|-------------|
| `/health` | App alive | 200 |
| `/health/live` | Liveness probe | 200 |
| `/health/ready` | Supabase + BigQuery + circuit breakers | 200/503 |

**Circuit Breakers** (`src/utils/circuit_breaker.py`):
| Service | Failure Threshold | Recovery Timeout |
|---------|-------------------|-----------------|
| SendGrid | 3 | 60s |
| Supabase | 5 | 30s |
| RAG (Travel Platform) | 5 | 60s |
| Rates Engine | 3 | 120s |
| HotelBeds | 3 | 60s |

All thread-safe with `threading.Lock()`. Status exposed via `/health/ready`.

**Retry Logic** (`src/utils/retry_utils.py`):
- `@retry_on_network_error(max_attempts=3, min_wait=2, max_wait=10)` decorator
- Exponential backoff, retries only on connection/timeout errors (not 4xx)
- Applied to: Supabase queries, SendGrid emails, travel platform calls

**Timeout Configuration**:
| Service | Timeout | Concern |
|---------|---------|---------|
| Hotel search | 120s | Necessary (multi-provider) |
| HotelBeds | 60s | OK |
| Knowledge indexing | 120s | OK |
| Website proxy | 30s | OK |
| Currency conversion | 10s | OK |
| **Email sending** | **Not set** | **Risk: hangs indefinitely** |

### Gaps
1. **HIGH**: Some HTTP calls lack explicit timeout parameters (email sending)
2. **MEDIUM**: Background tasks (FastAPI `BackgroundTasks`) are lost if instance restarts
3. **LOW**: Circuit breaker state is per-instance (not shared)

### Priority Fixes

| # | Fix | Effort | Priority |
|---|-----|--------|----------|
| 1 | Add `timeout=10` to all `requests.post()` calls in email_sender.py | 30 min | **HIGH** |
| 2 | Audit all httpx/requests calls for explicit timeout | 2 hours | **HIGH** |
| 3 | Add dead-letter queue for failed background tasks | 2 days | MEDIUM |

### Risk if Not Fixed
A hung SendGrid connection could tie up a worker thread indefinitely. With only 8 threads in the pool, 8 simultaneous email failures could freeze the entire instance.

---

## D. Security

### Standard for 1-3K Users
- JWT auth on all protected endpoints
- CORS locked to explicit origins in production
- Input validation (Pydantic) on all endpoints
- Rate limiting (per-tenant, per-endpoint)
- No hardcoded secrets
- Security headers (CSP, HSTS, X-Frame-Options)
- SQL injection prevention

### Current State

**Overall Security Score: 8.7/10 — Strong**

**Authentication** (`src/middleware/auth_middleware.py`):
- JWT tokens verified via Supabase Auth with `SUPABASE_JWT_SECRET`
- 143 protected endpoints use `Depends(get_current_user)`
- Tenant spoofing detection with IP-based rate limiting (3 attempts → 30-min block)
- Admin routes protected by `verify_admin_token()` with `hmac.compare_digest()` (timing-attack safe)
- 43 public paths defined (health checks, auth, webhooks, helpdesk)

**CORS** (`main.py:139-201`):
- Production: `CORS_ORIGINS` env var (explicit list via GitHub Secrets)
- Development fallback: `*.zorahai.com`, `*.holidaytoday.co.za` (wildcard subdomains)

**Input Validation**: 297 Pydantic model occurrences across 54 files. All POST/PUT endpoints validated. Field constraints: min/max length, patterns, enums, EmailStr.

**Rate Limiting** (`src/middleware/rate_limiter.py`):
| Endpoint | Limit | Window |
|----------|-------|--------|
| Quote generation | 200 | 1 hour |
| Quote chat | 1,000 | 1 hour |
| Helpdesk chat | 1,200 | 1 hour |
| Email webhook | 2,000 | 1 min |
| Daily API total | 100,000 | 24 hours |

**SQL Injection**: Zero raw SQL strings found. All queries use Supabase ORM (parameterized).

**Secrets**: All loaded from `os.getenv()`. No hardcoded credentials in source (only test fixtures with "test-*" prefixes).

**Security Headers** (`src/middleware/security_headers.py`):
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- Content-Security-Policy: `default-src 'none'; frame-ancestors 'none'`
- Strict-Transport-Security: `max-age=31536000` (production only)
- Permissions-Policy: disables camera, microphone, geolocation

**PII Audit** (`src/middleware/pii_audit_middleware.py`): Tracks access to sensitive data. GDPR/POPIA compliant.

**Tenant Isolation**: Row Level Security (RLS) enabled on all core tables (`database/migrations/009_core_table_rls.sql`). Query-level `tenant_id` filtering. Auth middleware validates token matches tenant.

### Gaps
1. **MEDIUM**: CORS fallback uses wildcard subdomains (development config)
2. **LOW**: No IP whitelisting for admin endpoints
3. **LOW**: No secret rotation mechanism
4. **LOW**: No CSP nonce for inline scripts (if any)

### Priority Fixes

| # | Fix | Effort | Priority |
|---|-----|--------|----------|
| 1 | Verify `CORS_ORIGINS` GitHub Secret has explicit production domains | 15 min | **MEDIUM** |
| 2 | Add admin IP whitelisting (Cloud Run IAM or middleware) | 2 hours | LOW |
| 3 | Document secret rotation schedule | 1 hour | LOW |

### Risk if Not Fixed
Wildcard CORS only matters if `CORS_ORIGINS` env var is not set in production (fallback). Since deploy.yml sets `CORS_ORIGINS=${{ secrets.CORS_ORIGINS }}`, this is **low risk** if the secret is configured correctly. Verify the secret value.

---

## E. Observability

### Standard for 1-3K Users
- Structured JSON logging with request IDs and tenant context
- Prometheus metrics (request count, duration, error rate)
- Error tracking (Sentry or equivalent)
- Performance monitoring (P95 latency dashboards)
- Alerting on error spikes, latency, and service degradation
- Uptime monitoring on health endpoints

### Current State

**Structured Logging** (`src/utils/structured_logger.py`, 281 lines):
- JSON format with ISO 8601 timestamps
- Request correlation IDs via `ContextVar` (async-safe)
- Tenant ID context automatically injected
- OpenTelemetry trace context integration (optional)
- Configurable levels: `LOG_LEVEL` env var

**Prometheus Metrics** (`src/api/metrics_routes.py` + `src/middleware/timing_middleware.py`):
- `http_requests_total` — Counter [method, path, status]
- `http_request_duration_seconds` — Histogram with 10 buckets
- `http_errors_total` — Counter for 4xx/5xx
- Path normalization (UUIDs → `{id}`) to prevent metric explosion
- `GET /metrics` endpoint exposed
- `X-Response-Time` header on all responses
- Slow request logging: WARNING at 500ms, CRITICAL at 2000ms

**Error Tracking**: Sentry DSN mentioned in `PRODUCTION_READINESS.md` as optional env var, but **NOT integrated in application code**. No `sentry_sdk` import found.

**Alerting**: Incident response runbook exists (`docs/runbooks/incident-response.md`, 172 lines) with severity levels (SEV1-SEV4). Alert rules referenced (`docs/alerting-rules.yaml`) but file does not exist.

### Gaps
1. **HIGH**: Sentry not integrated — errors only in Cloud Run logs
2. **HIGH**: No alerting rules configured (Alertmanager/Cloud Monitoring)
3. **HIGH**: No uptime monitoring service configured
4. **MEDIUM**: No performance dashboards (Grafana) consuming Prometheus metrics

### Priority Fixes

| # | Fix | Effort | Priority |
|---|-----|--------|----------|
| 1 | Integrate Sentry SDK (`pip install sentry-sdk[fastapi]`, add to main.py) | 2 hours | **HIGH** |
| 2 | Set up Cloud Monitoring alerts (error rate, latency, instance count) | 4 hours | **HIGH** |
| 3 | Configure uptime check on `/health/ready` (Cloud Monitoring or UptimeRobot) | 1 hour | **HIGH** |
| 4 | Deploy Grafana + Prometheus for metric dashboards | 2 days | MEDIUM |

### Risk if Not Fixed
Without Sentry, errors are only visible in Cloud Run logs — no aggregation, no notification, no trend analysis. Without alerting, you won't know when the platform is degraded until users complain. At 1-3K users, you need proactive monitoring, not reactive firefighting.

---

## F. Data Integrity

### Standard for 1-3K Users
- Database constraints (CHECK, FK, UNIQUE, NOT NULL)
- Row Level Security for tenant isolation
- Transaction safety for multi-step operations
- Point-in-time recovery (PITR) backups
- Migration strategy for zero-downtime schema changes

### Current State

**Database Constraints** (21 migrations, 2,755 lines in `database/migrations/`):
- CHECK constraints on: roles, consent types, legal basis, DSAR types, status workflows
- FOREIGN KEY: `auth.users` → `organization_users` (CASCADE), consent records (SET NULL)
- UNIQUE: `(tenant_id, email)` on users, invitations; `(tenant_id, request_number)` on DSARs
- NOT NULL: tenant_id, email, name, role, created_at on all core tables

**Row Level Security** (`database/migrations/009_core_table_rls.sql`, 369 lines):
- Enabled on: quotes, invoices, invoice_travelers, clients, activities, call_records, outbound_call_queue, inbound_tickets, helpdesk_sessions, knowledge_documents
- Pattern: service role gets full access; authenticated users filtered by `tenant_id` membership
- Verification queries documented in migration comments

**Transaction Safety**:
- No explicit `.begin()` / `ROLLBACK` patterns found in Python code
- Supabase SDK handles statement atomicity
- Database triggers (`update_*_updated_at`, `generate_dsar_number`) run atomically
- Multi-step operations (e.g., quote generation → email → invoice) are not wrapped in transactions

**Backup Strategy** (`docs/disaster-recovery-plan.md`, 126 lines):
- Supabase PITR: < 15 min RPO, 30-day retention (Pro plan)
- Manual snapshots before major deployments
- Git repo + Google Artifact Registry for code/images
- GCS versioned buckets with 90-day retention

**Performance Indexes** (`database/performance_indexes.sql`):
- 24 indexes covering common access patterns
- Composite indexes: `(tenant_id, created_at DESC)`, `(tenant_id, status)`
- Partial index: `WHERE status = 'paid'`
- Full-text search indexes commented out (not enabled)

### Gaps
1. **MEDIUM**: No explicit transactions for multi-step operations (quote + email + invoice)
2. **MEDIUM**: Missing some app-level tables from RLS (if any exist outside migrations)
3. **LOW**: DR plan not tested (no recorded drill results)

### Priority Fixes

| # | Fix | Effort | Priority |
|---|-----|--------|----------|
| 1 | Add Supabase RPC functions for multi-step operations that need atomicity | 2 days | **MEDIUM** |
| 2 | Enable full-text search indexes (uncomment pg_trgm in migration) | 1 hour | **MEDIUM** |
| 3 | Run DR drill and document results | 4 hours | **MEDIUM** |

### Risk if Not Fixed
If quote creation succeeds but email sending fails mid-operation, there's no rollback. The customer sees a "success" but never receives the email. At scale, these partial failures will accumulate. However, the retry/circuit-breaker patterns mitigate this significantly.

---

## G. Deployment

### Standard for 1-3K Users
- Automated CI/CD with tests gating deployment
- Security scanning (SAST, dependency audit, container scan)
- Rolling deployments with health check verification
- Rollback strategy (instant revision switch)
- Environment parity (staging mirrors production)
- Feature flags for gradual rollout

### Current State

**CI Pipeline** (`.github/workflows/ci.yml`, 120 lines):
1. TruffleHog secret scanning
2. Python 3.11 setup + dependency install
3. Flake8 linting (max-complexity=10)
4. Pytest with 57% coverage minimum
5. Bandit SAST security analysis
6. pip-audit dependency vulnerability check
7. Docker build + Trivy container scan (CRITICAL/HIGH severity fails)

**Deploy Pipeline** (`.github/workflows/deploy.yml`, 212 lines):
1. Pre-deploy: full pytest suite
2. Backend: `gcloud builds submit` → Cloud Run deploy → health check verification
3. Frontend: `npm ci && npm run build` → GCS upload with smart cache headers → CDN invalidation

**Cache Strategy for Frontend** (well-designed):
- Hashed assets: `max-age=31536000, immutable` (1 year)
- index.html: `no-cache, no-store, must-revalidate`
- Other static files: `max-age=3600` (1 hour)

**Rollback**: Cloud Run maintains previous revisions. Instant rollback via traffic splitting or `gcloud run services update-traffic`.

**Environment Parity**:
| Aspect | Dev | Production |
|--------|-----|-----------|
| Environment var | `development` | `production` |
| API docs | Enabled | Disabled |
| Log level | DEBUG | INFO |
| Rate limiting | In-memory | Redis |
| CORS | Localhost + wildcards | Explicit via secret |

**Feature Flags**: None. Only ad-hoc toggles: `ENABLE_TRACING`, `PII_AUDIT_ENABLED`, `JSON_LOGS`.

### Gaps
1. **MEDIUM**: No staging environment (dev → production directly)
2. **MEDIUM**: No feature flag system for gradual rollout
3. **LOW**: No smoke test suite for post-deploy verification beyond health check

### Priority Fixes

| # | Fix | Effort | Priority |
|---|-----|--------|----------|
| 1 | Create staging Cloud Run service (same config, separate Supabase project) | 1 day | **MEDIUM** |
| 2 | Add post-deploy smoke tests (critical user flows via curl/API calls) | 4 hours | **MEDIUM** |
| 3 | Implement basic feature flags (env var or DB-based) | 1 day | LOW |

### Risk if Not Fixed
Without staging, every deploy goes directly to production users. A bad deploy at peak hours affects all 1-3K users immediately. With staging, you catch issues before they reach users.

---

## Launch Checklist — Minimum Viable for 1-3K Users

### MUST DO (Blocks Launch) — ~1 week effort

- [ ] **Add `--workers 2` to Uvicorn CMD** (`Dockerfile:48`) — 5 min
- [ ] **Set `min-instances=1`** (`deploy.yml:106`) — 5 min
- [ ] **Deploy Redis** (Cloud Memorystore) and migrate all in-memory caches — 2-3 days
- [ ] **Use Supabase connection pooler URL** (port 6543 instead of 5432) — 1 hour
- [ ] **Add timeouts to all HTTP calls** (audit requests/httpx for missing `timeout=`) — 2 hours
- [ ] **Integrate Sentry** (`pip install sentry-sdk[fastapi]`) — 2 hours
- [ ] **Configure uptime monitoring** on `/health/ready` — 1 hour
- [ ] **Verify CORS_ORIGINS** GitHub Secret has explicit production domains — 15 min

### SHOULD DO (Before 2K Users) — ~1 week effort

- [ ] Set up Cloud Monitoring alerts (error rate > 5%, P95 latency > 2s, instance count)
- [ ] Batch currency conversions in hotel search (eliminate per-hotel loop)
- [ ] Fix admin analytics: add `.eq("status", "paid")` to invoice query
- [ ] Increase ThreadPoolExecutor to `max_workers=16`
- [ ] Enable pg_trgm + full-text search indexes
- [ ] Create staging environment
- [ ] Add post-deploy smoke tests
- [ ] Run disaster recovery drill

### NICE TO HAVE (Before 3K Users) — ~2 weeks effort

- [ ] Grafana + Prometheus dashboards
- [ ] Feature flag system
- [ ] Supabase RPC functions for transactional operations
- [ ] Vite manualChunks for vendor bundle splitting
- [ ] Admin endpoint IP whitelisting
- [ ] Cache cleanup / max-size limits on manual dict caches

---

## Architecture Diagram (Current)

```
                          ┌─────────────────┐
                          │   Cloud DNS      │
                          └────────┬────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
            ┌───────▼────────┐          ┌────────▼────────┐
            │  GCS Bucket    │          │  Cloud Run      │
            │  (Frontend)    │          │  (Backend)      │
            │  React SPA     │          │  FastAPI        │
            │  1.5MB JS      │          │  2CPU / 2GB     │
            │  CDN cached    │          │  0-10 instances │
            └────────────────┘          └────────┬────────┘
                                                 │
                    ┌────────────────────────────┼────────────────────────────┐
                    │                            │                            │
            ┌───────▼────────┐          ┌───────▼────────┐          ┌───────▼────────┐
            │  Supabase      │          │  BigQuery       │          │  External APIs  │
            │  PostgreSQL    │          │  (Rates/Pricing)│          │  HotelBeds     │
            │  + Auth        │          │                 │          │  RTTC          │
            │  + RLS         │          │                 │          │  SendGrid      │
            │  NO POOLING ❌ │          │                 │          │  OpenAI        │
            └────────────────┘          └─────────────────┘          └────────────────┘
```

---

## Risk Summary Matrix

| Risk | Likelihood | Impact | Mitigation | Status |
|------|-----------|--------|------------|--------|
| Instance cache inconsistency | **HIGH** (with >1 instance) | **HIGH** (wrong data shown) | Move to Redis | NOT DONE |
| Supabase connection exhaustion | **HIGH** (at scale) | **CRITICAL** (all requests fail) | Connection pooler | NOT DONE |
| Single worker CPU waste | **HIGH** (always) | **MEDIUM** (50% capacity loss) | Add workers | NOT DONE |
| Cold start latency | **MEDIUM** (after idle) | **HIGH** (15s first request) | min-instances=1 | NOT DONE |
| Error blindness | **HIGH** (no Sentry) | **HIGH** (silent failures) | Integrate Sentry | NOT DONE |
| Email timeout hang | **LOW** (depends on SendGrid) | **HIGH** (frozen worker) | Add timeout | NOT DONE |
| Hotel search bottleneck | **HIGH** (every search) | **MEDIUM** (poor UX) | Batch conversion | NOT DONE |
| No staging environment | **MEDIUM** (each deploy) | **HIGH** (prod-only testing) | Create staging | NOT DONE |
| DR untested | **LOW** (rare event) | **CRITICAL** (data loss) | Run drill | NOT DONE |

---

*This audit is based on static code analysis. Load testing with tools like k6 or Locust is recommended to validate findings under real concurrent load.*
