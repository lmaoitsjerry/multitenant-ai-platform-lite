# Codebase Structure

**Analysis Date:** 2026-01-23

## Directory Layout

```
multitenant-ai-platform-lite/
├── main.py                          # FastAPI application entry point
├── requirements.txt                 # Python dependencies
├── pyproject.toml                   # Project configuration, pytest settings
├── Dockerfile                       # Container build configuration
├── .env                             # Environment variables (local)
├── config/                          # Configuration loading
│   ├── loader.py                    # ClientConfig class, tenant config
│   ├── database.py                  # DatabaseTables abstraction
│   └── schema.json                  # JSON Schema for client.yaml
├── src/                             # Application source code
│   ├── api/                         # FastAPI route handlers
│   ├── agents/                      # AI agent orchestrators
│   ├── services/                    # Business logic services
│   ├── tools/                       # External service integrations
│   ├── middleware/                  # Request/response middleware
│   ├── webhooks/                    # Inbound webhook handlers
│   ├── utils/                       # Shared utilities
│   └── constants/                   # Constants and presets
├── clients/                         # Per-tenant configuration
│   ├── africastay/                  # Production tenant
│   ├── beachresorts/                # Demo tenant
│   ├── example/                     # Template tenant
│   └── {tenant_id}/                 # Each tenant has its own folder
├── tests/                           # Test suite
│   ├── conftest.py                  # Shared fixtures
│   ├── fixtures/                    # Test data generators
│   └── test_*.py                    # Test modules
├── templates/                       # Document templates
│   ├── emails/                      # Email HTML templates
│   └── pdf/                         # PDF generation templates
├── database/                        # Database schema
│   └── migrations/                  # SQL migration files
├── scripts/                         # Utility scripts
├── frontend/                        # Frontend applications
│   ├── tenant-dashboard/            # React dashboard for tenants
│   └── internal-admin/              # Internal admin panel
├── docs/                            # Documentation
└── .planning/                       # Planning documents
```

## Directory Purposes

**`config/`**
- Purpose: Tenant configuration management
- Contains: ClientConfig loader, DatabaseTables abstraction, JSON schema
- Key files:
  - `loader.py`: Main configuration class with all tenant properties
  - `database.py`: BigQuery/Supabase table name abstraction
  - `schema.json`: Validates client.yaml structure

**`src/api/`**
- Purpose: HTTP API endpoints
- Contains: FastAPI routers organized by domain
- Key files:
  - `routes.py`: Main router aggregation, quote/CRM/invoice endpoints
  - `auth_routes.py`: Login, password reset, token refresh
  - `admin_routes.py`: Platform provisioning endpoints
  - `analytics_routes.py`: Dashboard statistics
  - `knowledge_routes.py`: Knowledge base management
  - `helpdesk_routes.py`: AI helpdesk chat endpoints

**`src/agents/`**
- Purpose: AI-powered workflow orchestration
- Contains: Business logic agents that coordinate multiple tools/services
- Key files:
  - `quote_agent.py`: Full quote generation pipeline
  - `helpdesk_agent.py`: AI chatbot with function calling
  - `inbound_agent.py`: Voice/chat customer agent
  - `universal_email_parser.py`: LLM-based email parsing
  - `llm_email_parser.py`: Email detail extraction

**`src/services/`**
- Purpose: Domain-specific business logic
- Contains: Services for specific capabilities
- Key files:
  - `crm_service.py`: Client management, pipeline operations
  - `auth_service.py`: JWT validation, user management
  - `faiss_helpdesk_service.py`: FAISS vector search (singleton)
  - `tenant_config_service.py`: Database-backed tenant config
  - `rag_response_service.py`: RAG response generation
  - `reranker_service.py`: Search result reranking

**`src/tools/`**
- Purpose: External service integrations
- Contains: Wrappers for databases and APIs
- Key files:
  - `supabase_tool.py`: PostgreSQL operations (quotes, invoices, CRM)
  - `bigquery_tool.py`: Analytics queries, hotel rate search
  - `rag_tool.py`: RAG/vector search operations
  - `twilio_vapi_provisioner.py`: Phone number provisioning

