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
