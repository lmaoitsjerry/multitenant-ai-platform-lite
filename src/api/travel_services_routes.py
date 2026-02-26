"""
Travel Services API Routes

Provides endpoints for flights, transfers, and activities data.
Hotels are handled separately by rates_routes.py (live Juniper data).

Endpoints:
- GET  /api/v1/travel/flights          - List available flights
- GET  /api/v1/travel/flights/search   - Search flights by destination
- GET  /api/v1/travel/transfers        - List transfer prices
- GET  /api/v1/travel/transfers/search - Search transfers by destination
- GET  /api/v1/travel/activities       - List activities/excursions
- GET  /api/v1/travel/activities/search - Search activities by destination
"""

import logging
import asyncio
import time
from typing import List, Optional, Dict, Any, Tuple
from datetime import date

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from config.loader import ClientConfig
from src.api.dependencies import get_client_config

logger = logging.getLogger(__name__)

# ============================================================
# FLIGHT SEARCH DEDUP CACHE (single-flight pattern)
# ============================================================
# Prevents duplicate RTTC requests for the same route.
# Uses asyncio.Lock per cache key so concurrent requests coalesce.

_flight_cache: Dict[str, Tuple[float, dict]] = {}
_flight_locks: Dict[str, asyncio.Lock] = {}
FLIGHT_CACHE_TTL = 300  # 5 minutes


async def get_flights_cached(cache_key: str, fetcher):
    """Single-flight pattern: only one request per cache key at a time."""
    # Fast path: cache hit
    if cache_key in _flight_cache:
        ts, data = _flight_cache[cache_key]
        if time.time() - ts < FLIGHT_CACHE_TTL:
            logger.info(f"Flight cache hit for {cache_key}")
            return data

    # Slow path: acquire lock (coalescing)
    lock = _flight_locks.setdefault(cache_key, asyncio.Lock())
    async with lock:
        # Double-check after acquiring lock
        if cache_key in _flight_cache:
            ts, data = _flight_cache[cache_key]
            if time.time() - ts < FLIGHT_CACHE_TTL:
                return data
        result = await fetcher()
        _flight_cache[cache_key] = (time.time(), result)
        return result

travel_router = APIRouter(prefix="/api/v1/travel", tags=["Travel Services"])


# ============================================================
# PYDANTIC MODELS
# ============================================================

class FlightResult(BaseModel):
    """Flight search result"""
    destination: str
    departure_date: Optional[str] = None
    return_date: Optional[str] = None
    price_per_person: float
    airline: Optional[str] = None
    currency: str = "ZAR"


class FlightSearchResponse(BaseModel):
    """Response model for flight search"""
    success: bool
    destination: Optional[str] = None
    total_flights: int = 0
    flights: List[Dict[str, Any]] = []
    outbound_flights: List[Dict[str, Any]] = []
    return_flights: List[Dict[str, Any]] = []
    source: Optional[str] = None  # "rttc", "rttc_direct", "platform", or "bigquery"
    outbound: Optional[Dict[str, Any]] = None
    return_leg: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class TransferResult(BaseModel):
    """Transfer pricing result"""
    destination: str
    hotel_name: Optional[str] = None
    transfers_adult: float
    transfers_child: float
    currency: str = "ZAR"


class TransferSearchResponse(BaseModel):
    """Response model for transfer search"""
    success: bool
    destination: Optional[str] = None
    total_transfers: int = 0
    transfers: List[Dict[str, Any]] = []
    error: Optional[str] = None


class ActivityResult(BaseModel):
    """Activity/Excursion result"""
    activity_id: str
    name: str
    destination: str
    description: Optional[str] = None
    duration: Optional[str] = None
    price_adult: float
    price_child: Optional[float] = None
    currency: str = "ZAR"
    category: Optional[str] = None
    image_url: Optional[str] = None


class ActivitySearchResponse(BaseModel):
    """Response model for activity search"""
    success: bool
    destination: Optional[str] = None
    total_activities: int = 0
    activities: List[Dict[str, Any]] = []
    error: Optional[str] = None


# ============================================================
# FLIGHTS ENDPOINTS
# ============================================================

