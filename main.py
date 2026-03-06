"""
Multi-Tenant AI Platform Lite - Main API Server
FastAPI application serving multiple travel agency clients.
Each client is identified by the X-Client-ID header.

Lite version features:
- CRM (Pipeline, Clients, Activities)
- Quotes (Generate, View, Edit, Send)
- Invoices (Create, View, Edit, Send, PDF)
- Knowledge Base (Documents + Search)
- Email Auto-Quote (SendGrid inbound parse)
"""
# Force unbuffered output for Windows compatibility
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

import os
from dotenv import load_dotenv

# Load environment variables from .env file BEFORE other imports
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from config.loader import ClientConfig, get_config
from src.api.dependencies import get_client_config
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Configure structured JSON logging (must be before any logger usage)
from src.utils.structured_logger import setup_structured_logging, get_logger
log_level = os.getenv("LOG_LEVEL", "INFO")
json_logs = os.getenv("JSON_LOGS", "true").lower() == "true"
setup_structured_logging(level=log_level, json_output=json_logs)
logger = get_logger(__name__)

# Initialize Sentry error tracking (opt-in via SENTRY_DSN env var)
_sentry_dsn = os.getenv("SENTRY_DSN", "")
if _sentry_dsn:
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=_sentry_dsn,
            traces_sample_rate=0.1,
            environment=os.getenv("ENVIRONMENT", "development"),
            release=os.getenv("APP_VERSION", "1.0.0"),
        )
        logger.info("Sentry error tracking enabled")
    except Exception as e:
        logger.warning(f"Sentry init failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("Starting Multi-Tenant AI Platform...")

    # Suppress benign Windows asyncio connection errors (WinError 10054, 64)
    # These occur when clients disconnect but are harmless - they just spam logs
    if sys.platform == 'win32':
        import asyncio
        loop = asyncio.get_event_loop()
        _original_handler = loop.get_exception_handler()

        def _win_exception_handler(loop, context):
            exc = context.get('exception')
            if isinstance(exc, (ConnectionResetError, OSError)):
                return  # Suppress silently
            if _original_handler:
                _original_handler(loop, context)
            else:
                loop.default_exception_handler(context)

        loop.set_exception_handler(_win_exception_handler)

    # Initialize OpenTelemetry tracing (opt-in via ENABLE_TRACING=true)
    try:
        from src.utils.tracing import setup_tracing
        if setup_tracing(app):
            logger.info("OpenTelemetry tracing enabled")
    except Exception as e:
        logger.warning(f"Tracing setup skipped: {e}")

    yield
    logger.info("Shutting down...")


# Create FastAPI app
# Disable API docs endpoints in production to prevent information disclosure
_is_production = os.getenv("ENVIRONMENT", "development").lower() in ("production", "prod")
app = FastAPI(
    title="HT-ITC-Lite API",
    description="CRM, Quotes, and Invoices for travel agencies - Lite version",
    version="1.0.0-lite",
    lifespan=lifespan,
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)

# ==================== Rate Limiter Setup ====================
# Register rate limiter for auth endpoints (prevents brute force attacks)
from src.api.auth_routes import get_auth_limiter
auth_limiter = get_auth_limiter()
app.state.limiter = auth_limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ==================== Middleware Setup ====================
# NOTE: FastAPI middleware runs in REVERSE order of addition.
# Last added = first to process requests. Order matters!

# 0a. GZIP compression middleware - DISABLED on Windows
# GZipMiddleware combined with multiple BaseHTTPMiddleware layers causes response
# streaming deadlocks on Windows (responses over minimum_size never reach client).
# TODO: Re-enable when middleware is converted to pure ASGI or on Linux deployment.
# from starlette.middleware.gzip import GZipMiddleware
# app.add_middleware(GZipMiddleware, minimum_size=500)

# 0b. Request size limit middleware - reject oversized payloads (10 MB general, 50 MB uploads)
from src.middleware.request_size_middleware import RequestSizeMiddleware
app.add_middleware(RequestSizeMiddleware)

# 1. PII Audit middleware - logs access to personal data for GDPR/POPIA compliance
from src.middleware.pii_audit_middleware import setup_pii_audit_middleware
pii_audit_enabled = os.getenv("PII_AUDIT_ENABLED", "true").lower() == "true"
setup_pii_audit_middleware(app, enabled=pii_audit_enabled)

# 2. Auth middleware - validates JWT tokens for protected routes
from src.middleware.auth_middleware import AuthMiddleware
app.add_middleware(AuthMiddleware)

# 3. Rate limiting middleware - protects against abuse
from src.middleware.rate_limiter import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)

