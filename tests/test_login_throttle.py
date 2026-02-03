"""
Tests for login throttle module.

Tests the per-account login throttle that prevents brute-force attacks.
"""

import pytest
import time
from unittest.mock import patch


class TestCheckLoginAllowed:
    """Tests for the check_login_allowed function."""

    def setup_method(self):
        """Clear the accounts dict before each test."""
        from src.services import login_throttle
        with login_throttle._lock:
            login_throttle._accounts.clear()

    def test_first_login_always_allowed(self):
        """First login attempt for any email should be allowed."""
        from src.services.login_throttle import check_login_allowed

        allowed, remaining = check_login_allowed("newuser@example.com")
        assert allowed is True
        assert remaining == 0

    def test_email_case_insensitive(self):
        """Email lookups should be case-insensitive."""
        from src.services.login_throttle import check_login_allowed, record_failure

        # Record failure for lowercase
        record_failure("User@Example.com")

        # Check with different case should still find the record
        from src.services import login_throttle
        with login_throttle._lock:
            assert "user@example.com" in login_throttle._accounts

    def test_allowed_after_some_failures(self):
        """Should still allow login after a few failures (below threshold)."""
        from src.services.login_throttle import check_login_allowed, record_failure

        email = "test@example.com"

        # Record 5 failures (below threshold of 10)
        for _ in range(5):
            record_failure(email)

        allowed, remaining = check_login_allowed(email)
        assert allowed is True
        assert remaining == 0

    def test_locked_after_max_failures(self):
        """Should lock account after MAX_FAILURES consecutive failures."""
        from src.services.login_throttle import check_login_allowed, record_failure, MAX_FAILURES

        email = "attacker@example.com"

        # Record MAX_FAILURES failures
        for _ in range(MAX_FAILURES):
            record_failure(email)

        allowed, remaining = check_login_allowed(email)
        assert allowed is False
        assert remaining > 0
        assert remaining <= 15 * 60  # Should be at most LOCKOUT_SECONDS

    def test_locked_returns_remaining_seconds(self):
        """When locked, should return accurate remaining seconds."""
        from src.services.login_throttle import check_login_allowed, record_failure, MAX_FAILURES, LOCKOUT_SECONDS

        email = "locked@example.com"

        # Lock the account
        for _ in range(MAX_FAILURES):
            record_failure(email)

        allowed, remaining = check_login_allowed(email)
        assert allowed is False
        # Remaining should be close to LOCKOUT_SECONDS (within a second or two)
        assert LOCKOUT_SECONDS - 2 <= remaining <= LOCKOUT_SECONDS

    def test_lock_expires_after_timeout(self):
        """Account should be unlocked after LOCKOUT_SECONDS."""
        from src.services.login_throttle import check_login_allowed, record_failure, MAX_FAILURES
        from src.services import login_throttle

        email = "expired@example.com"

        # Lock the account
        for _ in range(MAX_FAILURES):
            record_failure(email)

        # Manually expire the lock
        with login_throttle._lock:
            state = login_throttle._accounts[email.lower()]
            state.locked_until = time.time() - 1  # Set to past

        allowed, remaining = check_login_allowed(email)
        assert allowed is True
        assert remaining == 0

    def test_lock_expiry_resets_failure_count(self):
        """When lock expires, failure count should be reset."""
        from src.services.login_throttle import check_login_allowed, record_failure, MAX_FAILURES
        from src.services import login_throttle

        email = "reset@example.com"

        # Lock the account
        for _ in range(MAX_FAILURES):
            record_failure(email)

        # Expire the lock
        with login_throttle._lock:
            state = login_throttle._accounts[email.lower()]
            state.locked_until = time.time() - 1

        # This should reset the state
        check_login_allowed(email)

        # Verify failures were reset
        with login_throttle._lock:
            state = login_throttle._accounts.get(email.lower())
            if state:
                assert state.failures == 0
                assert state.locked_until == 0.0


