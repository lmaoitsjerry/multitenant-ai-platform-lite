"""
Tenant Configuration Service - Database-backed tenant configuration

Usage:
    from src.services.tenant_config_service import TenantConfigService, get_tenant_config

    service = TenantConfigService()
    config = service.get_config("tenant_id")  # Returns dict

    # Or use convenience function
    config = get_tenant_config("tenant_id")

Features:
    - Database-first configuration (Supabase tenants table)
    - Uses shared infrastructure from environment variables
    - Redis caching with configurable TTL (5 minutes default)
    - Graceful fallback when Redis unavailable
    - Secret handling (resolved from env vars, not stored in DB)
"""

import os
import re
import json
import logging
import copy
from src.utils.error_handling import log_and_suppress
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def _substitute_env_vars(obj: Any) -> Any:
    """
    Recursively substitute environment variables in config values.

    Supports: ${VAR_NAME} or ${VAR_NAME:-default_value}
    """
    if isinstance(obj, dict):
        return {k: _substitute_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_substitute_env_vars(item) for item in obj]
    elif isinstance(obj, str):
        # Match ${VAR} or ${VAR:-default}
        pattern = r'\$\{([A-Z_][A-Z0-9_]*)(?::-([^}]+))?\}'

        def replacer(match):
            var_name = match.group(1)
            default = match.group(2)
            return os.getenv(var_name, default or '')

        return re.sub(pattern, replacer, obj)
    else:
        return obj


