# Architecture

**Analysis Date:** 2026-01-16

## Pattern Overview

**Overall:** Multi-Tenant SaaS with Layered Backend Architecture

**Key Characteristics:**
- Tenant isolation via `X-Client-ID` header and `tenant_id` column
- Hybrid data layer: Supabase (PostgreSQL) for operational data, BigQuery for analytics/pricing
- FastAPI backend with middleware stack for auth, rate limiting, PII audit
- Two separate React frontends: tenant dashboard and internal admin platform
- File-based tenant configuration with YAML per client

## Layers

**API Layer (Routes):**
- Purpose: HTTP endpoint handlers, request/response serialization
- Location: `src/api/`
- Contains: FastAPI routers, Pydantic models, endpoint definitions
- Depends on: Services, Tools, Middleware
- Used by: Frontend applications via REST API

**Service Layer:**
- Purpose: Business logic orchestration, domain operations
- Location: `src/services/`
- Contains: CRMService, AuthService, PerformanceService, ProvisioningService
- Depends on: Tools layer (Supabase, BigQuery)
- Used by: API routes, Agents

**Agent Layer:**
- Purpose: AI-orchestrated workflows (quote generation, follow-ups)
- Location: `src/agents/`
- Contains: QuoteAgent (primary orchestrator)
- Depends on: Services, Tools, Utils (PDF, Email)
- Used by: API routes for quote generation

**Tools Layer:**
- Purpose: External service integrations (database clients)
- Location: `src/tools/`
- Contains: SupabaseTool, BigQueryTool, RAGTool, TwilioVapiProvisioner
- Depends on: Config layer
- Used by: Services, Agents

**Middleware Layer:**
- Purpose: Cross-cutting concerns (auth, rate limiting, logging)
- Location: `src/middleware/`
- Contains: AuthMiddleware, RateLimitMiddleware, TimingMiddleware, PIIAuditMiddleware
- Depends on: Config layer
- Used by: FastAPI app (wraps all requests)

**Configuration Layer:**
- Purpose: Tenant configuration management
- Location: `config/` and `clients/{tenant_id}/`
- Contains: ClientConfig loader, DatabaseTables abstraction, schema validation
- Depends on: Environment variables, YAML files
- Used by: All layers

**Webhooks Layer:**
- Purpose: Inbound webhook handlers (email parsing)
- Location: `src/webhooks/`
- Contains: email_webhook.py (SendGrid inbound parse)
- Depends on: Services, Agents
- Used by: External services (SendGrid)

**Utils Layer:**
- Purpose: Shared utilities (PDF generation, email sending)
- Location: `src/utils/`
- Contains: PDFGenerator, EmailSender, TemplateRenderer
- Depends on: Config layer
- Used by: Agents, API routes

## Data Flow

**Quote Generation Flow:**

1. Frontend POST `/api/v1/quotes/generate` with customer data
2. AuthMiddleware validates JWT, attaches UserContext
3. `routes.py` extracts `X-Client-ID`, loads ClientConfig
4. QuoteAgent orchestrates: normalize data -> find hotels -> calculate pricing -> generate PDF -> send email -> save to Supabase -> add to CRM
5. Response returned with quote_id, status, consultant assignment

**Tenant Authentication Flow:**

1. User POST `/api/v1/auth/login` with email/password
2. AuthService queries Supabase for user by auth_user_id
3. JWT generated with tenant_id embedded
4. Frontend stores token, sends with all subsequent requests
5. AuthMiddleware validates token, loads user context

**Multi-Tenant Data Access:**

1. Every database query includes `tenant_id` filter
2. SupabaseTool and BigQueryTool receive ClientConfig
3. Row-level security (RLS) in Supabase enforces tenant isolation
4. BigQuery uses shared pricing dataset + tenant-specific analytics dataset

**State Management:**

- Backend: Stateless (no session storage, JWT-based auth)
- Frontend: React Context (AuthContext, ThemeContext, AppContext)
- Caching: In-memory client config cache, Supabase client cache per tenant

## Key Abstractions

**ClientConfig:**
- Purpose: Load and validate per-tenant YAML configuration
- Examples: `config/loader.py`
- Pattern: Singleton cache per tenant_id, property-based access

**DatabaseTables:**
- Purpose: Abstract BigQuery table names (shared vs tenant-specific)
- Examples: `config/database.py`
- Pattern: Property methods return fully-qualified table names

**SupabaseTool:**
- Purpose: Tenant-scoped Supabase operations with auto-filtering
- Examples: `src/tools/supabase_tool.py`
- Pattern: All methods automatically filter by `self.tenant_id`

**UserContext:**
- Purpose: Authenticated user info attached to request state
- Examples: `src/middleware/auth_middleware.py`
- Pattern: Middleware populates `request.state.user`, dependencies extract

## Entry Points

**Backend API Server:**
- Location: `main.py`
- Triggers: `uvicorn main:app` or direct execution
- Responsibilities: FastAPI app creation, middleware setup, router inclusion, lifespan management

**Tenant Dashboard Frontend:**
- Location: `frontend/tenant-dashboard/src/main.jsx`
- Triggers: Vite dev server or built bundle
- Responsibilities: React app bootstrap, router setup, context providers

**Internal Admin Frontend:**
- Location: `frontend/internal-admin/src/main.jsx`
- Triggers: Vite dev server or built bundle
- Responsibilities: Admin dashboard for platform operators

**Webhook Endpoints:**
- Location: `src/webhooks/email_webhook.py`
- Triggers: SendGrid inbound parse
- Responsibilities: Parse incoming emails, trigger quote generation

## Error Handling

**Strategy:** Layered exception handling with logging

**Patterns:**
- Routes: `try/except` blocks catching specific exceptions, returning HTTPException with appropriate status codes
- Services: Log errors, return None or empty list on failure (fail gracefully)
- Tools: Log errors, let exceptions propagate for caller to handle
- Global: `app.exception_handler(Exception)` catches unhandled errors, logs stack trace, returns 500

## Cross-Cutting Concerns

**Logging:** Python `logging` module with configurable level via `LOG_LEVEL` env var. Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

**Validation:** Pydantic models for request/response validation. JSON Schema validation for client YAML configs.

**Authentication:** JWT-based via Supabase Auth. AuthMiddleware validates tokens, attaches UserContext. Public paths bypass auth.

**Rate Limiting:** RateLimitMiddleware with configurable limits per endpoint pattern. Returns 429 with headers on limit exceeded.

**PII Audit:** PIIAuditMiddleware logs access to personal data endpoints for GDPR/POPIA compliance.

---

*Architecture analysis: 2026-01-16*
