"""
Performance Service - Consultant Performance Tracking

Calculates and tracks consultant performance metrics for leaderboard rankings.
A "converted" booking is defined as:
1. Invoice status = "paid"
2. Quote's check_out_date (departure date) has passed
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from src.tools.supabase_tool import SupabaseTool

logger = logging.getLogger(__name__)


@dataclass
class ConsultantPerformance:
    """Performance metrics for a single consultant"""
    consultant_id: str
    name: str
    email: str
    conversions: int  # Paid invoices with departed clients
    revenue: float  # Total revenue from conversions
    quote_count: int  # Total quotes created
    conversion_rate: float  # Conversions / quotes (percentage)
    rank: int = 0  # Ranking position


class PerformanceService:
    """Service for calculating and tracking consultant performance"""

    VALID_PERIODS = ["week", "month", "quarter", "year", "all"]
    VALID_METRICS = ["conversions", "revenue", "quotes"]

    def __init__(self, supabase_tool: SupabaseTool):
        """
        Initialize performance service.

        Args:
            supabase_tool: Configured SupabaseTool instance for database access
        """
        self.db = supabase_tool
        self.tenant_id = supabase_tool.tenant_id

    def _get_period_start(self, period: str) -> datetime:
        """
        Get the start date for a given period.

        Args:
            period: Time period (week, month, quarter, year, all)

        Returns:
            Start datetime for the period
        """
        now = datetime.utcnow()

        if period == "week":
            # Start of current week (Monday)
            days_since_monday = now.weekday()
            return (now - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif period == "month":
            # Start of current month
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == "quarter":
            # Start of current quarter
            quarter_month = ((now.month - 1) // 3) * 3 + 1
            return now.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == "year":
            # Start of current year
            return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:  # "all"
            # Beginning of time (for all-time stats)
            return datetime(2020, 1, 1)

    def get_consultant_rankings(
        self,
        period: str = "month",
        metric: str = "conversions",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get consultant rankings for the leaderboard.

        Args:
            period: Time period (week, month, quarter, year, all)
            metric: Sort metric (conversions, revenue, quotes)
            limit: Maximum number of results

        Returns:
            List of consultant performance data, ranked by the specified metric
        """
        if period not in self.VALID_PERIODS:
            period = "month"
        if metric not in self.VALID_METRICS:
            metric = "conversions"

        period_start = self._get_period_start(period)
        now = datetime.utcnow()

        try:
            # Get all consultants in the organization
            consultants = self.db.get_organization_users()
            consultant_map = {
                c["id"]: {"name": c["name"], "email": c["email"]}
                for c in consultants
                if c.get("role") == "consultant"
            }

            if not consultant_map:
                return []

            # Get quotes within the period for each consultant
            quotes_result = self.db.client.table("quotes")\
                .select("consultant_id, quote_id, check_out_date, created_at")\
                .eq("tenant_id", self.tenant_id)\
                .gte("created_at", period_start.isoformat())\
                .execute()

            quotes = quotes_result.data or []

            # Get invoices for the quotes
            quote_ids = [q["quote_id"] for q in quotes if q.get("quote_id")]

            if quote_ids:
                invoices_result = self.db.client.table("invoices")\
                    .select("quote_id, status, total_amount, consultant_id")\
                    .eq("tenant_id", self.tenant_id)\
                    .in_("quote_id", quote_ids)\
                    .execute()
                invoices = invoices_result.data or []
            else:
                invoices = []

            # Build quote lookup with check_out_date
            quote_lookup = {}
            for q in quotes:
                if q.get("quote_id"):
                    quote_lookup[q["quote_id"]] = {
                        "consultant_id": q.get("consultant_id"),
                        "check_out_date": q.get("check_out_date")
                    }

            # Calculate performance per consultant
            performance = {}

            # Initialize all consultants with zero stats
            for consultant_id in consultant_map:
                performance[consultant_id] = {
                    "consultant_id": consultant_id,
                    "name": consultant_map[consultant_id]["name"],
                    "email": consultant_map[consultant_id]["email"],
                    "conversions": 0,
                    "revenue": 0.0,
                    "quote_count": 0,
                    "conversion_rate": 0.0
                }

            # Count quotes per consultant
            for quote in quotes:
                consultant_id = quote.get("consultant_id")
                if consultant_id and consultant_id in performance:
                    performance[consultant_id]["quote_count"] += 1

            # Calculate conversions and revenue
            for invoice in invoices:
                quote_id = invoice.get("quote_id")
                quote_info = quote_lookup.get(quote_id, {})

                # Determine consultant (prefer invoice.consultant_id, fallback to quote.consultant_id)
                consultant_id = invoice.get("consultant_id") or quote_info.get("consultant_id")

                if not consultant_id or consultant_id not in performance:
                    continue

                # Check if this is a conversion (paid + departed)
                if invoice.get("status") == "paid":
                    check_out_date_str = quote_info.get("check_out_date")

                    if check_out_date_str:
                        try:
                            # Parse the check_out_date
                            if isinstance(check_out_date_str, str):
                                check_out_date = datetime.fromisoformat(
                                    check_out_date_str.replace("Z", "+00:00")
                                ).replace(tzinfo=None)
                            else:
                                check_out_date = check_out_date_str

                            # Only count as conversion if departure date has passed
                            if check_out_date < now:
                                performance[consultant_id]["conversions"] += 1
                                performance[consultant_id]["revenue"] += float(
                                    invoice.get("total_amount", 0) or 0
                                )
                        except (ValueError, TypeError) as e:
                            logger.debug(f"Could not parse check_out_date: {e}")
                            # If we can't parse the date, still count the conversion
                            performance[consultant_id]["conversions"] += 1
                            performance[consultant_id]["revenue"] += float(
                                invoice.get("total_amount", 0) or 0
                            )

            # Calculate conversion rates
            for consultant_id in performance:
                quote_count = performance[consultant_id]["quote_count"]
                if quote_count > 0:
                    performance[consultant_id]["conversion_rate"] = round(
                        (performance[consultant_id]["conversions"] / quote_count) * 100, 1
                    )

            # Convert to list and sort by metric
            rankings = list(performance.values())

            if metric == "revenue":
                rankings.sort(key=lambda x: (-x["revenue"], -x["conversions"]))
            elif metric == "quotes":
                rankings.sort(key=lambda x: (-x["quote_count"], -x["conversions"]))
            else:  # conversions (default)
                rankings.sort(key=lambda x: (-x["conversions"], -x["revenue"]))

            # Add ranking position
            for i, consultant in enumerate(rankings[:limit]):
                consultant["rank"] = i + 1

            return rankings[:limit]

        except Exception as e:
            logger.error(f"Failed to get consultant rankings: {e}")
            return []

    def get_consultant_performance(
        self,
        consultant_id: str,
        period: str = "month"
    ) -> Optional[Dict[str, Any]]:
        """
        Get performance metrics for a specific consultant.

        Args:
            consultant_id: The consultant's user ID
            period: Time period (week, month, quarter, year, all)

        Returns:
            Performance data for the consultant, including their rank
        """
        rankings = self.get_consultant_rankings(period=period, limit=1000)

        for consultant in rankings:
            if consultant["consultant_id"] == consultant_id:
                return consultant

        return None

    def get_performance_summary(
        self,
        period: str = "month"
    ) -> Dict[str, Any]:
        """
        Get overall performance summary for the organization.

        Args:
            period: Time period (week, month, quarter, year, all)

        Returns:
            Summary statistics including total conversions, revenue, etc.
        """
        rankings = self.get_consultant_rankings(period=period, limit=1000)

        total_conversions = sum(c["conversions"] for c in rankings)
        total_revenue = sum(c["revenue"] for c in rankings)
        total_quotes = sum(c["quote_count"] for c in rankings)
        active_consultants = len([c for c in rankings if c["quote_count"] > 0])

        avg_conversion_rate = 0.0
        if total_quotes > 0:
            avg_conversion_rate = round((total_conversions / total_quotes) * 100, 1)

        return {
            "period": period,
            "total_conversions": total_conversions,
            "total_revenue": total_revenue,
            "total_quotes": total_quotes,
            "active_consultants": active_consultants,
            "avg_conversion_rate": avg_conversion_rate,
            "top_performer": rankings[0] if rankings else None
        }
