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

# CORS configuration - allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:5174",  # Vite dev server (alternate port)
        "http://localhost:3000",  # Alternative dev port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "https://*.zorahai.com",  # Production domains
        "https://*.holidaytoday.co.za",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Performance timing middleware - logs request durations (add first to wrap all)
from src.middleware.timing_middleware import TimingMiddleware
app.add_middleware(TimingMiddleware)

# Rate limiting middleware - protects against abuse
from src.middleware.rate_limiter import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)

# Auth middleware - validates JWT tokens for protected routes
from src.middleware.auth_middleware import AuthMiddleware
app.add_middleware(AuthMiddleware)

# PII Audit middleware - logs access to personal data for GDPR/POPIA compliance
from src.middleware.pii_audit_middleware import setup_pii_audit_middleware
pii_audit_enabled = os.getenv("PII_AUDIT_ENABLED", "true").lower() == "true"
setup_pii_audit_middleware(app, enabled=pii_audit_enabled)


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
    """Get current client information including banking details"""
    return {
        "success": True,
        "data": {
            "client_id": config.client_id,
            "client_name": config.company_name,
            "currency": config.currency,
            "timezone": config.timezone,
            "destinations": config.destination_names,
            "primary_color": config.primary_color,
            "secondary_color": config.secondary_color,
            "logo_url": config.logo_url,
            # Contact Information
            "support_email": config.primary_email,
            "quotes_email": config.sendgrid_from_email or config.primary_email,
            "support_phone": getattr(config, 'support_phone', None),
            "website": getattr(config, 'website', None),
            # Banking Details
            "banking": {
                "bank_name": config.bank_name,
                "account_name": config.bank_account_name,
                "account_number": config.bank_account_number,
                "branch_code": config.bank_branch_code,
                "swift_code": config.bank_swift_code,
                "reference_prefix": config.payment_reference_prefix,
            },
            # SendGrid Details
            "email_settings": {
                "from_name": config.sendgrid_from_name,
                "from_email": config.sendgrid_from_email,
                "reply_to": config.sendgrid_reply_to,
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
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        reload=True
    )
