"""
Tenant Configuration Service - Database-backed tenant config with YAML fallback

Usage:
    from src.services.tenant_config_service import TenantConfigService, get_tenant_config

    service = TenantConfigService()
    config = service.get_config("tenant_id")  # Returns dict

    # Or use convenience function
    config = get_tenant_config("tenant_id")

Features:
    - Database-first lookup with YAML fallback
    - Redis caching with configurable TTL (5 minutes default)
    - Graceful fallback when Redis unavailable
    - Secret handling (resolved from env vars, not stored in DB)
"""

import os
import json
import logging
import copy
import re
from typing import Dict, Any, List, Optional
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


class TenantConfigService:
    """
    Tenant configuration service with dual-mode operation:
    1. Try Redis cache first (if available)
    2. Try database (Supabase tenants table)
    3. Fall back to YAML files for unmigrated tenants

    Ignores tn_* auto-generated test tenants (garbage data).
    """

    # Real tenants that are migrated to database
    # These are the actual test/development clients we use
    MIGRATED_TENANTS = {
        'africastay',
        'safariexplore-kvph',
        'safarirun-t0vc',
        'beachresorts',
    }

    # YAML-only tenants (skips cache for these)
    YAML_ONLY_TENANTS = {
        'africastay',
        'safariexplore-kvph',
        'safarirun-t0vc',
        'beachresorts',
        'example',
    }

    # tn_* prefixed tenants are auto-generated test data - ignore them
    # They will NOT be migrated and their YAML files can be deleted

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
        Get tenant configuration (cache -> database -> YAML fallback)

        Args:
            tenant_id: Tenant identifier

        Returns:
            Configuration dict or None if not found
        """
        # Skip tn_* auto-generated test tenants - they're garbage data
        if tenant_id.startswith('tn_'):
            logger.debug(f"Ignoring auto-generated test tenant: {tenant_id}")
            return None

        # Check if YAML-only tenant (skip cache for these)
        if tenant_id in self.YAML_ONLY_TENANTS:
            return self._load_from_yaml(tenant_id)

        # Try cache first
        cached = self._get_from_cache(tenant_id)
        if cached:
            return cached

        # Try database
        config = self._load_from_database(tenant_id)
        if config:
            self._set_cache(tenant_id, config)
            return config

        # Fall back to YAML
        logger.debug(f"Tenant {tenant_id} not in database, falling back to YAML")
        yaml_config = self._load_from_yaml(tenant_id)
        if yaml_config:
            # Cache YAML config too (same TTL)
            self._set_cache(tenant_id, yaml_config)
        return yaml_config

    def _load_from_database(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Load config from Supabase tenants table"""
        client = self._get_supabase_client()
        if not client:
            return None

        try:
            result = client.table("tenants").select("*").eq("id", tenant_id).single().execute()

            if not result.data:
                return None

            row = result.data

            # Check if this tenant has database config
            if row.get('config_source') != 'database':
                return None

            # Build config dict from database row
            tenant_config = row.get('tenant_config', {}) or {}

            config = {
                'client': {
                    'id': row['id'],
                    'name': row['name'],
                    'short_name': row.get('short_name', ''),
                    'timezone': row.get('timezone', 'Africa/Johannesburg'),
                    'currency': row.get('currency', 'ZAR'),
                },
                'branding': tenant_config.get('branding', {}),
                'destinations': tenant_config.get('destinations', []),
                'infrastructure': self._build_infrastructure(row, tenant_config),
                'email': self._build_email_config(row, tenant_config),
                'banking': tenant_config.get('banking', {}),
                'consultants': tenant_config.get('consultants', []),
                'agents': tenant_config.get('agents', {}),
            }

            # Add status info
            config['_meta'] = {
                'source': 'database',
                'status': row.get('status', 'active'),
                'plan': row.get('plan', 'lite'),
                'features_enabled': row.get('features_enabled', {}),
            }

            return config

        except Exception as e:
            logger.error(f"Error loading tenant {tenant_id} from database: {e}")
            return None

    def _build_infrastructure(self, row: Dict, tenant_config: Dict) -> Dict[str, Any]:
        """Build infrastructure config, resolving env vars for secrets"""
        infra = tenant_config.get('infrastructure', {})
        tenant_id = row['id']

        # GCP config
        gcp = infra.get('gcp', {}).copy() if infra.get('gcp') else {}
        gcp['project_id'] = row.get('gcp_project_id') or gcp.get('project_id', os.getenv('GCP_PROJECT_ID', ''))
        gcp['dataset'] = row.get('gcp_dataset') or gcp.get('dataset', '')
        gcp['region'] = gcp.get('region', 'us-central1')

        # Supabase - URL from config, keys from env
        supabase = infra.get('supabase', {}).copy() if infra.get('supabase') else {}
        supabase['url'] = os.getenv('SUPABASE_URL', supabase.get('url', ''))
        supabase['anon_key'] = os.getenv('SUPABASE_ANON_KEY', '')
        supabase['service_key'] = os.getenv('SUPABASE_SERVICE_KEY', '')

        # VAPI - try tenant-specific env var, fall back to config
        vapi = infra.get('vapi', {}).copy() if infra.get('vapi') else {}
        tenant_env_key = tenant_id.upper().replace('-', '_')
        vapi['api_key'] = os.getenv(f'{tenant_env_key}_VAPI_API_KEY') or os.getenv('VAPI_API_KEY', '')

        # OpenAI - shared API key from env
        openai = infra.get('openai', {}).copy() if infra.get('openai') else {}
        openai['api_key'] = os.getenv('OPENAI_API_KEY', '')

        return {
            'gcp': gcp,
            'supabase': supabase,
            'vapi': vapi,
            'openai': openai,
        }

    def _build_email_config(self, row: Dict, tenant_config: Dict) -> Dict[str, Any]:
        """Build email config, resolving env vars for API keys"""
        email = tenant_config.get('email', {}).copy() if tenant_config.get('email') else {}
        tenant_id = row['id']
        tenant_env_key = tenant_id.upper().replace('-', '_')

        email['primary'] = row.get('primary_email') or email.get('primary', '')

        # SendGrid - try tenant-specific env var
        sendgrid = email.get('sendgrid', {}).copy() if email.get('sendgrid') else {}
        sendgrid['api_key'] = os.getenv(f'{tenant_env_key}_SENDGRID_API_KEY') or os.getenv('SENDGRID_API_KEY', '')
        email['sendgrid'] = sendgrid

        # SMTP password from env
        smtp = email.get('smtp', {}).copy() if email.get('smtp') else {}
        smtp['password'] = os.getenv(f'{tenant_env_key}_SMTP_PASSWORD') or os.getenv('SMTP_PASSWORD', '')
        email['smtp'] = smtp

        # IMAP config
        imap = email.get('imap', {}).copy() if email.get('imap') else {}
        email['imap'] = imap

        return email

    def _load_from_yaml(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Load config from YAML file"""
        config_path = self.base_path / "clients" / tenant_id / "client.yaml"

        if not config_path.exists():
            return None

        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            # Substitute env vars
            config = self._substitute_env_vars(config)

            # Add meta info
            config['_meta'] = {
                'source': 'yaml',
                'status': 'active',
            }

            return config

        except Exception as e:
            logger.error(f"Error loading YAML for tenant {tenant_id}: {e}")
            return None

    def _substitute_env_vars(self, obj: Any) -> Any:
        """Recursively substitute ${VAR} and ${VAR:-default} patterns"""
        if isinstance(obj, dict):
            return {k: self._substitute_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            pattern = r'\$\{([A-Z_][A-Z0-9_]*)(?::-([^}]+))?\}'

            def replacer(match):
                var_name = match.group(1)
                default = match.group(2)
                return os.getenv(var_name, default or '')

            return re.sub(pattern, replacer, obj)
        else:
            return obj

    def save_config(self, tenant_id: str, config: Dict[str, Any]) -> bool:
        """
        Save tenant configuration to database

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

            row = {
                'id': tenant_id,
                'name': client_info.get('name', tenant_id),
                'short_name': client_info.get('short_name', ''),
                'timezone': client_info.get('timezone', 'Africa/Johannesburg'),
                'currency': client_info.get('currency', 'ZAR'),
                'primary_email': config.get('email', {}).get('primary', ''),
                'gcp_project_id': config.get('infrastructure', {}).get('gcp', {}).get('project_id', ''),
                'gcp_dataset': config.get('infrastructure', {}).get('gcp', {}).get('dataset', ''),
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

    def list_tenants(self, include_yaml: bool = True) -> List[str]:
        """
        List all available tenant IDs

        Args:
            include_yaml: Include YAML-only tenants in list

        Returns:
            List of tenant IDs
        """
        tenant_ids = set()

        # Get from database
        client = self._get_supabase_client()
        if client:
            try:
                result = client.table("tenants").select("id").eq("status", "active").execute()
                for row in result.data or []:
                    tenant_ids.add(row['id'])
            except Exception as e:
                logger.warning(f"Error listing tenants from database: {e}")

        # Add YAML tenants
        if include_yaml:
            clients_dir = self.base_path / "clients"
            if clients_dir.exists():
                for client_dir in clients_dir.iterdir():
                    if client_dir.is_dir():
                        # Skip tn_* auto-generated test tenants
                        if client_dir.name.startswith('tn_'):
                            continue
                        config_file = client_dir / "client.yaml"
                        if config_file.exists():
                            tenant_ids.add(client_dir.name)

        return sorted(list(tenant_ids))

    def get_tenant_status(self, tenant_id: str) -> str:
        """Get tenant status (active, suspended, deleted)"""
        client = self._get_supabase_client()
        if client:
            try:
                result = client.table("tenants").select("status").eq("id", tenant_id).single().execute()
                if result.data:
                    return result.data.get('status', 'active')
            except Exception:
                pass
        return 'active'  # Default for YAML tenants


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
