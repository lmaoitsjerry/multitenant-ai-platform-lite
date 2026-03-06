"""
Tests for CurrencyService — exchange rate fetching, caching, conversion, and fallback.
"""

import os
import time
import pytest
import httpx
from unittest.mock import patch, AsyncMock, MagicMock

from src.services.currency_service import CurrencyService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def svc():
    """Fresh CurrencyService instance (no singleton)."""
    return CurrencyService()


@pytest.fixture
def mock_frankfurter_eur_zar():
    """Mock httpx to return a realistic EUR→ZAR rate."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "amount": 1.0,
        "base": "EUR",
        "date": "2026-03-05",
        "rates": {"ZAR": 20.12},
    }
    mock_response.raise_for_status = MagicMock()
    return mock_response


@pytest.fixture
def mock_frankfurter_usd_zar():
    """Mock httpx to return a realistic USD→ZAR rate."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "amount": 1.0,
        "base": "USD",
        "date": "2026-03-05",
        "rates": {"ZAR": 18.45},
    }
    mock_response.raise_for_status = MagicMock()
    return mock_response


# ---------------------------------------------------------------------------
# get_rate tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_same_currency_returns_one(svc):
    """Same-currency conversion should return rate 1.0 without API call."""
    rate = await svc.get_rate("ZAR", "ZAR")
    assert rate == 1.0


@pytest.mark.asyncio
async def test_rate_fetched_from_api(svc, mock_frankfurter_eur_zar):
    """Should fetch live rate from Frankfurter API."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_frankfurter_eur_zar)

    with patch("src.services.currency_service.httpx.AsyncClient", return_value=mock_client):
        rate = await svc.get_rate("EUR", "ZAR")

    assert rate == 20.12
    mock_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_rate_cached(svc, mock_frankfurter_eur_zar):
    """Second call should use cache, not hit API again."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_frankfurter_eur_zar)

    with patch("src.services.currency_service.httpx.AsyncClient", return_value=mock_client):
        await svc.get_rate("EUR", "ZAR")
        rate2 = await svc.get_rate("EUR", "ZAR")

    assert rate2 == 20.12
    assert mock_client.get.call_count == 1  # Only one API call


@pytest.mark.asyncio
async def test_cache_expires(svc, mock_frankfurter_eur_zar):
    """Cache should expire after TTL, triggering a fresh API call."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_frankfurter_eur_zar)

    with patch("src.services.currency_service.httpx.AsyncClient", return_value=mock_client):
        await svc.get_rate("EUR", "ZAR")
        # Simulate cache expiry
        svc._last_fetch = time.time() - (svc.CACHE_TTL + 1)
        await svc.get_rate("EUR", "ZAR")

    assert mock_client.get.call_count == 2


@pytest.mark.asyncio
async def test_fallback_eur_zar_on_api_failure(svc):
    """When API fails, should fall back to EUR_ZAR_RATE env var."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))

    with patch("src.services.currency_service.httpx.AsyncClient", return_value=mock_client):
        rate = await svc.get_rate("EUR", "ZAR")

    assert rate == svc._fallback_rate


@pytest.mark.asyncio
async def test_fallback_env_var():
    """EUR_ZAR_RATE env var should override default fallback."""
    with patch.dict(os.environ, {"EUR_ZAR_RATE": "22.0"}):
        svc = CurrencyService()
    assert svc._fallback_rate == 22.0


@pytest.mark.asyncio
async def test_unknown_pair_returns_one(svc):
    """Unknown currency pair with no cache should return 1.0 as last resort."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))

    with patch("src.services.currency_service.httpx.AsyncClient", return_value=mock_client):
        rate = await svc.get_rate("GBP", "ZAR")

    assert rate == 1.0


# ---------------------------------------------------------------------------
# convert tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_convert_same_currency(svc):
    """Same-currency conversion returns amount unchanged, margin 0."""
    result = await svc.convert(100.0, "ZAR", "ZAR")
    assert result["amount"] == 100.0
    assert result["rate"] == 1.0
    assert result["margin"] == 0
    assert result["currency"] == "ZAR"


@pytest.mark.asyncio
async def test_convert_with_margin(svc, mock_frankfurter_eur_zar):
    """Conversion should apply margin on top of rate."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_frankfurter_eur_zar)

    with patch("src.services.currency_service.httpx.AsyncClient", return_value=mock_client):
        result = await svc.convert(100.0, "EUR", "ZAR", margin_pct=5.0)

    # 100 * 20.12 * 1.05 = 2112.60
    assert result["amount"] == 2112.6
    assert result["rate"] == 20.12
    assert result["margin"] == 5.0
    assert result["original_amount"] == 100.0
    assert result["original_currency"] == "EUR"
    assert result["currency"] == "ZAR"


