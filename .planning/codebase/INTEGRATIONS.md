# External Integrations

**Analysis Date:** 2026-01-16

## APIs & External Services

**AI/LLM Services:**
- OpenAI - LLM for quote generation, email parsing
  - SDK/Client: `openai`, `langchain-openai`
  - Auth: `OPENAI_API_KEY` env var, also in tenant `client.yaml`
  - Model: Configurable per tenant, default `gpt-4o-mini`

- Google Vertex AI - RAG corpus for knowledge base
  - SDK/Client: `google-cloud-aiplatform`, `langchain-google-vertexai`
  - Auth: GCP service account credentials
  - Config: `corpus_id` per tenant in `client.yaml`

- Sentence Transformers - Local embeddings for FAISS
  - Model: `all-mpnet-base-v2` (768 dimensions)
  - Used in: `src/services/faiss_helpdesk_service.py`

**Email:**
- SendGrid - Transactional email (quotes, invoices, invitations)
  - SDK/Client: `sendgrid` library + direct REST API via `requests`
  - Auth: `SENDGRID_API_KEY` env var (platform), per-tenant `sendgrid_api_key` in config/DB
  - Features: Subuser management, inbound parse webhooks
  - Implementation: `src/utils/email_sender.py`, `src/services/sendgrid_admin.py`

**Voice/Phone (Optional):**
- VAPI - Voice AI assistants
  - Config: `vapi_api_key`, `vapi_phone_number_id`, `vapi_assistant_id` per tenant
  - Implementation: `src/tools/twilio_vapi_provisioner.py`

## Data Storage

**Databases:**
- Supabase (PostgreSQL) - Primary operational database
  - Connection: `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` or `SUPABASE_ANON_KEY`
  - Client: `supabase` Python SDK
  - Per-tenant config in `client.yaml` under `infrastructure.supabase`
  - Implementation: `src/tools/supabase_tool.py`
  - Tables: `quotes`, `invoices`, `clients`, `activities`, `organization_users`, `tenant_settings`, `tenant_branding`

- Google BigQuery - Analytics and pricing data
  - Connection: GCP project via service account
  - Client: `google-cloud-bigquery`
  - Config: `gcp_project_id`, `dataset` (tenant-specific), `shared_pricing_dataset`
  - Implementation: `src/tools/bigquery_tool.py`, `config/database.py`
  - Shared tables: `hotel_rates`, `hotel_media`, `flight_prices`
  - Tenant tables: `quotes`, `cost_metrics`, `consultants`

**Vector Storage:**
- FAISS - Local vector similarity search
  - Storage: Google Cloud Storage bucket (`zorah-faiss-index`)
  - Files: `index.faiss` (vectors), `index.pkl` (metadata)
  - Implementation: `src/services/faiss_helpdesk_service.py`
  - Cached locally in temp directory

**File Storage:**
- Google Cloud Storage - FAISS index, documents
  - Client: `google-cloud-storage`
  - Buckets: `zorah-faiss-index` for helpdesk index

- Supabase Storage - Tenant assets (logos, branding)
  - Bucket: `tenant-assets`
  - Path pattern: `branding/{tenant_id}/{logo_type}.{ext}`

**Caching:**
- In-memory caching for:
  - Client configurations (`_config_cache` in `config/loader.py`)
  - Supabase clients (`_supabase_client_cache` in `src/tools/supabase_tool.py`)
  - Auth clients (`_auth_client_cache` in `src/services/auth_service.py`)
  - User lookups (`_user_cache` with 60s TTL)
  - Quote agents and CRM services per tenant

## Authentication & Identity

**Auth Provider:**
- Supabase Auth - User authentication and JWT management
  - Implementation: `src/services/auth_service.py`
  - Features: Email/password login, JWT tokens, refresh tokens
  - Password reset via Supabase email
  - Multi-tenant: Users linked to organizations via `organization_users` table
  - Tenant-agnostic login supported (auto-detect tenant from membership)

