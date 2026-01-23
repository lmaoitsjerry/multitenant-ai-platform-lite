# Codebase Structure

**Analysis Date:** 2025-01-23

## Directory Layout

```
multitenant-ai-platform-lite/
├── main.py                      # FastAPI application entry point
├── config/                      # Configuration loading and validation
│   ├── loader.py               # ClientConfig class, tenant config loading
│   ├── database.py             # DatabaseTables abstraction for BigQuery
│   └── schema.json             # JSON schema for config validation
├── src/                         # Backend source code
│   ├── agents/                 # AI agent orchestrators
│   ├── api/                    # FastAPI route handlers
│   ├── constants/              # Theme presets, enums
│   ├── middleware/             # Request/response middleware
│   ├── services/               # Business logic services
│   ├── tools/                  # External integrations
│   ├── utils/                  # Shared utilities
│   └── webhooks/               # Inbound webhooks
├── clients/                     # Per-tenant configuration
│   ├── africastay/             # Tenant: africastay
│   ├── beachresorts/           # Tenant: beachresorts
│   ├── example/                # Template tenant config
│   └── {tenant_id}/            # Additional tenants
├── frontend/                    # React frontend applications
│   ├── tenant-dashboard/       # Customer-facing dashboard (Vite + React)
│   └── internal-admin/         # Platform admin dashboard
├── database/                    # Database schema
│   └── migrations/             # SQL migration files
├── tests/                       # Test suite
│   └── fixtures/               # Test fixtures and mocks
├── scripts/                     # Utility scripts
├── templates/                   # Email/PDF templates
└── docs/                        # Documentation
```

## Directory Purposes

**`config/`:**
- Purpose: Tenant configuration management
- Contains: Config loader, database table abstraction, validation schema
- Key files: `loader.py` (ClientConfig), `database.py` (DatabaseTables)

**`src/agents/`:**
- Purpose: AI-powered business logic orchestrators
- Contains: Quote generation, email parsing, helpdesk agents
- Key files: `quote_agent.py`, `llm_email_parser.py`, `helpdesk_agent.py`, `inbound_agent.py`

**`src/api/`:**
- Purpose: HTTP endpoint handlers organized by domain
- Contains: FastAPI routers for quotes, CRM, invoices, admin, settings
- Key files: `routes.py` (main router), `auth_routes.py`, `knowledge_routes.py`, `admin_routes.py`

**`src/middleware/`:**
- Purpose: Cross-cutting request/response processing
- Contains: Auth, rate limiting, timing, security headers, PII audit
- Key files: `auth_middleware.py`, `rate_limiter.py`, `timing_middleware.py`

**`src/services/`:**
- Purpose: Business logic and data orchestration
- Contains: CRM, provisioning, FAISS search, tenant config, query classification
- Key files: `crm_service.py`, `faiss_helpdesk_service.py`, `tenant_config_service.py`

**`src/tools/`:**
- Purpose: External system integrations
- Contains: Database clients, API wrappers
- Key files: `supabase_tool.py`, `bigquery_tool.py`, `rag_tool.py`

**`src/utils/`:**
- Purpose: Shared utility functions
- Contains: PDF generation, email sending, logging, error handling
- Key files: `pdf_generator.py`, `email_sender.py`, `structured_logger.py`

**`src/webhooks/`:**
- Purpose: Inbound event handlers
- Contains: SendGrid email webhook
- Key files: `email_webhook.py`

**`clients/{tenant_id}/`:**
- Purpose: Tenant-specific configuration and assets
- Contains: `client.yaml` config, `prompts/` directory, `data/` directory
- Structure:
  ```
  clients/{tenant_id}/
  ├── client.yaml           # Main configuration file
  ├── prompts/              # Agent prompt templates
  │   ├── inbound.txt       # Inbound call prompts
  │   ├── helpdesk.txt      # Helpdesk agent prompts
  │   └── outbound.txt      # Outbound call prompts
  └── data/                 # Tenant data (optional)
      └── knowledge/        # RAG knowledge base documents
  ```

**`frontend/tenant-dashboard/`:**
- Purpose: Customer-facing React dashboard
- Contains: React components, pages, services, context
- Key files: `src/App.jsx`, `src/pages/`, `src/components/`, `src/services/`

**`frontend/internal-admin/`:**
- Purpose: Platform administration dashboard
- Contains: Admin components for tenant management
- Key files: `src/App.jsx`, `src/pages/`, `src/services/`

