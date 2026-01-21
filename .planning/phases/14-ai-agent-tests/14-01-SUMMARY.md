---
phase: 14-ai-agent-tests
plan: 01
title: OpenAI Mock Infrastructure & Helpdesk Agent Tests
subsystem: agents
tags: [openai, llm, testing, mocking, helpdesk-agent, function-calling]
status: complete

dependency_graph:
  requires:
    - "src/agents/helpdesk_agent.py"
    - "src/services/faiss_helpdesk_service.py"
  provides:
    - "Reusable OpenAI mock infrastructure"
    - "99.4% test coverage for helpdesk_agent.py"
  affects:
    - "Future LLM agent tests (quote_agent, inbound_agent)"
    - "OpenAI function calling test patterns"

tech_stack:
  added: []
  patterns:
    - "Mock class hierarchy for OpenAI response structure"
    - "Pattern-based response matching for conversations"
    - "Direct client injection for lazy-loading patterns"
    - "Sequential response mocking for multi-turn conversations"

key_files:
  created:
    - "tests/fixtures/openai_fixtures.py"
    - "tests/test_helpdesk_agent.py"
  modified: []

decisions:
  - id: "D-14-01-01"
    decision: "Use direct _client injection instead of patching inline imports"
    date: "2026-01-21"
  - id: "D-14-01-02"
    decision: "Create MockConversationClient for sequential response testing"
    date: "2026-01-21"
  - id: "D-14-01-03"
    decision: "Patch FAISS service at source module for inline imports"
    date: "2026-01-21"

metrics:
  duration: "~8 minutes"
  completed: "2026-01-21"
  tests_added: 58
  coverage_achieved: "99.4%"
---

# Phase 14 Plan 01: OpenAI Mock Infrastructure & Helpdesk Agent Tests Summary

**One-liner:** Created comprehensive OpenAI mock infrastructure with pattern-based responses and achieved 99.4% coverage for helpdesk_agent.py through 58 targeted tests.

## What Was Built

### OpenAI Mock Infrastructure (`tests/fixtures/openai_fixtures.py`)

Created a complete mock framework for testing OpenAI-dependent code:

1. **Mock Classes:**
   - `MockToolFunction` - Simulates function object in tool calls
   - `MockToolCall` - Simulates OpenAI tool/function call response
   - `MockOpenAIMessage` - Simulates `response.choices[0].message`
   - `MockOpenAIChoice` - Simulates completion choice
   - `MockOpenAIUsage` - Simulates token usage
   - `MockOpenAIResponse` - Full chat.completions.create() response
   - `MockChatCompletions` - Simulates client.chat.completions
   - `MockOpenAIClient` - Full client mock with pattern matching
   - `MockConversationClient` - Sequential response client for multi-turn tests

2. **Factory Functions:**
   - `create_mock_openai_client()` - Configurable client creation
   - `create_direct_response()` - Response without tool calls
   - `create_tool_call_response()` - Response with function call
   - `create_search_response()` - Preset for search_knowledge_base
   - `create_quote_response()` - Preset for start_quote
   - `create_platform_help_response()` - Preset for platform_help
   - `create_route_to_human_response()` - Preset for human routing

3. **Error Generators:**
   - `create_openai_api_error()` - Generic API error
   - `create_rate_limit_error()` - Rate limit simulation
   - `create_invalid_api_key_error()` - Auth error simulation

### Helpdesk Agent Tests (`tests/test_helpdesk_agent.py`)

Created 58 comprehensive tests across 11 test classes:

| Test Class | Tests | Coverage Focus |
|------------|-------|----------------|
| TestHelpdeskAgentInit | 4 | Initialization, lazy loading, API key handling |
| TestHelpdeskAgentChat | 8 | Direct responses, tool triggering, fallback |
| TestToolExecution | 16 | search, quote, platform_help, route_to_human |
| TestConversationManagement | 5 | reset, history trimming, stats |
| TestSingletonHelpers | 3 | get/reset singleton functions |
| TestToolCallsDefinitions | 6 | Tool schema validation |
| TestFallbackBehavior | 4 | Fallback response structure |
| TestHandleToolCalls | 3 | Unknown tools, history recording |
| TestEdgeCases | 7 | Empty messages, long messages, errors |
| TestMultipleTurnConversation | 2 | Context maintenance, tool accumulation |

## Coverage Results

```
Name                           Stmts   Miss Branch BrPart  Cover   Missing
--------------------------------------------------------------------------
src\agents\helpdesk_agent.py     126      0     30      1  99.4%   470->472
--------------------------------------------------------------------------
```

- **Target:** 50%
- **Achieved:** 99.4%
- **Uncovered:** Only `if __name__ == "__main__"` block

## Technical Approach

### Challenge: Inline Imports

The helpdesk_agent.py uses inline imports for OpenAI and FAISS services:

```python
@property
def client(self):
    if self._client is None and self.openai_api_key:
        import openai
        self._client = openai.OpenAI(api_key=self.openai_api_key)
```

### Solution: Direct Client Injection

Instead of patching the import, we inject the mock directly:

```python
def inject_mock_client(agent, mock_client):
    """Helper to inject a mock OpenAI client into an agent."""
    agent._client = mock_client

# In tests:
agent = HelpdeskAgent(mock_config)
inject_mock_client(agent, mock_client)
result = agent.chat("Hello!")
```

### Pattern-Based Response Matching

The mock client matches responses based on message content:

```python
mock_client = create_mock_openai_client()
mock_client.set_response_for_pattern(
    "mauritius",
    create_search_response("mauritius hotels", "hotel_info")
)
```

### Sequential Response Testing

For multi-turn conversations with tool calls:

```python
mock_client = MockConversationClient([
    create_search_response("mauritius"),  # First: tool call
    create_direct_response("Found hotels!")  # Second: final response
])
```

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Hash | Message |
|------|---------|
| ebbcab1 | test(14-01): create OpenAI mock infrastructure |
| 5d15f48 | test(14-01): create comprehensive helpdesk agent tests |
| bf33344 | test(14-01): verify 99.4% coverage for helpdesk agent |

## Next Phase Readiness

OpenAI mock infrastructure is ready for:
- Quote agent tests (14-02)
- Inbound agent tests (future)
- Any other OpenAI-dependent code testing

The pattern established here (direct client injection + pattern-based responses) can be reused across all LLM agent tests.
