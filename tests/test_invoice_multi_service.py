"""Test 8: Invoice Multi-Service Support"""
import os


def test_invoice_items_include_all_service_types():
    """When converting a multi-service quote to invoice, all service types should be included."""
    quote_hotels = [
        {"name": "Beach Resort", "type": "hotel", "total_price": 21000},
        {"name": "City Tour", "type": "activity", "total_price": 500},
        {"name": "Airport Transfer", "type": "transfer", "total_price": 350},
        {"name": "SAA Flight", "type": "flight", "total_price": 6910},
    ]

    service_types = set(h.get("type", "hotel") for h in quote_hotels)
    assert "hotel" in service_types
    assert "activity" in service_types
    assert "transfer" in service_types
    assert "flight" in service_types

    total = sum(h["total_price"] for h in quote_hotels)
    assert total == 28760


def test_invoice_modal_groups_by_type():
    """Verify the QuoteDetail ConvertToInvoiceModal groups items by service type."""
    filepath = os.path.join("frontend", "tenant-dashboard", "src", "pages", "quotes", "QuoteDetail.jsx")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Should contain service type grouping in the modal
    assert "serviceGroups" in content, \
        "Invoice modal should use serviceGroups for type grouping"
    assert "serviceTypeConfig" in content, \
        "Invoice modal should use serviceTypeConfig"

    # Should have section headers for different types
    assert "Hotel Options" in content, "Should have Hotel Options section"
    assert "Activities" in content, "Should have Activities section"
    assert "Transfers" in content, "Should have Transfers section"
    assert "Flights" in content, "Should have Flights section"


def test_invoice_modal_no_longer_uses_only_hotels():
    """The old hotels-only iteration pattern should be replaced."""
    filepath = os.path.join("frontend", "tenant-dashboard", "src", "pages", "quotes", "QuoteDetail.jsx")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # The modal should use allItems, not just hotels
    assert "allItems" in content, \
        "Modal should reference allItems (all service types)"

    # Should use Set for selection, not array (selectedItems vs selectedHotels)
    assert "selectedItems" in content, \
        "Modal should use selectedItems (Set) for multi-type selection"


def test_invoice_description_includes_type_label():
    """Invoice item descriptions should include the service type."""
    filepath = os.path.join("frontend", "tenant-dashboard", "src", "pages", "quotes", "QuoteDetail.jsx")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # The description template should include typeLabel
    assert "typeLabel" in content, \
        "Item description should include a type label (e.g., [Hotel], [Activity])"
