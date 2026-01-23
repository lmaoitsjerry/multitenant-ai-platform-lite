# Coding Conventions

**Analysis Date:** 2026-01-23

## Naming Patterns

**Files:**
- Python modules: `snake_case.py` (e.g., `auth_middleware.py`, `crm_service.py`)
- Test files: `test_{module_name}.py` (e.g., `test_auth_middleware.py`)
- Fixture files: `{domain}_fixtures.py` (e.g., `bigquery_fixtures.py`)

**Functions:**
- Use `snake_case` for functions: `get_client_config()`, `create_chainable_mock()`
- Async functions prefixed with operation: `async def get_user_by_auth_id()`
- Private functions prefixed with underscore: `_get_client_id_filter()`

**Variables:**
- Local variables: `snake_case` (e.g., `client_id`, `mock_config`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `PUBLIC_PATHS`, `TABLE_INVOICES`)
- Module-level caches: `_snake_case` (e.g., `_client_configs`, `_quote_agents`)

**Classes:**
- `PascalCase` for classes: `UserContext`, `AuthMiddleware`, `CRMService`
- Test classes: `Test{Feature}` (e.g., `TestAuthService`, `TestPublicPathDetection`)

**Types:**
- Enums: `PascalCase` with uppercase values: `PipelineStage.QUOTED`

## Code Style

**Formatting:**
- Tool: Black (version 24.8.0)
- Line length: 88 characters (Black default)
- Indentation: 4 spaces
- Strings: Double quotes preferred for docstrings, single or double for regular strings

**Linting:**
- Tool: flake8 (version 7.1.1)
- Type checking: mypy (version 1.11.2)
- No project-specific config files detected - using defaults

## Import Organization

**Order:**
1. Standard library imports
2. Third-party imports (fastapi, pydantic, etc.)
3. Local application imports

**Pattern from `src/api/routes.py`:**
```python
# Standard library
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum

# Third-party
from fastapi import APIRouter, HTTPException, Depends, Header, Query, Body, Request
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, Field

# Local imports
from config.loader import ClientConfig
from src.utils.error_handler import log_and_raise
from src.services.crm_service import CRMService, PipelineStage
```

**Path Aliases:**
- No path aliases configured
- Use relative imports from `src/` root: `from src.services.auth_service import AuthService`
- Config imports: `from config.loader import ClientConfig, get_config`

## Error Handling

**Patterns:**

Use `src/utils/error_handler.py` for consistent error responses:

```python
from src.utils.error_handler import log_and_raise, safe_error_response

# Pattern 1: Log and raise in one call (preferred)
try:
    # risky operation
except Exception as e:
    log_and_raise(500, "generating quote", e, logger)

# Pattern 2: Get HTTPException for more control
try:
    # risky operation
except HTTPException:
    raise  # Re-raise HTTP exceptions as-is
except Exception as e:
    raise safe_error_response(500, "processing request", e, logger)
```

**HTTP Exception Pattern:**
```python
# Always re-raise HTTPException before catching generic Exception
try:
    # operation
except HTTPException:
    raise
except Exception as e:
    log_and_raise(500, "operation description", e, logger)
```

**Security:** Never expose internal exception messages to clients. Use generic messages:
- 5xx errors: "An internal error occurred while {operation}. Please try again later."
- 4xx errors: "Error while {operation}. Please check your request and try again."

## Logging

**Framework:** Python `logging` module with structured JSON output

**Setup from `main.py`:**
```python
from src.utils.structured_logger import setup_structured_logging, get_logger

log_level = os.getenv("LOG_LEVEL", "INFO")
json_logs = os.getenv("JSON_LOGS", "true").lower() == "true"
setup_structured_logging(level=log_level, json_output=json_logs)
logger = get_logger(__name__)
```

