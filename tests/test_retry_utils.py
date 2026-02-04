"""
Retry Utils Tests

Tests for the reusable retry decorators.
"""

import pytest
from unittest.mock import MagicMock, patch
import requests
import httpx


class TestRetryOnNetworkError:
    """Tests for the retry_on_network_error decorator."""

    def test_decorator_returns_callable(self):
        """Decorator should return a callable."""
        from src.utils.retry_utils import retry_on_network_error

        decorator = retry_on_network_error()
        assert callable(decorator)

    def test_decorated_function_is_callable(self):
        """Decorated function should remain callable."""
        from src.utils.retry_utils import retry_on_network_error

        @retry_on_network_error(max_attempts=2)
        def my_func():
            return "result"

        assert callable(my_func)
        assert my_func() == "result"

    def test_retries_on_connection_error(self):
        """Should retry on requests ConnectionError."""
        from src.utils.retry_utils import retry_on_network_error

        call_count = 0

        @retry_on_network_error(max_attempts=3, min_wait=0, max_wait=1)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise requests.exceptions.ConnectionError("Connection failed")
            return "success"

        result = flaky_func()

        assert result == "success"
        assert call_count == 3

    def test_retries_on_timeout(self):
        """Should retry on requests Timeout."""
        from src.utils.retry_utils import retry_on_network_error

        call_count = 0

        @retry_on_network_error(max_attempts=3, min_wait=0, max_wait=1)
        def timeout_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise requests.exceptions.Timeout("Request timed out")
            return "success"

        result = timeout_func()

        assert result == "success"
        assert call_count == 2

    def test_does_not_retry_on_http_error(self):
        """Should NOT retry on HTTP errors (4xx, 5xx)."""
        from src.utils.retry_utils import retry_on_network_error

        call_count = 0

        @retry_on_network_error(max_attempts=3, min_wait=0, max_wait=1)
        def http_error_func():
            nonlocal call_count
            call_count += 1
            raise requests.exceptions.HTTPError("404 Not Found")

        with pytest.raises(requests.exceptions.HTTPError):
            http_error_func()

        # Should only be called once (no retry)
        assert call_count == 1

    def test_raises_after_max_attempts(self):
        """Should raise after max retry attempts exhausted."""
        from src.utils.retry_utils import retry_on_network_error

        call_count = 0

        @retry_on_network_error(max_attempts=2, min_wait=0, max_wait=1)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise requests.exceptions.ConnectionError("Always fails")

        with pytest.raises(requests.exceptions.ConnectionError):
            always_fails()

        assert call_count == 2

    def test_custom_max_attempts(self):
        """Should respect custom max_attempts parameter."""
        from src.utils.retry_utils import retry_on_network_error

        call_count = 0

        @retry_on_network_error(max_attempts=5, min_wait=0, max_wait=1)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 5:
                raise requests.exceptions.ConnectionError("Retry")
            return "done"

        result = flaky_func()

        assert result == "done"
        assert call_count == 5