**`src/middleware/`**
- Purpose: Cross-cutting request/response processing
- Contains: Middleware classes for FastAPI
- Key files:
  - `auth_middleware.py`: JWT validation, user context
  - `rate_limiter.py`: Request rate limiting
  - `security_headers.py`: CSP, HSTS, X-Frame-Options
  - `pii_audit_middleware.py`: GDPR/POPIA compliance logging
  - `timing_middleware.py`: Request duration logging
  - `request_id_middleware.py`: Unique request ID generation

**`src/utils/`**
- Purpose: Shared utility functions
- Contains: Helpers used across layers
- Key files:
  - `pdf_generator.py`: Quote/invoice PDF generation
  - `email_sender.py`: SendGrid email sending
  - `structured_logger.py`: JSON logging setup
  - `error_handler.py`: Centralized error handling
  - `template_renderer.py`: Jinja2 template rendering

**`src/webhooks/`**
- Purpose: Inbound event processing
- Contains: Handlers for external webhooks
- Key files:
  - `email_webhook.py`: SendGrid inbound parse handler

**`src/constants/`**
- Purpose: Static configuration values
- Contains: Enums, presets, constant definitions
- Key files:
  - `theme_presets.py`: Branding color presets

**`clients/`**
- Purpose: Per-tenant configuration and assets
- Contains: One folder per tenant with config and prompts
- Structure per tenant:
  - `client.yaml`: Tenant configuration
  - `prompts/`: Agent prompt templates
  - `data/knowledge/`: Knowledge base documents (optional)

**`tests/`**
- Purpose: Automated test suite
- Contains: Unit tests, integration tests, fixtures
- Key files:
  - `conftest.py`: Shared pytest fixtures
  - `fixtures/`: Test data generators (bigquery, sendgrid, openai)
  - `test_*.py`: Test modules matching source modules

**`templates/`**
- Purpose: Document generation templates
- Contains: HTML/Jinja2 templates
- Key files:
  - `emails/quote.html`: Quote email template
  - `pdf/`: PDF layout templates

**`database/migrations/`**
- Purpose: Database schema changes
- Contains: Sequential SQL migration files
- Key files:
  - `001_user_management.sql` through `014_tenant_config.sql`
  - Applied manually via Supabase SQL editor

**`scripts/`**
- Purpose: Development and admin utilities
- Contains: Python scripts for common tasks
- Key files:
  - `create_test_user.py`: Create users for testing
  - `migrate_tenants_to_db.py`: Move configs to database
  - `setup_client.py`: Provision new tenant

**`frontend/tenant-dashboard/`**
- Purpose: React dashboard for travel agencies
- Contains: Vite + React application
- Key locations:
  - `src/pages/`: Page components (Dashboard, Quotes, CRM)
  - `src/components/`: Reusable UI components
  - `src/context/`: React context providers (Auth, Theme, App)
  - `src/services/api.js`: Axios API client

**`frontend/internal-admin/`**
- Purpose: Internal platform admin panel
- Contains: Vite + React application
- Key locations:
  - `src/pages/`: Admin pages
  - `src/components/`: Admin UI components

## Key File Locations

**Entry Points:**
- `main.py`: FastAPI application startup
- `frontend/tenant-dashboard/src/main.jsx`: Dashboard app entry
- `frontend/internal-admin/src/main.jsx`: Admin app entry

**Configuration:**
- `.env`: Environment variables (API keys, URLs)
- `config/loader.py`: ClientConfig class
- `clients/{tenant}/client.yaml`: Per-tenant config
- `pyproject.toml`: Pytest and build configuration

**Core Logic:**
- `src/agents/quote_agent.py`: Quote generation workflow
- `src/services/crm_service.py`: CRM business logic
- `src/tools/supabase_tool.py`: Database operations
- `src/api/routes.py`: API endpoint definitions