**Patterns:**
- Create module-level logger: `logger = logging.getLogger(__name__)`
- Use f-strings for log messages: `logger.info(f"Created QuoteAgent for {config.client_id}")`
- Include context in brackets: `logger.info(f"[LIST_QUOTES] Returning {len(quotes)} quotes")`
- Log errors with exc_info: `logger.error(f"Failed to get client: {e}", exc_info=True)`

**Log Levels:**
- `DEBUG`: Detailed diagnostic info (e.g., query results)
- `INFO`: Normal operation events (e.g., service initialization)
- `WARNING`: Recoverable issues (e.g., fallback to default config)
- `ERROR`: Operation failures (always include exc_info=True)

## Comments

**When to Comment:**
- Module docstrings required at top of each file
- Class docstrings explaining purpose and usage
- Function docstrings for public APIs
- Inline comments for non-obvious logic

**Docstring Format (Google style):**
```python
def create_mock_bigquery_client(
    default_data: List[Dict[str, Any]] = None,
    preset_patterns: Dict[str, List[Dict[str, Any]]] = None
) -> MockBigQueryClient:
    """
    Create a configured MockBigQueryClient.

    Args:
        default_data: Default response for unmatched queries
        preset_patterns: Dict of pattern -> response data to pre-configure

    Returns:
        Configured MockBigQueryClient instance

    Example:
        client = create_mock_bigquery_client()
    """
```

**Section Headers:**
Use commented section headers for organization:
```python
# ==================== Configuration Fixtures ====================

# ==================== Public Paths ====================
```

## Function Design

**Size:** Functions should have single responsibility. Split large functions into helpers.

**Parameters:**
- Use type hints for all parameters: `def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:`
- Use `Optional[]` for nullable parameters
- Provide defaults where sensible: `limit: int = 50`

**Return Values:**
- Use type hints for returns
- Return `None` for "not found" cases (not empty dict)
- Return `{"success": True, "data": ...}` for API responses
- Return `bool` for operations that succeed/fail

## Module Design

**Exports:**
- Use `__all__` in `__init__.py` to explicitly list public exports
- See `tests/fixtures/__init__.py` for comprehensive example

**Service Pattern:**
```python
class CRMService:
    """Service class with dependency injection via config."""

    def __init__(self, config: ClientConfig):
        self.config = config
        self.supabase = None

        try:
            from src.tools.supabase_tool import SupabaseTool
            self.supabase = SupabaseTool(config)
        except Exception as e:
            logger.warning(f"Supabase not available: {e}")
```

**Caching Pattern:**
Module-level caches for expensive objects:
```python
# Global caches for performance
_client_configs = {}
_quote_agents = {}

def get_quote_agent(config: ClientConfig):
    """Get cached QuoteAgent for client"""
    if config.client_id not in _quote_agents:
        _quote_agents[config.client_id] = QuoteAgent(config)
    return _quote_agents[config.client_id]
```

## Pydantic Models

**Pattern for API request/response models:**
```python
from pydantic import BaseModel, EmailStr, Field

class TravelInquiry(BaseModel):
    """Travel inquiry for quote generation"""
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    destination: str
    adults: int = Field(default=2, ge=1, le=20)
    children_ages: Optional[List[int]] = None
```

## FastAPI Router Pattern

```python
from fastapi import APIRouter, HTTPException, Depends, Query

router = APIRouter(prefix="/api/v1/quotes", tags=["Quotes"])

@router.get("")
async def list_quotes(
    status: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    config: ClientConfig = Depends(get_client_config)
):
    """List quotes with optional filtering"""
    try:
        # implementation
        return {"success": True, "data": quotes, "count": len(quotes)}
    except Exception as e:
        log_and_raise(500, "listing quotes", e, logger)
```

## Middleware Pattern

Use Starlette BaseHTTPMiddleware:
```python
from starlette.middleware.base import BaseHTTPMiddleware

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Pre-processing
        if is_public_path(request.url.path):
            request.state.user = None
            return await call_next(request)

        # Authentication logic
        response = await call_next(request)
        # Post-processing
        return response
```

---

*Convention analysis: 2026-01-23*
