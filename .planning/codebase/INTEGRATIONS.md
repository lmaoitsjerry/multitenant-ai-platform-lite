# External Integrations

## Supabase
- **Auth**: JWT-based authentication
- **Database**: PostgreSQL with RLS
- **Config**: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`
- **Files**: `src/services/auth_service.py`, `src/tools/supabase_tool.py`

## SendGrid
- **Purpose**: Transactional email
- **Features**:
  - Subuser per tenant
  - Inbound Parse webhooks
  - Email templates
- **Config**: `SENDGRID_MASTER_API_KEY`, per-tenant subuser keys
- **Files**: `src/utils/email_sender.py`, `src/api/admin_sendgrid_routes.py`

## Google Cloud Storage (GCS)
- **Buckets**:
  - `zorah-faiss-index` - FAISS vector index (301MB index.faiss, 51MB index.pkl)
  - `zorah-475411-rag-documents` - Knowledge base documents
- **Files**: `src/services/faiss_helpdesk_service.py`, `src/api/admin_knowledge_routes.py`

## Google Vertex AI
- **Purpose**: LLM for email parsing
- **Model**: Gemini
- **Config**: `GCP_PROJECT_ID`
- **Files**: `src/api/onboarding_routes.py`

## Google BigQuery
- **Purpose**: Hotel database, analytics
- **Tables**: Hotels, rates, availability
- **Files**: `src/tools/bigquery_tool.py`

## VAPI
- **Purpose**: Voice AI
- **Config**: `VAPI_API_KEY`
- **Status**: Configured but minimal usage

## Twilio
- **Purpose**: SMS/WhatsApp
- **Config**: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`
- **Status**: Configured but minimal usage
