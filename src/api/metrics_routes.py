"""
Prometheus Metrics Endpoint

Exposes /metrics for Prometheus scraping. Guarded behind try/except so
the app still starts if prometheus_client is not installed.
"""

import re
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

metrics_router = APIRouter(tags=["Monitoring"])

try:
    from prometheus_client import (
        Counter,
        Histogram,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )

    # ── Metrics definitions ──
    REQUEST_COUNT = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "path", "status"],
    )

    REQUEST_DURATION = Histogram(
        "http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "path"],
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )

    ERROR_COUNT = Counter(
        "http_errors_total",
        "Total HTTP error responses (4xx/5xx)",
        ["method", "path", "status"],
    )

    PROMETHEUS_AVAILABLE = True

except ImportError:
    PROMETHEUS_AVAILABLE = False
    REQUEST_COUNT = None
    REQUEST_DURATION = None
    ERROR_COUNT = None


# ── Path normalizer (reduce cardinality) ──

_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I
)
_ID_RE = re.compile(r"/\d+(?=/|$)")


def normalize_path(path: str) -> str:
    """Replace UUIDs and numeric IDs with placeholders."""
    path = _UUID_RE.sub("{id}", path)
    path = _ID_RE.sub("/{id}", path)
    return path


@metrics_router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """Prometheus metrics endpoint."""
    if not PROMETHEUS_AVAILABLE:
        return PlainTextResponse(
            "# prometheus_client not installed\n", status_code=503
        )
    return PlainTextResponse(
        generate_latest(), media_type=CONTENT_TYPE_LATEST
    )
