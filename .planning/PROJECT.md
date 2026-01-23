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

**Blocking (Must Fix):**
- [ ] BLOCK-01: Fix race condition in DI caching (`routes.py:132-150`)
- [ ] BLOCK-02: Fix admin token timing attack vulnerability (`admin_routes.py:71-97`)
- [ ] BLOCK-03: Fix N+1 queries in CRM search (`crm_service.py:290-334`)
- [ ] BLOCK-04: Add circuit breaker + retry for OpenAI API
- [ ] BLOCK-05: Remove 15 bare exception handlers (8 in `email_webhook.py`, 7 in `analytics_routes.py`)
- [ ] BLOCK-06: Add database indexes for common query patterns
- [ ] BLOCK-07: Fix FAISS singleton thread safety
- [ ] BLOCK-08: Implement deletion operations in provisioning service

**High Priority:**
- [ ] HIGH-01: Standardize error handling on `safe_error_response()` pattern
- [ ] HIGH-02: Remove unused `logger.py`, use structured_logger everywhere
- [ ] HIGH-03: Fix async/sync mismatch in `admin_tenants_routes.py`
- [ ] HIGH-04: Add type hints to all public functions
- [ ] HIGH-05: Replace pipeline_summary with database aggregation
- [ ] HIGH-06: Add Redis caching for expensive operations (60s TTL)
- [ ] HIGH-07: Add timeouts to all Supabase queries (5-10 seconds)
- [ ] HIGH-08: Add bounds checking to all array/dict accesses
- [ ] HIGH-09: Implement graceful degradation when OpenAI unavailable
- [ ] HIGH-10: Add retry logic for GCS downloads

**Medium Priority:**
- [ ] MED-01: Standardize response format across all endpoints
- [ ] MED-02: Deduplicate PDF building code (3 locations)
- [ ] MED-03: Centralize table name constants
- [ ] MED-04: Add cache TTL to config/agent/service caches
- [ ] MED-05: Optimize MMR search O(n^2) complexity
- [ ] MED-06: Move CORS origins to environment variables

### Out of Scope

- Rebuilding FAISS index from UI — read-only index is acceptable
- Adding new destinations/hotels — focus on pipeline, not data
- Major refactoring of multi-tenant architecture — working fine
- Real-time chat/WebSocket — async email pipeline is sufficient
- Full TypeScript migration for frontends — deferred to v6.0
- Distributed tracing (OpenTelemetry) — deferred to v6.0
- Multi-GCP project consolidation — enterprise scale feature
- Fixing broken email pipeline — address after production hardening
- Helpdesk RAG quality improvements — address after production hardening

## Context

**v5.0 Audit Summary (2026-01-23):**

Deep-dive audit completed across code consistency, performance, and error handling. Full report: `.planning/PRODUCTION-AUDIT.md`

| Area | Issues | Critical | High | Medium |
|------|--------|----------|------|--------|
| Code Consistency | 25+ | 2 | 5 | 18 |
| Performance | 21 | 4 | 8 | 9 |
| Error Handling | 47+ | 8 | 12 | 27 |

**Key Findings:**
- Race conditions in dependency injection caching and FAISS singleton
- N+1 query patterns adding 1-5s latency to CRM operations
- 15 bare exception handlers swallowing errors silently
- No circuit breaker for OpenAI API (helpdesk crashes on outage)
- Missing database indexes on common query patterns

**Known Issues (Deferred to Later):**
1. **Inbound Email Pipeline**: Emails to tenant subusers should trigger quote generation - currently broken
2. **Helpdesk RAG Quality**: Responses are robotic list dumps instead of natural answers

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
*Last updated: 2026-01-23 — v5.0 deep-dive audit complete, production criteria defined*
