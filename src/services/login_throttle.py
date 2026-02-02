"""
Per-account login throttle to prevent brute-force attacks.

In-memory rate limiter keyed by email address.
Locks an account for LOCKOUT_SECONDS after MAX_FAILURES consecutive failures.
Clears on successful login.

Thread-safe via threading.Lock.
"""

import threading
import time
from typing import Tuple

MAX_FAILURES = 10
LOCKOUT_SECONDS = 15 * 60  # 15 minutes


class _AccountState:
    __slots__ = ("failures", "locked_until")

    def __init__(self):
        self.failures = 0
        self.locked_until = 0.0


_lock = threading.Lock()
_accounts: dict[str, _AccountState] = {}


def check_login_allowed(email: str) -> Tuple[bool, int]:
    """Check if login is allowed for this email.

    Returns:
        (allowed, remaining_seconds)
        allowed=True means the caller should proceed with authentication.
        If allowed=False, remaining_seconds indicates how long the lockout lasts.
    """
    key = email.lower()
    now = time.time()

    with _lock:
        state = _accounts.get(key)
        if state is None:
            return True, 0

        if state.locked_until > now:
            remaining = int(state.locked_until - now)
            return False, remaining

        # Lock has expired — reset
        if state.locked_until > 0:
            state.failures = 0
            state.locked_until = 0.0

        return True, 0


def record_failure(email: str) -> None:
    """Record a failed login attempt. May trigger a lockout."""
    key = email.lower()

    with _lock:
        state = _accounts.get(key)
        if state is None:
            state = _AccountState()
            _accounts[key] = state

        state.failures += 1
        if state.failures >= MAX_FAILURES:
            state.locked_until = time.time() + LOCKOUT_SECONDS


def record_success(email: str) -> None:
    """Clear failure count on successful login."""
    key = email.lower()

    with _lock:
        if key in _accounts:
            del _accounts[key]
