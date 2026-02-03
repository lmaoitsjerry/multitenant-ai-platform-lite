"""
Timing Middleware Tests

Tests for the performance timing middleware.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from starlette.requests import Request
from starlette.responses import Response


class TestTimingMiddleware:
    """Tests for the TimingMiddleware class."""

    def test_middleware_has_slow_threshold(self):
        """Middleware should have configurable slow threshold."""
        from src.middleware.timing_middleware import SLOW_THRESHOLD_MS

        assert SLOW_THRESHOLD_MS == 500  # 500ms

    def test_middleware_has_critical_threshold(self):
        """Middleware should have critical threshold."""
        from src.middleware.timing_middleware import CRITICAL_THRESHOLD_MS

        assert CRITICAL_THRESHOLD_MS == 2000  # 2s

    @pytest.mark.asyncio
    async def test_skips_health_check_endpoints(self):
        """Middleware should skip timing for health endpoints."""
        from src.middleware.timing_middleware import TimingMiddleware

        app = MagicMock()
        middleware = TimingMiddleware(app)

        # Mock request for /health/live
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/health/live",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)

        expected_response = Response(content="OK")
        call_next = AsyncMock(return_value=expected_response)

        response = await middleware.dispatch(request, call_next)

        # Should have called next without adding timing header
        call_next.assert_called_once()
        # Health endpoints skip the timing logic
        assert "X-Response-Time" not in response.headers

    @pytest.mark.asyncio
    async def test_skips_root_endpoint(self):
        """Middleware should skip timing for root endpoint."""
        from src.middleware.timing_middleware import TimingMiddleware

        app = MagicMock()
        middleware = TimingMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)

        expected_response = Response(content="OK")
        call_next = AsyncMock(return_value=expected_response)

        response = await middleware.dispatch(request, call_next)

        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_adds_response_time_header(self):
        """Middleware should add X-Response-Time header."""
        from src.middleware.timing_middleware import TimingMiddleware

        app = MagicMock()
        middleware = TimingMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/quotes",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)

        expected_response = Response(content="OK")
        call_next = AsyncMock(return_value=expected_response)

        response = await middleware.dispatch(request, call_next)

        # Should have timing header
        assert "X-Response-Time" in response.headers
        assert "ms" in response.headers["X-Response-Time"]

    @pytest.mark.asyncio
    async def test_logs_request_duration(self):
        """Middleware should log request duration."""
        from src.middleware.timing_middleware import TimingMiddleware

        app = MagicMock()
        middleware = TimingMiddleware(app)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/helpdesk/ask",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)

        expected_response = Response(content="OK", status_code=200)
        call_next = AsyncMock(return_value=expected_response)

        with patch('src.middleware.timing_middleware.logger') as mock_logger:
            response = await middleware.dispatch(request, call_next)

            # Should have logged (info for fast requests)
            assert mock_logger.info.called or mock_logger.warning.called

    @pytest.mark.asyncio
    async def test_logs_warning_for_slow_requests(self):
        """Middleware should log warning for slow requests."""
        from src.middleware.timing_middleware import TimingMiddleware
        import time

        app = MagicMock()
        middleware = TimingMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/quotes",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)

        # Simulate slow response
        async def slow_call_next(req):
            time.sleep(0.01)  # Small delay, we'll mock the time
            return Response(content="OK", status_code=200)

        # Mock time.perf_counter to simulate slow request
        with patch('src.middleware.timing_middleware.time.perf_counter') as mock_time:
            # First call returns start time, second call returns start + 0.6s (600ms)
            mock_time.side_effect = [0, 0.6]

            with patch('src.middleware.timing_middleware.logger') as mock_logger:
                call_next = AsyncMock(return_value=Response(content="OK"))
                response = await middleware.dispatch(request, call_next)

                # Should log warning for 600ms (> 500ms threshold)
                mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_logs_critical_for_very_slow_requests(self):
        """Middleware should log critical warning for very slow requests."""
        from src.middleware.timing_middleware import TimingMiddleware

        app = MagicMock()
        middleware = TimingMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/quotes",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)

        # Mock time.perf_counter to simulate very slow request (3 seconds)
        with patch('src.middleware.timing_middleware.time.perf_counter') as mock_time:
            mock_time.side_effect = [0, 3.0]  # 3000ms

            with patch('src.middleware.timing_middleware.logger') as mock_logger:
                call_next = AsyncMock(return_value=Response(content="OK"))
                response = await middleware.dispatch(request, call_next)

                # Should log warning with "critically slow" message
                mock_logger.warning.assert_called()


class TestPrometheusIntegration:
    """Tests for Prometheus metrics integration."""

    def test_prometheus_available_flag_exists(self):
        """Module should have PROMETHEUS_AVAILABLE flag."""
        from src.middleware.timing_middleware import PROMETHEUS_AVAILABLE

        assert isinstance(PROMETHEUS_AVAILABLE, bool)

    @pytest.mark.asyncio
    async def test_records_prometheus_metrics_when_available(self):
        """Should record Prometheus metrics when available."""
        from src.middleware.timing_middleware import TimingMiddleware, PROMETHEUS_AVAILABLE

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        app = MagicMock()
        middleware = TimingMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/quotes",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=Response(content="OK", status_code=200))

        # Should not raise
        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_records_error_count_for_4xx(self):
        """Should record error count for 4xx responses."""
        from src.middleware.timing_middleware import TimingMiddleware, PROMETHEUS_AVAILABLE

        if not PROMETHEUS_AVAILABLE:
            pytest.skip("Prometheus not available")

        app = MagicMock()
        middleware = TimingMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/quotes/notfound",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=Response(content="Not Found", status_code=404))

        # Should not raise
        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 404


class TestLoggerConfiguration:
    """Tests for logger configuration."""

    def test_logger_is_configured(self):
        """Module should have a performance logger."""
        from src.middleware.timing_middleware import logger
        import logging

        assert isinstance(logger, logging.Logger)
        assert logger.name == "performance"
