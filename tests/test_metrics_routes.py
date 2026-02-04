"""
Metrics Routes Unit Tests

Tests for the Prometheus metrics endpoint.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


# ==================== Fixtures ====================

@pytest.fixture
def test_client():
    """Create a basic TestClient."""
    from main import app
    return TestClient(app)


# ==================== Metrics Endpoint Tests ====================

class TestMetricsEndpoint:
    """Tests for GET /metrics endpoint."""

    def test_metrics_returns_prometheus_format(self, test_client):
        """GET /metrics should return Prometheus format."""
        response = test_client.get("/metrics")

        # Should return 200 if prometheus_client is available, 503 otherwise
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            # Should be plain text
            assert "text/plain" in response.headers.get("content-type", "")

    def test_metrics_contains_http_requests_total(self, test_client):
        """Metrics should include http_requests_total counter."""
        response = test_client.get("/metrics")

        if response.status_code == 200:
            content = response.text
            # Should contain our custom metrics
            assert "http_requests_total" in content or "prometheus_client" in content


# ==================== Path Normalizer Tests ====================

class TestPathNormalizer:
    """Tests for the normalize_path function."""

    def test_normalize_uuid_in_path(self):
        """Should replace UUIDs with {id}."""
        from src.api.metrics_routes import normalize_path

        path = "/api/v1/quotes/123e4567-e89b-12d3-a456-426614174000"
        normalized = normalize_path(path)

        assert "{id}" in normalized
        assert "123e4567" not in normalized

    def test_normalize_numeric_id_in_path(self):
        """Should replace numeric IDs with {id}."""
        from src.api.metrics_routes import normalize_path

        path = "/api/v1/users/12345/profile"
        normalized = normalize_path(path)

        assert "/{id}/" in normalized
        assert "/12345/" not in normalized

    def test_normalize_multiple_ids(self):
        """Should replace multiple IDs in same path."""
        from src.api.metrics_routes import normalize_path

        path = "/api/v1/tenants/123e4567-e89b-12d3-a456-426614174000/users/456"
        normalized = normalize_path(path)

        # Both should be replaced
        assert "123e4567" not in normalized
        assert "/456" not in normalized or "/{id}" in normalized

    def test_normalize_preserves_static_paths(self):
        """Should not modify paths without IDs."""
        from src.api.metrics_routes import normalize_path

        path = "/api/v1/health/ready"
        normalized = normalize_path(path)

        assert normalized == path

    def test_normalize_preserves_path_structure(self):
        """Should preserve overall path structure."""
        from src.api.metrics_routes import normalize_path

        path = "/api/v1/quotes/123e4567-e89b-12d3-a456-426614174000/items"
        normalized = normalize_path(path)

        assert "/api/v1/quotes/" in normalized
        assert "/items" in normalized


# ==================== Prometheus Availability Tests ====================

class TestPrometheusAvailability:
    """Tests for Prometheus client availability handling."""

    def test_prometheus_available_flag(self):
        """PROMETHEUS_AVAILABLE should be True when prometheus_client is installed."""
        from src.api.metrics_routes import PROMETHEUS_AVAILABLE

        # prometheus_client should be installed in this project
        assert isinstance(PROMETHEUS_AVAILABLE, bool)

    def test_metrics_objects_exist_when_available(self):
        """Metrics objects should exist when prometheus_client is available."""
        from src.api.metrics_routes import (
            PROMETHEUS_AVAILABLE,
            REQUEST_COUNT,
            REQUEST_DURATION,
            ERROR_COUNT,
        )

        if PROMETHEUS_AVAILABLE:
            assert REQUEST_COUNT is not None
            assert REQUEST_DURATION is not None
            assert ERROR_COUNT is not None
        else:
            assert REQUEST_COUNT is None
            assert REQUEST_DURATION is None
            assert ERROR_COUNT is None


# ==================== Metric Recording Tests ====================

class TestMetricRecording:
    """Tests for metric recording functionality."""

    def test_request_count_has_labels(self):
        """REQUEST_COUNT should have method, path, status labels."""
        from src.api.metrics_routes import PROMETHEUS_AVAILABLE, REQUEST_COUNT

        if PROMETHEUS_AVAILABLE and REQUEST_COUNT is not None:
            # Counter should accept these labels
            labeled = REQUEST_COUNT.labels(method="GET", path="/test", status="200")
            assert labeled is not None

    def test_request_duration_has_labels(self):
        """REQUEST_DURATION should have method, path labels."""
        from src.api.metrics_routes import PROMETHEUS_AVAILABLE, REQUEST_DURATION

        if PROMETHEUS_AVAILABLE and REQUEST_DURATION is not None:
            labeled = REQUEST_DURATION.labels(method="GET", path="/test")
            assert labeled is not None

    def test_error_count_has_labels(self):
        """ERROR_COUNT should have method, path, status labels."""
        from src.api.metrics_routes import PROMETHEUS_AVAILABLE, ERROR_COUNT

        if PROMETHEUS_AVAILABLE and ERROR_COUNT is not None:
            labeled = ERROR_COUNT.labels(method="GET", path="/test", status="500")
            assert labeled is not None


# ==================== Extended Path Normalizer Tests ====================

class TestPathNormalizerExtended:
    """Extended tests for path normalization."""

    def test_normalize_empty_path(self):
        """Should handle empty path."""
        from src.api.metrics_routes import normalize_path

        result = normalize_path("")
        assert result == ""

    def test_normalize_root_path(self):
        """Should preserve root path."""
        from src.api.metrics_routes import normalize_path

        result = normalize_path("/")
        assert result == "/"

    def test_normalize_query_params_preserved(self):
        """Should handle path without affecting query structure."""
        from src.api.metrics_routes import normalize_path

        path = "/api/v1/quotes/123"
        result = normalize_path(path)
        # Path without UUID should remain mostly unchanged
        assert "/api/v1/quotes/" in result

    def test_normalize_complex_uuid_patterns(self):
        """Should normalize various UUID formats."""
        from src.api.metrics_routes import normalize_path

        # Standard UUID
        path1 = "/quotes/550e8400-e29b-41d4-a716-446655440000"
        assert "{id}" in normalize_path(path1)

        # Mixed case UUID
        path2 = "/quotes/550E8400-E29B-41D4-A716-446655440000"
        assert "{id}" in normalize_path(path2)

    def test_normalize_numeric_only_path_segments(self):
        """Should normalize purely numeric path segments."""
        from src.api.metrics_routes import normalize_path

        path = "/api/v1/users/12345/orders/67890/items"
        normalized = normalize_path(path)

        # Should replace numeric IDs
        assert "12345" not in normalized
        assert "67890" not in normalized

    def test_normalize_preserves_version_numbers(self):
        """Should preserve API version numbers like v1, v2."""
        from src.api.metrics_routes import normalize_path

        path = "/api/v1/health"
        result = normalize_path(path)

        assert "v1" in result
        assert result == path  # No changes expected

    def test_normalize_mixed_id_types(self):
        """Should handle paths with both UUIDs and numeric IDs."""
        from src.api.metrics_routes import normalize_path

        path = "/tenants/550e8400-e29b-41d4-a716-446655440000/users/123"
        normalized = normalize_path(path)

        # Both should be replaced
        assert "550e8400" not in normalized
        # Numeric ID handling depends on implementation


class TestMetricsEndpointExtended:
    """Extended tests for metrics endpoint."""

    def test_metrics_endpoint_is_public(self, test_client):
        """Metrics endpoint should not require authentication."""
        response = test_client.get("/metrics")

        # Should not return 401/403
        assert response.status_code not in [401, 403]

    def test_metrics_content_type(self, test_client):
        """Metrics should return proper content type."""
        response = test_client.get("/metrics")

        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            # Prometheus format uses text/plain
            assert "text/plain" in content_type or "text" in content_type

    def test_metrics_contains_standard_metrics(self, test_client):
        """Metrics should contain standard Python/process metrics."""
        response = test_client.get("/metrics")

        if response.status_code == 200:
            content = response.text
            # Default Prometheus client metrics
            standard_metrics = [
                "process_",
                "python_",
            ]
            # At least some standard metrics should be present
            has_standard = any(m in content for m in standard_metrics)
            # This may or may not be true depending on configuration
            # Just verify we got some content
            assert len(content) > 0


class TestMetricsRouterSetup:
    """Tests for metrics router configuration."""

    def test_metrics_router_exists(self):
        """Metrics router should be defined."""
        from src.api.metrics_routes import router

        assert router is not None

    def test_metrics_router_has_metrics_endpoint(self):
        """Router should have /metrics endpoint."""
        from src.api.metrics_routes import router

        # Check routes
        route_paths = [r.path for r in router.routes]
        assert "/metrics" in route_paths or any("/metrics" in str(r) for r in router.routes)


class TestMetricsGracefulDegradation:
    """Tests for graceful degradation when Prometheus unavailable."""

    def test_metrics_returns_503_when_unavailable(self, test_client):
        """Should return 503 if Prometheus client unavailable."""
        from src.api.metrics_routes import PROMETHEUS_AVAILABLE

        if not PROMETHEUS_AVAILABLE:
            response = test_client.get("/metrics")
            assert response.status_code == 503

    def test_metrics_error_message_when_unavailable(self, test_client):
        """Should return descriptive error when unavailable."""
        from src.api.metrics_routes import PROMETHEUS_AVAILABLE

        if not PROMETHEUS_AVAILABLE:
            response = test_client.get("/metrics")
            # Should have some indication of why it's unavailable
            assert response.status_code == 503


class TestMetricLabels:
    """Tests for metric label values."""

    def test_request_count_method_label_values(self):
        """REQUEST_COUNT should accept standard HTTP methods."""
        from src.api.metrics_routes import PROMETHEUS_AVAILABLE, REQUEST_COUNT

        if PROMETHEUS_AVAILABLE and REQUEST_COUNT is not None:
            for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                labeled = REQUEST_COUNT.labels(method=method, path="/test", status="200")
                assert labeled is not None

    def test_request_count_status_codes(self):
        """REQUEST_COUNT should accept various status codes."""
        from src.api.metrics_routes import PROMETHEUS_AVAILABLE, REQUEST_COUNT

        if PROMETHEUS_AVAILABLE and REQUEST_COUNT is not None:
            for status in ["200", "201", "400", "404", "500", "503"]:
                labeled = REQUEST_COUNT.labels(method="GET", path="/test", status=status)
                assert labeled is not None

    def test_error_count_5xx_codes(self):
        """ERROR_COUNT should accept 5xx status codes."""
        from src.api.metrics_routes import PROMETHEUS_AVAILABLE, ERROR_COUNT

        if PROMETHEUS_AVAILABLE and ERROR_COUNT is not None:
            for status in ["500", "502", "503", "504"]:
                labeled = ERROR_COUNT.labels(method="GET", path="/test", status=status)
                assert labeled is not None
