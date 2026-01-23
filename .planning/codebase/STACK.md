# Technology Stack

**Analysis Date:** 2026-01-23

## Languages

**Primary:**
- Python 3.11+ - Backend API, AI agents, services, tools

**Secondary:**
- JavaScript/TypeScript (ES Modules) - Frontend React applications
- SQL - Database migrations, BigQuery analytics

## Runtime

**Environment:**
- Python 3.11 (specified in `pyproject.toml` and `Dockerfile`)
- Node.js (for frontend build tools)

**Package Manager:**
- pip (Python)
- Lockfile: Not present (uses `requirements.txt`)
- npm/yarn (JavaScript - lockfiles present in frontend)

## Frameworks

**Core:**
- FastAPI 0.115.4 - REST API framework (`main.py`, `src/api/`)
- Uvicorn 0.32.0 - ASGI server
- Pydantic 2.12.3 - Data validation and serialization
- Pydantic Settings 2.11.0 - Configuration management

**AI/ML:**
- LangChain 1.0.7 - AI orchestration framework
- LangChain OpenAI 1.0.3 - OpenAI integration
- LangChain Google VertexAI 3.0.3 - Vertex AI integration
- OpenAI 2.8.0 - GPT models for email parsing, helpdesk
- FAISS-CPU 1.7.4+ - Vector search for knowledge base
- Sentence Transformers 2.2.0+ - Embeddings (768-dim all-mpnet-base-v2)

**Testing:**
- pytest 8.3.0 - Test framework
- pytest-asyncio 0.24.0 - Async test support
- pytest-cov 6.0.0 - Coverage reporting

**Build/Dev:**
- Vite 7.2.x - Frontend build tool
- Docker - Container builds (`Dockerfile`)
- GitHub Actions - CI/CD (`ci.yml`, `deploy.yml`)

**Frontend (React Apps):**
- React 19.x - UI framework
- React Router DOM 7.x - Client-side routing
- Tailwind CSS 4.x (tenant-dashboard), 3.x (internal-admin) - Styling
- Axios 1.x - HTTP client
- Recharts 3.x - Charts and analytics
- Headless UI 2.x - Accessible components
- Heroicons 2.x - Icon library

## Key Dependencies

**Critical:**
- `supabase>=2.9.0` - Database client and auth
- `google-cloud-bigquery==3.26.0` - Analytics and hotel pricing data
- `google-cloud-storage==2.18.2` - FAISS index storage, document storage
- `google-cloud-aiplatform==1.127.0` - Vertex AI RAG (optional)
- `sendgrid==6.12.5` - Email delivery (quotes, invoices)
- `slowapi>=0.1.9` - Rate limiting
- `redis>=5.0.0` - Rate limit backend

**Infrastructure:**
- `google-auth==2.41.1` - GCP authentication
- `google-cloud-pubsub==2.33.0` - Event messaging
- `google-cloud-tasks>=2.16.0` - Background task scheduling

**Document Processing:**
- `weasyprint==66.0` - PDF generation (quotes, invoices)
- `pdfplumber==0.11.0` - PDF text extraction
- `pypdf==5.1.0` - PDF manipulation
- `jinja2==3.1.4` - HTML templating for PDFs
- `pillow==12.0.0` - Image processing

**Data Processing:**
- `pandas>=2.0.0` - Data manipulation
- `openpyxl==3.1.2` - Excel file support
- `pyarrow==21.0.0` - Parquet/Arrow support

**Utilities:**
- `pyyaml==6.0.1` - YAML config loading
- `jsonschema==4.23.0` - Config validation
- `python-dotenv==1.0.0` - Environment variables
- `tenacity==8.5.0` - Retry logic
- `requests==2.32.5` - HTTP client

**Security:**
- `PyJWT` (via supabase) - JWT token handling
- `gotrue` (via supabase) - Auth API errors

## Configuration

**Environment:**
- `.env` file at project root (loaded via `python-dotenv`)
- Client configs in `clients/{tenant_id}/client.yaml`
- Database settings in `tenant_settings` table (Supabase)

**Key Environment Variables:**
```
# Required
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=xxx
SUPABASE_SERVICE_KEY=xxx
GCP_PROJECT_ID=xxx
OPENAI_API_KEY=xxx
SENDGRID_MASTER_API_KEY=xxx

# Optional
SUPABASE_JWT_SECRET=xxx  # For JWT verification
VAPI_API_KEY=xxx         # Voice AI
TWILIO_ACCOUNT_SID=xxx   # Phone provisioning
TWILIO_AUTH_TOKEN=xxx
REDIS_URL=xxx            # Rate limiting
LOG_LEVEL=INFO
JSON_LOGS=true
CORS_ORIGINS=xxx
```

**Build:**
- `pyproject.toml` - Python project config, pytest settings, coverage config
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container build (Python 3.11-slim base)
- `railway.json` - Railway deployment config
- `render.yaml` - Render deployment config

## Platform Requirements

**Development:**
- Python 3.11+
- Node.js (for frontend builds)
- Docker (for containerized testing)
- GCP credentials (service account JSON or Application Default Credentials)

**Production:**
- Docker container runtime
- 2GB+ memory recommended
- GCP Cloud Run (primary) or Railway/Render

**Deployment Targets:**
- Google Cloud Run (primary - `deploy.yml`)
- Railway (alternative - `railway.json`)
- Render (alternative - `render.yaml`)

## Code Quality Tools

**Linting:**
- flake8 7.1.1 - Python linting
- ESLint 9.x - JavaScript/React linting

**Formatting:**
- black 24.8.0 - Python code formatter
- Prettier (via ESLint) - JavaScript formatting

**Type Checking:**
- mypy 1.11.2 - Python static type checking

## Test Configuration

**Pytest Settings (`pyproject.toml`):**
```toml
testpaths = ["tests"]
python_files = ["test_*.py"]
asyncio_mode = "auto"
addopts = "-v --tb=short"
```

**Coverage:**
- Source: `src/`, `main.py`, `config/`
- Threshold: 57% (enforced in CI)
- HTML reports: `htmlcov/`

---

*Stack analysis: 2026-01-23*
