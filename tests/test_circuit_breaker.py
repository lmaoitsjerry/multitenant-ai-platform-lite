"""
Tests for circuit breaker module.

Tests the CircuitBreaker class and its state transitions.
"""

import pytest
import time
from unittest.mock import patch


class TestCircuitBreakerInit:
    """Tests for CircuitBreaker initialization."""

    def test_default_values(self):
        """Should initialize with sensible defaults."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker()
        assert cb.name == "default"
        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 60
        assert cb.failures == 0
        assert cb.state == "closed"

    def test_custom_values(self):
        """Should accept custom configuration."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(
            name="custom",
            failure_threshold=3,
            recovery_timeout=30
        )
        assert cb.name == "custom"
        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 30


class TestCircuitBreakerStates:
    """Tests for circuit breaker state transitions."""

    def test_starts_closed(self):
        """Circuit breaker should start in closed state."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker()
        assert cb.state == "closed"
        assert cb.can_execute() is True

    def test_stays_closed_below_threshold(self):
        """Should stay closed when failures are below threshold."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=5)

        for _ in range(4):
            cb.record_failure()

        assert cb.state == "closed"
        assert cb.can_execute() is True

    def test_opens_at_threshold(self):
        """Should open when failures reach threshold."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3)

        for _ in range(3):
            cb.record_failure()

        assert cb.state == "open"
        assert cb.can_execute() is False

    def test_blocks_requests_when_open(self):
        """Should block requests when open."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        cb.record_failure()

        assert cb.state == "open"
        assert cb.can_execute() is False
        assert cb.can_execute() is False  # Multiple checks should return False

    def test_transitions_to_half_open(self):
        """Should transition to half-open after recovery timeout."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1)
        cb.record_failure()

        assert cb.state == "open"

        # Wait for recovery timeout
        time.sleep(1.1)

        # This call should transition to half-open
        assert cb.can_execute() is True
        assert cb.state == "half-open"

    def test_half_open_allows_requests(self):
        """Half-open state should allow test requests."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0)
        cb.record_failure()

        # Force half-open
        cb.state = "half-open"

        assert cb.can_execute() is True

    def test_closes_on_success_from_half_open(self):
        """Should close on success when in half-open state."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()
        cb.state = "half-open"

        cb.record_success()

        assert cb.state == "closed"
        assert cb.failures == 0

    def test_reopens_on_failure_from_half_open(self):
        """Should reopen on failure when in half-open state."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=1)
        cb.state = "half-open"

        cb.record_failure()

        assert cb.state == "open"

    def test_success_resets_failures(self):
        """Success should reset failure count."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=5)

        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.failures == 3

        cb.record_success()
        assert cb.failures == 0
        assert cb.state == "closed"


class TestCircuitBreakerGetStatus:
    """Tests for the get_status method."""

    def test_returns_status_dict(self):
        """Should return a status dictionary."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(name="test", failure_threshold=5)
        cb.record_failure()
        cb.record_failure()

        status = cb.get_status()

        assert status["name"] == "test"
        assert status["state"] == "closed"
        assert status["failures"] == 2
        assert status["threshold"] == 5

    def test_status_reflects_open_state(self):
        """Status should reflect open state."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()

        status = cb.get_status()
        assert status["state"] == "open"
        assert status["failures"] == 2


class TestSharedCircuitBreakers:
    """Tests for the shared circuit breaker instances."""

    def test_sendgrid_circuit_exists(self):
        """SendGrid circuit breaker should be configured."""
        from src.utils.circuit_breaker import sendgrid_circuit

        assert sendgrid_circuit.name == "sendgrid"
        assert sendgrid_circuit.failure_threshold == 3
        assert sendgrid_circuit.recovery_timeout == 60

    def test_supabase_circuit_exists(self):
        """Supabase circuit breaker should be configured."""
        from src.utils.circuit_breaker import supabase_circuit

        assert supabase_circuit.name == "supabase"
        assert supabase_circuit.failure_threshold == 5
        assert supabase_circuit.recovery_timeout == 30

    def test_rag_circuit_exists(self):
        """RAG circuit breaker should be configured."""
        from src.utils.circuit_breaker import rag_circuit

        assert rag_circuit.name == "travel_platform_rag"
        assert rag_circuit.failure_threshold == 5
        assert rag_circuit.recovery_timeout == 60

    def test_rates_circuit_exists(self):
        """Rates circuit breaker should be configured."""
        from src.utils.circuit_breaker import rates_circuit

        assert rates_circuit.name == "travel_platform_rates"
        assert rates_circuit.failure_threshold == 3
        assert rates_circuit.recovery_timeout == 120


class TestCircuitBreakerThreadSafety:
    """Tests for thread safety of circuit breakers."""

    def test_concurrent_failures(self):
        """Should handle concurrent failure recordings safely."""
        import threading
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=100)
        num_threads = 50

        def record():
            cb.record_failure()

        threads = [threading.Thread(target=record) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert cb.failures == num_threads

    def test_concurrent_state_checks(self):
        """Should handle concurrent state checks safely."""
        import threading
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=5)
        results = []

        def check():
            results.append(cb.can_execute())

        threads = [threading.Thread(target=check) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 50
        assert all(r is True for r in results)

    def test_concurrent_mixed_operations(self):
        """Should handle mixed concurrent operations safely."""
        import threading
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=10, recovery_timeout=0)

        def fail():
            cb.record_failure()

        def succeed():
            cb.record_success()

        def check():
            cb.can_execute()

        threads = []
        for _ in range(10):
            threads.append(threading.Thread(target=fail))
            threads.append(threading.Thread(target=succeed))
            threads.append(threading.Thread(target=check))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should complete without deadlock or error
        status = cb.get_status()
        assert "state" in status


class TestCircuitBreakerRecoveryTimeout:
    """Tests for recovery timeout behavior."""

    def test_stays_open_before_timeout(self):
        """Should stay open before recovery timeout expires."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        cb.record_failure()

        # Immediately check - should still be open
        assert cb.can_execute() is False
        assert cb.state == "open"

    def test_last_failure_time_updated(self):
        """Should update last_failure_time on each failure."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=5)

        time1 = time.time()
        cb.record_failure()
        time2 = cb.last_failure_time

        time.sleep(0.1)

        cb.record_failure()
        time3 = cb.last_failure_time

        assert time2 >= time1
        assert time3 > time2


# ==================== NEW TESTS: State Transitions, Failure Counting, Reset, Timeout ====================

class TestClosedToOpenTransition:
    """Detailed tests for closed -> open state transition."""

    def test_exact_threshold_opens(self):
        """Circuit should open at exactly the threshold count."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3)

        cb.record_failure()
        assert cb.state == "closed"
        cb.record_failure()
        assert cb.state == "closed"
        cb.record_failure()
        assert cb.state == "open"

    def test_failures_beyond_threshold_stay_open(self):
        """Failures beyond threshold should keep circuit open."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=2)
        for _ in range(10):
            cb.record_failure()

        assert cb.state == "open"
        assert cb.failures == 10

    def test_success_before_threshold_keeps_closed(self):
        """Success before reaching threshold keeps circuit closed."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()  # Reset before threshold

        assert cb.state == "closed"
        assert cb.failures == 0

    def test_interleaved_success_failure_prevents_opening(self):
        """Interleaved successes should prevent circuit from opening."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3)

        for _ in range(5):
            cb.record_failure()
            cb.record_failure()
            cb.record_success()  # Reset count each time

        assert cb.state == "closed"
        assert cb.failures == 0


class TestOpenToHalfOpenTransition:
    """Detailed tests for open -> half-open state transition."""

    def test_half_open_transition_with_zero_timeout(self):
        """Zero timeout should transition immediately to half-open."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0)
        cb.record_failure()

        assert cb.state == "open"
        # With 0 timeout, next check should transition
        result = cb.can_execute()
        assert result is True
        assert cb.state == "half-open"

    def test_half_open_transition_requires_timeout_elapse(self):
        """Should not transition to half-open before timeout."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=9999)
        cb.record_failure()

        assert cb.state == "open"
        assert cb.can_execute() is False
        assert cb.state == "open"  # Still open

    def test_half_open_with_mocked_time(self):
        """Should transition to half-open when time.time() exceeds threshold."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        cb.record_failure()

        # Mock time to be 61 seconds after failure
        with patch('src.utils.circuit_breaker.time') as mock_time:
            mock_time.time.return_value = cb.last_failure_time + 61
            assert cb.can_execute() is True
            assert cb.state == "half-open"


