"""Tests for structured error handling utilities."""

import pytest
import logging
from src.utils.error_handling import (
    ServiceError,
    log_and_suppress,
    handle_service_error,
    CircuitBreakerState,
)
from fastapi import HTTPException


class TestServiceError:
    def test_creates_with_context(self):
        err = ServiceError("kb", "Query failed", status_code=503)
        assert err.service == "kb"
        assert err.message == "Query failed"
        assert err.status_code == 503

    def test_to_http_exception(self):
        err = ServiceError("kb", "Not found", status_code=404)
        http_err = err.to_http_exception()
        assert isinstance(http_err, HTTPException)
        assert http_err.status_code == 404
        assert http_err.detail["service"] == "kb"

    def test_includes_details(self):
        err = ServiceError("kb", "Failed", details={"query": "test"})
        http_err = err.to_http_exception()
        assert http_err.detail["details"]["query"] == "test"

    def test_str_representation(self):
        err = ServiceError("kb", "Query failed")
        assert "[kb] Query failed" in str(err)

    def test_logs_with_cause(self, caplog):
        cause = ValueError("underlying error")
        err = ServiceError("kb", "Wrapped", cause=cause)
        with caplog.at_level(logging.ERROR):
            err.log()
        assert "kb" in caplog.text
        assert "Wrapped" in caplog.text

    def test_default_status_code_is_500(self):
        err = ServiceError("svc", "oops")
        assert err.status_code == 500

    def test_cause_preserved(self):
        cause = RuntimeError("root cause")
        err = ServiceError("svc", "wrapped", cause=cause)
        assert err.cause is cause

    def test_empty_details_by_default(self):
        err = ServiceError("svc", "msg")
        assert err.details == {}


class TestLogAndSuppress:
    def test_logs_warning_by_default(self, caplog):
        with caplog.at_level(logging.WARNING):
            log_and_suppress(ValueError("oops"), context="test_cleanup")
        assert "test_cleanup" in caplog.text
        assert "oops" in caplog.text

    def test_includes_extra_context(self, caplog):
        with caplog.at_level(logging.WARNING):
            log_and_suppress(
                ValueError("oops"), context="cleanup", file_path="/tmp/x"
            )
        assert "file_path" in caplog.text

    def test_custom_log_level(self, caplog):
        with caplog.at_level(logging.ERROR):
            log_and_suppress(
                ValueError("bad"), context="test", level=logging.ERROR
            )
        assert "bad" in caplog.text

    def test_does_not_raise(self):
        """log_and_suppress must never propagate the error."""
        log_and_suppress(RuntimeError("kaboom"), context="test")
        # If we get here, the error was suppressed


class TestHandleServiceError:
    def test_converts_service_error(self):
        err = ServiceError("kb", "Down", status_code=503)
        http_err = handle_service_error(err, "kb", "query")
        assert http_err.status_code == 503

    def test_passes_through_http_exception(self):
        err = HTTPException(status_code=422, detail="Bad input")
        result = handle_service_error(err, "kb", "query")
        assert result.status_code == 422

    def test_wraps_unexpected_error(self):
        err = RuntimeError("unexpected")
        http_err = handle_service_error(err, "kb", "query")
        assert http_err.status_code == 500
        assert "kb" in str(http_err.detail)

    def test_wraps_with_operation_context(self):
        err = TypeError("bad type")
        http_err = handle_service_error(err, "search", "indexing")
        assert http_err.detail["operation"] == "indexing"


class TestCircuitBreakerState:
    def test_closed_returns_empty(self):
        meta = CircuitBreakerState.response_metadata("closed")
        assert meta == {}

    def test_closed_no_fallback_returns_empty(self):
        meta = CircuitBreakerState.response_metadata(
            "closed", fallback_used=False
        )
        assert meta == {}

    def test_open_with_fallback(self):
        meta = CircuitBreakerState.response_metadata(
            "open", fallback_used=True, service="kb"
        )
        assert meta["_service_status"]["degraded"] is True
        assert meta["_service_status"]["fallback_used"] is True
        assert "kb" in meta["_service_status"]["message"]

    def test_half_open(self):
        meta = CircuitBreakerState.response_metadata(
            "half_open", service="rag"
        )
        assert meta["_service_status"]["degraded"] is True

    def test_closed_with_fallback_still_reports(self):
        meta = CircuitBreakerState.response_metadata(
            "closed", fallback_used=True, service="llm"
        )
        assert "_service_status" in meta
        assert meta["_service_status"]["fallback_used"] is True

    def test_constants(self):
        assert CircuitBreakerState.CLOSED == "closed"
        assert CircuitBreakerState.OPEN == "open"
        assert CircuitBreakerState.HALF_OPEN == "half_open"
