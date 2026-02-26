"""
Travel Platform Rates Client

Connects to the Zorah Travel Platform Rates Engine for live hotel availability.
Uses the full search endpoint which works with live Juniper data.

Configuration via environment variables:
- RATES_ENGINE_URL: Base URL (default: https://zorah-travel-platform-...)
- RATES_ENGINE_TIMEOUT: Request timeout in seconds (default: 120)
"""

import os
import re
import html
import logging
from typing import List, Dict, Optional, Any
from datetime import date

import httpx

from src.utils.circuit_breaker import rates_circuit
from src.utils.retry_utils import retry_on_async_network_error

logger = logging.getLogger(__name__)


def _is_quality_hotel(hotel: dict) -> bool:
    """Filter out Juniper placeholder hotels with internal code names."""
    name = hotel.get("hotel_name") or hotel.get("name") or ""
    if re.match(r'^Hotel\s+JP[A-Z0-9]+', name):
        return False
    if not name or len(name) < 3:
        return False
    return True


class TravelPlatformRatesClient:
    """
    Client for Zorah Travel Platform Rates Engine.

    Provides live hotel availability search via Juniper integration.
    Singleton pattern for connection reuse.
    """

    _instance = None

    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.base_url = os.getenv(
            "RATES_ENGINE_URL",
            "http://localhost:8080"
        )
        self.timeout = float(os.getenv("RATES_ENGINE_TIMEOUT", "120"))
        self._initialized = True
        self._last_error: Optional[str] = None

        logger.info(
            f"Rates Engine client initialized: url={self.base_url}, timeout={self.timeout}s"
        )

    async def is_available(self) -> bool:
        """Check if rates engine is available."""
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{self.base_url}/api/v1/travel-services/health",
                    timeout=10.0
                )
                if r.status_code == 200:
                    data = r.json()
                    status = data.get("status", "unknown")
                    logger.debug(
                        f"Rates Engine health: status={status}, "
                        f"providers={data.get('providers', {})}"
                    )
                    return status == "healthy"
                logger.warning(f"Rates Engine health check failed: {r.status_code}")
                return False
        except Exception as e:
            logger.warning(f"Rates Engine not available: {e}")
            self._last_error = str(e)
            return False

    async def search_hotels(
        self,
        destination: str,
        check_in: date,
        check_out: date,
        adults: int = 2,
        children_ages: Optional[List[int]] = None,
        max_hotels: int = 50
    ) -> Dict[str, Any]:
        """
        Full hotel availability search using live Juniper data.

        Args:
            destination: Destination name (e.g., "zanzibar", "mauritius")
            check_in: Check-in date
            check_out: Check-out date
            adults: Number of adults (default: 2)
            children_ages: List of children ages (default: empty)
            max_hotels: Maximum hotels to return (default: 50, recommended for performance)

        Returns:
            Dict with:
                - success: bool
                - destination: str
                - check_in: str
                - check_out: str
                - nights: int
                - total_hotels: int
                - hotels: List of hotel options with pricing
                - search_time_seconds: float
                - error: str (if failed)
        """
        if not rates_circuit.can_execute():
            logger.warning("Rates Engine circuit breaker OPEN — skipping search")
            return self._error_response("Circuit breaker open")

        url = f"{self.base_url}/api/v1/availability/search"

        payload = {
            "destination": destination.lower(),
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "rooms": [{"adults": adults, "children_ages": children_ages or []}],
            "max_hotels": max_hotels
        }

        try:
            data = await self._post_with_retry(url, payload)

            hotel_count = data.get("total_hotels", len(data.get("hotels", [])))
            search_time = data.get("search_time_seconds", 0)

            rates_circuit.record_success()

            # Log search results with more detail for debugging
            supplier = data.get("supplier", "unknown")
            logger.info(
                f"Rates Engine search complete: destination={destination}, "
                f"hotels={hotel_count}, supplier={supplier}, "
                f"max_requested={max_hotels}, time={search_time:.1f}s"
            )

            # Warn if significantly fewer results than requested
            if hotel_count < max_hotels // 2 and hotel_count > 0:
                logger.warning(
                    f"Low hotel count: got {hotel_count} hotels for {destination}, "
                    f"requested max {max_hotels}. This may indicate limited supplier availability."
                )

            # Filter out hotels with zero or missing pricing
            # Raw upstream data may use total_price or cheapest_price
            hotels_list = [
                h for h in data.get("hotels", [])
                if (h.get("cheapest_price") or h.get("total_price") or 0) > 0
            ]

            # Unescape HTML entities in hotel names (Juniper returns &eacute; etc.)
            for h in hotels_list:
                if h.get("hotel_name"):
                    h["hotel_name"] = html.unescape(h["hotel_name"])
                elif h.get("name"):
                    h["name"] = html.unescape(h["name"])

            # Filter out Juniper placeholder hotels (e.g. "Hotel JP03268C")
            hotels_list = [h for h in hotels_list if _is_quality_hotel(h)]

            return {
                "success": True,
                "destination": data.get("destination", destination),
                "check_in": data.get("check_in", check_in.isoformat()),
                "check_out": data.get("check_out", check_out.isoformat()),
                "nights": data.get("nights", (check_out - check_in).days),
                "total_hotels": len(hotels_list),
                "hotels": hotels_list,
                "search_time_seconds": search_time
            }

        except httpx.TimeoutException:
            self._last_error = f"Request timed out after {self.timeout}s"
            logger.error(f"Rates Engine timeout: {self._last_error}")
            rates_circuit.record_failure()
            return self._error_response(self._last_error)

        except httpx.ConnectError as e:
            self._last_error = f"Connection failed: {e}"
            logger.error(f"Rates Engine connection error: {self._last_error}")
            rates_circuit.record_failure()
            return self._error_response(self._last_error)

        except httpx.HTTPStatusError as e:
            self._last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"Rates Engine HTTP error: {self._last_error}")

            # If Juniper fails with IP whitelist error, fall back to HotelBeds
            if e.response.status_code == 500 and "whitelisted IP" in e.response.text:
                logger.info("Juniper requires whitelisted IP, falling back to HotelBeds")
                return await self._search_hotels_hotelbeds(
                    destination, check_in, check_out, adults, children_ages, max_hotels
                )

            rates_circuit.record_failure()
            return self._error_response(self._last_error)

        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Rates Engine error: {self._last_error}")
            rates_circuit.record_failure()
            return self._error_response(self._last_error)

    async def _search_hotels_hotelbeds(
        self,
        destination: str,
        check_in: date,
        check_out: date,
        adults: int = 2,
        children_ages: Optional[List[int]] = None,
        max_hotels: int = 50
    ) -> Dict[str, Any]:
        """
        Fallback search using HotelBeds API directly.
        Used when Juniper is unavailable (e.g., IP not whitelisted).
        """
        url = f"{self.base_url}/api/v1/hotelbeds/hotels/search"

        params = {
            "destination": destination.lower(),
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "adults": adults,
        }

        if children_ages:
            params["children_ages"] = ",".join(str(age) for age in children_ages)

        try:
            async with httpx.AsyncClient() as client:
                logger.info(
                    f"HotelBeds fallback search: destination={destination}, "
                    f"dates={check_in} to {check_out}"
                )

                r = await client.get(url, params=params, timeout=self.timeout)
                r.raise_for_status()
                data = r.json()

                # Transform HotelBeds response to match expected format
                hotels = data.get("hotels", [])
                nights = (check_out - check_in).days

                # Normalize hotel data to match Juniper format
                normalized_hotels = []
                for hotel in hotels[:max_hotels]:
                    normalized_hotels.append({
                        "hotel_id": hotel.get("hotel_id"),
                        "hotel_name": html.unescape(hotel.get("name", "")),
                        "destination": destination,
                        "stars": int(hotel.get("star_rating", "4").replace("*", "") or 4),
                        "image_url": hotel.get("image_url"),
                        "cheapest_price": hotel.get("total_price") or None,
                        "cheapest_meal_plan": hotel.get("meal_plan", "Bed & Breakfast"),
                        "currency": hotel.get("currency", "EUR"),
                        "options": [{
                            "room_type": hotel.get("room_type", "Standard Room"),
                            "meal_plan": hotel.get("meal_plan", "Bed & Breakfast"),
                            "price_total": hotel.get("total_price", 0),
                            "price_per_night": hotel.get("rate_per_night", 0),
                            "currency": hotel.get("currency", "EUR")
                        }],
                        "source": "hotelbeds"
                    })

                logger.info(f"HotelBeds search complete: {len(normalized_hotels)} hotels found")

                return {
                    "success": True,
                    "destination": destination,
                    "check_in": check_in.isoformat(),
                    "check_out": check_out.isoformat(),
                    "nights": nights,
                    "total_hotels": len(normalized_hotels),
                    "hotels": normalized_hotels,
                    "search_time_seconds": 0,
                    "source": "hotelbeds"
                }

        except Exception as e:
            self._last_error = f"HotelBeds fallback failed: {e}"
            logger.error(self._last_error)
            return self._error_response(self._last_error)

    async def search_flights_rttc(
        self,
        route: str,
        flight_date: str,
        passengers: int = 2,
        cabin_class: str = None
    ) -> Dict[str, Any]:
        """
        Search flights via RTTC aggregated endpoint.

        Uses GET /api/v1/travel-services/flights/search on the platform.

        Args:
            route: Route in IATA format e.g. "JNB-CPT"
            flight_date: Flight date (YYYY-MM-DD)
            passengers: Number of passengers (default: 2)
            cabin_class: Optional cabin class filter

        Returns:
            Dict with success, flights[], and metadata
        """
        if not rates_circuit.can_execute():
            logger.warning("Rates Engine circuit breaker OPEN — skipping RTTC flight search")
            return {"success": False, "flights": [], "error": "Circuit breaker open"}

        url = f"{self.base_url}/api/v1/travel-services/flights/search"
        params = {
            "route": route,
            "date": flight_date,
            "passengers": passengers,
        }
        if cabin_class:
            params["cabin_class"] = cabin_class

        try:
            async with httpx.AsyncClient() as client:
                logger.info(f"RTTC flight search: route={route}, date={flight_date}")
                r = await client.get(url, params=params, timeout=60.0)
                r.raise_for_status()
                data = r.json()
                rates_circuit.record_success()

                flights = data.get("flights", [])
                logger.info(f"RTTC flight search complete: {len(flights)} flights for {route}")
                return {
                    "success": True,
                    "flights": flights,
                    "total_flights": len(flights),
                    "route": route,
                    "date": flight_date,
                    "source": "rttc",
                }
        except httpx.TimeoutException:
            self._last_error = "RTTC flight search timed out after 60s"
            logger.error(self._last_error)
            rates_circuit.record_failure()
            return {"success": False, "flights": [], "error": self._last_error}
        except httpx.HTTPStatusError as e:
            self._last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"RTTC flight search HTTP error: {self._last_error}")
            rates_circuit.record_failure()
            return {"success": False, "flights": [], "error": self._last_error}
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"RTTC flight search error: {self._last_error}")
            rates_circuit.record_failure()
            return {"success": False, "flights": [], "error": self._last_error}

    async def search_rttc_flights_direct(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str = None,
        adults: int = 2,
        cabin_class: str = None
    ) -> Dict[str, Any]:
        """
        Search flights via RTTC direct endpoint with round-trip support.

        Uses GET /api/v1/travel-services/rttc/flights on the platform.
        Returns outbound_flights[] and return_flights[] for round-trip searches.

        Args:
            origin: Origin IATA code (e.g. "JNB")
            destination: Destination IATA code (e.g. "CPT")
            departure_date: Departure date (YYYY-MM-DD)
            return_date: Optional return date for round-trip (YYYY-MM-DD)
            adults: Number of adults (default: 2)
            cabin_class: Optional cabin class filter

        Returns:
            Dict with success, outbound_flights[], return_flights[], and metadata
        """
        if not rates_circuit.can_execute():
            logger.warning("Rates Engine circuit breaker OPEN — skipping RTTC direct flight search")
            return {
                "success": False,
                "outbound_flights": [],
                "return_flights": [],
                "error": "Circuit breaker open",
            }

        url = f"{self.base_url}/api/v1/travel-services/rttc/flights"
        params = {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "adults": adults,
        }
        if return_date:
            params["return_date"] = return_date
        if cabin_class:
            params["cabin_class"] = cabin_class

        try:
            async with httpx.AsyncClient() as client:
                logger.info(
                    f"RTTC direct flight search: {origin}->{destination}, "
                    f"depart={departure_date}, return={return_date}"
                )
                r = await client.get(url, params=params, timeout=60.0)
                r.raise_for_status()
                data = r.json()
                rates_circuit.record_success()

                outbound = data.get("outbound_flights", data.get("flights", []))
                return_flights = data.get("return_flights", [])
                logger.info(
                    f"RTTC direct search complete: {len(outbound)} outbound, "
                    f"{len(return_flights)} return flights"
                )
                return {
                    "success": True,
                    "outbound_flights": outbound,
                    "return_flights": return_flights,
                    "origin": origin,
                    "destination": destination,
                    "departure_date": departure_date,
                    "return_date": return_date,
                    "source": "rttc_direct",
                }
        except httpx.TimeoutException:
            self._last_error = "RTTC direct flight search timed out after 60s"
            logger.error(self._last_error)
            rates_circuit.record_failure()
            return {
                "success": False,
                "outbound_flights": [],
                "return_flights": [],
                "error": self._last_error,
            }
        except httpx.HTTPStatusError as e:
            self._last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"RTTC direct flight search HTTP error: {self._last_error}")
            rates_circuit.record_failure()
            return {
                "success": False,
                "outbound_flights": [],
                "return_flights": [],
                "error": self._last_error,
            }
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"RTTC direct flight search error: {self._last_error}")
            rates_circuit.record_failure()
            return {
                "success": False,
                "outbound_flights": [],
                "return_flights": [],
                "error": self._last_error,
            }

    async def get_flight_destinations(self) -> Dict[str, Any]:
        """Get destinations with flight data from platform."""
        if not rates_circuit.can_execute():
            logger.warning("Rates Engine circuit breaker OPEN — skipping flight destinations")
            return {"success": False, "destinations": [], "error": "Circuit breaker open"}

        url = f"{self.base_url}/api/v1/flights/destinations"
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(url, timeout=15.0)
                r.raise_for_status()
                rates_circuit.record_success()
                return {"success": True, **r.json()}
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Flight destinations failed: {e}")
            rates_circuit.record_failure()
            return {"success": False, "destinations": [], "error": str(e)}

    async def get_flight_price(
        self, destination: str, departure_date: str, return_date: str
    ) -> Dict[str, Any]:
        """Get matched round-trip flight price from platform."""
        if not rates_circuit.can_execute():
            logger.warning("Rates Engine circuit breaker OPEN — skipping flight price")
            return {"success": False, "error": "Circuit breaker open"}

        url = f"{self.base_url}/api/v1/flights/price"
        params = {
            "destination": destination,
            "departure_date": departure_date,
            "return_date": return_date,
        }
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(url, params=params, timeout=15.0)
                r.raise_for_status()
                rates_circuit.record_success()
                return {"success": True, **r.json()}
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Flight price lookup failed: {e}")
            rates_circuit.record_failure()
            return {"success": False, "error": str(e)}

    async def list_flights(
        self, destination: str = None, limit: int = 50, offset: int = 0
    ) -> Dict[str, Any]:
        """List flight records from platform."""
        if not rates_circuit.can_execute():
            logger.warning("Rates Engine circuit breaker OPEN — skipping flight list")
            return {"success": False, "flights": [], "error": "Circuit breaker open"}

        url = f"{self.base_url}/api/v1/flights/list"
        params = {"limit": limit, "offset": offset}
        if destination:
            params["destination"] = destination
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(url, params=params, timeout=15.0)
                r.raise_for_status()
                rates_circuit.record_success()
                return {"success": True, **r.json()}
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Flight list failed: {e}")
            rates_circuit.record_failure()
            return {"success": False, "flights": [], "error": str(e)}

    async def search_hotels_aggregated(
        self,
        destination: str,
        check_in: date,
        check_out: date,
        adults: int = 2,
        children: int = 0,
    ) -> Dict[str, Any]:
        """
        Multi-provider aggregated hotel search.

        Returns hotels from multiple providers (HotelBeds, Juniper, Hummingbird, RTTC)
        with normalized data format.
        """
        if not rates_circuit.can_execute():
            logger.warning("Rates Engine circuit breaker OPEN — skipping aggregated search")
            return self._error_response("Circuit breaker open")

        url = f"{self.base_url}/api/v1/travel-services/hotels/search/aggregated"
        params = {
            "destination": destination.lower(),
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "adults": adults,
            "children": children,
        }

        try:
            async with httpx.AsyncClient() as client:
                logger.info(
                    f"Aggregated hotel search: destination={destination}, "
                    f"dates={check_in} to {check_out}"
                )
                r = await client.get(url, params=params, timeout=self.timeout)
                r.raise_for_status()
                data = r.json()
                rates_circuit.record_success()

                # Normalize to match existing hotel format
                hotels = []
                for h in data.get("hotels", []):
                    # Parse star_rating (may be string like "5" or "4*")
                    raw_stars = h.get("star_rating")
                    try:
                        stars = int(str(raw_stars).replace("*", "")) if raw_stars else None
                    except (ValueError, TypeError):
                        stars = None

                    hotels.append({
                        "hotel_id": h.get("hotel_id"),
                        "hotel_name": html.unescape(h.get("name", "")),
                        "stars": stars,
                        "destination": h.get("destination"),
                        "zone": h.get("zone_name"),
                        "image_url": h.get("image_url"),
                        "latitude": float(h["latitude"]) if h.get("latitude") else None,
                        "longitude": float(h["longitude"]) if h.get("longitude") else None,
                        "cheapest_price": h.get("total_price"),
                        "cheapest_meal_plan": h.get("meal_plan"),
                        "source": h.get("source"),
                        "options": [{
                            "room_type": h.get("room_type", "Standard Room"),
                            "meal_plan": h.get("meal_plan", ""),
                            "price_total": h.get("total_price", 0),
                            "price_per_night": h.get("rate_per_night", 0),
                            "currency": h.get("currency", "EUR"),
                            "provider": h.get("source"),
                        }],
                    })

                # Filter out hotels with zero or missing pricing
                hotels = [h for h in hotels if h.get("cheapest_price") and h["cheapest_price"] > 0]

                # Filter out Juniper placeholder hotels
                hotels = [h for h in hotels if _is_quality_hotel(h)]

                logger.info(
                    f"Aggregated search complete: {len(hotels)} hotels (after price filter), "
                    f"aggregation={data.get('aggregation')}"
                )

                return {
                    "success": True,
                    "destination": data.get("destination", destination),
                    "check_in": data.get("check_in", check_in.isoformat()),
                    "check_out": data.get("check_out", check_out.isoformat()),
                    "nights": data.get("nights"),
                    "total_hotels": len(hotels),
                    "hotels": hotels,
                    "aggregation": data.get("aggregation"),
                }

        except httpx.TimeoutException:
            self._last_error = f"Aggregated search timed out after {self.timeout}s"
            logger.error(self._last_error)
            rates_circuit.record_failure()
            return self._error_response(self._last_error)

        except httpx.HTTPStatusError as e:
            self._last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"Aggregated search HTTP error: {self._last_error}")
            rates_circuit.record_failure()
            return self._error_response(self._last_error)

        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Aggregated search error: {self._last_error}")
            rates_circuit.record_failure()
            return self._error_response(self._last_error)

    async def search_hotels_by_names(
        self,
        destination: str,
        hotel_names: List[str],
        check_in: date,
        check_out: date,
        adults: int = 2,
        children_ages: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Search hotels by name - targeted search for specific hotels.

        NOTE: This endpoint requires hotel name mapping files to be configured.
        Use search_hotels() as the primary method until mapping is ready.

        Args:
            destination: Destination name
            hotel_names: List of hotel names to search
            check_in: Check-in date
            check_out: Check-out date
            adults: Number of adults
            children_ages: List of children ages

        Returns:
            Dict with matched hotels and their pricing
        """
        url = f"{self.base_url}/api/v1/availability/search-by-names"

        payload = {
            "destination": destination.lower(),
            "hotel_names": hotel_names,
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "adults": adults,
            "children_ages": children_ages or []
        }

        try:
            async with httpx.AsyncClient() as client:
                logger.info(
                    f"Rates Engine search-by-names: destination={destination}, "
                    f"hotels={len(hotel_names)}"
                )

                r = await client.post(url, json=payload, timeout=self.timeout)
                r.raise_for_status()
                data = r.json()

                return {
                    "success": True,
                    **data
                }

        except httpx.TimeoutException:
            self._last_error = f"Request timed out after {self.timeout}s"
            logger.error(f"Rates Engine timeout: {self._last_error}")
            return self._error_response(self._last_error)

        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Rates Engine error: {self._last_error}")
            return self._error_response(self._last_error)

    @retry_on_async_network_error(max_attempts=2, min_wait=3, max_wait=15)
    async def _post_with_retry(self, url: str, payload: dict) -> dict:
        """POST with retry on transient network errors. Returns parsed JSON."""
        async with httpx.AsyncClient() as client:
            logger.info(
                f"Rates Engine search: destination={payload.get('destination')}, "
                f"dates={payload.get('check_in')} to {payload.get('check_out')}"
            )
            r = await client.post(url, json=payload, timeout=self.timeout)
            r.raise_for_status()
            return r.json()

    def _error_response(self, error: str) -> Dict[str, Any]:
        """Return error response structure."""
        return {
            "success": False,
            "hotels": [],
            "total_hotels": 0,
            "error": error
        }

    def get_status(self) -> Dict[str, Any]:
        """Get client status."""
        return {
            "initialized": self._initialized,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "last_error": self._last_error
        }


# Singleton accessor
_client: Optional[TravelPlatformRatesClient] = None


def get_travel_platform_rates_client() -> TravelPlatformRatesClient:
    """Get the singleton Rates Engine client."""
    global _client
    if _client is None:
        _client = TravelPlatformRatesClient()
    return _client


def reset_travel_platform_rates_client():
    """Reset the singleton client (for testing)."""
    global _client
    TravelPlatformRatesClient._instance = None
    _client = None
