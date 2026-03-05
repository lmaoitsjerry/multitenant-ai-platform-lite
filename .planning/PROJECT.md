# Multi-Tenant AI Travel Platform

## What This Is

A multi-tenant AI-powered travel platform for property management companies, featuring helpdesk AI with RAG (FAISS), quote generation, invoicing, CRM, and email processing. The platform has two frontends: tenant dashboard for daily operations and internal admin for Zorah team management. Production-hardened with security controls, scalable infrastructure, and CI/CD automation.

## Core Value

Production-ready multi-tenant AI travel platform with secure tenant isolation, automated email-to-quote pipeline, and natural helpdesk responses.

## Current State

**Latest Milestone:** v5.0 Production Readiness Audit (shipped 2026-01-23)
**Status:** Production-ready, staging deployment

**v5.0 Delivered:**
- Thread-safe caching (lru_cache, double-check locking)
- Timing-safe auth (hmac.compare_digest)
- N+1 query elimination (batch queries)
- Circuit breaker + retry for OpenAI
- 10s timeouts on Supabase queries
- Response models, Redis caching, CORS from env

**Next Milestone Goals:** (define with /gsd:new-milestone)
- TBD

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
- ✓ PROD-01 to PROD-07: Critical fixes (thread-safe caching, timing-safe auth, N+1 queries, DB indexes, FAISS locking) — v5.0
- ✓ PROD-04/08-10/13/15/17/18: Error handling & resilience (circuit breaker, retries, timeouts, graceful degradation) — v5.0
- ✓ PROD-11/12/14/16/19/20/24: Code quality (async/sync, type hints, Redis caching, response models, CORS) — v5.0

### Active

(No active requirements — define with /gsd:new-milestone)

### Out of Scope

- Rebuilding FAISS index from UI — read-only index is acceptable
- Adding new destinations/hotels — focus on pipeline, not data
- Major refactoring of multi-tenant architecture — working fine
- Real-time chat/WebSocket — async email pipeline is sufficient
- Full TypeScript migration for frontends — deferred
- Distributed tracing (OpenTelemetry) — deferred
- Multi-GCP project consolidation — enterprise scale feature
- PROD-21: Table name constants — deferred (current scale OK)
- PROD-23: MMR O(n²) optimization — deferred (current index size OK)

## Context

**Current State (v5.0 shipped):**
- 29,200 lines of Python
- 1,554 tests, 57.5% coverage
- Production-ready with resilience patterns

**v5.0 Accomplishments:**
- 93+ issues identified in deep-dive audit
- 21 requirements completed across 3 phases (16-18)
- Thread-safe caching, timing-safe auth, batch queries
- Circuit breaker + retry for OpenAI
- 10s Supabase timeouts, graceful degradation

**Known Issues (Future Work):**
1. **Inbound Email Pipeline**: Emails to tenant subusers should trigger quote generation - currently broken
2. **Helpdesk RAG Quality**: Responses are robotic list dumps instead of natural answers
3. **PROD-21/23**: Table name constants and MMR optimization - deferred to later

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
| lru_cache for DI caching | Thread-safe, bounded memory | ✓ Good |
| hmac.compare_digest for tokens | Timing-safe comparison | ✓ Good |
| Circuit breaker for OpenAI | Resilience, prevents cascade failure | ✓ Good |
| 10s Supabase query timeout | Prevents hanging connections | ✓ Good |
| asyncio.to_thread for sync calls | Clean async/sync bridge | ✓ Good |

---
*Last updated: 2026-01-23 after v5.0 milestone*
