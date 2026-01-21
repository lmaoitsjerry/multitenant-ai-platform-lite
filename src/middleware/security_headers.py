"""
Security Headers Middleware

Adds security headers to all API responses to protect against common
web vulnerabilities like XSS, clickjacking, and MIME sniffing.

Headers added:
- X-Frame-Options: Prevents clickjacking
- X-Content-Type-Options: Prevents MIME sniffing
- X-XSS-Protection: Enables browser XSS filtering (legacy, but harmless)
- Strict-Transport-Security: Enforces HTTPS
- Content-Security-Policy: Restricts resource loading
- Referrer-Policy: Controls referrer information
"""

import os
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that adds security headers to all responses."""

    # Default CSP for API-only responses (restrictive)
    DEFAULT_CSP = "default-src 'none'; frame-ancestors 'none'"

    # Environment variable to customize CSP if needed
    # e.g., for embedded widgets: "default-src 'self'; frame-ancestors https://trusted.com"

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Get CSP from environment or use default
        csp = os.getenv("SECURITY_CSP", self.DEFAULT_CSP)

        # Clickjacking protection
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Legacy XSS protection (modern browsers ignore, but harmless)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Force HTTPS (only add in production)
        # max-age=31536000 = 1 year, includeSubDomains for full domain protection
        if os.getenv("ENVIRONMENT", "development") != "development":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content Security Policy - restrictive for API
        response.headers["Content-Security-Policy"] = csp

        # Referrer policy - don't leak URLs on cross-origin requests
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy - disable unnecessary browser features
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"

        return response