class TestRetryOnAsyncNetworkError:
    """Tests for the retry_on_async_network_error decorator."""

    def test_decorator_returns_callable(self):
        """Async decorator should return a callable."""
        from src.utils.retry_utils import retry_on_async_network_error

        decorator = retry_on_async_network_error()
        assert callable(decorator)

    @pytest.mark.asyncio
    async def test_decorated_async_function_is_callable(self):
        """Decorated async function should remain callable."""
        from src.utils.retry_utils import retry_on_async_network_error

        @retry_on_async_network_error(max_attempts=2)
        async def my_async_func():
            return "async_result"

        result = await my_async_func()
        assert result == "async_result"

    @pytest.mark.asyncio
    async def test_retries_on_connect_error(self):
        """Should retry on httpx ConnectError."""
        from src.utils.retry_utils import retry_on_async_network_error

        call_count = 0

        @retry_on_async_network_error(max_attempts=3, min_wait=0, max_wait=1)
        async def flaky_async():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("Connection failed")
            return "success"

        result = await flaky_async()

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retries_on_timeout_exception(self):
        """Should retry on httpx TimeoutException."""
        from src.utils.retry_utils import retry_on_async_network_error

        call_count = 0

        @retry_on_async_network_error(max_attempts=3, min_wait=0, max_wait=1)
        async def timeout_async():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.TimeoutException("Timeout")
            return "success"

        result = await timeout_async()

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_does_not_retry_on_http_status_error(self):
        """Should NOT retry on HTTP status errors."""
        from src.utils.retry_utils import retry_on_async_network_error

        call_count = 0

        @retry_on_async_network_error(max_attempts=3, min_wait=0, max_wait=1)
        async def http_error_async():
            nonlocal call_count
            call_count += 1
            # Create a mock request for HTTPStatusError
            request = httpx.Request("GET", "http://test.com")
            response = httpx.Response(404, request=request)
            raise httpx.HTTPStatusError("Not Found", request=request, response=response)

        with pytest.raises(httpx.HTTPStatusError):
            await http_error_async()

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_raises_after_max_attempts_async(self):
        """Should raise after max retry attempts exhausted (async)."""
        from src.utils.retry_utils import retry_on_async_network_error

        call_count = 0

        @retry_on_async_network_error(max_attempts=2, min_wait=0, max_wait=1)
        async def always_fails_async():
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("Always fails")

        with pytest.raises(httpx.ConnectError):
            await always_fails_async()

        assert call_count == 2


class TestModuleImports:
    """Tests for module-level imports and exports."""

    def test_tenacity_imports_available(self):
        """Required tenacity imports should be available."""
        from src.utils.retry_utils import (
            retry,
            stop_after_attempt,
            wait_exponential,
            retry_if_exception_type,
            before_sleep_log,
        )

        assert callable(retry)
        assert callable(stop_after_attempt)
        assert callable(wait_exponential)
        assert callable(retry_if_exception_type)
        assert callable(before_sleep_log)

    def test_logger_is_configured(self):
        """Module should have a configured logger."""
        from src.utils.retry_utils import logger
        import logging

        assert isinstance(logger, logging.Logger)
        assert logger.name == "src.utils.retry_utils"


class TestRetryParameters:
    """Tests for retry parameter configuration."""

    def test_default_max_attempts(self):
        """Default max_attempts should be reasonable."""
        from src.utils.retry_utils import retry_on_network_error

        # Create decorator with defaults
        call_count = 0

        @retry_on_network_error()
        def test_func():
            nonlocal call_count
            call_count += 1
            raise requests.exceptions.ConnectionError("Test")

        with pytest.raises(requests.exceptions.ConnectionError):
            test_func()

        # Default should be 3 attempts
        assert call_count == 3

    def test_min_wait_parameter(self):
        """min_wait parameter should affect backoff."""
        from src.utils.retry_utils import retry_on_network_error

        # With min_wait=0, retries should be fast
        @retry_on_network_error(max_attempts=2, min_wait=0, max_wait=1)
        def fast_retry():
            raise requests.exceptions.ConnectionError("Test")

        with pytest.raises(requests.exceptions.ConnectionError):
            fast_retry()

    def test_max_wait_parameter(self):
        """max_wait parameter should cap backoff time."""
        from src.utils.retry_utils import retry_on_network_error

        @retry_on_network_error(max_attempts=2, min_wait=0, max_wait=1)
        def capped_retry():
            raise requests.exceptions.ConnectionError("Test")

        with pytest.raises(requests.exceptions.ConnectionError):
            capped_retry()


