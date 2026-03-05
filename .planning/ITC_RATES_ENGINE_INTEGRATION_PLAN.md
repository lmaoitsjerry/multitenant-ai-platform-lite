# ITC Platform - Rates Engine Integration Plan

## Overview

This document outlines the plan to connect the ITC (Intelligent Travel Concierge) Platform to the Zorah Travel Platform Rates Engine for real-time hotel availability, flights, transfers, and activities.

---

## IMPLEMENTATION STATUS

> **Updated 2026-02-04**

### Current Status Summary

| Service | Integration | Data Status | UI Status | Notes |
|---------|-------------|-------------|-----------|-------|
| **Hotels** | Juniper + HotelBeds | Live data | Working | Juniper via `/api/v1/rates/hotels/search`, HotelBeds via `/api/v1/hotelbeds/hotels/search` |
| **Flights** | BigQuery | No data | Graceful fallback | Tables empty - needs population |
| **Activities** | HotelBeds APItude | Live data | Working | HotelBeds live activities, fallback to sample data |
| **Transfers** | HotelBeds APItude | Live data | Working | HotelBeds live transfers, fallback to BigQuery |
| **"Direct flights"** | N/A | N/A | Client-side filter | Not supported by API |

### HotelBeds Integration (NEW)

The platform now integrates with HotelBeds APItude for:
- **Hotels**: Global inventory with real-time availability (alternative to Juniper)
- **Activities**: Live tours, excursions, and experiences
- **Transfers**: Airport and ground transportation

**API Endpoints:**
- `GET /api/v1/hotelbeds/health` - Health check
- `GET /api/v1/hotelbeds/hotels/search` - Hotel search
- `GET /api/v1/hotelbeds/activities/search` - Activities search
- `GET /api/v1/hotelbeds/transfers/search` - Transfers search

**Client:** `src/services/hotelbeds_client.py`
**Routes:** `src/api/hotelbeds_routes.py`

**Currency:** All HotelBeds prices are in EUR

### Frontend Pages

- `/travel/hotels` - Hotel search with room/pax selector
- `/travel/packages` - Holiday packages (hotels + flights combined search)
- `/travel/activities` - Activities browser (sample data)
- `/travel/flights` - Flight pricing (coming soon)
- `/travel/transfers` - Transfer pricing (coming soon)

---

## IMPORTANT: Current Recommendations

> **Updated 2026-01-28**

### Hotel Search Strategy
**USE FULL SEARCH** (`/api/v1/availability/search`) as the primary method:
- Works with live Juniper data out of the box
- Set `max_hotels: 50` for reasonable response times (30-60s)
- No hotel name mapping required

**DEFER search-by-names** (`/api/v1/availability/search-by-names`) until:
- Hotel name mapping files are created
- Needed for targeted pricing of specific recommended hotels

### Flights/Transfers/Activities
**SKIP FOR INITIAL INTEGRATION** - These tables need to be populated with data first:
- `flights` table: Empty
- `transfers` table: Empty
- `activities` table: Empty

Focus on hotels first, add other services once data is available.

---

## 1. Architecture

### Current State
```
ITC Platform → RAG (Knowledge Search) ✅ Connected
ITC Platform → Rates Engine ❌ Not Connected
```

### Target State (Phase 1 - Hotels Only)
```
ITC Platform
    ├── RAG API (Knowledge Search) ✅
    │   └── /api/v1/rag/search
    │
    └── Rates Engine API (Hotels) 🎯
        └── /api/v1/availability/search  (RECOMMENDED - Full search)
```

### Future State (Phase 2 - Full Travel Services)
```
ITC Platform
    └── Rates Engine API (Travel Services)
        ├── /api/v1/availability/search           (Hotels) ✅
        ├── /api/v1/availability/search-by-names  (Hotels - when mapping ready)
        ├── /api/v1/travel-services/flights/search    (Future)
        ├── /api/v1/travel-services/transfers/search  (Future)
        └── /api/v1/travel-services/activities/search (Future)
```

---

## 2. API Endpoints Reference

### Base URL
```
https://zorah-travel-platform-1031318281967.us-central1.run.app
```

### Authentication
Currently NO authentication required for rates endpoints (can add JWT if needed).

---

### 2.1 Hotel Availability - Full Search (RECOMMENDED FOR NOW)

**Endpoint:** `POST /api/v1/availability/search`

**Use Case:** Primary hotel search - works with live Juniper data

