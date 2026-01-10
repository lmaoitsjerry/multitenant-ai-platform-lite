# Performance Audit Report

## Executive Summary

Target: **All pages should load in under 1 second**

Current Issues Identified:
- **6 Critical** performance issues in backend
- **4 Medium** priority frontend issues
- **2 Security** issues (SQL injection)

---

## Backend Issues

### CRITICAL: N+1 Query in Leaderboard

**File:** `src/api/analytics_routes.py:936-954`

**Problem:** For each user, a separate query fetches their invoices:
```python
for user in users:
    invoices_result = supabase.client.table('invoices')\
        .select("id, total_amount")\
        .eq('consultant_id', user['id'])\
        .execute()  # N+1 queries!
```

**Impact:** 50 users = 50 database queries = ~5 second response time

**Fix:** Use batch query with GROUP BY:
```python
# Single query for all consultants
result = supabase.client.table('invoices')\
    .select("consultant_id, total_amount.sum()")\
    .eq('tenant_id', config.client_id)\
    .eq('status', 'paid')\
    .gte('created_at', start_of_month.isoformat())\
    .group_by('consultant_id')\
    .execute()
```

---

### CRITICAL: Double Data Fetch in Tickets

**File:** `src/api/inbound_routes.py:79-82`

**Problem:** Fetches tickets twice - once for display, once for counting:
```python
tickets = supabase.list_tickets(limit=limit)
all_tickets = supabase.list_tickets(limit=1000)  # Just for stats!
```

**Fix:** Use Supabase count:
```python
tickets = supabase.list_tickets(limit=limit)
count_result = supabase.client.table('support_tickets')\
    .select('*', count='exact')\
    .eq('tenant_id', tenant_id)\
    .execute()
total_count = count_result.count
```

---

### HIGH: SELECT * Over-fetching

**Files:** Multiple locations throughout `src/api/` and `src/tools/`

**Problem:** Queries fetch all columns when only specific ones needed:
```python
.select("*")  # Fetches ALL columns including large JSON blobs
```

**Fix:** Specify only needed columns:
```python
.select("id, customer_name, destination, total_price, status, created_at")
```

---

### HIGH: Missing Query Limits

**Files:** `src/api/analytics_routes.py`, `src/api/leaderboard_routes.py`

**Problem:** Analytics queries can return unlimited rows:
```python
quotes_result = supabase.client.table('quotes')\
    .select("*")\
    .eq('tenant_id', config.client_id)\
    .execute()  # Could return 10,000+ rows!
```

**Fix:** Always add limits and pagination:
```python
.limit(1000)  # Reasonable maximum
# Or use pagination with offset
```

---

### CRITICAL: SQL Injection in BigQuery

**File:** `src/tools/bigquery_tool.py:109, 411`

**Problem:** Unparameterized strings in queries:
```python
query += f" AND r.meal_plan = '{meal_plan_pref}'"  # INJECTION RISK!
```

**Fix:** Use query parameters:
```python
job_config = bigquery.QueryJobConfig(
    query_parameters=[
        bigquery.ScalarQueryParameter("meal_plan", "STRING", meal_plan_pref)
    ]
)
query += " AND r.meal_plan = @meal_plan"
```

---

### MEDIUM: In-Memory Aggregation

**File:** `src/api/analytics_routes.py:382-448`

**Problem:** Aggregation done in Python instead of database:
```python
for q in quotes:
    status = q.get('status', 'unknown')
    status_counts[status] = status_counts.get(status, 0) + 1
```

**Fix:** Use database GROUP BY:
```sql
SELECT status, COUNT(*) as count
FROM quotes
WHERE tenant_id = $1
GROUP BY status
```

---

## Database Indexes

The existing `database/performance_indexes.sql` is comprehensive. Ensure it's been run on all tenant databases.

**Additional Recommended Indexes:**

```sql
-- For leaderboard month queries
CREATE INDEX IF NOT EXISTS idx_invoices_consultant_paid_month
ON invoices(tenant_id, consultant_id, created_at)
WHERE status = 'paid';

-- For analytics date range queries
CREATE INDEX IF NOT EXISTS idx_quotes_tenant_created_range
ON quotes(tenant_id, created_at DESC)
INCLUDE (status, destination, total_price);

-- For CRM pipeline view
CREATE INDEX IF NOT EXISTS idx_crm_clients_pipeline_view
ON crm_clients(tenant_id, pipeline_stage, updated_at DESC);
```

