#!/usr/bin/env python3
"""
Data Import Utility

Import hotel rates, flight prices, and other data for clients.

Usage:
    python scripts/import_data.py --client-id africastay --type hotel_rates --file data/rates.xlsx
"""

import click
import pandas as pd
from google.cloud import bigquery
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.loader import ClientConfig


@click.command()
@click.option('--client-id', required=True, help='Client identifier')
@click.option('--type', 'data_type', required=True, 
              type=click.Choice(['hotel_rates', 'flight_prices', 'hotel_media', 'consultants']),
              help='Type of data to import')
@click.option('--file', 'file_path', required=True, help='Path to Excel/CSV file')
@click.option('--sheet', default=None, help='Excel sheet name (if Excel file)')
def import_data(client_id, data_type, file_path, sheet):
    """Import data to BigQuery for a client"""
    
    click.echo(f"📊 Importing {data_type} for {client_id}")
    click.echo(f"📁 File: {file_path}\n")
    
    # Load configuration
    try:
        config = ClientConfig(client_id)
    except Exception as e:
        click.echo(f"❌ Failed to load config: {e}", err=True)
        sys.exit(1)
    
    # Read data file
    try:
        if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
            df = pd.read_excel(file_path, sheet_name=sheet)
        elif file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            click.echo("❌ Unsupported file format. Use .xlsx, .xls, or .csv", err=True)
            sys.exit(1)
        
        click.echo(f"✅ Loaded {len(df)} rows")
    except Exception as e:
        click.echo(f"❌ Failed to read file: {e}", err=True)
        sys.exit(1)
    
    # Validate and transform data
    try:
        df = validate_and_transform(df, data_type)
        click.echo(f"✅ Data validated")
    except Exception as e:
        click.echo(f"❌ Data validation failed: {e}", err=True)
        sys.exit(1)
    
    # Upload to BigQuery
    try:
        upload_to_bigquery(config, df, data_type)
        click.echo(f"✅ Uploaded {len(df)} records to BigQuery")
    except Exception as e:
        click.echo(f"❌ Upload failed: {e}", err=True)
        sys.exit(1)
    
    click.echo(f"\n✨ Import complete!")


def validate_and_transform(df, data_type):
    """Validate and transform dataframe based on data type"""
    
    if data_type == 'hotel_rates':
        required_cols = ['destination', 'hotel_name', 'room_type', 'meal_plan', 
                        'check_in_date', 'check_out_date', 'nights', 'total_7nights_pps']
        
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Generate rate_id if not present
        if 'rate_id' not in df.columns:
            import uuid
            df['rate_id'] = [str(uuid.uuid4()) for _ in range(len(df))]
        
        # Set defaults
        if 'is_active' not in df.columns:
            df['is_active'] = True
        
    elif data_type == 'flight_prices':
        required_cols = ['destination', 'departure_date', 'return_date', 'price_per_person']
        
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
    
    return df


def upload_to_bigquery(config, df, data_type):
    """Upload dataframe to BigQuery"""
    client = bigquery.Client(project=config.gcp_project_id)
    table_id = config.get_table_name(data_type)
    
    # Configure load job
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )
    
    # Load data
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()  # Wait for completion


if __name__ == '__main__':
    import_data()