@pytest.mark.asyncio
async def test_convert_zero_margin(svc, mock_frankfurter_eur_zar):
    """Zero margin should give raw converted amount."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_frankfurter_eur_zar)

    with patch("src.services.currency_service.httpx.AsyncClient", return_value=mock_client):
        result = await svc.convert(50.0, "EUR", "ZAR", margin_pct=0.0)

    # 50 * 20.12 * 1.0 = 1006.0
    assert result["amount"] == 1006.0


@pytest.mark.asyncio
async def test_convert_result_structure(svc, mock_frankfurter_eur_zar):
    """Convert result should contain all expected fields."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_frankfurter_eur_zar)

    with patch("src.services.currency_service.httpx.AsyncClient", return_value=mock_client):
        result = await svc.convert(10.0, "EUR", "ZAR")

    assert set(result.keys()) == {"amount", "currency", "original_amount", "original_currency", "rate", "margin"}


# ---------------------------------------------------------------------------
# Backend integration: _apply_activity_currency_conversion
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_activity_conversion_adds_zar_fields():
    """Backend conversion should add *_zar fields to non-ZAR activities."""
    from src.api.travel_services_routes import _apply_activity_currency_conversion

    activities = [
        {"name": "Snorkeling", "price_adult": 50.0, "price_child": 30.0, "currency": "EUR"},
        {"name": "Safari", "price_adult": 100.0, "currency": "ZAR"},  # Already ZAR — skip
    ]

    mock_svc = AsyncMock()
    mock_svc.convert = AsyncMock(side_effect=lambda amt, *a, **kw: {
        "amount": round(amt * 20.0 * 1.05, 2),
        "rate": 20.0,
    })

    with patch("src.services.currency_service.get_currency_service", return_value=mock_svc):
        result = await _apply_activity_currency_conversion(activities)

    # EUR activity should have _zar fields
    assert result[0]["price_adult_zar"] == 1050.0  # 50 * 20 * 1.05
    assert result[0]["price_child_zar"] == 630.0   # 30 * 20 * 1.05
    assert result[0]["original_currency"] == "EUR"

    # ZAR activity should NOT have _zar fields
    assert "price_adult_zar" not in result[1]


@pytest.mark.asyncio
async def test_transfer_conversion_adds_zar_fields():
    """Backend conversion should add *_zar fields to non-ZAR transfers."""
    from src.api.travel_services_routes import _apply_transfer_currency_conversion

    transfers = [
        {"price": 80.0, "transfers_adult": 80.0, "transfers_child": 40.0, "currency": "EUR"},
        {"price": 500.0, "transfers_adult": 500.0, "currency": "ZAR"},
    ]

    mock_svc = AsyncMock()
    mock_svc.convert = AsyncMock(side_effect=lambda amt, *a, **kw: {
        "amount": round(amt * 20.0 * 1.05, 2),
        "rate": 20.0,
    })

    with patch("src.services.currency_service.get_currency_service", return_value=mock_svc):
        result = await _apply_transfer_currency_conversion(transfers)

    assert result[0]["price_zar"] == 1680.0       # 80 * 20 * 1.05
    assert result[0]["transfers_adult_zar"] == 1680.0
    assert result[0]["transfers_child_zar"] == 840.0
    assert result[0]["original_currency"] == "EUR"

    assert "price_zar" not in result[1]


@pytest.mark.asyncio
async def test_activity_conversion_handles_api_failure():
    """If currency API fails, conversion should not crash — activity kept as-is."""
    from src.api.travel_services_routes import _apply_activity_currency_conversion

    activities = [
        {"name": "Diving", "price_adult": 120.0, "currency": "USD"},
    ]

    mock_svc = AsyncMock()
    mock_svc.convert = AsyncMock(side_effect=Exception("API down"))

    with patch("src.services.currency_service.get_currency_service", return_value=mock_svc):
        result = await _apply_activity_currency_conversion(activities)

    # Should not crash, activity stays as-is
    assert result[0]["price_adult"] == 120.0
    assert "price_adult_zar" not in result[0]
