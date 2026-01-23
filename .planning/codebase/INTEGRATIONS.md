# External Integrations

**Analysis Date:** 2026-01-23

## APIs & External Services

**AI/LLM:**
- OpenAI GPT-4o-mini - Email parsing, helpdesk responses
  - SDK/Client: `openai` Python package
  - Auth: `OPENAI_API_KEY`
  - Used in: `src/agents/llm_email_parser.py`, `src/services/rag_response_service.py`

- Google Vertex AI - RAG corpus search (optional)
  - SDK/Client: `google-cloud-aiplatform`, `vertexai.preview`
  - Auth: GCP service account or ADC
  - Used in: `src/tools/rag_tool.py`

**Email:**
- SendGrid - Transactional email (quotes, invoices, invitations)
  - SDK/Client: `requests` direct API (not sendgrid SDK)
  - Auth: `SENDGRID_MASTER_API_KEY`, per-tenant `sendgrid_api_key`
  - Endpoints: `/v3/mail/send`
  - Used in: `src/utils/email_sender.py`, `src/services/sendgrid_admin.py`
  - Features: Multi-tenant subuser support, inbound parse webhooks

- SendGrid Inbound Parse - Email-to-quote automation
  - Webhook: `/webhooks/email/inbound`
  - Used in: `src/webhooks/email_webhook.py`
  - Receives: Travel inquiries, auto-generates draft quotes

**Voice AI:**
- VAPI - Voice AI assistants (optional)
  - Auth: `VAPI_API_KEY`
  - Used in: `src/tools/twilio_vapi_provisioner.py`
  - Features: Inbound/outbound voice assistants