class TestRetryableExceptions:
    """Tests for which exceptions trigger retry."""

    def test_retries_requests_connection_error(self):
        """Should retry on requests.ConnectionError."""
        from src.utils.retry_utils import retry_on_network_error

        call_count = 0

        @retry_on_network_error(max_attempts=2, min_wait=0, max_wait=1)
        def conn_error():
            nonlocal call_count
            call_count += 1
            raise requests.exceptions.ConnectionError()

        with pytest.raises(requests.exceptions.ConnectionError):
            conn_error()

        assert call_count == 2

    def test_retries_requests_timeout(self):
        """Should retry on requests.Timeout."""
        from src.utils.retry_utils import retry_on_network_error

        call_count = 0

        @retry_on_network_error(max_attempts=2, min_wait=0, max_wait=1)
        def timeout():
            nonlocal call_count
            call_count += 1
            raise requests.exceptions.Timeout()

        with pytest.raises(requests.exceptions.Timeout):
            timeout()

        assert call_count == 2

    def test_does_not_retry_value_error(self):
        """Should NOT retry on ValueError."""
        from src.utils.retry_utils import retry_on_network_error

        call_count = 0

        @retry_on_network_error(max_attempts=3, min_wait=0, max_wait=1)
        def value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid value")

        with pytest.raises(ValueError):
            value_error()

        assert call_count == 1  # No retry

    def test_does_not_retry_key_error(self):
        """Should NOT retry on KeyError."""
        from src.utils.retry_utils import retry_on_network_error

        call_count = 0

        @retry_on_network_error(max_attempts=3, min_wait=0, max_wait=1)
        def key_error():
            nonlocal call_count
            call_count += 1
            raise KeyError("missing_key")

        with pytest.raises(KeyError):
            key_error()

        assert call_count == 1


class TestAsyncRetryableExceptions:
    """Tests for async exception handling."""

    @pytest.mark.asyncio
    async def test_retries_httpx_connect_error(self):
        """Should retry on httpx.ConnectError."""
        from src.utils.retry_utils import retry_on_async_network_error

        call_count = 0

        @retry_on_async_network_error(max_attempts=2, min_wait=0, max_wait=1)
        async def conn_error():
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("Connection refused")

        with pytest.raises(httpx.ConnectError):
            await conn_error()

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retries_httpx_timeout_exception(self):
        """Should retry on httpx.TimeoutException."""
        from src.utils.retry_utils import retry_on_async_network_error

        call_count = 0

        @retry_on_async_network_error(max_attempts=2, min_wait=0, max_wait=1)
        async def timeout():
            nonlocal call_count
            call_count += 1
            raise httpx.TimeoutException("Timeout")

        with pytest.raises(httpx.TimeoutException):
            await timeout()

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_does_not_retry_async_value_error(self):
        """Should NOT retry on ValueError in async."""
        from src.utils.retry_utils import retry_on_async_network_error

        call_count = 0

        @retry_on_async_network_error(max_attempts=3, min_wait=0, max_wait=1)
        async def value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid")

        with pytest.raises(ValueError):
            await value_error()

        assert call_count == 1


class TestReturnValuePreservation:
    """Tests for preserving return values."""

    def test_preserves_return_value(self):
        """Should preserve function return value."""
        from src.utils.retry_utils import retry_on_network_error

        @retry_on_network_error(max_attempts=2)
        def returns_dict():
            return {"key": "value", "number": 42}

        result = returns_dict()

        assert result == {"key": "value", "number": 42}

    def test_preserves_none_return(self):
        """Should preserve None return value."""
        from src.utils.retry_utils import retry_on_network_error

        @retry_on_network_error(max_attempts=2)
        def returns_none():
            return None

        result = returns_none()

        assert result is None

    @pytest.mark.asyncio
    async def test_preserves_async_return_value(self):
        """Should preserve async function return value."""
        from src.utils.retry_utils import retry_on_async_network_error

        @retry_on_async_network_error(max_attempts=2)
        async def async_returns_list():
            return [1, 2, 3]

        result = await async_returns_list()

        assert result == [1, 2, 3]


class TestFunctionArguments:
    """Tests for function argument handling."""

    def test_passes_args(self):
        """Should pass positional arguments to function."""
        from src.utils.retry_utils import retry_on_network_error

        @retry_on_network_error(max_attempts=2)
        def add(a, b):
            return a + b

        result = add(3, 4)

        assert result == 7

    def test_passes_kwargs(self):
        """Should pass keyword arguments to function."""
        from src.utils.retry_utils import retry_on_network_error

        @retry_on_network_error(max_attempts=2)
        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"

        result = greet("World", greeting="Hi")

        assert result == "Hi, World!"

    @pytest.mark.asyncio
    async def test_passes_async_args(self):
        """Should pass arguments to async function."""
        from src.utils.retry_utils import retry_on_async_network_error

        @retry_on_async_network_error(max_attempts=2)
        async def multiply(a, b):
            return a * b

        result = await multiply(5, 6)

        assert result == 30
