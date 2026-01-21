#!/usr/bin/env python3
"""
Migrate Tenant Configurations from YAML to Database

This script reads tenant YAML files and inserts them into the Supabase
tenants table. Only production tenants (tn_* prefix) are migrated.

Test tenants remain as YAML files:
- africastay
- safariexplore-kvph
- safarirun-t0vc
- beachresorts
- example

Usage:
    python scripts/migrate_tenants_to_db.py [--dry-run] [--tenant TENANT_ID]

Options:
    --dry-run       Show what would be migrated without making changes
    --tenant ID     Migrate only a specific tenant
    --force         Overwrite existing database records
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

import yaml

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Real tenants TO BE MIGRATED to database
MIGRATE_TENANTS = {
    'africastay',
    'safariexplore-kvph',
    'safarirun-t0vc',
    'beachresorts',
}

# Keep example as a template for new tenant setup (don't migrate, don't delete)
KEEP_AS_TEMPLATE = {'example'}


def get_supabase_client():
    """Get Supabase client for migration"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

    from supabase import create_client
    return create_client(url, key)


def load_yaml_config(tenant_id: str) -> Optional[Dict[str, Any]]:
    """Load tenant configuration from YAML file"""
    config_path = project_root / "clients" / tenant_id / "client.yaml"

    if not config_path.exists():
        logger.warning(f"No YAML file for tenant {tenant_id}")
        return None

    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading YAML for {tenant_id}: {e}")
        return None


