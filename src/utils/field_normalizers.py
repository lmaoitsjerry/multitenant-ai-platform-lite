"""
field_normalizers.py
Central field name mapping for the backend.
All provider responses pass through normalizers here.
All database queries use canonical names.
"""

from typing import Optional


# --- Quote Status ---

QUOTE_STATUS_CANONICAL = {
    "Draft": "draft",
    "DRAFT": "draft",
    "generated": "quoted",
    "Quoted": "quoted",
    "Accepted": "accepted",
    "Declined": "declined",
    "rejected": "declined",
    "Expired": "expired",
    "Converted": "converted",
}


def normalize_quote_status(status: Optional[str]) -> str:
    """Normalize any quote status variant to canonical lowercase value."""
    if not status:
        return "draft"
    return QUOTE_STATUS_CANONICAL.get(status, status.lower())


# --- Date Fields ---

def normalize_quote_dates(data: dict) -> dict:
    """Ensure check_in/check_out are the canonical field names. (fixes C4)"""
    normalized = dict(data)
    if "check_in_date" in normalized and "check_in" not in normalized:
        normalized["check_in"] = normalized.pop("check_in_date")
    if "check_out_date" in normalized and "check_out" not in normalized:
        normalized["check_out"] = normalized.pop("check_out_date")
    return normalized


# --- Hotel Pricing ---

def normalize_hotel_price(hotel: dict, nights: int = 1) -> float:
    """Extract canonical rate_per_night from any provider format. (fixes M9)"""
    for field in ("rate_per_night", "price_per_night", "nightly_rate"):
        if field in hotel and hotel[field] is not None:
            try:
                return float(hotel[field])
            except (ValueError, TypeError):
                continue

    if "total_price" in hotel and hotel["total_price"] and nights > 0:
        try:
            return float(hotel["total_price"]) / nights
        except (ValueError, TypeError):
            pass

    if "net_price" in hotel and hotel["net_price"]:
        try:
            return float(hotel["net_price"])
        except (ValueError, TypeError):
            pass

    return 0.0


# --- Activity Pricing ---

def normalize_activity_price(activity: dict) -> float:
    """Extract canonical price_per_person. (fixes M7)"""
    for field in ("price_per_person", "price_adult", "price"):
        if field in activity and activity[field] is not None:
            try:
                return float(activity[field])
            except (ValueError, TypeError):
                continue
    return 0.0


# --- Transfer Pricing ---

def normalize_transfer_price(transfer: dict) -> dict:
    """Extract canonical price and pricing_model. (fixes M8)"""
    price = 0.0
    for field in ("price", "price_per_transfer"):
        if field in transfer and transfer[field] is not None:
            try:
                price = float(transfer[field])
                break
            except (ValueError, TypeError):
                continue

    pricing_model = transfer.get("pricing_model")
    if not pricing_model:
        pricing_model = "per_person" if "price_per_person" in transfer else "per_transfer"

    return {"price": price, "pricing_model": pricing_model}


# --- KB Source Fields ---

def normalize_kb_source(source: dict) -> dict:
    """Normalize KB document source fields. (fixes C6, M20)"""
    normalized = dict(source)
    if "title" not in normalized:
        normalized["title"] = (
            normalized.get("filename")
            or normalized.get("topic")
            or "Untitled"
        )
    if "relevance_score" not in normalized and "score" in normalized:
        normalized["relevance_score"] = normalized["score"]
    return normalized


# --- Email Timestamp ---

def normalize_email_timestamp(data: dict) -> dict:
    """Ensure email_sent_at is the canonical field. (fixes M45)"""
    normalized = dict(data)
    if "sent_at" in normalized and "email_sent_at" not in normalized:
        normalized["email_sent_at"] = normalized.pop("sent_at")
    return normalized


# --- Invoice Fields ---

def normalize_invoice_create(data: dict) -> dict:
    """Normalize invoice creation payload. (fixes M43, M44)"""
    normalized = dict(data)

    # Convert due_date string to due_days integer
    if "due_date" in normalized and "due_days" not in normalized:
        from datetime import datetime, date
        try:
            due_date = datetime.fromisoformat(normalized["due_date"]).date()
            delta = (due_date - date.today()).days
            normalized["due_days"] = max(delta, 1)
        except (ValueError, TypeError):
            normalized["due_days"] = 30
        del normalized["due_date"]

    return normalized
