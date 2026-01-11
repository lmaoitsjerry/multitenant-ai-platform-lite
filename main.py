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

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from config.loader import ClientConfig, get_config

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("Starting Multi-Tenant AI Platform...")
    yield
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Multi-Tenant AI Travel Platform Lite",
    description="CRM, Quotes, and Invoices for travel agencies - Lite version",
    version="1.0.0-lite",
    lifespan=lifespan
)

# ==================== Middleware Setup ====================
# NOTE: FastAPI middleware runs in REVERSE order of addition.
# Last added = first to process requests. Order matters!

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

# 5. CORS middleware - MUST be added LAST so it runs FIRST
# This ensures CORS headers are added to ALL responses including errors
def get_cors_origins() -> list:
    """Get allowed CORS origins from environment or use defaults."""
    env_origins = os.getenv("CORS_ORIGINS", "")
    if env_origins:
        return [origin.strip() for origin in env_origins.split(",") if origin.strip()]

    # Default origins for development and production
    return [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:3000",
        "https://*.zorahai.com",
        "https://*.holidaytoday.co.za",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
)


# ==================== Dependency ====================

def get_client_config(x_client_id: str = Header(None, alias="X-Client-ID")) -> ClientConfig:
    """Get client configuration from header"""
    client_id = x_client_id or os.getenv("CLIENT_ID", "africastay")

    try:
        config = get_config(client_id)
        return config
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail=f"Unknown client: {client_id}")
    except Exception as e:
        logger.error(f"Error loading config for {client_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")


# ==================== Health & Info Endpoints ====================

@app.get("/")
async def root():
    """Root endpoint - API info"""
    return {
        "name": "Multi-Tenant AI Travel Platform",
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

    status_code = 200 if all_healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_healthy else "not_ready",
            "checks": checks,
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
    except Exception as e:
        logger.debug(f"Could not load tenant settings from database: {e}")

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
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error", "detail": str(exc)}
    )


# ==================== Run Server ====================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8080))
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
