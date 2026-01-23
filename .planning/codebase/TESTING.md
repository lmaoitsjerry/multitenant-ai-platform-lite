# Testing Patterns

**Analysis Date:** 2026-01-23

## Test Framework

**Runner:**
- pytest 8.3.0
- Config: `pyproject.toml` (tool.pytest.ini_options section)

**Assertion Library:**
- pytest built-in assertions
- unittest.mock for mocking

**Run Commands:**
```bash
pytest                           # Run all tests
pytest -v                        # Verbose output
pytest --tb=short               # Short traceback (default)
pytest -m "not slow"            # Skip slow/integration tests
pytest --cov=src --cov-report=html  # With coverage
pytest tests/test_auth_middleware.py -v  # Single file
```

## Test File Organization

**Location:**
- All tests in `tests/` directory (co-located at project root)
- Fixtures in `tests/fixtures/` subdirectory

**Naming:**
- Test files: `test_{module_name}.py`
- Test classes: `Test{Feature}` (e.g., `TestAuthService`)
- Test functions: `test_{behavior}_description` (e.g., `test_verify_jwt_with_valid_token`)

**Structure:**
```
tests/
    conftest.py                      # Shared fixtures
    utils.py                         # Test utilities
    fixtures/
        __init__.py                  # Re-exports all fixtures
        bigquery_fixtures.py         # BigQuery mocks
        sendgrid_fixtures.py         # SendGrid mocks
        openai_fixtures.py           # OpenAI mocks
        genai_fixtures.py            # Google GenAI mocks
        twilio_vapi_fixtures.py      # Twilio/VAPI mocks
        gcs_fixtures.py              # GCS/FAISS mocks
    test_api_routes.py
    test_auth_middleware.py
    test_services.py
    test_integration_*.py            # Integration tests
    ...
```

## Test Structure

**Suite Organization:**
```python
"""
Unit Tests for Auth Middleware

Tests for the AuthMiddleware class, specifically:
1. X-Client-ID header validation against JWT user's tenant
2. Tenant spoofing rejection (header != user's tenant)
3. Normal flow when header matches or is absent
4. Public path bypass
5. Missing/invalid auth handling

These tests verify SEC-02 security fix for tenant isolation.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestPublicPathDetection:
    """Test the is_public_path function"""

    def test_health_endpoint_is_public(self):
        """Test that /health endpoint is public"""
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/health') == True

    def test_protected_routes_are_not_public(self):
        """Test that protected API routes are not public"""
        from src.middleware.auth_middleware import is_public_path
        assert is_public_path('/api/v1/quotes') == False


class TestTenantSpoofingRejection:
    """
    Test that tenant spoofing attempts are rejected.
    Core SEC-02 security tests.
    """

    @pytest.mark.asyncio
    async def test_mismatched_tenant_header_returns_403(self):
        """
        Test: User from tenant_a sends X-Client-ID: tenant_b
        Expected: 403 Forbidden with "tenant mismatch" message
        """
        # Test implementation...
```

**Patterns:**
- Group related tests in classes with descriptive names
- Use docstrings to explain test purpose and expected behavior
- Document security-related tests with ticket references (e.g., SEC-02)

## Mocking

**Framework:** `unittest.mock`

**Patterns:**

**1. Chainable mock for Supabase queries (conftest.py):**
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
    mock.order.return_value = mock
    mock.limit.return_value = mock
    mock.single.return_value = mock
    mock.execute.return_value = MagicMock(data=[])
    return mock
```

**2. Environment variable patching:**
```python
with patch.dict(os.environ, {'SUPABASE_JWT_SECRET': 'test-secret'}):
    # Test code here
```

**3. Module patching:**
```python
with patch('src.middleware.auth_middleware.get_config') as mock_get_config, \
     patch('src.middleware.auth_middleware.AuthService') as MockAuthService:
    mock_get_config.return_value = MockConfig('tenant_a')
    mock_auth_instance = MagicMock()
    mock_auth_instance.verify_jwt.return_value = (True, {'sub': 'auth_user_123'})
    MockAuthService.return_value = mock_auth_instance
```

**4. AsyncMock for async functions:**
```python
mock_auth_instance.get_user_by_auth_id = AsyncMock(return_value=user_data)
```

**What to Mock:**
- External services (Supabase, BigQuery, SendGrid, OpenAI)
- Environment variables
- File system operations
- Network calls

**What NOT to Mock:**
- Business logic under test
- Pydantic model validation
- FastAPI routing

## Fixtures and Factories

**Pytest Fixtures (conftest.py):**
```python
@pytest.fixture
def mock_config():
    """Create a mock ClientConfig for testing."""
    config = MagicMock()
    config.client_id = "test_tenant"
    config.supabase_url = "https://test.supabase.co"
    config.supabase_service_key = "test-service-key"
    config.currency = "USD"
    config.company_name = "Test Company"
    return config

@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    return {
        'id': 'user_123',
        'auth_user_id': 'auth_123',
        'email': 'test@example.com',
        'role': 'admin',
        'tenant_id': 'test_tenant',
        'is_active': True
    }

@pytest.fixture
def authenticated_headers():
    """Return headers for authenticated requests."""
    return {
        'Authorization': 'Bearer test-jwt-token',
        'X-Client-ID': 'test_tenant',
        'Content-Type': 'application/json'
    }