@travel_router.get("/flights")
async def list_flights(
    destination: Optional[str] = Query(None, description="Filter by destination"),
    limit: int = Query(50, ge=1, le=200),
    config: ClientConfig = Depends(get_client_config)
) -> FlightSearchResponse:
    """
    List available flight prices.

    Tries the Zorah Travel Platform (RTTC data) first, falls back to BigQuery.
    """
    # Try platform first
    try:
        from src.services.travel_platform_rates_client import get_travel_platform_rates_client
        client = get_travel_platform_rates_client()
        result = await client.list_flights(
            destination=destination, limit=limit
        )
        if result.get("success") and result.get("flights"):
            # Transform platform response to expected format
            # Platform returns per-leg records: {destination, code, route, direction, date, price_zar}
            # Group outbound + return legs into round-trip records
            raw_flights = result.get("flights", [])
            grouped = {}
            for f in raw_flights:
                dest = f.get("destination") or f.get("code", "Unknown")
                direction = f.get("direction", "").lower()
                key = f"{dest}-{f.get('date', '')}"

                if dest not in grouped:
                    grouped[dest] = {}

                flight_date = f.get("date")
                if direction == "return" and flight_date:
                    # Find the most recent outbound for this destination to pair with
                    for existing_key, existing in grouped[dest].items():
                        if not existing.get("return_date"):
                            existing["return_date"] = flight_date
                            # Average the prices for round trip
                            existing["price_per_person"] = (
                                existing.get("price_per_person", 0) + float(f.get("price_zar", 0))
                            )
                            break
                    else:
                        grouped[dest][key] = {
                            "destination": dest,
                            "departure_date": None,
                            "return_date": flight_date,
                            "price_per_person": float(f.get("price_zar", 0)),
                            "airline": f.get("route", "RTTC"),
                            "currency": "ZAR",
                            "source": "platform",
                        }
                else:
                    grouped[dest][key] = {
                        "destination": dest,
                        "departure_date": flight_date,
                        "return_date": None,
                        "price_per_person": float(f.get("price_zar", 0)),
                        "airline": f.get("route", "RTTC"),
                        "currency": "ZAR",
                        "source": "platform",
                    }

            flights = []
            for dest_flights in grouped.values():
                flights.extend(dest_flights.values())

            logger.info(f"Platform flights: {len(flights)} records from RTTC data")
            return FlightSearchResponse(
                success=True,
                destination=destination,
                total_flights=len(flights),
                flights=flights[:limit],
                source="platform",
            )
    except Exception as e:
        logger.warning(f"Platform flight list failed, falling back to BigQuery: {e}")

    # Fall back to BigQuery
    try:
        from src.tools.bigquery_tool import BigQueryTool
        bq = BigQueryTool(config)
        if not bq.client:
            return FlightSearchResponse(
                success=False,
                error="BigQuery not configured"
            )

        where_clause = ""
        if destination:
            where_clause = f"WHERE UPPER(destination) = UPPER('{destination}')"

        query = f"""
        SELECT
            destination,
            departure_date,
            return_date,
            price_per_person,
            airline,
            created_at
        FROM {bq.db.flight_prices}
        {where_clause}
        ORDER BY destination, departure_date
        LIMIT {limit}
        """

        results = bq.client.query(query).result()
        flights = []

        for row in results:
            flights.append({
                "destination": row.destination,
                "departure_date": row.departure_date.isoformat() if row.departure_date else None,
                "return_date": row.return_date.isoformat() if row.return_date else None,
                "price_per_person": float(row.price_per_person) if row.price_per_person else 0,
                "airline": row.airline,
                "currency": "ZAR",
                "source": "bigquery",
            })

        return FlightSearchResponse(
            success=True,
            destination=destination,
            total_flights=len(flights),
            flights=flights,
            source="bigquery",
        )

    except Exception as e:
        logger.error(f"Flight list failed: {e}")
        return FlightSearchResponse(
            success=False,
            error=str(e)
        )


