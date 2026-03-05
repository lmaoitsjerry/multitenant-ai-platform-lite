"""
HotelBeds API Client

Connects to the Zorah Travel Platform HotelBeds endpoints for:
- Hotels: Global hotel inventory with real-time availability
- Activities: Tours, excursions, and experiences
- Transfers: Airport transfers and ground transportation

The HotelBeds API provides live data that supplements/replaces BigQuery static data.

Configuration via environment variables:
- HOTELBEDS_API_URL: Base URL (default: Zorah Travel Platform Cloud Run)
- HOTELBEDS_API_TIMEOUT: Request timeout in seconds (default: 60)
"""

import os
import logging
from typing import List, Dict, Optional, Any
from datetime import date

import httpx

from src.utils.circuit_breaker import hotelbeds_circuit

logger = logging.getLogger(__name__)


class HotelBedsClient:
    """
    Client for HotelBeds API via Zorah Travel Platform.

    Provides live data for hotels, activities, and transfers.
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
            "HOTELBEDS_API_URL",
            "http://localhost:8080"
        )
        self.timeout = float(os.getenv("HOTELBEDS_API_TIMEOUT", "60"))
        self._initialized = True
        self._last_error: Optional[str] = None

        logger.info(
            f"HotelBeds client initialized: url={self.base_url}, timeout={self.timeout}s"
        )

    async def health_check(self) -> Dict[str, Any]:
        """
        Check HotelBeds API health status.

        Returns:
            Dict with status, environment, and available services
        """
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{self.base_url}/api/v1/hotelbeds/health",
                    timeout=10.0
                )
                if r.status_code == 200:
                    data = r.json()
                    logger.debug(f"HotelBeds health: {data.get('status')}")
                    return {
                        "success": True,
                        "available": data.get("status") == "healthy",
                        **data
                    }
                return {
                    "success": False,
                    "available": False,
                    "error": f"HTTP {r.status_code}"
                }
        except Exception as e:
            logger.warning(f"HotelBeds health check failed: {e}")
            self._last_error = str(e)
            return {
                "success": False,
                "available": False,
                "error": str(e)
            }

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
        Search hotels via HotelBeds API.

        Args:
            destination: Destination name (e.g., "zanzibar", "mauritius")
            check_in: Check-in date
            check_out: Check-out date
            adults: Number of adults (default: 2)
            children_ages: List of children ages (optional)
            max_hotels: Maximum hotels to return (default: 50)

        Returns:
            Dict with hotels array and metadata
        """
        if not hotelbeds_circuit.can_execute():
            logger.warning("HotelBeds circuit breaker OPEN — skipping search")
            return self._error_response("Circuit breaker open")

        try:
            params = {
                "destination": destination.lower(),
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "adults": adults,
                "max_hotels": max_hotels
            }

            async with httpx.AsyncClient() as client:
                logger.info(f"HotelBeds hotel search: {destination}, {check_in} to {check_out}")

                # Use POST if children_ages provided, otherwise GET
                if children_ages:
                    r = await client.post(
                        f"{self.base_url}/api/v1/hotelbeds/hotels/search",
                        json={
                            **params,
                            "children_ages": children_ages
                        },
                        timeout=self.timeout
                    )
                else:
                    r = await client.get(
                        f"{self.base_url}/api/v1/hotelbeds/hotels/search",
                        params=params,
                        timeout=self.timeout
                    )

                r.raise_for_status()
                data = r.json()

                hotelbeds_circuit.record_success()

                # Normalize hotels: ensure zone and provider fields are present
                hotels = data.get("hotels", [])
                for hotel in hotels:
                    hotel.setdefault("zone", hotel.get("zone_name") or hotel.get("location"))
                    # Tag each option with provider for frontend badge
                    for option in hotel.get("options", []):
                        option.setdefault("provider", "hotelbeds")

                logger.info(
                    f"HotelBeds hotel search complete: {data.get('count', 0)} hotels"
                )

                return {
                    "success": True,
                    "source": "hotelbeds",
                    **data
                }

        except httpx.TimeoutException:
            self._last_error = f"Request timed out after {self.timeout}s"
            logger.error(f"HotelBeds timeout: {self._last_error}")
            hotelbeds_circuit.record_failure()
            return self._error_response(self._last_error)

        except httpx.HTTPStatusError as e:
            self._last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"HotelBeds HTTP error: {self._last_error}")
            hotelbeds_circuit.record_failure()
            return self._error_response(self._last_error)

        except Exception as e:
            self._last_error = str(e)
            logger.error(f"HotelBeds error: {self._last_error}")
            hotelbeds_circuit.record_failure()
            return self._error_response(self._last_error)

    async def search_activities(
        self,
        destination: str,
        participants: int = 2
    ) -> Dict[str, Any]:
        """
        Search activities via HotelBeds API.

        Args:
            destination: Destination name (e.g., "zanzibar", "mauritius")
            participants: Number of participants (default: 2)

        Returns:
            Dict with activities array and metadata
        """
        if not hotelbeds_circuit.can_execute():
            logger.warning("HotelBeds circuit breaker OPEN — skipping activities search")
            return self._error_response("Circuit breaker open")

        try:
            params = {
                "destination": destination.lower(),
                "participants": participants
            }

            async with httpx.AsyncClient() as client:
                logger.info(f"HotelBeds activities search: {destination}, {participants} participants")

                r = await client.get(
                    f"{self.base_url}/api/v1/hotelbeds/activities/search",
                    params=params,
                    timeout=self.timeout
                )

                r.raise_for_status()
                data = r.json()

                hotelbeds_circuit.record_success()

                logger.info(
                    f"HotelBeds activities search complete: {data.get('count', 0)} activities"
                )

                return {
                    "success": True,
                    "source": "hotelbeds",
                    **data
                }

        except httpx.TimeoutException:
            self._last_error = f"Request timed out after {self.timeout}s"
            logger.error(f"HotelBeds activities timeout: {self._last_error}")
            hotelbeds_circuit.record_failure()
            return self._error_response(self._last_error)

        except httpx.HTTPStatusError as e:
            self._last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"HotelBeds activities HTTP error: {self._last_error}")
            hotelbeds_circuit.record_failure()
            return self._error_response(self._last_error)

        except Exception as e:
            self._last_error = str(e)
            logger.error(f"HotelBeds activities error: {self._last_error}")
            hotelbeds_circuit.record_failure()
            return self._error_response(self._last_error)

    async def search_transfers(
        self,
        route: str,
        transfer_date: date,
        passengers: int = 2
    ) -> Dict[str, Any]:
        """
        Search transfers via HotelBeds API.

        Args:
            route: Route description (e.g., "Zanzibar Airport to Stone Town")
            transfer_date: Transfer date
            passengers: Number of passengers (default: 2)

        Returns:
            Dict with transfers array and metadata
        """
        if not hotelbeds_circuit.can_execute():
            logger.warning("HotelBeds circuit breaker OPEN — skipping transfers search")
            return self._error_response("Circuit breaker open")

        try:
            params = {
                "route": route,
                "date": transfer_date.isoformat(),
                "passengers": passengers
            }

            async with httpx.AsyncClient() as client:
                logger.info(f"HotelBeds transfers search: {route}, {transfer_date}")

                r = await client.get(
                    f"{self.base_url}/api/v1/hotelbeds/transfers/search",
                    params=params,
                    timeout=self.timeout
                )

                r.raise_for_status()
                data = r.json()

                hotelbeds_circuit.record_success()

                logger.info(
                    f"HotelBeds transfers search complete: {data.get('count', 0)} transfers"
                )

                return {
                    "success": True,
                    "source": "hotelbeds",
                    **data
                }

        except httpx.TimeoutException:
            self._last_error = f"Request timed out after {self.timeout}s"
            logger.error(f"HotelBeds transfers timeout: {self._last_error}")
            hotelbeds_circuit.record_failure()
            return self._error_response(self._last_error)

        except httpx.HTTPStatusError as e:
            self._last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"HotelBeds transfers HTTP error: {self._last_error}")
            hotelbeds_circuit.record_failure()
            return self._error_response(self._last_error)

        except Exception as e:
            self._last_error = str(e)
            logger.error(f"HotelBeds transfers error: {self._last_error}")
            hotelbeds_circuit.record_failure()
            return self._error_response(self._last_error)

    async def check_rates(
        self,
        rate_key: str,
        rooms: int = 1
    ) -> Dict[str, Any]:
        """
        Pre-booking rate verification via HotelBeds.

        Confirms the current price for a rate_key from hotel search results.

        Args:
            rate_key: Rate key from hotel search results
            rooms: Number of rooms (default: 1)

        Returns:
            Dict with confirmed price information
        """
        if not hotelbeds_circuit.can_execute():
            logger.warning("HotelBeds circuit breaker OPEN — skipping rate check")
            return self._error_response("Circuit breaker open")

        try:
            payload = {
                "rate_key": rate_key,
                "rooms": rooms,
            }

            async with httpx.AsyncClient() as client:
                logger.info(f"HotelBeds check rates: rate_key={rate_key[:20]}...")

                r = await client.post(
                    f"{self.base_url}/api/v1/hotelbeds/checkrates",
                    json=payload,
                    timeout=self.timeout,
                )

                r.raise_for_status()
                data = r.json()

                hotelbeds_circuit.record_success()

                logger.info(f"HotelBeds check rates complete: {data.get('status', 'unknown')}")

                return {
                    "success": True,
                    "source": "hotelbeds",
                    **data,
                }

        except httpx.TimeoutException:
            self._last_error = f"Rate check timed out after {self.timeout}s"
            logger.error(f"HotelBeds rate check timeout: {self._last_error}")
            hotelbeds_circuit.record_failure()
            return self._error_response(self._last_error)

        except httpx.HTTPStatusError as e:
            self._last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"HotelBeds rate check HTTP error: {self._last_error}")
            hotelbeds_circuit.record_failure()
            return self._error_response(self._last_error)

        except Exception as e:
            self._last_error = str(e)
            logger.error(f"HotelBeds rate check error: {self._last_error}")
            hotelbeds_circuit.record_failure()
            return self._error_response(self._last_error)

    def _error_response(self, error: str) -> Dict[str, Any]:
        """Return error response structure."""
        return {
            "success": False,
            "error": error,
            "hotels": [],
            "activities": [],
            "transfers": [],
            "count": 0
        }

    def get_status(self) -> Dict[str, Any]:
        """Get client status."""
        return {
            "initialized": self._initialized,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "last_error": self._last_error,
            "circuit_breaker": hotelbeds_circuit.get_status()
        }


# Singleton accessor
_client: Optional[HotelBedsClient] = None


def get_hotelbeds_client() -> HotelBedsClient:
    """Get the singleton HotelBeds client."""
    global _client
    if _client is None:
        _client = HotelBedsClient()
    return _client


def reset_hotelbeds_client():
    """Reset the singleton client (for testing)."""
    global _client
    HotelBedsClient._instance = None
    _client = None