**`database/migrations/`:**
- Purpose: SQL migration scripts for Supabase
- Contains: Sequential migration files (001_, 002_, etc.)
- Naming: `{number}_{description}.sql`

**`tests/`:**
- Purpose: Python test suite
- Contains: Unit tests, integration tests, fixtures
- Key files: `conftest.py`, `test_*.py`, `fixtures/`

## Key File Locations

**Entry Points:**
- `main.py`: FastAPI application startup, middleware registration
- `src/api/routes.py`: Router aggregation with `include_routers()`

**Configuration:**
- `config/loader.py`: `ClientConfig` class, `get_config()` function
- `config/database.py`: `DatabaseTables` class for BigQuery table names
- `config/schema.json`: JSON schema for config validation
- `.env`: Environment variables (not committed)

**Core Logic:**
- `src/agents/quote_agent.py`: Quote generation orchestrator
- `src/services/crm_service.py`: CRM pipeline management
- `src/tools/supabase_tool.py`: All Supabase operations

**Testing:**
- `tests/conftest.py`: Pytest fixtures and configuration
- `tests/fixtures/`: Mock fixtures for external services

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `quote_agent.py`)
- Route files: `{domain}_routes.py` (e.g., `auth_routes.py`, `pricing_routes.py`)
- Test files: `test_{module}.py` (e.g., `test_quote_agent.py`)
- Migration files: `{NNN}_{description}.sql` (e.g., `001_user_management.sql`)

**Directories:**
- Backend: `snake_case` (e.g., `src/services/`)
- Frontend: `kebab-case` (e.g., `tenant-dashboard/`)
- Tenant configs: Lowercase tenant ID (e.g., `clients/africastay/`)

**Classes:**
- PascalCase: `QuoteAgent`, `CRMService`, `ClientConfig`

**Functions:**
- snake_case: `generate_quote()`, `get_client_config()`

## Where to Add New Code

**New API Endpoint:**
- Create route file: `src/api/{domain}_routes.py`
- Add router to: `src/api/routes.py` in `include_routers()`
- Add tests: `tests/test_{domain}_routes.py`

**New Service:**
- Create service: `src/services/{name}_service.py`
- Follow pattern: Class with `__init__(self, config: ClientConfig)`
- Add tests: `tests/test_{name}_service.py`

**New Agent:**
- Create agent: `src/agents/{name}_agent.py`
- Follow pattern: Class orchestrating tools/services with LLM
- Add prompts if needed: `clients/{tenant}/prompts/{name}.txt`

**New Tool (External Integration):**
- Create tool: `src/tools/{name}_tool.py`
- Follow pattern: Tenant-scoped with `tenant_id` filtering
- Add fixtures: `tests/fixtures/{name}_fixtures.py`

**New Frontend Page:**
- Tenant dashboard: `frontend/tenant-dashboard/src/pages/{Name}.jsx`
- Admin dashboard: `frontend/internal-admin/src/pages/{Name}.jsx`
- Add route in corresponding `App.jsx`

**New Tenant:**
- Copy `clients/example/` to `clients/{new_tenant_id}/`
- Edit `clients/{new_tenant_id}/client.yaml` with tenant config
- Customize prompts in `clients/{new_tenant_id}/prompts/`

**New Middleware:**
- Create: `src/middleware/{name}_middleware.py`
- Register in `main.py` (order matters - last added runs first)

**Database Migration:**
- Create: `database/migrations/{NNN}_{description}.sql`
- Run manually via Supabase SQL editor or migration tool

## Special Directories

**`htmlcov/`:**
- Purpose: Coverage report HTML output
- Generated: Yes (by pytest-cov)
- Committed: No (.gitignore)

**`.planning/`:**
- Purpose: GSD planning documents and codebase mapping
- Generated: Partially (by GSD commands)
- Committed: Yes

**`venv/`:**
- Purpose: Python virtual environment
- Generated: Yes
- Committed: No (.gitignore)

**`__pycache__/`:**
- Purpose: Python bytecode cache
- Generated: Yes
- Committed: No (.gitignore)

**`node_modules/`:**
- Purpose: Node.js dependencies (frontend)
- Generated: Yes (npm install)
- Committed: No (.gitignore)

**`dist/`:**
- Purpose: Frontend build output
- Generated: Yes (npm run build)
- Committed: No (.gitignore)

---

*Structure analysis: 2025-01-23*
