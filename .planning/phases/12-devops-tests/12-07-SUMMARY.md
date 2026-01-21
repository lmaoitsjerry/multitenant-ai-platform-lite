---
phase: 12
plan: 07
subsystem: testing
tags: [tests, pytest, pricing, knowledge, crm, mocking]
dependency_graph:
  requires:
    - 12-05 (test infrastructure)
    - 12-06 (test patterns)
  provides:
    - Pricing routes tests (32 tests)
    - Knowledge routes tests (35 tests)
    - CRM service tests (31 tests)
    - Additional 7% coverage increase
  affects:
    - Future test development
    - CI pipeline test runs
tech_stack:
  added: []
  patterns:
    - Fixture-based service mocking
    - Mock injection for external services
    - Pydantic model validation tests
key_files:
  created:
    - tests/test_pricing_routes.py
    - tests/test_knowledge_routes.py
    - tests/test_crm_service.py
  modified: []
decisions:
  - decision: Mock SupabaseTool via __init__ patching
    rationale: SupabaseTool is imported inside CRMService __init__ with dynamic import; patching __init__ provides clean isolation
    date: 2026-01-21
  - decision: Test FAISSIndexManager with tmp_path fixture
    rationale: Uses pytest tmp_path for isolated file system tests without affecting real data directories
    date: 2026-01-21
metrics:
  duration: ~15 minutes
  completed: 2026-01-21
---

# Phase 12 Plan 07: Pricing, Knowledge & CRM Tests Summary

Tests for pricing routes, knowledge base routes, and CRM service functionality.

## One-Liner

98 new tests (32 pricing + 35 knowledge + 31 CRM) covering 1557 lines of test code.

## Deliverables

### 1. Pricing Routes Tests (test_pricing_routes.py)

**462 lines, 32 tests**

Test coverage for all pricing endpoints:
- Rate CRUD endpoints (list, create, get, update, delete)
- Import/export endpoints (CSV bulk operations)
- Hotel listing and hotel rates endpoints
- Destination listing endpoint
- Pricing statistics endpoint

Key test categories:
- Authentication requirement verification (20+ tests)
- Route existence validation
- Pydantic model validation (RateBase, RateCreate, RateUpdate, HotelBase, SeasonDefinition, ImportResult)
- BigQuery availability checking
- Dependency injection and caching behavior

### 2. Knowledge Routes Tests (test_knowledge_routes.py)

**543 lines, 35 tests**

Test coverage for knowledge base endpoints:
- Document CRUD endpoints (list, upload, get, delete)
- Document operations (reindex, download)
- Search endpoints (POST and GET methods)
- Admin endpoints (status, rebuild, categories)

Key test categories:
- Authentication requirement verification
- Route existence validation
- Pydantic model validation (DocumentMetadata, SearchRequest, SearchResult)
- FAISSIndexManager unit tests:
  - Directory creation
  - Metadata loading/migration
  - Text chunking
  - Status reporting
- Dependency injection and caching
- File type support validation

### 3. CRM Service Tests (test_crm_service.py)

**552 lines, 31 tests**

Test coverage for CRMService:
- PipelineStage enum validation
- Service initialization
- Client operations (get_or_create, get_by_email, get_by_id, update)
- Stage updates with activity logging
- Client search with filtering
- Activity retrieval
- Pipeline summary calculation
- Client statistics

Key test categories:
- Graceful handling without Supabase connection
- Mocked database operations
- Query filtering logic
- Helper method validation (_get_client_id_filter, _count_by_field)

## Test Results

```
============================= 98 passed in 13.49s =============================
```

All tests pass with no failures or errors.

## Coverage Impact

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total tests | 297 | 395 | +98 |
| New test files | 0 | 3 | +3 |
| Lines of test code | ~7500 | ~9000 | +1557 |
| Estimated coverage | 30% | 37% | +7% |

## Testing Patterns Used

### 1. Fixture-Based Service Mocking
```python
@pytest.fixture
def crm_service_with_mock_db(mock_config, mock_supabase):
    with patch.object(CRMService, '__init__', return_value=None):
        service = CRMService.__new__(CRMService)
        service.config = mock_config
        service.supabase = mock_supabase
        return service
```

### 2. tmp_path for File System Tests
```python
def test_load_metadata_creates_default(self, mock_config, tmp_path):
    manager.metadata_file = tmp_path / "metadata.json"
    metadata = manager._load_metadata()
    assert "documents" in metadata
```

### 3. Auth Requirement Verification
```python
def test_list_rates_requires_auth(self, test_client):
    response = test_client.get("/api/v1/pricing/rates")
    assert response.status_code == 401
```

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- [x] All test files created with target line counts (340+ target, 1557 actual)
- [x] All tests pass (98/98)
- [x] Coverage increases (~7% estimated)

## Next Steps

- Plan 12-08: Final test coverage expansion
- Continue toward 70% coverage target
