# Multi-Tenant AI Platform - Architecture Documentation

**Version**: 2.0  
**Date**: December 2025  
**Status**: Production Ready

---

## Overview

A fully multi-tenant AI platform for travel agencies, enabling new client setup in under 1 hour with zero code changes.

**Key Features**:
- ✅ Zero hardcoded values
- ✅ Complete client isolation
- ✅ Dynamic configuration system
- ✅ Automated setup (<1 hour)
- ✅ Template-based prompts and emails
- ✅ Client-specific branding

---

## Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENT LAYER                             │
│  client.yaml → ClientConfig → All Components                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Agents     │  │    Tools     │  │  Templates   │      │
│  │ - Inbound    │  │ - BigQuery   │  │ - Email      │      │
│  │ - Helpdesk   │  │ - RAG        │  │ - PDF        │      │
│  │ - Outbound   │  │ - Email      │  │ - Prompts    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  INFRASTRUCTURE LAYER                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ BigQuery │  │ Vertex   │  │ Supabase │  │  SMTP    │   │
│  │ (Pricing)│  │   AI     │  │  (Auth)  │  │ (Email)  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
multitenant/
├── config/                 # Configuration system
│   ├── loader.py          # ClientConfig loader
│   ├── schema.json        # Validation schema
│   └── database.py        # Table abstraction
├── clients/               # Client-specific configs
│   ├── africastay/
│   │   ├── client.yaml    # Configuration
│   │   └── prompts/       # Agent prompts
│   └── example/           # Template
├── src/
│   ├── agents/            # AI agents
│   ├── tools/             # Tools (BigQuery, RAG)
│   └── utils/             # Utilities
├── templates/             # Jinja2 templates
│   ├── emails/            # Email templates
│   └── pdf/               # PDF templates
└── scripts/               # Automation scripts
```

---

## Configuration System

### client.yaml Structure

```yaml
client:
  id: "clientid"           # Unique identifier
  name: "Client Name"      # Display name
  
branding:
  company_name: "Company"
  primary_color: "#FF6B6B"
  logo_url: "https://..."
  
destinations:
  - name: "Zanzibar"
    code: "ZNZ"
    enabled: true
    
infrastructure:
  gcp:
    project_id: "project-123"
    dataset: "analytics"
    corpus_id: "12345"
  supabase:
    url: "https://..."
    anon_key: "${SUPABASE_KEY}"  # Env var
  openai:
    api_key: "${OPENAI_API_KEY}"
    
email:
  primary: "contact@company.com"
  smtp:
    host: "mail.company.com"
    username: "user"
    password: "${SMTP_PASS}"
```

### Environment Variables

Sensitive values use `${VAR_NAME}` syntax and are loaded from environment:

```bash
export OPENAI_API_KEY="sk-..."
export SMTP_PASS="password123"
```

---

## Core Components

### 1. ClientConfig (config/loader.py)

Central configuration loader with validation and property access.

```python
config = ClientConfig('africastay')

# Property access
config.gcp_project_id      # "zorah-475411"
config.dataset_name        # "africastay_analytics"
config.destination_names   # ["Zanzibar", "Mauritius", ...]
config.primary_color       # "#FF6B6B"
```

### 2. DatabaseTables (config/database.py)

Abstracts all database table names.

```python
db = DatabaseTables(config)

db.hotel_rates        # "zorah-475411.africastay_analytics.hotel_rates"
db.consultants        # "zorah-475411.africastay_analytics.consultants"
```

### 3. Agents

All agents load prompts from template files:

```python
# InboundAgent - Customer chat
agent = InboundAgent(config, session_id)
response = agent.chat("I want to visit Zanzibar")

# HelpdeskAgent - Employee support
agent = HelpdeskAgent(config, session_id)
response = agent.chat("What is our commission?")
```

### 4. Tools

**BigQueryTool**: Query pricing and analytics
```python
bq = BigQueryTool(config)
hotels = bq.find_matching_hotels('Zanzibar', '2025-12-15', '2025-12-22', 7, 2)
```

**RAGTool**: Search knowledge base
```python
rag = RAGTool(config)
results = rag.search_knowledge_base('visa requirements')
```

### 5. Templates

**Email Templates**: Jinja2 with branding
```python
renderer = TemplateRenderer(config)
html = renderer.render_template('emails/quote.html', context)
```

**PDF Generation**: WeasyPrint
```python
pdf_gen = PDFGenerator(config)
pdf_bytes = pdf_gen.generate_quote_pdf(quote_data)
```

---

## Client Setup Process

### Step 1: Create Configuration

```bash
cp clients/example/client.yaml.template clients/newclient/client.yaml
# Edit client.yaml with client details
```

### Step 2: Run Setup Script

```bash
python scripts/setup_client.py setup \
    --client-id newclient \
    --config-file clients/newclient/client.yaml
```

This creates:
- BigQuery dataset + 6 tables
- Vertex AI RAG corpus
- Supabase tables
- Environment file

**Time**: 20-30 minutes

### Step 3: Import Data

```bash
python scripts/import_data.py \
    --client-id newclient \
    --type hotel_rates \
    --file data/rates.xlsx
```

**Time**: 5-10 minutes

### Step 4: Upload Knowledge Base

Upload documents to Vertex AI RAG corpus via GCP Console.

**Time**: 10-15 minutes

### Total Setup Time: **45-60 minutes** ✅

---

## Multi-Tenancy Features

### 1. Complete Isolation

Each client has:
- Separate BigQuery dataset
- Separate RAG corpus
- Separate Supabase tables
- Independent configuration

### 2. Zero Code Changes

Switching clients only requires changing `CLIENT_ID` environment variable:

```bash
export CLIENT_ID=africastay  # Uses AfricaStay config
export CLIENT_ID=acmetravel  # Uses AcmeTravel config
```

Same codebase serves all clients!

### 3. Dynamic Branding

Emails and PDFs automatically use client branding:
- Colors from `branding.primary_color`
- Logo from `branding.logo_url`
- Signature from `branding.email_signature`

### 4. Flexible Destinations

Each client defines their own destinations in `client.yaml`. The system validates all user inputs against the client's destination list.

---

## Deployment

### Cloud Run Deployment

Each client can be deployed independently:

```bash
# Build container
docker build -t gcr.io/PROJECT/client-api:latest .

# Deploy to Cloud Run
gcloud run deploy client-api \
    --image gcr.io/PROJECT/client-api:latest \
    --set-env-vars CLIENT_ID=africastay \
    --region us-central1
```

### Shared Deployment

Multiple clients can share one deployment:

```bash
# Route by subdomain
africastay.platform.com → CLIENT_ID=africastay
acmetravel.platform.com → CLIENT_ID=acmetravel
```

---

## Security

- API keys stored in environment variables
- Supabase Row Level Security (RLS) for multi-tenancy
- Client data completely isolated
- No cross-client data leakage

---

## Performance

- Configuration cached per client
- BigQuery queries optimized with partitioning
- RAG search uses vector indexing
- Email sending is async

---

## Monitoring

Key metrics tracked in `cost_metrics` table:
- RAG query count/cost
- BigQuery bytes processed
- Email sending volume
- API response times

---

## Future Enhancements

1. **Admin Dashboard**: Web UI for client management
2. **Analytics Dashboard**: Per-client performance metrics
3. **A/B Testing**: Template variations
4. **Multi-Language**: i18n support
5. **API Gateway**: Centralized routing

---

## Support

For questions or issues:
- Documentation: `docs/`
- Architecture: This file
- Setup Guide: `scripts/README.md`
