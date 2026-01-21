"""
Request ID Middleware for distributed tracing.

This middleware:
1. Generates a unique request ID (UUID4) for each request
2. Respects incoming X-Request-ID header for distributed tracing
3. Sets the request_id in contextvars for logging
4. Adds X-Request-ID to response headers
5. Logs request start and completion with timing

Usage in main.py:
    from src.middleware.request_id_middleware import RequestIdMiddleware
    app.add_middleware(RequestIdMiddleware)  # Add LAST so it runs FIRST
"""

import uuid
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from src.utils.structured_logger import set_request_id, clear_request_id, get_logger

logger = get_logger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware to generate and propagate request IDs for distributed tracing.

    This middleware ensures every request has a unique identifier that:
    - Is included in all log entries for the request
    - Is returned in the X-Request-ID response header
    - Can be passed between services for distributed tracing

    The middleware should be added LAST in the middleware chain so it runs
    FIRST (FastAPI processes middleware in reverse order).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with request ID tracking.

        Args:
            request: The incoming request
            call_next: The next handler in the chain

        Returns:
            Response with X-Request-ID header
        """
        # Get existing request ID from header or generate new one
        # This allows distributed tracing across services
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Set in contextvars for logging (all subsequent logs include this ID)
        set_request_id(request_id)

        # Store in request state for access in route handlers
        request.state.request_id = request_id

        # Record start time for duration logging
        start_time = time.perf_counter()

        # Log request start with key metadata
        logger.info(
            "Request started",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params) if request.query_params else None,
                "client_ip": self._get_client_ip(request),
                "user_agent": request.headers.get("User-Agent", "")[:100],  # Truncate long UAs
            }
        )

        try:
            # Process request through the rest of the middleware chain
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Add request ID to response headers for client-side tracing
            response.headers["X-Request-ID"] = request_id

            # Log request completion
            logger.info(
                "Request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                }
            )

            return response

        except Exception as e:
            # Calculate duration even for errors
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log the error (exception will be re-raised)
            logger.error(
                "Request failed with exception",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "error_type": type(e).__name__,
                    "error_message": str(e)[:500],  # Truncate long messages
                },
                exc_info=True
            )

            # Re-raise to let FastAPI's exception handlers deal with it
            raise

        finally:
            # Clear request ID to prevent leakage to other contexts
            clear_request_id()

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, handling proxies.

        Args:
            request: The incoming request

        Returns:
            Client IP address
        """
        # Check for forwarded headers (when behind proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain (original client)
            return forwarded_for.split(",")[0].strip()

        # Check for real IP header (some proxies use this)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct connection IP
        if request.client:
            return request.client.host

        return "unknown"
