# Codebase Structure

**Analysis Date:** 2026-01-16

## Directory Layout

```
multitenant-ai-platform-lite/
├── main.py                     # FastAPI app entry point
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container build
├── .env                        # Environment variables (not committed)
├── config/                     # Configuration system
│   ├── loader.py              # ClientConfig class
│   ├── database.py            # DatabaseTables abstraction
│   └── schema.json            # YAML validation schema
├── clients/                    # Per-tenant configurations
│   ├── example/               # Template tenant
│   │   └── client.yaml       # Tenant config
│   ├── africastay/            # Production tenant
│   └── tn_*/                   # Auto-provisioned tenants
├── src/                        # Backend source code
│   ├── api/                   # FastAPI route handlers
│   ├── services/              # Business logic
│   ├── agents/                # AI orchestration
│   ├── tools/                 # External integrations
│   ├── middleware/            # Request middleware
│   ├── webhooks/              # Inbound webhooks
│   ├── utils/                 # Utilities (PDF, email)
│   └── constants/             # Shared constants
├── frontend/                   # React applications
│   ├── tenant-dashboard/      # Tenant-facing SPA
│   └── internal-admin/        # Internal admin SPA
├── database/                   # Database artifacts
│   └── migrations/            # Supabase SQL migrations
├── templates/                  # Document templates
│   ├── emails/                # Email HTML templates
│   └── pdf/                   # PDF templates
├── tests/                      # Test suite
├── scripts/                    # Utility scripts
└── docs/                       # Documentation
```

## Directory Purposes

**`config/`:**
- Purpose: Configuration loading and validation system
- Contains: ClientConfig class, DatabaseTables abstraction, JSON schema
- Key files: `loader.py` (main), `database.py` (BigQuery table names), `schema.json` (validation)

**`clients/`:**
- Purpose: Per-tenant configuration storage
- Contains: YAML config files, agent prompts, tenant-specific assets
- Key files: `{tenant_id}/client.yaml` defines all tenant settings

**`src/api/`:**
- Purpose: REST API endpoint definitions
- Contains: FastAPI routers organized by domain
- Key files: `routes.py` (quotes, CRM, invoices), `admin_routes.py`, `auth_routes.py`, `analytics_routes.py`

**`src/services/`:**
- Purpose: Business logic layer
- Contains: Domain-specific service classes
- Key files: `auth_service.py`, `crm_service.py`, `performance_service.py`, `provisioning_service.py`

**`src/agents/`:**
- Purpose: AI-orchestrated workflows
- Contains: Agent classes that coordinate multiple services
- Key files: `quote_agent.py` (primary orchestrator for quote generation)

**`src/tools/`:**
- Purpose: External service client wrappers
- Contains: Database tools, API clients
- Key files: `supabase_tool.py` (PostgreSQL ops), `bigquery_tool.py` (analytics), `rag_tool.py` (knowledge search)

**`src/middleware/`:**
- Purpose: Request processing middleware
- Contains: Auth, rate limiting, PII audit, timing
- Key files: `auth_middleware.py`, `rate_limiter.py`, `pii_audit_middleware.py`, `timing_middleware.py`

**`src/webhooks/`:**
- Purpose: Inbound webhook handlers
- Contains: Email webhook processing
- Key files: `email_webhook.py` (SendGrid inbound parse)

**`src/utils/`:**
- Purpose: Shared utilities
- Contains: PDF generation, email sending, template rendering
- Key files: `pdf_generator.py`, `email_sender.py`, `template_renderer.py`

**`frontend/tenant-dashboard/`:**
- Purpose: Tenant-facing React SPA
- Contains: Pages, components, context, services, hooks
- Key files: `src/App.jsx` (routing), `src/services/api.js` (API client), `src/context/AuthContext.jsx`

**`frontend/internal-admin/`:**
- Purpose: Internal platform admin dashboard
- Contains: Admin-only pages (tenants, usage, knowledge)
- Key files: `src/App.jsx` (routing), `src/pages/TenantsList.jsx`, `src/pages/Dashboard.jsx`

**`database/migrations/`:**
- Purpose: Supabase schema migrations
- Contains: Numbered SQL migration files
- Key files: `001_user_management.sql` through `013_logo_email_url.sql`

**`templates/`:**
- Purpose: Document templates for PDF/email generation
- Contains: HTML templates with Jinja2 syntax
- Key files: `emails/quote.html`, `pdf/quote.html`, `pdf/invoice.html`