@travel_router.get("/flights/search")
async def search_flights(
    destination: str = Query(..., description="Destination name or IATA code"),
    origin: str = Query("JNB", description="Origin IATA code (default: JNB)"),
    departure_date: Optional[str] = Query(None, description="Departure date (YYYY-MM-DD)"),
    return_date: Optional[str] = Query(None, description="Return date (YYYY-MM-DD)"),
    adults: int = Query(2, ge=1, le=9, description="Number of adults"),
    cabin_class: Optional[str] = Query(None, description="Cabin class filter"),
    config: ClientConfig = Depends(get_client_config)
) -> FlightSearchResponse:
    """
    Search flights by destination and optional dates.

    Primary: RTTC live flights (rich data with airline names, times, logos).
    Fallback: Legacy platform price matcher, then BigQuery.
    """
    from src.services.travel_platform_rates_client import get_travel_platform_rates_client

    # Build route for RTTC: "JNB-CPT" format
    dest_upper = destination.upper().strip()
    route = f"{origin.upper()}-{dest_upper}"

    # === Try RTTC aggregated endpoint first (with dedup cache) ===
    try:
        client = get_travel_platform_rates_client()

        if departure_date:
            cache_key = f"rttc-agg:{route}:{departure_date}:{adults}:{cabin_class or ''}"

            async def _fetch_rttc_agg():
                return await client.search_flights_rttc(
                    route=route,
                    flight_date=departure_date,
                    passengers=adults,
                    cabin_class=cabin_class,
                )

            result = await get_flights_cached(cache_key, _fetch_rttc_agg)
            if result.get("success") and result.get("flights"):
                flights = result["flights"]
                logger.info(f"RTTC flight search: {len(flights)} flights for {route}")
                return FlightSearchResponse(
                    success=True,
                    destination=destination,
                    total_flights=len(flights),
                    flights=flights,
                    source="rttc",
                )
    except Exception as e:
        logger.warning(f"RTTC aggregated flight search failed: {e}")

    # === Try legacy platform price matcher ===
    try:
        client = get_travel_platform_rates_client()

        if departure_date and return_date:
            result = await client.get_flight_price(destination, departure_date, return_date)
            if result.get("success"):
                outbound = result.get("outbound")
                return_leg = result.get("return")
                total = result.get("total_round_trip_zar", 0)

                flights = [{
                    "destination": destination,
                    "departure_date": outbound.get("date") if outbound else departure_date,
                    "return_date": return_leg.get("date") if return_leg else return_date,
                    "price_per_person": total,
                    "airline": outbound.get("route", "RTTC") if outbound else "RTTC",
                    "currency": "ZAR",
                    "source": "platform",
                }]

                logger.info(f"Platform flight price: {destination} = R{total}")
                return FlightSearchResponse(
                    success=True,
                    destination=destination,
                    total_flights=1,
                    flights=flights,
                    source="platform",
                    outbound=outbound,
                    return_leg=return_leg,
                )

        # Without both dates, use list_flights filtered by destination
        result = await client.list_flights(destination=destination, limit=20)
        if result.get("success") and result.get("flights"):
            raw_flights = result.get("flights", [])
            flights = []
            for f in raw_flights:
                flights.append({
                    "destination": f.get("destination") or f.get("code", destination),
                    "departure_date": f.get("date") if f.get("direction", "").lower() == "outbound" else None,
                    "return_date": f.get("date") if f.get("direction", "").lower() == "return" else None,
                    "price_per_person": float(f.get("price_zar", 0)),
                    "airline": f.get("route", "RTTC"),
                    "currency": "ZAR",
                    "source": "platform",
                })

            logger.info(f"Platform flight search: {len(flights)} records for {destination}")
            return FlightSearchResponse(
                success=True,
                destination=destination,
                total_flights=len(flights),
                flights=flights,
                source="platform",
            )
    except Exception as e:
        logger.warning(f"Platform flight search failed, falling back to BigQuery: {e}")

    # === Fall back to BigQuery ===
    try:
        from src.tools.bigquery_tool import BigQueryTool
        bq = BigQueryTool(config)
        if not bq.client:
            return FlightSearchResponse(
                success=False,
                destination=destination,
                error="BigQuery not configured"
            )

        if departure_date:
            query = f"""
            SELECT
                destination,
                departure_date,
                return_date,
                price_per_person,
                airline
            FROM {bq.db.flight_prices}
            WHERE UPPER(destination) = UPPER(@destination)
            ORDER BY ABS(DATE_DIFF(@departure_date, departure_date, DAY)) ASC
            LIMIT 10
            """
            from google.cloud import bigquery
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("destination", "STRING", destination),
                    bigquery.ScalarQueryParameter("departure_date", "DATE", departure_date)
                ]
            )
            results = bq.client.query(query, job_config=job_config).result()
        else:
            query = f"""
            SELECT
                destination,
                departure_date,
                return_date,
                price_per_person,
                airline
            FROM {bq.db.flight_prices}
            WHERE UPPER(destination) = UPPER('{destination}')
            ORDER BY departure_date DESC
            LIMIT 10
            """
            results = bq.client.query(query).result()

        flights = []
        for row in results:
            flights.append({
                "destination": row.destination,
                "departure_date": row.departure_date.isoformat() if row.departure_date else None,
                "return_date": row.return_date.isoformat() if row.return_date else None,
                "price_per_person": float(row.price_per_person) if row.price_per_person else 0,
                "airline": row.airline,
                "currency": "ZAR",
                "source": "bigquery",
            })

        return FlightSearchResponse(
            success=True,
            destination=destination,
            total_flights=len(flights),
            flights=flights,
            source="bigquery",
        )

    except Exception as e:
        logger.error(f"Flight search failed: {e}")
        return FlightSearchResponse(
            success=False,
            destination=destination,
            error=str(e)
        )


