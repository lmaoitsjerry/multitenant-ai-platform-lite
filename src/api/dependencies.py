"""
Shared FastAPI Dependencies

Common dependency functions used across multiple route modules.
Consolidates the get_client_config pattern that was duplicated 12+ times.
"""

import os
import logging
from typing import Optional
from fastapi import Header, HTTPException
from config.loader import ClientConfig

logger = logging.getLogger(__name__)

_client_configs: dict[str, ClientConfig] = {}


class FallbackClientConfig:
    """
    Fallback configuration when tenant is not found in database.

    Used for development/demo scenarios. Provides minimal config
    using environment variables for shared infrastructure.
    """

    def __init__(self, client_id: str):
        self.client_id = client_id
        self._config_source = 'fallback'

        # Build config from environment variables
        self.config = {
            'client': {
                'id': client_id,
                'name': client_id.title().replace('_', ' ').replace('-', ' '),
                'short_name': client_id,
                'timezone': os.getenv('DEFAULT_TIMEZONE', 'Africa/Johannesburg'),
                'currency': os.getenv('DEFAULT_CURRENCY', 'ZAR'),
            },
            'branding': {
                'company_name': client_id.title().replace('_', ' ').replace('-', ' '),
                'primary_color': '#2E86AB',
                'secondary_color': '#4ECDC4',
                'email_signature': f'Best regards,\nThe {client_id.title()} Team',
            },
            'destinations': [],
            'infrastructure': {
                'gcp': {
                    'project_id': os.getenv('GCP_PROJECT_ID', ''),
                    'region': 'us-central1',
                    'dataset': os.getenv('GCP_DATASET', client_id),
                    'shared_pricing_dataset': 'africastay_analytics',
                },
                'supabase': {
                    'url': os.getenv('SUPABASE_URL', ''),
                    'anon_key': os.getenv('SUPABASE_ANON_KEY', ''),
                    'service_key': os.getenv('SUPABASE_SERVICE_KEY', ''),
                },
                'openai': {
                    'api_key': os.getenv('OPENAI_API_KEY', ''),
                    'model': 'gpt-4o-mini',
                },
                'vapi': {
                    'api_key': os.getenv('VAPI_API_KEY', ''),
                },
            },
            'email': {
                'primary': os.getenv('DEFAULT_EMAIL', ''),
                'sendgrid': {
                    'api_key': os.getenv('SENDGRID_MASTER_API_KEY', ''),
                    'from_email': os.getenv('SENDGRID_FROM_EMAIL', ''),
                    'from_name': os.getenv('SENDGRID_FROM_NAME', client_id.title()),
                },
                'smtp': {},
                'imap': {},
            },
            'banking': {},
            'consultants': [],
            'agents': {
                'inbound': {'enabled': True},
                'helpdesk': {'enabled': True},
                'outbound': {'enabled': False},
            },
            '_meta': {
                'source': 'fallback',
                'status': 'active',
                'plan': 'lite',
            },
        }

        logger.warning(
            f"Using fallback config for tenant '{client_id}'. "
            f"Add tenant to database for full functionality."
        )

    @property
    def config_source(self) -> str:
        return self._config_source

    @property
    def name(self) -> str:
        return self.config['client']['name']

    @property
    def short_name(self) -> str:
        return self.config['client']['short_name']

    @property
    def timezone(self) -> str:
        return self.config['client']['timezone']

    @property
    def currency(self) -> str:
        return self.config['client'].get('currency', 'USD')

    @property
    def company_name(self) -> str:
        return self.config.get('branding', {}).get('company_name', self.name)

    @property
    def logo_url(self) -> Optional[str]:
        return self.config.get('branding', {}).get('logo_url')

    @property
    def primary_color(self) -> str:
        return self.config.get('branding', {}).get('primary_color', '#2E86AB')

    @property
    def secondary_color(self) -> str:
        return self.config.get('branding', {}).get('secondary_color', '#4ECDC4')

    @property
    def email_signature(self) -> str:
        return self.config.get('branding', {}).get('email_signature', '')

    @property
    def support_phone(self) -> Optional[str]:
        return None

    @property
    def website(self) -> Optional[str]:
        return None

    @property
    def fax_number(self) -> Optional[str]:
        return None

    @property
    def destinations(self):
        return self.config.get('destinations', [])

    @property
    def destination_names(self):
        return [d['name'] for d in self.destinations]

    @property
    def destination_codes(self):
        return [d['code'] for d in self.destinations]

    @property
    def gcp_project_id(self) -> str:
        return self.config['infrastructure']['gcp']['project_id']

    @property
    def gcp_region(self) -> str:
        return self.config['infrastructure']['gcp'].get('region', 'us-central1')

    @property
    def dataset_name(self) -> str:
        return self.config['infrastructure']['gcp']['dataset']

    @property
    def shared_pricing_dataset(self) -> str:
        return self.config['infrastructure']['gcp'].get('shared_pricing_dataset', 'africastay_analytics')

    @property
    def corpus_id(self) -> Optional[str]:
        return None

    @property
    def supabase_url(self) -> str:
        return self.config['infrastructure']['supabase']['url']

    @property
    def supabase_anon_key(self) -> str:
        return self.config['infrastructure']['supabase']['anon_key']

    @property
    def supabase_service_key(self) -> Optional[str]:
        return self.config['infrastructure']['supabase'].get('service_key')

    @property
    def vapi_api_key(self) -> Optional[str]:
        return self.config['infrastructure'].get('vapi', {}).get('api_key')

    @property
    def vapi_phone_number_id(self) -> Optional[str]:
        return None

    @property
    def vapi_assistant_id(self) -> Optional[str]:
        return None

    @property
    def vapi_outbound_assistant_id(self) -> Optional[str]:
        return None

    @property
    def openai_api_key(self) -> str:
        return self.config['infrastructure']['openai']['api_key']

    @property
    def openai_model(self) -> str:
        return self.config['infrastructure']['openai'].get('model', 'gpt-4o-mini')

    @property
    def primary_email(self) -> str:
        return self.config['email']['primary']

    @property
    def smtp_host(self) -> str:
        return ''

    @property
    def smtp_port(self) -> int:
        return 465

    @property
    def smtp_username(self) -> str:
        return ''

    @property
    def smtp_password(self) -> Optional[str]:
        return None

    @property
    def imap_host(self) -> str:
        return ''

    @property
    def imap_port(self) -> int:
        return 993

    @property
    def sendgrid_api_key(self) -> Optional[str]:
        return self.config.get('email', {}).get('sendgrid', {}).get('api_key')

    @property
    def sendgrid_from_email(self) -> Optional[str]:
        return self.config.get('email', {}).get('sendgrid', {}).get('from_email')

    @property
    def sendgrid_from_name(self) -> Optional[str]:
        return self.config.get('email', {}).get('sendgrid', {}).get('from_name')

    @property
    def sendgrid_reply_to(self) -> Optional[str]:
        return self.config.get('email', {}).get('sendgrid', {}).get('reply_to')

    @property
    def banking(self):
        return self.config.get('banking', {})

    @property
    def bank_name(self) -> Optional[str]:
        return None

    @property
    def bank_account_name(self) -> Optional[str]:
        return None

    @property
    def bank_account_number(self) -> Optional[str]:
        return None

    @property
    def bank_branch_code(self) -> Optional[str]:
        return None

    @property
    def bank_swift_code(self) -> Optional[str]:
        return None

    @property
    def payment_reference_prefix(self) -> str:
        return self.short_name.upper()[:3]

    @property
    def consultants(self):
        return []

    def get_agent_config(self, agent_type: str):
        return self.config.get('agents', {}).get(agent_type, {'enabled': True})

    def is_agent_enabled(self, agent_type: str) -> bool:
        return self.get_agent_config(agent_type).get('enabled', True)

    def get_table_name(self, table: str) -> str:
        return f"{self.gcp_project_id}.{self.dataset_name}.{table}"

    def to_dict(self):
        return self.config.copy()

    def __repr__(self) -> str:
        return f"FallbackClientConfig(client_id='{self.client_id}')"


def get_client_config(x_client_id: Optional[str] = Header(None, alias="X-Client-ID")) -> ClientConfig:
    """Get client configuration from X-Client-ID header with caching.

    Resolves the tenant from the X-Client-ID header (or CLIENT_ID env var fallback),
    loads the ClientConfig, and caches it for subsequent requests.

    If tenant is not found in database OR config loading fails for any reason,
    returns a FallbackClientConfig that uses environment variables for shared
    infrastructure. This ensures the app always works, even during database
    connectivity issues.
    """
    client_id = x_client_id or os.getenv("CLIENT_ID", "example")

    if client_id not in _client_configs:
        try:
            _client_configs[client_id] = ClientConfig(client_id)
            logger.info(f"Loaded configuration for client: {client_id}")
        except FileNotFoundError:
            logger.warning(f"Tenant '{client_id}' not found in database, using fallback config")
            _client_configs[client_id] = FallbackClientConfig(client_id)
        except Exception as e:
            # Config loading failed (DB connectivity, import error, etc.)
            # Use fallback instead of crashing - the app should always work
            logger.error(f"Failed to load config for {client_id}: {e}, using fallback config")
            _client_configs[client_id] = FallbackClientConfig(client_id)

    return _client_configs[client_id]