```

**MockFactory Pattern (tests/utils.py):**
```python
class MockFactory:
    """Factory for creating various mock objects."""

    @staticmethod
    def create_supabase_response(data=None, error=None):
        response = MagicMock()
        response.data = data if data is not None else []
        response.error = error
        return response

    @staticmethod
    def create_config(client_id='test_tenant', **kwargs):
        config = MagicMock()
        config.client_id = client_id
        # ... set all attributes
        return config
```

**Data Generators (fixtures/bigquery_fixtures.py):**
```python
def generate_quotes(n: int = 3, statuses: List[str] = None) -> List[Dict]:
    """Generate realistic quote records."""
    if statuses is None:
        statuses = ["accepted", "sent", "draft"]
    quotes = []
    for i in range(n):
        quotes.append({
            "quote_id": f"QT-{datetime.now().strftime('%Y%m%d')}-{i+1:03d}",
            "tenant_id": "test_tenant",
            "customer_name": f"Customer {i}",
            "status": statuses[i % len(statuses)],
            # ... more fields
        })
    return quotes
```

**Location:**
- Shared fixtures: `tests/conftest.py`
- Utility functions: `tests/utils.py`
- Domain-specific fixtures: `tests/fixtures/{domain}_fixtures.py`

## Coverage

**Requirements:**
- Current threshold: 57% (enforced in pyproject.toml)
- Target: 70%

**Configuration (pyproject.toml):**
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
]
```

**View Coverage:**
```bash
pytest --cov=src --cov-report=html
# Open htmlcov/index.html in browser
```

## Test Types

**Unit Tests:**
- Scope: Single function or method
- Naming: `test_{function}_{scenario}`
- Mock all external dependencies
- Located in: `tests/test_{module}.py`

**Integration Tests:**
- Scope: Multiple components working together
- Naming: `test_integration_{feature}.py`
- Marked with `@pytest.mark.integration`
- May use real database connections (mocked in CI)

**Test Markers:**
```python
@pytest.mark.slow        # Skip with -m "not slow"
@pytest.mark.integration # Integration tests
@pytest.mark.unit        # Unit tests
@pytest.mark.asyncio     # Async tests
```

## Common Patterns

**Async Testing:**
```python
@pytest.mark.asyncio
async def test_async_function():
    """Test async function with AsyncMock."""
    mock_service = MagicMock()
    mock_service.get_user = AsyncMock(return_value={'id': '123'})

    result = await mock_service.get_user('123')
    assert result['id'] == '123'
```

**Error Testing:**
```python
def test_invalid_token_returns_401(self):
    """verify_jwt should return False for invalid token."""
    from src.services.auth_service import AuthService

    with patch.dict(os.environ, {'SUPABASE_JWT_SECRET': 'correct-secret'}):
        service = AuthService(url='https://test.supabase.co', key='key')
        token = jwt.encode({'sub': 'user123'}, 'wrong-secret', algorithm='HS256')

        valid, result = service.verify_jwt(token)

        assert valid is False
        assert 'error' in result
```

**HTTP Response Testing:**
```python
def test_health_returns_healthy(self):
    """GET /health should return healthy status."""
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
```

**Assertion Helpers (tests/utils.py):**
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
```

## Test Client Setup

**FastAPI TestClient with mocked services:**
```python
@pytest.fixture
def test_client():
    """Create a FastAPI TestClient with FAISS service mocked."""
    mock_faiss = MagicMock()
    mock_faiss.initialize.return_value = False
    mock_faiss.get_status.return_value = {
        "initialized": False,
        "error": "Mocked for tests"
    }

    with patch('src.services.faiss_helpdesk_service.FAISSHelpdeskService._instance', None):
        with patch('src.services.faiss_helpdesk_service.get_faiss_helpdesk_service', return_value=mock_faiss):
            from fastapi.testclient import TestClient
            from main import app
            yield TestClient(app)
```

## Singleton Reset Pattern

For services using singleton pattern, reset between tests:
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

## External API Mock Fixtures

**Available in `tests/fixtures/`:**

| Module | Purpose | Key Exports |
|--------|---------|-------------|
| `bigquery_fixtures.py` | BigQuery client mocks | `MockBigQueryClient`, `generate_quotes()` |
| `sendgrid_fixtures.py` | SendGrid API mocks | `MockSendGridClient`, `generate_subusers()` |
| `openai_fixtures.py` | OpenAI API mocks | `MockOpenAIClient`, `create_tool_call_response()` |
| `genai_fixtures.py` | Google GenAI mocks | `MockGenAIClient`, `create_travel_inquiry_response()` |
| `twilio_vapi_fixtures.py` | Twilio/VAPI mocks | `MockRequestsSession`, `generate_available_numbers()` |
| `gcs_fixtures.py` | GCS/FAISS mocks | `MockGCSClient`, `MockFAISSIndex` |

**Usage:**
```python
from tests.fixtures.bigquery_fixtures import (
    create_mock_bigquery_client,
    generate_quotes,
)

def test_with_bigquery():
    client = create_mock_bigquery_client()
    client.set_response_for_pattern("quotes", generate_quotes(5))

    with patch('src.tools.bigquery_tool.get_client', return_value=client):
        # Test code here
```

---

*Testing analysis: 2026-01-23*
