# Multi-Tenant AI Travel Platform - Bug Fixes & Optimizations

## What This Is

A multi-tenant AI-powered travel platform for property management companies, featuring helpdesk AI with RAG (FAISS), quote generation, invoicing, CRM, and email processing. The platform has two frontends: tenant dashboard for daily operations and internal admin for Zorah team management.

## Core Value

Reliable AI-powered helpdesk that answers tenant property queries using FAISS vector search over 98K+ documents, with fast dashboard experiences for both tenants and admins.

## Requirements

### Validated

- ✓ Multi-tenant architecture with X-Client-ID isolation — existing
- ✓ JWT authentication via Supabase — existing
- ✓ FAISS vector search with 98,086 documents loaded from GCS — existing
- ✓ Quote generation agent with PDF output — existing
- ✓ Invoice management with Stripe integration — existing
- ✓ CRM with leads and contacts — existing
- ✓ Email processing via SendGrid webhooks — existing
- ✓ Internal admin platform with tenant management — existing
- ✓ Helpdesk FAISS integration (public endpoints) — Phase 1

### Active

- [ ] Issue 2: Tenant dashboard slow performance (multiple API calls, no caching)
- [ ] Issue 3: Admin revenue showing $0 (paid_at field not set correctly)
- [ ] Issue 5: Admin platform slow loading (multiple API calls on mount)

### Out of Scope

- Major refactoring of multi-tenant architecture — working fine, just needs optimization
- Rebuilding FAISS index from UI — read-only index is acceptable for now
- Adding new features — focus on fixing existing issues only

## Context

**Current Issues Identified:**
1. **Helpdesk** (FIXED): Was returning hardcoded responses instead of FAISS RAG search due to auth issues. Fixed by making endpoints public.
2. **Tenant Dashboard Performance**: Multiple API calls on mount, no caching, slow perceived loading.
3. **Admin Revenue**: Invoice `paid_at` field may not be set correctly, causing $0 revenue display.
4. **Admin Knowledge Base** (FIXED): Now displays FAISS index stats (98,086 vectors, document count, bucket info).
5. **Admin Platform Loading**: Similar to tenant dashboard - multiple API calls, no lazy loading.

**Technical Environment:**
- Backend: FastAPI (Python 3.11) on Cloud Run
- Frontend: React + Vite + Tailwind CSS
- Database: Supabase (PostgreSQL with RLS)
- Vector Store: FAISS index in GCS bucket `zorah-faiss-index`
- Embeddings: sentence-transformers `all-mpnet-base-v2` (768 dimensions)
- Email: SendGrid with subusers per tenant

**Known Technical Debt (from CONCERNS.md):**
- FAISS loads 98K vectors on startup (~100 seconds cold start)
- Hardcoded admin token in `src/api/admin_routes.py`
- No automated test suite
- Some endpoints return generic errors

## Constraints

- **Tech Stack**: Must use existing stack (FastAPI, React, Supabase) — no new frameworks
- **Performance**: Dashboard pages should load perceived content in <2 seconds
- **Backwards Compatibility**: No breaking changes to API contracts
- **Memory**: FAISS + sentence-transformers is ~500MB, must stay within Cloud Run limits

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Make helpdesk endpoints public | Prevents 401 errors with expired JWT tokens | ✓ Good |
| Use optional auth for helpdesk | Allows both authenticated and anonymous queries | ✓ Good |
| Add FAISS stats to admin knowledge base | Provides visibility into vector index health | ✓ Good |
| Focus on caching for performance | Simpler than restructuring API calls | — Pending |

---
*Last updated: 2026-01-16 after GSD initialization*