def strip_secrets(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove secrets from config before storing in database.
    Secrets are resolved from environment variables at runtime.
    """
    import copy
    stripped = copy.deepcopy(config)

    # Remove client section (stored in columns)
    stripped.pop('client', None)

    # Strip infrastructure secrets
    if 'infrastructure' in stripped:
        infra = stripped['infrastructure']

        if 'supabase' in infra:
            infra['supabase'].pop('anon_key', None)
            infra['supabase'].pop('service_key', None)
            # Keep URL as it's not a secret

        if 'vapi' in infra:
            infra['vapi'].pop('api_key', None)
            # Keep IDs (phone_number_id, assistant_id)

        if 'openai' in infra:
            infra['openai'].pop('api_key', None)
            # Keep model setting

    # Strip email secrets
    if 'email' in stripped:
        email = stripped['email']

        if 'sendgrid' in email:
            email['sendgrid'].pop('api_key', None)
            # Keep from_email, from_name, reply_to

        if 'smtp' in email:
            email['smtp'].pop('password', None)
            # Keep host, port, username

    return stripped


def build_tenant_row(tenant_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Build database row from YAML config"""
    client_info = config.get('client', {})
    email_info = config.get('email', {})
    infra_info = config.get('infrastructure', {})

    return {
        'id': tenant_id,
        'name': client_info.get('name', tenant_id),
        'short_name': client_info.get('short_name', ''),
        'status': 'active',
        'plan': 'lite',  # Default plan
        'admin_email': email_info.get('primary', ''),
        'support_email': email_info.get('primary', ''),
        'timezone': client_info.get('timezone', 'Africa/Johannesburg'),
        'currency': client_info.get('currency', 'ZAR'),
        'primary_email': email_info.get('primary', ''),
        'gcp_project_id': infra_info.get('gcp', {}).get('project_id', ''),
        'gcp_dataset': infra_info.get('gcp', {}).get('dataset', ''),
        'config_source': 'database',
        'tenant_config': strip_secrets(config),
        'max_users': 5,
        'max_monthly_quotes': 100,
        'max_storage_gb': 1,
        'features_enabled': {
            'ai_helpdesk': True,
            'email_quotes': True,
            'voice_calls': bool(infra_info.get('vapi', {}).get('assistant_id')),
        },
    }


def get_tenants_to_migrate() -> List[str]:
    """Get list of real tenant IDs to migrate to database"""
    clients_dir = project_root / "clients"
    tenants = []

    for tenant_id in MIGRATE_TENANTS:
        client_dir = clients_dir / tenant_id
        config_file = client_dir / "client.yaml"
        if config_file.exists():
            tenants.append(tenant_id)
        else:
            logger.warning(f"Tenant {tenant_id} in MIGRATE_TENANTS but no YAML file found")

    return sorted(tenants)


def get_tenants_to_delete() -> List[str]:
    """Get list of tn_* test tenant directories to delete"""
    clients_dir = project_root / "clients"
    to_delete = []

    for client_dir in clients_dir.iterdir():
        if client_dir.is_dir():
            tenant_id = client_dir.name

            # Delete tn_* auto-generated test tenants
            if tenant_id.startswith('tn_'):
                to_delete.append(tenant_id)

    return sorted(to_delete)


def delete_tenant_directory(tenant_id: str, dry_run: bool = False) -> bool:
    """Delete a tenant's YAML directory"""
    import shutil
    client_dir = project_root / "clients" / tenant_id

    if not client_dir.exists():
        return True

    if dry_run:
        logger.info(f"  [DRY RUN] Would delete directory: {client_dir}")
        return True

    try:
        shutil.rmtree(client_dir)
        logger.info(f"  Deleted: {client_dir}")
        return True
    except Exception as e:
        logger.error(f"  Failed to delete {client_dir}: {e}")
        return False


def check_existing(client, tenant_id: str) -> bool:
    """Check if tenant already exists in database"""
    try:
        result = client.table("tenants").select("id, config_source").eq("id", tenant_id).execute()
        if result.data:
            return True
    except Exception:
        pass
    return False


def migrate_tenant(client, tenant_id: str, dry_run: bool = False, force: bool = False) -> bool:
    """
    Migrate a single tenant from YAML to database

    Returns:
        True if migration successful (or skipped in dry-run)
    """
    logger.info(f"Processing tenant: {tenant_id}")

    # Load YAML config
    config = load_yaml_config(tenant_id)
    if not config:
        logger.error(f"  Failed to load YAML config")
        return False

    # Check if already exists
    exists = check_existing(client, tenant_id)
    if exists and not force:
        logger.info(f"  Already exists in database, skipping (use --force to overwrite)")
        return True

    # Build row
    row = build_tenant_row(tenant_id, config)

    if dry_run:
        logger.info(f"  [DRY RUN] Would {'update' if exists else 'insert'}: {row['name']}")
        logger.info(f"    - Email: {row['primary_email']}")
        logger.info(f"    - Timezone: {row['timezone']}")
        logger.info(f"    - Currency: {row['currency']}")
        logger.info(f"    - Destinations: {len(config.get('destinations', []))}")
        return True

    # Insert/update
    try:
        if exists and force:
            client.table("tenants").update(row).eq("id", tenant_id).execute()
            logger.info(f"  Updated: {row['name']}")
        else:
            client.table("tenants").insert(row).execute()
            logger.info(f"  Inserted: {row['name']}")
        return True
    except Exception as e:
        logger.error(f"  Failed to save: {e}")
        return False


def verify_migration(client, tenant_ids: List[str]) -> Dict[str, Any]:
    """Verify migration by checking all tenants are in database"""
    results = {
        'total': len(tenant_ids),
        'found': 0,
        'missing': [],
        'source_database': 0,
    }

    for tenant_id in tenant_ids:
        try:
            result = client.table("tenants").select("id, config_source").eq("id", tenant_id).single().execute()
            if result.data:
                results['found'] += 1
                if result.data.get('config_source') == 'database':
                    results['source_database'] += 1
            else:
                results['missing'].append(tenant_id)
        except Exception:
            results['missing'].append(tenant_id)

    return results


def main():
    parser = argparse.ArgumentParser(description='Migrate real tenants to database and clean up test data')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    parser.add_argument('--tenant', type=str, help='Migrate only a specific tenant')
    parser.add_argument('--force', action='store_true', help='Overwrite existing records')
    parser.add_argument('--verify', action='store_true', help='Verify migration status')
    parser.add_argument('--cleanup', action='store_true', help='Delete tn_* test tenant directories')
    parser.add_argument('--skip-cleanup', action='store_true', help='Skip deletion of tn_* directories')
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Tenant Migration: Real Tenants to Database + Cleanup")
    logger.info("=" * 60)

    # Get Supabase client
    try:
        client = get_supabase_client()
        logger.info("Connected to Supabase")
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {e}")
        sys.exit(1)

    # Get tenants to migrate
    if args.tenant:
        if args.tenant not in MIGRATE_TENANTS:
            logger.error(f"Tenant {args.tenant} is not in MIGRATE_TENANTS list: {MIGRATE_TENANTS}")
            sys.exit(1)
        tenants = [args.tenant]
    else:
        tenants = get_tenants_to_migrate()

    logger.info(f"Real tenants to migrate: {len(tenants)} - {tenants}")
    logger.info(f"Template kept (not migrated): {KEEP_AS_TEMPLATE}")

    if args.dry_run:
        logger.info("Mode: DRY RUN (no changes will be made)")

    # Phase 1: Migrate real tenants to database
    logger.info("\n--- Phase 1: Migrate real tenants ---")
    success = 0
    failed = 0

    for tenant_id in tenants:
        if migrate_tenant(client, tenant_id, dry_run=args.dry_run, force=args.force):
            success += 1
        else:
            failed += 1

    logger.info(f"Migration: {success} success, {failed} failed")

    # Phase 2: Clean up tn_* test tenant directories
    if not args.skip_cleanup:
        logger.info("\n--- Phase 2: Clean up tn_* test directories ---")
        to_delete = get_tenants_to_delete()
        logger.info(f"Test tenant directories to delete: {len(to_delete)}")

        deleted = 0
        delete_failed = 0
        for tenant_id in to_delete:
            if delete_tenant_directory(tenant_id, dry_run=args.dry_run):
                deleted += 1
            else:
                delete_failed += 1

        logger.info(f"Cleanup: {deleted} deleted, {delete_failed} failed")

    logger.info("\n" + "=" * 60)
    logger.info("Operation complete")

    # Verify if requested
    if args.verify or not args.dry_run:
        logger.info("\nVerification:")
        verification = verify_migration(client, tenants)
        logger.info(f"  Real tenants: {verification['total']}")
        logger.info(f"  Found in database: {verification['found']}")
        logger.info(f"  With config_source=database: {verification['source_database']}")
        if verification['missing']:
            logger.warning(f"  Missing: {verification['missing']}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
