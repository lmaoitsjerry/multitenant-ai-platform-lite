# Technology Stack

**Analysis Date:** 2026-01-16

## Languages

**Primary:**
- Python 3.x - Backend API, AI agents, services
- JavaScript/JSX - Frontend React applications

**Secondary:**
- SQL - Database migrations and queries
- HTML/CSS - PDF templates, email templates

## Runtime

**Environment:**
- Python 3.x (no .python-version specified)
- Node.js (for frontend builds)

**Package Manager:**
- pip (Python) - `requirements.txt` present
- npm (JavaScript) - `package.json` in frontend directories
- Lockfile: No `requirements.lock`, `package-lock.json` present in node_modules

## Frameworks

**Core:**
- FastAPI 0.115.4 - Python async web framework
- React 19.x - Frontend UI framework
- Pydantic 2.12.3 - Data validation and settings

**Testing:**
- pytest 8.3.0 - Python test runner
- pytest-asyncio 0.24.0 - Async test support
- pytest-cov 6.0.0 - Coverage reporting

**Build/Dev:**
- Vite 7.2.x - Frontend build tool and dev server
- uvicorn 0.32.0 - ASGI server
- Tailwind CSS 4.1.18 / 3.4.17 - Utility-first CSS

## Key Dependencies

**AI/LLM:**
- langchain 1.0.7 - LLM orchestration
- langchain-openai 1.0.3 - OpenAI integration
- langchain-google-vertexai 3.0.3 - Vertex AI integration
- openai 2.8.0 - OpenAI API client
- sentence-transformers >=2.2.0 - Local embeddings (768-dim)

**Google Cloud:**
- google-cloud-bigquery 3.26.0 - Analytics/pricing data
- google-cloud-storage 2.18.2 - File storage
- google-cloud-aiplatform 1.127.0 - Vertex AI RAG
- google-cloud-pubsub 2.33.0 - Message queues
- google-cloud-tasks >=2.16.0 - Task scheduling

**Database:**
- supabase >=2.9.0 - PostgreSQL client + Auth
- postgrest >=0.17.0 - REST API for Postgres

**Vector Search:**
- faiss-cpu >=1.7.4 - Local vector similarity search

**Document Processing:**
- weasyprint 66.0 - HTML to PDF (primary)
- fpdf2 - PDF fallback for Windows
- pdfplumber 0.11.0 - PDF text extraction
- pypdf 5.1.0 - PDF manipulation
- jinja2 3.1.4 - Template rendering

**Email:**
- sendgrid 6.12.5 - Transactional email
- python-http-client 3.3.7 - HTTP client

**Data Processing:**
- pandas >=2.0.0 - Data analysis
- openpyxl 3.1.2 - Excel files
- pyarrow 21.0.0 - Columnar data format

**Frontend (Tenant Dashboard):**
- react 19.2.0 - UI library
- react-router-dom 7.10.1 - Client routing
- axios 1.13.2 - HTTP client
- recharts 3.5.1 - Charts/visualization
- @headlessui/react 2.2.9 - Accessible components
- @heroicons/react 2.2.0 - Icons
- @dnd-kit/* - Drag and drop
- date-fns 4.1.0 - Date utilities

**Frontend (Internal Admin):**
- react 19.1.0 - UI library
- react-router-dom 7.5.2 - Client routing
- axios 1.7.9 - HTTP client

**Code Quality:**
- black 24.8.0 - Python formatter
- flake8 7.1.1 - Python linter
- mypy 1.11.2 - Type checker
- eslint 9.39.1 - JavaScript linter

## Configuration

**Environment:**
- `.env` file at project root (present, not committed)
- `python-dotenv 1.0.0` for loading env vars
- Environment variable substitution in YAML configs: `${VAR_NAME}` or `${VAR_NAME:-default}`

**Key Environment Variables:**
- `SENDGRID_API_KEY` - Email service
- `OPENAI_API_KEY` - AI services
- `SUPABASE_URL` - Database URL
- `SUPABASE_SERVICE_KEY` / `SUPABASE_KEY` - Database auth
- `FAISS_BUCKET_NAME` - GCS bucket for FAISS index (default: `zorah-faiss-index`)
- `LOG_LEVEL` - Logging verbosity (default: INFO)
- `PORT` - Server port (default: 8080)
- `HOST` - Server host (default: 127.0.0.1)
- `CORS_ORIGINS` - Allowed CORS origins
- `PII_AUDIT_ENABLED` - GDPR/POPIA compliance logging

**Build Configuration:**
- `vite.config.js` - Frontend build config (minimal, uses @vitejs/plugin-react)
- `postcss.config.js` - PostCSS/Tailwind config
- `config/schema.json` - JSON Schema for client YAML validation

**Multi-Tenant Configuration:**
- Per-tenant YAML config in `clients/{tenant_id}/client.yaml`
- Schema validated against `config/schema.json`
- Loaded via `config/loader.py` with caching

## Platform Requirements

**Development:**
- Python 3.x
- Node.js (for frontend)
- GTK3 runtime (for WeasyPrint PDF generation, optional on Windows)

**Production:**
- Docker support via `Dockerfile`
- Railway (`railway.json`)
- Render (`render.yaml`)
- Any ASGI-compatible hosting

**Database:**
- Supabase (PostgreSQL) for operational data
- Google BigQuery for analytics/pricing data

---

*Stack analysis: 2026-01-16*
