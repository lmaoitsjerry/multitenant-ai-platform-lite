"""
Security Headers Middleware (Pure ASGI)

Adds security headers to all API responses to protect against common
web vulnerabilities like XSS, clickjacking, and MIME sniffing.

Headers added:
- X-Frame-Options: Prevents clickjacking
- X-Content-Type-Options: Prevents MIME sniffing
- X-XSS-Protection: Enables browser XSS filtering (legacy, but harmless)
- Strict-Transport-Security: Enforces HTTPS
- Content-Security-Policy: Restricts resource loading
- Referrer-Policy: Controls referrer information

Note: Public PDF endpoints (/api/v1/public/*) allow iframe embedding
for quote and invoice previews in the dashboard.
"""

import os
import logging

logger = logging.getLogger(__name__)

# Build frame-ancestors from CORS_ORIGINS env var (includes frontend URLs)
_cors_origins = os.getenv("CORS_ORIGINS", "")
_extra_origins = [o.strip() for o in _cors_origins.split(",") if o.strip()] if _cors_origins else []
_frame_ancestors = "'self' http://localhost:* https://localhost:*"
if _extra_origins:
    _frame_ancestors += " " + " ".join(_extra_origins)

# Default CSP for API-only responses (restrictive)
DEFAULT_CSP = "default-src 'none'; frame-ancestors 'none'"

# CSP for embeddable content (PDFs that can be shown in iframes)
EMBEDDABLE_CSP = f"default-src 'none'; frame-ancestors {_frame_ancestors}"

# Paths that allow iframe embedding (for PDF previews and knowledge base)
EMBEDDABLE_PATHS = (
    "/api/v1/public/quotes/",
    "/api/v1/public/invoices/",
    "/api/v1/knowledge/global/",
)


class SecurityHeadersMiddleware:
    """Pure ASGI middleware that adds security headers to all responses."""

    def __init__(self, app):
        self.app = app
        self.is_production = os.getenv("ENVIRONMENT", "development") != "development"
        self.csp = os.getenv("SECURITY_CSP", DEFAULT_CSP)

    def _is_embeddable_path(self, path: str) -> bool:
        """Check if the path should allow iframe embedding."""
        return any(path.startswith(prefix) for prefix in EMBEDDABLE_PATHS)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Get the request path
        path = scope.get("path", "")
        is_embeddable = self._is_embeddable_path(path)

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))

                # Use appropriate CSP and X-Frame-Options based on path
                if is_embeddable:
                    csp_value = EMBEDDABLE_CSP
                    frame_options = b"SAMEORIGIN"
                else:
                    csp_value = self.csp
                    frame_options = b"DENY"

                extra_headers = [
                    (b"x-frame-options", frame_options),
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-xss-protection", b"1; mode=block"),
                    (b"content-security-policy", csp_value.encode()),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                    (b"permissions-policy", b"geolocation=(), camera=(), microphone=()"),
                ]
                if self.is_production:
                    extra_headers.append(
                        (b"strict-transport-security", b"max-age=31536000; includeSubDomains")
                    )
                message = {
                    **message,
                    "headers": list(message.get("headers", [])) + extra_headers,
                }
            await send(message)

        await self.app(scope, receive, send_with_headers)
