# Coding Conventions

**Analysis Date:** 2025-01-16

## Naming Patterns

**Python Files:**
- snake_case for modules: `quote_agent.py`, `auth_service.py`, `rate_limiter.py`
- Prefix with domain: `admin_routes.py`, `crm_service.py`, `bigquery_tool.py`

**Python Functions:**
- snake_case: `generate_quote()`, `get_client_by_email()`, `_normalize_customer_data()`
- Private methods prefixed with underscore: `_make_key()`, `_clean_expired()`

**Python Classes:**
- PascalCase: `QuoteAgent`, `ClientConfig`, `RateLimiter`, `DatabaseTables`
- Pydantic models: `VAPIProvisionRequest`, `TenantConfigUpdate`

**Python Variables:**
- snake_case: `customer_data`, `quote_id`, `hotel_options`
- Constants: UPPER_SNAKE_CASE: `ACCESS_TOKEN_KEY`, `CACHE_TTL`, `DEFAULT_REQUESTS_PER_MINUTE`

**React Files:**
- PascalCase for components: `Dashboard.jsx`, `QuoteDetail.jsx`, `AuthContext.jsx`
- camelCase for utilities: `api.js`, `usePrefetch.js`

**React Components:**
- PascalCase: `StatCard`, `QuickAction`, `SkeletonTable`
- Hooks: `useApp()`, `useAuth()`, prefix with `use`

**React Variables:**
- camelCase: `dashboardData`, `isStale`, `sidebarExpanded`
- State setters: `setUser`, `setLoading`, `setSidebarOpen`

## Code Style

**Python Formatting:**
- No explicit formatter configured (recommend adding `black` or `ruff`)
- 4-space indentation (standard Python)
- Max line length: ~100-120 chars (implicit)

**Python Linting:**
- No linter configured (recommend adding `flake8` or `ruff`)

**JavaScript/React Formatting:**
- No Prettier configured
- Uses ESLint with React hooks plugin
- Config: `frontend/tenant-dashboard/eslint.config.js`

**JavaScript Linting:**
- ESLint 9.x with flat config
- React hooks recommended rules
- React Refresh plugin for Vite HMR
- Rule: `no-unused-vars` ignores capitalized variables (component patterns)

## Import Organization

**Python Import Order:**
1. Standard library imports (`os`, `logging`, `uuid`, `datetime`)
2. Third-party imports (`fastapi`, `pydantic`, `jwt`)
3. Local imports (`config.loader`, `src.services`, `src.tools`)

**Python Example:**
```python
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from config.loader import ClientConfig
from src.tools.supabase_tool import SupabaseTool
```

**React Import Order:**
1. React core imports
2. React Router imports
3. Third-party libraries
4. Local contexts
5. Local components
6. Local services/utilities

**React Example:**
```jsx
import { useState, useEffect, useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { DocumentTextIcon, UsersIcon } from '@heroicons/react/24/outline';
import { useApp } from '../context/AppContext';
import { dashboardApi, quotesApi } from '../services/api';
```

**Path Aliases:**
- None configured (use relative paths)
- Common pattern: `../context/`, `../services/`, `../../components/`

## Error Handling

**Python API Routes:**
```python
try:
    # Business logic
    result = service.do_something()
    return {"success": True, "data": result}
except SomeSpecificError as e:
    logger.error(f"Specific error: {e}")
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail=str(e))
```

**Python Services:**
```python
try:
    # Service logic
    return result
except Exception as e:
    logger.error(f"Failed to {action}: {e}")
    return None  # or empty dict/list
```

**React API Calls:**
```jsx
try {
  const response = await api.someMethod();
  if (response.data?.success) {
    setData(response.data.data);
  }
} catch (error) {
  console.error('Operation failed:', error);
  // Often silently fail or show error state
}
```

**React API Service Pattern:**
```javascript
export const someApi = {
  action: async () => {
    try {
      const response = await api.post('/endpoint');
      return response;
    } catch (error) {
      return { data: { success: false, error: error.message } };
    }
  },
};
```

## Logging

**Python Framework:** Standard `logging` module

**Logger Setup:**
```python
import logging
logger = logging.getLogger(__name__)
```

