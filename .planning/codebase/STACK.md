# Technology Stack

**Analysis Date:** 2025-01-23

## Languages

**Primary:**
- Python 3.11+ - Backend API and all business logic

**Secondary:**
- SQL - BigQuery queries for hotel rates and analytics
- YAML - Tenant configuration files (`clients/{tenant}/client.yaml`)
- JSON - Configuration schemas and API responses
- Jinja2 - HTML email and PDF templates

## Runtime

**Environment:**
- Python 3.11 (required: `>=3.11` in `pyproject.toml`)
- Runs on Docker (Python 3.11-slim base image)

**Package Manager:**
- pip with `requirements.txt`
- Lockfile: Not present (uses pinned versions in requirements.txt)

## Frameworks

**Core:**
- FastAPI 0.115.4 - REST API framework
- Uvicorn 0.32.0 - ASGI server
- Pydantic 2.12.3 - Data validation and settings

**AI/LLM:**
- LangChain 1.0.7 - LLM orchestration
- LangChain-OpenAI 1.0.3 - OpenAI integration
- LangChain-Google-VertexAI 3.0.3 - Google AI integration
- OpenAI 2.8.0 - GPT models for email parsing and helpdesk

**Vector Search:**
- FAISS-CPU >=1.7.4 - Vector similarity search
- Sentence-Transformers >=2.2.0 - Embeddings (all-mpnet-base-v2, 768-dim)

**Testing:**
- pytest 8.3.0 - Test framework
- pytest-asyncio 0.24.0 - Async test support
- pytest-cov 6.0.0 - Coverage reporting

**Build/Dev:**
- Docker - Containerization (`Dockerfile`)
- GitHub Actions - CI/CD (`.github/workflows/ci.yml`)
- black 24.8.0 - Code formatting
- flake8 7.1.1 - Linting
- mypy 1.11.2 - Type checking

## Key Dependencies

**Critical:**
- `supabase >=2.9.0` - Primary database client (PostgreSQL via Supabase)
- `google-cloud-bigquery 3.26.0` - Analytics and hotel pricing data
- `google-cloud-storage 2.18.2` - FAISS index storage
- `sendgrid 6.12.5` - Transactional email delivery
- `openai 2.8.0` - LLM for email parsing and responses

**Infrastructure:**
- `slowapi >=0.1.9` - Rate limiting
- `redis >=5.0.0` - Rate limit storage (optional)
- `tenacity 8.5.0` - Retry logic with exponential backoff
- `pyyaml 6.0.1` - YAML configuration parsing
- `python-dotenv 1.0.0` - Environment variable loading
- `pyjwt` (via supabase) - JWT token handling

**Document Processing:**
- `weasyprint 66.0` - PDF generation for quotes/invoices
- `pdfplumber 0.11.0` - PDF text extraction
- `pypdf 5.1.0` - PDF manipulation
- `pillow 12.0.0` - Image processing
- `pandas >=2.0.0` - Data manipulation
- `openpyxl 3.1.2` - Excel file handling

## Configuration

**Environment Variables:**
Required variables loaded from `.env`:
- `PORT` - Server port (default: 8000)
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_ANON_KEY` - Supabase anonymous key
- `SUPABASE_SERVICE_KEY` - Supabase service role key
- `GCP_PROJECT_ID` - Google Cloud project ID
- `OPENAI_API_KEY` - OpenAI API key for FAISS embeddings
- `SENDGRID_MASTER_API_KEY` - Master SendGrid API key
- `VAPI_API_KEY` - Voice AI API key
- `TWILIO_ACCOUNT_SID` - Twilio account SID
- `TWILIO_AUTH_TOKEN` - Twilio auth token

Optional:
- `CORS_ORIGINS` - Comma-separated allowed origins
- `LOG_LEVEL` - Logging level (default: INFO)
- `JSON_LOGS` - Enable JSON logging (default: true)
- `PII_AUDIT_ENABLED` - Enable PII audit logging (default: true)
- `SUPABASE_JWT_SECRET` - JWT signature verification (production)
- `FAISS_BUCKET_NAME` - GCS bucket for FAISS index
- `FAISS_INDEX_PREFIX` - GCS path prefix for index files

**Build Configuration:**
- `pyproject.toml` - pytest configuration, coverage settings
- `Dockerfile` - Production container build
- `.github/workflows/ci.yml` - CI pipeline configuration

**Tenant Configuration:**
- Per-tenant YAML files: `clients/{tenant_id}/client.yaml`
- Schema validation: `config/schema.json`
- Database override: `tenant_settings` table in Supabase

## Platform Requirements

**Development:**
- Python 3.11+
- pip
- Docker (optional, for containerized development)
- Access to Supabase project
- GCP project with BigQuery and Cloud Storage

**Production:**
- Docker container (python:3.11-slim based)
- Non-root user (uid 1000) for security
- System dependencies: libpango, libgdk-pixbuf, curl (for WeasyPrint)
- Health check endpoint: `/health`
- Readiness probe: `/health/ready`
- Liveness probe: `/health/live`

**Deployment Targets:**
- Railway (configured in `railway.json`)
- Render (configured in `render.yaml`)
- Any container platform supporting Docker

---

*Stack analysis: 2025-01-23*
