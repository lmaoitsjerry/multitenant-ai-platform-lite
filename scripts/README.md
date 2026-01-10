# Multi-Tenant AI Platform - Scripts

Automation scripts for client setup and management.

## Setup Client

Complete infrastructure setup for a new client:

```bash
python scripts/setup_client.py setup \
    --client-id acmetravel \
    --config-file clients/acmetravel/client.yaml
```

## Import Data

Import hotel rates from Excel:

```bash
python scripts/import_data.py \
    --client-id acmetravel \
    --type hotel_rates \
    --file data/acmetravel_rates.xlsx
```

## Validate Configuration

Check client configuration:

```bash
python scripts/setup_client.py validate --client-id acmetravel
```