---

## Frontend Issues

### 1. Missing Memoization

**Files:** `Analytics.jsx`, `Pipeline.jsx`

**Problem:** Components re-render unnecessarily on every state change.

**Fix:** Add React.memo and useMemo:
```jsx
const StatCard = memo(function StatCard({ title, value, ...props }) {
  return (/* ... */);
});

// Memoize expensive calculations
const chartData = useMemo(() =>
  processChartData(rawData), [rawData]
);
```

### 2. Redundant API Calls

**Problem:** Some pages make duplicate API calls.

**Fix:** Already implemented caching in `api.js` with `fetchWithSWR`. Ensure all endpoints use it.

### 3. Large Component Re-renders

**File:** `Settings.jsx` (600+ lines)

**Problem:** Entire Settings page re-renders when any field changes.

**Fix:** Split into smaller components with their own state:
```jsx
const ProfileSection = memo(function ProfileSection() {
  const [profile, setProfile] = useState({});
  // Local state prevents parent re-renders
});
```

### 4. Bundle Size

**Issue:** Heroicons imported individually creates efficient tree-shaking, but verify with bundle analyzer.

**Action:** Run `npm run build -- --analyze` to check bundle size.

---

## Recommended Caching Strategy

### Backend Caching

```python
# Add Redis or in-memory cache for hot paths
from functools import lru_cache
from datetime import timedelta

@lru_cache(maxsize=100)
def get_dashboard_stats(tenant_id: str, cache_key: str):
    # Cache for 5 minutes
    pass

# Or use Redis for distributed caching
import redis
cache = redis.Redis()

def get_cached_stats(tenant_id: str):
    key = f"stats:{tenant_id}"
    cached = cache.get(key)
    if cached:
        return json.loads(cached)

    stats = calculate_stats(tenant_id)
    cache.setex(key, timedelta(minutes=5), json.dumps(stats))
    return stats
```

### Frontend Caching (Already Implemented)

Current `api.js` TTLs:
- `CACHE_TTL`: 10 minutes (rates)
- `STATS_CACHE_TTL`: 5 minutes (stats)
- `STATIC_CACHE_TTL`: 30 minutes (hotels/destinations)

These are appropriate. The issue is backend response times, not frontend caching.

---

## Action Items by Priority

### Immediate (Day 1)
1. ✅ Run `performance_indexes.sql` on all tenant databases
2. 🔴 Fix SQL injection in BigQuery tool
3. 🔴 Fix N+1 query in leaderboard endpoint

### Short Term (Week 1)
4. 🟠 Add limits to all analytics queries
5. 🟠 Change SELECT * to specific columns
6. 🟠 Fix double-fetch in tickets endpoint

### Medium Term (Week 2-3)
7. 🟡 Add backend caching layer (Redis)
8. 🟡 Split large frontend components
9. 🟡 Add React.memo to heavy components

---

## SQL Fixes - Ready to Apply

### Fix 1: Add Missing Performance Indexes

```sql
-- Run in Supabase SQL Editor
-- Additional indexes beyond the existing file

-- For leaderboard performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invoices_leaderboard
ON invoices(tenant_id, consultant_id, status, created_at)
WHERE status = 'paid';

-- For analytics date range queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_quotes_analytics
ON quotes(tenant_id, created_at DESC, status);

-- For faster count queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_support_tickets_count
ON support_tickets(tenant_id, status);

-- Partial index for active clients only
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_crm_clients_active
ON crm_clients(tenant_id, pipeline_stage, updated_at DESC)
WHERE pipeline_stage NOT IN ('LOST', 'TRAVELLED');
```

### Fix 2: Database Statistics Update

```sql
-- Update statistics for query planner
ANALYZE quotes;
ANALYZE invoices;
ANALYZE crm_clients;
ANALYZE support_tickets;
ANALYZE organization_users;
```

---

## Monitoring Recommendations

1. **Add response time logging:**
```python
import time
from fastapi import Request

@app.middleware("http")
async def log_response_time(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    if duration > 1.0:  # Log slow requests
        logger.warning(f"Slow request: {request.url.path} took {duration:.2f}s")
    return response
```

2. **Set up Supabase query monitoring:**
   - Enable `pg_stat_statements` extension
   - Monitor slow queries in Supabase dashboard

3. **Frontend performance monitoring:**
   - Add Web Vitals tracking
   - Set up alerting for LCP > 2.5s