class TenantConfigService:
    """
    Tenant configuration service - Database as single source of truth.

    Configuration flow:
    1. Try Redis cache first (if available)
    2. Load from Supabase tenants table
    3. Build complete config using DB row + env var defaults

    Secrets are NEVER stored in database - resolved from env vars at runtime.
    """

    # Cache TTL in seconds (5 minutes)
    CACHE_TTL = 300

    # Cache key prefix
    CACHE_PREFIX = "tenant_config:"

    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path) if base_path else Path(__file__).parent.parent.parent
        self._supabase = None
        self._redis = None
        self._redis_available = None  # Lazy check - None means not checked yet

    def _get_supabase_client(self):
        """Get or create Supabase client (lazy initialization)"""
        if self._supabase is None:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

            if url and key:
                try:
                    from supabase import create_client
                    self._supabase = create_client(url, key)
                except Exception as e:
                    logger.warning(f"Could not create Supabase client: {e}")

        return self._supabase

    def _get_redis_client(self):
        """Get Redis client for caching (lazy initialization with fallback)"""
        if self._redis_available is False:
            return None

        if self._redis is None:
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                try:
                    import redis
                    self._redis = redis.from_url(redis_url)
                    self._redis.ping()
                    self._redis_available = True
                    logger.info("Redis cache connected for tenant config")
                except Exception as e:
                    logger.warning(f"Redis not available for tenant config cache: {e}")
                    self._redis_available = False
                    self._redis = None
            else:
                self._redis_available = False

        return self._redis

    def _cache_key(self, tenant_id: str) -> str:
        """Generate cache key for tenant"""
        return f"{self.CACHE_PREFIX}{tenant_id}"

    def _get_from_cache(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get tenant config from Redis cache"""
        redis_client = self._get_redis_client()
        if not redis_client:
            return None

        try:
            key = self._cache_key(tenant_id)
            data = redis_client.get(key)
            if data:
                logger.debug(f"Cache hit for tenant {tenant_id}")
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis cache read error: {e}")

        return None

    def _set_cache(self, tenant_id: str, config: Dict[str, Any]):
        """Store tenant config in Redis cache"""
        redis_client = self._get_redis_client()
        if not redis_client:
            return

        try:
            key = self._cache_key(tenant_id)
            # Don't cache secrets - they're resolved at runtime anyway
            redis_client.setex(key, self.CACHE_TTL, json.dumps(config))
            logger.debug(f"Cached config for tenant {tenant_id} (TTL: {self.CACHE_TTL}s)")
        except Exception as e:
            logger.warning(f"Redis cache write error: {e}")

    def _invalidate_cache(self, tenant_id: str):
        """Remove tenant config from cache"""
        redis_client = self._get_redis_client()
        if not redis_client:
            return

        try:
            key = self._cache_key(tenant_id)
            redis_client.delete(key)
            logger.debug(f"Invalidated cache for tenant {tenant_id}")
        except Exception as e:
            logger.warning(f"Redis cache delete error: {e}")

    def invalidate_all_cache(self):
        """Clear all tenant config cache entries"""
        redis_client = self._get_redis_client()
        if not redis_client:
            return

        try:
            # Find and delete all tenant config keys
            pattern = f"{self.CACHE_PREFIX}*"
            cursor = 0
            while True:
                cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
                if keys:
                    redis_client.delete(*keys)
                if cursor == 0:
                    break
            logger.info("Invalidated all tenant config cache")
        except Exception as e:
            logger.warning(f"Redis cache clear error: {e}")

    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cache status"""
        redis_client = self._get_redis_client()
        if not redis_client:
            return {
                'backend': 'none',
                'available': False,
                'ttl_seconds': self.CACHE_TTL,
            }

        try:
            # Count cached tenants
            pattern = f"{self.CACHE_PREFIX}*"
            cursor, keys = redis_client.scan(0, match=pattern, count=1000)
            count = len(keys)

            return {
                'backend': 'redis',
                'available': True,
                'ttl_seconds': self.CACHE_TTL,
                'cached_tenants': count,
            }
        except Exception:
            return {
                'backend': 'redis',
                'available': False,
                'ttl_seconds': self.CACHE_TTL,
            }

    def get_config(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get tenant configuration from database.

        Database is the single source of truth. Configuration is built from:
        1. Tenant row data (id, name, timezone, currency, etc.)
        2. tenant_config JSONB (branding, destinations, etc.)
        3. Shared infrastructure from environment variables

        Args:
            tenant_id: Tenant identifier

        Returns:
            Configuration dict or None if tenant not found
        """
        # Try cache first
        cached = self._get_from_cache(tenant_id)
        if cached:
            return cached

        # Load from database
        config = self._load_from_database(tenant_id)
        if config:
            self._set_cache(tenant_id, config)
            return config

        # Tenant not found in database
        logger.warning(f"Tenant {tenant_id} not found in database")
        return None

    def _load_from_database(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Load config from Supabase tenants table.

        Builds complete configuration from:
        - Database row columns (id, name, timezone, etc.)
        - tenant_config JSONB (branding, destinations, etc.)
        - Environment variables (API keys, Supabase URL, etc.)
        """
        client = self._get_supabase_client()
        if not client:
            logger.error("Supabase client not available - check SUPABASE_URL and SUPABASE_SERVICE_KEY")
            return None

        try:
            result = client.table("tenants").select("*").eq("id", tenant_id).single().execute()

            if not result.data:
                return None

            row = result.data

            # Get tenant_config JSONB (may be empty {} for new tenants)
            tenant_config = row.get('tenant_config', {}) or {}

            # Build complete configuration
            config = {
                'client': self._build_client_info(row, tenant_config),
                'branding': self._build_branding(row, tenant_config),
                'destinations': tenant_config.get('destinations', []),
                'infrastructure': self._build_infrastructure(row, tenant_config),
                'email': self._build_email_config(row, tenant_config),
                'banking': tenant_config.get('banking', {}),
                'consultants': tenant_config.get('consultants', []),
                'agents': tenant_config.get('agents', {}),
                'outbound': tenant_config.get('outbound', {}),
                'quotes': tenant_config.get('quotes', {}),
                'knowledge_base': tenant_config.get('knowledge_base', {}),
            }

            # Add metadata
            config['_meta'] = {
                'source': 'database',
                'status': row.get('status', 'active'),
                'plan': row.get('plan', 'lite'),
                'features_enabled': row.get('features_enabled', {}),
                'has_full_config': bool(tenant_config),  # True if tenant_config is not empty
            }

            logger.debug(f"Loaded tenant {tenant_id} from database (has_full_config: {config['_meta']['has_full_config']})")

            # Substitute any ${VAR} or ${VAR:-default} patterns in config values
            config = _substitute_env_vars(config)

            return config

        except Exception as e:
            # Don't log as error for "not found" cases (single() throws when no rows)
            if "0 rows" in str(e) or "No rows" in str(e):
                logger.debug(f"Tenant {tenant_id} not found in database")
            else:
                logger.error(f"Error loading tenant {tenant_id} from database: {e}")
            return None

    def _build_client_info(self, row: Dict, tenant_config: Dict) -> Dict[str, Any]:
        """Build client info section"""
        # Use row columns first, fall back to tenant_config, then defaults
        client_config = tenant_config.get('client', {})

        return {
            'id': row['id'],
            'name': row.get('name') or client_config.get('name', row['id']),
            'short_name': row.get('short_name') or client_config.get('short_name', row['id'][:20]),
            'timezone': row.get('timezone') or client_config.get('timezone', 'Africa/Johannesburg'),
            'currency': row.get('currency') or client_config.get('currency', 'ZAR'),
        }

    def _build_branding(self, row: Dict, tenant_config: Dict) -> Dict[str, Any]:
        """Build branding section with defaults"""
        branding = tenant_config.get('branding', {})
        tenant_name = row.get('name', row['id'])

        return {
            'company_name': branding.get('company_name', tenant_name),
            'logo_url': branding.get('logo_url'),
            'primary_color': branding.get('primary_color', '#2E86AB'),
            'secondary_color': branding.get('secondary_color', '#4ECDC4'),
            'accent_color': branding.get('accent_color'),
            'theme_id': branding.get('theme_id'),
            'email_signature': branding.get('email_signature', f'Best regards,\nThe {tenant_name} Team'),
        }

    def _build_infrastructure(self, row: Dict, tenant_config: Dict) -> Dict[str, Any]:
        """
        Build infrastructure config.

        Uses shared infrastructure from environment variables.
        Secrets are NEVER stored in database.
        """
        infra = tenant_config.get('infrastructure', {})
        tenant_id = row['id']
        tenant_env_key = tenant_id.upper().replace('-', '_').replace(' ', '_')

        # GCP config - use row columns, then tenant_config, then env vars
        gcp = infra.get('gcp', {}).copy() if infra.get('gcp') else {}
        gcp['project_id'] = row.get('gcp_project_id') or gcp.get('project_id') or os.getenv('GCP_PROJECT_ID', '')
        gcp['dataset'] = row.get('gcp_dataset') or gcp.get('dataset', '')
        gcp['region'] = gcp.get('region', 'us-central1')
        gcp['shared_pricing_dataset'] = gcp.get('shared_pricing_dataset', 'africastay_analytics')

        # Supabase - ALWAYS from environment variables (shared across all tenants)
        supabase = {
            'url': os.getenv('SUPABASE_URL', ''),
            'anon_key': os.getenv('SUPABASE_ANON_KEY', ''),
            'service_key': os.getenv('SUPABASE_SERVICE_KEY', ''),
        }

        # VAPI - try tenant-specific env var, fall back to shared
        vapi = infra.get('vapi', {}).copy() if infra.get('vapi') else {}
        vapi['api_key'] = os.getenv(f'{tenant_env_key}_VAPI_API_KEY') or os.getenv('VAPI_API_KEY', '')
        vapi['phone_number_id'] = vapi.get('phone_number_id', '')
        vapi['assistant_id'] = vapi.get('assistant_id', '')
        vapi['outbound_assistant_id'] = vapi.get('outbound_assistant_id', '')

        # OpenAI - shared API key from env
        openai = infra.get('openai', {}).copy() if infra.get('openai') else {}
        openai['api_key'] = os.getenv('OPENAI_API_KEY', '')
        openai['model'] = openai.get('model', 'gpt-4o-mini')

        return {
            'gcp': gcp,
            'supabase': supabase,
            'vapi': vapi,
            'openai': openai,
        }

    def _build_email_config(self, row: Dict, tenant_config: Dict) -> Dict[str, Any]:
        """
        Build email config.

        API keys and passwords from environment variables.
        """
        email = tenant_config.get('email', {}).copy() if tenant_config.get('email') else {}
        tenant_id = row['id']
        tenant_env_key = tenant_id.upper().replace('-', '_').replace(' ', '_')

        # Primary email from row or tenant_config
        email['primary'] = row.get('primary_email') or email.get('primary', '')

        # SendGrid - master key as fallback; per-tenant keys loaded from DB at runtime
        sendgrid = email.get('sendgrid', {}).copy() if email.get('sendgrid') else {}
        sendgrid['api_key'] = os.getenv('SENDGRID_MASTER_API_KEY', '')
        sendgrid['from_email'] = sendgrid.get('from_email', email.get('primary', ''))
        sendgrid['from_name'] = sendgrid.get('from_name', row.get('name', ''))
        sendgrid['reply_to'] = sendgrid.get('reply_to', email.get('primary', ''))
        email['sendgrid'] = sendgrid

        # SMTP - password from env
        smtp = email.get('smtp', {}).copy() if email.get('smtp') else {}
        smtp['password'] = os.getenv(f'{tenant_env_key}_SMTP_PASSWORD') or os.getenv('SMTP_PASSWORD', '')
        smtp['host'] = smtp.get('host', '')
        smtp['port'] = smtp.get('port', 465)
        smtp['username'] = smtp.get('username', '')
        email['smtp'] = smtp

        # IMAP config
        imap = email.get('imap', {}).copy() if email.get('imap') else {}
        imap['host'] = imap.get('host', '')
        imap['port'] = imap.get('port', 993)
        email['imap'] = imap

        return email

    def save_config(self, tenant_id: str, config: Dict[str, Any]) -> bool:
        """
        Save tenant configuration to database.

        Args:
            tenant_id: Tenant identifier
            config: Full configuration dict

        Returns:
            True if saved successfully
        """
        client = self._get_supabase_client()
        if not client:
            logger.error("Cannot save config: Supabase client not available")
            return False

        try:
            # Extract core fields for columns
            client_info = config.get('client', {})
            email_config = config.get('email', {})
            infra = config.get('infrastructure', {})

            row = {
                'id': tenant_id,
                'name': client_info.get('name', tenant_id),
                'short_name': client_info.get('short_name', ''),
                'timezone': client_info.get('timezone', 'Africa/Johannesburg'),
                'currency': client_info.get('currency', 'ZAR'),
                'primary_email': email_config.get('primary', ''),
                'gcp_project_id': infra.get('gcp', {}).get('project_id', ''),
                'gcp_dataset': infra.get('gcp', {}).get('dataset', ''),
                'config_source': 'database',
                'tenant_config': self._strip_secrets(config),
            }

            # Upsert (insert or update)
            client.table("tenants").upsert(row, on_conflict='id').execute()

            # Invalidate cache after successful save
            self._invalidate_cache(tenant_id)

            logger.info(f"Saved config for tenant {tenant_id} to database")
            return True

        except Exception as e:
            logger.error(f"Error saving config for tenant {tenant_id}: {e}")
            return False

    def _strip_secrets(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Remove secrets from config before storing in database"""
        # Deep copy to avoid modifying original
        stripped = copy.deepcopy(config)

        # Remove meta
        stripped.pop('_meta', None)

        # Remove client (stored in columns)
        stripped.pop('client', None)

        # Remove secrets from infrastructure
        if 'infrastructure' in stripped:
            infra = stripped['infrastructure']
            if 'supabase' in infra:
                infra['supabase'].pop('anon_key', None)
                infra['supabase'].pop('service_key', None)
            if 'vapi' in infra:
                infra['vapi'].pop('api_key', None)
            if 'openai' in infra:
                infra['openai'].pop('api_key', None)

        # Remove secrets from email
        if 'email' in stripped:
            email = stripped['email']
            if 'sendgrid' in email:
                email['sendgrid'].pop('api_key', None)
            if 'smtp' in email:
                email['smtp'].pop('password', None)

        return stripped

    def list_tenants(self, active_only: bool = True) -> List[str]:
        """
        List all tenant IDs from database.

        Args:
            active_only: Only return active tenants

        Returns:
            List of tenant IDs
        """
        client = self._get_supabase_client()
        if not client:
            return []

        try:
            query = client.table("tenants").select("id")
            if active_only:
                query = query.eq("status", "active")

            result = query.execute()
            return [row['id'] for row in result.data or []]
        except Exception as e:
            logger.warning(f"Error listing tenants from database: {e}")
            return []

    def get_tenant_status(self, tenant_id: str) -> str:
        """Get tenant status (active, suspended, deleted)"""
        client = self._get_supabase_client()
        if client:
            try:
                result = client.table("tenants").select("status").eq("id", tenant_id).single().execute()
                if result.data:
                    return result.data.get('status', 'active')
            except Exception as e:
                log_and_suppress(e, context="get_tenant_status", tenant_id=tenant_id)
        return 'unknown'

    def tenant_exists(self, tenant_id: str) -> bool:
        """Check if tenant exists in database"""
        client = self._get_supabase_client()
        if not client:
            return False

        try:
            result = client.table("tenants").select("id").eq("id", tenant_id).single().execute()
            return bool(result.data)
        except Exception as e:
            log_and_suppress(e, context="tenant_exists", tenant_id=tenant_id)
            return False


# Module-level convenience functions
_service_instance: Optional[TenantConfigService] = None


def get_service() -> TenantConfigService:
    """Get or create singleton service instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = TenantConfigService()
    return _service_instance


def reset_service():
    """Reset the singleton service instance (for cache clearing)"""
    global _service_instance
    _service_instance = None


def get_tenant_config(tenant_id: str) -> Optional[Dict[str, Any]]:
    """Convenience function to get tenant config"""
    return get_service().get_config(tenant_id)


def list_all_tenants() -> List[str]:
    """Convenience function to list all tenants"""
    return get_service().list_tenants()
