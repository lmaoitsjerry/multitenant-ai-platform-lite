"""
HotelBeds API Routes

Provides endpoints to access HotelBeds data via the Zorah Travel Platform:
- Hotels: Global hotel inventory with real-time availability
- Activities: Tours, excursions, and experiences
- Transfers: Airport transfers and ground transportation

Endpoints:
- GET  /api/v1/hotelbeds/health              - Check HotelBeds API status
- GET  /api/v1/hotelbeds/hotels/search       - Search hotels
- POST /api/v1/hotelbeds/hotels/search       - Search hotels (with children)
- GET  /api/v1/hotelbeds/activities/search   - Search activities
- GET  /api/v1/hotelbeds/transfers/search    - Search transfers
"""

import logging
from datetime import date
from typing import List, Optional, Any, Dict

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from src.services.travel_platform_rates_client import get_travel_platform_rates_client

logger = logging.getLogger(__name__)

hotelbeds_router = APIRouter(prefix="/api/v1/hotelbeds", tags=["HotelBeds"])


# ============================================================
# PYDANTIC MODELS
# ============================================================

class HotelSearchRequest(BaseModel):
    """Request model for hotel search with children."""
    destination: str = Field(..., description="Destination name (e.g., 'zanzibar', 'mauritius')")
    check_in: date = Field(..., description="Check-in date (YYYY-MM-DD)")
    check_out: date = Field(..., description="Check-out date (YYYY-MM-DD)")
    adults: int = Field(default=2, ge=1, le=10, description="Number of adults")
    children_ages: List[int] = Field(default=[], description="Ages of children")
    max_hotels: int = Field(default=50, ge=1, le=200, description="Maximum hotels to return")

    @field_validator('destination')
    @classmethod
    def validate_destination(cls, v: str) -> str:
        """Normalize destination name."""
        return v.strip().lower()

    @field_validator('check_out')
    @classmethod
    def validate_dates(cls, v: date, info) -> date:
        """Validate check_out is after check_in."""
        check_in = info.data.get('check_in')
        if check_in and v <= check_in:
            raise ValueError('check_out must be after check_in')
        return v


class ActivitySearchRequest(BaseModel):
    """Request model for activity search."""
    destination: str = Field(..., description="Destination name")
    participants: int = Field(default=2, ge=1, le=50, description="Number of participants")

    @field_validator('destination')
    @classmethod
    def validate_destination(cls, v: str) -> str:
        return v.strip().lower()


class CheckRatesRequest(BaseModel):
    """Request model for pre-booking rate check."""
    rate_key: str = Field(..., description="Rate key from hotel search results")
    rooms: int = Field(default=1, ge=1, le=10, description="Number of rooms")


class TransferSearchRequest(BaseModel):
    """Request model for transfer search."""
    route: str = Field(..., description="Route description (e.g., 'Zanzibar Airport to Stone Town')")
    transfer_date: date = Field(..., description="Transfer date (YYYY-MM-DD)")
    passengers: int = Field(default=2, ge=1, le=20, description="Number of passengers")


# ============================================================
# ENDPOINTS
# ============================================================

@hotelbeds_router.get("/health")
async def hotelbeds_health() -> Dict[str, Any]:
    """
    Check travel services API health status.

    Returns:
        - available: Whether the API is reachable
        - status: Client configuration details
    """
    client = get_travel_platform_rates_client()
    available = await client.is_available()
    return {
        "success": True,
        "available": available,
        "status": client.get_status(),
    }


@hotelbeds_router.get("/status")
def hotelbeds_status() -> Dict[str, Any]:
    """
    Get detailed client status.

    Returns client configuration and circuit breaker state.
    """
    client = get_travel_platform_rates_client()
    return {
        "success": True,
        "client": client.get_status()
    }


@hotelbeds_router.get("/hotels/search")
async def search_hotels_get(
    destination: str = Query(..., description="Destination name"),
    check_in: date = Query(..., description="Check-in date"),
    check_out: date = Query(..., description="Check-out date"),
    adults: int = Query(default=2, ge=1, le=10, description="Number of adults"),
    max_hotels: int = Query(default=50, ge=1, le=200, description="Maximum hotels to return")
) -> Dict[str, Any]:
    """
    Search hotels via aggregated multi-provider search (GET method).

    Delegates to TravelPlatformRatesClient for unified 4-provider search.
    """
    if check_out <= check_in:
        raise HTTPException(status_code=400, detail="Check-out must be after check-in")

    client = get_travel_platform_rates_client()

    result = await client.search_hotels_aggregated(
        destination=destination.lower(),
        check_in=check_in,
        check_out=check_out,
        adults=adults,
    )

    if not result.get("success"):
        return {
            "success": False,
            "source": "aggregated",
            "destination": destination,
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "hotels": [],
            "count": 0,
            "error": result.get("error", "Search failed")
        }

    return result