**Log Levels Used:**
- `logger.info()`: Normal operations, state changes
- `logger.warning()`: Recoverable issues, fallbacks
- `logger.error()`: Failures, exceptions

**Pattern Examples:**
```python
logger.info(f"Quote {quote_id} generated successfully")
logger.warning(f"Supabase not available: {e}")
logger.error(f"Failed to save quote to Supabase: {e}")
```

**React/JavaScript:**
- Uses `console.log()`, `console.debug()`, `console.error()`
- Debug messages use prefix: `console.log('[Auth] Initializing...')`
- Cache operations use `console.debug()`

## Comments

**Python Docstrings:**
- Multi-line docstrings for classes and public methods
- Brief description, Args section, Returns section

```python
def generate_quote(
    self,
    customer_data: Dict[str, Any],
    send_email: bool = True,
) -> Dict[str, Any]:
    """
    Generate a complete quote for customer

    Args:
        customer_data: Customer travel requirements
        send_email: Whether to send quote email

    Returns:
        Dict with quote details and status
    """
```

**Module Headers:**
```python
"""
Quote Agent - Multi-Tenant Version

Orchestrates the full quote generation flow:
1. Parse customer requirements
2. Find matching hotels
...

Usage:
    from config.loader import ClientConfig
    from src.agents.quote_agent import QuoteAgent
    ...
"""
```

**React/JSX Comments:**
- JSDoc for complex components/functions
- Inline comments for non-obvious logic

```jsx
/**
 * Skeleton Loading Components
 *
 * Provides visual placeholders while content is loading,
 * creating a smoother perceived loading experience.
 */
```

## Function Design

**Python Functions:**
- Use type hints for parameters and return values
- Default parameters for optional behavior
- Return dictionaries with `success` boolean for API responses

```python
def get_client(
    self,
    client_id: str,
    include_activities: bool = False
) -> Optional[Dict[str, Any]]:
```

**Python API Response Pattern:**
```python
return {
    'success': True,
    'data': result,
    'message': 'Operation completed'
}
```

**React Hooks:**
- Use `useState` for local state
- Use `useEffect` for side effects with proper dependencies
- Use `useMemo` for expensive computations
- Use `useCallback` for stable function references

```jsx
const loadDashboard = useCallback(async (isBackgroundRefresh = false) => {
  // ...implementation
}, [dashboardData]);
```

## Module Design

**Python Modules:**
- Single responsibility per module
- Class-based services with `__init__` accepting `ClientConfig`
- Standalone utility functions for simple operations

**Service Pattern:**
```python
class SomeService:
    def __init__(self, config: ClientConfig):
        self.config = config
        self.db = DatabaseTables(config)
        # Initialize dependencies
```

**React Context Pattern:**
```jsx
const SomeContext = createContext(null);

export function SomeProvider({ children }) {
  const [state, setState] = useState(null);

  const value = {
    state,
    action: () => { /* ... */ },
  };

  return (
    <SomeContext.Provider value={value}>
      {children}
    </SomeContext.Provider>
  );
}

export function useSome() {
  const context = useContext(SomeContext);
  if (!context) {
    throw new Error('useSome must be used within SomeProvider');
  }
  return context;
}
```

**React API Module Pattern (api.js):**
- Single axios instance with interceptors
- Domain-specific API objects: `quotesApi`, `crmApi`, `invoicesApi`
- Caching built into API methods
- Export named functions and default axios instance

## Component Patterns

**React Functional Components:**
```jsx
export default function ComponentName({ prop1, prop2 }) {
  const [state, setState] = useState(null);

  useEffect(() => {
    // Side effects
  }, [dependencies]);

  return (
    <div className="...">
      {/* JSX */}
    </div>
  );
}
```

**Tailwind CSS Classes:**
- Use utility classes directly in JSX
- Custom theme classes: `bg-theme-background`, `text-theme-primary`, `card`, `btn-primary`
- Responsive prefixes: `md:grid-cols-2`, `lg:grid-cols-4`

**Skeleton Loading Pattern:**
```jsx
{loading ? (
  <div className="animate-pulse bg-gray-200 rounded h-8 w-16"></div>
) : (
  <p className="text-2xl font-bold">{value}</p>
)}
```

---

*Convention analysis: 2025-01-16*
