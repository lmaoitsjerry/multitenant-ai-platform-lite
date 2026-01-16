# Testing Setup

## Backend Testing
- **Framework**: pytest (not extensively used)
- **Test Location**: No dedicated test directory observed
- **Coverage**: Minimal automated tests

## Frontend Testing
- **Framework**: Jest/Vitest (available via Vite)
- **Test Location**: No test files observed
- **Coverage**: No automated tests

## Manual Testing Approach
The codebase uses manual testing via:
- Curl commands for API testing
- Browser DevTools for frontend
- Server logs for debugging

## Test Endpoints
- `/api/v1/helpdesk/test-search` - FAISS search testing
- `/api/v1/helpdesk/faiss-status` - Service status
- `/health` - Health check

## Recommended Test Coverage
Areas that would benefit from tests:
1. Auth flow (login, token refresh)
2. Multi-tenant isolation
3. FAISS search accuracy
4. Email webhook processing
5. Quote generation flow
