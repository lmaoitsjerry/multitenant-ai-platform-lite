"""
Travel Platform Rates Client

Connects to the Zorah Travel Platform Rates Engine for live hotel availability.
Uses the full search endpoint which works with live Juniper data.

Configuration via environment variables:
- RATES_ENGINE_URL: Base URL (default: https://zorah-travel-platform-...)
- RATES_ENGINE_TIMEOUT: Request timeout in seconds (default: 120)
"""

import os
import logging
from typing import List, Dict, Optional, Any
from datetime import date

import httpx

from src.utils.circuit_breaker import rates_circuit
from src.utils.retry_utils import retry_on_async_network_error

logger = logging.getLogger(__name__)


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
            "https://zorah-travel-platform-1031318281967.us-central1.run.app"
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

            logger.info(
                f"Rates Engine search complete: destination={destination}, "
                f"hotels={hotel_count}, time={search_time:.1f}s"
            )

            return {
                "success": True,
                "destination": data.get("destination", destination),
                "check_in": data.get("check_in", check_in.isoformat()),
                "check_out": data.get("check_out", check_out.isoformat()),
                "nights": data.get("nights", (check_out - check_in).days),
                "total_hotels": hotel_count,
                "hotels": data.get("hotels", []),
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
            rates_circuit.record_failure()
            return self._error_response(self._last_error)

        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Rates Engine error: {self._last_error}")
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
