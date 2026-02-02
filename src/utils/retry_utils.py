"""
Reusable retry decorators for external service calls.

Uses tenacity for exponential backoff with configurable retry conditions.
Pair with circuit breakers from src.utils.circuit_breaker for full resilience.
"""

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging
import requests
import httpx

logger = logging.getLogger(__name__)


def retry_on_network_error(max_attempts: int = 3, min_wait: int = 2, max_wait: int = 10):
    """Retry decorator for sync HTTP calls (requests library).

    Retries on ConnectionError and Timeout only. Never retries 4xx responses.
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type((
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


def retry_on_async_network_error(max_attempts: int = 3, min_wait: int = 2, max_wait: int = 10):
    """Retry decorator for async HTTP calls (httpx library).

    Retries on ConnectError and TimeoutException only. Never retries 4xx responses.
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type((
            httpx.ConnectError,
            httpx.TimeoutException,
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
