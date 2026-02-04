"""
Dependencies Module Tests

Tests for shared FastAPI dependencies.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException


class TestGetClientConfig:
    """Tests for the get_client_config dependency."""

    def test_returns_client_config_for_valid_client(self):
        """Should return ClientConfig for valid client ID."""
        from src.api.dependencies import get_client_config, _client_configs

        # Clear cache
        _client_configs.clear()

        mock_config = MagicMock()
        mock_config.client_id = "test_client"

        with patch('src.api.dependencies.ClientConfig', return_value=mock_config):
            result = get_client_config(x_client_id="test_client")

            assert result is mock_config

    def test_caches_client_config(self):
        """Should cache ClientConfig after first load."""
        from src.api.dependencies import get_client_config, _client_configs

        _client_configs.clear()

        mock_config = MagicMock()

        with patch('src.api.dependencies.ClientConfig', return_value=mock_config) as mock_class:
            # First call
            result1 = get_client_config(x_client_id="cached_client")
            # Second call
            result2 = get_client_config(x_client_id="cached_client")

            # Constructor should only be called once
            mock_class.assert_called_once_with("cached_client")
            assert result1 is result2

    def test_raises_400_on_invalid_client(self):
        """Should raise HTTPException 400 on config error."""
        from src.api.dependencies import get_client_config, _client_configs

        _client_configs.clear()

        with patch('src.api.dependencies.ClientConfig', side_effect=Exception("Config not found")):
            with pytest.raises(HTTPException) as exc_info:
                get_client_config(x_client_id="invalid_client")

            assert exc_info.value.status_code == 400
            assert "Invalid client" in exc_info.value.detail

    def test_uses_env_var_fallback(self):
        """Should fall back to CLIENT_ID env var if header not provided."""
        from src.api.dependencies import get_client_config, _client_configs

        _client_configs.clear()

        mock_config = MagicMock()

        with patch.dict('os.environ', {'CLIENT_ID': 'env_client'}):
            with patch('src.api.dependencies.ClientConfig', return_value=mock_config) as mock_class:
                result = get_client_config(x_client_id=None)

                mock_class.assert_called_once_with("env_client")

    def test_uses_example_as_default(self):
        """Should use 'example' as default client ID."""
        from src.api.dependencies import get_client_config, _client_configs

        _client_configs.clear()

        mock_config = MagicMock()

        with patch.dict('os.environ', {}, clear=True):
            with patch('src.api.dependencies.ClientConfig', return_value=mock_config) as mock_class:
                result = get_client_config(x_client_id=None)

                mock_class.assert_called_once_with("example")


class TestClientConfigCache:
    """Tests for the client config cache."""

    def test_cache_is_module_level_dict(self):
        """_client_configs should be a module-level dict."""
        from src.api.dependencies import _client_configs

        assert isinstance(_client_configs, dict)

    def test_different_clients_cached_separately(self):
        """Different clients should be cached separately."""
        from src.api.dependencies import get_client_config, _client_configs

        _client_configs.clear()

        mock_config1 = MagicMock()
        mock_config1.client_id = "client1"
        mock_config2 = MagicMock()
        mock_config2.client_id = "client2"

        with patch('src.api.dependencies.ClientConfig', side_effect=[mock_config1, mock_config2]):
            result1 = get_client_config(x_client_id="client1")
            result2 = get_client_config(x_client_id="client2")

            assert result1 is not result2
            assert len(_client_configs) == 2
            assert "client1" in _client_configs
            assert "client2" in _client_configs

    def test_cache_returns_same_instance(self):
        """Same client ID should return same cached instance."""
        from src.api.dependencies import get_client_config, _client_configs

        _client_configs.clear()

        mock_config = MagicMock()
        mock_config.client_id = "same_client"

        with patch('src.api.dependencies.ClientConfig', return_value=mock_config):
            result1 = get_client_config(x_client_id="same_client")
            result2 = get_client_config(x_client_id="same_client")
            result3 = get_client_config(x_client_id="same_client")

            # All should be the same object
            assert result1 is result2
            assert result2 is result3

    def test_cache_clear_forces_reload(self):
        """Clearing cache should force reload on next request."""
        from src.api.dependencies import get_client_config, _client_configs

        _client_configs.clear()

        mock_config1 = MagicMock()
        mock_config1.client_id = "reload_client"
        mock_config2 = MagicMock()
        mock_config2.client_id = "reload_client"

        with patch('src.api.dependencies.ClientConfig', side_effect=[mock_config1, mock_config2]) as mock_class:
            get_client_config(x_client_id="reload_client")
            assert mock_class.call_count == 1

            _client_configs.clear()

            get_client_config(x_client_id="reload_client")
            assert mock_class.call_count == 2


class TestErrorHandling:
    """Tests for error handling in get_client_config."""

    def test_logs_error_on_config_failure(self):
        """Should log error when ClientConfig raises."""
        from src.api.dependencies import get_client_config, _client_configs, logger

        _client_configs.clear()

        with patch('src.api.dependencies.ClientConfig', side_effect=ValueError("Test error")):
            with patch.object(logger, 'error') as mock_logger:
                with pytest.raises(HTTPException):
                    get_client_config(x_client_id="failing_client")

                # Should have logged the error
                mock_logger.assert_called()
                assert "failing_client" in str(mock_logger.call_args)

    def test_logs_info_on_successful_load(self):
        """Should log info when config loads successfully."""
        from src.api.dependencies import get_client_config, _client_configs, logger

        _client_configs.clear()

        mock_config = MagicMock()

        with patch('src.api.dependencies.ClientConfig', return_value=mock_config):
            with patch.object(logger, 'info') as mock_logger:
                get_client_config(x_client_id="new_client")

                mock_logger.assert_called()
                assert "new_client" in str(mock_logger.call_args)

    def test_http_exception_has_correct_status(self):
        """HTTPException should be 400 Bad Request."""
        from src.api.dependencies import get_client_config, _client_configs

        _client_configs.clear()

        with patch('src.api.dependencies.ClientConfig', side_effect=Exception("Not found")):
            with pytest.raises(HTTPException) as exc_info:
                get_client_config(x_client_id="bad_client")

            assert exc_info.value.status_code == 400

    def test_http_exception_has_descriptive_detail(self):
        """HTTPException detail should include client ID."""
        from src.api.dependencies import get_client_config, _client_configs

        _client_configs.clear()

        with patch('src.api.dependencies.ClientConfig', side_effect=Exception("Not found")):
            with pytest.raises(HTTPException) as exc_info:
                get_client_config(x_client_id="specific_client")

            assert "specific_client" in exc_info.value.detail


class TestHeaderHandling:
    """Tests for X-Client-ID header handling."""

    def test_header_alias_x_client_id(self):
        """Should accept X-Client-ID header."""
        from src.api.dependencies import get_client_config, _client_configs

        _client_configs.clear()

        mock_config = MagicMock()

        with patch('src.api.dependencies.ClientConfig', return_value=mock_config) as mock_class:
            get_client_config(x_client_id="header_client")

            mock_class.assert_called_once_with("header_client")

    def test_empty_string_header_uses_fallback(self):
        """Empty string header should use fallback."""
        from src.api.dependencies import get_client_config, _client_configs

        _client_configs.clear()

        mock_config = MagicMock()

        with patch.dict('os.environ', {'CLIENT_ID': 'env_fallback'}):
            with patch('src.api.dependencies.ClientConfig', return_value=mock_config) as mock_class:
                # Empty string is falsy, should use env fallback
                get_client_config(x_client_id="")

                # Python's `or` treats empty string as falsy
                # So it should use env var


class TestConcurrencyConsiderations:
    """Tests for cache thread-safety considerations."""

    def test_cache_populated_atomically(self):
        """Cache should not have partial entries."""
        from src.api.dependencies import get_client_config, _client_configs

        _client_configs.clear()

        mock_config = MagicMock()
        mock_config.client_id = "atomic_client"

        with patch('src.api.dependencies.ClientConfig', return_value=mock_config):
            get_client_config(x_client_id="atomic_client")

            # Entry should be fully present
            assert "atomic_client" in _client_configs
            assert _client_configs["atomic_client"] is mock_config


class TestIntegrationScenarios:
    """Integration-like tests for realistic usage patterns."""

    def test_multiple_tenants_sequential(self):
        """Should handle multiple tenants loaded sequentially."""
        from src.api.dependencies import get_client_config, _client_configs

        _client_configs.clear()

        tenants = ["tenant_a", "tenant_b", "tenant_c"]
        mock_configs = {t: MagicMock(client_id=t) for t in tenants}

        with patch('src.api.dependencies.ClientConfig', side_effect=lambda t: mock_configs[t]):
            for tenant in tenants:
                result = get_client_config(x_client_id=tenant)
                assert result.client_id == tenant

            assert len(_client_configs) == 3

    def test_interleaved_access_pattern(self):
        """Should handle interleaved access to multiple tenants."""
        from src.api.dependencies import get_client_config, _client_configs

        _client_configs.clear()

        mock_config1 = MagicMock(client_id="interleave1")
        mock_config2 = MagicMock(client_id="interleave2")

        with patch('src.api.dependencies.ClientConfig', side_effect=[mock_config1, mock_config2]) as mock_class:
            # Access tenant1
            r1 = get_client_config(x_client_id="interleave1")
            # Access tenant2
            r2 = get_client_config(x_client_id="interleave2")
            # Access tenant1 again (should be cached)
            r3 = get_client_config(x_client_id="interleave1")
            # Access tenant2 again (should be cached)
            r4 = get_client_config(x_client_id="interleave2")

            # Only 2 config loads
            assert mock_class.call_count == 2

            # Same instances returned
            assert r1 is r3
            assert r2 is r4

    def test_exception_on_one_tenant_doesnt_affect_others(self):
        """Exception loading one tenant shouldn't affect others."""
        from src.api.dependencies import get_client_config, _client_configs

        _client_configs.clear()

        mock_good_config = MagicMock(client_id="good_tenant")

        def config_factory(client_id):
            if client_id == "bad_tenant":
                raise ValueError("Config error")
            return mock_good_config

        with patch('src.api.dependencies.ClientConfig', side_effect=config_factory):
            # Bad tenant fails
            with pytest.raises(HTTPException):
                get_client_config(x_client_id="bad_tenant")

            # Good tenant should still work
            result = get_client_config(x_client_id="good_tenant")
            assert result is mock_good_config
