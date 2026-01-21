"""
Provisioning Service Unit Tests

Comprehensive tests for tenant provisioning service:
- SendGridProvisioner class
- TenantProvisioningService class
- Subuser creation
- API key creation
- Verified sender setup
- Domain authentication
- Client config generation
- Prompt template creation

Uses mocked external services (SendGrid, BigQuery, Supabase).
These tests verify:
1. Service initialization
2. API request formatting
3. Error handling
4. Config file generation
5. End-to-end provisioning flow
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path
import json
import yaml
import tempfile
import os


# ==================== Fixtures ====================

@pytest.fixture
def sendgrid_api_key():
    """Test SendGrid API key."""
    return "SG.test-master-api-key"


@pytest.fixture
def mock_tenant_config():
    """Sample tenant configuration for provisioning."""
    return {
        "client_id": "test_travel",
        "company_name": "Test Travel Agency",
        "short_name": "testtravel",
        "contact_email": "admin@testtravel.com",
        "from_email": "sales@testtravel.com",
        "from_name": "Test Travel Sales",
        "domain": "testtravel.com",
        "timezone": "Africa/Johannesburg",
        "currency": "ZAR",
        "destinations": ["Cape Town", "Zanzibar", "Victoria Falls"],
        "primary_color": "#FF6B6B",
        "secondary_color": "#4ECDC4",
        "address": "123 Main St",
        "city": "Cape Town",
        "country": "South Africa"
    }


# ==================== SendGridProvisioner Tests ====================

class TestSendGridProvisionerInit:
    """Test SendGridProvisioner initialization."""

    def test_init_with_api_key(self, sendgrid_api_key):
        """Provisioner initializes with API key."""
        from src.services.provisioning_service import SendGridProvisioner

        provisioner = SendGridProvisioner(sendgrid_api_key)

        assert provisioner.api_key == sendgrid_api_key
        assert "Bearer" in provisioner.headers["Authorization"]
        assert provisioner.base_url == "https://api.sendgrid.com/v3"


class TestSendGridSubuserCreation:
    """Test SendGrid subuser creation."""

    @patch("src.services.provisioning_service.requests.post")
    def test_create_subuser_success(self, mock_post, sendgrid_api_key):
        """Successful subuser creation."""
        from src.services.provisioning_service import SendGridProvisioner

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "username": "testtravel",
            "user_id": 12345
        }
        mock_post.return_value = mock_response

        provisioner = SendGridProvisioner(sendgrid_api_key)
        result = provisioner.create_subuser(
            username="test_travel",
            email="admin@testtravel.com"
        )

        assert result["success"] == True
        assert "data" in result
        assert "password" in result["data"]  # Auto-generated

    @patch("src.services.provisioning_service.requests.post")
    def test_create_subuser_sanitizes_username(self, mock_post, sendgrid_api_key):
        """Username is sanitized to lowercase alphanumeric."""
        from src.services.provisioning_service import SendGridProvisioner

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"username": "testtravel123"}
        mock_post.return_value = mock_response

        provisioner = SendGridProvisioner(sendgrid_api_key)
        provisioner.create_subuser(
            username="Test_Travel-123!",
            email="admin@test.com"
        )

        # Check the request was made with sanitized username
        call_args = mock_post.call_args
        request_body = call_args.kwargs["json"]
        assert request_body["username"] == "testtravel123"

    @patch("src.services.provisioning_service.requests.post")
    def test_create_subuser_failure(self, mock_post, sendgrid_api_key):
        """Handle subuser creation failure."""
        from src.services.provisioning_service import SendGridProvisioner

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Username already exists"
        mock_post.return_value = mock_response

        provisioner = SendGridProvisioner(sendgrid_api_key)
        result = provisioner.create_subuser(
            username="existing_user",
            email="admin@test.com"
        )

        assert result["success"] == False
        assert "error" in result


class TestSendGridAPIKeyCreation:
    """Test SendGrid API key creation."""

    @patch("src.services.provisioning_service.requests.post")
    def test_create_api_key_success(self, mock_post, sendgrid_api_key):
        """Successful API key creation."""
        from src.services.provisioning_service import SendGridProvisioner

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "api_key": "SG.new-api-key",
            "api_key_id": "key-id-123",
            "name": "test-key"
        }
        mock_post.return_value = mock_response

        provisioner = SendGridProvisioner(sendgrid_api_key)
        result = provisioner.create_api_key(name="test-key")

        assert result["success"] == True
        assert result["data"]["api_key"] == "SG.new-api-key"

    @patch("src.services.provisioning_service.requests.post")
    def test_create_api_key_with_subuser(self, mock_post, sendgrid_api_key):
        """API key created on behalf of subuser."""
        from src.services.provisioning_service import SendGridProvisioner

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"api_key": "SG.subuser-key"}
        mock_post.return_value = mock_response

        provisioner = SendGridProvisioner(sendgrid_api_key)
        provisioner.create_api_key(name="subuser-key", subuser="testsubuser")

        # Check on-behalf-of header was set
        call_args = mock_post.call_args
        headers = call_args.kwargs["headers"]
        assert headers.get("on-behalf-of") == "testsubuser"

    @patch("src.services.provisioning_service.requests.post")
    def test_create_api_key_default_scopes(self, mock_post, sendgrid_api_key):
        """Default scopes are applied."""
        from src.services.provisioning_service import SendGridProvisioner

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"api_key": "SG.key"}
        mock_post.return_value = mock_response

        provisioner = SendGridProvisioner(sendgrid_api_key)
        provisioner.create_api_key(name="test-key")

        call_args = mock_post.call_args
        request_body = call_args.kwargs["json"]
        assert "mail.send" in request_body["scopes"]


class TestSendGridVerifiedSender:
    """Test verified sender creation."""

    @patch("src.services.provisioning_service.requests.post")
    def test_add_verified_sender_success(self, mock_post, sendgrid_api_key):
        """Successful verified sender creation."""
        from src.services.provisioning_service import SendGridProvisioner

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": 12345,
            "from_email": "sales@test.com",
            "verified": True
        }
        mock_post.return_value = mock_response

        provisioner = SendGridProvisioner(sendgrid_api_key)
        result = provisioner.add_verified_sender(
            from_email="sales@test.com",
            from_name="Test Sales",
            reply_to="support@test.com",
            nickname="Test Company",
            address="123 Main St",
            city="Cape Town",
            country="South Africa"
        )

        assert result["success"] == True


class TestSendGridIPAssignment:
    """Test IP address assignment."""

    @patch("src.services.provisioning_service.requests.put")
    @patch("src.services.provisioning_service.requests.get")
    def test_assign_ip_success(self, mock_get, mock_put, sendgrid_api_key):
        """Successful IP assignment."""
        from src.services.provisioning_service import SendGridProvisioner

        # Mock GET IPs response
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = [{"ip": "1.2.3.4"}]
        mock_get.return_value = mock_get_response

        # Mock PUT assignment response
        mock_put_response = MagicMock()
        mock_put_response.status_code = 200
        mock_put_response.json.return_value = {"ips": ["1.2.3.4"]}
        mock_put.return_value = mock_put_response

        provisioner = SendGridProvisioner(sendgrid_api_key)
        result = provisioner.assign_ip_to_subuser("testuser")

        assert result["success"] == True
        assert result["ip"] == "1.2.3.4"

    @patch("src.services.provisioning_service.requests.get")
    def test_assign_ip_no_ips_available(self, mock_get, sendgrid_api_key):
        """Handle no IPs available."""
        from src.services.provisioning_service import SendGridProvisioner

        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = []  # No IPs
        mock_get.return_value = mock_get_response

        provisioner = SendGridProvisioner(sendgrid_api_key)
        result = provisioner.assign_ip_to_subuser("testuser")

        assert result["success"] == False
        assert "No IPs available" in result["error"]


class TestSendGridDomainAuth:
    """Test domain authentication setup."""

    @patch("src.services.provisioning_service.requests.post")
    def test_setup_domain_authentication_success(self, mock_post, sendgrid_api_key):
        """Successful domain authentication setup."""
        from src.services.provisioning_service import SendGridProvisioner

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": 1234,
            "domain": "testtravel.com",
            "dns": [
                {"type": "CNAME", "host": "em1234", "data": "sendgrid.net"}
            ]
        }
        mock_post.return_value = mock_response

        provisioner = SendGridProvisioner(sendgrid_api_key)
        result = provisioner.setup_domain_authentication(
            domain="testtravel.com"
        )

        assert result["success"] == True
        assert "data" in result


# ==================== TenantProvisioningService Tests ====================

class TestTenantProvisioningServiceInit:
    """Test TenantProvisioningService initialization."""

    def test_init_with_env_vars(self):
        """Service initializes from environment variables."""
        from src.services.provisioning_service import TenantProvisioningService

        with patch.dict(os.environ, {
            "SENDGRID_MASTER_API_KEY": "SG.test-key",
            "GCP_PROJECT_ID": "test-project"
        }):
            service = TenantProvisioningService()

            assert service.sendgrid_key == "SG.test-key"
            assert service.gcp_project == "test-project"

    def test_init_with_explicit_params(self):
        """Service initializes with explicit parameters."""
        from src.services.provisioning_service import TenantProvisioningService

        service = TenantProvisioningService(
            sendgrid_master_key="SG.explicit-key",
            gcp_project_id="explicit-project"
        )

        assert service.sendgrid_key == "SG.explicit-key"
        assert service.gcp_project == "explicit-project"


class TestTenantProvisioning:
    """Test full tenant provisioning flow."""

    @patch("src.services.provisioning_service.requests.post")
    @patch("src.services.provisioning_service.requests.get")
    @patch("src.services.provisioning_service.requests.put")
    def test_provision_tenant_full_flow(
        self, mock_put, mock_get, mock_post,
        mock_tenant_config, tmp_path
    ):
        """Full provisioning flow creates all resources."""
        from src.services.provisioning_service import TenantProvisioningService

        # Mock all API responses
        mock_post.return_value = MagicMock(
            status_code=201,
            json=lambda: {"api_key": "SG.new-key", "api_key_id": "123"}
        )
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: [{"ip": "1.2.3.4"}]
        )
        mock_put.return_value = MagicMock(
            status_code=200,
            json=lambda: {"ips": ["1.2.3.4"]}
        )

        service = TenantProvisioningService(
            sendgrid_master_key="SG.master-key",
            base_path=str(tmp_path)
        )

        result = service.provision_tenant(
            config=mock_tenant_config,
            create_sendgrid_subuser=True,
            create_bigquery_dataset=False
        )

        # Check result structure
        assert result["client_id"] == "test_travel"
        assert "steps_completed" in result
        assert "credentials" in result

    def test_provision_tenant_creates_config_file(
        self, mock_tenant_config, tmp_path
    ):
        """Provisioning creates client.yaml file."""
        from src.services.provisioning_service import TenantProvisioningService

        service = TenantProvisioningService(
            sendgrid_master_key=None,  # Skip SendGrid
            base_path=str(tmp_path)
        )

        result = service.provision_tenant(
            config=mock_tenant_config,
            create_sendgrid_subuser=False,
            create_bigquery_dataset=False
        )

        # Check config file was created
        config_path = tmp_path / "clients" / "test_travel" / "client.yaml"
        assert config_path.exists()

        # Verify config content
        with open(config_path) as f:
            config = yaml.safe_load(f)
            assert config["client"]["id"] == "test_travel"
            assert config["client"]["name"] == "Test Travel Agency"
            assert config["branding"]["company_name"] == "Test Travel Agency"

    def test_provision_tenant_creates_prompts(
        self, mock_tenant_config, tmp_path
    ):
        """Provisioning creates prompt template files."""
        from src.services.provisioning_service import TenantProvisioningService

        service = TenantProvisioningService(
            sendgrid_master_key=None,
            base_path=str(tmp_path)
        )

        service.provision_tenant(
            config=mock_tenant_config,
            create_sendgrid_subuser=False,
            create_bigquery_dataset=False
        )

        # Check prompt files were created
        prompts_dir = tmp_path / "clients" / "test_travel" / "prompts"
        assert prompts_dir.exists()
        assert (prompts_dir / "inbound.txt").exists()
        assert (prompts_dir / "helpdesk.txt").exists()
        assert (prompts_dir / "outbound.txt").exists()

    def test_provision_tenant_prompt_content(
        self, mock_tenant_config, tmp_path
    ):
        """Prompt templates contain company-specific content."""
        from src.services.provisioning_service import TenantProvisioningService

        service = TenantProvisioningService(
            sendgrid_master_key=None,
            base_path=str(tmp_path)
        )

        service.provision_tenant(
            config=mock_tenant_config,
            create_sendgrid_subuser=False,
            create_bigquery_dataset=False
        )

        # Check inbound prompt content
        inbound_path = tmp_path / "clients" / "test_travel" / "prompts" / "inbound.txt"
        content = inbound_path.read_text()
        assert "Test Travel Agency" in content
        assert "Cape Town" in content or "Zanzibar" in content

    def test_provision_tenant_creates_env_example(
        self, mock_tenant_config, tmp_path
    ):
        """Provisioning creates .env.example file."""
        from src.services.provisioning_service import TenantProvisioningService

        service = TenantProvisioningService(
            sendgrid_master_key=None,
            base_path=str(tmp_path)
        )

        service.provision_tenant(
            config=mock_tenant_config,
            create_sendgrid_subuser=False,
            create_bigquery_dataset=False
        )

        env_path = tmp_path / "clients" / "test_travel" / ".env.example"
        assert env_path.exists()
        content = env_path.read_text()
        assert "SENDGRID_API_KEY" in content


class TestTenantProvisioningErrors:
    """Test error handling in provisioning."""

    @patch("src.services.provisioning_service.requests.post")
    def test_provision_handles_sendgrid_failure(
        self, mock_post, mock_tenant_config, tmp_path
    ):
        """Provisioning continues with partial success."""
        from src.services.provisioning_service import TenantProvisioningService

        mock_post.return_value = MagicMock(
            status_code=400,
            text="SendGrid API Error"
        )

        service = TenantProvisioningService(
            sendgrid_master_key="SG.test-key",
            base_path=str(tmp_path)
        )

        result = service.provision_tenant(
            config=mock_tenant_config,
            create_sendgrid_subuser=True
        )

        # Should have partial success (config created, SendGrid failed)
        assert "errors" in result
        assert len(result["errors"]) > 0
        assert "client_config" in result["steps_completed"]


class TestConfigGeneration:
    """Test client configuration file generation."""

    def test_config_has_destinations(self, mock_tenant_config, tmp_path):
        """Config includes destination list."""
        from src.services.provisioning_service import TenantProvisioningService

        service = TenantProvisioningService(
            sendgrid_master_key=None,
            base_path=str(tmp_path)
        )

        service.provision_tenant(
            config=mock_tenant_config,
            create_sendgrid_subuser=False
        )

        config_path = tmp_path / "clients" / "test_travel" / "client.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert "destinations" in config
        assert len(config["destinations"]) == 3
        # Each destination should have name, code, enabled
        for dest in config["destinations"]:
            assert "name" in dest
            assert "code" in dest
            assert "enabled" in dest

    def test_config_has_infrastructure(self, mock_tenant_config, tmp_path):
        """Config includes infrastructure settings."""
        from src.services.provisioning_service import TenantProvisioningService

        service = TenantProvisioningService(
            sendgrid_master_key=None,
            base_path=str(tmp_path)
        )

        service.provision_tenant(
            config=mock_tenant_config,
            create_sendgrid_subuser=False
        )

        config_path = tmp_path / "clients" / "test_travel" / "client.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert "infrastructure" in config
        assert "gcp" in config["infrastructure"]
        assert "supabase" in config["infrastructure"]
        assert "openai" in config["infrastructure"]

    def test_config_has_email_settings(self, mock_tenant_config, tmp_path):
        """Config includes email settings."""
        from src.services.provisioning_service import TenantProvisioningService

        service = TenantProvisioningService(
            sendgrid_master_key=None,
            base_path=str(tmp_path)
        )

        service.provision_tenant(
            config=mock_tenant_config,
            create_sendgrid_subuser=False
        )

        config_path = tmp_path / "clients" / "test_travel" / "client.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert "email" in config
        assert config["email"]["primary"] == "sales@testtravel.com"
        assert "sendgrid" in config["email"]


# ==================== Deprovisioning Tests ====================

class TestTenantDeprovisioning:
    """Test tenant deprovisioning (cleanup)."""

    def test_deprovision_returns_result(self, tmp_path):
        """Deprovisioning returns result structure."""
        from src.services.provisioning_service import TenantProvisioningService

        service = TenantProvisioningService(
            base_path=str(tmp_path)
        )

        result = service.deprovision_tenant("test_tenant")

        assert "success" in result
        assert "steps_completed" in result
        assert "errors" in result


# ==================== API Routes Tests ====================

class TestProvisioningRoutes:
    """Test provisioning API routes creation."""

    def test_create_provisioning_routes(self):
        """create_provisioning_routes returns router."""
        from src.services.provisioning_service import create_provisioning_routes

        router = create_provisioning_routes()

        assert router is not None
        assert router.prefix == "/api/v1/admin/tenants"
