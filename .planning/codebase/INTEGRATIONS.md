# External Integrations

**Analysis Date:** 2025-01-23

## APIs & External Services

**OpenAI:**
- Purpose: LLM for email parsing, helpdesk responses, and RAG synthesis
- SDK: `openai 2.8.0`, `langchain-openai 1.0.3`
- Models: GPT-4o-mini (default, configurable per tenant)
- Auth: `OPENAI_API_KEY` env var
- Implementation: `src/agents/llm_email_parser.py`, `src/services/rag_response_service.py`

**Google Cloud Platform:**
- BigQuery - Hotel rates, flight prices, analytics
  - Client: `google-cloud-bigquery 3.26.0`
  - Implementation: `src/tools/bigquery_tool.py`
  - Project: `GCP_PROJECT_ID` env var
  - Datasets: tenant-specific (`{tenant}_analytics`), shared pricing
- Cloud Storage - FAISS index storage
  - Client: `google-cloud-storage 2.18.2`
  - Bucket: `zorah-475411-rag-documents` (default)
  - Implementation: `src/services/faiss_helpdesk_service.py`
- Vertex AI - RAG capabilities (optional)
  - Client: `langchain-google-vertexai 3.0.3`
  - Implementation: `src/tools/rag_tool.py`

**SendGrid:**
- Purpose: Transactional email (quotes, invoices, invitations)
- SDK: `sendgrid 6.12.5` (but uses direct API via requests)
- Implementation: `src/utils/email_sender.py`
- Auth: Per-tenant API keys in `tenant_settings` or `client.yaml`
- Features:
  - Inbound Parse webhook: `src/webhooks/email_webhook.py`
  - Quote emails with PDF attachments
  - Invoice emails with payment details
  - User invitation emails

**Twilio:**
- Purpose: Phone number provisioning
- Implementation: `src/tools/twilio_vapi_provisioner.py`
- Auth: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` env vars
- Features:
  - Search available numbers by country
  - Purchase numbers
  - Address registration for regulatory compliance
  - Integration with VAPI for voice AI

**VAPI (Voice AI):**
- Purpose: AI voice assistants for inbound/outbound calls
- Implementation: `src/tools/twilio_vapi_provisioner.py`
- Auth: `VAPI_API_KEY` env var
- Features:
  - Import Twilio numbers to VAPI
  - Assign assistants to phone numbers
  - Per-tenant webhook routing

## Data Storage

**Supabase (PostgreSQL):**
- Primary database for operational data
- Client: `supabase >=2.9.0`
- Implementation: `src/tools/supabase_tool.py`
- Connection: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` env vars
- Tables:
  - `quotes` - Travel quotes
  - `invoices` - Customer invoices
  - `invoice_travelers` - Traveler details
  - `clients` - CRM contacts
  - `activities` - CRM activity log
  - `inbound_tickets` - Support tickets
  - `outbound_call_queue` - Scheduled calls
  - `call_records` - Call transcripts
  - `helpdesk_sessions` - Chat sessions
  - `tenant_settings` - Tenant configuration overrides
  - `tenant_branding` - UI customization
  - `tenant_templates` - Quote/invoice templates
  - `organization_users` - User accounts
  - `user_invitations` - Pending invitations

**BigQuery:**
- Analytics and pricing data
- Client: `google-cloud-bigquery 3.26.0`
- Implementation: `src/tools/bigquery_tool.py`
- Tables:
  - `hotel_rates` - Hotel pricing (shared across tenants)
  - `flight_prices` - Flight pricing
  - `consultants` - Sales team (optional)

**Google Cloud Storage:**
- FAISS index files for helpdesk knowledge base
- Bucket: `zorah-475411-rag-documents`
- Files: `faiss_indexes/index.faiss`, `faiss_indexes/index.pkl`
- Local cache: System temp directory (`/tmp/zorah_faiss_cache`)

**File Storage (Supabase Storage):**
- Bucket: `tenant-assets`
- Purpose: Tenant logos and branding assets
- Implementation: `SupabaseTool.upload_logo_to_storage()`

