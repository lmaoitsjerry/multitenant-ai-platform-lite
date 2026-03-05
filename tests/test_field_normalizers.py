"""Tests for src/utils/field_normalizers.py — canonical field name mapping."""

import pytest
from datetime import date, timedelta

from src.utils.field_normalizers import (
    normalize_quote_status,
    normalize_quote_dates,
    normalize_hotel_price,
    normalize_activity_price,
    normalize_transfer_price,
    normalize_kb_source,
    normalize_email_timestamp,
    normalize_invoice_create,
)


class TestNormalizeQuoteStatus:
    @pytest.mark.parametrize("input_val,expected", [
        ("Draft", "draft"),
        ("DRAFT", "draft"),
        ("generated", "quoted"),
        ("Quoted", "quoted"),
        ("rejected", "declined"),
        ("Accepted", "accepted"),
        ("Declined", "declined"),
        ("Expired", "expired"),
        ("Converted", "converted"),
        (None, "draft"),
        ("", "draft"),
        ("custom", "custom"),
    ])
    def test_normalizes_variants(self, input_val, expected):
        assert normalize_quote_status(input_val) == expected


class TestNormalizeQuoteDates:
    def test_remaps_date_suffix_fields(self):
        data = {"check_in_date": "2025-06-01", "check_out_date": "2025-06-05", "name": "Test"}
        result = normalize_quote_dates(data)
        assert result["check_in"] == "2025-06-01"
        assert result["check_out"] == "2025-06-05"
        assert "check_in_date" not in result
        assert "check_out_date" not in result

    def test_preserves_canonical_fields(self):
        data = {"check_in": "2025-06-01", "check_out": "2025-06-05"}
        result = normalize_quote_dates(data)
        assert result["check_in"] == "2025-06-01"
        assert result["check_out"] == "2025-06-05"

    def test_does_not_overwrite_existing_canonical(self):
        data = {"check_in": "2025-06-01", "check_in_date": "2025-07-01"}
        result = normalize_quote_dates(data)
        assert result["check_in"] == "2025-06-01"

    def test_preserves_other_fields(self):
        data = {"check_in_date": "2025-06-01", "customer_name": "John"}
        result = normalize_quote_dates(data)
        assert result["customer_name"] == "John"

    def test_empty_dict(self):
        assert normalize_quote_dates({}) == {}


class TestNormalizeHotelPrice:
    def test_prefers_rate_per_night(self):
        assert normalize_hotel_price({"rate_per_night": 150, "price_per_night": 200}) == 150.0

    def test_fallback_to_price_per_night(self):
        assert normalize_hotel_price({"price_per_night": 200}) == 200.0

    def test_fallback_to_nightly_rate(self):
        assert normalize_hotel_price({"nightly_rate": 180}) == 180.0

    def test_fallback_to_total_divided_by_nights(self):
        assert normalize_hotel_price({"total_price": 600}, nights=3) == 200.0

    def test_fallback_to_net_price(self):
        assert normalize_hotel_price({"net_price": 120}) == 120.0

    def test_returns_zero_when_empty(self):
        assert normalize_hotel_price({}) == 0.0

    def test_handles_non_numeric(self):
        assert normalize_hotel_price({"rate_per_night": "N/A"}) == 0.0

    def test_handles_none_values(self):
        assert normalize_hotel_price({"rate_per_night": None, "price_per_night": 100}) == 100.0

    def test_zero_nights_skips_total_division(self):
        assert normalize_hotel_price({"total_price": 600}, nights=0) == 0.0


class TestNormalizeActivityPrice:
    def test_prefers_price_per_person(self):
        assert normalize_activity_price({"price_per_person": 50, "price_adult": 75}) == 50.0

    def test_falls_back_to_price_adult(self):
        assert normalize_activity_price({"price_adult": 75}) == 75.0

    def test_falls_back_to_price(self):
        assert normalize_activity_price({"price": 30}) == 30.0

    def test_returns_zero_when_empty(self):
        assert normalize_activity_price({}) == 0.0

    def test_handles_non_numeric(self):
        assert normalize_activity_price({"price_per_person": "free"}) == 0.0


