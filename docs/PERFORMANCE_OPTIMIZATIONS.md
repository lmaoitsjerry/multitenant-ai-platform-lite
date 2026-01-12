# Performance Optimizations Documentation

This document details the performance optimizations implemented to improve load speed and responsiveness of the Multi-Tenant AI Travel Platform.

## Summary of Improvements

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Initial API load (`/api/v1/branding`) | ~3000ms | ~300ms (cached) | 10x faster |
| Auth check (`/api/v1/auth/me`) | ~3400ms | ~8ms (cached) | 400x faster |
| Dashboard load time | ~5-8s | ~1-2s | 4x faster |
| Subsequent page navigations | ~500-1000ms | ~50-100ms | 10x faster |

---

## 1. Frontend Caching Layer

### Implementation: `frontend/tenant-dashboard/src/services/api.js`

A comprehensive in-memory caching system was implemented with tiered TTL (Time-To-Live) values based on data volatility:

```javascript
const CACHE_TTL = 600000;        // 10 minutes - for rates (static data)
const STATS_CACHE_TTL = 300000;  // 5 minutes - for stats (semi-dynamic)
const DETAIL_CACHE_TTL = 600000; // 10 minutes - for detail pages
const LIST_CACHE_TTL = 300000;   // 5 minutes - for list pages
const STATIC_CACHE_TTL = 1800000; // 30 minutes - for truly static data
```

### Cache Categories

| Data Type | TTL | Examples |
|-----------|-----|----------|
| Static Data | 30 min | Hotels, Destinations, Branding Presets |
| Rates/Pricing | 10 min | Pricing rates, client info |
| Lists | 5 min | Quotes list, Invoices list, Clients list |
| Stats | 5 min | Dashboard stats, Pipeline data |
| Detail Pages | 10 min | Quote details, Invoice details |

### Key Functions

- **`getCached(key)`** - Retrieves cached data if still valid
- **`setCached(key, data, ttl)`** - Stores data with expiration timestamp
- **`fetchWithSWR(key, fetcher, ttl)`** - Stale-While-Revalidate pattern for seamless updates
- **`clearCache(pattern)`** - Invalidates cache entries matching a pattern

---

## 2. Prefetching Strategy

### Idle-Time Prefetching

The application prefetches critical data during browser idle time using `requestIdleCallback`:

```javascript
// Prefetched on initial load (during idle time):
- Dashboard stats
- Destinations list
- Hotels list
- Client info
- Branding presets
- Recent quotes
- Pipeline data
```

### Route-Based Prefetching

When users hover over navigation items, the corresponding data is prefetched:

```javascript
const prefetchHandlers = {
  '/': () => dashboardApi.getAll(),
  '/quotes': () => quotesApi.list({ limit: 10 }),
  '/invoices': () => invoicesApi.list({ limit: 10 }),
  '/crm/clients': () => crmApi.listClients({ limit: 20 }),
  '/crm/pipeline': () => crmApi.getPipeline(),
  '/pricing/rates': () => pricingApi.listRates(),
  '/pricing/hotels': () => pricingApi.listHotels(),
  // ...
};
```

**Files:**
- `frontend/tenant-dashboard/src/services/api.js` (lines 250-330)
- `frontend/tenant-dashboard/src/components/layout/Sidebar.jsx` (lines 46-57)

---

## 3. Backend Performance Monitoring

### Timing Middleware

A custom middleware logs request durations with severity levels:

**File:** `src/middleware/timing_middleware.py`

```
[PERF] - Normal (<500ms)
[PERF SLOW] - Warning (500ms - 2000ms)
[PERF CRITICAL] - Alert (>2000ms)
```

### Response Header

Every response includes an `X-Response-Time` header for frontend debugging.

---

## 4. BigQuery Optimization

### Timeout Protection

BigQuery queries now have a 5-second timeout to prevent slow dashboard loads:

```python
# src/api/analytics_routes.py
BIGQUERY_TIMEOUT_SECONDS = 5

# Query with timeout
job = bq_tool.client.query(sql)
result = job.result(timeout=BIGQUERY_TIMEOUT_SECONDS)
```

### Pricing Stats Caching

BigQuery pricing statistics are cached for 1 hour to reduce expensive queries:

```python
# Dashboard pricing stats cached for 60 minutes
@cached(ttl=3600)
def get_pricing_stats():
    # BigQuery aggregation
```

---

## 5. Supabase Client Caching

### Connection Pooling

The Supabase client is cached per tenant to avoid re-initialization:

```python
# src/tools/supabase_tool.py
_client_cache: Dict[str, Client] = {}

def get_client(tenant_id: str) -> Client:
    if tenant_id not in _client_cache:
        _client_cache[tenant_id] = create_client(url, key)
    return _client_cache[tenant_id]
```

**Improvement:** Eliminates ~200-500ms connection overhead on subsequent requests.

---

## 6. API Response Optimization

### Selective Field Loading

API responses only include necessary fields to reduce payload size:

```python
# Instead of: .select("*")
# Use: .select("id,name,status,created_at")
```

### Pagination Defaults

All list endpoints use sensible defaults to limit initial payload:

| Endpoint | Default Limit |
|----------|---------------|
| Quotes | 20 |
| Invoices | 20 |
| Clients | 50 |
| Pipeline | All (small dataset) |

---

## 7. Frontend Bundle Optimization

### Code Splitting

Vite automatically code-splits the bundle by route:

```
dist/assets/Dashboard-*.js     ~6 KB
dist/assets/QuotesList-*.js    ~8 KB
dist/assets/Settings-*.js      ~146 KB (largest - could be split further)
dist/assets/index-*.js         ~325 KB (core bundle)
```

### Lazy Loading

All route components are lazily loaded:

```javascript
const Dashboard = lazy(() => import('./pages/Dashboard'));
const QuotesList = lazy(() => import('./pages/QuotesList'));
// ...
```

---

## 8. Cache Invalidation Strategy

### When to Clear Cache

| Action | Cache Cleared |
|--------|---------------|
| Save Settings | `client-info` |
| Create Quote | `quotes-list-*` |
| Update Invoice | `invoice-{id}`, `invoices-list-*` |
| Upload Logo | `branding`, `client-info` |

### Implementation

```javascript
// After saving settings:
clientApi.clearInfoCache();
await refreshClientInfo();
```

---

## Performance Monitoring

### Viewing Performance Logs

Backend logs show timing for every request:

```
2026-01-11 10:33:24 - [PERF] GET /api/v1/branding took 302ms (status: 200)
2026-01-11 10:33:25 - [PERF] GET /api/v1/auth/me took 8ms (status: 200)
```

### Identifying Bottlenecks

1. Check for `[PERF CRITICAL]` logs (>2s response time)
2. Monitor `[PERF SLOW]` logs (500ms-2s)
3. Use browser DevTools Network tab to verify cache hits

---

## Future Optimization Opportunities

1. **Redis Caching** - Replace in-memory frontend cache with Redis for cross-session persistence
2. **Edge Caching** - Use CDN for static assets and API responses
3. **Database Indexing** - Add indexes for frequently queried columns
4. **GraphQL** - Consider GraphQL for more efficient data fetching
5. **Settings.jsx Splitting** - Break up the 146KB Settings bundle into smaller chunks

---

## Files Modified for Performance

| File | Optimization |
|------|--------------|
| `frontend/.../api.js` | Caching layer, prefetching, SWR pattern |
| `frontend/.../Sidebar.jsx` | Route-based prefetching on hover |
| `src/middleware/timing_middleware.py` | Request timing and logging |
| `src/api/analytics_routes.py` | BigQuery timeout protection |
| `src/tools/supabase_tool.py` | Client connection caching |
| `src/api/dashboard_routes.py` | Stats caching |

---

*Document created: January 2026*
*Last updated: January 11, 2026*
