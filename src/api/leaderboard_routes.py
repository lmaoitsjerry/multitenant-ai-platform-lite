"""
Leaderboard API Routes

Endpoints for consultant performance leaderboard and rankings.
"""

import os
import logging
from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel
from typing import Optional, List

from src.middleware.auth_middleware import get_current_user, UserContext
from src.tools.supabase_tool import SupabaseTool
from src.services.performance_service import PerformanceService
from config.loader import get_config

logger = logging.getLogger(__name__)

leaderboard_router = APIRouter(prefix="/api/v1/leaderboard", tags=["Leaderboard"])


# ==================== Pydantic Models ====================

class ConsultantRankingResponse(BaseModel):
    rank: int
    consultant_id: str
    name: str
    email: str
    conversions: int
    revenue: float
    quote_count: int
    conversion_rate: float


class LeaderboardResponse(BaseModel):
    success: bool
    period: str
    metric: str
    rankings: List[ConsultantRankingResponse]
    total_consultants: int


class MyPerformanceResponse(BaseModel):
    success: bool
    period: str
    rank: int
    name: str
    conversions: int
    revenue: float
    quote_count: int
    conversion_rate: float
    total_consultants: int


class PerformanceSummaryResponse(BaseModel):
    success: bool
    period: str
    total_conversions: int
    total_revenue: float
    total_quotes: int
    active_consultants: int
    avg_conversion_rate: float
    top_performer: Optional[ConsultantRankingResponse] = None


# ==================== Dependencies ====================

def get_supabase_tool(x_client_id: str = Header(None, alias="X-Client-ID")) -> SupabaseTool:
    """Get SupabaseTool instance for the tenant"""
    client_id = x_client_id or os.getenv("CLIENT_ID", "africastay")

    try:
        config = get_config(client_id)
        return SupabaseTool(config)
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail=f"Unknown client: {client_id}")


def get_performance_service(db: SupabaseTool = Depends(get_supabase_tool)) -> PerformanceService:
    """Get PerformanceService instance"""
    return PerformanceService(db)


# ==================== Endpoints ====================

@leaderboard_router.get("/rankings", response_model=LeaderboardResponse)
async def get_rankings(
    request: Request,
    period: str = "month",
    metric: str = "conversions",
    limit: int = 50,
    user: UserContext = Depends(get_current_user),
    performance_service: PerformanceService = Depends(get_performance_service)
):
    """
    Get consultant rankings for the leaderboard.

    Args:
        period: Time period (week, month, quarter, year, all)
        metric: Sort by metric (conversions, revenue, quotes)
        limit: Maximum results (default 50)

    Returns:
        List of consultants ranked by the specified metric
    """
    try:
        # Validate period
        valid_periods = ["week", "month", "quarter", "year", "all"]
        if period not in valid_periods:
            period = "month"

        # Validate metric
        valid_metrics = ["conversions", "revenue", "quotes"]
        if metric not in valid_metrics:
            metric = "conversions"

        rankings = performance_service.get_consultant_rankings(
            period=period,
            metric=metric,
            limit=limit
        )

        return LeaderboardResponse(
            success=True,
            period=period,
            metric=metric,
            rankings=[
                ConsultantRankingResponse(
                    rank=r["rank"],
                    consultant_id=r["consultant_id"],
                    name=r["name"],
                    email=r["email"],
                    conversions=r["conversions"],
                    revenue=r["revenue"],
                    quote_count=r["quote_count"],
                    conversion_rate=r["conversion_rate"]
                )
                for r in rankings
            ],
            total_consultants=len(rankings)
        )
    except Exception as e:
        logger.error(f"Error getting rankings: {e}")
        raise HTTPException(status_code=500, detail="Failed to get rankings")


