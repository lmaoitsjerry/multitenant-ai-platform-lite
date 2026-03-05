"""
Structured error handling utilities.

Complements error_handler.py (which provides log_and_raise for routes).
This module provides:
- log_and_suppress: Replace bare except:pass with visible, structured logging
- ServiceError: Typed error for service-layer failures
- handle_service_error: Convert any exception to HTTPException
- CircuitBreakerState: Metadata for degraded-service API responses

Usage:
    from src.utils.error_handling import log_and_suppress, ServiceError

    # Replace: except: pass
    try:
        cleanup_temp_file(path)
    except Exception as e:
        log_and_suppress(e, context="cleanup_temp_file", file_path=path)

    # For operations that should fail visibly:
    try:
        result = supabase.table("kb").select("*").execute()
    except Exception as e:
        raise ServiceError("knowledge_storage", "Failed to query KB", cause=e)
"""

import logging
from typing import Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    """
    Structured error for service-layer failures.
    Carries context about which service failed and why.
    """

    def __init__(
        self,
        service: str,
        message: str,
        cause: Optional[Exception] = None,
        details: Optional[dict] = None,
        status_code: int = 500,
    ):
        self.service = service
        self.message = message
        self.cause = cause
        self.details = details or {}
        self.status_code = status_code
        super().__init__(f"[{service}] {message}")

    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException for route handlers."""
        return HTTPException(
            status_code=self.status_code,
            detail={
                "error": self.message,
                "service": self.service,
                "details": self.details,
            },
        )

    def log(self, level: int = logging.ERROR):
        """Log this error with full context."""
        logger.log(
            level,
            "[%s] %s | details=%s",
            self.service,
            self.message,
            self.details,
            exc_info=self.cause,
        )


def log_and_suppress(
    error: Exception,
    context: str,
    level: int = logging.WARNING,
    **extra,
) -> None:
    """
    Log an error with context, then suppress it.

    Use ONLY for non-critical operations where failure is acceptable
    (e.g., cleanup, cache invalidation, analytics).

    This replaces bare ``except: pass`` with visible, structured logging.
    """
    logger.log(
        level,
        "Suppressed error in %s: %s | %s",
        context,
        str(error),
        extra if extra else "",
        exc_info=True if level >= logging.ERROR else False,
    )


def handle_service_error(
    error: Exception, service: str, operation: str
) -> HTTPException:
    """
    Convert any exception to an appropriate HTTPException.
    Use in route handlers as a catch-all.
    """
    if isinstance(error, HTTPException):
        return error

    if isinstance(error, ServiceError):
        error.log()
        return error.to_http_exception()

    # Unexpected error — log full traceback
    logger.error(
        "[%s] Unexpected error during %s: %s",
        service,
        operation,
        str(error),
        exc_info=True,
    )

    return HTTPException(
        status_code=500,
        detail={
            "error": f"Internal error in {service}",
            "operation": operation,
        },
    )


class CircuitBreakerState:
    """
    Lightweight circuit breaker info for user-facing responses.
    Use when a service is degraded but the request can still partially succeed.
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    @staticmethod
    def response_metadata(
        state: str, fallback_used: bool = False, service: str = ""
    ) -> dict:
        """
        Generate metadata to include in API responses when circuit breaker is active.
        Frontend can use this to show appropriate messaging.
        """
        if state == CircuitBreakerState.CLOSED and not fallback_used:
            return {}

        return {
            "_service_status": {
                "degraded": state != CircuitBreakerState.CLOSED,
                "fallback_used": fallback_used,
                "service": service,
                "message": (
                    f"The {service} service is temporarily unavailable. "
                    "Showing cached/fallback results."
                    if fallback_used
                    else ""
                ),
            },
        }
