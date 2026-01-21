"""
Unit tests for Rate Limiting

Tests cover:
- InMemoryRateLimitStore behavior
- RateLimiter logic
- RateLimitMiddleware integration
- Configuration defaults and overrides
- Redis fallback behavior

These tests verify the rate limiting system works correctly for
both in-memory and Redis backends without requiring Redis in CI.
"""

import pytest
import time
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.middleware.rate_limiter import (
    InMemoryRateLimitStore,
    RedisRateLimitStore,
    RateLimiter,
    RateLimitMiddleware,
    RateLimitConfig,
    get_store,
    get_rate_limit_store_info,
)


# ==================== InMemoryRateLimitStore Tests ====================

class TestInMemoryRateLimitStore:
    """Tests for in-memory rate limit storage."""

    def test_increment_returns_count(self):
        """Increment should return the new count."""
        store = InMemoryRateLimitStore()

        count1 = store.increment("test_key", 60)
        count2 = store.increment("test_key", 60)
        count3 = store.increment("test_key", 60)

        assert count1 == 1
        assert count2 == 2
        assert count3 == 3

    def test_get_count_returns_current(self):
        """Get count should return current value."""
        store = InMemoryRateLimitStore()

        store.increment("test_key", 60)
        store.increment("test_key", 60)

        assert store.get_count("test_key") == 2

    def test_get_count_returns_zero_for_unknown(self):
        """Get count should return 0 for unknown keys."""
        store = InMemoryRateLimitStore()

        assert store.get_count("unknown_key") == 0

    def test_reset_clears_count(self):
        """Reset should clear the count for a key."""
        store = InMemoryRateLimitStore()

        store.increment("test_key", 60)
        store.increment("test_key", 60)
        store.reset("test_key")

        assert store.get_count("test_key") == 0

    def test_expired_entries_cleaned(self):
        """Expired entries should be cleaned up."""
        store = InMemoryRateLimitStore()

        # Set a very short window (1 second)
        store.increment("test_key", 1)
        assert store.get_count("test_key") == 1

        # Wait for expiry
        time.sleep(1.1)

        # Should be cleaned up on next access
        assert store.get_count("test_key") == 0

    def test_different_keys_independent(self):
        """Different keys should have independent counts."""
        store = InMemoryRateLimitStore()

        store.increment("key_a", 60)
        store.increment("key_a", 60)
        store.increment("key_b", 60)

        assert store.get_count("key_a") == 2
        assert store.get_count("key_b") == 1

    def test_reset_nonexistent_key_no_error(self):
        """Reset should not error for nonexistent key."""
        store = InMemoryRateLimitStore()

        # Should not raise
        store.reset("nonexistent_key")

        assert store.get_count("nonexistent_key") == 0


# ==================== RateLimitConfig Tests ====================

class TestRateLimitConfig:
    """Tests for rate limit configuration."""

    def test_get_limit_exact_match(self):
        """Should return exact match limit."""
        requests, window = RateLimitConfig.get_limit('/api/v1/quotes/generate')

        assert requests == 200
        assert window == 3600

    def test_get_limit_default_for_unknown(self):
        """Should return default for unknown paths."""
        requests, window = RateLimitConfig.get_limit('/api/v1/unknown/endpoint')

        assert requests == RateLimitConfig.DEFAULT_REQUESTS_PER_MINUTE
        assert window == 60

    def test_get_daily_limit_quotes(self):
        """Should return daily limit for quotes."""
        limit = RateLimitConfig.get_daily_limit('quotes')
        assert limit == 1000

    def test_get_daily_limit_emails(self):
        """Should return daily limit for emails."""
        limit = RateLimitConfig.get_daily_limit('emails')
        assert limit == 1500

    def test_get_daily_limit_unknown_returns_default(self):
        """Should return default for unknown resource type."""
        limit = RateLimitConfig.get_daily_limit('unknown_resource')
        assert limit == 1000  # default

    def test_get_limit_prefix_match(self):
        """Should match prefix for nested paths."""
        # /api/v1/quotes should match /api/v1/quotes prefix
        requests, window = RateLimitConfig.get_limit('/api/v1/quotes')

        assert requests == 600
        assert window == 60

    def test_get_limit_helpdesk_chat(self):
        """Should return correct limits for helpdesk chat."""
        requests, window = RateLimitConfig.get_limit('/api/v1/helpdesk/chat')

        assert requests == 1200
        assert window == 3600

    def test_get_limit_webhooks(self):
        """Should return high limits for webhooks."""
        requests, window = RateLimitConfig.get_limit('/webhooks/email')

        assert requests == 2000
        assert window == 60