# 4. Performance timing middleware - logs request durations
from src.middleware.timing_middleware import TimingMiddleware
app.add_middleware(TimingMiddleware)

# 5. Security headers middleware - adds CSP, X-Frame-Options, HSTS, etc.
from src.middleware.security_headers import SecurityHeadersMiddleware
app.add_middleware(SecurityHeadersMiddleware)

# 6. CORS middleware - MUST be added LAST so it runs FIRST
# This ensures CORS headers are added to ALL responses including errors
def get_cors_origins() -> list:
    """
    Get allowed CORS origins from environment or use defaults.

    Environment Variable:
        CORS_ORIGINS: Comma-separated list of allowed origins.

    Format Examples:
        - Single origin: CORS_ORIGINS=https://app.example.com
        - Multiple origins: CORS_ORIGINS=https://app.example.com,https://admin.example.com
        - With ports: CORS_ORIGINS=http://localhost:3000,http://localhost:5173

    Production Recommendation:
        Set CORS_ORIGINS explicitly in production to restrict access to known
        frontend domains only. Avoid wildcards in production for security.

    Development Default:
        When CORS_ORIGINS is not set, allows localhost ports 5173-5180 (Vite),
        3000 (React), and *.zorahai.com, *.holidaytoday.co.za subdomains.

    Returns:
        list: List of allowed origin strings.
    """
    env_origins = os.getenv("CORS_ORIGINS", "")
    if env_origins:
        return [origin.strip() for origin in env_origins.split(",") if origin.strip()]

    # Default origins for development and production
    # Include multiple Vite ports since it auto-increments when ports are in use
    return [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://localhost:5177",
        "http://localhost:5178",
        "http://localhost:5179",
        "http://localhost:5180",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:5176",
        "http://127.0.0.1:5177",
        "http://127.0.0.1:5178",
        "http://127.0.0.1:5179",
        "http://127.0.0.1:5180",
        "http://127.0.0.1:3000",
        "https://*.zorahai.com",
        "https://*.holidaytoday.co.za",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization", "Content-Type", "X-Client-ID", "X-Tenant-ID",
        "X-Request-ID", "X-Admin-Token", "Accept", "Origin",
    ],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-Response-Time"],
)

# 7. Request ID middleware - generates unique request IDs for tracing
# MUST be added LAST so it runs FIRST (generates ID before other middleware logs)
from src.middleware.request_id_middleware import RequestIdMiddleware
app.add_middleware(RequestIdMiddleware)


# ==================== Health & Info Endpoints ====================

@app.get("/")
async def root():
    """Root endpoint - API info"""
    return {
        "name": "HT-ITC-Lite",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Basic health check endpoint for load balancers"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/health/ready")
