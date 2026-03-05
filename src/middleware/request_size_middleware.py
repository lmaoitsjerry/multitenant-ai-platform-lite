"""
Request Size Middleware (Pure ASGI)

Enforces maximum request body size to prevent denial-of-service via oversized payloads.
Checks Content-Length header before the body is read.
"""

import json
from src.utils.structured_logger import get_logger

logger = get_logger(__name__)

# 10 MB general limit
DEFAULT_MAX_SIZE = 10 * 1024 * 1024
# 50 MB for file upload paths
UPLOAD_MAX_SIZE = 50 * 1024 * 1024

UPLOAD_PREFIXES = (
    "/api/v1/knowledge/upload",
    "/api/v1/knowledge/documents",
)


class RequestSizeMiddleware:
    """Pure ASGI middleware that rejects requests whose Content-Length exceeds the allowed maximum."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Check Content-Length header
        content_length = None
        for key, value in scope.get("headers", []):
            if key == b"content-length":
                try:
                    content_length = int(value)
                except ValueError:
                    # Invalid Content-Length
                    body = json.dumps({"detail": "Invalid Content-Length header"}).encode()
                    await send({
                        "type": "http.response.start",
                        "status": 400,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"content-length", str(len(body)).encode()),
                        ],
                    })
                    await send({"type": "http.response.body", "body": body})
                    return
                break

        if content_length is not None:
            path = scope.get("path", "")
            max_size = DEFAULT_MAX_SIZE
            if any(path.startswith(p) for p in UPLOAD_PREFIXES):
                max_size = UPLOAD_MAX_SIZE

            if content_length > max_size:
                logger.warning(
                    f"Request too large: {content_length} bytes on {path} "
                    f"(limit {max_size})"
                )
                body = json.dumps({
                    "detail": f"Request body too large. Maximum size: {max_size // (1024 * 1024)} MB"
                }).encode()
                await send({
                    "type": "http.response.start",
                    "status": 413,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode()),
                    ],
                })
                await send({"type": "http.response.body", "body": body})
                return

        await self.app(scope, receive, send)
