"""Test 7: Double Notifications Removed"""
import re


def test_only_one_notify_email_received_call():
    """email_webhook.py should only call notify_email_received once (in background task)."""
    with open("src/webhooks/email_webhook.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Count actual function calls (with parenthesis)
    calls = re.findall(r'notify_email_received\s*\(', content)

    assert len(calls) == 1, \
        f"Expected exactly 1 notify_email_received() call, found {len(calls)}"


def test_notification_in_background_task_only():
    """The remaining notification call should be in the background processing section."""
    with open("src/webhooks/email_webhook.py", "r", encoding="utf-8") as f:
        lines = f.readlines()

    call_lines = []
    for i, line in enumerate(lines, 1):
        if 'notify_email_received(' in line:
            call_lines.append(i)

    assert len(call_lines) == 1, \
        f"Expected 1 notify_email_received call, found at lines: {call_lines}"

    # The single call should be past line 600 (in the background task section)
    assert call_lines[0] > 600, \
        f"notify_email_received should be in background task (line >600), found at line {call_lines[0]}"
