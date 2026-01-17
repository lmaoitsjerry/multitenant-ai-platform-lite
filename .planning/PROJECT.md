# Multi-Tenant AI Travel Platform - Inbound Email & Helpdesk RAG

## What This Is

A multi-tenant AI-powered travel platform for property management companies, featuring helpdesk AI with RAG (FAISS), quote generation, invoicing, CRM, and email processing. The platform has two frontends: tenant dashboard for daily operations and internal admin for Zorah team management.

## Core Value

Automated inbound email processing that generates and sends quotes without manual intervention, backed by a helpdesk that provides natural, helpful responses using RAG over 98K+ documents.

## Requirements

### Validated

- ✓ Multi-tenant architecture with X-Client-ID isolation — v1.0
- ✓ JWT authentication via Supabase — v1.0
- ✓ FAISS vector search with 98,086 documents loaded from GCS — v1.0
- ✓ Quote generation agent with PDF output — v1.0
- ✓ Invoice management with Stripe integration — v1.0
- ✓ CRM with leads and contacts — v1.0
- ✓ Email processing via SendGrid webhooks — v1.0
- ✓ Internal admin platform with tenant management — v1.0
- ✓ Helpdesk FAISS integration (public endpoints) — v1.0
- ✓ Tenant dashboard instant loading (stale-while-revalidate) — v1.0
- ✓ Admin platform instant loading (caching patterns) — v1.0
- ✓ EMAIL-01: SendGrid Inbound Parse receives emails and triggers webhook — v2.0
- ✓ EMAIL-02: Webhook endpoint parses email and finds tenant by TO address — v2.0
- ✓ EMAIL-03: LLM-powered email parser extracts trip details (destination, dates, travelers, budget) — v2.0
- ✓ EMAIL-04: Quote generator creates quote from parsed details with hotel/rate lookup — v2.0
- ✓ EMAIL-05: Quote email sent via tenant's SendGrid subuser credentials — v2.0
- ✓ EMAIL-06: Notification created in tenant dashboard ("New inquiry - Quote sent") — v2.0
- ✓ RAG-01: Search returns 5-8 relevant documents for context — v2.0
- ✓ RAG-02: LLM synthesizes natural, conversational response from context — v2.0
- ✓ RAG-03: Response includes specific details (names, prices, features) from documents — v2.0
- ✓ RAG-04: Handles unknown questions gracefully with honest acknowledgment — v2.0

### Active

None - v2.0 milestone complete.

### Out of Scope

- Rebuilding FAISS index from UI — read-only index is acceptable
- Adding new destinations/hotels — focus on pipeline, not data
- Major refactoring of multi-tenant architecture — working fine
- Real-time chat/WebSocket — async email pipeline is sufficient

## Context

**Current State:**
1. **Inbound Email Pipeline (BROKEN)**: Emails sent to tenant SendGrid subusers (e.g., final-itc-3@zorah.ai) should trigger automatic quote generation. Currently no quotes are being generated or sent.

2. **Helpdesk RAG (POOR QUALITY)**: FAISS searches work but responses are robotic, list-like dumps of search results instead of natural, helpful answers.

**Expected Inbound Email Flow:**
```
Customer Email → SendGrid Inbound Parse → Webhook → Tenant Lookup →
Email Parser (LLM) → Quote Generator → Email Sender → Notification
```

**Expected Helpdesk Behavior:**
- User asks: "What hotels do you have in Zanzibar with beach access?"
- Current: Returns list of search results
- Required: Natural response recommending specific properties with features

**Technical Environment:**
- Backend: FastAPI (Python 3.11) on Cloud Run
- Frontend: React + Vite + Tailwind CSS
- Database: Supabase (PostgreSQL with RLS)
- Vector Store: FAISS index in GCS bucket `zorah-faiss-index`
- Embeddings: sentence-transformers `all-mpnet-base-v2` (768 dimensions)
- Email: SendGrid with subusers per tenant
- LLM: OpenAI GPT-4o-mini for parsing and responses

## Constraints

- **Surgical Changes**: All changes must be production-ready, no breaking changes
- **Edge Cases**: Every edge case must be handled with comprehensive logging
- **SendGrid Subusers**: Emails MUST be sent via tenant's subuser, not main account
- **Response Time**: Helpdesk responses < 3 seconds
- **Memory**: Stay within Cloud Run limits (FAISS + sentence-transformers ~500MB)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use GPT-4o-mini for email parsing | Fast, cheap, good at structured extraction | — Pending |
| Fallback rule-based parser | Handles cases where LLM fails | — Pending |
| Send via tenant SendGrid subuser | Maintains tenant branding and deliverability | — Pending |
| Return 5-8 documents for RAG context | More context = better synthesis | — Pending |
| Temperature 0.7 for helpdesk | Natural variation without hallucination | — Pending |

---
*Last updated: 2026-01-17 - v2.0 milestone complete*
