"""
Performance Timing Middleware

Logs request duration for all API endpoints to identify slow operations.
Uses structured logger for consistent JSON output.
"""

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from src.utils.structured_logger import get_logger

logger = get_logger("performance")

# Thresholds for highlighting slow requests
SLOW_THRESHOLD_MS = 500  # Warn if request takes > 500ms
CRITICAL_THRESHOLD_MS = 2000  # Critical if request takes > 2s


class TimingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs the duration of every HTTP request.
    Helps identify slow endpoints for optimization.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip timing for health checks and static files
        path = request.url.path
        if path in ["/", "/health", "/health/live"]:
            return await call_next(request)

        start_time = time.perf_counter()

        # Process the request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Determine log level based on duration
        method = request.method
        status = response.status_code

        extra = {
            "method": method,
            "path": path,
            "status_code": status,
            "duration_ms": round(duration_ms, 2),
        }

        if duration_ms >= CRITICAL_THRESHOLD_MS:
            logger.warning("Request critically slow", extra=extra)
        elif duration_ms >= SLOW_THRESHOLD_MS:
            logger.warning("Request slow", extra=extra)
        else:
            logger.info("Request completed", extra=extra)

        # Add timing header to response for frontend debugging
        response.headers["X-Response-Time"] = f"{duration_ms:.0f}ms"

        return response
