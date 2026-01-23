"""
Admin Analytics Routes - Platform-Wide Analytics

Endpoints for:
- Platform overview metrics
- Usage analytics over time
- Top performing tenants
- Growth metrics

These endpoints require admin authentication (X-Admin-Token header).
"""

import logging
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from config.loader import list_clients, ClientConfig
from src.api.admin_routes import verify_admin_token
from src.utils.error_handler import log_and_raise

logger = logging.getLogger(__name__)

admin_analytics_router = APIRouter(prefix="/api/v1/admin/analytics", tags=["Admin - Analytics"])


# ==================== Simple In-Memory Cache ====================

_cache = {}
CACHE_TTL_SECONDS = 60  # Cache for 1 minute


def get_cached(key: str) -> Optional[Any]:
    """Get value from cache if not expired"""
    if key in _cache:
        entry = _cache[key]
        if datetime.now() < entry['expires']:
            return entry['data']
        else:
            del _cache[key]
    return None


def set_cached(key: str, data: Any, ttl: int = CACHE_TTL_SECONDS):
    """Set value in cache with TTL"""
    _cache[key] = {
        'data': data,
        'expires': datetime.now() + timedelta(seconds=ttl)
    }


# ==================== Pydantic Models ====================

class PlatformOverview(BaseModel):
    """Platform-wide overview metrics"""
    total_tenants: int = 0
    active_tenants: int = 0
    suspended_tenants: int = 0
    trial_tenants: int = 0

    total_quotes: int = 0
    quotes_this_month: int = 0
    quotes_last_month: int = 0

    total_invoices: int = 0
    invoices_paid: int = 0
    invoices_paid_this_month: int = 0  # Added: paid invoices this month
    invoices_pending: int = 0

    total_revenue: float = 0
    revenue_this_month: float = 0

    total_users: int = 0
    total_clients: int = 0
    total_crm_clients: int = 0  # Added: alias for frontend compatibility

    # Trends
    tenant_growth_percent: float = 0
    quote_growth_percent: float = 0


class UsageDataPoint(BaseModel):
    """Single data point for usage charts"""
    date: str
    quotes: int = 0
    invoices: int = 0
    emails: int = 0
    logins: int = 0


class TopTenant(BaseModel):
    """Top tenant by metric"""
    tenant_id: str
    company_name: str
    value: float
    rank: int


class TenantUsageStats(BaseModel):
    """Detailed tenant usage statistics for top tenants view"""
    tenant_id: str
    company_name: str
    quotes_count: int = 0
    invoices_count: int = 0
    invoices_paid: int = 0
    total_revenue: float = 0
    users_count: int = 0
    clients_count: int = 0


class GrowthMetrics(BaseModel):
    """Tenant growth metrics"""
    new_tenants_this_week: int = 0
    new_tenants_this_month: int = 0
    new_tenants_last_month: int = 0
    growth_rate_percent: float = 0
    churn_rate_percent: float = 0


# ==================== Helper Functions ====================

