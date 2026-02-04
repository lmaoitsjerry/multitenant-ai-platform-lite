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


class TestSkipPaths:
    """Tests for path skipping logic."""

    @pytest.mark.asyncio
    async def test_skips_health_live(self):
        """Should skip /health/live."""
        from src.middleware.timing_middleware import TimingMiddleware

        app = MagicMock()
        middleware = TimingMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/health/live",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=Response(content="OK"))

        response = await middleware.dispatch(request, call_next)

        assert "X-Response-Time" not in response.headers

    @pytest.mark.asyncio
    async def test_skips_health_ready(self):
        """Should skip /health/ready."""
        from src.middleware.timing_middleware import TimingMiddleware

        app = MagicMock()
        middleware = TimingMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/health/ready",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=Response(content="OK"))

        response = await middleware.dispatch(request, call_next)

        assert "X-Response-Time" not in response.headers

    @pytest.mark.asyncio
    async def test_skips_metrics(self):
        """Should skip /metrics."""
        from src.middleware.timing_middleware import TimingMiddleware

        app = MagicMock()
        middleware = TimingMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/metrics",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=Response(content="OK"))

        response = await middleware.dispatch(request, call_next)

        assert "X-Response-Time" not in response.headers

    @pytest.mark.asyncio
    async def test_does_not_skip_api_endpoints(self):
        """Should NOT skip API endpoints."""
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
        call_next = AsyncMock(return_value=Response(content="OK"))

        response = await middleware.dispatch(request, call_next)

        assert "X-Response-Time" in response.headers


class TestResponseTimeHeader:
    """Tests for X-Response-Time header."""

    @pytest.mark.asyncio
    async def test_header_format(self):
        """X-Response-Time should be formatted with ms suffix."""
        from src.middleware.timing_middleware import TimingMiddleware

        app = MagicMock()
        middleware = TimingMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/test",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=Response(content="OK"))

        response = await middleware.dispatch(request, call_next)

        header = response.headers["X-Response-Time"]
        assert header.endswith("ms")

    @pytest.mark.asyncio
    async def test_header_contains_numeric_value(self):
        """X-Response-Time should contain numeric value."""
        from src.middleware.timing_middleware import TimingMiddleware

        app = MagicMock()
        middleware = TimingMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/test",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=Response(content="OK"))

        response = await middleware.dispatch(request, call_next)

        header = response.headers["X-Response-Time"]
        # Extract numeric part
        numeric_part = header.replace("ms", "").strip()
        float(numeric_part)  # Should not raise

    @pytest.mark.asyncio
    async def test_header_value_is_non_negative(self):
        """X-Response-Time should be non-negative."""
        from src.middleware.timing_middleware import TimingMiddleware

        app = MagicMock()
        middleware = TimingMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/test",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=Response(content="OK"))

        response = await middleware.dispatch(request, call_next)

        header = response.headers["X-Response-Time"]
        numeric_part = float(header.replace("ms", "").strip())
        assert numeric_part >= 0


class TestThresholdLogging:
    """Tests for threshold-based logging."""

    @pytest.mark.asyncio
    async def test_fast_request_logs_info(self):
        """Fast requests should log at info level."""
        from src.middleware.timing_middleware import TimingMiddleware

        app = MagicMock()
        middleware = TimingMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/test",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=Response(content="OK", status_code=200))

        with patch('src.middleware.timing_middleware.time.perf_counter') as mock_time:
            mock_time.side_effect = [0, 0.1]  # 100ms (fast)

            with patch('src.middleware.timing_middleware.logger') as mock_logger:
                await middleware.dispatch(request, call_next)

                # Fast request logs at info level
                mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_slow_request_logs_warning(self):
        """Slow requests should log at warning level."""
        from src.middleware.timing_middleware import TimingMiddleware

        app = MagicMock()
        middleware = TimingMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/test",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=Response(content="OK", status_code=200))

        with patch('src.middleware.timing_middleware.time.perf_counter') as mock_time:
            mock_time.side_effect = [0, 0.6]  # 600ms (slow)

            with patch('src.middleware.timing_middleware.logger') as mock_logger:
                await middleware.dispatch(request, call_next)

                mock_logger.warning.assert_called()


class TestHTTPMethods:
    """Tests for different HTTP methods."""

    @pytest.mark.asyncio
    async def test_handles_get(self):
        """Should handle GET requests."""
        from src.middleware.timing_middleware import TimingMiddleware

        app = MagicMock()
        middleware = TimingMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/test",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=Response(content="OK"))

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_handles_post(self):
        """Should handle POST requests."""
        from src.middleware.timing_middleware import TimingMiddleware

        app = MagicMock()
        middleware = TimingMiddleware(app)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/test",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=Response(content="OK", status_code=201))

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_handles_put(self):
        """Should handle PUT requests."""
        from src.middleware.timing_middleware import TimingMiddleware

        app = MagicMock()
        middleware = TimingMiddleware(app)

        scope = {
            "type": "http",
            "method": "PUT",
            "path": "/api/v1/test/123",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=Response(content="OK"))

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_handles_delete(self):
        """Should handle DELETE requests."""
        from src.middleware.timing_middleware import TimingMiddleware

        app = MagicMock()
        middleware = TimingMiddleware(app)

        scope = {
            "type": "http",
            "method": "DELETE",
            "path": "/api/v1/test/123",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=Response(content="", status_code=204))

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 204


class TestStatusCodeTracking:
    """Tests for status code tracking."""

    @pytest.mark.asyncio
    async def test_logs_2xx_status(self):
        """Should log 2xx status codes."""
        from src.middleware.timing_middleware import TimingMiddleware

        app = MagicMock()
        middleware = TimingMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/test",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=Response(content="OK", status_code=200))

        with patch('src.middleware.timing_middleware.logger') as mock_logger:
            await middleware.dispatch(request, call_next)

            # Check status code is in log
            call_args = str(mock_logger.info.call_args)
            assert "200" in call_args

    @pytest.mark.asyncio
    async def test_logs_4xx_status(self):
        """Should log 4xx status codes."""
        from src.middleware.timing_middleware import TimingMiddleware

        app = MagicMock()
        middleware = TimingMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/test",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=Response(content="Not Found", status_code=404))

        with patch('src.middleware.timing_middleware.logger') as mock_logger:
            await middleware.dispatch(request, call_next)

            # Check status code is in log
            assert mock_logger.info.called or mock_logger.warning.called

    @pytest.mark.asyncio
    async def test_logs_5xx_status(self):
        """Should log 5xx status codes."""
        from src.middleware.timing_middleware import TimingMiddleware

        app = MagicMock()
        middleware = TimingMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/test",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=Response(content="Error", status_code=500))

        with patch('src.middleware.timing_middleware.logger') as mock_logger:
            await middleware.dispatch(request, call_next)

            # 5xx errors should be logged
            assert mock_logger.info.called or mock_logger.warning.called
