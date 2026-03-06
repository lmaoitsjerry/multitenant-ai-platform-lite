"""Test 4: Auto-Send on Accept"""
import os


def test_send_email_flag_is_true():
    """Verify the frontend sends send_email: true, save_as_draft: false."""
    filepath = os.path.join("frontend", "tenant-dashboard", "src", "pages", "EnquiryTriage.jsx")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    assert "send_email: true" in content, \
        "handleAccept should have send_email: true"

    assert "save_as_draft: false" in content, \
        "handleAccept should have save_as_draft: false"


def test_notification_text_updated():
    """Verify notification says 'sent to client', not 'draft'."""
    filepath = os.path.join("frontend", "tenant-dashboard", "src", "pages", "EnquiryTriage.jsx")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Quote created and sent to client" in content, \
        "Success notification should say 'Quote created and sent to client'"
    assert "Draft quote created" not in content, \
        "Old draft notification text should be removed"
