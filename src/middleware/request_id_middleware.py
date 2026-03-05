"""
Request ID Middleware for distributed tracing (Pure ASGI).

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
from src.utils.structured_logger import set_request_id, clear_request_id, clear_tenant_id, get_logger

logger = get_logger(__name__)


class RequestIdMiddleware:
    """Pure ASGI middleware for request ID tracking and distributed tracing.

    This middleware ensures every request has a unique identifier that:
    - Is included in all log entries for the request
    - Is returned in the X-Request-ID response header
    - Can be passed between services for distributed tracing

    The middleware should be added LAST in the middleware chain so it runs
    FIRST (FastAPI processes middleware in reverse order).
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Get existing request ID from header or generate new one
        request_id = None
        headers = dict(scope.get("headers", []))
        for key, value in scope.get("headers", []):
            if key == b"x-request-id":
                request_id = value.decode("utf-8", errors="replace")
                break
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store request_id in scope state for route handler access via request.state
        scope.setdefault("state", {})["request_id"] = request_id

        # Set in contextvars for logging
        set_request_id(request_id)

        # Extract request metadata for logging
        method = scope.get("method", "")
        path = scope.get("path", "")
        query_string = scope.get("query_string", b"").decode("utf-8", errors="replace")
        client = scope.get("client")
        client_ip = self._get_client_ip(scope)
        user_agent = ""
        for key, value in scope.get("headers", []):
            if key == b"user-agent":
                user_agent = value.decode("utf-8", errors="replace")[:100]
                break

        start_time = time.perf_counter()

        logger.info(
            "Request started",
            extra={
                "method": method,
                "path": path,
                "query": query_string if query_string else None,
                "client_ip": client_ip,
                "user_agent": user_agent,
            }
        )

        status_code = 0

        async def send_with_request_id(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
                extra_headers = [
                    (b"x-request-id", request_id.encode()),
                ]
                message = {
                    **message,
                    "headers": list(message.get("headers", [])) + extra_headers,
                }
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)

            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "Request completed",
                extra={
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 2),
                }
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "Request failed with exception",
                extra={
                    "method": method,
                    "path": path,
                    "duration_ms": round(duration_ms, 2),
                    "error_type": type(e).__name__,
                    "error_message": str(e)[:500],
                },
                exc_info=True
            )
            raise
        finally:
            clear_request_id()
            clear_tenant_id()

    def _get_client_ip(self, scope) -> str:
        """Extract client IP, handling proxies."""
        for key, value in scope.get("headers", []):
            if key == b"x-forwarded-for":
                return value.decode("utf-8", errors="replace").split(",")[0].strip()
            if key == b"x-real-ip":
                return value.decode("utf-8", errors="replace")

        client = scope.get("client")
        if client:
            return client[0]

        return "unknown"
