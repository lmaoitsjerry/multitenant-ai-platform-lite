"""
Website Builder Proxy Routes

Proxies API requests from the frontend to the Website Builder service,
avoiding CORS issues in production where frontend and website builder
are on different origins.

In development, Vite's dev proxy handles this at /wb.
In production, this FastAPI proxy handles it at /api/v1/wb.
"""

import os
import logging
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
import httpx

logger = logging.getLogger(__name__)

website_proxy_router = APIRouter(prefix="/api/v1/wb", tags=["Website Builder Proxy"])

# Target URL for the website builder service
WEBSITE_BUILDER_TARGET = os.getenv("WEBSITE_BUILDER_URL", "http://localhost:3000")

# Shared async client (reused across requests for connection pooling)
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    """Lazy-init a shared async HTTP client."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=WEBSITE_BUILDER_TARGET,
            timeout=30.0,
            follow_redirects=True,
        )
    return _client


# Headers to strip when forwarding (hop-by-hop or security-sensitive)
_STRIP_REQUEST_HEADERS = {"host", "content-length", "transfer-encoding"}
_STRIP_RESPONSE_HEADERS = {"transfer-encoding", "content-encoding", "content-length"}


@website_proxy_router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_to_website_builder(path: str, request: Request):
    """
    Forward any request to the Website Builder service.

    /api/v1/wb/api/analytics/summary → WEBSITE_BUILDER_URL/api/analytics/summary
    """
    client = _get_client()

    # Build target URL
    target_url = f"/{path}"
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    # Forward headers (strip hop-by-hop)
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in _STRIP_REQUEST_HEADERS
    }

    try:
        body = await request.body()
        resp = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body if body else None,
        )

        # Build response headers (strip hop-by-hop and upstream CORS headers
        # to avoid duplicates — CORSMiddleware handles CORS for all responses)
        response_headers = {
            k: v for k, v in resp.headers.items()
            if k.lower() not in _STRIP_RESPONSE_HEADERS
            and not k.lower().startswith("access-control-")
        }

        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=response_headers,
        )

    except httpx.ConnectError:
        logger.warning(f"Website Builder unreachable at {WEBSITE_BUILDER_TARGET}")
        raise HTTPException(
            status_code=502,
            detail="Website Builder service is not reachable"
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Website Builder service timed out"
        )
    except Exception as e:
        logger.error(f"Website Builder proxy error: {e}")
        raise HTTPException(
            status_code=502,
            detail="Website Builder proxy error"
        )
