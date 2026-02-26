"""
Rates API Routes

Provides endpoints for hotel availability search via Travel Platform Rates Engine.
Uses live Juniper data for real-time pricing.

Endpoints:
- GET  /api/v1/rates/health     - Check rates engine availability
- POST /api/v1/rates/hotels/search - Search hotel availability
"""

import logging
from datetime import date
from typing import List, Optional, Any, Dict

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, field_validator

from src.middleware.auth_middleware import get_current_user_optional
from src.services.travel_platform_rates_client import get_travel_platform_rates_client
from src.services.currency_service import get_currency_service

logger = logging.getLogger(__name__)

rates_router = APIRouter(prefix="/api/v1/rates", tags=["Rates"])


# ============================================================
# PYDANTIC MODELS
# ============================================================

class HotelSearchRequest(BaseModel):
    """Request model for hotel availability search"""
    destination: str = Field(..., description="Destination name (e.g., 'zanzibar', 'mauritius')")
    check_in: date = Field(..., description="Check-in date (YYYY-MM-DD)")
    check_out: date = Field(..., description="Check-out date (YYYY-MM-DD)")
    adults: int = Field(default=2, ge=1, le=10, description="Number of adults")
    children_ages: List[int] = Field(default=[], description="Ages of children")
    max_hotels: int = Field(default=50, ge=1, le=200, description="Maximum hotels to return")

    @field_validator('destination')
    @classmethod
    def validate_destination(cls, v: str) -> str:
        """Normalize destination name"""
        return v.strip().lower()

    @field_validator('check_out')
    @classmethod
    def validate_dates(cls, v: date, info) -> date:
        """Validate check_out is after check_in"""
        check_in = info.data.get('check_in')
        if check_in and v <= check_in:
            raise ValueError('check_out must be after check_in')
        return v


class HotelSearchByNamesRequest(BaseModel):
    """Request model for hotel search by specific names"""
    destination: str = Field(..., description="Destination name")
    hotel_names: List[str] = Field(..., min_length=1, max_length=20, description="Hotel names to search")
    check_in: date = Field(..., description="Check-in date")
    check_out: date = Field(..., description="Check-out date")
    adults: int = Field(default=2, ge=1, le=10)
    children_ages: List[int] = Field(default=[])


class HotelOption(BaseModel):
    """Individual room/rate option within a hotel"""
    room_type: str
    meal_plan: str
    price_total: float
    price_per_night: float
    currency: str
    availability: str
    occupancy: int
    # Enrichment fields (optional - render only when upstream provides them)
    room_description: Optional[str] = None
    bed_type: Optional[str] = None
    room_size: Optional[str] = None
    view: Optional[str] = None
    cancellation_policy: Optional[str] = None
    refundable: Optional[bool] = None
    provider: Optional[str] = None
    rate_code: Optional[str] = None


