"""
Rates API Routes

Provides endpoints for hotel availability search via Travel Platform Rates Engine.
Uses live Juniper data for real-time pricing.

Endpoints:
- GET  /api/v1/rates/health     - Check rates engine availability
- POST /api/v1/rates/hotels/search - Search hotel availability
"""

import asyncio
import logging
from datetime import date
from typing import List, Optional, Any, Dict

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, field_validator

from config.loader import ClientConfig, get_client_config
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
    # Merged profile metadata
    response_format: Optional[str] = None
    aggregation: Optional[Dict[str, Any]] = None
    provider_status: Optional[Dict[str, Any]] = None
    merge_stats: Optional[Dict[str, Any]] = None


def _get_hotel_currency(hotel: dict) -> str:
    """Extract the base currency from a hotel result."""
    if hotel.get("best_rate"):
        cur = hotel["best_rate"].get("currency")
        if cur:
            return cur
    if hotel.get("options"):
        cur = hotel["options"][0].get("currency")
        if cur:
            return cur
    return hotel.get("currency", "ZAR")


async def _apply_currency_conversion(hotels: list, target_currency: str = "ZAR", margin_pct: float = 5.0) -> list:
    """Apply currency conversion to hotels with non-ZAR pricing.

    Handles both merged profile format (all_rates[], best_rate) and
    legacy format (options[]).
    """
    currency_svc = get_currency_service()

    # Pre-collect all unique source currencies and warm the cache
    source_currencies = set()
    for hotel in hotels:
        cur = _get_hotel_currency(hotel)
        if cur and cur.upper() != target_currency.upper():
            source_currencies.add(cur.upper())
    if source_currencies:
        await currency_svc.ensure_rates_cached(source_currencies, target_currency)

    for hotel in hotels:
        # Determine base currency from best_rate, options, or hotel level
        hotel_currency = None
        if hotel.get("best_rate"):
            hotel_currency = hotel["best_rate"].get("currency")
        if not hotel_currency and hotel.get("options"):
            hotel_currency = hotel["options"][0].get("currency")
        if not hotel_currency:
            hotel_currency = hotel.get("currency", "ZAR")

        # Convert cheapest_price
        if hotel_currency.upper() != target_currency.upper() and hotel.get("cheapest_price"):
            conversion = await currency_svc.convert(
                hotel["cheapest_price"], hotel_currency, target_currency, margin_pct
            )
            hotel["display_price_zar"] = conversion["amount"]
            hotel["original_currency"] = conversion["original_currency"]
            hotel["exchange_rate"] = conversion["rate"]

        # Convert best_rate if present
        best_rate = hotel.get("best_rate")
        if best_rate:
            rate_currency = best_rate.get("currency", hotel_currency)
            if rate_currency.upper() != target_currency.upper():
                if best_rate.get("rate_per_night") and not best_rate.get("rate_per_night_zar"):
                    conv = await currency_svc.convert(best_rate["rate_per_night"], rate_currency, target_currency, margin_pct)
                    best_rate["rate_per_night_zar"] = conv["amount"]

        # Convert all_rates[] if present
        for rate in hotel.get("all_rates", []):
            rate_currency = rate.get("currency", hotel_currency)
            if rate_currency.upper() != target_currency.upper():
                if rate.get("rate_per_night") and not rate.get("rate_per_night_zar"):
                    conv = await currency_svc.convert(rate["rate_per_night"], rate_currency, target_currency, margin_pct)
                    rate["rate_per_night_zar"] = conv["amount"]

        # Convert options[] (backward compat)
        for opt in hotel.get("options", []):
            opt_currency = opt.get("currency", hotel_currency)
            if opt_currency.upper() != target_currency.upper():
                if opt.get("price_total"):
                    conv = await currency_svc.convert(opt["price_total"], opt_currency, target_currency, margin_pct)
                    opt["price_total_zar"] = conv["amount"]
                if opt.get("price_per_night") and not opt.get("price_per_night_zar"):
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
            children=len(request.children_ages),
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
    destination: str = Query(..., description="Destination name"),
    check_in: date = Query(..., description="Check-in date (YYYY-MM-DD)"),
    check_out: date = Query(..., description="Check-out date (YYYY-MM-DD)"),
    adults: int = Query(default=2, ge=1, le=20, description="Number of adults"),
    children: int = Query(default=0, ge=0, le=10, description="Number of children"),
    config: ClientConfig = Depends(get_client_config),
) -> Dict[str, Any]:
    """
    Multi-provider aggregated hotel search.

    Returns hotels from multiple providers (HotelBeds, Juniper, Hummingbird, RTTC)
    via the Zorah Travel Platform aggregation endpoint.

    Falls back to BigQuery hotel_rates pricing data when the Rates Engine
    returns 0 results for a destination.
    """
    nights = (check_out - check_in).days

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

        # If Cloud Run returned hotels, return them
        if result.get("hotels"):
            return result

        # Fallback: query BigQuery hotel_rates for this destination
        logger.info(f"Aggregated search returned 0 hotels for {destination}, trying BigQuery fallback")
        bq_hotels = await _bigquery_hotel_fallback(config, destination, check_in, check_out, nights)
        if bq_hotels:
            return {
                "success": True,
                "destination": destination,
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "nights": nights,
                "total_hotels": len(bq_hotels),
                "hotels": bq_hotels,
                "aggregation": {"source": "bigquery_pricing"},
                "search_time_seconds": 0,
            }

        return result  # Return the original (empty) result

    except Exception as e:
        logger.error(f"Aggregated hotel search failed: {e}", exc_info=True)
        return {
            "success": False,
            "total_hotels": 0,
            "hotels": [],
            "error": str(e),
        }


