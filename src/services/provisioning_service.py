"""
Tenant Provisioning Service - Automated Client Onboarding

Automates the entire process of setting up a new client:
1. Create SendGrid subuser + API key
2. Create Supabase tables/RLS (if using shared instance)
3. Create BigQuery dataset (optional)
4. Generate client.yaml configuration
5. Create prompt files from templates

Usage:
    from src.services.provisioning_service import TenantProvisioningService
    
    provisioner = TenantProvisioningService()
    
    result = provisioner.provision_tenant({
        'client_id': 'acme_travel',
        'company_name': 'Acme Travel Agency',
        'contact_email': 'admin@acmetravel.com',
        'from_email': 'sales@acmetravel.com',
        'domain': 'acmetravel.com',
        'timezone': 'America/New_York',
        'currency': 'USD',
        'destinations': ['Bali', 'Maldives', 'Thailand'],
        'primary_color': '#FF6B6B',
        'secondary_color': '#4ECDC4'
    })
"""

import os
import re
import json
import yaml
import secrets
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Try imports
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from google.cloud import bigquery
    BIGQUERY_AVAILABLE = True
except ImportError:
    BIGQUERY_AVAILABLE = False

try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


class SendGridProvisioner:
    """Handles SendGrid subuser and API key creation"""
    
    def __init__(self, master_api_key: str):
        """
        Initialize with master SendGrid API key
        
        Args:
            master_api_key: Parent account API key with subuser management permissions
        """
        self.api_key = master_api_key
        self.base_url = "https://api.sendgrid.com/v3"
        self.headers = {
            "Authorization": f"Bearer {master_api_key}",
            "Content-Type": "application/json"
        }
    
    def create_subuser(
        self,
        username: str,
        email: str,
        password: Optional[str] = None,
        ips: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a SendGrid subuser
        
        Args:
            username: Subuser username (lowercase, alphanumeric)
            email: Contact email for the subuser
            password: Password (auto-generated if not provided)
            ips: List of IP addresses to assign (uses shared if not provided)
            
        Returns:
            Subuser creation response
        """
        if not password:
            password = secrets.token_urlsafe(16)
        
        # Sanitize username
        username = re.sub(r'[^a-z0-9]', '', username.lower())
        
        payload = {
            "username": username,
            "email": email,
            "password": password,
            "ips": ips or []  # Empty = use parent account IPs
        }
        
        response = requests.post(
            f"{self.base_url}/subusers",
            headers=self.headers,
            json=payload
        )
        
        if response.status_code == 201:
            result = response.json()
            result['password'] = password  # Include for initial setup
            logger.info(f"✅ SendGrid subuser created: {username}")
            return {'success': True, 'data': result}
        else:
            logger.error(f"❌ SendGrid subuser creation failed: {response.text}")
            return {'success': False, 'error': response.text}
    
    def create_api_key(
        self,
        name: str,
        scopes: Optional[List[str]] = None,
        subuser: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an API key for a subuser
        
        Args:
            name: API key name
            scopes: Permission scopes (defaults to mail.send)
            subuser: Subuser username (creates key under subuser)
            
        Returns:
            API key creation response with the key
        """
        if not scopes:
            # Default scopes for sending emails
            scopes = [
                "mail.send",
                "sender_verification_eligible",
                "2fa_exempt"
            ]
        
        payload = {
            "name": name,
            "scopes": scopes
        }
        
        headers = self.headers.copy()
        if subuser:
            headers["on-behalf-of"] = subuser
        
        response = requests.post(
            f"{self.base_url}/api_keys",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 201:
            result = response.json()
            logger.info(f"✅ SendGrid API key created: {name}")
            return {'success': True, 'data': result}
        else:
            logger.error(f"❌ SendGrid API key creation failed: {response.text}")
            return {'success': False, 'error': response.text}
    
    def add_verified_sender(
        self,
        from_email: str,
        from_name: str,
        reply_to: str,
        nickname: str,
        address: str,
        city: str,
        country: str,
        subuser: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a verified sender identity
        
        Args:
            from_email: Sender email address
            from_name: Sender display name
            reply_to: Reply-to email
            nickname: Sender nickname
            address: Physical address (required by CAN-SPAM)
            city: City
            country: Country
            subuser: Subuser username
            
        Returns:
            Verification response
        """
        payload = {
            "nickname": nickname,
            "from_email": from_email,
            "from_name": from_name,
            "reply_to": reply_to,
            "address": address,
            "city": city,
            "country": country
        }
        
        headers = self.headers.copy()
        if subuser:
            headers["on-behalf-of"] = subuser
        
        response = requests.post(
            f"{self.base_url}/verified_senders",
            headers=headers,
            json=payload
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            logger.info(f"✅ Verified sender created: {from_email}")
            return {'success': True, 'data': result}
        else:
            logger.error(f"❌ Verified sender creation failed: {response.text}")
            return {'success': False, 'error': response.text}
    
    def assign_ip_to_subuser(
        self,
        subuser: str,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assign an IP address to a subuser
        
        Args:
            subuser: Subuser username
            ip_address: Specific IP to assign (uses first available if not specified)
            
        Returns:
            Assignment result
        """
        # Get available IPs if not specified
        if not ip_address:
            resp = requests.get(f"{self.base_url}/ips", headers=self.headers)
            if resp.status_code == 200:
                ips = resp.json()
                if ips:
                    ip_address = ips[0].get('ip')
                else:
                    return {'success': False, 'error': 'No IPs available'}
            else:
                return {'success': False, 'error': resp.text}
        
        # Assign IP to subuser using PUT endpoint
        response = requests.put(
            f"{self.base_url}/subusers/{subuser}/ips",
            headers=self.headers,
            json=[ip_address]
        )
        
        if response.status_code == 200:
            logger.info(f"✅ IP {ip_address} assigned to {subuser}")
            return {'success': True, 'ip': ip_address, 'data': response.json()}
        else:
            logger.error(f"❌ IP assignment failed: {response.text}")
            return {'success': False, 'error': response.text}

    def setup_domain_authentication(
        self,
        domain: str,
        subuser: Optional[str] = None,
        custom_dkim_selector: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Initiate domain authentication (DKIM/SPF)
        
        Args:
            domain: Domain to authenticate
            subuser: Subuser username
            custom_dkim_selector: Custom DKIM selector (optional)
            
        Returns:
            DNS records that need to be added
        """
        payload = {
            "domain": domain,
            "automatic_security": True,  # Auto-rotate DKIM keys
            "default": True
        }
        
        if custom_dkim_selector:
            payload["custom_dkim_selector"] = custom_dkim_selector
        
        headers = self.headers.copy()
        if subuser:
            headers["on-behalf-of"] = subuser
        
        response = requests.post(
            f"{self.base_url}/whitelabel/domains",
            headers=headers,
            json=payload
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            logger.info(f"✅ Domain authentication initiated: {domain}")
            return {'success': True, 'data': result}
        else:
            logger.error(f"❌ Domain authentication failed: {response.text}")
            return {'success': False, 'error': response.text}


class TenantProvisioningService:
    """Complete tenant provisioning automation"""
    
    def __init__(
        self,
        sendgrid_master_key: Optional[str] = None,
        gcp_project_id: Optional[str] = None,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        base_path: Optional[str] = None
    ):
        """
        Initialize provisioning service
        
        Args:
            sendgrid_master_key: Master SendGrid API key
            gcp_project_id: GCP project for BigQuery datasets
            supabase_url: Master Supabase URL
            supabase_key: Master Supabase service key
            base_path: Project base path
        """
        self.sendgrid_key = sendgrid_master_key or os.getenv("SENDGRID_MASTER_API_KEY")
        self.gcp_project = gcp_project_id or os.getenv("GCP_PROJECT_ID")
        self.supabase_url = supabase_url or os.getenv("MASTER_SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("MASTER_SUPABASE_KEY")
        self.base_path = Path(base_path) if base_path else Path(__file__).parent.parent.parent
        
        # Initialize sub-services
        self.sendgrid = SendGridProvisioner(self.sendgrid_key) if self.sendgrid_key else None
        
        logger.info("Tenant provisioning service initialized")
    
    def provision_tenant(
        self,
        config: Dict[str, Any],
        create_sendgrid_subuser: bool = True,
        create_bigquery_dataset: bool = False,
        setup_domain_auth: bool = False
    ) -> Dict[str, Any]:
        """
        Provision a new tenant with all required resources
        
        Args:
            config: Tenant configuration dict:
                - client_id: Unique identifier (lowercase, no spaces)
                - company_name: Full company name
                - short_name: Short name
                - contact_email: Admin contact email
                - from_email: Email sender address
                - from_name: Email sender name
                - domain: Company domain (for SendGrid auth)
                - timezone: IANA timezone
                - currency: ISO currency code
                - destinations: List of destination names
                - primary_color: Brand primary color (hex)
                - secondary_color: Brand secondary color (hex)
                - address: Physical address (for CAN-SPAM)
                - city: City
                - country: Country
            create_sendgrid_subuser: Create SendGrid subuser
            create_bigquery_dataset: Create BigQuery dataset
            setup_domain_auth: Initiate domain authentication
            
        Returns:
            Provisioning result with credentials
        """
        result = {
            'success': True,
            'client_id': config['client_id'],
            'steps_completed': [],
            'credentials': {},
            'dns_records': [],
            'errors': []
        }
        
        client_id = config['client_id']
        
        try:
            # Step 1: Create SendGrid subuser
            if create_sendgrid_subuser and self.sendgrid:
                sg_result = self._provision_sendgrid(config, setup_domain_auth)
                if sg_result['success']:
                    result['steps_completed'].append('sendgrid_subuser')
                    result['credentials']['sendgrid'] = sg_result['credentials']
                    if sg_result.get('dns_records'):
                        result['dns_records'] = sg_result['dns_records']
                else:
                    result['errors'].append(f"SendGrid: {sg_result['error']}")
            
            # Step 2: Create BigQuery dataset (optional)
            if create_bigquery_dataset and BIGQUERY_AVAILABLE:
                bq_result = self._provision_bigquery(config)
                if bq_result['success']:
                    result['steps_completed'].append('bigquery_dataset')
                else:
                    result['errors'].append(f"BigQuery: {bq_result['error']}")
            
            # Step 3: Create client directory and config
            config_result = self._create_client_config(config, result.get('credentials', {}))
            if config_result['success']:
                result['steps_completed'].append('client_config')
                result['config_path'] = config_result['path']
            else:
                result['errors'].append(f"Config: {config_result['error']}")
            
            # Step 4: Create prompt templates
            prompts_result = self._create_prompt_templates(config)
            if prompts_result['success']:
                result['steps_completed'].append('prompt_templates')
            
            # Determine overall success
            if result['errors']:
                result['success'] = len(result['steps_completed']) > 0  # Partial success
            
            logger.info(f"✅ Tenant provisioning completed for {client_id}: {result['steps_completed']}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Tenant provisioning failed: {e}")
            result['success'] = False
            result['errors'].append(str(e))
            return result
    
    def _provision_sendgrid(
        self,
        config: Dict[str, Any],
        setup_domain: bool = False
    ) -> Dict[str, Any]:
        """Provision SendGrid resources"""
        client_id = config['client_id']
        
        # Create subuser
        subuser_result = self.sendgrid.create_subuser(
            username=client_id,
            email=config['contact_email']
        )
        
        if not subuser_result['success']:
            return subuser_result
        
        # Create API key for subuser
        api_key_result = self.sendgrid.create_api_key(
            name=f"{client_id}-mail-api-key",
            subuser=client_id
        )
        
        if not api_key_result['success']:
            return api_key_result
        
        # Create verified sender
        sender_result = self.sendgrid.add_verified_sender(
            from_email=config['from_email'],
            from_name=config.get('from_name', config['company_name']),
            reply_to=config.get('reply_to', config['from_email']),
            nickname=config['company_name'],
            address=config.get('address', '123 Main St'),
            city=config.get('city', 'New York'),
            country=config.get('country', 'USA'),
            subuser=client_id
        )
        
        result = {
            'success': True,
            'credentials': {
                'subuser': client_id,
                'api_key': api_key_result['data']['api_key'],
                'api_key_id': api_key_result['data']['api_key_id']
            }
        }
        
        # Assign IP to subuser (required for sending)
        ip_result = self.sendgrid.assign_ip_to_subuser(client_id)
        if ip_result['success']:
            result['credentials']['ip_address'] = ip_result['ip']
            logger.info(f"IP {ip_result['ip']} assigned to {client_id}")
        else:
            logger.warning(f"IP assignment failed: {ip_result.get('error')}")
        
        # Setup domain authentication if requested
        if setup_domain and config.get('domain'):
            domain_result = self.sendgrid.setup_domain_authentication(
                domain=config['domain'],
                subuser=client_id
            )
            if domain_result['success']:
                result['dns_records'] = domain_result['data'].get('dns', [])
        
        return result
    
    def _provision_bigquery(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create BigQuery dataset for tenant"""
        try:
            client = bigquery.Client(project=self.gcp_project)
            dataset_id = f"{self.gcp_project}.{config['client_id']}_analytics"
            
            dataset = bigquery.Dataset(dataset_id)
            dataset.location = config.get('gcp_region', 'US')
            dataset.description = f"Analytics dataset for {config['company_name']}"
            
            dataset = client.create_dataset(dataset, exists_ok=True)
            
            logger.info(f"✅ BigQuery dataset created: {dataset_id}")
            return {'success': True, 'dataset_id': dataset_id}
            
        except Exception as e:
            logger.error(f"❌ BigQuery dataset creation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _create_client_config(
        self,
        config: Dict[str, Any],
        credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate client.yaml configuration file"""
        try:
            client_id = config['client_id']
            client_dir = self.base_path / "clients" / client_id
            client_dir.mkdir(parents=True, exist_ok=True)
            
            # Build destinations list
            destinations = []
            for dest in config.get('destinations', ['Bali', 'Maldives']):
                code = re.sub(r'[^A-Z]', '', dest.upper())[:4]
                destinations.append({
                    'name': dest,
                    'code': code,
                    'enabled': True
                })
            
            # Build config structure
            yaml_config = {
                'client': {
                    'id': client_id,
                    'name': config['company_name'],
                    'short_name': config.get('short_name', client_id.replace('_', '')),
                    'timezone': config.get('timezone', 'UTC'),
                    'currency': config.get('currency', 'USD')
                },
                'branding': {
                    'company_name': config['company_name'],
                    'logo_url': config.get('logo_url', ''),
                    'primary_color': config.get('primary_color', '#FF6B6B'),
                    'secondary_color': config.get('secondary_color', '#4ECDC4'),
                    'email_signature': config.get('email_signature', f"Best regards,\nThe {config['company_name']} Team")
                },
                'destinations': destinations,
                'infrastructure': {
                    'gcp': {
                        'project_id': config.get('gcp_project_id', '${GCP_PROJECT_ID}'),
                        'region': config.get('gcp_region', 'us-central1'),
                        'dataset': f"{client_id}_analytics",
                        'corpus_id': ''
                    },
                    'supabase': {
                        'url': config.get('supabase_url', '${SUPABASE_URL}'),
                        'anon_key': config.get('supabase_anon_key', '${SUPABASE_ANON_KEY}'),
                        'service_key': f'${{{client_id.upper()}_SUPABASE_SERVICE_KEY}}'
                    },
                    'vapi': {
                        'api_key': f'${{{client_id.upper()}_VAPI_API_KEY}}',
                        'phone_number_id': config.get('vapi_phone_id', ''),
                        'assistant_id': config.get('vapi_assistant_id', '')
                    },
                    'openai': {
                        'api_key': '${OPENAI_API_KEY}',
                        'model': 'gpt-4o-mini'
                    }
                },
                'email': {
                    'primary': config['from_email'],
                    'sendgrid': {
                        'api_key': f'${{{client_id.upper()}_SENDGRID_API_KEY}}',
                        'from_email': config['from_email'],
                        'from_name': config.get('from_name', config['company_name']),
                        'reply_to': config.get('reply_to', config['from_email'])
                    },
                    'smtp': {
                        'host': config.get('smtp_host', 'smtp.sendgrid.net'),
                        'port': config.get('smtp_port', 465),
                        'username': 'apikey',
                        'password': f'${{{client_id.upper()}_SENDGRID_API_KEY}}'
                    },
                    'imap': {
                        'host': config.get('imap_host', f'imap.{config.get("domain", "example.com")}'),
                        'port': 993
                    }
                },
                'consultants': config.get('consultants', [
                    {'id': 'consultant_1', 'name': 'Default Consultant', 'email': config['contact_email'], 'active': True}
                ]),
                'agents': {
                    'inbound': {'enabled': True, 'prompt_file': 'prompts/inbound.txt'},
                    'helpdesk': {'enabled': True, 'prompt_file': 'prompts/helpdesk.txt'},
                    'outbound': {'enabled': True, 'prompt_file': 'prompts/outbound.txt'}
                }
            }
            
            # Write YAML file
            config_path = client_dir / "client.yaml"
            with open(config_path, 'w') as f:
                yaml.dump(yaml_config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
            
            # Create .env.example with required variables
            env_example = f"""# Environment variables for {config['company_name']}
# Copy to .env and fill in actual values

# SendGrid (from provisioning)
{client_id.upper()}_SENDGRID_API_KEY={credentials.get('sendgrid', {}).get('api_key', 'SG.xxx')}

# Supabase
{client_id.upper()}_SUPABASE_SERVICE_KEY=your-supabase-service-key

# VAPI (if using voice)
{client_id.upper()}_VAPI_API_KEY=your-vapi-key

# OpenAI (shared or per-tenant)
OPENAI_API_KEY=sk-xxx
"""
            env_path = client_dir / ".env.example"
            with open(env_path, 'w') as f:
                f.write(env_example)
            
            logger.info(f"✅ Client config created: {config_path}")
            return {'success': True, 'path': str(config_path)}
            
        except Exception as e:
            logger.error(f"❌ Config creation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _create_prompt_templates(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create AI prompt templates for tenant"""
        try:
            client_id = config['client_id']
            company_name = config['company_name']
            prompts_dir = self.base_path / "clients" / client_id / "prompts"
            prompts_dir.mkdir(parents=True, exist_ok=True)
            
            destinations = ', '.join(config.get('destinations', ['various destinations']))
            
            # Inbound agent prompt
            inbound_prompt = f"""You are a friendly travel assistant for {company_name}.

Your role is to help customers with:
- Travel inquiries about {destinations}
- Quote requests
- Booking information
- General travel questions

Be warm, professional, and helpful. Collect the following information for quote requests:
- Destination
- Travel dates
- Number of adults and children
- Budget (if they're willing to share)
- Any special requirements

Company: {company_name}
"""
            
            # Helpdesk prompt
            helpdesk_prompt = f"""You are an internal helpdesk assistant for {company_name}.

Your role is to help employees with:
- Hotel information and policies
- Booking procedures
- Pricing and rates
- Destination information
- Company policies

Be professional, accurate, and helpful. If you don't know something, say so.

Company: {company_name}
Available destinations: {destinations}
"""
            
            # Outbound prompt
            outbound_prompt = f"""You are Nala, a friendly travel consultant calling on behalf of {company_name}.

You are making a follow-up call about a travel quote the customer received.

Goals:
1. Confirm they received the quote
2. Answer any questions they have
3. Help them decide on a hotel option
4. Offer to proceed with booking if they're ready

Be warm, conversational, and not pushy. Listen to their concerns.

Company: {company_name}
"""
            
            # Write prompts
            (prompts_dir / "inbound.txt").write_text(inbound_prompt)
            (prompts_dir / "helpdesk.txt").write_text(helpdesk_prompt)
            (prompts_dir / "outbound.txt").write_text(outbound_prompt)
            
            logger.info(f"✅ Prompt templates created for {client_id}")
            return {'success': True}
            
        except Exception as e:
            logger.error(f"❌ Prompt creation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def deprovision_tenant(self, client_id: str) -> Dict[str, Any]:
        """
        Remove a tenant and clean up resources
        
        WARNING: This is destructive!
        
        Args:
            client_id: Tenant to remove
            
        Returns:
            Deprovisioning result
        """
        result = {
            'success': True,
            'steps_completed': [],
            'errors': []
        }
        
        # TODO: Implement SendGrid subuser deletion
        # TODO: Implement BigQuery dataset deletion (with confirmation)
        # TODO: Remove client directory
        
        logger.warning(f"⚠️ Tenant deprovisioning not fully implemented for {client_id}")
        return result


# ==================== API Endpoints ====================

def create_provisioning_routes():
    """Create FastAPI routes for provisioning"""
    from fastapi import APIRouter, HTTPException, Depends, Header
    from pydantic import BaseModel, EmailStr
    from typing import List
    
    router = APIRouter(prefix="/api/v1/admin/tenants", tags=["Admin - Tenant Provisioning"])
    
    class TenantCreateRequest(BaseModel):
        client_id: str
        company_name: str
        contact_email: EmailStr
        from_email: EmailStr
        from_name: str
        domain: str
        timezone: str = "UTC"
        currency: str = "USD"
        destinations: List[str] = ["Bali", "Maldives"]
        primary_color: str = "#FF6B6B"
        secondary_color: str = "#4ECDC4"
        address: str = "123 Main St"
        city: str = "New York"
        country: str = "USA"
        create_sendgrid: bool = True
        setup_domain_auth: bool = False
    
    @router.post("/provision")
    async def provision_tenant(
        request: TenantCreateRequest,
        admin_key: str = Header(..., alias="X-Admin-Key")
    ):
        """
        Provision a new tenant
        
        Requires X-Admin-Key header for authentication.
        """
        # Verify admin key
        expected_key = os.getenv("ADMIN_API_KEY")
        if not expected_key or admin_key != expected_key:
            raise HTTPException(status_code=401, detail="Invalid admin key")
        
        provisioner = TenantProvisioningService()
        
        result = provisioner.provision_tenant(
            config=request.model_dump(),
            create_sendgrid_subuser=request.create_sendgrid,
            setup_domain_auth=request.setup_domain_auth
        )
        
        if not result['success'] and not result['steps_completed']:
            raise HTTPException(status_code=500, detail=result['errors'])
        
        return result
    
    @router.get("/{client_id}")
    async def get_tenant_status(
        client_id: str,
        admin_key: str = Header(..., alias="X-Admin-Key")
    ):
        """Get tenant provisioning status"""
        expected_key = os.getenv("ADMIN_API_KEY")
        if not expected_key or admin_key != expected_key:
            raise HTTPException(status_code=401, detail="Invalid admin key")
        
        # Check if client exists
        from config.loader import ClientConfig
        try:
            config = ClientConfig(client_id)
            return {
                "exists": True,
                "client_id": client_id,
                "company_name": config.company_name,
                "destinations": config.destination_names
            }
        except FileNotFoundError:
            return {"exists": False, "client_id": client_id}
    
    return router
