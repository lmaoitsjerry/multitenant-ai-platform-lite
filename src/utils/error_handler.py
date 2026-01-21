"""
Error Handler Utility - Secure Error Response Generation

Provides centralized error handling to prevent information leakage in API responses.
Internal exception details are logged for debugging while generic messages are
returned to API consumers.

Security: Never expose internal exception messages to clients. Attackers can use
detailed error messages to understand system internals and find vulnerabilities.

Usage:
    from src.utils.error_handler import log_and_raise, safe_error_response

    # Option 1: Log and raise in one call
    try:
        # risky operation
    except Exception as e:
        log_and_raise(500, "processing request", e, logger)

    # Option 2: Get HTTPException for more control
    try:
        # risky operation
    except Exception as e:
        exc = safe_error_response(500, "processing request", e, logger)
        # do something before raising
        raise exc
"""

import logging
from typing import NoReturn
from fastapi import HTTPException


def safe_error_response(
    status_code: int,
    operation: str,
    exception: Exception,
    logger: logging.Logger
) -> HTTPException:
    """
    Create a safe HTTPException that doesn't expose internal details.

    Logs the full exception with traceback for debugging, then returns
    an HTTPException with a generic user-facing message.

    Args:
        status_code: HTTP status code (e.g., 500, 400)
        operation: Description of what operation failed (e.g., "listing quotes")
        exception: The caught exception
        logger: Logger instance for recording the error

    Returns:
        HTTPException with sanitized error message

    Example:
        except Exception as e:
            raise safe_error_response(500, "generating quote", e, logger)
    """
    # Log full details for debugging (includes traceback)
    logger.error(f"{operation} failed: {exception}", exc_info=True)

    # Generate user-facing message based on status code
    if status_code >= 500:
        # Server errors get generic message
        detail = f"An internal error occurred while {operation}. Please try again later."
    else:
        # Client errors (4xx) can be more specific but still don't expose internals
        detail = f"Error while {operation}. Please check your request and try again."

    return HTTPException(status_code=status_code, detail=detail)


def log_and_raise(
    status_code: int,
    operation: str,
    exception: Exception,
    logger: logging.Logger
) -> NoReturn:
    """
    Log an exception and raise a safe HTTPException.

    Convenience function that combines logging and raising in one call.

    Args:
        status_code: HTTP status code (e.g., 500, 400)
        operation: Description of what operation failed (e.g., "listing quotes")
        exception: The caught exception
        logger: Logger instance for recording the error

    Raises:
        HTTPException: Always raises with sanitized error message

    Example:
        except Exception as e:
            log_and_raise(500, "creating invoice", e, logger)
    """
    raise safe_error_response(status_code, operation, exception, logger)