class TestNormalizeTransferPrice:
    def test_detects_per_person_model(self):
        result = normalize_transfer_price({"price": 25, "price_per_person": 25})
        assert result["pricing_model"] == "per_person"
        assert result["price"] == 25.0

    def test_defaults_to_per_transfer(self):
        result = normalize_transfer_price({"price": 100})
        assert result["pricing_model"] == "per_transfer"
        assert result["price"] == 100.0

    def test_explicit_pricing_model_preserved(self):
        result = normalize_transfer_price({"price": 50, "pricing_model": "per_vehicle"})
        assert result["pricing_model"] == "per_vehicle"

    def test_fallback_to_price_per_transfer(self):
        result = normalize_transfer_price({"price_per_transfer": 80})
        assert result["price"] == 80.0

    def test_empty_returns_zero(self):
        result = normalize_transfer_price({})
        assert result["price"] == 0.0
        assert result["pricing_model"] == "per_transfer"


class TestNormalizeKbSource:
    def test_maps_filename_to_title(self):
        result = normalize_kb_source({"filename": "guide.pdf"})
        assert result["title"] == "guide.pdf"

    def test_maps_topic_to_title(self):
        result = normalize_kb_source({"topic": "Visa Requirements"})
        assert result["title"] == "Visa Requirements"

    def test_preserves_existing_title(self):
        result = normalize_kb_source({"title": "My Doc", "filename": "other.pdf"})
        assert result["title"] == "My Doc"

    def test_maps_score_to_relevance_score(self):
        result = normalize_kb_source({"score": 0.85})
        assert result["relevance_score"] == 0.85

    def test_preserves_existing_relevance_score(self):
        result = normalize_kb_source({"relevance_score": 0.9, "score": 0.5})
        assert result["relevance_score"] == 0.9

    def test_defaults_to_untitled(self):
        result = normalize_kb_source({})
        assert result["title"] == "Untitled"

    def test_does_not_mutate_input(self):
        original = {"filename": "test.pdf", "score": 0.7}
        original_copy = dict(original)
        normalize_kb_source(original)
        assert original == original_copy


class TestNormalizeEmailTimestamp:
    def test_remaps_sent_at(self):
        result = normalize_email_timestamp({"sent_at": "2025-01-01T00:00:00Z"})
        assert result["email_sent_at"] == "2025-01-01T00:00:00Z"
        assert "sent_at" not in result

    def test_preserves_existing_email_sent_at(self):
        result = normalize_email_timestamp({"email_sent_at": "2025-01-01T00:00:00Z"})
        assert result["email_sent_at"] == "2025-01-01T00:00:00Z"

    def test_does_not_overwrite_email_sent_at_with_sent_at(self):
        result = normalize_email_timestamp({
            "email_sent_at": "2025-01-01",
            "sent_at": "2025-02-01",
        })
        assert result["email_sent_at"] == "2025-01-01"

    def test_empty_dict(self):
        assert normalize_email_timestamp({}) == {}


class TestNormalizeInvoiceCreate:
    def test_converts_due_date_to_due_days(self):
        future = (date.today() + timedelta(days=15)).isoformat()
        result = normalize_invoice_create({"due_date": future})
        assert "due_days" in result
        assert result["due_days"] >= 14
        assert "due_date" not in result

    def test_preserves_existing_due_days(self):
        result = normalize_invoice_create({"due_days": 45})
        assert result["due_days"] == 45

    def test_defaults_to_30_on_invalid_date(self):
        result = normalize_invoice_create({"due_date": "not-a-date"})
        assert result["due_days"] == 30

    def test_minimum_one_day(self):
        past = (date.today() - timedelta(days=5)).isoformat()
        result = normalize_invoice_create({"due_date": past})
        assert result["due_days"] == 1

    def test_preserves_other_fields(self):
        result = normalize_invoice_create({"due_days": 7, "customer_name": "John"})
        assert result["customer_name"] == "John"