async def readiness_check(config: ClientConfig = Depends(get_client_config)):
    """
    Readiness check - verifies all dependencies are available.
    Use for Kubernetes readiness probes.
    """
    checks = {
        "database": "unknown",
        "bigquery": "unknown",
    }
    all_healthy = True

    # Check Supabase connection
    try:
        from src.tools.supabase_tool import SupabaseTool
        supabase = SupabaseTool(config)
        if supabase.client:
            # Simple query to verify connection
            supabase.client.table('quotes').select("id").limit(1).execute()
            checks["database"] = "healthy"
        else:
            checks["database"] = "not_configured"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)[:50]}"
        all_healthy = False

    # Check BigQuery connection
    try:
        from src.tools.bigquery_tool import BigQueryTool
        bq = BigQueryTool(config)
        if bq.client:
            # Simple query to verify connection
            list(bq.client.query("SELECT 1").result())
            checks["bigquery"] = "healthy"
        else:
            checks["bigquery"] = "not_configured"
    except Exception as e:
        checks["bigquery"] = f"unhealthy: {str(e)[:50]}"
        all_healthy = False

    # Include circuit breaker statuses
    try:
        from src.utils.circuit_breaker import sendgrid_circuit, supabase_circuit
        circuit_breakers = {
            "sendgrid": sendgrid_circuit.get_status(),
            "supabase": supabase_circuit.get_status(),
        }
    except Exception:
        circuit_breakers = {}

    status_code = 200 if all_healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_healthy else "not_ready",
            "checks": checks,
            "circuit_breakers": circuit_breakers,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.get("/health/live")
async def liveness_check():
    """
    Liveness check - verifies the application is running.
    Use for Kubernetes liveness probes.
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/v1/client/info")
async def get_client_info(config: ClientConfig = Depends(get_client_config)):
    """Get current client information including banking details.

    Reads from database first (tenant_settings table), then falls back to config file.
    """
    from src.tools.supabase_tool import SupabaseTool

    # Get settings from database (may override config)
    db_settings = {}
    try:
        db = SupabaseTool(config)
        db_settings = db.get_tenant_settings() or {}
        logger.info(f"Loaded tenant settings for {config.client_id}: company_name={db_settings.get('company_name')}")
    except Exception as e:
        logger.warning(f"Could not load tenant settings from database: {e}")

    return {
        "success": True,
        "data": {
            "client_id": config.client_id,
            # Company info: DB first, then config fallback
            "client_name": db_settings.get("company_name") or config.company_name,
            "currency": db_settings.get("currency") or config.currency,
            "timezone": db_settings.get("timezone") or config.timezone,
            "destinations": config.destination_names,
            "primary_color": config.primary_color,
            "secondary_color": config.secondary_color,
            "logo_url": config.logo_url,
            # Contact Information: DB first, then config fallback
            "support_email": db_settings.get("support_email") or config.primary_email,
            "quotes_email": db_settings.get("quotes_email") or config.sendgrid_from_email or config.primary_email,
            "support_phone": db_settings.get("support_phone") or getattr(config, 'support_phone', None),
            "website": db_settings.get("website") or getattr(config, 'website', None),
            # Banking Details: DB first, then config fallback
            "banking": {
                "bank_name": db_settings.get("bank_name") or config.bank_name,
                "account_name": db_settings.get("bank_account_name") or config.bank_account_name,
                "account_number": db_settings.get("bank_account_number") or config.bank_account_number,
                "branch_code": db_settings.get("bank_branch_code") or config.bank_branch_code,
                "swift_code": db_settings.get("bank_swift_code") or config.bank_swift_code,
                "reference_prefix": db_settings.get("payment_reference_prefix") or config.payment_reference_prefix,
            },
            # Email Settings: DB first, then config fallback
            "email_settings": {
                "from_name": db_settings.get("email_from_name") or config.sendgrid_from_name,
                "from_email": db_settings.get("email_from_email") or config.sendgrid_from_email,
                "reply_to": db_settings.get("email_reply_to") or config.sendgrid_reply_to,
            },
        }
    }


# ==================== Include All Routers ====================

from src.api.routes import include_routers
include_routers(app)


# ==================== Error Handlers ====================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler — don't swallow HTTPExceptions."""
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "error": exc.detail}
        )
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error"}
    )


# ==================== Run Server ====================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    reload = os.getenv("RELOAD", "false").lower() == "true"

    logger.info(f"Starting server on {host}:{port} (reload={reload})")

    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
