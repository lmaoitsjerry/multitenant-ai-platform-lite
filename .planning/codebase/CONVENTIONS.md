# Coding Conventions

**Analysis Date:** 2026-01-23

## Naming Patterns

**Files:**
- `snake_case.py` for Python modules: `crm_service.py`, `quote_agent.py`, `auth_middleware.py`
- `test_*.py` for test files: `test_crm_service.py`, `test_api_routes.py`
- Routes named by domain: `{domain}_routes.py` (e.g., `pricing_routes.py`, `branding_routes.py`)
- Services named by domain: `{domain}_service.py` (e.g., `crm_service.py`, `auth_service.py`)

**Functions:**
- `snake_case` for all functions: `get_client()`, `create_invoice()`, `verify_jwt()`
- Async functions prefixed with context: `async def list_quotes()`, `async def get_pipeline()`
- Private helpers prefixed with underscore: `_get_client_id_filter()`, `_count_by_field()`

**Variables:**
- `snake_case` for local variables and parameters: `client_id`, `tenant_id`, `quote_data`
- ALL_CAPS for constants: `PUBLIC_PATHS`, `TABLE_QUOTES`, `DEFAULT_QUERY_TIMEOUT`
- Protected attributes with underscore: `_config_source`, `_executor`

**Types:**
- `PascalCase` for classes: `CRMService`, `QuoteAgent`, `SupabaseTool`, `UserContext`
- `PascalCase` for Pydantic models: `TravelInquiry`, `ClientCreate`, `InvoiceStatusUpdate`
- `PascalCase` for Enums: `PipelineStage`, `PipelineStageEnum`

**API Routes:**
- Kebab-case for multi-word paths: `/api/v1/convert-quote`, `/api/v1/sendgrid-inbound`
- Plural nouns for collections: `/api/v1/quotes`, `/api/v1/invoices`, `/api/v1/clients`
- Nested resources for relationships: `/api/v1/clients/{client_id}/activities`

## Code Style

**Formatting:**
- Tool: `black` (version 24.8.0)
- Line length: 88 characters (black default)
- Indentation: 4 spaces

**Linting:**
- Tool: `flake8` (version 7.1.1)
- Type checking: `mypy` (version 1.11.2)
- No explicit configuration files detected - using tool defaults

## Import Organization

**Order:**
1. Standard library imports
2. Third-party imports (FastAPI, Pydantic, etc.)
3. Local imports (config, src modules)

**Pattern observed in `src/api/routes.py`:**
```python
# 1. Standard library
import logging
from functools import lru_cache
from datetime import datetime, date
from enum import Enum

# 2. Third-party
from fastapi import APIRouter, HTTPException, Depends, Header, Query, Body, Request
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any

# 3. Local
from config.loader import ClientConfig
from src.utils.error_handler import log_and_raise
from src.services.crm_service import CRMService, PipelineStage
```

**Path Aliases:**
- No path aliases configured (tsconfig.json not used - Python project)
- Direct relative imports: `from src.services.crm_service import CRMService`
- Config imports: `from config.loader import ClientConfig, get_config`

## Error Handling

**Patterns:**

1. **Centralized Error Handler** (`src/utils/error_handler.py`):
```python
from src.utils.error_handler import log_and_raise, safe_error_response

try:
    result = agent.generate_quote(...)
except HTTPException:
    raise  # Re-raise HTTPException as-is
except Exception as e:
    log_and_raise(500, "generating quote", e, logger)
```

2. **Security-Conscious Error Messages:**
- Internal details logged for debugging: `logger.error(f"{operation} failed: {exception}", exc_info=True)`
- Generic messages returned to clients: `"An internal error occurred while {operation}. Please try again later."`
- Never expose stack traces or internal paths to API consumers

3. **Supabase Operation Pattern:**
```python
if not self.client:
    return None  # Graceful degradation

try:
    result = self.client.table(...).execute()
    if result.data:
        return result.data[0]
    return None
except Exception as e:
    logger.error(f"Failed to {operation}: {e}")
    return None
```

4. **Timeout Protection** (`src/tools/supabase_tool.py`):
```python
def execute_with_timeout(self, query_func, timeout=10, operation="query"):
    try:
        future = self._executor.submit(query_func)
        result = future.result(timeout=timeout)
        return result
    except FuturesTimeoutError:
        raise TimeoutError(f"Query '{operation}' timed out after {timeout}s")
```

## Logging

