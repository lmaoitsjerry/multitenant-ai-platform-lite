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
