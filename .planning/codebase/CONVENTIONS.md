# Coding Conventions

## File Naming
- Python: `snake_case.py`
- React components: `PascalCase.jsx`
- CSS/Tailwind: Component-specific classes

## Function Naming
- Python: `snake_case`
- JavaScript: `camelCase`
- React components: `PascalCase`

## API Routes
- Pattern: `/api/v1/{domain}/{action}`
- Admin routes: `/api/v1/admin/{domain}/{action}`
- Webhooks: `/api/webhooks/{service}`

## Import Organization (Python)
```python
# Standard library
import os
import logging

# Third-party
from fastapi import APIRouter, Depends
from pydantic import BaseModel

# Local
from config.loader import ClientConfig
from src.services.auth_service import AuthService
```

## Error Handling
- FastAPI HTTPException for API errors
- Logging with `logger.error()` for debugging
- Try/except blocks with specific error handling

## Logging Pattern
```python
logger = logging.getLogger(__name__)
logger.info("Operation started")
logger.error(f"Failed: {e}", exc_info=True)
```

## Response Format
```python
{
    "success": True,
    "data": {...},
    "message": "Optional message"
}
```

## Authentication Headers
- `Authorization: Bearer <jwt_token>` - User auth
- `X-Client-ID: <tenant_id>` - Tenant context
- `X-Admin-Token: <admin_token>` - Admin auth
