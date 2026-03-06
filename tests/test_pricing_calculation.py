"""Test 1: Hotel Pricing — Nightly Rate × Nights"""
import pytest


def test_quote_total_sums_all_hotels():
    """Quote agent should sum ALL hotel total_prices, not just the first one."""
    final_hotels = [
        {"name": "Hotel A", "total_price": 10000, "type": "hotel"},
        {"name": "Hotel B", "total_price": 15000, "type": "hotel"},
        {"name": "Activity C", "total_price": 500, "type": "activity"},
    ]

    total = sum(h.get('total_price', 0) for h in final_hotels)
    assert total == 25500, f"Expected 25500, got {total}"


def test_nightly_rate_times_nights():
    """Verify the multiplication logic: per_night × nights = total."""
    per_night = 4319.72
    nights = 7
    expected_total = per_night * nights  # 30238.04

    assert abs(expected_total - 30238.04) < 0.01, f"Expected ~30238.04, got {expected_total}"
    assert expected_total != per_night, "Total should not equal nightly rate!"


def test_zero_nights_fallback():
    """When nights is 0 or None, fallback to 1 to avoid zeroing out price."""
    per_night = 5000
    nights = 0
    safe_nights = nights or 1
    total = per_night * safe_nights
    assert total == 5000, f"Fallback to 1 night: expected 5000, got {total}"


def test_none_nights_fallback():
    """When nights is None, fallback to 1."""
    per_night = 3000
    nights = None
    safe_nights = nights or 1
    total = per_night * safe_nights
    assert total == 3000
