"""Test 9: Quote Status Constraint"""


def test_quoted_status_is_valid():
    """The 'quoted' status should be in the valid statuses."""
    valid_statuses = [
        'queued', 'processing', 'parsed', 'validation_failed', 'generated',
        'draft', 'sent', 'pending', 'accepted', 'rejected', 'expired',
        'failed', 'booked', 'quoted', 'viewed', 'converted', 'cancelled',
        'no_availability'
    ]

    assert 'quoted' in valid_statuses
    assert 'viewed' in valid_statuses
    assert 'no_availability' in valid_statuses

    for status in valid_statuses:
        assert status == status.lower(), f"Status '{status}' should be lowercase"


def test_normalize_quote_status():
    """normalizeQuoteStatus should handle various status inputs."""
    from src.utils.field_normalizers import normalize_quote_status

    assert normalize_quote_status('draft') == 'draft'
    assert normalize_quote_status('DRAFT') == 'draft'
    assert normalize_quote_status('quoted') == 'quoted'
    assert normalize_quote_status('Generated') == 'generated'
    assert normalize_quote_status(None) == 'draft'
    assert normalize_quote_status('') == 'draft'
