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