def get_supabase_admin_client() -> Optional[Any]:
    """Get Supabase client for admin operations"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

    if not url or not key:
        return None

    from supabase import create_client
    return create_client(url, key)


async def get_all_quotes_stats() -> Dict[str, Any]:
    """Get aggregate quote statistics across all tenants"""
    client = get_supabase_admin_client()
    if not client:
        return {"total": 0, "this_month": 0, "last_month": 0}

    try:
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (month_start - timedelta(days=1)).replace(day=1)

        # Total quotes
        total = client.table("quotes").select("id", count="exact").execute()

        # This month
        this_month = client.table("quotes").select("id", count="exact").gte("created_at", month_start.isoformat()).execute()

        # Last month
        last_month = client.table("quotes").select("id", count="exact").gte("created_at", last_month_start.isoformat()).lt("created_at", month_start.isoformat()).execute()

        return {
            "total": total.count or 0,
            "this_month": this_month.count or 0,
            "last_month": last_month.count or 0
        }
    except Exception as e:
        logger.error(f"Error getting quote stats: {e}")
        return {"total": 0, "this_month": 0, "last_month": 0}


async def get_all_invoices_stats() -> Dict[str, Any]:
    """Get aggregate invoice statistics across all tenants"""
    client = get_supabase_admin_client()
    if not client:
        return {
            "total": 0, "paid": 0, "paid_this_month": 0, "pending": 0,
            "total_amount": 0, "this_month_amount": 0
        }

    try:
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Get all invoices - include paid_at for accurate revenue calculations
        result = client.table("invoices").select(
            "id, status, total_amount, created_at, paid_at"
        ).execute()

        if not result.data:
            return {
                "total": 0, "paid": 0, "paid_this_month": 0, "pending": 0,
                "total_amount": 0, "this_month_amount": 0
            }

        total = len(result.data)
        paid_invoices = [i for i in result.data if i.get("status") == "paid"]
        paid = len(paid_invoices)
        pending = len([i for i in result.data if i.get("status") in ["sent", "draft", "partial"]])

        # Total revenue = sum of PAID invoices' amounts only
        total_amount = sum(i.get("total_amount", 0) or 0 for i in paid_invoices)

        # This month revenue = sum of invoices PAID this month (by paid_at date)
        paid_this_month = []
        for inv in paid_invoices:
            # Use paid_at date for accurate "this month" calculation
            # Fall back to created_at for legacy invoices without paid_at
            paid_date = inv.get("paid_at") or inv.get("created_at")
            if paid_date and paid_date >= month_start.isoformat():
                paid_this_month.append(inv)

        this_month_amount = sum(i.get("total_amount", 0) or 0 for i in paid_this_month)
        paid_this_month_count = len(paid_this_month)

        return {
            "total": total,
            "paid": paid,
            "paid_this_month": paid_this_month_count,
            "pending": pending,
            "total_amount": total_amount,
            "this_month_amount": this_month_amount
        }
    except Exception as e:
        logger.error(f"Error getting invoice stats: {e}")
        return {
            "total": 0, "paid": 0, "paid_this_month": 0, "pending": 0,
            "total_amount": 0, "this_month_amount": 0
        }


async def get_user_and_client_counts() -> Dict[str, int]:
    """Get total users and CRM clients across all tenants"""
    client = get_supabase_admin_client()
    if not client:
        return {"users": 0, "clients": 0}

    try:
        users = client.table("organization_users").select("id", count="exact").eq("is_active", True).execute()
        users_count = users.count or 0

        # Try 'clients' table first, fall back to 'crm_clients' if not found
        clients_count = 0
        try:
            clients = client.table("clients").select("id", count="exact").execute()
            clients_count = clients.count or 0
        except Exception:
            # Try alternate table name
            try:
                clients = client.table("crm_clients").select("id", count="exact").execute()
                clients_count = clients.count or 0
            except Exception as e2:
                logger.warning(f"Could not query clients table: {e2}")

        return {
            "users": users_count,
            "clients": clients_count
        }
    except Exception as e:
        logger.error(f"Error getting user/client counts: {e}")
        return {"users": 0, "clients": 0}


# ==================== Endpoints ====================

@admin_analytics_router.get("/overview")
async def get_platform_overview(
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    Get platform-wide overview metrics.

    Returns aggregate statistics across all tenants including:
    - Tenant counts by status
    - Quote and invoice totals
    - Revenue metrics
    - Growth trends

    Results are cached for 60 seconds for performance.
    """
    # Check cache first
    cached = get_cached("platform_overview")
    if cached:
        return cached

    try:
        # Get tenant counts
        client_ids = list_clients()
        total_tenants = len(client_ids)

        active_tenants = total_tenants
        suspended_tenants = 0
        trial_tenants = 0

        # Fetch all stats (these are already optimized with batch queries)
        quote_stats = await get_all_quotes_stats()
        invoice_stats = await get_all_invoices_stats()
        counts = await get_user_and_client_counts()

        # Calculate growth percentages
        quote_growth = 0
        if quote_stats["last_month"] > 0:
            quote_growth = ((quote_stats["this_month"] - quote_stats["last_month"]) / quote_stats["last_month"]) * 100

        overview = PlatformOverview(
            total_tenants=total_tenants,
            active_tenants=active_tenants,
            suspended_tenants=suspended_tenants,
            trial_tenants=trial_tenants,
            total_quotes=quote_stats["total"],
            quotes_this_month=quote_stats["this_month"],
            quotes_last_month=quote_stats["last_month"],
            total_invoices=invoice_stats["total"],
            invoices_paid=invoice_stats["paid"],
            invoices_paid_this_month=invoice_stats["paid_this_month"],
            invoices_pending=invoice_stats["pending"],
            total_revenue=invoice_stats["total_amount"],
            revenue_this_month=invoice_stats["this_month_amount"],
            total_users=counts["users"],
            total_clients=counts["clients"],
            total_crm_clients=counts["clients"],
            quote_growth_percent=round(quote_growth, 1)
        )

        result = {
            "success": True,
            "data": overview.model_dump()
        }

        # Cache the result
        set_cached("platform_overview", result)

        return result

    except Exception as e:
        log_and_raise(500, "getting platform overview", e, logger)