class TestHalfOpenBehavior:
    """Detailed tests for half-open state behavior."""

    def test_success_in_half_open_closes_circuit(self):
        """Success in half-open should close circuit and reset failures."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0)
        cb.record_failure()

        # Transition to half-open
        cb.can_execute()
        assert cb.state == "half-open"

        cb.record_success()
        assert cb.state == "closed"
        assert cb.failures == 0

    def test_failure_in_half_open_reopens_circuit(self):
        """Failure in half-open should reopen the circuit."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0)
        cb.record_failure()

        # Transition to half-open
        cb.can_execute()
        assert cb.state == "half-open"

        cb.record_failure()
        assert cb.state == "open"

    def test_multiple_can_execute_in_half_open(self):
        """Multiple can_execute in half-open should all return True."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=1)
        cb.state = "half-open"

        assert cb.can_execute() is True
        assert cb.can_execute() is True
        assert cb.can_execute() is True

    def test_full_cycle_closed_open_half_closed(self):
        """Full lifecycle: closed -> open -> half-open -> closed."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)

        # Start closed
        assert cb.state == "closed"
        assert cb.can_execute() is True

        # Trigger failures -> open
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"

        # Before timeout, should be blocked
        assert cb.can_execute() is False

        # Simulate timeout expiry via mocked time
        with patch('src.utils.circuit_breaker.time') as mock_time:
            mock_time.time.return_value = cb.last_failure_time + 61
            assert cb.can_execute() is True
            assert cb.state == "half-open"

        # Success -> closed
        cb.record_success()
        assert cb.state == "closed"
        assert cb.failures == 0
        assert cb.can_execute() is True


