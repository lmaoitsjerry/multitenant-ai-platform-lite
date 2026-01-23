# Architecture

**Analysis Date:** 2026-01-23

## Pattern Overview

**Overall:** Multi-Tenant Monolith with Service Layer

**Key Characteristics:**
- Single FastAPI application serving multiple tenants via `X-Client-ID` header
- Layered architecture: Routes -> Services/Agents -> Tools -> External Services
- Row-level tenant isolation in shared Supabase/PostgreSQL database
- Shared BigQuery pricing data, tenant-specific analytics datasets
- Configuration-driven tenant customization via YAML files (migrating to database)

## Layers

**API Layer (Routes):**
- Purpose: HTTP endpoints, request validation, response formatting
- Location: `src/api/`
- Contains: FastAPI routers, Pydantic models, endpoint handlers
- Depends on: Services, Agents, Tools
- Used by: Frontend clients, webhooks, external integrations

**Agent Layer:**
- Purpose: Orchestrate complex business workflows (quote generation, helpdesk, email parsing)
- Location: `src/agents/`
- Contains: QuoteAgent, HelpdeskAgent, InboundAgent, UniversalEmailParser
- Depends on: Tools, Services, Config
- Used by: API routes, webhooks

**Service Layer:**
- Purpose: Domain-specific business logic (CRM, Auth, RAG, Reranking)
- Location: `src/services/`
- Contains: CRMService, AuthService, FAISSHelpdeskService, PerformanceService
- Depends on: Tools, Config
- Used by: Agents, API routes

**Tools Layer:**
- Purpose: External service integrations (database clients, APIs)
- Location: `src/tools/`
- Contains: SupabaseTool, BigQueryTool, RAGTool, TwilioVapiProvisioner
- Depends on: Config
- Used by: Agents, Services

**Middleware Layer:**
- Purpose: Cross-cutting concerns (auth, rate limiting, logging, security)
- Location: `src/middleware/`
- Contains: AuthMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware, PIIAuditMiddleware
- Depends on: AuthService, Config
- Used by: FastAPI app (applied to all requests)

**Config Layer:**
- Purpose: Tenant configuration loading, database table abstraction
- Location: `config/`
- Contains: ClientConfig, DatabaseTables, TenantConfigService
- Depends on: YAML files, Supabase tenants table
- Used by: All layers

**Webhooks Layer:**
- Purpose: Handle inbound events from external services
- Location: `src/webhooks/`
- Contains: Email webhook (SendGrid inbound parse)
- Depends on: Agents, Config
- Used by: External services (SendGrid)

**Utils Layer:**
- Purpose: Shared utilities (logging, PDF generation, email sending, error handling)
- Location: `src/utils/`
- Contains: PDFGenerator, EmailSender, StructuredLogger, ErrorHandler
- Depends on: Config
- Used by: All layers

## Data Flow

**Quote Generation Flow:**

1. API receives POST `/api/v1/quotes/generate` with customer data
2. `QuoteAgent.generate_quote()` orchestrates the workflow
3. `BigQueryTool.find_matching_hotels()` queries shared hotel_rates table
4. Agent calculates pricing options based on travelers
5. `PDFGenerator.generate_quote_pdf()` creates branded PDF
6. `EmailSender.send_quote_email()` sends via tenant's SendGrid subuser
7. `SupabaseTool.create_quote()` saves to quotes table with tenant_id
8. `CRMService.get_or_create_client()` adds/updates CRM record

**Email Inbound Flow (Auto-Quote):**

1. SendGrid inbound parse webhook hits `/webhooks/sendgrid-inbound`
2. `email_webhook.resolve_tenant()` matches TO address to tenant
3. `UniversalEmailParser.parse()` extracts travel details via LLM
4. `QuoteAgent.generate_quote(initial_status='draft')` creates quote
5. Quote saved as draft for consultant review

**Authentication Flow:**