# ==================== RateLimiter Tests ====================

class TestRateLimiter:
    """Tests for RateLimiter logic."""

    def test_is_allowed_under_limit(self):
        """Should return True when under limit."""
        store = InMemoryRateLimitStore()
        limiter = RateLimiter(store=store)

        # Should be allowed (under limit of 10)
        assert limiter.is_allowed("tenant_1", "/api/test", 10, 60) is True

    def test_is_allowed_at_limit(self):
        """Should return True at exactly the limit."""
        store = InMemoryRateLimitStore()
        limiter = RateLimiter(store=store)

        # Make 9 requests (limit is 10)
        for _ in range(9):
            limiter.is_allowed("tenant_1", "/api/test", 10, 60)

        # 10th request should still be allowed (count 10 = at limit)
        assert limiter.is_allowed("tenant_1", "/api/test", 10, 60) is True

    def test_is_allowed_over_limit(self):
        """Should return False when over limit."""
        store = InMemoryRateLimitStore()
        limiter = RateLimiter(store=store)

        # Make 10 requests to reach limit
        for _ in range(10):
            limiter.is_allowed("tenant_1", "/api/test", 10, 60)

        # 11th request should be denied (count 11 > limit 10)
        assert limiter.is_allowed("tenant_1", "/api/test", 10, 60) is False

    def test_check_rate_limit_returns_tuple(self):
        """check_rate_limit should return correct tuple."""
        store = InMemoryRateLimitStore()
        limiter = RateLimiter(store=store)

        allowed, current, limit, reset = limiter.check_rate_limit(
            "tenant_1", "/api/test", 100, 60
        )

        assert allowed is True
        assert current == 1
        assert limit == 100
        assert reset == 60

    def test_different_tenants_independent(self):
        """Different tenants should have independent limits."""
        store = InMemoryRateLimitStore()
        limiter = RateLimiter(store=store)

        # Exhaust tenant_1's limit
        for _ in range(10):
            limiter.is_allowed("tenant_1", "/api/test", 10, 60)

        # tenant_2 should still be allowed
        assert limiter.is_allowed("tenant_2", "/api/test", 10, 60) is True

        # tenant_1 should be denied (11th request)
        assert limiter.is_allowed("tenant_1", "/api/test", 10, 60) is False

    def test_different_endpoints_independent(self):
        """Different endpoints should have independent limits."""
        store = InMemoryRateLimitStore()
        limiter = RateLimiter(store=store)

        # Exhaust limit for /api/endpoint_a
        for _ in range(10):
            limiter.is_allowed("tenant_1", "/api/endpoint_a", 10, 60)

        # /api/endpoint_b should still be allowed
        assert limiter.is_allowed("tenant_1", "/api/endpoint_b", 10, 60) is True

        # /api/endpoint_a should be denied
        assert limiter.is_allowed("tenant_1", "/api/endpoint_a", 10, 60) is False

    def test_uses_config_when_no_limit_specified(self):
        """Should use RateLimitConfig when no limit specified."""
        store = InMemoryRateLimitStore()
        limiter = RateLimiter(store=store)

        # Call without specifying limits - should use config
        allowed = limiter.is_allowed("tenant_1", "/api/v1/quotes/generate")

        assert allowed is True  # Should use config limits


# ==================== RateLimitMiddleware Tests ====================

