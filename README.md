# AI Platform - Multi-Tenant

**Multi-tenant AI platform for travel agencies**

Supports multiple clients with <1 hour setup time per client.

## Quick Start

### For New Client Setup

```bash
# 1. Create client configuration
cp clients/example/client.yaml.template clients/yourclient/client.yaml

# 2. Edit configuration
nano clients/yourclient/client.yaml

# 3. Run setup automation
python scripts/setup_client.py --client-id yourclient

# 4. Import data
python scripts/import_hotel_rates.py --client-id yourclient --excel-file rates.xlsx

# 5. Deploy
./scripts/deploy.sh yourclient
```

Setup time: **30-45 minutes**

## Architecture

- **FastAPI** - REST API server
- **LangChain** - AI agent orchestration  
- **Vertex AI RAG** - Knowledge base
- **BigQuery** - Analytics database
- **Supabase** - Application database
- **VAPI** - Phone calling

## Structure

```
ai-platform-multitenant/
├── config/          # Configuration system
├── clients/         # Client-specific configs
├── src/            # Source code
├── scripts/        # Setup automation
└── docs/           # Documentation
```

## Features

- 🤖 3 AI Agents (Inbound, Helpdesk, Outbound)
- 📧 Email automation
- 📞 AI phone calling
- 💰 Quote generation
- 📊 Analytics dashboard
- 🔒 Multi-tenant isolation

## Documentation

- [Architecture](docs/architecture.md)
- [Client Setup Guide](docs/client_setup.md)
- [Configuration Reference](docs/configuration.md)

## License

Proprietary