@travel_router.get("/flights/rttc")
async def search_rttc_flights(
    origin: str = Query(..., description="Origin IATA code (e.g. JNB)"),
    destination: str = Query(..., description="Destination IATA code (e.g. CPT)"),
    departure_date: str = Query(..., description="Departure date (YYYY-MM-DD)"),
    return_date: Optional[str] = Query(None, description="Return date for round-trip (YYYY-MM-DD)"),
    adults: int = Query(2, ge=1, le=9, description="Number of adults"),
    cabin_class: Optional[str] = Query(None, description="Cabin class filter"),
) -> FlightSearchResponse:
    """
    Direct RTTC round-trip flight search.

    Returns rich flight data with airline names, logos, times, duration, stops, etc.
    When return_date is provided, returns separate outbound_flights and return_flights.
    """
    try:
        from src.services.travel_platform_rates_client import get_travel_platform_rates_client
        client = get_travel_platform_rates_client()

        cache_key = f"rttc-direct:{origin.upper()}-{destination.upper()}:{departure_date}:{return_date or ''}:{adults}:{cabin_class or ''}"

        async def _fetch_rttc_direct():
            return await client.search_rttc_flights_direct(
                origin=origin.upper(),
                destination=destination.upper(),
                departure_date=departure_date,
                return_date=return_date,
                adults=adults,
                cabin_class=cabin_class,
            )

        result = await get_flights_cached(cache_key, _fetch_rttc_direct)

        if result.get("success"):
            outbound = result.get("outbound_flights", [])
            return_fl = result.get("return_flights", [])
            # Combine for the flat flights[] list as well
            all_flights = outbound + return_fl
            return FlightSearchResponse(
                success=True,
                destination=destination,
                total_flights=len(all_flights),
                flights=all_flights,
                outbound_flights=outbound,
                return_flights=return_fl,
                source="rttc_direct",
            )

        # RTTC direct failed — try aggregated endpoint as fallback
        route = f"{origin.upper()}-{destination.upper()}"
        agg_cache_key = f"rttc-agg:{route}:{departure_date}:{adults}:{cabin_class or ''}"

        async def _fetch_rttc_agg_fallback():
            return await client.search_flights_rttc(
                route=route,
                flight_date=departure_date,
                passengers=adults,
                cabin_class=cabin_class,
            )

        agg_result = await get_flights_cached(agg_cache_key, _fetch_rttc_agg_fallback)
        if agg_result.get("success") and agg_result.get("flights"):
            flights = agg_result["flights"]
            return FlightSearchResponse(
                success=True,
                destination=destination,
                total_flights=len(flights),
                flights=flights,
                source="rttc",
            )

        return FlightSearchResponse(
            success=False,
            destination=destination,
            error=result.get("error", "No flights found"),
        )

    except Exception as e:
        logger.error(f"RTTC flight search failed: {e}")
        return FlightSearchResponse(
            success=False,
            destination=destination,
            error=str(e),
        )


@travel_router.get("/flights/destinations")
async def flight_destinations() -> Dict[str, Any]:
    """
    Get destinations with flight data from the platform.

    Returns destinations with avg prices and date ranges from RTTC data.
    """
    try:
        from src.services.travel_platform_rates_client import get_travel_platform_rates_client
        client = get_travel_platform_rates_client()
        result = await client.get_flight_destinations()
        return result
    except Exception as e:
        logger.error(f"Flight destinations failed: {e}")
        return {"success": False, "destinations": [], "error": str(e)}


