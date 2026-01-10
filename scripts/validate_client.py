#!/usr/bin/env python3
"""
Client Validation and Testing Script

Run comprehensive tests on client configuration and components.

Usage:
    python validate_client.py --client-id africastay
    python validate_client.py --client-id africastay --component bigquery
"""

import click
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.loader import ClientConfig
from config.database import DatabaseTables


@click.command()
@click.option('--client-id', required=True, help='Client identifier to validate')
@click.option('--component', default='all', help='Component to test (all, config, database, etc)')
def validate(client_id, component):
    """Validate client configuration and test components"""
    
    click.echo(f"🧪 Validating client: {click.style(client_id, bold=True, fg='cyan')}\n")
    
    # Test 1: Configuration
    click.echo("📋 Testing Configuration...")
    try:
        config = ClientConfig(client_id)
        click.echo(f"   ✓ Client ID: {config.client_id}")
        click.echo(f"   ✓ Name: {config.name}")
        click.echo(f"   ✓ Destinations: {', '.join(config.destination_names)}")
        click.echo(f"   ✓ GCP Project: {config.gcp_project_id}")
        click.echo(f"   ✅ Configuration valid\n")
    except Exception as e:
        click.echo(f"   ❌ Configuration error: {e}\n", err=True)
        sys.exit(1)
    
    # Test 2: Database Abstraction
    if component in ['all', 'database']:
        click.echo("🗄️  Testing Database Abstraction...")
        try:
            db = DatabaseTables(config)
            click.echo(f"   ✓ Hotel rates: {db.hotel_rates}")
            click.echo(f"   ✓ Consultants: {db.consultants}")
            click.echo(f"   ✅ Database abstraction working\n")
        except Exception as e:
            click.echo(f"   ❌ Database error: {e}\n", err=True)
    
    click.echo(f"\n✨ {click.style('Validation complete!', fg='green', bold=True)}")


if __name__ == '__main__':
    validate()
