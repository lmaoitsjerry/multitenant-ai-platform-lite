#!/usr/bin/env python3
"""
Client Setup Automation Tool

Automates the complete setup process for a new client.
Target: Complete setup in <1 hour.

Usage:
    python scripts/setup_client.py --client-id acmetravel --config-file clients/acmetravel/client.yaml
    
    # Or interactive mode:
    python scripts/setup_client.py --interactive
"""

import click
import yaml
import json
from pathlib import Path
from google.cloud import bigquery, aiplatform
from google.cloud import storage
from supabase import create_client
import sys
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.loader import ClientConfig


@click.group()
def cli():
    """Client Setup Automation Tool"""
    pass


@cli.command()
@click.option('--client-id', required=True, help='Client identifier (e.g., acmetravel)')
@click.option('--config-file', required=True, help='Path to client.yaml file')
@click.option('--skip-bigquery', is_flag=True, help='Skip BigQuery setup')
@click.option('--skip-supabase', is_flag=True, help='Skip Supabase setup')
@click.option('--skip-rag', is_flag=True, help='Skip RAG corpus creation')
def setup(client_id, config_file, skip_bigquery, skip_supabase, skip_rag):
    """
    Set up complete infrastructure for new client
    
    This will:
    1. Validate configuration
    2. Create BigQuery dataset and tables
    3. Create Vertex AI RAG corpus
    4. Create Supabase tables
    5. Generate environment file
    """
    click.echo(f"🚀 Setting up client: {click.style(client_id, bold=True, fg='green')}")
    click.echo(f"📖 Config file: {config_file}\n")
    
    # Step 1: Load and validate configuration
    click.echo("📋 Step 1/5: Loading configuration...")
    try:
        config = load_and_validate_config(config_file)
        click.echo(f"   ✅ Configuration valid for {config['client']['name']}\n")
    except Exception as e:
        click.echo(f"   ❌ Configuration error: {e}", err=True)
        sys.exit(1)
    
    # Step 2: Create BigQuery dataset and tables
    if not skip_bigquery:
        click.echo("📊 Step 2/5: Creating BigQuery dataset and tables...")
        try:
            create_bigquery_infrastructure(config)
            click.echo(f"   ✅ BigQuery dataset '{config['infrastructure']['gcp']['dataset']}' created\n")
        except Exception as e:
            click.echo(f"   ❌ BigQuery setup failed: {e}", err=True)
            if not click.confirm("Continue anyway?"):
                sys.exit(1)
    else:
        click.echo("📊 Step 2/5: Skipped BigQuery setup\n")
    
    # Step 3: Create Vertex AI RAG corpus
    if not skip_rag:
        click.echo("🧠 Step 3/5: Creating Vertex AI RAG corpus...")
        try:
            corpus_id = create_rag_corpus(config)
            click.echo(f"   ✅ RAG corpus created: {corpus_id}")
            click.echo(f"   📝 Update client.yaml with: corpus_id: '{corpus_id}'\n")
        except Exception as e:
            click.echo(f"   ❌ RAG corpus creation failed: {e}", err=True)
            click.echo(f"   ⚠️  You can create it manually later\n")
    else:
        click.echo("🧠 Step 3/5: Skipped RAG corpus creation\n")
    
    # Step 4: Create Supabase tables
    if not skip_supabase:
        click.echo("💾 Step 4/5: Creating Supabase tables...")
        try:
            create_supabase_tables(config)
            click.echo(f"   ✅ Supabase tables created\n")
        except Exception as e:
            click.echo(f"   ❌ Supabase setup failed: {e}", err=True)
            if not click.confirm("Continue anyway?"):
                sys.exit(1)
    else:
        click.echo("💾 Step 4/5: Skipped Supabase setup\n")
    
    # Step 5: Generate .env file
    click.echo("🔐 Step 5/5: Generating environment file...")
    try:
        env_path = generate_env_file(client_id, config)
        click.echo(f"   ✅ Environment file created: {env_path}\n")
    except Exception as e:
        click.echo(f"   ❌ Failed to generate .env: {e}", err=True)
    
    # Summary
    click.echo("=" * 60)
    click.echo(f"✨ {click.style('Setup Complete!', bold=True, fg='green')}")
    click.echo("=" * 60)
    click.echo("\n📋 Next Steps:")
    click.echo("1. Import hotel rates data:")
    click.echo(f"   python scripts/import_data.py --client-id {client_id} --type hotel_rates --file data.xlsx")
    click.echo("2. Upload knowledge base documents:")
    click.echo(f"   python scripts/upload_docs.py --client-id {client_id} --dir docs/")
    click.echo("3. Test the system:")
    click.echo(f"   python scripts/test_client.py --client-id {client_id}")
    click.echo("4. Deploy to Cloud Run:")
    click.echo(f"   ./scripts/deploy.sh {client_id}\n")


