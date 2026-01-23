# Architecture

**Analysis Date:** 2025-01-23

## Pattern Overview

**Overall:** Multi-Tenant Monolith with Layered Service Architecture

**Key Characteristics:**
- Single FastAPI application serving multiple travel agency clients (tenants)
- Tenant isolation via `X-Client-ID` header and `tenant_id` column in all database tables
- Agent-based AI orchestration for quote generation and email processing
- YAML-based per-tenant configuration with database fallback support
- Shared infrastructure (Supabase, BigQuery) with logical data separation

## Layers

**API Layer:**
- Purpose: HTTP endpoints, request validation, authentication, and routing
- Location: `src/api/`
- Contains: FastAPI routers organized by domain (quotes, CRM, invoices, admin, etc.)
- Depends on: Services, Agents, Middleware
- Used by: Frontend applications (React), webhooks (SendGrid), external clients

**Middleware Layer:**
- Purpose: Cross-cutting concerns - auth, rate limiting, timing, security headers
- Location: `src/middleware/`
- Contains: Request/response interceptors, JWT validation, PII auditing
- Depends on: Config, Auth Service
- Used by: All API requests

**Agent Layer:**
- Purpose: AI-powered business logic orchestration (LLM interactions)
- Location: `src/agents/`
- Contains: QuoteAgent, HelpdeskAgent, InboundAgent, EmailParsers
- Depends on: Tools, Services, Config
- Used by: API routes, Webhooks

**Service Layer:**
- Purpose: Business logic, data orchestration, caching
- Location: `src/services/`
- Contains: CRMService, ProvisioningService, FAISSHelpdeskService, TenantConfigService
- Depends on: Tools, Config
- Used by: Agents, API routes

**Tools Layer:**
- Purpose: External system integrations (databases, APIs)
- Location: `src/tools/`
- Contains: SupabaseTool, BigQueryTool, RAGTool, TwilioVapiProvisioner
- Depends on: Config
- Used by: Services, Agents

**Utils Layer:**
- Purpose: Shared utilities (PDF generation, email sending, logging)
- Location: `src/utils/`
- Contains: PDFGenerator, EmailSender, StructuredLogger, ErrorHandler
- Depends on: Config
- Used by: All layers

**Config Layer:**
- Purpose: Tenant configuration loading, validation, caching
- Location: `config/`
- Contains: ClientConfig class, DatabaseTables abstraction, JSON schema
- Depends on: Environment variables, YAML files, Supabase (optional)
- Used by: All layers

**Webhooks Layer:**
- Purpose: Inbound event processing (emails, callbacks)
- Location: `src/webhooks/`
- Contains: Email webhook for SendGrid Inbound Parse
- Depends on: Agents, Config
- Used by: External services (SendGrid)

## Data Flow

**Quote Generation Flow:**

1. Request arrives at `POST /api/v1/quotes/generate` with `X-Client-ID` header
2. `get_client_config()` loads tenant configuration from YAML/database
3. `QuoteAgent.generate_quote()` orchestrates the flow:
   - Normalizes customer data
   - Queries BigQuery `hotel_rates` table for matching hotels
   - Calculates pricing via `BigQueryTool.calculate_quote_price()`
   - Generates PDF via `PDFGenerator`
   - Sends email via `EmailSender` (tenant's SendGrid subuser)
   - Saves quote to Supabase `quotes` table with `tenant_id`
   - Creates CRM client record via `CRMService`
4. Response returned with quote details

**Inbound Email Flow:**

1. SendGrid Inbound Parse posts to `/webhooks/email/inbound`
2. Email webhook extracts tenant from TO address (cache lookup -> database -> direct)
3. Background task `process_inbound_email()` runs:
   - `LLMEmailParser` extracts travel requirements via OpenAI
   - Falls back to `UniversalEmailParser` (rule-based) on failure
   - If travel inquiry detected, creates draft quote via `QuoteAgent`
   - Logs to BigQuery for non-travel emails

**State Management:**
- Session state: Not used (stateless API)
- Tenant config: LRU cached in `config.loader._config_cache`, Redis cache in `TenantConfigService`
- Database connections: Cached per tenant in `_supabase_client_cache`
- FAISS index: Singleton with file cache in `tempfile` directory

## Key Abstractions

**ClientConfig:**
- Purpose: Typed access to tenant configuration (destinations, credentials, branding)
- Examples: `config/loader.py`
- Pattern: Property-based access with YAML/database dual-source

**DatabaseTables:**
- Purpose: Centralized BigQuery table name management with tenant isolation
- Examples: `config/database.py`
- Pattern: Property methods returning fully-qualified table names

**SupabaseTool:**
- Purpose: Tenant-scoped Supabase operations with automatic `tenant_id` filtering
- Examples: `src/tools/supabase_tool.py`
- Pattern: All queries include `.eq('tenant_id', self.tenant_id)`

**PipelineStage:**
- Purpose: CRM pipeline state machine (QUOTED -> NEGOTIATING -> BOOKED -> PAID -> TRAVELLED/LOST)
- Examples: `src/services/crm_service.py`
- Pattern: Enum with stage transitions tracked via activity logging

## Entry Points

**Main Application:**
- Location: `main.py`
- Triggers: `uvicorn.run()` or process manager
- Responsibilities: FastAPI app setup, middleware registration, router inclusion, lifespan events

**API Routes:**
- Location: `src/api/routes.py` (includes all domain routers)
- Triggers: HTTP requests
- Responsibilities: Quote generation, CRM operations, invoicing, admin functions

**Email Webhook:**
- Location: `src/webhooks/email_webhook.py`
- Triggers: SendGrid Inbound Parse POST
- Responsibilities: Tenant resolution, email parsing, draft quote creation

**Background Tasks:**
- Location: Various (email processing, call scheduling)
- Triggers: FastAPI `BackgroundTasks`
- Responsibilities: Async processing after request completion

## Error Handling

**Strategy:** Centralized error handler with structured logging

**Patterns:**
- `log_and_raise()` in `src/utils/error_handler.py` for consistent HTTP error responses
- Global exception handler in `main.py` catches unhandled exceptions
- Supabase operations wrapped in try/except with graceful fallbacks
- BigQuery queries have 8-second timeout to stay under frontend limits

## Cross-Cutting Concerns

**Logging:**
- `src/utils/structured_logger.py` for JSON-formatted logs
- Request ID middleware for request tracing
- `[TENANT_ID]` prefix pattern for tenant-scoped logs

**Validation:**
- Pydantic models for request/response validation
- JSON schema validation for tenant config (`config/schema.json`)
- Input sanitization in email parsers

**Authentication:**
- JWT validation via `AuthMiddleware` (Supabase auth)
- `X-Client-ID` header for tenant identification
- Admin routes use `X-Admin-Token` header
- Public routes defined in `PUBLIC_PATHS` and `PUBLIC_PREFIXES`

**Rate Limiting:**
- `RateLimitMiddleware` with SlowAPI
- Auth endpoints have stricter limits (brute-force protection)
- Per-endpoint rate limits configurable

---

*Architecture analysis: 2025-01-23*