**Request:**
```json
{
  "destination": "zanzibar",
  "check_in": "2026-03-15",
  "check_out": "2026-03-20",
  "rooms": [
    {"adults": 2, "children_ages": []}
  ],
  "max_hotels": 50
}
```

**Response:**
```json
{
  "destination": "zanzibar",
  "check_in": "2026-03-15",
  "check_out": "2026-03-20",
  "nights": 5,
  "total_hotels": 50,
  "hotels": [
    {
      "hotel_id": "JP01043K",
      "hotel_name": "Ocean Paradise Resort & Spa",
      "stars": 5,
      "priority": 1,
      "image_url": "https://...",
      "options": [
        {
          "room_type": "Superior Ocean View",
          "meal_plan": "Half Board",
          "price_total": 45000,
          "price_per_night": 9000,
          "currency": "ZAR",
          "availability": "available",
          "occupancy": 2
        }
      ],
      "cheapest_price": 45000,
      "cheapest_meal_plan": "Half Board"
    }
  ],
  "search_time_seconds": 45.3
}
```

**Performance:** 30-60 seconds with `max_hotels: 50`

**Important:** Always set `max_hotels` to limit results:
- `max_hotels: 50` → ~30-60 seconds (recommended)
- `max_hotels: 100` → ~60-90 seconds
- `max_hotels: 500` → 60-120 seconds (avoid)

---

### 2.2 Hotel Availability - By Names (FUTURE - When Mapping Ready)

**Endpoint:** `POST /api/v1/availability/search-by-names`

**Use Case:** When ITC has specific hotels to price (e.g., from RAG recommendations)

**Status:** Requires hotel name mapping files to be created first

**Request:**
```json
{
  "destination": "zanzibar",
  "hotel_names": [
    "Ocean Paradise Resort",
    "Diamonds Mapenzi Beach",
    "Baraza Resort"
  ],
  "check_in": "2026-03-15",
  "check_out": "2026-03-20",
  "adults": 2,
  "children_ages": []
}
```

**Response:**
```json
{
  "destination": "zanzibar",
  "check_in": "2026-03-15",
  "check_out": "2026-03-20",
  "nights": 5,
  "hotels": [
    {
      "hotel_id": "JP01043K",
      "hotel_name": "Ocean Paradise Resort & Spa",
      "match_score": 0.95,
      "match_type": "normalized_exact",
      "requested_name": "Ocean Paradise Resort",
      "destination": "Zanzibar",
      "stars": 5,
      "options": [...],
      "cheapest_price": 45000
    }
  ],
  "unmatched_hotels": ["Some Unknown Hotel"],
  "search_time_seconds": 5.2
}
```

**Performance:** 5-10 seconds (once mapping is ready)

---

### 2.3 Health Check

**Endpoint:** `GET /api/v1/travel-services/health`

**Response:**
```json
{
  "status": "healthy",
  "providers": {
    "juniper": "connected",
    "bigquery": "connected"
  }
}
```

---

### 2.4 Flight/Transfer/Activity Search (FUTURE - Data Not Available)

These endpoints exist but require data population:

| Service | Endpoint | Status |
|---------|----------|--------|
| Flights | `GET /api/v1/travel-services/flights/search` | Data needed |
| Transfers | `GET /api/v1/travel-services/transfers/search` | Data needed |
| Activities | `GET /api/v1/travel-services/activities/search` | Data needed |

---

## 3. Implementation Steps

### Phase 1: Create Rates Client (Day 1)

Create a client class in ITC Platform to interact with the Rates Engine.

**File:** `src/services/travel_platform_rates_client.py`

