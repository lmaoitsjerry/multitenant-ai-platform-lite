"""
Performance Timing Middleware (Pure ASGI)

Logs request duration for all API endpoints to identify slow operations.
Uses structured logger for consistent JSON output.
"""

import time
from src.utils.structured_logger import get_logger

logger = get_logger("performance")

# Import Prometheus metrics lazily to avoid blocking startup
PROMETHEUS_AVAILABLE = False
REQUEST_COUNT = None
REQUEST_DURATION = None
ERROR_COUNT = None
normalize_path = None
_prometheus_init_attempted = False


def _lazy_init_prometheus():
    """Lazily initialize Prometheus metrics on first use."""
    global PROMETHEUS_AVAILABLE, REQUEST_COUNT, REQUEST_DURATION, ERROR_COUNT, normalize_path, _prometheus_init_attempted

    if _prometheus_init_attempted:
        return PROMETHEUS_AVAILABLE

    _prometheus_init_attempted = True

    try:
        from src.api.metrics_routes import (
            REQUEST_COUNT as _RC, REQUEST_DURATION as _RD, ERROR_COUNT as _EC,
            normalize_path as _np, PROMETHEUS_AVAILABLE as _PA,
        )
        REQUEST_COUNT = _RC
        REQUEST_DURATION = _RD
        ERROR_COUNT = _EC
        normalize_path = _np
        PROMETHEUS_AVAILABLE = _PA
    except (ImportError, Exception) as e:
        logger.debug(f"Prometheus metrics not available: {e}")
        PROMETHEUS_AVAILABLE = False

    return PROMETHEUS_AVAILABLE

# Thresholds for highlighting slow requests
SLOW_THRESHOLD_MS = 500  # Warn if request takes > 500ms
CRITICAL_THRESHOLD_MS = 2000  # Critical if request takes > 2s


class TimingMiddleware:
    """
    Pure ASGI middleware that logs the duration of every HTTP request.
    Helps identify slow endpoints for optimization.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Skip timing for health checks
        if path in ["/", "/health", "/health/live"]:
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()
        status_code = 0

        async def send_with_timing(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
                # Add timing header
                duration_ms = (time.perf_counter() - start_time) * 1000
                extra_headers = [
                    (b"x-response-time", f"{duration_ms:.0f}ms".encode()),
                ]
                message = {
                    **message,
                    "headers": list(message.get("headers", [])) + extra_headers,
                }
            await send(message)

        try:
            await self.app(scope, receive, send_with_timing)
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000
            method = scope.get("method", "")

            extra = {
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2),
            }

            if duration_ms >= CRITICAL_THRESHOLD_MS:
                logger.warning("Request critically slow", extra=extra)
            elif duration_ms >= SLOW_THRESHOLD_MS:
                logger.warning("Request slow", extra=extra)
            else:
                logger.info("Request completed", extra=extra)

            # Record Prometheus metrics (lazy init to avoid blocking startup)
            if _lazy_init_prometheus() and REQUEST_COUNT is not None and normalize_path is not None:
                norm = normalize_path(path)
                duration_s = duration_ms / 1000.0
                REQUEST_COUNT.labels(method=method, path=norm, status=str(status_code)).inc()
                REQUEST_DURATION.labels(method=method, path=norm).observe(duration_s)
                if status_code >= 400:
                    ERROR_COUNT.labels(method=method, path=norm, status=str(status_code)).inc()
