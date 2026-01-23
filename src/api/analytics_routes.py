"""
Analytics API Routes

Provides comprehensive analytics and statistics endpoints:
- Dashboard summary stats
- Quote analytics
- Invoice analytics
- Call analytics
- CRM pipeline analytics

All endpoints support tenant isolation via X-Client-ID header.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Header, Query
from pydantic import BaseModel

from config.loader import ClientConfig
from src.utils.error_handler import log_and_raise

logger = logging.getLogger(__name__)

# ==================== Router ====================

analytics_router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])
dashboard_router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


# ==================== Dependency ====================

_client_configs = {}

def get_client_config(x_client_id: str = Header(None, alias="X-Client-ID")) -> ClientConfig:
    """Get client configuration from header"""
    import os
    client_id = x_client_id or os.getenv("CLIENT_ID", "example")

    if client_id not in _client_configs:
        try:
            _client_configs[client_id] = ClientConfig(client_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid client: {client_id}")

    return _client_configs[client_id]


# ==================== Response Models ====================

class DateRange(BaseModel):
    """Date range filter"""
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None    # YYYY-MM-DD
    period: str = "30d"               # 7d, 30d, 90d, year, all


# ==================== Helper Functions ====================

def get_date_range(period: str) -> tuple:
    """Convert period string to date range"""
    now = datetime.utcnow()

    if period == "7d":
        start = now - timedelta(days=7)
    elif period == "30d":
        start = now - timedelta(days=30)
    elif period == "90d":
        start = now - timedelta(days=90)
    elif period == "year":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:  # all
        start = datetime(2020, 1, 1)

    return start, now


def calculate_change(current: float, previous: float) -> Dict[str, Any]:
    """Calculate percentage change between periods"""
    if previous == 0:
        return {"value": 0, "type": "neutral"}

    change = ((current - previous) / previous) * 100
    return {
        "value": round(abs(change), 1),
        "type": "positive" if change >= 0 else "negative"
    }


# ==================== Dashboard Stats ====================

@dashboard_router.get("/stats")
async def get_dashboard_stats(
    period: str = Query(default="30d", regex="^(7d|30d|90d|year|all)$"),
    config: ClientConfig = Depends(get_client_config)
):
    """
    Get aggregated dashboard statistics

    Returns key metrics for the dashboard overview:
    - Quote stats (total, accepted, pending)
    - Revenue stats (total, collected, outstanding)
    - Client stats (total, new this period)
    - Call stats (completed, pending)
    """
    from src.tools.supabase_tool import SupabaseTool
    from src.services.crm_service import CRMService

    try:
        supabase = SupabaseTool(config)
        crm = CRMService(config)

        start_date, end_date = get_date_range(period)
        prev_start = start_date - (end_date - start_date)

        stats = {
            "quotes": {"total": 0, "accepted": 0, "pending": 0, "conversion_rate": 0},
            "revenue": {"total": 0, "collected": 0, "outstanding": 0, "overdue": 0},
            "clients": {"total": 0, "new": 0, "active": 0},
            "calls": {"completed": 0, "pending": 0, "scheduled": 0},
            "period": period,
            "generated_at": datetime.utcnow().isoformat()
        }

        if not supabase.client:
            return {"success": True, "data": stats}

        # Quote stats
        try:
            quotes_result = supabase.client.table('quotes')\
                .select("status, total_price, created_at")\
                .eq('tenant_id', config.client_id)\
                .gte('created_at', start_date.isoformat())\
                .execute()

            quotes = quotes_result.data or []
            stats["quotes"]["total"] = len(quotes)
            stats["quotes"]["accepted"] = len([q for q in quotes if q.get('status') == 'accepted'])
            stats["quotes"]["pending"] = len([q for q in quotes if q.get('status') in ('sent', 'viewed', 'draft')])

            if stats["quotes"]["total"] > 0:
                stats["quotes"]["conversion_rate"] = round(
                    (stats["quotes"]["accepted"] / stats["quotes"]["total"]) * 100, 1
                )

            stats["revenue"]["total"] = sum(q.get('total_price', 0) or 0 for q in quotes)
        except Exception as e:
            logger.warning(f"Failed to get quote stats: {e}")

        # Invoice stats
        try:
            invoices_result = supabase.client.table('invoices')\
                .select("status, total_amount, due_date, created_at")\
                .eq('tenant_id', config.client_id)\
                .execute()

            invoices = invoices_result.data or []
            now = datetime.utcnow()

            for inv in invoices:
                amount = inv.get('total_amount', 0) or 0
                status = inv.get('status', '')

                if status == 'paid':
                    stats["revenue"]["collected"] += amount
                elif status in ('sent', 'viewed', 'draft'):
                    stats["revenue"]["outstanding"] += amount
                    # Check if overdue
                    due_date = inv.get('due_date')
                    if due_date:
                        try:
                            due = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                            if due < now:
                                stats["revenue"]["overdue"] += amount
                        except (ValueError, TypeError) as e:
                            logger.debug(f"Failed to parse due_date {due_date}: {e}")
        except Exception as e:
            logger.warning(f"Failed to get invoice stats: {e}")

        # Client stats
        try:
            crm_stats = crm.get_client_stats()
            stats["clients"]["total"] = crm_stats.get('total_clients', 0)

            # Count new clients in period
            clients_result = supabase.client.table('clients')\
                .select("created_at")\
                .eq('tenant_id', config.client_id)\
                .gte('created_at', start_date.isoformat())\
                .execute()

            stats["clients"]["new"] = len(clients_result.data or [])

            # Active = not in LOST or TRAVELLED stage
            by_stage = crm_stats.get('by_stage', {})
            stats["clients"]["active"] = stats["clients"]["total"] - by_stage.get('LOST', 0) - by_stage.get('TRAVELLED', 0)
        except Exception as e:
            logger.warning(f"Failed to get client stats: {e}")

        # Call stats
        try:
            # Completed calls
            calls_result = supabase.client.table('call_records')\
                .select("call_status, created_at")\
                .eq('tenant_id', config.client_id)\
                .gte('created_at', start_date.isoformat())\
                .execute()

            calls = calls_result.data or []
            stats["calls"]["completed"] = len([c for c in calls if c.get('call_status') == 'completed'])

            # Pending calls
            queue_result = supabase.client.table('outbound_call_queue')\
                .select("call_status")\
                .eq('tenant_id', config.client_id)\
                .in_('call_status', ['queued', 'scheduled'])\
                .execute()

            queue = queue_result.data or []
            stats["calls"]["pending"] = len([c for c in queue if c.get('call_status') == 'queued'])
            stats["calls"]["scheduled"] = len([c for c in queue if c.get('call_status') == 'scheduled'])
        except Exception as e:
            logger.warning(f"Failed to get call stats: {e}")

        return {"success": True, "data": stats}

    except Exception as e:
        log_and_raise(500, "getting dashboard stats", e, logger)


@dashboard_router.get("/activity")
async def get_recent_activity(
    limit: int = Query(default=20, le=50),
    config: ClientConfig = Depends(get_client_config)
):
    """Get recent activity across all modules"""
    from src.tools.supabase_tool import SupabaseTool

    try:
        supabase = SupabaseTool(config)
        activities = []

        if not supabase.client:
            return {"success": True, "data": activities}

        # Get recent quotes
        try:
            quotes = supabase.client.table('quotes')\
                .select("quote_id, customer_name, destination, status, created_at")\
                .eq('tenant_id', config.client_id)\
                .order('created_at', desc=True)\
                .limit(5)\
                .execute()

            for q in (quotes.data or []):
                activities.append({
                    "type": "quote",
                    "title": f"Quote for {q.get('customer_name', 'Unknown')}",
                    "subtitle": q.get('destination', ''),
                    "status": q.get('status'),
                    "timestamp": q.get('created_at'),
                    "link": f"/quotes/{q.get('quote_id')}"
                })
        except Exception as e:
            logger.debug(f"Could not fetch recent quotes: {e}")

        # Get recent invoices
        try:
            invoices = supabase.client.table('invoices')\
                .select("invoice_id, customer_name, total_amount, status, created_at")\
                .eq('tenant_id', config.client_id)\
                .order('created_at', desc=True)\
                .limit(5)\
                .execute()

            for inv in (invoices.data or []):
                activities.append({
                    "type": "invoice",
                    "title": f"Invoice for {inv.get('customer_name', 'Unknown')}",
                    "subtitle": f"{config.currency} {inv.get('total_amount', 0):,.0f}",
                    "status": inv.get('status'),
                    "timestamp": inv.get('created_at'),
                    "link": f"/invoices/{inv.get('invoice_id')}"
                })
        except Exception as e:
            logger.debug(f"Could not fetch recent invoices: {e}")

        # Get recent client activities
        try:
            client_activities = supabase.client.table('activities')\
                .select("activity_type, description, created_at, client_id")\
                .eq('tenant_id', config.client_id)\
                .order('created_at', desc=True)\
                .limit(5)\
                .execute()

            for act in (client_activities.data or []):
                activities.append({
                    "type": "activity",
                    "title": act.get('activity_type', 'Activity'),
                    "subtitle": act.get('description', ''),
                    "timestamp": act.get('created_at'),
                    "link": f"/crm/clients/{act.get('client_id')}"
                })
        except Exception as e:
            logger.debug(f"Could not fetch recent activities: {e}")

        # Sort by timestamp and limit
        activities.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return {"success": True, "data": activities[:limit]}

    except Exception as e:
        log_and_raise(500, "getting recent activity", e, logger)


# ==================== Quote Analytics ====================

@analytics_router.get("/quotes")
async def get_quote_analytics(
    period: str = Query(default="30d", regex="^(7d|30d|90d|year|all)$"),
    config: ClientConfig = Depends(get_client_config)
):
    """
    Get detailed quote analytics

    Returns:
    - Summary stats
    - By status breakdown
    - By destination breakdown
    - Trend over time
    - Top performing hotels
    """
    from src.tools.supabase_tool import SupabaseTool

    try:
        supabase = SupabaseTool(config)
        start_date, end_date = get_date_range(period)

        result = {
            "summary": {
                "total": 0,
                "total_value": 0,
                "avg_value": 0,
                "conversion_rate": 0
            },
            "by_status": {},
            "by_destination": [],
            "by_hotel": [],
            "trend": [],
            "period": period
        }

        if not supabase.client:
            return {"success": True, "data": result}

        # Get all quotes in period
        quotes_result = supabase.client.table('quotes')\
            .select("*")\
            .eq('tenant_id', config.client_id)\
            .gte('created_at', start_date.isoformat())\
            .order('created_at', desc=True)\
            .execute()

        quotes = quotes_result.data or []

        if not quotes:
            return {"success": True, "data": result}

        # Summary stats
        result["summary"]["total"] = len(quotes)
        result["summary"]["total_value"] = sum(q.get('total_price', 0) or 0 for q in quotes)
        result["summary"]["avg_value"] = round(result["summary"]["total_value"] / len(quotes), 2)

        accepted = len([q for q in quotes if q.get('status') == 'accepted'])
        result["summary"]["conversion_rate"] = round((accepted / len(quotes)) * 100, 1)

        # By status
        status_counts = {}
        status_values = {}
        for q in quotes:
            status = q.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
            status_values[status] = status_values.get(status, 0) + (q.get('total_price', 0) or 0)

        result["by_status"] = {
            status: {"count": count, "value": status_values.get(status, 0)}
            for status, count in status_counts.items()
        }

        # By destination
        dest_stats = {}
        for q in quotes:
            dest = q.get('destination', 'Unknown')
            if dest not in dest_stats:
                dest_stats[dest] = {"count": 0, "value": 0, "accepted": 0}
            dest_stats[dest]["count"] += 1
            dest_stats[dest]["value"] += q.get('total_price', 0) or 0
            if q.get('status') == 'accepted':
                dest_stats[dest]["accepted"] += 1

        result["by_destination"] = [
            {"destination": dest, **stats}
            for dest, stats in sorted(dest_stats.items(), key=lambda x: x[1]["count"], reverse=True)
        ][:10]

        # By hotel (from 'hotels' array field)
        import json
        hotel_stats = {}
        for q in quotes:
            # The 'hotels' field contains an array of hotel objects
            hotels_data = q.get('hotels')
            if hotels_data:
                try:
                    hotels = json.loads(hotels_data) if isinstance(hotels_data, str) else hotels_data
                    if isinstance(hotels, list):
                        for hotel in hotels:
                            hotel_name = hotel.get('name') or hotel.get('hotel_name')
                            if hotel_name:
                                if hotel_name not in hotel_stats:
                                    hotel_stats[hotel_name] = {"count": 0, "value": 0}
                                hotel_stats[hotel_name]["count"] += 1
                                hotel_stats[hotel_name]["value"] += hotel.get('total_price', 0) or 0
                except Exception as e:
                    logger.debug(f"Could not parse hotels data: {e}")

        result["by_hotel"] = [
            {"hotel": hotel, **stats}
            for hotel, stats in sorted(hotel_stats.items(), key=lambda x: x[1]["count"], reverse=True)
        ][:10]

        # Trend (group by week/month depending on period)
        from collections import defaultdict
        trend_data = defaultdict(lambda: {"count": 0, "value": 0})

        for q in quotes:
            created = q.get('created_at', '')
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    if period in ('7d', '30d'):
                        key = dt.strftime('%Y-%m-%d')
                    else:
                        key = dt.strftime('%Y-%m')
                    trend_data[key]["count"] += 1
                    trend_data[key]["value"] += q.get('total_price', 0) or 0
                except (ValueError, TypeError) as e:
                    logger.debug(f"Failed to parse quote created_at: {e}")

        result["trend"] = [
            {"date": date, **data}
            for date, data in sorted(trend_data.items())
        ]

        return {"success": True, "data": result}

    except Exception as e:
        log_and_raise(500, "getting quote analytics", e, logger)


# ==================== Invoice Analytics ====================

@analytics_router.get("/invoices")
async def get_invoice_analytics(
    period: str = Query(default="30d", regex="^(7d|30d|90d|year|all)$"),
    config: ClientConfig = Depends(get_client_config)
):
    """
    Get detailed invoice analytics

    Returns:
    - Summary stats (total, paid, outstanding, overdue)
    - By status breakdown
    - Payment timeline
    - Aging report
    """
    from src.tools.supabase_tool import SupabaseTool

    try:
        supabase = SupabaseTool(config)
        start_date, end_date = get_date_range(period)
        now = datetime.utcnow()

        result = {
            "summary": {
                "total_invoices": 0,
                "total_value": 0,
                "paid_value": 0,
                "outstanding_value": 0,
                "overdue_value": 0,
                "avg_invoice_value": 0,
                "payment_rate": 0
            },
            "by_status": {},
            "aging": {
                "current": 0,
                "30_days": 0,
                "60_days": 0,
                "90_plus_days": 0
            },
            "trend": [],
            "period": period
        }

        if not supabase.client:
            return {"success": True, "data": result}

        # Get all invoices
        invoices_result = supabase.client.table('invoices')\
            .select("*")\
            .eq('tenant_id', config.client_id)\
            .execute()

        invoices = invoices_result.data or []

        if not invoices:
            return {"success": True, "data": result}

        # Summary stats
        result["summary"]["total_invoices"] = len(invoices)
        result["summary"]["total_value"] = sum(inv.get('total_amount', 0) or 0 for inv in invoices)

        if invoices:
            result["summary"]["avg_invoice_value"] = round(
                result["summary"]["total_value"] / len(invoices), 2
            )

        # By status and aging
        status_counts = {}
        status_values = {}

        for inv in invoices:
            amount = inv.get('total_amount', 0) or 0
            status = inv.get('status', 'draft')

            status_counts[status] = status_counts.get(status, 0) + 1
            status_values[status] = status_values.get(status, 0) + amount

            if status == 'paid':
                result["summary"]["paid_value"] += amount
            else:
                result["summary"]["outstanding_value"] += amount

                # Aging calculation
                due_date_str = inv.get('due_date')
                if due_date_str:
                    try:
                        due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                        days_overdue = (now - due_date).days

                        if days_overdue <= 0:
                            result["aging"]["current"] += amount
                        elif days_overdue <= 30:
                            result["aging"]["30_days"] += amount
                            result["summary"]["overdue_value"] += amount
                        elif days_overdue <= 60:
                            result["aging"]["60_days"] += amount
                            result["summary"]["overdue_value"] += amount
                        else:
                            result["aging"]["90_plus_days"] += amount
                            result["summary"]["overdue_value"] += amount
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Failed to parse invoice due_date: {e}")
                        result["aging"]["current"] += amount
                else:
                    result["aging"]["current"] += amount

        result["by_status"] = {
            status: {"count": count, "value": status_values.get(status, 0)}
            for status, count in status_counts.items()
        }

        # Payment rate
        if result["summary"]["total_value"] > 0:
            result["summary"]["payment_rate"] = round(
                (result["summary"]["paid_value"] / result["summary"]["total_value"]) * 100, 1
            )

        # Trend (payments over time)
        from collections import defaultdict
        trend_data = defaultdict(lambda: {"invoiced": 0, "paid": 0, "count": 0})

        for inv in invoices:
            created = inv.get('created_at', '')
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    if dt >= start_date:
                        if period in ('7d', '30d'):
                            key = dt.strftime('%Y-%m-%d')
                        else:
                            key = dt.strftime('%Y-%m')

                        amount = inv.get('total_amount', 0) or 0
                        trend_data[key]["invoiced"] += amount
                        trend_data[key]["count"] += 1

                        if inv.get('status') == 'paid':
                            trend_data[key]["paid"] += amount
                except (ValueError, TypeError) as e:
                    logger.debug(f"Failed to parse invoice created_at: {e}")

        result["trend"] = [
            {"date": date, **data}
            for date, data in sorted(trend_data.items())
        ]

        return {"success": True, "data": result}

    except Exception as e:
        log_and_raise(500, "getting invoice analytics", e, logger)


# ==================== Call Analytics ====================

@analytics_router.get("/calls")
async def get_call_analytics(
    period: str = Query(default="30d", regex="^(7d|30d|90d|year|all)$"),
    config: ClientConfig = Depends(get_client_config)
):
    """
    Get detailed call analytics

    Returns:
    - Summary stats (total, completed, avg duration)
    - By outcome breakdown
    - Queue status
    - Trend over time
    """
    from src.tools.supabase_tool import SupabaseTool

    try:
        supabase = SupabaseTool(config)
        start_date, end_date = get_date_range(period)

        result = {
            "summary": {
                "total_calls": 0,
                "completed": 0,
                "failed": 0,
                "avg_duration_seconds": 0,
                "success_rate": 0
            },
            "queue": {
                "pending": 0,
                "scheduled": 0,
                "in_progress": 0
            },
            "by_outcome": {},
            "trend": [],
            "period": period
        }

        if not supabase.client:
            return {"success": True, "data": result}

        # Get call records - handle both 'call_status' and 'status' column names
        try:
            records_result = supabase.client.table('call_records')\
                .select("*")\
                .eq('tenant_id', config.client_id)\
                .gte('created_at', start_date.isoformat())\
                .execute()

            records = records_result.data or []

            result["summary"]["total_calls"] = len(records)

            total_duration = 0
            outcome_counts = {}

            for rec in records:
                # Support both 'call_status' and 'status' column names
                status = rec.get('call_status') or rec.get('status', 'unknown')
                outcome = rec.get('outcome', status)

                outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

                if status == 'completed':
                    result["summary"]["completed"] += 1
                    # Support both 'duration_seconds' and 'duration'
                    duration = rec.get('duration_seconds') or rec.get('duration', 0) or 0
                    total_duration += duration
                elif status in ('failed', 'no_answer', 'busy', 'error'):
                    result["summary"]["failed"] += 1

            if result["summary"]["completed"] > 0:
                result["summary"]["avg_duration_seconds"] = round(
                    total_duration / result["summary"]["completed"], 1
                )

            if result["summary"]["total_calls"] > 0:
                result["summary"]["success_rate"] = round(
                    (result["summary"]["completed"] / result["summary"]["total_calls"]) * 100, 1
                )

            result["by_outcome"] = outcome_counts

        except Exception as e:
            logger.warning(f"Could not get call records: {e}")

        # Get queue status - handle table/column variations
        try:
            queue_result = supabase.client.table('outbound_call_queue')\
                .select("*")\
                .eq('tenant_id', config.client_id)\
                .execute()

            for item in (queue_result.data or []):
                # Support both 'call_status' and 'status' column names
                status = item.get('call_status') or item.get('status', '')
                if status in ('queued', 'pending'):
                    result["queue"]["pending"] += 1
                elif status == 'scheduled':
                    result["queue"]["scheduled"] += 1
                elif status == 'in_progress':
                    result["queue"]["in_progress"] += 1

        except Exception as e:
            logger.warning(f"Could not get call queue: {e}")

        # Trend
        from collections import defaultdict
        trend_data = defaultdict(lambda: {"calls": 0, "completed": 0, "duration": 0})

        try:
            for rec in records:
                created = rec.get('created_at', '')
                if created:
                    try:
                        dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        if period in ('7d', '30d'):
                            key = dt.strftime('%Y-%m-%d')
                        else:
                            key = dt.strftime('%Y-%m')

                        trend_data[key]["calls"] += 1
                        if rec.get('call_status') == 'completed':
                            trend_data[key]["completed"] += 1
                            trend_data[key]["duration"] += rec.get('duration_seconds', 0) or 0
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Failed to parse call created_at: {e}")
        except Exception as e:
            logger.debug(f"Failed to process call trend data: {e}")

        result["trend"] = [
            {"date": date, **data}
            for date, data in sorted(trend_data.items())
        ]

        return {"success": True, "data": result}

    except Exception as e:
        log_and_raise(500, "getting call analytics", e, logger)


# ==================== Pipeline Analytics ====================

@analytics_router.get("/pipeline")
async def get_pipeline_analytics(
    config: ClientConfig = Depends(get_client_config)
):
    """
    Get detailed pipeline analytics

    Returns:
    - Stage breakdown with counts and values
    - Conversion funnel
    - Average time in each stage
    """
    from src.services.crm_service import CRMService, PipelineStage

    try:
        crm = CRMService(config)

        summary = crm.get_pipeline_summary()
        stats = crm.get_client_stats()

        logger.info(f"Pipeline analytics - Summary: {summary}")
        logger.info(f"Pipeline analytics - Stats total_value: {stats.get('total_value', 0)}")

        # Calculate funnel conversion rates
        stages = ['QUOTED', 'NEGOTIATING', 'BOOKED', 'PAID', 'TRAVELLED']
        funnel = []

        prev_count = None
        for stage in stages:
            stage_data = summary.get(stage, {})
            count = stage_data.get('count', 0)
            value = stage_data.get('value', 0)

            conversion = 100 if prev_count is None else (
                round((count / prev_count) * 100, 1) if prev_count > 0 else 0
            )

            funnel.append({
                "stage": stage,
                "count": count,
                "value": value,
                "conversion_rate": conversion
            })

            prev_count = count

        return {
            "success": True,
            "data": {
                "summary": summary,
                "funnel": funnel,
                "by_source": stats.get('by_source', {}),
                "total_clients": stats.get('total_clients', 0),
                "total_pipeline_value": stats.get('total_value', 0)
            }
        }

    except Exception as e:
        log_and_raise(500, "getting pipeline analytics", e, logger)


# ==================== Aggregated Dashboard Endpoint ====================

# Cache for dashboard data (5 minute TTL for faster page loads)
_dashboard_cache = {}
_cache_ttl = 300  # seconds (5 minutes) - fresh data
_stale_ttl = 1800  # seconds (30 minutes) - stale but usable, refresh in background

# Separate cache for BigQuery pricing stats (4 hour TTL - rarely changes)
_pricing_stats_cache = {}
_pricing_stats_ttl = 14400  # seconds (4 hours) - pricing data doesn't change often


# Import BigQuery client from pricing_routes to share the same client and availability flag
async def get_bigquery_client_async(config: ClientConfig):
    """Get BigQuery client - uses shared client from pricing_routes.py"""
    try:
        from src.api.pricing_routes import get_bigquery_client_async as pricing_get_bq_client
        return await pricing_get_bq_client(config)
    except ImportError as e:
        logger.warning(f"[Dashboard] Could not import pricing BigQuery client: {e}")
        return None
    except Exception as e:
        logger.warning(f"[Dashboard] Failed to get BigQuery client: {e}")
        return None


async def _refresh_dashboard_cache(config: ClientConfig, cache_key: str):
    """Background task to refresh dashboard cache without blocking the response"""
    import asyncio
    from datetime import datetime
    from src.tools.supabase_tool import SupabaseTool

    try:
        now = datetime.utcnow()
        supabase = SupabaseTool(config)

        result = {
            "stats": {
                "total_quotes": 0,
                "active_clients": 0,
                "total_hotels": 0,
                "total_destinations": 0,
            },
            "recent_quotes": [],
            "usage": {},
            "generated_at": now.isoformat()
        }

        # Simplified parallel fetch for background refresh
        async def fetch_counts():
            try:
                quotes = await asyncio.to_thread(
                    lambda: supabase.client.table('quotes')
                        .select("id", count="exact")
                        .eq('tenant_id', config.client_id)
                        .execute()
                )
                clients = await asyncio.to_thread(
                    lambda: supabase.client.table('clients')
                        .select("id", count="exact")
                        .eq('tenant_id', config.client_id)
                        .execute()
                )
                return quotes.count or 0, clients.count or 0
            except Exception as e:
                logger.warning(f"Failed to fetch usage stats: {e}")
                return 0, 0

        async def fetch_pricing_stats():
            pricing_cache_key = f"pricing_{config.client_id}"
            if pricing_cache_key in _pricing_stats_cache:
                cached = _pricing_stats_cache[pricing_cache_key]
                if (now - cached['timestamp']).total_seconds() < _pricing_stats_ttl:
                    return cached['data']

            try:
                client = await get_bigquery_client_async(config)
                if not client:
                    if pricing_cache_key in _pricing_stats_cache:
                        return _pricing_stats_cache[pricing_cache_key]['data']
                    return {"hotels": 0, "destinations": 0}

                def _query():
                    # Count all hotels and destinations (no is_active filter for overview)
                    hotel_query = f"""
                    SELECT
                        COUNT(DISTINCT hotel_name) as hotel_count,
                        COUNT(DISTINCT destination) as dest_count
                    FROM `{config.gcp_project_id}.{config.shared_pricing_dataset}.hotel_rates`
                    """
                    result = client.query(hotel_query).result()
                    rows = list(result)
                    return rows[0] if rows else None

                row = await asyncio.to_thread(_query)
                if row:
                    hotel_count = row.hotel_count if row.hotel_count is not None else 0
                    dest_count = row.dest_count if row.dest_count is not None else 0
                    stats = {"hotels": int(hotel_count), "destinations": int(dest_count)}
                    _pricing_stats_cache[pricing_cache_key] = {'data': stats, 'timestamp': now}
                    return stats
                return {"hotels": 0, "destinations": 0}
            except Exception as e:
                logger.warning(f"Background refresh - pricing stats failed: {e}")
                if pricing_cache_key in _pricing_stats_cache:
                    return _pricing_stats_cache[pricing_cache_key]['data']
                return {"hotels": 0, "destinations": 0}

        quote_count, client_count = await fetch_counts()
        pricing_stats = await fetch_pricing_stats()

        result["stats"]["total_quotes"] = quote_count
        result["stats"]["active_clients"] = client_count
        result["stats"]["total_hotels"] = pricing_stats.get("hotels", 0)
        result["stats"]["total_destinations"] = pricing_stats.get("destinations", 0)

        # Update cache
        _dashboard_cache[cache_key] = {"data": result, "timestamp": now}
        logger.info(f"Background refresh completed for {config.client_id}")

    except Exception as e:
        logger.warning(f"Background cache refresh failed: {e}")


@dashboard_router.get("/all")
async def get_dashboard_all(
    config: ClientConfig = Depends(get_client_config)
):
    """
    Get ALL dashboard data in a single request (optimized for performance)

    Returns everything the dashboard needs:
    - Stats (quotes, clients, hotels, destinations)
    - Recent quotes (last 5)
    - Top performers / leaderboard (top 5)
    - Usage limits

    Uses caching (5min TTL) with stale-while-revalidate (30min) for optimal performance.
    """
    import asyncio
    from datetime import datetime, timedelta

    cache_key = f"dashboard_{config.client_id}"
    now = datetime.utcnow()

    # Check cache - implement stale-while-revalidate pattern
    if cache_key in _dashboard_cache:
        cached = _dashboard_cache[cache_key]
        cache_age = (now - cached['timestamp']).total_seconds()

        if cache_age < _cache_ttl:
            # Fresh cache - return immediately
            logger.debug(f"Returning fresh cached dashboard for {config.client_id}")
            return {"success": True, "data": cached['data'], "cached": True}

        if cache_age < _stale_ttl:
            # Stale cache - return immediately, but trigger background refresh
            logger.debug(f"Returning stale cached dashboard for {config.client_id}, triggering background refresh")
            # Fire and forget background refresh
            asyncio.create_task(_refresh_dashboard_cache(config, cache_key))
            return {"success": True, "data": cached['data'], "cached": True, "stale": True}

    from src.tools.supabase_tool import SupabaseTool

    result = {
        "stats": {
            "total_quotes": 0,
            "active_clients": 0,
            "total_hotels": 0,
            "total_destinations": 0,
        },
        "recent_quotes": [],
        "usage": {},
        "generated_at": now.isoformat()
    }

    try:
        supabase = SupabaseTool(config)

        # Fetch all data in parallel using asyncio.to_thread to avoid blocking
        async def fetch_quotes():
            try:
                def _query():
                    return supabase.client.table('quotes')\
                        .select("quote_id, customer_name, customer_email, destination, total_price, status, created_at")\
                        .eq('tenant_id', config.client_id)\
                        .order('created_at', desc=True)\
                        .limit(5)\
                        .execute()
                quotes_result = await asyncio.to_thread(_query)
                return quotes_result.data or []
            except Exception as e:
                logger.warning(f"Failed to fetch quotes: {e}")
                return []

        async def fetch_quote_count():
            try:
                def _query():
                    return supabase.client.table('quotes')\
                        .select("id", count="exact")\
                        .eq('tenant_id', config.client_id)\
                        .execute()
                count_result = await asyncio.to_thread(_query)
                return count_result.count or 0
            except Exception as e:
                logger.warning(f"Failed to fetch quote count: {e}")
                return 0

        async def fetch_client_count():
            try:
                def _query():
                    return supabase.client.table('clients')\
                        .select("id", count="exact")\
                        .eq('tenant_id', config.client_id)\
                        .execute()
                count_result = await asyncio.to_thread(_query)
                return count_result.count or 0
            except Exception as e:
                logger.warning(f"Failed to fetch client count: {e}")
                return 0

        async def fetch_pricing_stats():
            # Check pricing stats cache first (4 hour TTL - pricing data rarely changes)
            pricing_cache_key = f"pricing_{config.client_id}"
            if pricing_cache_key in _pricing_stats_cache:
                cached = _pricing_stats_cache[pricing_cache_key]
                if (now - cached['timestamp']).total_seconds() < _pricing_stats_ttl:
                    logger.debug(f"Returning cached pricing stats for {config.client_id}")
                    return cached['data']

            try:
                # Use cached BigQuery client (same pattern as working pricing_routes.py)
                client = await get_bigquery_client_async(config)
                if not client:
                    logger.warning(f"BigQuery client not available for {config.client_id}")
                    # Return cached value if available, else 0
                    if pricing_cache_key in _pricing_stats_cache:
                        return _pricing_stats_cache[pricing_cache_key]['data']
                    return {"hotels": 0, "destinations": 0}

                def _query():
                    # Count all hotels and destinations (don't filter by is_active for overview stats)
                    hotel_query = f"""
                    SELECT
                        COUNT(DISTINCT hotel_name) as hotel_count,
                        COUNT(DISTINCT destination) as dest_count
                    FROM `{config.gcp_project_id}.{config.shared_pricing_dataset}.hotel_rates`
                    """
                    result = client.query(hotel_query).result()
                    rows = list(result)
                    return rows[0] if rows else None

                # No timeout needed - client init already handles cold start
                row = await asyncio.to_thread(_query)
                if row:
                    hotel_count = row.hotel_count if row.hotel_count is not None else 0
                    dest_count = row.dest_count if row.dest_count is not None else 0
                    stats = {"hotels": int(hotel_count), "destinations": int(dest_count)}
                    logger.info(f"Fetched pricing stats for {config.client_id}: {stats}")
                    # Cache the result
                    _pricing_stats_cache[pricing_cache_key] = {
                        'data': stats,
                        'timestamp': now
                    }
                    return stats
                return {"hotels": 0, "destinations": 0}
            except Exception as e:
                logger.warning(f"Failed to fetch pricing stats for {config.client_id}: {e}")
                # Return cached value if available
                if pricing_cache_key in _pricing_stats_cache:
                    return _pricing_stats_cache[pricing_cache_key]['data']
                return {"hotels": 0, "destinations": 0}

        async def fetch_usage():
            try:
                # Simplified usage stats
                today = now.date().isoformat()
                def _query():
                    return supabase.client.table('quotes')\
                        .select("id", count="exact")\
                        .eq('tenant_id', config.client_id)\
                        .gte('created_at', today)\
                        .execute()
                quotes_today = await asyncio.to_thread(_query)

                return {
                    "quotes": {"current": quotes_today.count or 0, "limit": 100},
                    "api_calls": {"current": 0, "limit": 1000}
                }
            except Exception as e:
                logger.warning(f"Failed to fetch usage: {e}")
                return {}

        # Execute all fetches in parallel
        quotes, quote_count, client_count, pricing_stats, usage = await asyncio.gather(
            fetch_quotes(),
            fetch_quote_count(),
            fetch_client_count(),
            fetch_pricing_stats(),
            fetch_usage(),
            return_exceptions=True
        )

        # Handle any exceptions that were returned
        if isinstance(quotes, Exception):
            quotes = []
        if isinstance(quote_count, Exception):
            quote_count = 0
        if isinstance(client_count, Exception):
            client_count = 0
        if isinstance(pricing_stats, Exception):
            pricing_stats = {"hotels": 0, "destinations": 0}
        if isinstance(usage, Exception):
            usage = {}

        # Build result
        result["stats"]["total_quotes"] = quote_count
        result["stats"]["active_clients"] = client_count
        result["stats"]["total_hotels"] = pricing_stats.get("hotels", 0)
        result["stats"]["total_destinations"] = pricing_stats.get("destinations", 0)
        result["recent_quotes"] = quotes
        result["usage"] = usage

        # Cache the result
        _dashboard_cache[cache_key] = {
            "data": result,
            "timestamp": now
        }

        return {"success": True, "data": result, "cached": False}

    except Exception as e:
        logger.error(f"Failed to get aggregated dashboard: {e}")
        return {"success": True, "data": result, "error": str(e)}


# ==================== Export Function ====================

def include_analytics_routers(app):
    """Include analytics routers in the FastAPI app"""
    app.include_router(analytics_router)
    app.include_router(dashboard_router)