```python
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
from typing import List, Dict, Optional
from datetime import date
import httpx

logger = logging.getLogger(__name__)


class TravelPlatformRatesClient:
    """Client for Zorah Travel Platform Rates Engine"""

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
        self._last_error = None

        logger.info(
            f"Rates Engine client initialized: url={self.base_url}, timeout={self.timeout}s"
        )

    async def is_available(self) -> bool:
        """Check if rates engine is available"""
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{self.base_url}/api/v1/travel-services/health",
                    timeout=10.0
                )
                if r.status_code == 200:
                    data = r.json()
                    return data.get("status") == "healthy"
                return False
        except Exception as e:
            logger.warning(f"Rates Engine health check failed: {e}")
            self._last_error = str(e)
            return False

    async def search_hotels(
        self,
        destination: str,
        check_in: date,
        check_out: date,
        adults: int = 2,
        children_ages: List[int] = None,
        max_hotels: int = 50  # Recommended limit for reasonable response times
    ) -> Dict:
        """
        Full hotel availability search using live Juniper data.

        Args:
            destination: Destination name (e.g., "zanzibar", "mauritius")
            check_in: Check-in date
            check_out: Check-out date
            adults: Number of adults (default: 2)
            children_ages: List of children ages (default: empty)
            max_hotels: Maximum hotels to return (default: 50, recommended)

        Returns:
            Dict with hotels, prices, and availability
        """
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    f"{self.base_url}/api/v1/availability/search",
                    json={
                        "destination": destination,
                        "check_in": check_in.isoformat(),
                        "check_out": check_out.isoformat(),
                        "rooms": [{"adults": adults, "children_ages": children_ages or []}],
                        "max_hotels": max_hotels
                    },
                    timeout=self.timeout
                )
                r.raise_for_status()
                data = r.json()

                logger.info(
                    f"Rates Engine search: destination={destination}, "
                    f"hotels={data.get('total_hotels', 0)}, "
                    f"time={data.get('search_time_seconds', 0):.1f}s"
                )

                return {
                    "success": True,
                    **data
                }

        except httpx.TimeoutException:
            self._last_error = f"Request timed out after {self.timeout}s"
            logger.error(f"Rates Engine timeout: {self._last_error}")
            return {"success": False, "error": self._last_error, "hotels": []}

        except httpx.HTTPStatusError as e:
            self._last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"Rates Engine HTTP error: {self._last_error}")
            return {"success": False, "error": self._last_error, "hotels": []}

        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Rates Engine error: {self._last_error}")
            return {"success": False, "error": self._last_error, "hotels": []}

    def get_status(self) -> Dict:
        """Get client status"""
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
```

---

### Phase 2: Add Configuration (Day 1)

**Add to ITC Platform `.env`:**
```env
# Rates Engine (Travel Platform)
RATES_ENGINE_URL=https://zorah-travel-platform-1031318281967.us-central1.run.app
RATES_ENGINE_TIMEOUT=120
```

---

### Phase 3: Create API Endpoint (Day 1-2)

**File:** `src/api/rates_routes.py`

```python
"""
Rates API Routes

Provides endpoints for hotel availability search via Travel Platform Rates Engine.
"""

from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.services.travel_platform_rates_client import get_travel_platform_rates_client

rates_router = APIRouter(prefix="/api/v1/rates", tags=["Rates"])


class HotelSearchRequest(BaseModel):
    destination: str
    check_in: date
    check_out: date
    adults: int = 2
    children_ages: list[int] = []
    max_hotels: int = 50


@rates_router.get("/health")
async def rates_health():
    """Check Rates Engine availability"""
    client = get_travel_platform_rates_client()
    available = await client.is_available()
    return {
        "success": True,
        "available": available,
        "status": client.get_status()
    }


@rates_router.post("/hotels/search")
async def search_hotels(request: HotelSearchRequest):
    """
    Search hotel availability.

    Uses live Juniper data via Travel Platform Rates Engine.
    Response time: 30-60 seconds with max_hotels=50.
    """
    client = get_travel_platform_rates_client()

    result = await client.search_hotels(
        destination=request.destination,
        check_in=request.check_in,
        check_out=request.check_out,
        adults=request.adults,
        children_ages=request.children_ages,
        max_hotels=request.max_hotels
    )

    return result
```

---

### Phase 4: Integrate with Quote Generation (Day 2-3)

Update the quote agent to use live rates:

```python
# In quote_agent.py or similar

async def get_hotel_rates_for_quote(
    destination: str,
    check_in: date,
    check_out: date,
    adults: int
) -> list:
    """Get live hotel rates for quote generation"""
    client = get_travel_platform_rates_client()

    result = await client.search_hotels(
        destination=destination,
        check_in=check_in,
        check_out=check_out,
        adults=adults,
        max_hotels=50
    )

    if not result.get("success"):
        # Fall back to static rates from BigQuery
        return await get_static_hotel_rates(destination, check_in, check_out)

    return result.get("hotels", [])
```

---

## 4. Available Destinations

| Destination | Juniper Code | Approx. Hotels |
|-------------|--------------|----------------|
| Zanzibar | JPD039707 | ~200+ |
| Mauritius | JPD034841 | ~150+ |
| Maldives | JPD034842 | ~100+ |
| Kenya | JPD034821 | ~80+ |
| Victoria Falls | JPD036577 | ~30+ |

---