@leaderboard_router.get("/me", response_model=MyPerformanceResponse)
async def get_my_performance(
    request: Request,
    period: str = "month",
    user: UserContext = Depends(get_current_user),
    performance_service: PerformanceService = Depends(get_performance_service)
):
    """
    Get the current user's performance and ranking.

    Args:
        period: Time period (week, month, quarter, year, all)

    Returns:
        Current user's performance data including rank
    """
    try:
        # Validate period
        valid_periods = ["week", "month", "quarter", "year", "all"]
        if period not in valid_periods:
            period = "month"

        # Get all rankings to determine position
        all_rankings = performance_service.get_consultant_rankings(period=period, limit=1000)
        total_consultants = len(all_rankings)

        # Find current user's performance
        my_performance = None
        for r in all_rankings:
            if r["consultant_id"] == user.user_id:
                my_performance = r
                break

        if not my_performance:
            # User not in rankings (might be admin or no data yet)
            return MyPerformanceResponse(
                success=True,
                period=period,
                rank=0,
                name=user.name,
                conversions=0,
                revenue=0.0,
                quote_count=0,
                conversion_rate=0.0,
                total_consultants=total_consultants
            )

        return MyPerformanceResponse(
            success=True,
            period=period,
            rank=my_performance["rank"],
            name=my_performance["name"],
            conversions=my_performance["conversions"],
            revenue=my_performance["revenue"],
            quote_count=my_performance["quote_count"],
            conversion_rate=my_performance["conversion_rate"],
            total_consultants=total_consultants
        )
    except Exception as e:
        logger.error(f"Error getting my performance: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance")


@leaderboard_router.get("/summary", response_model=PerformanceSummaryResponse)
async def get_performance_summary(
    request: Request,
    period: str = "month",
    user: UserContext = Depends(get_current_user),
    performance_service: PerformanceService = Depends(get_performance_service)
):
    """
    Get overall organization performance summary.

    Admin-focused view showing total metrics across all consultants.

    Args:
        period: Time period (week, month, quarter, year, all)

    Returns:
        Organization-wide performance summary
    """
    try:
        # Validate period
        valid_periods = ["week", "month", "quarter", "year", "all"]
        if period not in valid_periods:
            period = "month"

        summary = performance_service.get_performance_summary(period=period)

        top_performer = None
        if summary.get("top_performer"):
            tp = summary["top_performer"]
            top_performer = ConsultantRankingResponse(
                rank=tp["rank"],
                consultant_id=tp["consultant_id"],
                name=tp["name"],
                email=tp["email"],
                conversions=tp["conversions"],
                revenue=tp["revenue"],
                quote_count=tp["quote_count"],
                conversion_rate=tp["conversion_rate"]
            )

        return PerformanceSummaryResponse(
            success=True,
            period=summary["period"],
            total_conversions=summary["total_conversions"],
            total_revenue=summary["total_revenue"],
            total_quotes=summary["total_quotes"],
            active_consultants=summary["active_consultants"],
            avg_conversion_rate=summary["avg_conversion_rate"],
            top_performer=top_performer
        )
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get summary")


@leaderboard_router.get("/consultant/{consultant_id}")
async def get_consultant_performance(
    consultant_id: str,
    request: Request,
    period: str = "month",
    user: UserContext = Depends(get_current_user),
    performance_service: PerformanceService = Depends(get_performance_service)
):
    """
    Get performance for a specific consultant.

    Args:
        consultant_id: The consultant's user ID
        period: Time period (week, month, quarter, year, all)

    Returns:
        Consultant's performance data
    """
    try:
        # Validate period
        valid_periods = ["week", "month", "quarter", "year", "all"]
        if period not in valid_periods:
            period = "month"

        performance = performance_service.get_consultant_performance(
            consultant_id=consultant_id,
            period=period
        )

        if not performance:
            raise HTTPException(status_code=404, detail="Consultant not found")

        return {
            "success": True,
            "period": period,
            "consultant": ConsultantRankingResponse(
                rank=performance["rank"],
                consultant_id=performance["consultant_id"],
                name=performance["name"],
                email=performance["email"],
                conversions=performance["conversions"],
                revenue=performance["revenue"],
                quote_count=performance["quote_count"],
                conversion_rate=performance["conversion_rate"]
            )
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting consultant performance: {e}")
        raise HTTPException(status_code=500, detail="Failed to get consultant performance")