class TestRecordFailure:
    """Tests for the record_failure function."""

    def setup_method(self):
        """Clear the accounts dict before each test."""
        from src.services import login_throttle
        with login_throttle._lock:
            login_throttle._accounts.clear()

    def test_creates_state_on_first_failure(self):
        """Should create account state on first failure."""
        from src.services.login_throttle import record_failure
        from src.services import login_throttle

        email = "new@example.com"
        record_failure(email)

        with login_throttle._lock:
            assert email.lower() in login_throttle._accounts
            state = login_throttle._accounts[email.lower()]
            assert state.failures == 1
            assert state.locked_until == 0.0

    def test_increments_failure_count(self):
        """Should increment failure count on each failure."""
        from src.services.login_throttle import record_failure
        from src.services import login_throttle

        email = "counter@example.com"

        for expected_count in range(1, 6):
            record_failure(email)
            with login_throttle._lock:
                state = login_throttle._accounts[email.lower()]
                assert state.failures == expected_count

    def test_sets_lockout_at_threshold(self):
        """Should set locked_until when failure count reaches threshold."""
        from src.services.login_throttle import record_failure, MAX_FAILURES, LOCKOUT_SECONDS
        from src.services import login_throttle

        email = "threshold@example.com"

        # Record failures up to but not including threshold
        for _ in range(MAX_FAILURES - 1):
            record_failure(email)

        with login_throttle._lock:
            state = login_throttle._accounts[email.lower()]
            assert state.locked_until == 0.0  # Not locked yet

        # This should trigger the lockout
        record_failure(email)

        with login_throttle._lock:
            state = login_throttle._accounts[email.lower()]
            assert state.locked_until > time.time()
            assert state.locked_until <= time.time() + LOCKOUT_SECONDS + 1


class TestRecordSuccess:
    """Tests for the record_success function."""

    def setup_method(self):
        """Clear the accounts dict before each test."""
        from src.services import login_throttle
        with login_throttle._lock:
            login_throttle._accounts.clear()

    def test_clears_existing_state(self):
        """Should remove account state on successful login."""
        from src.services.login_throttle import record_failure, record_success
        from src.services import login_throttle

        email = "success@example.com"

        # Create some state
        record_failure(email)
        record_failure(email)

        # Success should clear it
        record_success(email)

        with login_throttle._lock:
            assert email.lower() not in login_throttle._accounts

    def test_noop_for_unknown_email(self):
        """Should do nothing for an email with no recorded failures."""
        from src.services.login_throttle import record_success
        from src.services import login_throttle

        email = "unknown@example.com"

        # Should not raise
        record_success(email)

        with login_throttle._lock:
            assert email.lower() not in login_throttle._accounts

    def test_clears_locked_state(self):
        """Should clear state even if account was locked."""
        from src.services.login_throttle import record_failure, record_success, MAX_FAILURES
        from src.services import login_throttle

        email = "waslocked@example.com"

        # Lock the account
        for _ in range(MAX_FAILURES):
            record_failure(email)

        # Success should clear it
        record_success(email)

        with login_throttle._lock:
            assert email.lower() not in login_throttle._accounts


class TestThreadSafety:
    """Tests for thread safety of the login throttle."""

    def setup_method(self):
        """Clear the accounts dict before each test."""
        from src.services import login_throttle
        with login_throttle._lock:
            login_throttle._accounts.clear()

    def test_concurrent_failures(self):
        """Should handle concurrent failure recordings safely."""
        import threading
        from src.services.login_throttle import record_failure
        from src.services import login_throttle

        email = "concurrent@example.com"
        num_threads = 20

        def record():
            record_failure(email)

        threads = [threading.Thread(target=record) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        with login_throttle._lock:
            state = login_throttle._accounts[email.lower()]
            assert state.failures == num_threads

    def test_concurrent_check_and_failure(self):
        """Should handle concurrent checks and failures safely."""
        import threading
        from src.services.login_throttle import check_login_allowed, record_failure
        from src.services import login_throttle

        email = "mixed@example.com"
        results = []

        def check():
            result = check_login_allowed(email)
            results.append(result)

        def fail():
            record_failure(email)

        threads = []
        for _ in range(10):
            threads.append(threading.Thread(target=check))
            threads.append(threading.Thread(target=fail))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All operations should complete without error
        assert len(results) == 10
        for allowed, remaining in results:
            assert isinstance(allowed, bool)
            assert isinstance(remaining, int)