@hotelbeds_router.post("/hotels/search")
async def search_hotels_post(request: HotelSearchRequest) -> Dict[str, Any]:
    """
    Search hotels via aggregated multi-provider search (POST method).

    Delegates to TravelPlatformRatesClient for unified 4-provider search.
    """
    client = get_travel_platform_rates_client()

    result = await client.search_hotels_aggregated(
        destination=request.destination,
        check_in=request.check_in,
        check_out=request.check_out,
        adults=request.adults,
        children=len(request.children_ages) if request.children_ages else 0,
    )

    if not result.get("success"):
        return {
            "success": False,
            "source": "aggregated",
            "destination": request.destination,
            "check_in": request.check_in.isoformat(),
            "check_out": request.check_out.isoformat(),
            "hotels": [],
            "count": 0,
            "error": result.get("error", "Search failed")
        }

    return result


@hotelbeds_router.get("/activities/search")
async def search_activities(
    destination: str = Query(..., description="Destination name"),
    participants: int = Query(default=2, ge=1, le=50, description="Number of participants")
) -> Dict[str, Any]:
    """
    Search activities via unified Cloud Run endpoint.

    Returns tours, excursions, and experiences available at the destination.
    """
    client = get_travel_platform_rates_client()

    result = await client.search_activities(
        destination=destination.lower(),
        participants=participants,
    )

    if not result.get("success"):
        return {
            "success": False,
            "source": "unified",
            "destination": destination,
            "participants": participants,
            "activities": [],
            "count": 0,
            "error": result.get("error", "Search failed")
        }

    return result


@hotelbeds_router.post("/activities/search")
async def search_activities_post(request: ActivitySearchRequest) -> Dict[str, Any]:
    """
    Search activities via unified Cloud Run endpoint (POST method).
    """
    client = get_travel_platform_rates_client()

    result = await client.search_activities(
        destination=request.destination,
        participants=request.participants,
    )

    if not result.get("success"):
        return {
            "success": False,
            "source": "unified",
            "destination": request.destination,
            "participants": request.participants,
            "activities": [],
            "count": 0,
            "error": result.get("error", "Search failed")
        }

    return result


@hotelbeds_router.get("/transfers/search")
async def search_transfers(
    route: str = Query("", description="Route description (legacy compat)"),
    date: date = Query(..., description="Transfer date"),
    passengers: int = Query(default=2, ge=1, le=20, description="Number of passengers"),
    from_code: Optional[str] = Query(None, description="Origin IATA code"),
    to_code: Optional[str] = Query(None, description="Destination IATA code"),
) -> Dict[str, Any]:
    """
    Search transfers via unified Cloud Run endpoint.

    Returns airport transfers and ground transportation options.
    """
    client = get_travel_platform_rates_client()

    # Use from_code/to_code if provided, otherwise extract from route
    origin = from_code or ""
    dest = to_code or ""

    result = await client.search_transfers(
        from_code=origin,
        to_code=dest,
        transfer_date=date.isoformat(),
        passengers=passengers,
    )

    if not result.get("success"):
        return {
            "success": False,
            "source": "unified",
            "route": route,
            "date": date.isoformat(),
            "passengers": passengers,
            "transfers": [],
            "count": 0,
            "error": result.get("error", "Search failed")
        }

    return result


@hotelbeds_router.post("/transfers/search")
async def search_transfers_post(request: TransferSearchRequest) -> Dict[str, Any]:
    """
    Search transfers via unified Cloud Run endpoint (POST method).
    """
    client = get_travel_platform_rates_client()

    result = await client.search_transfers(
        from_code="",
        to_code="",
        transfer_date=request.transfer_date.isoformat(),
        passengers=request.passengers,
    )

    if not result.get("success"):
        return {
            "success": False,
            "source": "unified",
            "route": request.route,
            "date": request.transfer_date.isoformat(),
            "passengers": request.passengers,
            "transfers": [],
            "count": 0,
            "error": result.get("error", "Search failed")
        }

    return result


# ============================================================
# ROUTER REGISTRATION
# ============================================================

def include_hotelbeds_router(app: Any) -> None:
    """Include HotelBeds router in the FastAPI app."""
    app.include_router(hotelbeds_router)
