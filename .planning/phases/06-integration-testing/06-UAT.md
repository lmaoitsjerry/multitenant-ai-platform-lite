---
status: testing
phase: 06-integration-testing
source: [04-01-SUMMARY.md, 05-02-SUMMARY.md, 06-02-SUMMARY.md]
started: 2026-01-17T05:45:00Z
updated: 2026-01-17T05:45:00Z
---

## Current Test

number: 1
name: Helpdesk Natural Language Response
expected: |
  Ask the helpdesk about hotels in a destination. Response should be:
  - Conversational, not a bullet list or raw document dump
  - Contains specific hotel names, prices, or features from the knowledge base
  - Has timing data (search_ms, synthesis_ms, total_ms) in the response
  - Source names show document titles, not temp file paths like /tmp/...
awaiting: user response

## Tests

### 1. Helpdesk Natural Language Response
expected: Helpdesk response is conversational with specific details from knowledge base, not raw document dump. Sources show clean document names.
result: issue
reported: "Response shows raw document dumps with partial sentences, duplicate content, and temp file paths as sources. Uses fallback mode instead of LLM synthesis. User wants research on better RAG/FAISS for natural, helpful answers."
severity: blocker

### 2. Helpdesk Unknown Question Handling
expected: When asked an off-topic question (like "What is the capital of France?"), helpdesk gracefully acknowledges lack of knowledge instead of giving generic travel advice.
result: [pending]

### 3. Draft Quote Creation from Email
expected: When an inbound email arrives, a draft quote is created (status='draft') for consultant review before sending.
result: [pending]

### 4. Quote Approval and Send
expected: Consultant can click "Send" on a draft quote. Email with PDF attachment is sent to customer. Quote status changes to 'sent'. Notification appears in dashboard.
result: [pending]

### 5. Quote Resend Button
expected: Clicking "Resend" on an already-sent quote resends the email without creating a new quote. Customer receives the same quote again.
result: [pending]

### 6. Tenant Routing from Email
expected: Email sent to tenant-specific address (e.g., final-itc-3@zorah.ai) is routed to the correct tenant's dashboard, not a hardcoded tenant.
result: [pending]

## Summary

total: 6
passed: 0
issues: 1
pending: 5
skipped: 0

## Gaps

- truth: "Helpdesk response is conversational with specific details from knowledge base"
  status: failed
  reason: "User reported: Response shows raw document dumps with partial sentences, duplicate content, and temp file paths as sources. Uses fallback mode instead of LLM synthesis."
  severity: blocker
  test: 1
  root_cause: "LLM synthesis not working - likely missing OPENAI_API_KEY or fallback triggered. Source cleanup code not deployed."
  artifacts:
    - path: "src/services/rag_response_service.py"
      issue: "Fallback being triggered instead of LLM synthesis"
    - path: "src/api/helpdesk_routes.py"
      issue: "Source names not using cleaned format"
  missing:
    - "Ensure OPENAI_API_KEY environment variable is set"
    - "Deploy code changes from commits 5602e16, e32a913"
    - "Research better RAG chunking and retrieval strategies"

  research_completed: true
  research_file: ".planning/research/RAG_FAISS_BEST_PRACTICES.md"
  research_findings:
    - "Root cause: OPENAI_API_KEY not set in production - triggers fallback mode"
    - "Add health check endpoint to verify API key status"
    - "Re-ranking with cross-encoder improves retrieval by 15-48%"
    - "MMR for diversity in hotel queries (lambda 0.6-0.7)"
    - "Improved prompt engineering with examples"
    - "Dynamic generation parameters based on query type"