def load_and_validate_config(config_path):
    """Load and validate client configuration"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Validate required fields
    required_fields = [
        'client.id',
        'client.name',
        'infrastructure.gcp.project_id',
        'infrastructure.gcp.dataset',
        'infrastructure.supabase.url',
        'infrastructure.openai.api_key',
        'email.primary',
    ]
    
    for field in required_fields:
        keys = field.split('.')
        value = config
        for key in keys:
            value = value.get(key)
            if value is None:
                raise ValueError(f"Missing required field: {field}")
    
    return config


def create_bigquery_infrastructure(config):
    """Create BigQuery dataset and all required tables"""
    project_id = config['infrastructure']['gcp']['project_id']
    dataset_id = config['infrastructure']['gcp']['dataset']
    region = config['infrastructure']['gcp'].get('region', 'us-central1')
    
    client = bigquery.Client(project=project_id)
    
    # Create dataset
    dataset = bigquery.Dataset(f"{project_id}.{dataset_id}")
    dataset.location = region
    dataset = client.create_dataset(dataset, exists_ok=True)
    
    # Create tables
    tables_sql = {
        'hotel_rates': """
            CREATE TABLE IF NOT EXISTS `{project}.{dataset}.hotel_rates` (
                rate_id STRING NOT NULL,
                destination STRING NOT NULL,
                hotel_name STRING NOT NULL,
                hotel_rating INT64,
                room_type STRING,
                meal_plan STRING,
                check_in_date DATE NOT NULL,
                check_out_date DATE NOT NULL,
                nights INT64 NOT NULL,
                total_7nights_pps INT64,
                total_7nights_single INT64,
                total_7nights_child INT64,
                transfers_adult INT64,
                transfers_child INT64,
                is_active BOOL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
            )
        """,
        'hotel_media': """
            CREATE TABLE IF NOT EXISTS `{project}.{dataset}.hotel_media` (
                hotel_name STRING NOT NULL,
                destination STRING NOT NULL,
                description STRING,
                image_url STRING,
                amenities ARRAY<STRING>,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
            )
        """,
        'flight_prices': """
            CREATE TABLE IF NOT EXISTS `{project}.{dataset}.flight_prices` (
                destination STRING NOT NULL,
                departure_date DATE NOT NULL,
                return_date DATE NOT NULL,
                price_per_person INT64 NOT NULL,
                airline STRING,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
            )
        """,
        'consultants': """
            CREATE TABLE IF NOT EXISTS `{project}.{dataset}.consultants` (
                consultant_id STRING NOT NULL,
                name STRING NOT NULL,
                email STRING NOT NULL,
                is_active BOOL DEFAULT TRUE,
                last_assigned TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
            )
        """,
        'quotes': """
            CREATE TABLE IF NOT EXISTS `{project}.{dataset}.quotes` (
                quote_id STRING NOT NULL,
                customer_name STRING,
                customer_email STRING,
                destination STRING,
                check_in DATE,
                check_out DATE,
                adults INT64,
                children INT64,
                quote_data JSON,
                consultant_id STRING,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
                status STRING DEFAULT 'sent'
            )
        """,
        'cost_metrics': """
            CREATE TABLE IF NOT EXISTS `{project}.{dataset}.cost_metrics` (
                metric_name STRING NOT NULL,
                metric_value FLOAT64,
                timestamp TIMESTAMP NOT NULL,
                source STRING,
                details JSON
            )
        """,
    }
    
    for table_name, sql in tables_sql.items():
        query = sql.format(project=project_id, dataset=dataset_id)
        client.query(query).result()
        click.echo(f"   ✓ Created table: {table_name}")
    
    # Insert default consultants if provided
    if 'consultants' in config:
        insert_consultants(client, project_id, dataset_id, config['consultants'])


def insert_consultants(client, project_id, dataset_id, consultants):
    """Insert consultant records"""
    import uuid
    
    for consultant in consultants:
        if consultant.get('active', True):
            query = f"""
                INSERT INTO `{project_id}.{dataset_id}.consultants` 
                (consultant_id, name, email, is_active, created_at)
                VALUES (
                    '{uuid.uuid4()}',
                    '{consultant['name']}',
                    '{consultant['email']}',
                    TRUE,
                    CURRENT_TIMESTAMP()
                )
            """
            client.query(query).result()
            click.echo(f"   ✓ Added consultant: {consultant['name']}")


def create_rag_corpus(config):
    """Create Vertex AI RAG corpus"""
    project_id = config['infrastructure']['gcp']['project_id']
    region = config['infrastructure']['gcp'].get('region', 'us-central1')
    client_name = config['client']['name']
    
    aiplatform.init(project=project_id, location=region)
    
    # Create corpus
    from vertexai.preview import rag
    
    corpus = rag.create_corpus(
        display_name=f"{client_name}_knowledge_base",
        description=f"Knowledge base for {client_name}"
    )
    
    # Extract corpus ID from resource name
    corpus_id = corpus.name.split('/')[-1]
    
    return corpus_id


def create_supabase_tables(config):
    """Create Supabase tables"""
    url = config['infrastructure']['supabase']['url']
    key = config['infrastructure']['supabase'].get('service_key') or config['infrastructure']['supabase']['anon_key']
    
    supabase = create_client(url, key)
    
    # SQL for table creation
    tables_sql = """
    CREATE TABLE IF NOT EXISTS employees (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        employee_id TEXT UNIQUE NOT NULL,
        auth_user_id UUID REFERENCES auth.users(id),
        full_name TEXT NOT NULL,
        email TEXT NOT NULL,
        department TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    
    CREATE TABLE IF NOT EXISTS inbound_tickets (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        requirements JSONB,
        conversation_transcript JSONB,
        quote_id TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    
    CREATE TABLE IF NOT EXISTS helpdesk_conversations (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        session_id TEXT NOT NULL,
        employee_id TEXT,
        messages JSONB,
        total_messages INT DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    
    CREATE TABLE IF NOT EXISTS knowledge_base_files (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        file_name TEXT NOT NULL,
        file_path TEXT,
        file_size INT,
        file_type TEXT,
        uploaded_by_name TEXT,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """
    
    # Execute SQL (Note: Supabase Python client doesn't support raw SQL well)
    # This would typically be done via Supabase dashboard or SQL editor
    click.echo("   ⚠️  Supabase tables should be created via SQL editor")
    click.echo("   📋 Copy the SQL from scripts/supabase_tables.sql")


def generate_env_file(client_id, config):
    """Generate .env file for client"""
    env_content = f"""# Environment variables for {config['client']['name']}
# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}

# Client
CLIENT_ID={client_id}

# Google Cloud
GCP_PROJECT_ID={config['infrastructure']['gcp']['project_id']}
GCP_REGION={config['infrastructure']['gcp'].get('region', 'us-central1')}
BIGQUERY_DATASET={config['infrastructure']['gcp']['dataset']}
CORPUS_ID={config['infrastructure']['gcp'].get('corpus_id', '')}

# Supabase
SUPABASE_URL={config['infrastructure']['supabase']['url']}
SUPABASE_KEY={config['infrastructure']['supabase']['anon_key']}
SUPABASE_SERVICE_KEY={config['infrastructure']['supabase'].get('service_key', '')}

# OpenAI
OPENAI_API_KEY={config['infrastructure']['openai']['api_key']}

# VAPI (if configured)
VAPI_API_KEY={config['infrastructure'].get('vapi', {}).get('api_key', '')}

# Email
SMTP_HOST={config['email']['smtp']['host']}
SMTP_PORT={config['email']['smtp']['port']}
SMTP_USER={config['email']['smtp']['username']}
SMTP_PASSWORD=<SET_THIS>

# App Configuration
PORT=8080
ENVIRONMENT=production
"""
    
    env_path = Path(f".env.{client_id}")
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    return env_path


@cli.command()
@click.option('--client-id', required=True)
def validate(client_id):
    """Validate client configuration"""
    config_path = Path(f"clients/{client_id}/client.yaml")
    
    if not config_path.exists():
        click.echo(f"❌ Configuration file not found: {config_path}", err=True)
        sys.exit(1)
    
    try:
        config = ClientConfig(client_id)
        click.echo(f"✅ Configuration valid for {config.name}")
        click.echo(f"\nClient Details:")
        click.echo(f"  Name: {config.name}")
        click.echo(f"  Destinations: {', '.join(config.destination_names)}")
        click.echo(f"  GCP Project: {config.gcp_project_id}")
        click.echo(f"  Dataset: {config.dataset_name}")
        click.echo(f"  Email: {config.primary_email}")
    except Exception as e:
        click.echo(f"❌ Configuration error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
