# Multi-Tenant AI Travel Platform

## What This Is

A multi-tenant AI-powered travel platform for property management companies, featuring helpdesk AI with RAG (FAISS), quote generation, invoicing, CRM, and email processing. The platform has two frontends: tenant dashboard for daily operations and internal admin for Zorah team management. Production-hardened with security controls, scalable infrastructure, and CI/CD automation.

## Core Value

Production-ready multi-tenant AI travel platform with secure tenant isolation, automated email-to-quote pipeline, and natural helpdesk responses.

## Current Milestone: v5.0 Production Readiness Audit

**Goal:** Comprehensive audit and optimization to prepare for production deployment.

**Focus areas:**
- **Code consistency** — Standardize patterns, remove dead code, clean up technical debt
- **Performance** — Optimize slow queries, API latency, caching gaps
- **Edge case handling** — Error handling, failure modes, graceful degradation

**Approach:**
1. Verify codebase mapping is current
2. Define production-ready criteria based on audit findings
3. Execute optimization phases systematically

**Status:** Staging only — free to refactor without breaking live users

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
- ✓ SEC-01 to SEC-05: Security hardening (tenant validation, headers, error sanitization) — v3.0
- ✓ SCALE-01 to SCALE-03: Scalability (DB tenant registry, Redis rate limiting/caching) — v3.0
- ✓ DEVOPS-01 to DEVOPS-03: CI/CD, non-root Docker, structured logging — v3.0
- ✓ TEST-01 to TEST-03: Auth, rate limiting, tenant isolation tests — v3.0
- ✓ COVER-01 to COVER-05: External API mocking (BigQuery, Twilio, SendGrid, LLM agents) — v4.0
- ✓ TEST-04: 57.5% test coverage achieved with 1,554 tests — v4.0

### Active

- [ ] AUDIT-01: Verify and update codebase mapping
- [ ] AUDIT-02: Define production-ready criteria from audit findings
- [ ] CODE-01: Standardize code patterns and remove inconsistencies
- [ ] CODE-02: Remove dead code and technical debt
- [ ] PERF-01: Optimize slow database queries and API latency
- [ ] PERF-02: Review and optimize caching strategy
- [ ] EDGE-01: Audit and improve error handling across codebase
- [ ] EDGE-02: Ensure graceful degradation for failure modes

### Out of Scope

- Rebuilding FAISS index from UI — read-only index is acceptable
- Adding new destinations/hotels — focus on pipeline, not data
- Major refactoring of multi-tenant architecture — working fine
- Real-time chat/WebSocket — async email pipeline is sufficient
- Full TypeScript migration for frontends — deferred to v5.0
- Distributed tracing (OpenTelemetry) — deferred to v5.0
- Multi-GCP project consolidation — enterprise scale feature

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
| Temperature 0.7 for helpdesk | Natural variation without hallucination | ✓ Good |
| 45% coverage baseline for v3.0 | 70% requires 20-25hrs for external API mocking | ✓ Good |
| Database-backed tenant config | Scalability over file-based YAML | ✓ Good |
| Redis rate limiting with fallback | Production resilience | ✓ Good |

---
*Last updated: 2026-01-23 — v5.0 Production Readiness Audit started*
