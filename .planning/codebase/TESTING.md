# Testing Patterns

**Analysis Date:** 2026-01-23

## Test Framework

**Runner:**
- pytest (version 8.3.0)
- Config: `pyproject.toml` section `[tool.pytest.ini_options]`

**Assertion Library:**
- pytest built-in assertions
- unittest.mock for mocking

**Run Commands:**
```bash
pytest                           # Run all tests
pytest tests/test_services.py    # Run specific file
pytest -v --tb=short             # Verbose with short traceback (default)
pytest -m "not slow"             # Skip slow tests
pytest -m "unit"                 # Run only unit tests
pytest --cov=src --cov-report=html  # With coverage
```

## Test File Organization

**Location:**
- Separate `tests/` directory at project root
- Test fixtures in `tests/fixtures/`

**Naming:**
- Test files: `test_{module}.py`
- Test classes: `Test{ClassName}` or `Test{Feature}Endpoint`
- Test functions: `test_{behavior_description}`

**Structure:**
```
tests/
  conftest.py                    # Shared fixtures
  utils.py                       # Test utilities
  fixtures/
    __init__.py
    bigquery_fixtures.py         # BigQuery mock infrastructure
    sendgrid_fixtures.py         # SendGrid mock data
    openai_fixtures.py           # OpenAI mock responses
    genai_fixtures.py            # Google AI fixtures
    gcs_fixtures.py              # GCS storage fixtures
    twilio_vapi_fixtures.py      # Twilio/VAPI fixtures
  test_api_routes.py             # Core API route tests
  test_services.py               # Service layer tests
  test_crm_service.py            # CRM service unit tests
  test_supabase_tool.py          # Supabase operations tests
  test_integration_*.py          # Integration test suites
  ...
```

## Test Structure

**Suite Organization:**
```python
"""
Module docstring explaining test scope
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


# ==================== Fixtures ====================

@pytest.fixture
def mock_config():
    """Create a mock ClientConfig."""
    config = MagicMock()
    config.client_id = "test_tenant"
    config.supabase_url = "https://test.supabase.co"
    config.supabase_service_key = "test-service-key"
    config.currency = "USD"
    return config


# ==================== Test Classes ====================

class TestFeatureName:
    """Test description."""

    def test_behavior_description(self, mock_config):
        """Should do X when Y happens."""
        # Arrange

        # Act

        # Assert
```

**Patterns:**
- Group related tests in classes
- Use descriptive class names: `TestPipelineStage`, `TestQuoteListEndpoint`
- Use section comments: `# ==================== Section Name ====================`
- Docstrings explain test purpose

## Mocking

**Framework:** `unittest.mock` (MagicMock, AsyncMock, patch)

**Patterns:**

1. **Chainable Mock for Supabase:**
```python
def create_chainable_mock():
    """Create a mock that supports method chaining for Supabase queries."""
    mock = MagicMock()
    mock.select.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.delete.return_value = mock
    mock.eq.return_value = mock
    mock.neq.return_value = mock
    mock.gt.return_value = mock
    mock.gte.return_value = mock
    mock.lt.return_value = mock
    mock.lte.return_value = mock
    mock.is_.return_value = mock
    mock.in_.return_value = mock
    mock.order.return_value = mock
    mock.limit.return_value = mock
    mock.range.return_value = mock
    mock.single.return_value = mock
    mock.execute.return_value = MagicMock(data=[])
    return mock
```

2. **Service Initialization Mock:**
```python
@pytest.fixture
def crm_service_with_mock_db(mock_config, mock_supabase):
    """Create a CRMService with mocked Supabase."""
    from src.services.crm_service import CRMService

    with patch.object(CRMService, '__init__', return_value=None):
        service = CRMService.__new__(CRMService)
        service.config = mock_config
        service.supabase = mock_supabase
        return service
```

3. **Environment Variables:**
```python
@pytest.fixture
def mock_env_vars():
    """Set up common environment variables for testing."""
    env_vars = {
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_SERVICE_KEY': 'test-service-key',
        'OPENAI_API_KEY': 'test-openai-key',
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars
```