## 5. Error Handling

### Timeout Handling
```python
try:
    hotels = await rates_client.search_hotels(...)
except Exception:
    # Fall back to static rates or cached data
    hotels = await get_cached_or_static_rates(destination)
```

### Graceful Degradation
```python
async def get_hotel_options(destination, ...):
    # Try live Juniper rates first
    result = await rates_client.search_hotels(destination, ...)

    if result.get("success") and result.get("hotels"):
        return result["hotels"]

    # Fall back to BigQuery static rates
    logger.warning("Live rates unavailable, using static rates")
    return await get_static_rates_from_bigquery(destination, ...)
```

---

## 6. Performance Considerations

| Operation | Expected Time | Notes |
|-----------|---------------|-------|
| Full hotel search (max_hotels=50) | 30-60 sec | **Recommended** |
| Full hotel search (max_hotels=100) | 60-90 sec | Use if needed |
| Full hotel search (max_hotels=500) | 60-120 sec | Avoid |
| Health check | <1 sec | Use for monitoring |

**Optimization Tips:**
1. Always set `max_hotels: 50` for initial implementation
2. Cache results for repeat searches (consider 5-15 min TTL)
3. Show loading state in UI (search can take 30-60 seconds)
4. Consider background prefetch for popular destinations

---

## 7. Testing Checklist

### Phase 1 (Hotels Only)
- [ ] Health check returns healthy
- [ ] Full hotel search returns results for Zanzibar
- [ ] Full hotel search returns results for Mauritius
- [ ] Timeout handling works (test with slow network)
- [ ] Error responses handled gracefully
- [ ] Quote generation uses live rates

### Phase 2 (Future - When Data Available)
- [ ] Flight search returns results
- [ ] Transfer search returns results
- [ ] Activity search returns results
- [ ] Hotel search-by-names works with mapping

---

## 8. Next Steps

### Immediate (Phase 1)
1. **Implement the rates client** (`travel_platform_rates_client.py`)
2. **Add rates routes** (`rates_routes.py`)
3. **Test hotel search** for Zanzibar and Mauritius
4. **Integrate with quote generation**

### Future (Phase 2)
1. Create hotel name mapping files for search-by-names
2. Populate flights/transfers/activities tables
3. Add caching layer for frequent searches
4. Add authentication if needed (JWT tokens)

---

## Contact

For issues with the Rates Engine API:
- Cloud Run logs: `gcloud logging read "resource.type=cloud_run_revision"`
- BigQuery data: `zorah-475411.travel_platform`
- Juniper status: Contact AfricaStay support

---

---

## 9. UI Implementation Notes

### Search Bar Standardization (2026-02-04)

**Hotels Page** (`/travel/hotels`):
- Destination selector
- Departure date (check-in)
- Return date (check-out)
- Room/Pax selector (expandable dropdown with adults/children per room)
- CTA: "Search hotel"

**Holiday Packages Page** (`/travel/packages`):
- Departure airport selector (JNB, CPT, DUR)
- Destination selector
- Departure date
- Return date
- Room/Pax selector
- "Only direct flights" checkbox (client-side filter only)
- CTA: "Search offers"

### Graceful Fallbacks

When data is unavailable:
- **Flights**: Shows "Flight pricing coming soon" with links to Quote Generator
- **Transfers**: Shows "Transfer pricing coming soon" with links to Quote Generator
- **Activities**: Shows "Sample Data" badge and informational notice

### "Direct Flights Only" Feature

The "Only direct flights" checkbox is implemented as a **client-side filter only**. The rates engine API does not support this parameter. Options:

1. **Current**: UI checkbox shows notice that filter applies when flight data is available
2. **Future**: Could add server-side support if the rates engine adds this capability
3. **Alternative**: Remove the checkbox until API support is added

---

## 10. Next Steps to Enable Full Functionality

### To Enable Flight Pricing:
1. Populate BigQuery `flight_prices` table with data
2. Required columns: `destination`, `departure_date`, `return_date`, `price_per_person`, `airline`
3. Update `travel_services_routes.py` if schema changes

### To Enable Transfer Pricing:
1. Populate BigQuery `hotel_rates` table with `transfers_adult` and `transfers_child` columns
2. Ensure destination and hotel_name fields match hotel search results

### To Enable Live Activities:
1. Connect to Travel Platform activities API (when available)
2. Replace `SAMPLE_ACTIVITIES` in `travel_services_routes.py` with API calls

---

*Last Updated: 2026-02-04*