class TestRateLimitMiddleware:
    """Tests for rate limit middleware integration."""

    @pytest.fixture
    def app_with_middleware(self):
        """Create a test app with rate limiting middleware."""
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware)

        @app.get("/api/test")
        def test_endpoint():
            return {"status": "ok"}

        @app.get("/health")
        def health_endpoint():
            return {"status": "healthy"}

        @app.get("/docs")
        def docs_endpoint():
            return {"docs": "here"}

        return app

    def test_returns_rate_limit_headers(self, app_with_middleware):
        """Response should include rate limit headers."""
        client = TestClient(app_with_middleware)

        response = client.get("/api/test", headers={"X-Client-ID": "test_tenant"})

        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    def test_skips_health_endpoint(self, app_with_middleware):
        """Should not rate limit health endpoints."""
        client = TestClient(app_with_middleware)

        # Make many requests to health endpoint
        for _ in range(100):
            response = client.get("/health")
            assert response.status_code == 200

        # No rate limit headers on health endpoint
        response = client.get("/health")
        assert "X-RateLimit-Limit" not in response.headers

    def test_skips_docs_endpoint(self, app_with_middleware):
        """Should not rate limit docs endpoint."""
        client = TestClient(app_with_middleware)

        for _ in range(100):
            response = client.get("/docs")
            assert response.status_code == 200

    def test_uses_client_id_header(self, app_with_middleware):
        """Should use X-Client-ID for tenant identification."""
        client = TestClient(app_with_middleware)

        # Different tenants should have independent limits
        response1 = client.get("/api/test", headers={"X-Client-ID": "tenant_a"})
        response2 = client.get("/api/test", headers={"X-Client-ID": "tenant_b"})

        # Both should succeed (independent limits)
        assert response1.status_code == 200
        assert response2.status_code == 200

    def test_uses_default_tenant_without_header(self, app_with_middleware):
        """Should use default tenant when X-Client-ID not provided."""
        client = TestClient(app_with_middleware)

        # Request without X-Client-ID header
        response = client.get("/api/test")

        # Should still work (uses default)
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers

    def test_rate_limit_headers_values(self, app_with_middleware):
        """Rate limit header values should be correct."""
        client = TestClient(app_with_middleware)

        response = client.get("/api/test", headers={"X-Client-ID": "tenant_check"})

        limit = int(response.headers["X-RateLimit-Limit"])
        remaining = int(response.headers["X-RateLimit-Remaining"])

        assert limit > 0
        assert remaining >= 0
        assert remaining <= limit


# ==================== Store Info Tests ====================

class TestStoreInfo:
    """Tests for rate limit store information."""

    def test_get_store_info_memory(self):
        """Should return memory backend info when Redis not configured."""
        # Clear any cached store
        import src.middleware.rate_limiter as rl
        rl._store = None

        with patch.dict('os.environ', {}, clear=True):
            # Force recreation of store
            rl._store = None
            info = get_rate_limit_store_info()

        assert info["backend"] == "memory"
        assert info["redis_connected"] is False

    def test_get_store_info_includes_message(self):
        """Store info should include a message."""
        import src.middleware.rate_limiter as rl
        rl._store = None

        with patch.dict('os.environ', {}, clear=True):
            rl._store = None
            info = get_rate_limit_store_info()

        assert "message" in info
        assert isinstance(info["message"], str)


# ==================== Redis Fallback Tests ====================