4. **External Service Mock:**
```python
with patch('src.tools.supabase_tool.get_cached_supabase_client') as mock_get_client:
    mock_get_client.return_value = mock_supabase_client
    # Test code here
```

**What to Mock:**
- External services: Supabase, BigQuery, SendGrid, OpenAI
- Network calls: HTTP clients (httpx)
- File system operations (when testing service logic)
- Time-dependent operations
- Singleton instances (FAISS service)

**What NOT to Mock:**
- Business logic within the service under test
- Pydantic model validation
- Core Python functionality
- The test subject itself

## Fixtures and Factories

**Test Data - MockFactory** (`tests/utils.py`):
```python
class MockFactory:
    @staticmethod
    def create_config(client_id='test_tenant', currency='USD', **kwargs):
        config = MagicMock()
        config.client_id = client_id
        config.currency = currency
        # ... set all attributes
        return config

    @staticmethod
    def create_user(user_id='user_123', role='admin', tenant_id='test_tenant'):
        return {
            'id': user_id,
            'email': 'test@example.com',
            'role': role,
            'tenant_id': tenant_id,
            'is_active': True
        }

    @staticmethod
    def create_chainable_mock():
        # Returns Supabase-style chainable mock
```

**Data Generators** (`tests/fixtures/bigquery_fixtures.py`):
```python
def generate_quotes(n=3, statuses=None, tenant_id="test_tenant"):
    """Generate realistic quote records."""
    # Returns list of quote dicts

def generate_invoices(n=3, statuses=None, tenant_id="test_tenant"):
    """Generate realistic invoice records with aging data."""

def generate_clients(n=5, stages=None, tenant_id="test_tenant"):
    """Generate CRM client records."""

def generate_call_records(n=5, outcomes=None, tenant_id="test_tenant"):
    """Generate call record data."""
```

**Location:**
- Shared fixtures: `tests/conftest.py`
- Domain fixtures: `tests/fixtures/bigquery_fixtures.py`, etc.
- Test utilities: `tests/utils.py`

## Coverage

**Requirements:** 57% minimum (enforced in CI)

**Configuration** (`pyproject.toml`):
```toml
[tool.coverage.run]
source = ["src", "main.py", "config"]
omit = ["tests/*", "*/__pycache__/*", "venv/*"]
branch = true

[tool.coverage.report]
fail_under = 57
show_missing = true
precision = 1
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "pass",
]
```

**View Coverage:**
```bash
pytest --cov=src --cov-report=html
# Open htmlcov/index.html in browser
```

## Test Types

**Unit Tests:**
- Scope: Single class/function isolation
- Dependencies: All mocked
- Location: `tests/test_{service}.py`
- Marker: `@pytest.mark.unit`
- Example: `test_crm_service.py`, `test_services.py`

**Integration Tests:**
- Scope: Multiple components working together
- Dependencies: External services mocked, internal components real
- Location: `tests/test_integration_*.py`
- Marker: `@pytest.mark.integration`, `@pytest.mark.slow`
- Example: `test_integration_email_pipeline.py`, `test_integration_tenant_isolation.py`

**Route Tests:**
- Scope: HTTP endpoint behavior
- Tool: `FastAPI TestClient`
- Focus: Auth required, validation, response format
- Example: `test_api_routes.py`, `test_core_routes.py`

**E2E Tests:**
- Framework: Not configured (no Playwright/Selenium)
- Manual testing via frontend

## Common Patterns

**Async Testing:**
```python
@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# pytest-asyncio handles most async tests automatically via:
# asyncio_mode = "auto" in pyproject.toml
```

**Error Testing:**
```python
def test_verify_jwt_with_expired_token(self):
    """verify_jwt should return False for expired token."""
    from src.services.auth_service import AuthService

    # Create expired token
    exp = datetime.utcnow() - timedelta(hours=1)
    token = jwt.encode({'sub': 'user123', 'exp': exp}, secret, algorithm='HS256')

    valid, result = service.verify_jwt(token)

    assert valid is False
    assert 'error' in result
```

**Authentication Testing:**
```python
class TestProtectedRoutes:
    def test_quotes_requires_auth(self, test_client):
        """GET /api/v1/quotes requires authentication."""
        response = test_client.get("/api/v1/quotes")
        assert response.status_code == 401

    def test_invoices_requires_auth(self, test_client):
        """GET /api/v1/invoices requires authentication."""
        response = test_client.get("/api/v1/invoices")
        assert response.status_code == 401
```

