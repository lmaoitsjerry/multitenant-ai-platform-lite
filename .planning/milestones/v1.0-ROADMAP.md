# Roadmap: Multi-Tenant AI Platform Bug Fixes

## Overview

Fix performance issues and data accuracy bugs across the tenant dashboard and admin platform. Three phases targeting dashboard loading speed and revenue calculation accuracy.

## Phases

- [x] **Phase 1: Tenant Dashboard Performance** - Fix slow loading with caching and lazy loading
- [x] **Phase 2: Invoice Revenue Fix** - Fix paid_at field and revenue calculations
- [x] **Phase 3: Admin Platform Performance** - Optimize admin dashboard loading

## Phase Details

### Phase 1: Tenant Dashboard Performance
**Goal**: Tenant dashboard loads quickly with responsive UI
**Depends on**: Nothing (first phase)
**Requirements**: PERF-01, PERF-03
**Success Criteria** (what must be TRUE):
  1. Dashboard page renders initial content within 500ms
  2. API calls are batched or parallelized where possible
  3. Skeleton loaders show during data fetches
  4. No duplicate API calls on page mount
**Research**: Unlikely (React patterns, existing codebase)
**Plans**: 2 plans

Plans:
- [x] 01-01: Non-blocking Layout + stale-while-revalidate for clientInfo
- [ ] 01-02: Optimize warmCache + verify performance

### Phase 2: Invoice Revenue Fix
**Goal**: Revenue calculations show accurate data
**Depends on**: Nothing (independent)
**Requirements**: DATA-01, DATA-02
**Success Criteria** (what must be TRUE):
  1. Invoice `paid_at` timestamp is set when payment webhook received
  2. Admin revenue dashboard shows sum of paid invoices
  3. Revenue chart displays accurate historical data
**Research**: Unlikely (existing Supabase/Stripe patterns)
**Plans**: 2 plans

Plans:
- [x] 02-01: Fix invoice paid_at field + admin revenue calculation

### Phase 3: Admin Platform Performance
**Goal**: Admin platform loads quickly
**Depends on**: Phase 1 (reuse patterns)
**Requirements**: PERF-02
**Success Criteria** (what must be TRUE):
  1. Admin dashboard renders initial content within 500ms
  2. Tenant list loads with pagination
  3. Analytics data loads progressively
**Research**: Unlikely (same patterns as Phase 1)
**Plans**: 1 plan

Plans:
- [x] 03-01: Apply caching and lazy loading to admin dashboard

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Tenant Dashboard Performance | 1/1 | Complete | 2026-01-16 |
| 2. Invoice Revenue Fix | 1/1 | Complete | 2026-01-16 |
| 3. Admin Platform Performance | 1/1 | Complete | 2026-01-16 |

---
*Created: 2026-01-16*
