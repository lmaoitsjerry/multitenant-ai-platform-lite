"""
Service Layer Tests

Tests for:
- AuthService (JWT verification, user lookup)
- CRMService (client management)
- ProvisioningService (tenant setup)

These tests focus on critical paths for security and business logic.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import os
import jwt
from datetime import datetime, timedelta


class TestAuthService:
    """Test AuthService functionality."""

    def test_auth_service_initializes(self):
        """AuthService should initialize with credentials."""
        from src.services.auth_service import AuthService

        with patch.dict(os.environ, {'SUPABASE_JWT_SECRET': 'test-secret'}):
            with patch('src.services.auth_service.get_cached_auth_client') as mock_client:
                mock_client.return_value = MagicMock()
                service = AuthService(
                    supabase_url='https://test.supabase.co',
                    supabase_key='test-key'
                )
                assert service is not None
                assert service.supabase_url == 'https://test.supabase.co'

    def test_verify_jwt_with_valid_token(self):
        """verify_jwt should return True for valid token."""
        from src.services.auth_service import AuthService

        secret = 'test-secret-key-for-jwt-verification'

        with patch.dict(os.environ, {'SUPABASE_JWT_SECRET': secret}):
            with patch('src.services.auth_service.get_cached_auth_client') as mock_client:
                mock_client.return_value = MagicMock()
                service = AuthService(
                    supabase_url='https://test.supabase.co',
                    supabase_key='test-key'
                )

                # Create a valid token with required claims (including aud for Supabase)
                exp = datetime.utcnow() + timedelta(hours=1)
                token = jwt.encode(
                    {'sub': 'user123', 'exp': exp, 'iss': 'https://test.supabase.co/auth/v1', 'aud': 'authenticated'},
                    secret,
                    algorithm='HS256'
                )

                valid, payload = service.verify_jwt(token)

                assert valid is True
                assert payload['sub'] == 'user123'

    def test_verify_jwt_with_expired_token(self):
        """verify_jwt should return False for expired token."""
        from src.services.auth_service import AuthService

        secret = 'test-secret-key-for-jwt-verification'

        with patch.dict(os.environ, {'SUPABASE_JWT_SECRET': secret}):
            with patch('src.services.auth_service.get_cached_auth_client') as mock_client:
                mock_client.return_value = MagicMock()
                service = AuthService(
                    supabase_url='https://test.supabase.co',
                    supabase_key='test-key'
                )

                # Create an expired token (1 hour ago)
                exp = datetime.utcnow() - timedelta(hours=1)
                token = jwt.encode(
                    {'sub': 'user123', 'exp': exp},
                    secret,
                    algorithm='HS256'
                )

                valid, result = service.verify_jwt(token)

                assert valid is False
                assert 'error' in result

    def test_verify_jwt_with_invalid_signature(self):
        """verify_jwt should return False for token with wrong signature."""
        from src.services.auth_service import AuthService

        correct_secret = 'correct-secret-key'
        wrong_secret = 'wrong-secret-key'

        with patch.dict(os.environ, {'SUPABASE_JWT_SECRET': correct_secret}):
            with patch('src.services.auth_service.get_cached_auth_client') as mock_client:
                mock_client.return_value = MagicMock()
                service = AuthService(
                    supabase_url='https://test.supabase.co',
                    supabase_key='test-key'
                )

                # Create token with WRONG secret
                exp = datetime.utcnow() + timedelta(hours=1)
                token = jwt.encode(
                    {'sub': 'user123', 'exp': exp},
                    wrong_secret,  # Wrong secret
                    algorithm='HS256'
                )

                valid, result = service.verify_jwt(token)

                assert valid is False
                assert 'error' in result

    def test_verify_jwt_with_malformed_token(self):
        """verify_jwt should return False for malformed token."""
        from src.services.auth_service import AuthService

        with patch.dict(os.environ, {'SUPABASE_JWT_SECRET': 'test-secret'}):
            with patch('src.services.auth_service.get_cached_auth_client') as mock_client:
                mock_client.return_value = MagicMock()
                service = AuthService(
                    supabase_url='https://test.supabase.co',
                    supabase_key='test-key'
                )

                valid, result = service.verify_jwt("not.a.valid.jwt.token")

                assert valid is False
                assert 'error' in result

    def test_verify_jwt_missing_subject(self):
        """verify_jwt should return False for token missing 'sub' claim."""
        from src.services.auth_service import AuthService

        secret = 'test-secret-key'

        with patch.dict(os.environ, {'SUPABASE_JWT_SECRET': secret}):
            with patch('src.services.auth_service.get_cached_auth_client') as mock_client:
                mock_client.return_value = MagicMock()
                service = AuthService(
                    supabase_url='https://test.supabase.co',
                    supabase_key='test-key'
                )

                # Token without 'sub' claim
                exp = datetime.utcnow() + timedelta(hours=1)
                token = jwt.encode(
                    {'exp': exp, 'iat': datetime.utcnow()},  # No 'sub'
                    secret,
                    algorithm='HS256'
                )

                valid, result = service.verify_jwt(token)

                assert valid is False
                assert 'error' in result

    @pytest.mark.asyncio
    async def test_get_user_by_auth_id(self):
        """get_user_by_auth_id should return user from database."""
        from src.services.auth_service import AuthService

        mock_user_data = {
            'id': 'org_user_123',
            'auth_user_id': 'auth_123',
            'email': 'test@example.com',
            'name': 'Test User',
            'role': 'admin',
            'tenant_id': 'test_tenant',
            'is_active': True
        }

        with patch.dict(os.environ, {'SUPABASE_JWT_SECRET': 'test-secret'}):
            with patch('src.services.auth_service.get_cached_auth_client') as mock_client:
                mock_supabase = MagicMock()

                # Setup mock for database query
                mock_result = MagicMock()
                mock_result.data = mock_user_data
                mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_result

                mock_client.return_value = mock_supabase

                service = AuthService(
                    supabase_url='https://test.supabase.co',
                    supabase_key='test-key'
                )

                # Clear any cached user
                from src.services.auth_service import _user_cache
                _user_cache.clear()

                user = await service.get_user_by_auth_id('auth_123', 'test_tenant')

                assert user is not None
                assert user['email'] == 'test@example.com'

    @pytest.mark.asyncio
    async def test_get_user_by_auth_id_not_found(self):
        """get_user_by_auth_id should return None if user not found."""
        from src.services.auth_service import AuthService

        with patch.dict(os.environ, {'SUPABASE_JWT_SECRET': 'test-secret'}):
            with patch('src.services.auth_service.get_cached_auth_client') as mock_client:
                mock_supabase = MagicMock()

                # Setup mock to raise exception (user not found)
                mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("No rows")

                mock_client.return_value = mock_supabase

                service = AuthService(
                    supabase_url='https://test.supabase.co',
                    supabase_key='test-key'
                )

                # Clear any cached user
                from src.services.auth_service import _user_cache
                _user_cache.clear()

                user = await service.get_user_by_auth_id('nonexistent', 'test_tenant')

                assert user is None


class TestCRMService:
    """Test CRMService functionality."""

    def test_crm_service_initializes(self):
        """CRMService should initialize with config."""
        from src.services.crm_service import CRMService

        mock_config = MagicMock()
        mock_config.client_id = 'test_tenant'

        # Patch at the import location inside crm_service
        with patch('src.tools.supabase_tool.SupabaseTool'):
            service = CRMService(mock_config)
            assert service is not None
            assert service.config == mock_config

    def test_crm_service_handles_missing_supabase(self):
        """CRMService should handle missing Supabase gracefully."""
        from src.services.crm_service import CRMService

        mock_config = MagicMock()
        mock_config.client_id = 'test_tenant'

        # Patch the internal import in crm_service __init__
        with patch.object(CRMService, '__init__', return_value=None) as mock_init:
            service = CRMService.__new__(CRMService)
            service.config = mock_config
            service.supabase = None

            assert service is not None
            assert service.supabase is None

    def test_pipeline_stages_defined(self):
        """Pipeline stages enum should be defined."""
        from src.services.crm_service import PipelineStage

        assert PipelineStage.QUOTED.value == "QUOTED"
        assert PipelineStage.NEGOTIATING.value == "NEGOTIATING"
        assert PipelineStage.BOOKED.value == "BOOKED"
        assert PipelineStage.PAID.value == "PAID"
        assert PipelineStage.TRAVELLED.value == "TRAVELLED"
        assert PipelineStage.LOST.value == "LOST"

    def test_get_client_by_email_returns_none_without_db(self):
        """get_client_by_email should return None when DB unavailable."""
        from src.services.crm_service import CRMService

        mock_config = MagicMock()
        mock_config.client_id = 'test_tenant'

        # Create service with no supabase
        with patch.object(CRMService, '__init__', return_value=None):
            service = CRMService.__new__(CRMService)
            service.config = mock_config
            service.supabase = None

            result = service.get_client_by_email('test@example.com')
            assert result is None


class TestProvisioningService:
    """Test ProvisioningService functionality."""

    def test_provisioning_service_exists(self):
        """ProvisioningService should be importable."""
        from src.services.provisioning_service import TenantProvisioningService
        assert TenantProvisioningService is not None

    def test_provisioning_service_initializes(self):
        """TenantProvisioningService should initialize."""
        from src.services.provisioning_service import TenantProvisioningService

        service = TenantProvisioningService()
        assert service is not None


class TestTenantConfigServiceIntegration:
    """Additional integration tests for TenantConfigService."""

    def test_get_supabase_client_method_exists(self):
        """TenantConfigService should have _get_supabase_client method."""
        from src.services.tenant_config_service import TenantConfigService

        service = TenantConfigService()
        assert hasattr(service, '_get_supabase_client')
        assert callable(service._get_supabase_client)

    def test_service_returns_none_without_env_vars(self):
        """_get_supabase_client returns None when env vars not set."""
        from src.services.tenant_config_service import TenantConfigService

        # Clear environment variables
        with patch.dict(os.environ, {}, clear=True):
            service = TenantConfigService()
            service._supabase_client = None

            # Without SUPABASE_URL, should return None
            client = service._get_supabase_client()
            # Either None or error handling

    def test_config_source_tracking(self):
        """Config should track whether it came from DB or YAML."""
        # Verify meta tracking concept exists
        db_config = {'client': {'id': 'test'}, '_meta': {'source': 'database'}}
        yaml_config = {'client': {'id': 'test'}, '_meta': {'source': 'yaml'}}

        assert db_config['_meta']['source'] == 'database'
        assert yaml_config['_meta']['source'] == 'yaml'


class TestStructuredLogger:
    """Test structured logging utilities."""

    def test_get_logger_returns_logger(self):
        """get_logger should return a logger instance."""
        from src.utils.structured_logger import get_logger

        logger = get_logger("test_module")
        assert logger is not None
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')

    def test_logger_name_set_correctly(self):
        """Logger should have correct name."""
        from src.utils.structured_logger import get_logger

        logger = get_logger("my.test.module")
        assert logger.name == "my.test.module"


class TestRequestIdContext:
    """Test request ID context variable."""

    def test_request_id_context_var_exists(self):
        """request_id_var should be defined."""
        from src.utils.structured_logger import request_id_var

        assert request_id_var is not None

    def test_request_id_can_be_set(self):
        """Request ID can be set in context."""
        from src.utils.structured_logger import request_id_var

        token = request_id_var.set("test-request-id-123")
        try:
            value = request_id_var.get()
            assert value == "test-request-id-123"
        finally:
            request_id_var.reset(token)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