**Tenant Isolation Testing:**
```python
def test_create_ticket_includes_tenant_id(self, mock_config):
    """Created ticket should include tenant_id for isolation."""
    # Verify tenant_id is in the inserted record
    call_args = mock_client.table.return_value.insert.call_args
    inserted_record = call_args[0][0]
    assert inserted_record['tenant_id'] == 'test_tenant'
```

## Test Client Setup

**FastAPI TestClient with Mocked Services:**
```python
@pytest.fixture
def test_client():
    """Create a FastAPI TestClient with FAISS service mocked."""
    mock_faiss = MagicMock()
    mock_faiss.initialize.return_value = False
    mock_faiss.get_status.return_value = {"initialized": False}

    with patch('src.services.faiss_helpdesk_service.FAISSHelpdeskService._instance', None):
        with patch('src.services.faiss_helpdesk_service.get_faiss_helpdesk_service', return_value=mock_faiss):
            with patch.dict('sys.modules', {'google.cloud.storage': MagicMock()}):
                from fastapi.testclient import TestClient
                from main import app
                yield TestClient(app)
```

**Authenticated Request Headers:**
```python
@pytest.fixture
def authenticated_headers():
    return {
        'Authorization': 'Bearer test-jwt-token',
        'X-Client-ID': 'test_tenant',
        'Content-Type': 'application/json'
    }

@pytest.fixture
def admin_headers():
    return {
        'X-Admin-Token': 'test-admin-token',
        'Content-Type': 'application/json'
    }
```

## Test Markers

**Configuration** (`pyproject.toml`):
```toml
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]
```

**Auto-marking** (`conftest.py`):
```python
def pytest_collection_modifyitems(config, items):
    for item in items:
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        if "slow" in item.nodeid or "test_integration" in item.nodeid:
            item.add_marker(pytest.mark.slow)
```

## Cache Cleanup

**Reset Between Tests:**
```python
@pytest.fixture(autouse=True)
def reset_caches():
    """Reset any caches between tests."""
    yield
    # Clear auth service user cache
    try:
        from src.services.auth_service import _user_cache
        _user_cache.clear()
    except ImportError:
        pass

    # Clear tenant config cache
    try:
        from src.services.tenant_config_service import TenantConfigService
        if hasattr(TenantConfigService, '_instance'):
            TenantConfigService._instance = None
    except ImportError:
        pass
```

## BigQuery Mock Infrastructure

**Pattern-Based Response Matching** (`tests/fixtures/bigquery_fixtures.py`):
```python
class MockBigQueryClient:
    def set_response_for_pattern(self, pattern: str, rows: List[Dict]):
        """Set response data for queries matching a pattern."""
        self._pattern_responses[pattern.lower()] = rows

    def query(self, sql: str, job_config=None):
        sql_lower = sql.lower()
        for pattern, rows in self._pattern_responses.items():
            if pattern in sql_lower:
                return MockBigQueryQueryJob(rows)
        return MockBigQueryQueryJob(self._default_response)

# Usage in test:
mock_client.set_response_for_pattern("hotel_rates", generate_hotel_rates(5))
mock_client.set_response_for_pattern("COUNT(*)", [{'count': 42}])
```

## Assertion Helpers

**From `tests/utils.py`:**
```python
def assert_success_response(response, expected_status=200):
    """Assert that a response indicates success."""
    assert response.status_code == expected_status
    if response.headers.get('content-type', '').startswith('application/json'):
        data = response.json()
        assert data.get('success', True) is True

def assert_error_response(response, expected_status, expected_detail=None):
    """Assert that a response indicates an error."""
    assert response.status_code == expected_status
    if expected_detail:
        data = response.json()
        assert expected_detail in str(data.get('detail', ''))

def assert_list_response(response, min_length=0, max_length=None):
    """Assert that a response contains a list of items."""
    assert_success_response(response)
    data = response.json()
    items = data.get('data', data.get('items', []))
    assert isinstance(items, list)
```

---

*Testing analysis: 2026-01-23*
