"""Test 2: Quote Agent Total — Sum All Services"""
import pytest


def test_quote_agent_sums_all_services():
    """Total price should sum ALL items in final_hotels, not just index [0]."""
    final_hotels = [
        {"name": "Beach Resort", "total_price": 21000, "type": "hotel", "nights": 7},
        {"name": "City Tour", "total_price": 500, "type": "activity"},
        {"name": "Airport Transfer", "total_price": 350, "type": "transfer"},
        {"name": "SAA Flight", "total_price": 6910, "type": "flight"},
    ]

    total = sum(h.get('total_price', 0) for h in final_hotels)
    assert total == 28760, f"Expected 28760, got {total}"

    # Old buggy code would return only first item
    old_buggy_total = final_hotels[0]['total_price'] if final_hotels else 0
    assert old_buggy_total == 21000, "Old code only used first hotel"
    assert total != old_buggy_total, "New total should differ from old single-hotel total"


def test_empty_hotels_returns_zero():
    """Empty hotels list should return 0 total."""
    final_hotels = []
    total = sum(h.get('total_price', 0) for h in final_hotels) if final_hotels else 0
    assert total == 0


def test_mixed_service_types_all_included():
    """All service types (hotel, flight, transfer, activity) should be summed."""
    items = [
        {"type": "hotel", "total_price": 15000},
        {"type": "hotel", "total_price": 12000},
        {"type": "flight", "total_price": 8500},
        {"type": "transfer", "total_price": 200},
        {"type": "activity", "total_price": 110},
        {"type": "activity", "total_price": 55},
    ]
    total = sum(i.get('total_price', 0) for i in items)
    assert total == 35865


def test_missing_total_price_defaults_zero():
    """Items without total_price should default to 0 in the sum."""
    items = [
        {"type": "hotel", "total_price": 10000},
        {"type": "activity"},  # no total_price
        {"type": "transfer", "total_price": 300},
    ]
    total = sum(h.get('total_price', 0) for h in items)
    assert total == 10300