class HotelResult(BaseModel):
    """Hotel search result"""
    hotel_id: str
    hotel_name: str
    stars: Optional[int] = None
    destination: Optional[str] = None
    zone: Optional[str] = None
    image_url: Optional[str] = None
    options: List[Dict[str, Any]] = []
    cheapest_price: Optional[float] = None
    cheapest_meal_plan: Optional[str] = None
    # Enrichment fields (optional - render only when upstream provides them)
    description: Optional[str] = None
    amenities: Optional[List[str]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None


class HotelSearchResponse(BaseModel):
    """Response model for hotel search"""
    success: bool
    destination: Optional[str] = None
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    nights: Optional[int] = None
    total_hotels: int = 0
    hotels: List[Dict[str, Any]] = []
    search_time_seconds: Optional[float] = None
    error: Optional[str] = None


async def _apply_currency_conversion(hotels: list, target_currency: str = "ZAR", margin_pct: float = 5.0) -> list:
    """Apply currency conversion to hotels with non-ZAR pricing."""
    currency_svc = get_currency_service()
    for hotel in hotels:
        # Convert cheapest_price
        hotel_currency = None
        if hotel.get("options"):
            hotel_currency = hotel["options"][0].get("currency")
        if not hotel_currency:
            hotel_currency = hotel.get("currency", "ZAR")

        if hotel_currency.upper() != target_currency.upper() and hotel.get("cheapest_price"):
            conversion = await currency_svc.convert(
                hotel["cheapest_price"], hotel_currency, target_currency, margin_pct
            )
            hotel["display_price_zar"] = conversion["amount"]
            hotel["original_currency"] = conversion["original_currency"]
            hotel["exchange_rate"] = conversion["rate"]

        # Convert option prices
        for opt in hotel.get("options", []):
            opt_currency = opt.get("currency", hotel_currency)
            if opt_currency.upper() != target_currency.upper():
                if opt.get("price_total"):
                    conv = await currency_svc.convert(opt["price_total"], opt_currency, target_currency, margin_pct)
                    opt["price_total_zar"] = conv["amount"]
                if opt.get("price_per_night"):
                    conv = await currency_svc.convert(opt["price_per_night"], opt_currency, target_currency, margin_pct)
                    opt["price_per_night_zar"] = conv["amount"]
    return hotels


# ============================================================
# ENDPOINTS
# ============================================================

@rates_router.get("/health")
async def rates_health(
    user: Optional[dict] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Check Rates Engine availability.

    Returns:
        - available: Whether the rates engine is responding
        - status: Client configuration details
    """
    try:
        client = get_travel_platform_rates_client()
        available = await client.is_available()

        return {
            "success": True,
            "available": available,
            "status": client.get_status()
        }
    except Exception as e:
        logger.error(f"Rates health check failed: {e}")
        return {
            "success": False,
            "available": False,
            "error": str(e)
        }


@rates_router.post("/hotels/search", response_model=HotelSearchResponse)
async def search_hotels(request: HotelSearchRequest) -> HotelSearchResponse:
    """
    Search hotel availability using live Juniper data.

    This endpoint connects to the Travel Platform Rates Engine for real-time
    hotel availability and pricing.

    **Performance Notes:**
    - Response time: 30-60 seconds with max_hotels=50
    - Larger max_hotels values increase response time
    - Consider showing a loading state in the UI

    **Example Request:**
    ```json
    {
        "destination": "zanzibar",
        "check_in": "2026-03-15",
        "check_out": "2026-03-20",
        "adults": 2,
        "children_ages": [],
        "max_hotels": 50
    }
    ```

    Returns:
        Hotel options with room types, meal plans, and pricing
    """
    try:
        client = get_travel_platform_rates_client()

        result = await client.search_hotels(
            destination=request.destination,
            check_in=request.check_in,
            check_out=request.check_out,
            adults=request.adults,
            children_ages=request.children_ages,
            max_hotels=request.max_hotels
        )

        # Apply currency conversion for non-ZAR results
        if result.get("hotels"):
            await _apply_currency_conversion(result["hotels"])

        return HotelSearchResponse(**result)

    except Exception as e:
        logger.error(f"Hotel search failed: {e}", exc_info=True)
        return HotelSearchResponse(
            success=False,
            total_hotels=0,
            hotels=[],
            error=str(e)
        )


@rates_router.post("/hotels/search-by-names", response_model=HotelSearchResponse)
async def search_hotels_by_names(request: HotelSearchByNamesRequest) -> Dict[str, Any]:
    """
    Search specific hotels by name.

    **Note:** This endpoint requires hotel name mapping files to be configured
    in the Travel Platform. Use `/hotels/search` as the primary method until
    mapping is ready.

    This is faster than full search when you know specific hotels to price
    (e.g., from RAG recommendations).

    **Performance Notes:**
    - Response time: 5-10 seconds for 5-10 hotels
    - Much faster than full search

    Returns:
        Matched hotels with pricing, plus list of unmatched hotel names
    """
    try:
        client = get_travel_platform_rates_client()

        result = await client.search_hotels_by_names(
            destination=request.destination,
            hotel_names=request.hotel_names,
            check_in=request.check_in,
            check_out=request.check_out,
            adults=request.adults,
            children_ages=request.children_ages
        )

        return result

    except Exception as e:
        logger.error(f"Hotel search by names failed: {e}", exc_info=True)
        return {
            "success": False,
            "hotels": [],
            "unmatched_hotels": request.hotel_names,
            "error": str(e)
        }


@rates_router.get("/hotels/search/aggregated")
async def search_hotels_aggregated(
    destination: str,
    check_in: date,
    check_out: date,
    adults: int = 2,
    children: int = 0,
) -> Dict[str, Any]:
    """
    Multi-provider aggregated hotel search.

    Returns hotels from multiple providers (HotelBeds, Juniper, Hummingbird, RTTC)
    via the Zorah Travel Platform aggregation endpoint.

    Uses the same response format as the standard hotel search so the frontend
    can use it interchangeably.
    """
    try:
        client = get_travel_platform_rates_client()
        result = await client.search_hotels_aggregated(
            destination=destination,
            check_in=check_in,
            check_out=check_out,
            adults=adults,
            children=children,
        )

        # Apply currency conversion for non-ZAR results
        if result.get("hotels"):
            await _apply_currency_conversion(result["hotels"])

        return result

    except Exception as e:
        logger.error(f"Aggregated hotel search failed: {e}", exc_info=True)
        return {
            "success": False,
            "total_hotels": 0,
            "hotels": [],
            "error": str(e),
        }


@rates_router.get("/destinations")
def list_destinations() -> Dict[str, Any]:
    """
    List available destinations for hotel search.

    Returns the destinations supported by the Rates Engine.
    """
    # Only destinations with confirmed Juniper codes in the Rates Engine
    destinations = [
        {"code": "zanzibar", "name": "Zanzibar", "country": "Tanzania"},
        {"code": "mauritius", "name": "Mauritius", "country": "Mauritius"},
        {"code": "maldives", "name": "Maldives", "country": "Maldives"},
        {"code": "kenya", "name": "Kenya", "country": "Kenya"},
    ]

    return {
        "success": True,
        "destinations": destinations,
        "count": len(destinations)
    }


# ============================================================
# ROUTER REGISTRATION
# ============================================================

def include_rates_router(app: Any) -> None:
    """Include rates router in the FastAPI app"""
    app.include_router(rates_router)
