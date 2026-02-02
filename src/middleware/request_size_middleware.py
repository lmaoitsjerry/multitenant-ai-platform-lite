"""
Request Size Middleware

Enforces maximum request body size to prevent denial-of-service via oversized payloads.
Checks Content-Length header before the body is read.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
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


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Content-Length exceeds the allowed maximum."""

    async def dispatch(self, request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                length = int(content_length)
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid Content-Length header"},
                )

            max_size = DEFAULT_MAX_SIZE
            if any(request.url.path.startswith(p) for p in UPLOAD_PREFIXES):
                max_size = UPLOAD_MAX_SIZE

            if length > max_size:
                logger.warning(
                    f"Request too large: {length} bytes on {request.url.path} "
                    f"(limit {max_size})"
                )
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": f"Request body too large. Maximum size: {max_size // (1024 * 1024)} MB"
                    },
                )

        return await call_next(request)