async def _bigquery_hotel_fallback(
    config: ClientConfig,
    destination: str,
    check_in: date,
    check_out: date,
    nights: int,
) -> list:
    """Query BigQuery hotel_rates for hotels in a destination as fallback."""
    try:
        from src.api.pricing_routes import get_bigquery_client_async
        bq_client = await get_bigquery_client_async(config)
        if not bq_client:
            return []

        # Try multiple destination name formats to handle code vs display name
        # e.g., "victoria-falls" → also try "Victoria Falls"
        dest_display = destination.replace("-", " ").title()

        query = f"""
        SELECT
            hotel_name,
            hotel_rating,
            destination,
            room_type,
            meal_plan,
            MIN(total_7nights_pps) as min_price_pps,
            MIN(total_7nights_single) as min_price_single,
            MIN(total_7nights_child) as min_price_child
        FROM `{config.gcp_project_id}.{config.shared_pricing_dataset}.hotel_rates`
        WHERE (UPPER(destination) = UPPER(@destination)
               OR UPPER(destination) = UPPER(@dest_display))
          AND is_active = TRUE
        GROUP BY hotel_name, hotel_rating, destination, room_type, meal_plan
        ORDER BY hotel_name, min_price_pps
        """

        from google.cloud import bigquery
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("destination", "STRING", destination),
                bigquery.ScalarQueryParameter("dest_display", "STRING", dest_display),
            ]
        )

        rows = await asyncio.to_thread(
            lambda: list(bq_client.query(query, job_config=job_config).result())
        )

        if not rows:
            return []

        # Group rows by hotel_name to build profiles
        hotel_map = {}
        for row in rows:
            name = row.hotel_name
            if name not in hotel_map:
                hotel_map[name] = {
                    "hotel_id": f"bq_{name.lower().replace(' ', '_')[:30]}",
                    "hotel_name": name,
                    "star_rating": int(row.hotel_rating) if row.hotel_rating else None,
                    "stars": int(row.hotel_rating) if row.hotel_rating else None,
                    "destination": row.destination,
                    "zone": None,
                    "image_url": None,
                    "cheapest_price": None,
                    "cheapest_meal_plan": None,
                    "best_rate": None,
                    "all_rates": [],
                    "sources": ["bigquery"],
                    "source": "bigquery",
                    "options": [],
                }

            price_pps = float(row.min_price_pps) if row.min_price_pps else 0
            # Scale 7-night price to per-night
            rate_per_night = round(price_pps / 7, 2) if price_pps else 0

            option = {
                "room_type": row.room_type or "Standard Room",
                "meal_plan": row.meal_plan or "",
                "price_total": round(rate_per_night * nights, 2),
                "price_per_night": rate_per_night,
                "rate_per_night_zar": rate_per_night,
                "currency": "ZAR",
                "source": "bigquery",
                "provider": "bigquery",
            }
            hotel_map[name]["options"].append(option)
            hotel_map[name]["all_rates"].append(option)

            # Track cheapest
            current_cheapest = hotel_map[name]["cheapest_price"]
            if rate_per_night > 0 and (current_cheapest is None or rate_per_night < current_cheapest):
                hotel_map[name]["cheapest_price"] = rate_per_night
                hotel_map[name]["cheapest_meal_plan"] = row.meal_plan
                hotel_map[name]["best_rate"] = {
                    "room_type": row.room_type or "Standard Room",
                    "meal_plan": row.meal_plan or "",
                    "rate_per_night": rate_per_night,
                    "rate_per_night_zar": rate_per_night,
                    "currency": "ZAR",
                    "source": "bigquery",
                }

        hotels = [h for h in hotel_map.values() if h["cheapest_price"] and h["cheapest_price"] > 0]
        logger.info(f"BigQuery fallback found {len(hotels)} hotels for {destination}")
        return hotels

    except Exception as e:
        logger.warning(f"BigQuery hotel fallback failed for {destination}: {e}")
        return []


@rates_router.get("/destinations")
def list_destinations() -> Dict[str, Any]:
    """
    List available destinations for hotel search.

    Returns the destinations supported by the Rates Engine.
    """
    # Destinations supported by the Rates Engine (Juniper + aggregated providers)
    destinations = [
        {"code": "zanzibar", "name": "Zanzibar", "country": "Tanzania"},
        {"code": "mauritius", "name": "Mauritius", "country": "Mauritius"},
        {"code": "maldives", "name": "Maldives", "country": "Maldives"},
        {"code": "kenya", "name": "Kenya", "country": "Kenya"},
        {"code": "seychelles", "name": "Seychelles", "country": "Seychelles"},
        {"code": "cape-town", "name": "Cape Town", "country": "South Africa"},
        {"code": "victoria-falls", "name": "Victoria Falls", "country": "Zimbabwe/Zambia"},
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
