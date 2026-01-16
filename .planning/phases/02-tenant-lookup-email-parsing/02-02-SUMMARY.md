---
phase: 02-tenant-lookup-email-parsing
plan: 02
subsystem: email-parsing
tags: [openai, gpt-4o-mini, email-parser, llm, fallback]

dependency_graph:
  requires: [01-01]
  provides: [llm-email-parsing, enhanced-extraction]
  affects: [03-01, 05-01]

tech_stack:
  added: [openai]
  patterns: [llm-with-fallback, json-structured-output]

key_files:
  created:
    - src/agents/llm_email_parser.py
  modified:
    - src/webhooks/email_webhook.py
    - tests/test_email_parser.py

decisions:
  - id: D-02-02-01
    decision: Use GPT-4o-mini for cost-efficient parsing
    rationale: ~$0.15/1M tokens, fast response, good accuracy for extraction
  - id: D-02-02-02
    decision: Always fallback to rule-based parser on any LLM failure
    rationale: Reliability over accuracy - better to have approximate result than failure

metrics:
  duration: 4m
  completed: 2026-01-16
---

# Phase 02 Plan 02: LLM Email Parser Summary

**One-liner:** GPT-4o-mini powered email parser with automatic fallback to rule-based UniversalEmailParser on failures.

## What Was Built

### LLMEmailParser Class (`src/agents/llm_email_parser.py`)
New email parser that uses OpenAI GPT-4o-mini for intelligent extraction of travel inquiry details:

```python
class LLMEmailParser:
    def __init__(self, config: ClientConfig)
    def parse(self, email_body: str, subject: str) -> Dict[str, Any]
    def _parse_with_llm(self, full_text: str) -> Optional[Dict[str, Any]]
    def _normalize_llm_result(self, result: Dict) -> Dict[str, Any]
    def _find_closest_destination(self, destination: str) -> str
```

**Key Features:**
- JSON structured output mode for consistent extraction
- Low temperature (0.1) for deterministic results
- 10-second timeout to prevent hanging
- Destination list included in prompt for better matching
- Budget normalization (R50000, 50k, 50000 all work)
- Automatic fallback to UniversalEmailParser on ANY failure

### Webhook Integration
Modified `process_inbound_email()` to use LLMEmailParser as primary:

```python
# STEP 8: Email parser import
from src.agents.llm_email_parser import LLMEmailParser
from src.agents.universal_email_parser import UniversalEmailParser

# STEP 9: Email parsed
parser = LLMEmailParser(config)
parsed_data = parser.parse(email.body_text, email.subject)
```

Diagnostic logging now includes `parse_method` field to show whether LLM or fallback was used.

### Test Suite
16 comprehensive tests covering:
- LLM parsing success path
- Fallback on no API key
- Fallback on LLM failure
- Budget format normalization
- Destination fuzzy matching
- Empty/malformed email handling
- Long email handling
- Special character handling

## Extracted Fields

The LLM parser extracts:
| Field | Type | Description |
|-------|------|-------------|
| destination | str | Matched against tenant's destination list |
| check_in | str | YYYY-MM-DD format |
| check_out | str | YYYY-MM-DD format |
| adults | int | Default 2 |
| children | int | Default 0 |
| children_ages | List[int] | Ages of children |
| budget | int | Total budget in ZAR |
| budget_is_per_person | bool | Whether budget was per person |
| name | str | Customer name |
| email | str | Customer email |
| phone | str | Customer phone |
| is_travel_inquiry | bool | Whether this is a travel inquiry |
| special_requests | str | Any special requirements |
| parse_method | str | 'llm' or 'fallback' |

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 203db0d | feat | Create LLM-powered email parser |
| bf86bb0 | feat | Integrate LLM parser into email webhook |
| bb90f9b | test | Add comprehensive email parser tests |

## Verification Results

| Check | Status |
|-------|--------|
| LLMEmailParser class exists | PASS |
| Fallback logic present | PASS |
| Webhook integration complete | PASS |
| parse_method in diagnostic logging | PASS |
| Tests pass (16/16) | PASS |

## Next Phase Readiness

**Ready for Phase 3:** Quote agent uses parsed_data dict - no changes needed to downstream flow.

**Dependencies satisfied:**
- LLMEmailParser provides same output format as UniversalEmailParser
- parse_method field added for observability
- Fallback ensures 100% availability

**No blockers identified.**
