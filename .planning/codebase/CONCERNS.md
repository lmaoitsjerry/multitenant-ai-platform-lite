# Technical Concerns & Debt

## Performance Issues

### 1. FAISS Initialization on Startup
- **Location**: `main.py`, `faiss_helpdesk_service.py`
- **Issue**: FAISS loads 98K vectors on startup (~100 seconds)
- **Impact**: Slow cold starts on Cloud Run
- **Mitigation**: Service preloading, but still adds latency

### 2. Sentence Transformer Memory
- **Location**: `faiss_helpdesk_service.py:121`
- **Issue**: `all-mpnet-base-v2` model is large (~400MB)
- **Impact**: Paging file errors on low-memory systems
- **Status**: Handled with `local_files_only` fallback

### 3. Dashboard Loading
- **Issue**: Multiple API calls on mount
- **Areas**: Tenant dashboard, admin platform
- **Fix Needed**: Add caching, lazy loading

## Security Considerations

### 1. Hardcoded Admin Token
- **Location**: `src/api/admin_routes.py`
- **Issue**: Admin token is hardcoded
- **Recommendation**: Move to environment variable

### 2. API Keys in .env
- **Location**: `.env` file
- **Issue**: Contains production keys
- **Recommendation**: Use secret manager in production

## Code Quality

### 1. Missing Tests
- No automated test suite
- Manual testing only
- Risk: Regressions on changes

### 2. Error Handling Gaps
- Some endpoints return generic errors
- Stack traces occasionally leaked

## Incomplete Features

### 1. Invoice Payment Tracking
- `paid_at` field may not be set correctly
- Revenue calculations may show $0

### 2. Knowledge Base Management
- Only 3 test documents in manageable bucket
- FAISS index is read-only (no rebuild from UI)

## TODO Comments Found
- Various cleanup tasks scattered in code
- WeasyPrint library issues (fallback to fpdf2)
