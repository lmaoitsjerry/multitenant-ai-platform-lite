# Testing Patterns

**Analysis Date:** 2025-01-16

## Test Framework

**Python:**
- Runner: `unittest` (standard library)
- Config: None (uses unittest discovery)
- No pytest, no coverage tool configured

**Run Commands:**
```bash
python run_tests.py           # Run all tests
python -m unittest discover   # Alternative discovery
python tests/test_config.py   # Run single test file
```

**JavaScript/React:**
- No test framework configured
- No Jest, Vitest, or React Testing Library found
- `package.json` has no test script

## Test File Organization

**Python Location:**
- Tests in dedicated `tests/` directory at project root
- Pattern: `tests/test_*.py`

**Directory Structure:**
```
tests/
├── test_config.py        # Configuration loading tests
├── test_email_parser.py  # Email parsing tests
└── test_templates.py     # Template rendering tests
```

**JavaScript/React:**
- No test files found
- No `__tests__/` directories
- No `*.test.js` or `*.spec.js` files

## Test Structure

**Python unittest Pattern:**
```python
import unittest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.loader import ClientConfig

class TestConfiguration(unittest.TestCase):
    def setUp(self):
        # Setup for each test
        self.config = ClientConfig('example')

    def test_feature_name(self):
        """Test that feature does expected thing"""
        result = self.config.some_property
        self.assertEqual(result, expected_value)

    def test_error_case(self):
        """Test that invalid input raises error"""
        with self.assertRaises(Exception):
            ClientConfig('non_existent')

if __name__ == '__main__':
    unittest.main()
```

**Test Discovery Runner (`run_tests.py`):**
```python
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def run_tests():
    """Run all tests in the tests directory"""
    loader = unittest.TestLoader()
    start_dir = str(Path(__file__).parent / 'tests')
    suite = loader.discover(start_dir, pattern='test_*.py')

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if not result.wasSuccessful():
        sys.exit(1)

if __name__ == '__main__':
    run_tests()
```

## Mocking

**Framework:** `unittest.mock`

**Patterns:**
```python
from unittest.mock import MagicMock, patch

class TestTemplates(unittest.TestCase):
    @patch('src.utils.pdf_generator.HTML')
    def test_pdf_generation(self, mock_html):
        """Test PDF generation logic (mocking WeasyPrint)"""
        # Setup mock
        mock_html_instance = MagicMock()
        mock_html.return_value = mock_html_instance
        mock_html_instance.write_pdf.return_value = b'%PDF-1.4...'

        # Execute
        pdf_gen = PDFGenerator(self.config)
        pdf_bytes = pdf_gen.generate_quote_pdf(quote_data)

        # Assert
        self.assertTrue(len(pdf_bytes) > 0)
        mock_html.assert_called()
```

**What to Mock:**
- External services (WeasyPrint, email sending)
- Database calls (when testing business logic)
- API calls to third-party services

**What NOT to Mock:**
- ClientConfig loading (uses real test config)
- File system operations with test fixtures
- Simple utility functions

## Fixtures and Factories

**Test Data:**
- Uses `example` client configuration as test fixture
- Client config at `clients/example/config.yaml`
- Real file-based configuration, not mocked

**Pattern:**
```python
class TestEmailParser(unittest.TestCase):
    def setUp(self):
        self.config = ClientConfig('example')
        self.parser = UniversalEmailParser(self.config)
```

**Test Input Data:**
```python
def test_traveler_extraction(self):
    email_body = "2 adults and 3 children aged 5, 8, 12"
    result = self.parser.parse(email_body)
    self.assertEqual(result['adults'], 2)
```

**Location:**
- No dedicated fixtures directory
- Test data defined inline in test methods
- `clients/example/` serves as test client configuration

## Coverage

**Requirements:** None enforced

**Coverage Tool:** Not configured

**Recommendation:**
```bash
# Add to requirements.txt
coverage==7.x

# Run with coverage
coverage run -m pytest tests/
coverage report -m
coverage html
```

## Test Types

**Unit Tests:**
- Configuration loading (`test_config.py`)
- Email parsing (`test_email_parser.py`)
- Template rendering (`test_templates.py`)
- Focus on isolated components

**Integration Tests:**
- Not found in codebase
- Would test database + service interactions

**E2E Tests:**
- Not implemented
- No Playwright, Cypress, or Selenium
- Consider adding for critical user flows

**API Tests:**
- `test_vapi_integration.py` (manual script, not unittest)
- Uses `requests` library to test live endpoints
- Not part of automated test suite

## Common Patterns

**Assertion Patterns:**
```python
# Equality
self.assertEqual(result, expected)

# Contains
self.assertIn('Bali', destinations)

# Boolean
self.assertTrue(len(destinations) >= 2)

# Exception
with self.assertRaises(Exception):
    invalid_operation()
```

**Test Method Naming:**
```python
def test_feature_does_expected_thing(self):
    """Docstring describes what is being tested"""

def test_error_on_invalid_input(self):
    """Test error handling for edge case"""

def test_fallback_for_unknown_value(self):
    """Test graceful degradation"""
```

**Async Testing:**
- Not used (no async test patterns found)
- Backend uses async FastAPI but tests are synchronous

**Error Testing:**
```python
def test_missing_client(self):
    """Test that loading a non-existent client raises an error"""
    with self.assertRaises(Exception):
        ClientConfig('non_existent_client')
```

## Manual/Integration Test Scripts

**VAPI Integration Test (`test_vapi_integration.py`):**
```python
"""
VAPI Integration Test Script

Tests the new VAPI endpoints:
1. Outbound call trigger
2. Provisioning status
3. Phone number search
4. VAPI webhook RAG integration

Usage:
    python test_vapi_integration.py

Set environment variables first:
    VAPI_API_KEY, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
"""
```

- Not part of unittest suite
- Run manually against live server
- Uses `requests` for HTTP calls
- Colored terminal output (disabled on Windows)

## Test Gaps and Recommendations

**Missing Test Coverage:**
- API route handlers (FastAPI endpoints)
- React components (no frontend tests)
- Database operations (Supabase, BigQuery)
- Authentication flows
- Rate limiting logic

**Recommended Additions:**

1. **pytest Migration:**
```bash
pip install pytest pytest-asyncio pytest-cov
```

2. **FastAPI Route Tests:**
```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
```

3. **React Testing (Vitest + Testing Library):**
```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom
```

```jsx
// Dashboard.test.jsx
import { render, screen } from '@testing-library/react';
import Dashboard from './Dashboard';

test('renders welcome message', () => {
  render(<Dashboard />);
  expect(screen.getByText(/good morning/i)).toBeInTheDocument();
});
```

4. **Add pytest.ini:**
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
asyncio_mode = auto
```

5. **Add Coverage Config (.coveragerc):**
```ini
[run]
source = src,config
omit = */tests/*,*/__pycache__/*

[report]
exclude_lines =
    pragma: no cover
    if __name__ == .__main__.:
```

---

*Testing analysis: 2025-01-16*
