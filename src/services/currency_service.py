"""
Currency conversion service with live exchange rates.

Uses Frankfurter API (free, ECB data, no key needed) with 4-hour caching.
Supports per-tenant margin from tenant_config.pricing.currency_margin_pct.

Fallback: EUR_ZAR_RATE env var if Frankfurter API is unreachable.
"""

import os
import time
import logging
from typing import Dict, Optional

import httpx

logger = logging.getLogger(__name__)

# Singleton instance
_currency_service: Optional["CurrencyService"] = None


def get_currency_service() -> "CurrencyService":
    """Get or create singleton CurrencyService instance."""
    global _currency_service
    if _currency_service is None:
        _currency_service = CurrencyService()
    return _currency_service


class CurrencyService:
    """Live currency conversion with caching and per-tenant margin support."""

    CACHE_TTL = 14400  # 4 hours
    API_URL = "https://api.frankfurter.app/latest"

    def __init__(self):
        self._rates: Dict[str, float] = {}
        self._last_fetch: float = 0
        self._fallback_rate = float(os.getenv("EUR_ZAR_RATE", "20.5"))

    async def get_rate(self, from_currency: str, to_currency: str) -> float:
        """Fetch live rate with 4hr cache, fallback to env var."""
        if from_currency == to_currency:
            return 1.0

        cache_key = f"{from_currency}_{to_currency}"

        # Return cached rate if still fresh
        if cache_key in self._rates and (time.time() - self._last_fetch) < self.CACHE_TTL:
            return self._rates[cache_key]

        # Fetch from Frankfurter API
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    self.API_URL,
                    params={"from": from_currency.upper(), "to": to_currency.upper()},
                    timeout=10,
                )
                r.raise_for_status()
                data = r.json()
                rate = data.get("rates", {}).get(to_currency.upper())
                if rate:
                    self._rates[cache_key] = float(rate)
                    self._last_fetch = time.time()
                    logger.info(f"Currency rate fetched: 1 {from_currency} = {rate} {to_currency}")
                    return float(rate)
        except Exception as e:
            logger.warning(f"Frankfurter API failed, using fallback rate: {e}")

        # Fallback for common EUR→ZAR case
        if from_currency.upper() == "EUR" and to_currency.upper() == "ZAR":
            return self._fallback_rate

        # For other pairs, check if we have a stale cached rate
        if cache_key in self._rates:
            logger.warning(f"Using stale cached rate for {cache_key}")
            return self._rates[cache_key]

        # Last resort: return 1.0 (no conversion) and log error
        logger.error(f"No rate available for {from_currency} → {to_currency}, returning 1.0")
        return 1.0

    async def convert(
        self,
        amount: float,
        from_currency: str,
        to_currency: str = "ZAR",
        margin_pct: float = 5.0,
    ) -> Dict:
        """Convert with margin. Caller passes tenant's margin_pct from config."""
        if from_currency.upper() == to_currency.upper():
            return {
                "amount": round(amount, 2),
                "currency": to_currency,
                "original_amount": amount,
                "original_currency": from_currency,
                "rate": 1.0,
                "margin": 0,
            }

        rate = await self.get_rate(from_currency, to_currency)
        converted = round(amount * rate * (1 + margin_pct / 100), 2)
        return {
            "amount": converted,
            "currency": to_currency,
            "original_amount": amount,
            "original_currency": from_currency,
            "rate": rate,
            "margin": margin_pct,
        }