**Caching:**
- In-memory caches for:
  - Supabase clients (`_supabase_client_cache`)
  - Auth clients (`_auth_client_cache`)
  - User sessions (`_user_cache`, 60s TTL)
  - Tenant email mappings (`_tenant_email_cache`, 300s TTL)
  - Client configs (`_config_cache`)
- Redis (optional) - Rate limiting storage via `slowapi`

## Authentication & Identity

**Supabase Auth:**
- JWT-based authentication
- Implementation: `src/services/auth_service.py`
- Features:
  - Email/password login
  - Token refresh
  - Password reset (via Supabase)
  - Multi-tenant user management
- Middleware: `src/middleware/auth_middleware.py`
- Rate limiting: `src/api/auth_routes.py` with `slowapi`

**JWT Verification:**
- Library: `pyjwt` (via supabase SDK)
- Secret: `SUPABASE_JWT_SECRET` env var (production)
- Development mode: Signature verification disabled if secret not set

## Monitoring & Observability

**Structured Logging:**
- Implementation: `src/utils/structured_logger.py`
- JSON output for production (`JSON_LOGS=true`)
- Request ID tracking via `src/middleware/request_id_middleware.py`
- Performance timing via `src/middleware/timing_middleware.py`

**PII Audit Logging:**
- Implementation: `src/middleware/pii_audit_middleware.py`
- GDPR/POPIA compliance logging
- Enabled via `PII_AUDIT_ENABLED` env var

**Error Tracking:**
- Global exception handler in `main.py`
- Structured error responses via `src/utils/error_handler.py`

**Health Checks:**
- `/health` - Basic liveness
- `/health/ready` - Full readiness (DB + BigQuery)
- `/health/live` - Kubernetes liveness probe
- Docker HEALTHCHECK configured in `Dockerfile`

## CI/CD & Deployment

**GitHub Actions:**
- Configuration: `.github/workflows/ci.yml`
- Jobs:
  - `test` - Linting (flake8) + pytest with 57% coverage threshold
  - `docker-build` - Docker image build validation

**Container Registry:**
- Docker image tagged with git SHA
- Build caching via GitHub Actions cache

**Hosting Platforms:**
- Railway: `railway.json` configuration
- Render: `render.yaml` configuration
- Port: 8080 (container) / configurable via `PORT` env

## Webhooks & Callbacks

**Incoming Webhooks:**
- `/webhooks/email/inbound` - SendGrid Inbound Parse (multi-tenant)
- `/webhooks/email/inbound/{tenant_id}` - Per-tenant email webhook
- `/webhooks/email/debug` - Debug endpoint for testing

**Outgoing Webhooks:**
- VAPI server URL per tenant: `https://api.zorahai.com/webhooks/vapi/{client_id}`
- Configured during phone number provisioning

## Environment Configuration

**Required Environment Variables:**
```
PORT=8000
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...
GCP_PROJECT_ID=project-id
OPENAI_API_KEY=sk-...
SENDGRID_MASTER_API_KEY=SG...
VAPI_API_KEY=uuid
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
```

**Optional Environment Variables:**
```
CORS_ORIGINS=https://app.example.com
LOG_LEVEL=INFO
JSON_LOGS=true
PII_AUDIT_ENABLED=true
SUPABASE_JWT_SECRET=...
FAISS_BUCKET_NAME=bucket-name
FAISS_INDEX_PREFIX=faiss_indexes/
BASE_URL=https://api.example.com
```

**Per-Tenant Configuration:**
Stored in `clients/{tenant_id}/client.yaml` or database (`tenant_settings` table):
- SendGrid API key and sender settings
- Banking details for invoices
- GCP dataset name
- VAPI assistant IDs
- OpenAI model preference
- Branding colors and logo URLs

**Secrets Management:**
- Environment variables in production
- `.env` file for local development (in `.gitignore`)
- Supports `${VAR:-default}` syntax in YAML configs

---

*Integration audit: 2025-01-23*