## Key File Locations

**Entry Points:**
- `main.py`: Backend FastAPI application
- `frontend/tenant-dashboard/src/main.jsx`: Tenant dashboard React entry
- `frontend/internal-admin/src/main.jsx`: Admin dashboard React entry

**Configuration:**
- `config/loader.py`: ClientConfig class definition
- `config/database.py`: DatabaseTables abstraction
- `config/schema.json`: YAML validation schema
- `clients/{tenant_id}/client.yaml`: Per-tenant configuration

**Core Logic:**
- `src/agents/quote_agent.py`: Quote generation orchestrator
- `src/services/crm_service.py`: CRM business logic
- `src/services/auth_service.py`: Authentication logic
- `src/tools/supabase_tool.py`: Supabase database operations
- `src/tools/bigquery_tool.py`: BigQuery analytics queries

**API Routes:**
- `src/api/routes.py`: Main routes (quotes, CRM, invoices)
- `src/api/auth_routes.py`: Authentication endpoints
- `src/api/admin_routes.py`: Admin/provisioning endpoints
- `src/api/analytics_routes.py`: Dashboard analytics
- `src/api/helpdesk_routes.py`: AI helpdesk search

**Testing:**
- `tests/`: Test directory (limited coverage)
- Root-level `test_*.py`: Ad-hoc integration tests

## Naming Conventions

**Files:**
- Python: `snake_case.py` (e.g., `quote_agent.py`, `auth_service.py`)
- React components: `PascalCase.jsx` (e.g., `Dashboard.jsx`, `ClientsList.jsx`)
- React services: `camelCase.js` (e.g., `api.js`)
- SQL migrations: `NNN_description.sql` (e.g., `007_notifications.sql`)

**Directories:**
- Python packages: `snake_case` (e.g., `src/services`, `src/middleware`)
- React: `camelCase` (e.g., `components/common`, `pages/quotes`)
- Tenant configs: `{tenant_id}` format (e.g., `africastay`, `tn_092bb439_003b8ded5fe4`)

**Classes and Functions:**
- Python classes: `PascalCase` (e.g., `QuoteAgent`, `CRMService`)
- Python functions: `snake_case` (e.g., `get_client_config`, `generate_quote`)
- React components: `PascalCase` (e.g., `QuotesList`, `ProtectedRoute`)
- React hooks: `useCamelCase` (e.g., `useAuth`)

## Where to Add New Code

**New API Endpoint:**
- Create route in `src/api/{domain}_routes.py` or add to existing router
- Add router to `src/api/routes.py` in `include_routers()` function
- Use Pydantic models for request/response validation
- Inject dependencies via `Depends(get_client_config)`

**New Service:**
- Create `src/services/{name}_service.py`
- Initialize with `ClientConfig` parameter
- Use SupabaseTool/BigQueryTool for data access
- Import and use from routes or agents

**New Tenant Dashboard Page:**
- Create `frontend/tenant-dashboard/src/pages/{Name}.jsx`
- Add lazy import in `src/App.jsx`
- Add route in the Routes section
- Use `api.js` functions for backend calls

**New Admin Dashboard Page:**
- Create `frontend/internal-admin/src/pages/{Name}.jsx`
- Import in `src/App.jsx`
- Add route and navigation item

**New Database Migration:**
- Create `database/migrations/NNN_{description}.sql`
- Number sequentially after last migration
- Run via Supabase dashboard or CLI

**New Utility:**
- Add to `src/utils/` for shared utilities
- Keep focused on single responsibility

## Special Directories

**`clients/`:**
- Purpose: Tenant-specific YAML configurations
- Generated: Yes (by provisioning service for new tenants)
- Committed: Partial (example committed, production tenants in .gitignore)

**`venv/` and `node_modules/`:**
- Purpose: Dependency installations
- Generated: Yes
- Committed: No (in .gitignore)

**`__pycache__/`:**
- Purpose: Python bytecode cache
- Generated: Yes
- Committed: No (in .gitignore)

**`frontend/*/dist/`:**
- Purpose: Built frontend bundles
- Generated: Yes (by Vite build)
- Committed: No typically

**`.planning/`:**
- Purpose: GSD planning documents
- Generated: Yes (by Claude Code agents)
- Committed: Yes

---

*Structure analysis: 2026-01-16*
