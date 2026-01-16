# Architecture

## Multi-Tenant Pattern
- **Tenant Isolation**: X-Client-ID header identifies tenant
- **Database**: Row-level security in Supabase
- **Config**: Per-tenant config files in `config/clients/`
- **SendGrid**: Subuser per tenant for email isolation

## Layers

### API Layer (`src/api/`)
- FastAPI routers
- Request validation (Pydantic)
- Response formatting
- Auth middleware

### Service Layer (`src/services/`)
- Business logic
- External API integrations
- Caching

### Tools Layer (`src/tools/`)
- Database tools (Supabase, BigQuery)
- PDF generation
- Email sending

### Agents Layer (`src/agents/`)
- AI-powered workflows
- Quote generation
- Email parsing

## Request Flow
```
Request → Auth Middleware → Rate Limiter → Router → Service → Database → Response
```

## Authentication Flow
1. User logs in via `/api/v1/auth/login`
2. Supabase returns JWT tokens
3. Frontend stores in localStorage
4. Subsequent requests include `Authorization: Bearer <token>`
5. Auth middleware validates JWT and sets `request.state.user`

## Key Patterns
- Singleton services (FAISS, config loaders)
- Dependency injection via FastAPI `Depends()`
- Background tasks for async operations
- In-memory caching with TTL