- Twilio - Phone number provisioning (optional)
  - Auth: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`
  - Used in: `src/tools/twilio_vapi_provisioner.py`, `src/services/provisioning_service.py`

## Data Storage

**Primary Database:**
- Supabase (PostgreSQL)
  - Connection: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
  - Client: `supabase-py` via `src/tools/supabase_tool.py`
  - Tables: `quotes`, `invoices`, `clients`, `activities`, `organization_users`, `tenant_settings`, `tenant_branding`, `user_invitations`, etc.
  - Auth: Supabase Auth with JWT tokens
  - RLS: Row-level security by `tenant_id`

**Analytics/Pricing:**
- Google BigQuery
  - Connection: `GCP_PROJECT_ID`, GCP credentials
  - Client: `google-cloud-bigquery` via `src/tools/bigquery_tool.py`
  - Datasets: `africastay_analytics` (shared pricing), tenant-specific datasets
  - Tables: `hotel_rates`, `flight_prices`, `consultants`

**File/Object Storage:**
- Google Cloud Storage
  - Connection: GCP credentials
  - Client: `google-cloud-storage`
  - Buckets:
    - `zorah-475411-rag-documents` - FAISS indexes (`faiss_indexes/index.faiss`, `index.pkl`)
  - Used in: `src/services/faiss_helpdesk_service.py`

- Supabase Storage
  - Bucket: `tenant-assets`
  - Used for: Tenant logos, branding assets
  - Used in: `src/tools/supabase_tool.py` (upload_logo_to_storage)

**Vector Search:**
- FAISS (via GCS)
  - Index: Shared helpdesk knowledge base
  - Embeddings: 768-dim `all-mpnet-base-v2` (sentence-transformers)
  - Cache: Local temp directory, 24-hour TTL
  - Used in: `src/services/faiss_helpdesk_service.py`

**Caching:**
- Redis (optional)
  - Connection: `REDIS_URL`
  - Used for: Rate limiting backend
  - Fallback: In-memory rate limiting

## Authentication & Identity

**Auth Provider:**
- Supabase Auth
  - Implementation: Email/password authentication
  - JWT: HS256 tokens, optional signature verification
  - Secret: `SUPABASE_JWT_SECRET`
  - Used in: `src/services/auth_service.py`, `src/middleware/auth_middleware.py`

**Authorization:**
- Multi-tenant via `tenant_id` claim in JWT
- Role-based: `admin`, `consultant`, `user` roles
- RLS: Database-level row isolation by tenant

**Protected Routes:**
- All `/api/v1/*` routes (except `/public/*`)
- Auth middleware: `src/middleware/auth_middleware.py`
- Rate limiting: `src/middleware/rate_limiter.py`

## Monitoring & Observability

**Error Tracking:**
- None (use GCP Cloud Logging in production)

**Logs:**
- Structured JSON logging via `src/utils/structured_logger.py`
- Configurable: `LOG_LEVEL`, `JSON_LOGS` env vars
- PII audit logging: `src/middleware/pii_audit_middleware.py`

**Metrics:**
- Request timing middleware: `src/middleware/timing_middleware.py`
- Health checks: `/health`, `/health/ready`, `/health/live`

## CI/CD & Deployment

**Hosting:**
- Google Cloud Run (primary)
  - Region: `us-central1`
  - Memory: 2Gi
  - CPU: 2
  - Scale: 0-10 instances

- Railway (alternative)
  - Config: `railway.json`

- Render (alternative)
  - Config: `render.yaml`

**CI Pipeline:**
- GitHub Actions
  - CI: `.github/workflows/ci.yml`
    - Python 3.11
    - Linting (flake8)
    - Tests with coverage (57% threshold)
    - Docker build verification
  - Deploy: `.github/workflows/deploy.yml`
    - Triggers on CI success
    - Workload Identity Federation auth
    - Artifact Registry push
    - Cloud Run deployment

**Container Registry:**
- Google Artifact Registry
  - Path: `{region}-docker.pkg.dev/{project}/{service}/{service}:{sha}`

## Environment Configuration

**Required env vars:**
```
SUPABASE_URL          # PostgreSQL/Auth
SUPABASE_ANON_KEY     # Public operations
SUPABASE_SERVICE_KEY  # Admin operations
GCP_PROJECT_ID        # BigQuery, GCS, Vertex AI
OPENAI_API_KEY        # LLM for email parsing
SENDGRID_MASTER_API_KEY # Email delivery
```

**Optional env vars:**
```
SUPABASE_JWT_SECRET   # Enable JWT signature verification
VAPI_API_KEY          # Voice AI
TWILIO_ACCOUNT_SID    # Phone provisioning
TWILIO_AUTH_TOKEN
REDIS_URL             # Rate limiting backend
LOG_LEVEL             # DEBUG, INFO, WARNING, ERROR
JSON_LOGS             # true/false
CORS_ORIGINS          # Comma-separated origins
PII_AUDIT_ENABLED     # GDPR/POPIA audit logging
```

**Secrets location:**
- GitHub Secrets (CI/CD)
- GCP Secret Manager (production recommended)
- `.env` file (development)

## Webhooks & Callbacks

**Incoming:**
- `/webhooks/email/inbound` - SendGrid Inbound Parse
  - Receives travel inquiry emails
  - Routes to tenant by email address lookup
  - Triggers background quote generation
- `/api/webhooks/sendgrid-inbound` - Legacy endpoint (redirects)

**Outgoing:**
- SendGrid webhooks for email delivery status (optional)
- VAPI call completion webhooks (optional)

## API Versioning

**Current:** v1 (prefix `/api/v1/`)

**Endpoints by Domain:**
- `/api/v1/quotes/*` - Quote management
- `/api/v1/crm/*` - CRM clients and pipeline
- `/api/v1/invoices/*` - Invoice management
- `/api/v1/public/*` - Public shareable links (no auth)
- `/api/v1/auth/*` - Authentication
- `/api/v1/users/*` - User management
- `/api/v1/admin/*` - Admin operations
- `/api/v1/branding/*` - White-labeling
- `/api/v1/settings/*` - Tenant settings
- `/api/v1/helpdesk/*` - AI helpdesk
- `/api/v1/knowledge/*` - Knowledge base

## Integration Health Checks

**Readiness Check (`/health/ready`):**
- Supabase connection test
- BigQuery connection test

**Liveness Check (`/health/live`):**
- Basic application health

---

*Integration audit: 2026-01-23*
