---
created: 2026-01-17T09:27
title: Switch helpdesk to leaner FAISS index bucket
area: api
files:
  - src/services/faiss_helpdesk_service.py:24
  - src/api/helpdesk_routes.py
  - src/services/rag_response_service.py
---

## Problem

The current helpdesk system connects to `zorah-faiss-index` bucket which has 98,086 vectors. There is a much leaner, more targeted FAISS index at:

- Bucket: `zorah-475411-rag-documents`
- Path: `faiss_indexes/` (contains the FAISS index files)
- Also contains source documents for reference

The leaner index should provide:
- Faster search times
- More relevant results (curated content)
- Better accuracy for travel-related queries

Additionally, need to:
1. Verify OpenAI API key is configured in env/venv
2. Research and implement an AI agent that orchestrates helpdesk tasks
3. Test the new bucket connection works end-to-end

## Solution

1. Update `GCS_BUCKET_NAME` in `faiss_helpdesk_service.py` from `zorah-faiss-index` to `zorah-475411-rag-documents`
2. Update file paths to look in `faiss_indexes/` subdirectory
3. Test with `/api/v1/helpdesk/health` and `/api/v1/helpdesk/accuracy-test`
4. Verify OPENAI_API_KEY is set in environment
5. Research agent patterns (LangChain agents, custom orchestration, tool-calling)
6. Implement helpdesk agent that can:
   - Search knowledge base
   - Generate quotes
   - Answer platform questions
   - Route to human when needed
