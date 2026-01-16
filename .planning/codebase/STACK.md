# Tech Stack

## Languages
- **Python 3.11+** - Backend API
- **JavaScript/TypeScript** - Frontend (React)

## Backend Framework
- **FastAPI** - Main API framework
- **Uvicorn** - ASGI server
- **Pydantic** - Data validation

## Frontend Frameworks
- **React 18** - UI framework
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **React Router** - Navigation

## Database
- **Supabase (PostgreSQL)** - Primary database
- **Row Level Security** - Multi-tenant isolation

## Vector Search
- **FAISS** - Vector similarity search
- **sentence-transformers** - Embeddings (all-mpnet-base-v2, 768-dim)
- **LangChain** - Document store format

## Key Dependencies

### Backend (requirements.txt)
- `fastapi` - API framework
- `uvicorn` - Server
- `supabase` - Database client
- `google-cloud-storage` - GCS integration
- `google-cloud-bigquery` - Analytics
- `sendgrid` - Email
- `faiss-cpu` - Vector search
- `sentence-transformers` - Embeddings
- `langchain-community` - Document loaders
- `fpdf2` - PDF generation

### Frontend (package.json)
- `react` - UI
- `react-router-dom` - Routing
- `axios` - HTTP client
- `@heroicons/react` - Icons
- `recharts` - Charts
- `tailwindcss` - Styling