**Framework:** Python `logging` module with structured JSON output

**Setup** (`src/utils/structured_logger.py`):
```python
from src.utils.structured_logger import setup_structured_logging, get_logger

setup_structured_logging(level="INFO", json_output=True)
logger = get_logger(__name__)
```

**Patterns:**
- Request ID propagation via `contextvars` (async-safe)
- All log entries include: `timestamp`, `level`, `logger`, `message`, `request_id`, `service`
- Slow query warnings for operations exceeding 3 seconds
- Log levels used:
  - `logger.debug()` - Detailed information for debugging
  - `logger.info()` - Operational events (client created, quote generated)
  - `logger.warning()` - Non-critical issues (FAISS not available, cache miss)
  - `logger.error()` - Operation failures with `exc_info=True` for stack traces

**Standard Log Format:**
```python
logger.info(f"[LIST_QUOTES] Returning {len(quotes)} quotes for tenant {config.client_id}")
logger.error(f"Failed to create invoice: {e}", exc_info=True)
```

## Comments

**When to Comment:**
- Module docstrings at top of every file explaining purpose and usage
- Class docstrings explaining responsibility
- Function docstrings for public APIs with Args/Returns sections
- Inline comments for non-obvious business logic
- Security notes for sensitive operations

**JSDoc/TSDoc (Docstring Pattern):**
```python
def get_or_create_client(
    self,
    email: str,
    name: str,
    phone: Optional[str] = None,
    source: str = "manual",
    consultant_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Get existing client or create new one
    New clients start in QUOTED stage
    """
```

**Security Comments Pattern:**
```python
# SECURITY NOTE: The X-Client-ID header is initially trusted to load tenant config.
# After JWT verification and user lookup, we validate that the header matches
# the user's actual tenant_id. This prevents tenant spoofing attacks.
```

## Function Design

**Size:**
- Most functions under 50 lines
- Complex functions like `search_clients()` up to 100 lines (acceptable for batch operations)

**Parameters:**
- Required parameters first, optional with defaults after
- Use `Optional[Type]` for nullable parameters
- Common pattern: `(config: ClientConfig, **kwargs)`

**Return Values:**
- Single items: Return `Optional[Dict]` (None on failure/not found)
- Collections: Return `List[Dict]` (empty list on failure)
- Operations: Return `bool` (True on success)
- Complex results: Return `Dict[str, Any]` with success indicator

**Response Pattern for API routes:**
```python
return {
    "success": True,
    "data": result,
    "count": len(result) if isinstance(result, list) else None
}
```

## Module Design

**Exports:**
- Classes and functions exported at module level
- No `__all__` declarations (implicit exports)

**Barrel Files:**
- `src/api/__init__.py`, `src/services/__init__.py` exist but are minimal
- Direct imports preferred: `from src.services.crm_service import CRMService`

**Service Pattern:**
```python
class CRMService:
    def __init__(self, config: ClientConfig):
        self.config = config
        self.tenant_id = config.client_id
        # Initialize dependencies
```

**Caching Pattern:**
```python
@lru_cache(maxsize=100)
def _get_cached_config(client_id: str) -> ClientConfig:
    """Thread-safe via lru_cache"""
    return ClientConfig(client_id)
```

## Pydantic Model Patterns

**Request Models:**
```python
class TravelInquiry(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    destination: str
    adults: int = Field(default=2, ge=1, le=20)
```

**Response Models** (`src/utils/response_models.py`):
```python
class APIResponse(BaseModel):
    success: bool = True
    data: Optional[Any] = None
    message: Optional[str] = None
    error: Optional[str] = None
```

## Multi-Tenancy Patterns

**Tenant Identification:**
- Header: `X-Client-ID` for tenant context
- Always filter by `tenant_id` in database queries
- Validate header matches JWT user's tenant

**Tenant Isolation in Queries:**
```python
result = self.client.table('clients')\
    .select("*")\
    .eq('tenant_id', self.config.client_id)\  # Always filter
    .eq('email', email)\
    .execute()
```

## Constants and Configuration

**Table Constants:**
```python
class SupabaseTool:
    TABLE_QUOTES = "quotes"
    TABLE_INVOICES = "invoices"
    TABLE_CLIENTS = "clients"
```

**Public Paths:**
```python
PUBLIC_PATHS = {
    "/",
    "/health",
    "/api/v1/auth/login",
    "/api/v1/branding",
}
```

---

*Convention analysis: 2026-01-23*