# Check if redis module is available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class TestRedisFallback:
    """Tests for Redis fallback behavior.

    These tests verify that the RedisRateLimitStore falls back correctly
    when Redis is unavailable. Tests are skipped if redis package not installed.
    """

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
    def test_falls_back_when_redis_unavailable(self):
        """Should fall back to memory when Redis connection fails."""
        with patch.object(redis, 'from_url') as mock_redis:
            mock_redis.side_effect = Exception("Connection refused")

            store = RedisRateLimitStore("redis://invalid:6379")

            # Should use fallback
            assert store._redis is None

            # Should still work (using fallback)
            count = store.increment("test_key", 60)
            assert count == 1

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
    def test_is_healthy_returns_false_when_no_redis(self):
        """is_healthy should return False when Redis not connected."""
        with patch.object(redis, 'from_url') as mock_redis:
            mock_redis.side_effect = Exception("Connection refused")

            store = RedisRateLimitStore("redis://invalid:6379")

            assert store.is_healthy() is False

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
    def test_get_count_uses_fallback(self):
        """get_count should use fallback when Redis unavailable."""
        with patch.object(redis, 'from_url') as mock_redis:
            mock_redis.side_effect = Exception("Connection refused")

            store = RedisRateLimitStore("redis://invalid:6379")

            # Increment then get count - should use fallback
            store.increment("test_key", 60)
            count = store.get_count("test_key")

            assert count == 1

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
    def test_reset_uses_fallback(self):
        """reset should use fallback when Redis unavailable."""
        with patch.object(redis, 'from_url') as mock_redis:
            mock_redis.side_effect = Exception("Connection refused")

            store = RedisRateLimitStore("redis://invalid:6379")

            store.increment("test_key", 60)
            store.reset("test_key")
            count = store.get_count("test_key")

            assert count == 0

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
    def test_redis_store_with_valid_connection(self):
        """Test Redis store with mocked valid connection."""
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True

        # Mock pipeline
        mock_pipe = MagicMock()
        mock_pipe.execute.return_value = [5]  # Returns count of 5
        mock_redis_client.pipeline.return_value = mock_pipe

        with patch.object(redis, 'from_url', return_value=mock_redis_client):
            store = RedisRateLimitStore("redis://localhost:6379")

            assert store.is_healthy() is True

            # Test increment uses Redis pipeline
            count = store.increment("test_key", 60)
            assert count == 5
            mock_pipe.incr.assert_called_once_with("test_key")
            mock_pipe.expire.assert_called_once_with("test_key", 60)

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
    def test_redis_store_get_count_valid(self):
        """Test Redis store get_count with mocked connection."""
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True
        mock_redis_client.get.return_value = b"42"

        with patch.object(redis, 'from_url', return_value=mock_redis_client):
            store = RedisRateLimitStore("redis://localhost:6379")

            count = store.get_count("test_key")
            assert count == 42
            mock_redis_client.get.assert_called_once_with("test_key")

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
    def test_redis_store_get_count_none(self):
        """Test Redis store get_count returns 0 for non-existent key."""
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True
        mock_redis_client.get.return_value = None

        with patch.object(redis, 'from_url', return_value=mock_redis_client):
            store = RedisRateLimitStore("redis://localhost:6379")

            count = store.get_count("nonexistent")
            assert count == 0

    def test_fallback_without_redis_module(self):
        """Test that RedisRateLimitStore gracefully handles missing Redis.

        The rate limiter should fall back to in-memory storage when Redis
        module import fails inside the store constructor.
        """
        # This tests the actual behavior when the redis import inside
        # RedisRateLimitStore fails (fallback to memory)
        store = RedisRateLimitStore("redis://invalid:6379")

        # Should use in-memory fallback
        count = store.increment("test_key", 60)
        assert count == 1

        count2 = store.increment("test_key", 60)
        assert count2 == 2

        assert store.get_count("test_key") == 2

        store.reset("test_key")
        assert store.get_count("test_key") == 0


# ==================== Rate Limit Decorator Tests ====================

class TestRateLimitDecorator:
    """Tests for the @rate_limit decorator."""

    def test_decorator_exists(self):
        """Rate limit decorator should be importable."""
        from src.middleware.rate_limiter import rate_limit

        assert callable(rate_limit)

    def test_decorator_creates_wrapper(self):
        """Decorator should create a wrapper function."""
        from src.middleware.rate_limiter import rate_limit

        @rate_limit(requests=10, window=60)
        async def test_func():
            return "result"

        assert callable(test_func)
        assert test_func.__name__ == "test_func"


# ==================== Get Store Tests ====================

class TestGetStore:
    """Tests for the get_store function."""

    def test_get_store_returns_store(self):
        """get_store should return a RateLimitStore instance."""
        import src.middleware.rate_limiter as rl
        rl._store = None

        with patch.dict('os.environ', {}, clear=True):
            store = get_store()

        assert store is not None
        assert hasattr(store, 'increment')
        assert hasattr(store, 'get_count')
        assert hasattr(store, 'reset')

    def test_get_store_caches_instance(self):
        """get_store should return the same instance on subsequent calls."""
        import src.middleware.rate_limiter as rl
        rl._store = None

        with patch.dict('os.environ', {}, clear=True):
            store1 = get_store()
            store2 = get_store()

        assert store1 is store2

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
    def test_get_store_uses_redis_when_configured(self):
        """get_store should use Redis when REDIS_URL is set."""
        import src.middleware.rate_limiter as rl
        rl._store = None

        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True

        with patch.dict('os.environ', {'REDIS_URL': 'redis://localhost:6379'}):
            with patch.object(redis, 'from_url', return_value=mock_redis_client):
                rl._store = None
                store = get_store()

        assert isinstance(store, RedisRateLimitStore)

    def test_get_store_uses_memory_without_redis_url(self):
        """get_store should use in-memory when REDIS_URL not set."""
        import src.middleware.rate_limiter as rl
        rl._store = None

        with patch.dict('os.environ', {}, clear=True):
            rl._store = None
            store = get_store()

        assert isinstance(store, InMemoryRateLimitStore)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
