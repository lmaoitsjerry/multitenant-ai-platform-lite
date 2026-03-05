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
        children: int = 0,
        max_hotels: int = 50
    ) -> Dict[str, Any]:
        """
        Multi-provider aggregated hotel search.

        Delegates to the aggregated endpoint which searches Juniper, HotelBeds,
        Hummingbird, and RTTC in parallel with GPS-based deduplication.

        Args:
            destination: Destination name (e.g., "zanzibar", "mauritius")
            check_in: Check-in date
            check_out: Check-out date
            adults: Number of adults (default: 2)
            children: Number of children (default: 0)
            max_hotels: Maximum hotels to return (default: 50)

        Returns:
            Dict with merged hotel profiles including all_rates[], best_rate, sources, etc.
        """
        return await self.search_hotels_aggregated(
            destination=destination,
            check_in=check_in,
            check_out=check_out,
            adults=adults,
            children=children,
        )

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
        Multi-provider aggregated hotel search with merged profiles.

        Returns hotels from multiple providers (HotelBeds, Juniper, Hummingbird, RTTC)
        as merged profiles with all_rates[], best_rate, sources, merge_method, etc.
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

                # Pass through merged profiles from upstream
                hotels = []
                for h in data.get("hotels", []):
                    # Parse star_rating (may be string like "5" or "4*")
                    raw_stars = h.get("star_rating")
                    try:
                        star_rating = int(str(raw_stars).replace("*", "")) if raw_stars else None
                    except (ValueError, TypeError):
                        star_rating = None

                    # Unescape hotel name
                    name = h.get("name") or h.get("hotel_name") or ""
                    hotel_name = html.unescape(name)

                    # Pass through merged profile fields
                    best_rate = h.get("best_rate") or {}
                    all_rates = h.get("all_rates") or []
                    sources = h.get("sources") or ([h.get("source")] if h.get("source") else [])

                    # Determine cheapest price from best_rate or fallback
                    cheapest_price = (
                        best_rate.get("rate_per_night_zar")
                        or best_rate.get("rate_per_night")
                        or h.get("total_price")
                        or h.get("cheapest_price")
                        or 0
                    )

                    # Build backward-compatible options[] from all_rates[]
                    options = []
                    for rate in all_rates:
                        options.append({
                            "room_type": rate.get("room_type", "Standard Room"),
                            "meal_plan": rate.get("meal_plan", ""),
                            "price_total": rate.get("total_price") or rate.get("rate_per_night", 0),
                            "price_per_night": rate.get("rate_per_night", 0),
                            "price_per_night_zar": rate.get("rate_per_night_zar"),
                            "currency": rate.get("currency", "EUR"),
                            "source": rate.get("source"),
                            "provider": rate.get("source"),
                        })

                    # If no all_rates, build a single option from flat fields
                    if not options:
                        options.append({
                            "room_type": h.get("room_type", "Standard Room"),
                            "meal_plan": h.get("meal_plan", ""),
                            "price_total": h.get("total_price", 0),
                            "price_per_night": h.get("rate_per_night", 0),
                            "price_per_night_zar": h.get("rate_per_night_zar"),
                            "currency": h.get("currency", "EUR"),
                            "source": h.get("source"),
                            "provider": h.get("source"),
                        })

                    hotel = {
                        "hotel_id": h.get("hotel_id"),
                        "hotel_name": hotel_name,
                        "star_rating": star_rating,
                        "stars": star_rating,  # backward compat
                        "destination": h.get("destination"),
                        "zone": h.get("zone_name"),
                        "image_url": (h.get("image_url") or "").replace("http://photos.hotelbeds.com", "https://photos.hotelbeds.com") or None,
                        "latitude": float(h["latitude"]) if h.get("latitude") else None,
                        "longitude": float(h["longitude"]) if h.get("longitude") else None,
                        "cheapest_price": cheapest_price,
                        "cheapest_meal_plan": best_rate.get("meal_plan") or h.get("meal_plan"),
                        "best_rate": best_rate,
                        "all_rates": all_rates,
                        "sources": sources,
                        "source": sources[0] if sources else h.get("source"),
                        "merge_method": h.get("merge_method"),
                        "provider_codes": h.get("provider_codes"),
                        "options": options,
                        # Content enrichment fields (pass through from upstream when available)
                        "description": h.get("description"),
                        "amenities": h.get("amenities") or h.get("facilities"),
                        "address": h.get("address"),
                        "images": [img.replace("http://", "https://") if isinstance(img, str) else img for img in (h.get("images") or [])],
                    }
                    hotels.append(hotel)

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
                    "nights": data.get("nights") or (check_out - check_in).days,
                    "total_hotels": len(hotels),
                    "hotels": hotels,
                    "aggregation": data.get("aggregation"),
                    "response_format": data.get("response_format", "merged_profiles"),
                    "merge_stats": data.get("merge_stats"),
                    "provider_status": data.get("provider_status"),
                    "search_time_seconds": data.get("search_time_seconds", 0),
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

    async def search_transfers(
        self,
        from_code: str,
        to_code: str,
        transfer_date: str,
        passengers: int = 2,
        from_type: str = "IATA",
        to_type: str = "IATA",
    ) -> Dict[str, Any]:
        """
        Search transfers via unified Cloud Run endpoint.

        Args:
            from_code: Origin code (IATA or location)
            to_code: Destination code (IATA or location)
            transfer_date: Transfer date (YYYY-MM-DD)
            passengers: Number of passengers
            from_type: Origin code type ("IATA", "ATLAS", etc.)
            to_type: Destination code type ("IATA", "ATLAS", etc.)
        """
        if not rates_circuit.can_execute():
            return {"success": False, "transfers": [], "error": "Circuit breaker open"}

        url = f"{self.base_url}/api/v1/travel-services/transfers/search"
        params = {
            "from_code": from_code,
            "to_code": to_code,
            "date": transfer_date,
            "passengers": passengers,
            "from_type": from_type,
            "to_type": to_type,
        }

        try:
            async with httpx.AsyncClient() as client:
                logger.info(f"Transfer search: {from_code}->{to_code}, date={transfer_date}")
                r = await client.get(url, params=params, timeout=60.0)
                r.raise_for_status()
                data = r.json()
                rates_circuit.record_success()

                transfers = data.get("transfers", [])
                logger.info(f"Transfer search complete: {len(transfers)} results")
                return {
                    "success": True,
                    "transfers": transfers,
                    "total_transfers": len(transfers),
                    **{k: v for k, v in data.items() if k not in ("transfers",)},
                }
        except httpx.TimeoutException:
            self._last_error = "Transfer search timed out after 60s"
            logger.error(self._last_error)
            rates_circuit.record_failure()
            return {"success": False, "transfers": [], "error": self._last_error}
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Transfer search error: {self._last_error}")
            rates_circuit.record_failure()
            return {"success": False, "transfers": [], "error": self._last_error}

    async def search_activities(
        self,
        destination: str,
        participants: int = 2,
        activity_date: str = None,
    ) -> Dict[str, Any]:
        """
        Search activities via unified Cloud Run endpoint.

        Args:
            destination: Destination name
            participants: Number of participants
            activity_date: Optional activity date (YYYY-MM-DD)
        """
        if not rates_circuit.can_execute():
            return {"success": False, "activities": [], "error": "Circuit breaker open"}

        url = f"{self.base_url}/api/v1/travel-services/activities/search"
        params = {
            "destination": destination.lower(),
            "participants": participants,
        }
        if activity_date:
            params["activity_date"] = activity_date

        try:
            async with httpx.AsyncClient() as client:
                logger.info(f"Activity search: destination={destination}, participants={participants}")
                r = await client.get(url, params=params, timeout=60.0)
                r.raise_for_status()
                data = r.json()
                rates_circuit.record_success()

                activities = data.get("activities", [])
                logger.info(f"Activity search complete: {len(activities)} results")
                return {
                    "success": True,
                    "activities": activities,
                    "total_activities": len(activities),
                    **{k: v for k, v in data.items() if k not in ("activities",)},
                }
        except httpx.TimeoutException:
            self._last_error = "Activity search timed out after 60s"
            logger.error(self._last_error)
            rates_circuit.record_failure()
            return {"success": False, "activities": [], "error": self._last_error}
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Activity search error: {self._last_error}")
            rates_circuit.record_failure()
            return {"success": False, "activities": [], "error": self._last_error}

    async def search_car_rentals(
        self,
        city: str,
        pickup_date: str,
        dropoff_date: str,
        pickup_time: str = "10:00",
        dropoff_time: str = "10:00",
    ) -> Dict[str, Any]:
        """
        Search car rentals via RTTC GDS endpoint.

        Args:
            city: City name
            pickup_date: Pickup date (YYYY-MM-DD)
            dropoff_date: Dropoff date (YYYY-MM-DD)
            pickup_time: Pickup time (HH:MM)
            dropoff_time: Dropoff time (HH:MM)
        """
        if not rates_circuit.can_execute():
            return {"success": False, "car_rentals": [], "error": "Circuit breaker open"}

        url = f"{self.base_url}/api/v1/travel-services/rttc/car-rentals"
        params = {
            "city": city,
            "pickup_date": pickup_date,
            "dropoff_date": dropoff_date,
            "pickup_time": pickup_time,
            "dropoff_time": dropoff_time,
        }

        try:
            async with httpx.AsyncClient() as client:
                logger.info(f"Car rental search: city={city}, {pickup_date} to {dropoff_date}")
                r = await client.get(url, params=params, timeout=60.0)
                r.raise_for_status()
                data = r.json()
                rates_circuit.record_success()

                rentals = data.get("car_rentals", data.get("rentals", []))
                logger.info(f"Car rental search complete: {len(rentals)} results")
                return {
                    "success": True,
                    "car_rentals": rentals,
                    "total_car_rentals": len(rentals),
                    **{k: v for k, v in data.items() if k not in ("car_rentals", "rentals")},
                }
        except httpx.TimeoutException:
            self._last_error = "Car rental search timed out after 60s"
            logger.error(self._last_error)
            rates_circuit.record_failure()
            return {"success": False, "car_rentals": [], "error": self._last_error}
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Car rental search error: {self._last_error}")
            rates_circuit.record_failure()
            return {"success": False, "car_rentals": [], "error": self._last_error}

    async def search_buses(
        self,
        from_city: str,
        to_city: str,
        travel_date: str,
        adults: int = 1,
        children: int = 0,
    ) -> Dict[str, Any]:
        """
        Search bus routes via RTTC GDS endpoint.

        Args:
            from_city: Departure city
            to_city: Destination city
            travel_date: Travel date (YYYY-MM-DD)
            adults: Number of adults
            children: Number of children
        """
        if not rates_circuit.can_execute():
            return {"success": False, "buses": [], "error": "Circuit breaker open"}

        url = f"{self.base_url}/api/v1/travel-services/rttc/buses"
        params = {
            "from_city": from_city,
            "to_city": to_city,
            "travel_date": travel_date,
            "adults": adults,
            "children": children,
        }

        try:
            async with httpx.AsyncClient() as client:
                logger.info(f"Bus search: {from_city}->{to_city}, date={travel_date}")
                r = await client.get(url, params=params, timeout=60.0)
                r.raise_for_status()
                data = r.json()
                rates_circuit.record_success()

                buses = data.get("buses", [])
                logger.info(f"Bus search complete: {len(buses)} results")
                return {
                    "success": True,
                    "buses": buses,
                    "total_buses": len(buses),
                    **{k: v for k, v in data.items() if k not in ("buses",)},
                }
        except httpx.TimeoutException:
            self._last_error = "Bus search timed out after 60s"
            logger.error(self._last_error)
            rates_circuit.record_failure()
            return {"success": False, "buses": [], "error": self._last_error}
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Bus search error: {self._last_error}")
            rates_circuit.record_failure()
            return {"success": False, "buses": [], "error": self._last_error}

    async def get_bus_departure_points(self) -> Dict[str, Any]:
        """Get available bus departure points from RTTC GDS."""
        if not rates_circuit.can_execute():
            return {"success": False, "departure_points": [], "error": "Circuit breaker open"}

        url = f"{self.base_url}/api/v1/travel-services/rttc/buses/departure-points"
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(url, timeout=15.0)
                r.raise_for_status()
                data = r.json()
                rates_circuit.record_success()
                return {"success": True, **data}
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Bus departure points failed: {e}")
            rates_circuit.record_failure()
            return {"success": False, "departure_points": [], "error": str(e)}

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