1. User logs in via POST `/api/v1/auth/login`
2. `AuthService.authenticate()` validates credentials against Supabase Auth
3. JWT token returned with user_id, tenant_id, role claims
4. Subsequent requests include `Authorization: Bearer <token>`
5. `AuthMiddleware` validates token, sets `request.state.user`
6. Protected routes access user via `get_current_user(request)`

**State Management:**
- No server-side session state (stateless JWT auth)
- Tenant context passed via `X-Client-ID` header or JWT claims
- Config cached per-tenant in memory (`_config_cache`)
- Service instances cached per-tenant (`_quote_agents`, `_crm_services`)

## Key Abstractions

**ClientConfig:**
- Purpose: Encapsulates all tenant-specific configuration
- Examples: `config/loader.py`
- Pattern: Singleton per tenant with caching

**DatabaseTables:**
- Purpose: Abstracts BigQuery table names (shared vs tenant-specific datasets)
- Examples: `config/database.py`
- Pattern: Property-based access to fully-qualified table names

**SupabaseTool:**
- Purpose: Tenant-isolated database operations
- Examples: `src/tools/supabase_tool.py`
- Pattern: All queries filter by `tenant_id` column

**Pipeline Stages:**
- Purpose: CRM workflow states (QUOTED -> NEGOTIATING -> BOOKED -> PAID -> TRAVELLED)
- Examples: `src/services/crm_service.py`
- Pattern: Enum-based state machine

## Entry Points

**Main Application:**
- Location: `main.py`
- Triggers: `uvicorn main:app` or `python main.py`
- Responsibilities: FastAPI app creation, middleware setup, router inclusion, lifespan management

**API Routers:**
- Location: `src/api/routes.py` -> `include_routers(app)`
- Triggers: HTTP requests
- Responsibilities: Route registration for all API endpoints

**Webhooks:**
- Location: `src/webhooks/email_webhook.py`
- Triggers: POST from SendGrid inbound parse
- Responsibilities: Email processing, tenant resolution, auto-quote generation

**Scripts:**
- Location: `scripts/`
- Triggers: Manual CLI execution
- Responsibilities: Tenant provisioning, data migration, user creation

## Error Handling

**Strategy:** Centralized error handling with structured logging

**Patterns:**
- `log_and_raise()` utility for consistent error logging and HTTP exceptions
- Global exception handler in `main.py` catches unhandled errors
- Per-route try/except for specific error types (HTTPException raised early)
- Structured JSON logging with request_id for tracing

**Example:**
```python
from src.utils.error_handler import log_and_raise

try:
    result = await some_operation()
except HTTPException:
    raise  # Re-raise HTTP exceptions as-is
except Exception as e:
    log_and_raise(500, "performing operation", e, logger)
```

## Cross-Cutting Concerns

**Logging:**
- Structured JSON logging via `src/utils/structured_logger.py`
- Request ID middleware adds unique ID to all logs
- Log level configurable via `LOG_LEVEL` env var

**Validation:**
- Pydantic models for request/response validation
- JSON Schema validation for client.yaml configs
- Type hints throughout codebase

**Authentication:**
- JWT-based auth via Supabase Auth
- `AuthMiddleware` validates tokens on protected routes
- Role-based access control (admin, consultant, user)
- `X-Admin-Token` header for internal admin API

**Multi-Tenancy:**
- Tenant ID from `X-Client-ID` header or JWT claims
- Row-level filtering via `tenant_id` column in all tables
- Shared pricing data in BigQuery, tenant-specific CRM/quotes in Supabase
- Per-tenant configuration via YAML or database

**Rate Limiting:**
- `slowapi` for auth endpoints (brute force protection)
- Custom `RateLimitMiddleware` for general API rate limiting
- Per-tenant quotas supported

**Security:**
- CORS middleware with configurable origins
- Security headers (CSP, X-Frame-Options, HSTS)
- PII audit logging for compliance (GDPR/POPIA)

---

*Architecture analysis: 2026-01-23*
