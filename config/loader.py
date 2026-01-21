"""
Configuration Loader - Loads and validates client configuration

Usage:
    from config.loader import ClientConfig

    config = ClientConfig('africastay')
    print(config.gcp_project_id)
    print(config.destinations)

Now supports dual-mode operation via TenantConfigService:
1. Database-first (for migrated tenants)
2. YAML fallback (for backward compatibility)
"""

import yaml
import json
import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from jsonschema import validate, ValidationError

logger = logging.getLogger(__name__)

# Lazy imports to avoid circular dependency with services
_tenant_config_service_module = None


def _get_tenant_config_service_module():
    """Lazy import of tenant_config_service to avoid circular imports"""
    global _tenant_config_service_module
    if _tenant_config_service_module is None:
        from src.services import tenant_config_service
        _tenant_config_service_module = tenant_config_service
    return _tenant_config_service_module


def get_config_service():
    """Get TenantConfigService singleton"""
    return _get_tenant_config_service_module().get_service()


def reset_config_service():
    """Reset TenantConfigService singleton"""
    module = _get_tenant_config_service_module()
    if module:
        module.reset_service()


class ClientConfig:
    """Load and validate client configuration from YAML or database"""

    def __init__(self, client_id: str, base_path: Optional[str] = None):
        """
        Initialize client configuration

        Args:
            client_id: Unique client identifier (e.g., 'africastay')
            base_path: Base directory path (defaults to project root)
        """
        self.client_id = client_id

        if base_path is None:
            # Default to project root
            base_path = Path(__file__).parent.parent

        self.base_path = Path(base_path)
        self.config_path = self.base_path / "clients" / client_id / "client.yaml"
        self.schema_path = self.base_path / "config" / "schema.json"
        self._config_source = 'yaml'  # Default

        # Try TenantConfigService first (database + YAML fallback)
        try:
            service = get_config_service()
            config = service.get_config(client_id)
            if config:
                self.config = config
                self._config_source = config.get('_meta', {}).get('source', 'service')
                # Skip validation for database configs (validated on save)
                if self._config_source != 'database':
                    self._validate_config()
                return
        except Exception as e:
            logger.debug(f"TenantConfigService unavailable: {e}")

        # Direct YAML fallback (original behavior)
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        self.config = self._load_config()
        self._config_source = 'yaml'
        self._validate_config()

    @property
    def config_source(self) -> str:
        """Source of configuration: 'database', 'yaml', or 'service'"""
        return self._config_source

    def _load_config(self) -> Dict[str, Any]:
        """Load YAML configuration file"""
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Substitute environment variables
        config = self._substitute_env_vars(config)

        return config

    def _substitute_env_vars(self, obj: Any) -> Any:
        """
        Recursively substitute environment variables in config

        Supports: ${VAR_NAME} or ${VAR_NAME:-default_value}
        """
        if isinstance(obj, dict):
            return {k: self._substitute_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            # Match ${VAR} or ${VAR:-default}
            pattern = r'\$\{([A-Z_]+)(?::-([^}]+))?\}'

            def replacer(match):
                var_name = match.group(1)
                default = match.group(2)
                return os.getenv(var_name, default or '')

            return re.sub(pattern, replacer, obj)
        else:
            return obj

    def _validate_config(self):
        """Validate configuration against JSON schema"""
        if not self.schema_path.exists():
            logger.warning(f"Schema file not found: {self.schema_path}, skipping validation")
            return

        with open(self.schema_path, 'r') as f:
            schema = json.load(f)

        try:
            validate(instance=self.config, schema=schema)
        except ValidationError as e:
            raise ValueError(f"Configuration validation failed: {e.message}")

    # ==================== Client Properties ====================

    @property
    def name(self) -> str:
        """Full company name"""
        return self.config['client']['name']

    @property
    def short_name(self) -> str:
        """Short name (lowercase, no spaces)"""
        return self.config['client']['short_name']

    @property
    def timezone(self) -> str:
        """IANA timezone"""
        return self.config['client']['timezone']

    @property
    def currency(self) -> str:
        """ISO currency code"""
        return self.config['client'].get('currency', 'USD')

    # ==================== Branding Properties ====================

    @property
    def company_name(self) -> str:
        """Brand company name"""
        return self.config.get('branding', {}).get('company_name', self.name)

    @property
    def logo_url(self) -> Optional[str]:
        """Brand logo URL"""
        return self.config.get('branding', {}).get('logo_url')

    @property
    def primary_color(self) -> str:
        """Brand primary color (hex)"""
        return self.config.get('branding', {}).get('primary_color', '#FF6B6B')

    @property
    def secondary_color(self) -> str:
        """Brand secondary color (hex)"""
        return self.config.get('branding', {}).get('secondary_color', '#4ECDC4')

    @property
    def email_signature(self) -> str:
        """Brand email signature"""
        return self.config.get('branding', {}).get('email_signature', f'Best regards,\nThe {self.company_name} Team')

    @property
    def support_phone(self) -> Optional[str]:
        """Support phone number"""
        return self.config.get('branding', {}).get('phone') or self.config.get('company', {}).get('phone')

    @property
    def website(self) -> Optional[str]:
        """Company website URL"""
        return self.config.get('branding', {}).get('website') or self.config.get('company', {}).get('website')

    @property
    def fax_number(self) -> Optional[str]:
        """Fax number"""
        return self.config.get('branding', {}).get('fax') or self.config.get('company', {}).get('fax')

    # ==================== Destination Properties ====================

    @property
    def destinations(self) -> List[Dict[str, Any]]:
        """List of enabled destinations"""
        all_dests = self.config.get('destinations', [])
        return [d for d in all_dests if d.get('enabled', True)]

    @property
    def destination_names(self) -> List[str]:
        """List of destination names"""
        return [d['name'] for d in self.destinations]

    @property
    def destination_codes(self) -> List[str]:
        """List of destination codes"""
        return [d['code'] for d in self.destinations]

    def get_destination_search_terms(self, destination: str) -> List[str]:
        """
        Get all search terms for a destination (name + aliases)

        Args:
            destination: Destination name to expand

        Returns:
            List of destination names to search for
        """
        search_terms = [destination]
        for dest in self.destinations:
            if dest['name'].lower() == destination.lower():
                # Add the canonical name
                search_terms = [dest['name']]
                # Add any aliases from config
                aliases = dest.get('aliases', [])
                search_terms.extend(aliases)
                break
        return search_terms

    # ==================== Infrastructure Properties ====================

    @property
    def gcp_project_id(self) -> str:
        """GCP project ID"""
        return self.config['infrastructure']['gcp']['project_id']

    @property
    def gcp_region(self) -> str:
        """GCP region"""
        return self.config['infrastructure']['gcp'].get('region', 'us-central1')

    @property
    def dataset_name(self) -> str:
        """BigQuery dataset name (tenant-specific for quotes, analytics)"""
        return self.config['infrastructure']['gcp']['dataset']

    @property
    def shared_pricing_dataset(self) -> str:
        """
        Shared BigQuery dataset for pricing data (hotel_rates, flight_prices).
        All tenants use the same pricing dataset.
        Defaults to 'africastay_analytics' if not specified.
        """
        return self.config['infrastructure']['gcp'].get('shared_pricing_dataset', 'africastay_analytics')

    @property
    def corpus_id(self) -> Optional[str]:
        """Vertex AI RAG corpus ID"""
        return self.config['infrastructure']['gcp'].get('corpus_id')

    @property
    def supabase_url(self) -> str:
        """Supabase project URL"""
        return self.config['infrastructure']['supabase']['url']

    @property
    def supabase_anon_key(self) -> str:
        """Supabase anon key"""
        return self.config['infrastructure']['supabase']['anon_key']

    @property
    def supabase_service_key(self) -> Optional[str]:
        """Supabase service role key"""
        return self.config['infrastructure']['supabase'].get('service_key')

    # ==================== VAPI Properties ====================

    @property
    def vapi_api_key(self) -> Optional[str]:
        """VAPI API key"""
        return self.config['infrastructure'].get('vapi', {}).get('api_key')

    @property
    def vapi_phone_number_id(self) -> Optional[str]:
        """VAPI phone number ID"""
        return self.config['infrastructure'].get('vapi', {}).get('phone_number_id')

    @property
    def vapi_assistant_id(self) -> Optional[str]:
        """VAPI assistant ID (inbound)"""
        return self.config['infrastructure'].get('vapi', {}).get('assistant_id')

    @property
    def vapi_outbound_assistant_id(self) -> Optional[str]:
        """VAPI outbound assistant ID"""
        return self.config['infrastructure'].get('vapi', {}).get('outbound_assistant_id')

    # ==================== OpenAI Properties ====================

    @property
    def openai_api_key(self) -> str:
        """OpenAI API key"""
        return self.config['infrastructure']['openai']['api_key']

    @property
    def openai_model(self) -> str:
        """OpenAI model name"""
        return self.config['infrastructure']['openai'].get('model', 'gpt-4o-mini')

    # ==================== Email Properties ====================

    @property
    def primary_email(self) -> str:
        """Primary email address"""
        return self.config['email']['primary']

    @property
    def smtp_host(self) -> str:
        """SMTP server host"""
        return self.config['email'].get('smtp', {}).get('host', '')

    @property
    def smtp_port(self) -> int:
        """SMTP server port"""
        return self.config['email'].get('smtp', {}).get('port', 465)

    @property
    def smtp_username(self) -> str:
        """SMTP username"""
        return self.config['email'].get('smtp', {}).get('username', '')

    @property
    def smtp_password(self) -> Optional[str]:
        """SMTP password"""
        return self.config['email'].get('smtp', {}).get('password')

    @property
    def imap_host(self) -> str:
        """IMAP server host"""
        return self.config['email'].get('imap', {}).get('host', '')

    @property
    def imap_port(self) -> int:
        """IMAP server port"""
        return self.config['email'].get('imap', {}).get('port', 993)

    # ==================== SendGrid Properties ====================

    @property
    def sendgrid_api_key(self) -> Optional[str]:
        """SendGrid API key (per-tenant)"""
        return self.config.get('email', {}).get('sendgrid', {}).get('api_key')

    @property
    def sendgrid_from_email(self) -> Optional[str]:
        """SendGrid verified sender email"""
        return self.config.get('email', {}).get('sendgrid', {}).get('from_email')

    @property
    def sendgrid_from_name(self) -> Optional[str]:
        """SendGrid sender display name"""
        return self.config.get('email', {}).get('sendgrid', {}).get('from_name')

    @property
    def sendgrid_reply_to(self) -> Optional[str]:
        """SendGrid reply-to address"""
        return self.config.get('email', {}).get('sendgrid', {}).get('reply_to')

    # ==================== Banking Properties (for invoices) ====================

    @property
    def banking(self) -> Dict[str, Any]:
        """Banking details for invoices"""
        return self.config.get('banking', {})

    @property
    def bank_name(self) -> Optional[str]:
        """Bank name"""
        return self.banking.get('bank_name')

    @property
    def bank_account_name(self) -> Optional[str]:
        """Bank account name"""
        return self.banking.get('account_name')

    @property
    def bank_account_number(self) -> Optional[str]:
        """Bank account number"""
        return self.banking.get('account_number')

    @property
    def bank_branch_code(self) -> Optional[str]:
        """Bank branch code"""
        return self.banking.get('branch_code')

    @property
    def bank_swift_code(self) -> Optional[str]:
        """Bank SWIFT code for international transfers"""
        return self.banking.get('swift_code')

    @property
    def payment_reference_prefix(self) -> str:
        """Prefix for payment references"""
        return self.banking.get('reference_prefix', self.short_name.upper()[:3])

    # ==================== Consultant Properties ====================

    @property
    def consultants(self) -> List[Dict[str, Any]]:
        """List of active consultants"""
        all_consultants = self.config.get('consultants', [])
        return [c for c in all_consultants if c.get('active', True)]

    # ==================== Agent Properties ====================

    def get_agent_config(self, agent_type: str) -> Dict[str, Any]:
        """
        Get configuration for specific agent type

        Args:
            agent_type: 'inbound', 'helpdesk', or 'outbound'

        Returns:
            Agent configuration dict
        """
        return self.config.get('agents', {}).get(agent_type, {'enabled': True})

    def is_agent_enabled(self, agent_type: str) -> bool:
        """Check if agent is enabled"""
        return self.get_agent_config(agent_type).get('enabled', True)

    def get_prompt_path(self, agent_type: str) -> Path:
        """Get path to agent prompt file"""
        agent_config = self.get_agent_config(agent_type)
        prompt_file = agent_config.get('prompt_file', f'prompts/{agent_type}.txt')
        return self.base_path / "clients" / self.client_id / prompt_file

    # ==================== Helper Methods ====================

    def get_table_name(self, table: str) -> str:
        """
        Get fully qualified BigQuery table name

        Args:
            table: Table name (e.g., 'hotel_rates')

        Returns:
            Fully qualified name (e.g., 'project.dataset.table')
        """
        return f"{self.gcp_project_id}.{self.dataset_name}.{table}"

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        return self.config.copy()

    def __repr__(self) -> str:
        return f"ClientConfig(client_id='{self.client_id}', name='{self.name}')"


# Singleton pattern for easy access
_config_cache = {}


def clear_config_cache(client_id: str = None):
    """
    Clear the config cache.

    Args:
        client_id: If provided, only clear cache for this client.
                   If None, clear entire cache.
    """
    global _config_cache
    if client_id:
        _config_cache.pop(client_id, None)
    else:
        _config_cache = {}

    # Also reset TenantConfigService instance to force refresh
    reset_config_service()


def get_config(client_id: str) -> ClientConfig:
    """
    Get or create client configuration (cached)

    Args:
        client_id: Client identifier

    Returns:
        ClientConfig instance
    """
    if client_id not in _config_cache:
        _config_cache[client_id] = ClientConfig(client_id)
    return _config_cache[client_id]


def list_clients() -> List[str]:
    """
    List all available client IDs from database and filesystem.

    Uses TenantConfigService which combines database tenants with
    YAML-only tenants, and filters out tn_* auto-generated test tenants.

    Returns:
        List of client IDs
    """
    try:
        service = get_config_service()
        return service.list_tenants()
    except Exception as e:
        logger.warning(f"TenantConfigService unavailable, falling back to filesystem: {e}")
        # Fallback to filesystem scan
        clients_dir = Path(__file__).parent.parent / "clients"

        if not clients_dir.exists():
            return []

        client_ids = []
        for client_dir in clients_dir.iterdir():
            if client_dir.is_dir():
                # Skip tn_* auto-generated test tenants
                if client_dir.name.startswith('tn_'):
                    continue
                config_file = client_dir / "client.yaml"
                if config_file.exists():
                    client_ids.append(client_dir.name)

        return sorted(client_ids)


def get_client_config(client_id: str) -> Optional[Dict[str, Any]]:
    """
    Get raw client configuration as dictionary.

    Args:
        client_id: Client identifier

    Returns:
        Configuration dictionary or None if not found
    """
    try:
        config = get_config(client_id)
        return config.to_dict()
    except FileNotFoundError:
        return None