**Testing:**
- `tests/conftest.py`: Test fixtures and configuration
- `tests/fixtures/`: Mock data generators
- `tests/test_*.py`: Test modules

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `quote_agent.py`)
- React components: `PascalCase.jsx` (e.g., `Dashboard.jsx`)
- Test files: `test_{module_name}.py` (e.g., `test_quote_agent.py`)
- Config files: `lowercase` (e.g., `client.yaml`, `schema.json`)

**Directories:**
- Python packages: `snake_case` (e.g., `src/services/`)
- React folders: `kebab-case` or `lowercase` (e.g., `tenant-dashboard/`)
- Tenant folders: Exact tenant ID (e.g., `africastay/`)

**Classes:**
- Service classes: `{Domain}Service` (e.g., `CRMService`, `AuthService`)
- Agent classes: `{Purpose}Agent` (e.g., `QuoteAgent`, `HelpdeskAgent`)
- Tool classes: `{Service}Tool` (e.g., `SupabaseTool`, `BigQueryTool`)
- Middleware: `{Feature}Middleware` (e.g., `AuthMiddleware`)

**Functions:**
- Public functions: `snake_case` (e.g., `generate_quote()`)
- Private functions: `_snake_case` (e.g., `_validate_config()`)
- Route handlers: Descriptive verb-noun (e.g., `get_quote()`, `create_invoice()`)

## Where to Add New Code

**New API Endpoint:**
- Create router in `src/api/{domain}_routes.py`
- Add router to `src/api/routes.py` -> `include_routers()`
- Add Pydantic models in same file or `src/api/routes.py`
- Add tests in `tests/test_{domain}_routes.py`

**New Agent:**
- Create `src/agents/{purpose}_agent.py`
- Follow pattern from `quote_agent.py` (config injection, logging)
- Add tests in `tests/test_{purpose}_agent.py`

**New Service:**
- Create `src/services/{domain}_service.py`
- Inject `ClientConfig` in constructor
- Add mock fixture in `tests/conftest.py`
- Add tests in `tests/test_{domain}_service.py`

**New Tool (External Integration):**
- Create `src/tools/{service}_tool.py`
- Use connection caching pattern from `supabase_tool.py`
- Add mock fixtures in `tests/fixtures/{service}_fixtures.py`
- Add tests in `tests/test_{service}_tool.py`

**New Middleware:**
- Create `src/middleware/{feature}_middleware.py`
- Add to `main.py` middleware stack (order matters!)
- Document execution order in `main.py` comments

**New Tenant:**
- Create `clients/{tenant_id}/client.yaml` from `clients/example/`
- Add prompts in `clients/{tenant_id}/prompts/`
- Register in Supabase `tenants` table
- Run `scripts/setup_client.py` for provisioning

**New Database Migration:**
- Create `database/migrations/{NNN}_{description}.sql`
- Apply via Supabase SQL editor
- Document schema changes

**New Test Fixture:**
- Add to `tests/conftest.py` for shared fixtures
- Add to `tests/fixtures/` for domain-specific generators
- Follow existing mock patterns (chainable Supabase, BigQuery)

**New Frontend Page:**
- Create `frontend/tenant-dashboard/src/pages/{Page}.jsx`
- Add route in `App.jsx`
- Create components in `src/components/{domain}/`

## Special Directories

**`.planning/`**
- Purpose: Development planning documents
- Generated: No (manually created)
- Committed: Yes

**`htmlcov/`**
- Purpose: Test coverage HTML reports
- Generated: Yes (by `pytest --cov`)
- Committed: No (in .gitignore)

**`__pycache__/`**
- Purpose: Python bytecode cache
- Generated: Yes
- Committed: No (in .gitignore)

**`frontend/*/node_modules/`**
- Purpose: NPM dependencies
- Generated: Yes (by `npm install`)
- Committed: No (in .gitignore)

**`frontend/*/dist/`**
- Purpose: Built frontend assets
- Generated: Yes (by `npm run build`)
- Committed: Varies (may be included for simple deployments)

**`venv/`**
- Purpose: Python virtual environment
- Generated: Yes
- Committed: No (in .gitignore)

---

*Structure analysis: 2026-01-23*