class TestFailureCounting:
    """Tests for failure counting precision."""

    def test_failure_count_increments_exactly(self):
        """Each record_failure should increment failures by exactly 1."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=100)

        for i in range(1, 50):
            cb.record_failure()
            assert cb.failures == i

    def test_success_resets_count_to_zero(self):
        """record_success should always reset failures to 0."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=100)

        for count in [1, 5, 10, 50]:
            for _ in range(count):
                cb.record_failure()
            cb.record_success()
            assert cb.failures == 0

    def test_failure_threshold_one(self):
        """Threshold of 1 should open on first failure."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()

        assert cb.state == "open"
        assert cb.failures == 1


class TestGetStatusComprehensive:
    """Comprehensive tests for get_status in various states."""

    def test_status_in_closed_state(self):
        """Status should correctly report closed state."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(name="test-status", failure_threshold=5)
        status = cb.get_status()

        assert status == {
            "name": "test-status",
            "state": "closed",
            "failures": 0,
            "threshold": 5,
        }

    def test_status_in_half_open_state(self):
        """Status should correctly report half-open state."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(name="half", failure_threshold=3)
        cb.state = "half-open"
        cb.failures = 3

        status = cb.get_status()
        assert status["state"] == "half-open"
        assert status["failures"] == 3

    def test_status_returns_new_dict_each_time(self):
        """get_status should return a new dict each call (not mutable)."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker()
        status1 = cb.get_status()
        status2 = cb.get_status()

        assert status1 is not status2
        assert status1 == status2


class TestHotbeldsCircuitBreaker:
    """Tests for the hotelbeds shared circuit breaker instance."""

    def test_hotelbeds_circuit_exists(self):
        """Hotelbeds circuit breaker should be configured."""
        from src.utils.circuit_breaker import hotelbeds_circuit

        assert hotelbeds_circuit.name == "hotelbeds"
        assert hotelbeds_circuit.failure_threshold == 3
        assert hotelbeds_circuit.recovery_timeout == 60

    def test_shared_circuits_are_independent(self):
        """Shared circuit breakers should not affect each other."""
        from src.utils.circuit_breaker import sendgrid_circuit, supabase_circuit

        # Reset states
        sendgrid_circuit.failures = 0
        sendgrid_circuit.state = "closed"
        supabase_circuit.failures = 0
        supabase_circuit.state = "closed"

        sendgrid_circuit.record_failure()
        sendgrid_circuit.record_failure()
        sendgrid_circuit.record_failure()

        assert sendgrid_circuit.state == "open"
        assert supabase_circuit.state == "closed"
        assert supabase_circuit.failures == 0

        # Cleanup
        sendgrid_circuit.record_success()


class TestRecoveryTimeoutEdgeCases:
    """Edge case tests for recovery_timeout boundaries."""

    def test_recovery_at_exact_boundary(self):
        """Should transition at exactly the recovery timeout boundary."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=5)
        cb.record_failure()

        # Mock time to be exactly at boundary
        with patch('src.utils.circuit_breaker.time') as mock_time:
            mock_time.time.return_value = cb.last_failure_time + 5
            assert cb.can_execute() is True
            assert cb.state == "half-open"

    def test_recovery_one_second_before_boundary(self):
        """Should stay open one second before recovery timeout."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=5)
        cb.record_failure()

        with patch('src.utils.circuit_breaker.time') as mock_time:
            mock_time.time.return_value = cb.last_failure_time + 4.999
            assert cb.can_execute() is False
            assert cb.state == "open"

    def test_large_recovery_timeout(self):
        """Should handle large recovery timeout values."""
        from src.utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=86400)  # 24 hours
        cb.record_failure()

        assert cb.can_execute() is False
        assert cb.state == "open"
