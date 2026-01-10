"""
Performance Timing Middleware

Logs request duration for all API endpoints to identify slow operations.
Format: [PERF] METHOD /path took XXXms (status: YYY)
"""

import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("performance")

# Set up a dedicated performance logger
perf_handler = logging.StreamHandler()
perf_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
logger.addHandler(perf_handler)
logger.setLevel(logging.INFO)

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
        if path in ["/", "/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        start_time = time.perf_counter()

        # Process the request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Determine log level based on duration
        method = request.method
        status = response.status_code

        # Format the log message
        if duration_ms >= CRITICAL_THRESHOLD_MS:
            log_prefix = "[PERF CRITICAL]"
            log_func = logger.warning
        elif duration_ms >= SLOW_THRESHOLD_MS:
            log_prefix = "[PERF SLOW]"
            log_func = logger.warning
        else:
            log_prefix = "[PERF]"
            log_func = logger.info

        # Log the timing
        log_func(f"{log_prefix} {method} {path} took {duration_ms:.0f}ms (status: {status})")

        # Add timing header to response for frontend debugging
        response.headers["X-Response-Time"] = f"{duration_ms:.0f}ms"

        return response