@admin_analytics_router.get("/usage")
async def get_usage_analytics(
    period: str = Query("30d", description="Time period: 7d, 30d, 90d, 1y"),
    metric: str = Query("all", description="Metric to return: all, quotes, invoices, emails"),
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    Get usage analytics over time.

    Returns daily data points for the specified period.
    """
    try:
        # Parse period
        period_days = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}.get(period, 30)
        start_date = datetime.now() - timedelta(days=period_days)

        client = get_supabase_admin_client()
        data_points = []

        if client:
            try:
                # Get quotes by day
                quotes = client.table("quotes").select("created_at").gte("created_at", start_date.isoformat()).execute()

                # Get invoices by day
                invoices = client.table("invoices").select("created_at").gte("created_at", start_date.isoformat()).execute()

                # Aggregate by day
                quote_by_day = {}
                invoice_by_day = {}

                for q in quotes.data or []:
                    day = q["created_at"][:10]
                    quote_by_day[day] = quote_by_day.get(day, 0) + 1

                for i in invoices.data or []:
                    day = i["created_at"][:10]
                    invoice_by_day[day] = invoice_by_day.get(day, 0) + 1

                # Build data points for each day
                current = start_date
                while current <= datetime.now():
                    day_str = current.strftime("%Y-%m-%d")
                    data_points.append(UsageDataPoint(
                        date=day_str,
                        quotes=quote_by_day.get(day_str, 0),
                        invoices=invoice_by_day.get(day_str, 0),
                        emails=0,  # TODO: Get from SendGrid
                        logins=0   # TODO: Track logins
                    ))
                    current += timedelta(days=1)

            except Exception as e:
                logger.error(f"Error getting usage data: {e}")

        return {
            "success": True,
            "period": period,
            "data": [dp.model_dump() for dp in data_points]
        }

    except Exception as e:
        log_and_raise(500, "getting usage analytics", e, logger)


@admin_analytics_router.get("/tenants/top")
async def get_top_tenants(
    metric: str = Query("quotes", description="Metric to sort by: quotes, invoices, revenue"),
    limit: int = Query(10, ge=1, le=50),
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    Get top performing tenants by specified metric.

    Returns detailed usage stats for each tenant, sorted by the specified metric.
    Optimized to use batch queries instead of per-tenant queries.
    """
    try:
        client_ids = list_clients()

        client = get_supabase_admin_client()
        if not client:
            return {"success": True, "data": [], "metric": metric}

        # Batch fetch all data in parallel (4 queries total instead of N*4)
        import asyncio

        async def fetch_all_data():
            # Get all quotes grouped by tenant_id
            quotes_result = client.table("quotes").select("tenant_id").execute()

            # Get all invoices with status and amount
            invoices_result = client.table("invoices").select("tenant_id, status, total_amount").execute()

            # Get all active users
            users_result = client.table("organization_users").select("tenant_id").eq("is_active", True).execute()

            # Get all CRM clients
            clients_result = client.table("clients").select("tenant_id").execute()

            return quotes_result, invoices_result, users_result, clients_result

        quotes_result, invoices_result, users_result, clients_result = await asyncio.to_thread(fetch_all_data)

        # Aggregate data by tenant_id in Python (much faster than N queries)
        quotes_by_tenant = {}
        for q in quotes_result.data or []:
            tid = q.get("tenant_id")
            if tid:
                quotes_by_tenant[tid] = quotes_by_tenant.get(tid, 0) + 1

        invoices_by_tenant = {}
        revenue_by_tenant = {}
        paid_by_tenant = {}
        for inv in invoices_result.data or []:
            tid = inv.get("tenant_id")
            if tid:
                invoices_by_tenant[tid] = invoices_by_tenant.get(tid, 0) + 1
                revenue_by_tenant[tid] = revenue_by_tenant.get(tid, 0) + (inv.get("total_amount") or 0)
                if inv.get("status") == "paid":
                    paid_by_tenant[tid] = paid_by_tenant.get(tid, 0) + 1

        users_by_tenant = {}
        for u in users_result.data or []:
            tid = u.get("tenant_id")
            if tid:
                users_by_tenant[tid] = users_by_tenant.get(tid, 0) + 1

        clients_by_tenant = {}
        for c in clients_result.data or []:
            tid = c.get("tenant_id")
            if tid:
                clients_by_tenant[tid] = clients_by_tenant.get(tid, 0) + 1

        # Build tenant stats
        tenant_stats = []
        for tenant_id in client_ids:
            try:
                config = ClientConfig(tenant_id)
                company_name = getattr(config, 'company_name', tenant_id)

                tenant_stats.append(TenantUsageStats(
                    tenant_id=tenant_id,
                    company_name=company_name,
                    quotes_count=quotes_by_tenant.get(tenant_id, 0),
                    invoices_count=invoices_by_tenant.get(tenant_id, 0),
                    invoices_paid=paid_by_tenant.get(tenant_id, 0),
                    total_revenue=revenue_by_tenant.get(tenant_id, 0),
                    users_count=users_by_tenant.get(tenant_id, 0),
                    clients_count=clients_by_tenant.get(tenant_id, 0)
                ))
            except Exception as e:
                logger.warning(f"Could not load config for {tenant_id}: {e}")
                continue

        # Sort by specified metric descending
        if metric == "quotes":
            tenant_stats.sort(key=lambda x: x.quotes_count, reverse=True)
        elif metric == "invoices":
            tenant_stats.sort(key=lambda x: x.invoices_count, reverse=True)
        elif metric == "revenue":
            tenant_stats.sort(key=lambda x: x.total_revenue, reverse=True)
        else:
            tenant_stats.sort(key=lambda x: x.total_revenue, reverse=True)

        return {
            "success": True,
            "metric": metric,
            "data": [t.model_dump() for t in tenant_stats[:limit]]
        }

    except Exception as e:
        log_and_raise(500, "getting top tenants", e, logger)


@admin_analytics_router.get("/growth")
async def get_growth_metrics(
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    Get tenant growth metrics.
    """
    try:
        # For now, return placeholder data
        # TODO: Implement proper tracking of tenant creation dates
        metrics = GrowthMetrics(
            new_tenants_this_week=0,
            new_tenants_this_month=0,
            new_tenants_last_month=0,
            growth_rate_percent=0,
            churn_rate_percent=0
        )

        return {
            "success": True,
            "data": metrics.model_dump()
        }

    except Exception as e:
        log_and_raise(500, "getting growth metrics", e, logger)


# ==================== Router Registration ====================

def include_admin_analytics_router(app: Any) -> None:
    """Include admin analytics router in the FastAPI app"""
    app.include_router(admin_analytics_router)
