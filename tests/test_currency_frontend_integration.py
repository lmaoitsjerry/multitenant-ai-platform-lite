"""
Tests verifying the frontend correctly uses ZAR-converted fields
for all service types (hotels, activities, transfers, flights).

Checks JSX source for the expected patterns — no runtime needed.
"""

import re
import pytest


HOLIDAY_PACKAGES_PATH = "frontend/tenant-dashboard/src/pages/travel/HolidayPackages.jsx"


@pytest.fixture
def jsx_source():
    with open(HOLIDAY_PACKAGES_PATH, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Hotels — already fixed in Round 7, verify still correct
# ---------------------------------------------------------------------------

class TestHotelZarPreference:
    def test_hotel_addtoquote_uses_display_price_zar(self, jsx_source):
        """Hotel AddToQuoteButton #1 should prefer display_price_zar."""
        assert "hotel.display_price_zar" in jsx_source

    def test_hotel_option_uses_rate_per_night_zar(self, jsx_source):
        """Hotel AddToQuoteButton #2 should prefer rate_per_night_zar."""
        assert "option.rate_per_night_zar" in jsx_source


# ---------------------------------------------------------------------------
# Activities — EUR→ZAR conversion
# ---------------------------------------------------------------------------

class TestActivityZarPreference:
    def test_activity_card_price_prefers_zar(self, jsx_source):
        """Activity card display should prefer price_per_person_zar or price_adult_zar."""
        assert "activity.price_per_person_zar" in jsx_source or "activity.price_adult_zar" in jsx_source

    def test_activity_addtoquote_uses_zar_price(self, jsx_source):
        """Activity AddToQuoteButton should use ZAR-converted price."""
        assert "activity.price_per_person_zar" in jsx_source

    def test_activity_child_price_prefers_zar(self, jsx_source):
        """Activity child price display should prefer price_child_zar."""
        assert "activity.price_child_zar" in jsx_source

    def test_no_hardcoded_eur_fallback(self, jsx_source):
        """Activity currency should NOT have hardcoded EUR fallback."""
        # Find activity AddToQuoteButton context
        activity_sections = re.findall(
            r"type:\s*['\"]activity['\"].*?currency:.*?\n",
            jsx_source,
            re.DOTALL,
        )
        for section in activity_sections:
            assert "'EUR'" not in section, f"Found hardcoded EUR fallback in activity section: {section[:100]}"


# ---------------------------------------------------------------------------
# Transfers — EUR→ZAR conversion
# ---------------------------------------------------------------------------

class TestTransferZarPreference:
    def test_transfer_card_price_prefers_zar(self, jsx_source):
        """Transfer card display should prefer price_zar."""
        assert "transfer.price_zar" in jsx_source

    def test_transfer_addtoquote_uses_zar(self, jsx_source):
        """Transfer AddToQuoteButton should use ZAR-converted price."""
        assert "transfer.price_zar" in jsx_source or "transfer.transfers_adult_zar" in jsx_source

    def test_transfer_currency_defaults_to_zar(self, jsx_source):
        """Transfer currency fallback should be ZAR, not EUR."""
        transfer_sections = re.findall(
            r"type:\s*['\"]transfer['\"].*?currency:.*?\n",
            jsx_source,
            re.DOTALL,
        )
        for section in transfer_sections:
            assert "'EUR'" not in section, f"Found EUR fallback in transfer section: {section[:100]}"


# ---------------------------------------------------------------------------
# Flights — already ZAR from backend
# ---------------------------------------------------------------------------

class TestFlightZarPreference:
    def test_flight_currency_defaults_to_zar(self, jsx_source):
        """Flight currency fallback should be ZAR."""
        # Find flight price display
        assert "flight.currency || 'ZAR'" in jsx_source or "flight.currency||'ZAR'" in jsx_source

    def test_flight_addtoquote_currency_zar(self, jsx_source):
        """Flight AddToQuoteButton currency should default to ZAR."""
        flight_sections = re.findall(
            r"type:\s*['\"]flight['\"].*?currency:.*?\n",
            jsx_source,
            re.DOTALL,
        )
        for section in flight_sections:
            assert "'EUR'" not in section, f"Found EUR fallback in flight section: {section[:100]}"


# ---------------------------------------------------------------------------
# Backend conversion functions exist
# ---------------------------------------------------------------------------

class TestBackendConversionExists:
    def test_activity_conversion_function_exists(self):
        """travel_services_routes should have _apply_activity_currency_conversion."""
        with open("src/api/travel_services_routes.py", "r", encoding="utf-8") as f:
            source = f.read()
        assert "async def _apply_activity_currency_conversion" in source

    def test_transfer_conversion_function_exists(self):
        """travel_services_routes should have _apply_transfer_currency_conversion."""
        with open("src/api/travel_services_routes.py", "r", encoding="utf-8") as f:
            source = f.read()
        assert "async def _apply_transfer_currency_conversion" in source

    def test_activity_endpoints_call_conversion(self):
        """Both activity endpoints should call _apply_activity_currency_conversion."""
        with open("src/api/travel_services_routes.py", "r", encoding="utf-8") as f:
            source = f.read()
        # Should be called at least 3 times (list_activities Cloud Run + fallback, search_activities Cloud Run + fallback)
        assert source.count("await _apply_activity_currency_conversion") >= 3

    def test_transfer_endpoints_call_conversion(self):
        """Both transfer endpoints should call _apply_transfer_currency_conversion."""
        with open("src/api/travel_services_routes.py", "r", encoding="utf-8") as f:
            source = f.read()
        assert source.count("await _apply_transfer_currency_conversion") >= 2
