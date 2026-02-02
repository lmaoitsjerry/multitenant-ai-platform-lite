"""
Reusable circuit breaker for external service calls.

Prevents cascade failures by temporarily stopping requests to unhealthy services.
States: closed (normal) -> open (blocking) -> half-open (testing recovery).
"""
import threading
import time
from src.utils.structured_logger import get_logger

logger = get_logger(__name__)


class CircuitBreaker:
    """Thread-safe circuit breaker for external service calls."""

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout: int = 60
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "closed"
        self._lock = threading.Lock()

    def record_success(self):
        with self._lock:
            self.failures = 0
            self.state = "closed"

    def record_failure(self):
        with self._lock:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.failure_threshold:
                self.state = "open"
                logger.warning(
                    f"Circuit breaker [{self.name}] OPEN after {self.failures} failures"
                )

    def can_execute(self) -> bool:
        with self._lock:
            if self.state == "closed":
                return True
            if self.state == "open":
                if time.time() - self.last_failure_time >= self.recovery_timeout:
                    self.state = "half-open"
                    logger.info(
                        f"Circuit breaker [{self.name}] HALF-OPEN, allowing test request"
                    )
                    return True
                return False
            return True  # half-open allows requests

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state,
            "failures": self.failures,
            "threshold": self.failure_threshold,
        }


# Shared circuit breakers for external services
sendgrid_circuit = CircuitBreaker(name="sendgrid", failure_threshold=3, recovery_timeout=60)
supabase_circuit = CircuitBreaker(name="supabase", failure_threshold=5, recovery_timeout=30)
rag_circuit = CircuitBreaker(name="travel_platform_rag", failure_threshold=5, recovery_timeout=60)
rates_circuit = CircuitBreaker(name="travel_platform_rates", failure_threshold=3, recovery_timeout=120)