@travel_router.get("/flights/price")
async def flight_price(
    destination: str = Query(..., description="Destination name"),
    departure_date: str = Query(..., description="Departure date (YYYY-MM-DD)"),
    return_date: str = Query(..., description="Return date (YYYY-MM-DD)"),
) -> Dict[str, Any]:
    """
    Get matched round-trip flight price from the platform.

    Returns outbound + return legs with total round-trip price in ZAR.
    """
    try:
        from src.services.travel_platform_rates_client import get_travel_platform_rates_client
        client = get_travel_platform_rates_client()
        result = await client.get_flight_price(destination, departure_date, return_date)
        return result
    except Exception as e:
        logger.error(f"Flight price lookup failed: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# TRANSFERS ENDPOINTS
# ============================================================

@travel_router.get("/transfers")
async def list_transfers(
    destination: Optional[str] = Query(None, description="Filter by destination"),
    route: Optional[str] = Query(None, description="Transfer route (e.g. 'Zanzibar Airport to Stone Town')"),
    transfer_date: Optional[str] = Query(None, description="Transfer date (YYYY-MM-DD)"),
    passengers: int = Query(2, ge=1, le=20, description="Number of passengers"),
    limit: int = Query(50, ge=1, le=200),
    config: ClientConfig = Depends(get_client_config)
) -> TransferSearchResponse:
    """
    List transfer prices.

    Primary: HotelBeds live transfers (real-time pricing).
    Fallback: BigQuery static transfer pricing from hotel rates.
    """
    # Try HotelBeds live data first (requires route + date)
    if destination and route and transfer_date:
        try:
            from src.services.hotelbeds_client import get_hotelbeds_client
            from datetime import date as date_type
            hb_client = get_hotelbeds_client()
            result = await hb_client.search_transfers(
                route=route,
                transfer_date=date_type.fromisoformat(transfer_date),
                passengers=passengers,
            )
            if result.get("success") and result.get("transfers"):
                transfers = _map_hotelbeds_transfers(result["transfers"])
                transfers = transfers[:limit]
                logger.info(f"HotelBeds transfers: {len(transfers)} results for {route}")
                return TransferSearchResponse(
                    success=True,
                    destination=destination,
                    total_transfers=len(transfers),
                    transfers=transfers,
                )
        except Exception as e:
            logger.warning(f"HotelBeds transfers failed, using BigQuery fallback: {e}")

    # Fallback to BigQuery
    from src.tools.bigquery_tool import BigQueryTool

    try:
        bq = BigQueryTool(config)
        if not bq.client:
            return TransferSearchResponse(
                success=False,
                error="BigQuery not configured"
            )

        where_clause = "WHERE transfers_adult > 0"
        if destination:
            where_clause += f" AND UPPER(destination) = UPPER('{destination}')"

        query = f"""
        SELECT DISTINCT
            destination,
            hotel_name,
            transfers_adult,
            transfers_child
        FROM {bq.db.hotel_rates}
        {where_clause}
        ORDER BY destination, hotel_name
        LIMIT {limit}
        """

        results = bq.client.query(query).result()
        transfers = []

        for row in results:
            transfers.append({
                "destination": row.destination,
                "hotel_name": row.hotel_name,
                "transfers_adult": float(row.transfers_adult) if row.transfers_adult else 0,
                "transfers_child": float(row.transfers_child) if row.transfers_child else 0,
                "currency": "ZAR"
            })

        return TransferSearchResponse(
            success=True,
            destination=destination,
            total_transfers=len(transfers),
            transfers=transfers
        )

    except Exception as e:
        logger.error(f"Transfer list failed: {e}")
        return TransferSearchResponse(
            success=False,
            error=str(e)
        )


@travel_router.get("/transfers/search")
async def search_transfers(
    destination: str = Query(..., description="Destination name"),
    hotel_name: Optional[str] = Query(None, description="Filter by hotel name"),
    route: Optional[str] = Query(None, description="Transfer route (e.g. 'Zanzibar Airport to Stone Town')"),
    transfer_date: Optional[str] = Query(None, description="Transfer date (YYYY-MM-DD)"),
    passengers: int = Query(2, ge=1, le=20, description="Number of passengers"),
    config: ClientConfig = Depends(get_client_config)
) -> TransferSearchResponse:
    """
    Search transfer prices by destination.

    Primary: HotelBeds live transfers (real-time pricing).
    Fallback: BigQuery static transfer pricing from hotel rates.
    """
    # Try HotelBeds live data first
    if route and transfer_date:
        try:
            from src.services.hotelbeds_client import get_hotelbeds_client
            from datetime import date as date_type
            hb_client = get_hotelbeds_client()
            result = await hb_client.search_transfers(
                route=route,
                transfer_date=date_type.fromisoformat(transfer_date),
                passengers=passengers,
            )
            if result.get("success") and result.get("transfers"):
                transfers = _map_hotelbeds_transfers(result["transfers"])
                logger.info(f"HotelBeds transfer search: {len(transfers)} results for {route}")
                return TransferSearchResponse(
                    success=True,
                    destination=destination,
                    total_transfers=len(transfers),
                    transfers=transfers,
                )
        except Exception as e:
            logger.warning(f"HotelBeds transfer search failed, using BigQuery fallback: {e}")

    # Fallback to BigQuery
    from src.tools.bigquery_tool import BigQueryTool

    try:
        bq = BigQueryTool(config)
        if not bq.client:
            return TransferSearchResponse(
                success=False,
                destination=destination,
                error="BigQuery not configured"
            )

        where_clause = f"WHERE UPPER(destination) = UPPER('{destination}') AND transfers_adult > 0"
        if hotel_name:
            where_clause += f" AND LOWER(hotel_name) LIKE LOWER('%{hotel_name}%')"

        query = f"""
        SELECT DISTINCT
            destination,
            hotel_name,
            transfers_adult,
            transfers_child
        FROM {bq.db.hotel_rates}
        {where_clause}
        ORDER BY hotel_name
        LIMIT 50
        """

        results = bq.client.query(query).result()
        transfers = []

        for row in results:
            transfers.append({
                "destination": row.destination,
                "hotel_name": row.hotel_name,
                "transfers_adult": float(row.transfers_adult) if row.transfers_adult else 0,
                "transfers_child": float(row.transfers_child) if row.transfers_child else 0,
                "currency": "ZAR"
            })

        return TransferSearchResponse(
            success=True,
            destination=destination,
            total_transfers=len(transfers),
            transfers=transfers
        )

    except Exception as e:
        logger.error(f"Transfer search failed: {e}")
        return TransferSearchResponse(
            success=False,
            destination=destination,
            error=str(e)
        )


# ============================================================
# ACTIVITIES ENDPOINTS
# ============================================================

HOTELBEDS_IMAGE_BASE = "https://photos.hotelbeds.com/giata/"


def _map_hotelbeds_activities(raw_activities: list, destination: str) -> list:
    """Map HotelBeds activity response to our normalized format."""
    import re
    mapped = []
    for a in raw_activities:
        # Resolve image URL — HotelBeds may return relative paths
        image_url = a.get("image_url") or a.get("image") or None
        if image_url and not image_url.startswith("http"):
            image_url = HOTELBEDS_IMAGE_BASE + image_url

        # Strip HTML from description
        description = a.get("description", "") or ""
        description = re.sub(r"<[^>]*>", "", description)

        # Duration formatting
        duration = None
        duration_hours = a.get("duration_hours")
        if duration_hours:
            duration = f"{duration_hours} hours"

        mapped.append({
            "activity_id": a.get("activity_id", ""),
            "name": a.get("name", ""),
            "destination": destination,
            "description": description,
            "duration": duration,
            "price_adult": a.get("price_per_person") or 0,
            "price_child": None,
            "currency": a.get("currency", "EUR"),
            "category": a.get("category"),
            "image_url": image_url,
            "source": "hotelbeds",
            "total_price": a.get("total_price"),
        })
    return mapped


def _map_hotelbeds_transfers(raw_transfers: list) -> list:
    """Map HotelBeds transfer response to our normalized format."""
    mapped = []
    for t in raw_transfers:
        mapped.append({
            "destination": t.get("destination", ""),
            "hotel_name": t.get("route", ""),
            "transfers_adult": t.get("price_per_transfer") or 0,
            "transfers_child": 0,
            "currency": t.get("currency", "EUR"),
            "vehicle_type": t.get("vehicle_type"),
            "vehicle_category": t.get("vehicle_category"),
            "max_passengers": t.get("max_passengers"),
            "duration_minutes": t.get("duration_minutes"),
            "source": "hotelbeds",
        })
    return mapped


# Static activities data - fallback when HotelBeds is unavailable
SAMPLE_ACTIVITIES = [
    {
        "activity_id": "ACT001",
        "name": "Spice Tour",
        "destination": "zanzibar",
        "description": "Explore Zanzibar's famous spice plantations and learn about cloves, nutmeg, cinnamon and more.",
        "duration": "Half Day (4 hours)",
        "price_adult": 45,
        "price_child": 25,
        "currency": "USD",
        "category": "Cultural",
        "image_url": "https://images.unsplash.com/photo-1596040033229-a9821ebd058d?w=400"
    },
    {
        "activity_id": "ACT002",
        "name": "Stone Town Walking Tour",
        "destination": "zanzibar",
        "description": "Discover the UNESCO World Heritage Site with its winding alleys, historic buildings and vibrant markets.",
        "duration": "3 hours",
        "price_adult": 35,
        "price_child": 20,
        "currency": "USD",
        "category": "Cultural",
        "image_url": "https://images.unsplash.com/photo-1590523741831-ab7e8b8f9c7f?w=400"
    },
    {
        "activity_id": "ACT003",
        "name": "Dolphin Tour & Snorkeling",
        "destination": "zanzibar",
        "description": "Swim with dolphins at Kizimkazi and snorkel in crystal clear waters.",
        "duration": "Full Day",
        "price_adult": 85,
        "price_child": 50,
        "currency": "USD",
        "category": "Water Sports",
        "image_url": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=400"
    },
    {
        "activity_id": "ACT004",
        "name": "Prison Island Tour",
        "destination": "zanzibar",
        "description": "Visit the historic island and meet the giant Aldabra tortoises, some over 100 years old.",
        "duration": "Half Day",
        "price_adult": 50,
        "price_child": 30,
        "currency": "USD",
        "category": "Nature",
        "image_url": "https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=400"
    },
    {
        "activity_id": "ACT005",
        "name": "Safari Blue",
        "destination": "zanzibar",
        "description": "Full day sailing adventure with snorkeling, sandbank visit, seafood lunch and more.",
        "duration": "Full Day",
        "price_adult": 95,
        "price_child": 55,
        "currency": "USD",
        "category": "Water Sports",
        "image_url": "https://images.unsplash.com/photo-1544551763-77ef2d0cfc6c?w=400"
    },
    {
        "activity_id": "ACT006",
        "name": "Catamaran Sunset Cruise",
        "destination": "mauritius",
        "description": "Sail along the west coast with dinner, drinks and stunning sunset views.",
        "duration": "4 hours",
        "price_adult": 120,
        "price_child": 70,
        "currency": "USD",
        "category": "Cruises",
        "image_url": "https://images.unsplash.com/photo-1500917293891-ef795e70e1f6?w=400"
    },
    {
        "activity_id": "ACT007",
        "name": "Ile aux Cerfs Island Tour",
        "destination": "mauritius",
        "description": "Speedboat to the famous island with pristine beaches and optional water sports.",
        "duration": "Full Day",
        "price_adult": 85,
        "price_child": 45,
        "currency": "USD",
        "category": "Beach",
        "image_url": "https://images.unsplash.com/photo-1559494007-9f5847c49d94?w=400"
    },
    {
        "activity_id": "ACT008",
        "name": "Chamarel Seven Colored Earth",
        "destination": "mauritius",
        "description": "Visit the geological wonder, Chamarel Waterfall, and rum distillery.",
        "duration": "Half Day",
        "price_adult": 65,
        "price_child": 35,
        "currency": "USD",
        "category": "Nature",
        "image_url": "https://images.unsplash.com/photo-1580060839134-75a5edca2e99?w=400"
    },
    {
        "activity_id": "ACT009",
        "name": "Swimming with Dolphins",
        "destination": "mauritius",
        "description": "Early morning boat trip to swim with wild spinner dolphins in their natural habitat.",
        "duration": "Half Day",
        "price_adult": 75,
        "price_child": 45,
        "currency": "USD",
        "category": "Water Sports",
        "image_url": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=400"
    },
    {
        "activity_id": "ACT010",
        "name": "Male City Tour",
        "destination": "maldives",
        "description": "Explore the capital city including the Grand Friday Mosque, fish market and local shops.",
        "duration": "3 hours",
        "price_adult": 55,
        "price_child": 30,
        "currency": "USD",
        "category": "Cultural",
        "image_url": "https://images.unsplash.com/photo-1514282401047-d79a71a590e8?w=400"
    },
    {
        "activity_id": "ACT011",
        "name": "Sunset Fishing Trip",
        "destination": "maldives",
        "description": "Traditional Maldivian line fishing experience with BBQ dinner on the beach.",
        "duration": "4 hours",
        "price_adult": 85,
        "price_child": 50,
        "currency": "USD",
        "category": "Fishing",
        "image_url": "https://images.unsplash.com/photo-1544551763-77ef2d0cfc6c?w=400"
    },
    {
        "activity_id": "ACT012",
        "name": "Snorkeling Safari",
        "destination": "maldives",
        "description": "Visit multiple snorkeling spots to see manta rays, turtles and colorful reef fish.",
        "duration": "Full Day",
        "price_adult": 110,
        "price_child": 65,
        "currency": "USD",
        "category": "Water Sports",
        "image_url": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=400"
    },
    {
        "activity_id": "ACT013",
        "name": "Masai Mara Game Drive",
        "destination": "kenya",
        "description": "Full day safari in the world-famous Masai Mara with expert guides.",
        "duration": "Full Day",
        "price_adult": 250,
        "price_child": 150,
        "currency": "USD",
        "category": "Safari",
        "image_url": "https://images.unsplash.com/photo-1516426122078-c23e76319801?w=400"
    },
    {
        "activity_id": "ACT014",
        "name": "Hot Air Balloon Safari",
        "destination": "kenya",
        "description": "Sunrise balloon flight over the Mara with champagne breakfast.",
        "duration": "4 hours",
        "price_adult": 450,
        "price_child": 350,
        "currency": "USD",
        "category": "Safari",
        "image_url": "https://images.unsplash.com/photo-1504598318550-17eba1008a68?w=400"
    },
    {
        "activity_id": "ACT015",
        "name": "Victoria Falls Tour",
        "destination": "victoria-falls",
        "description": "Guided tour of the majestic Victoria Falls from the Zimbabwe side.",
        "duration": "3 hours",
        "price_adult": 50,
        "price_child": 25,
        "currency": "USD",
        "category": "Nature",
        "image_url": "https://images.unsplash.com/photo-1568625365131-079e026a927d?w=400"
    },
    {
        "activity_id": "ACT016",
        "name": "Sunset Cruise on Zambezi",
        "destination": "victoria-falls",
        "description": "Relaxing cruise with drinks and snacks while watching hippos and elephants.",
        "duration": "2.5 hours",
        "price_adult": 65,
        "price_child": 35,
        "currency": "USD",
        "category": "Cruises",
        "image_url": "https://images.unsplash.com/photo-1516426122078-c23e76319801?w=400"
    },
    {
        "activity_id": "ACT017",
        "name": "Bungee Jump",
        "destination": "victoria-falls",
        "description": "111m bungee jump from the Victoria Falls Bridge - not for the faint hearted!",
        "duration": "1 hour",
        "price_adult": 160,
        "price_child": None,
        "currency": "USD",
        "category": "Adventure",
        "image_url": "https://images.unsplash.com/photo-1540039155733-5bb30b53aa14?w=400"
    },
]


@travel_router.get("/activities")
async def list_activities(
    destination: Optional[str] = Query(None, description="Filter by destination"),
    category: Optional[str] = Query(None, description="Filter by category"),
    participants: int = Query(2, ge=1, le=50, description="Number of participants"),
    limit: int = Query(50, ge=1, le=200)
) -> ActivitySearchResponse:
    """
    List available activities and excursions.

    Primary: HotelBeds live activities (real pricing and availability).
    Fallback: Sample data for demonstration.
    """
    # Try HotelBeds live data first (requires a destination)
    if destination:
        try:
            from src.services.hotelbeds_client import get_hotelbeds_client
            hb_client = get_hotelbeds_client()
            result = await hb_client.search_activities(
                destination=destination.lower(),
                participants=participants,
            )
            if result.get("success") and result.get("activities"):
                activities = _map_hotelbeds_activities(result["activities"], destination)

                # Apply category filter (client-side)
                if category:
                    activities = [a for a in activities if a.get("category", "").lower() == category.lower()]

                activities = activities[:limit]

                logger.info(f"HotelBeds activities: {len(activities)} results for {destination}")
                return ActivitySearchResponse(
                    success=True,
                    destination=destination,
                    total_activities=len(activities),
                    activities=activities,
                )
        except Exception as e:
            logger.warning(f"HotelBeds activities failed, using sample data: {e}")

    # Fallback to sample data
    try:
        activities = SAMPLE_ACTIVITIES.copy()

        if destination:
            activities = [a for a in activities if a["destination"].lower() == destination.lower()]

        if category:
            activities = [a for a in activities if a.get("category", "").lower() == category.lower()]

        activities = activities[:limit]

        return ActivitySearchResponse(
            success=True,
            destination=destination,
            total_activities=len(activities),
            activities=activities
        )

    except Exception as e:
        logger.error(f"Activity list failed: {e}")
        return ActivitySearchResponse(
            success=False,
            error=str(e)
        )


@travel_router.get("/activities/search")
async def search_activities(
    destination: str = Query(..., description="Destination name"),
    category: Optional[str] = Query(None, description="Filter by category"),
    query: Optional[str] = Query(None, description="Search in name/description"),
    participants: int = Query(2, ge=1, le=50, description="Number of participants"),
) -> ActivitySearchResponse:
    """
    Search activities by destination.

    Primary: HotelBeds live activities (real pricing and availability).
    Fallback: Sample data for demonstration.
    """
    # Try HotelBeds live data first
    try:
        from src.services.hotelbeds_client import get_hotelbeds_client
        hb_client = get_hotelbeds_client()
        result = await hb_client.search_activities(
            destination=destination.lower(),
            participants=participants,
        )
        if result.get("success") and result.get("activities"):
            activities = _map_hotelbeds_activities(result["activities"], destination)

            # Apply category filter
            if category:
                activities = [a for a in activities if a.get("category", "").lower() == category.lower()]

            # Apply search query
            if query:
                query_lower = query.lower()
                activities = [
                    a for a in activities
                    if query_lower in a.get("name", "").lower()
                    or query_lower in (a.get("description") or "").lower()
                ]

            logger.info(f"HotelBeds activity search: {len(activities)} results for {destination}")
            return ActivitySearchResponse(
                success=True,
                destination=destination,
                total_activities=len(activities),
                activities=activities,
            )
    except Exception as e:
        logger.warning(f"HotelBeds activity search failed, using sample data: {e}")

    # Fallback to sample data
    try:
        activities = [a for a in SAMPLE_ACTIVITIES if a["destination"].lower() == destination.lower()]

        if category:
            activities = [a for a in activities if a.get("category", "").lower() == category.lower()]

        if query:
            query_lower = query.lower()
            activities = [
                a for a in activities
                if query_lower in a["name"].lower() or query_lower in (a.get("description") or "").lower()
            ]

        return ActivitySearchResponse(
            success=True,
            destination=destination,
            total_activities=len(activities),
            activities=activities
        )

    except Exception as e:
        logger.error(f"Activity search failed: {e}")
        return ActivitySearchResponse(
            success=False,
            destination=destination,
            error=str(e)
        )


@travel_router.get("/activities/categories")
def list_activity_categories() -> Dict[str, Any]:
    """
    List available activity categories.
    """
    categories = list(set(a.get("category") for a in SAMPLE_ACTIVITIES if a.get("category")))
    categories.sort()

    return {
        "success": True,
        "categories": categories,
        "count": len(categories)
    }


# ============================================================
# DESTINATIONS OVERVIEW
# ============================================================

@travel_router.get("/destinations")
def list_all_destinations() -> Dict[str, Any]:
    """
    List all available destinations with service availability.
    """
    destinations = [
        {"code": "zanzibar", "name": "Zanzibar", "country": "Tanzania", "hotels": True, "activities": True, "flights": True, "transfers": True},
        {"code": "mauritius", "name": "Mauritius", "country": "Mauritius", "hotels": True, "activities": True, "flights": True, "transfers": True},
        {"code": "maldives", "name": "Maldives", "country": "Maldives", "hotels": True, "activities": True, "flights": True, "transfers": True},
        {"code": "kenya", "name": "Kenya", "country": "Kenya", "hotels": True, "activities": True, "flights": True, "transfers": True},
        {"code": "victoria-falls", "name": "Victoria Falls", "country": "Zimbabwe/Zambia", "hotels": True, "activities": True, "flights": True, "transfers": True},
        {"code": "seychelles", "name": "Seychelles", "country": "Seychelles", "hotels": True, "activities": False, "flights": True, "transfers": True},
        {"code": "cape-town", "name": "Cape Town", "country": "South Africa", "hotels": True, "activities": False, "flights": True, "transfers": True},
    ]

    return {
        "success": True,
        "destinations": destinations,
        "count": len(destinations)
    }


# ============================================================
# ROUTER REGISTRATION
# ============================================================

def include_travel_router(app) -> None:
    """Include travel services router in the FastAPI app"""
    app.include_router(travel_router)