**JWT Handling:**
- Local JWT decode (no signature verification for performance)
- Expiration validation
- User cached by `auth_user_id` for 60 seconds

**Middleware:**
- `src/middleware/auth_middleware.py` - JWT validation on protected routes
- `src/middleware/rate_limiter.py` - Rate limiting per IP/tenant
- `src/middleware/pii_audit_middleware.py` - GDPR/POPIA compliance logging

## Monitoring & Observability

**Error Tracking:**
- Console logging via Python `logging` module
- Global exception handler in FastAPI
- No external error tracking service detected

**Logs:**
- Structured logging with timestamps
- Configurable via `LOG_LEVEL` env var
- Performance timing via `src/middleware/timing_middleware.py`

**Health Checks:**
- `/health` - Basic liveness
- `/health/ready` - Readiness with dependency checks (Supabase, BigQuery)
- `/health/live` - Kubernetes liveness probe

## CI/CD & Deployment

**Hosting:**
- Docker via `Dockerfile`
- Railway via `railway.json`
- Render via `render.yaml`

**CI Pipeline:**
- No CI configuration detected (no `.github/workflows`, no `gitlab-ci.yml`)

**Deployment Config:**
- `Dockerfile`: Python base image, pip install, uvicorn server
- `railway.json`: Build and start commands
- `render.yaml`: Web service configuration

## Environment Configuration

**Required env vars:**
- `OPENAI_API_KEY` - AI services
- `SUPABASE_URL` - Database connection
- `SUPABASE_SERVICE_KEY` or `SUPABASE_KEY` - Database auth
- `SENDGRID_API_KEY` - Email services (platform level)

**Optional env vars:**
- `FAISS_BUCKET_NAME` - Custom GCS bucket for FAISS index
- `LOG_LEVEL` - Logging verbosity
- `PORT`, `HOST` - Server binding
- `CORS_ORIGINS` - Allowed origins (comma-separated)
- `PII_AUDIT_ENABLED` - Enable PII access logging
- `CLIENT_ID` - Default tenant if not in header
- `BASE_URL` - Public API URL

**Secrets location:**
- Environment variables (`.env` file locally)
- Per-tenant secrets in `clients/{tenant_id}/client.yaml`
- Database-stored secrets in `tenant_settings` table (SendGrid subuser keys)

## Webhooks & Callbacks

**Incoming:**
- `/webhooks/email/inbound` - SendGrid Inbound Parse (generic)
- `/webhooks/email/inbound/{tenant_id}` - Per-tenant email webhook
- `/webhooks/email/debug` - Debug endpoint for webhook testing
- `/api/webhooks/sendgrid-inbound` - Legacy endpoint (routes to africastay)

**Outgoing:**
- SendGrid email sends (quotes, invoices, invitations)
- No other outgoing webhooks detected

**Webhook Configuration:**
- SendGrid Inbound Parse requires MX record: `mx.sendgrid.net` on `inbound.zorah.ai`
- Tenant routing via:
  1. Subdomain: `{tenant}@inbound.domain.com`
  2. Plus addressing: `quotes+{tenant}@domain.com`
  3. `X-Tenant-ID` header
  4. `[TENANT:xxx]` in subject line

## Third-Party SDKs Summary

| Service | Package | Purpose |
|---------|---------|---------|
| OpenAI | `openai`, `langchain-openai` | LLM for AI agents |
| Google Cloud | `google-cloud-*` | BigQuery, Storage, Vertex AI |
| Supabase | `supabase` | PostgreSQL + Auth |
| SendGrid | `sendgrid`, `requests` | Email delivery |
| FAISS | `faiss-cpu` | Vector search |
| WeasyPrint | `weasyprint` | PDF generation |
| Sentence Transformers | `sentence-transformers` | Embeddings |

---

*Integration audit: 2026-01-16*
