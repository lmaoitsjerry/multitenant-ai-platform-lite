# Roadmap: Inbound Email Auto-Quote & Helpdesk RAG Enhancement

## Overview

Fix two critical systems: (1) Inbound email pipeline that should auto-generate and send quotes, (2) Helpdesk RAG that should return natural, helpful responses instead of robotic lists.

## Phases

- [x] **Phase 1: Diagnostics & Logging** - Verify current state, add logging, test webhook accessibility
- [x] **Phase 2: Tenant Lookup & Email Parsing** - Robust tenant lookup, LLM-powered email parser
- [x] **Phase 3: Quote Generation Pipeline** - Connect parser to quote generator, create quotes
- [x] **Phase 4: Email Sending & Notifications** - Send quotes via SendGrid subuser, create notifications
- [x] **Phase 5: Helpdesk RAG Enhancement** - Natural responses with context synthesis
- [ ] **Phase 6: Integration Testing** - End-to-end verification, production deployment

## Phase Details

### Phase 1: Diagnostics & Logging
**Goal:** Understand current state of inbound email pipeline, add comprehensive logging
**Depends on:** Nothing (first phase)
**Requirements:** EMAIL-01
**Success Criteria** (what must be TRUE):
  1. Webhook endpoint exists and is accessible from external
  2. SendGrid Inbound Parse configuration documented
  3. Comprehensive logging added to webhook endpoint
  4. Current failure point identified with evidence
**Research:** Check SendGrid dashboard, MX records, Cloud Run logs
**Plans:** 1 plan

Plans:
- [x] 01-01: Diagnose inbound email pipeline + add logging

### Phase 2: Tenant Lookup & Email Parsing
**Goal:** Emails correctly routed to tenants and parsed for trip details
**Depends on:** Phase 1 (need working webhook first)
**Requirements:** EMAIL-02, EMAIL-03
**Success Criteria** (what must be TRUE):
  1. Tenant found by support_email OR sendgrid_username@zorah.ai
  2. Email parser extracts: destination, dates, travelers, budget
  3. Fallback rule-based parser handles LLM failures
  4. Edge cases handled (malformed emails, missing fields)
**Research:** Unlikely (existing patterns)
**Plans:** 2 plans

Plans:
- [x] 02-01: Implement robust tenant lookup by email address
- [x] 02-02: Implement LLM-powered email parser with fallback

### Phase 3: Quote Generation Pipeline
**Goal:** Parsed trip details become quote records in database
**Depends on:** Phase 2 (need parsed trip details)
**Requirements:** EMAIL-04
**Success Criteria** (what must be TRUE):
  1. Quote created with correct destination, dates, travelers
  2. Hotels queried for destination
  3. Pricing calculated from rates
  4. Quote record saved to database with status "draft"
**Research:** Unlikely (existing quote generation code)
**Plans:** 1 plan

Plans:
- [x] 03-01: Connect email parser to quote generator

### Phase 4: Email Sending & Notifications
**Goal:** Quotes sent to customers, notifications shown in dashboard
**Depends on:** Phase 3 (need generated quote)
**Requirements:** EMAIL-05, EMAIL-06
**Success Criteria** (what must be TRUE):
  1. Email sent via tenant's SendGrid subuser (not main account)
  2. Quote email includes quote details and PDF attachment
  3. Notification created for tenant dashboard
  4. Quote status updated to "sent"
**Research:** Unlikely (existing SendGrid integration)
**Plans:** 1 plan (consolidated - existing infrastructure covers most requirements)

Plans:
- [x] 04-01: Quote approval and sending workflow

### Phase 5: Helpdesk RAG Enhancement
**Goal:** Natural, helpful responses instead of robotic lists
**Depends on:** Nothing (independent of email pipeline)
**Requirements:** RAG-01, RAG-02, RAG-03, RAG-04
**Success Criteria** (what must be TRUE):
  1. Search returns 5-8 relevant documents
  2. Response is conversational, not list-like
  3. Response includes specific details from context
  4. Unknown questions handled gracefully
  5. Response time < 3 seconds
**Research:** Unlikely (existing FAISS + OpenAI patterns)
**Plans:** 2 plans

Plans:
- [x] 05-01: Enhance FAISS search to return more context
- [x] 05-02: Implement RAG response generation with natural tone

### Phase 6: Integration Testing
**Goal:** End-to-end verification of both systems
**Depends on:** Phases 1-5 (all features complete)
**Requirements:** All EMAIL-*, RAG-*
**Success Criteria** (what must be TRUE):
  1. Email → Quote → Notification pipeline works end-to-end
  2. Helpdesk returns natural responses for various queries
  3. No regressions in existing functionality
  4. Production deployment successful
**Research:** None
**Plans:** 1 plan

Plans:
- [ ] 06-01: End-to-end integration testing and deployment

## Progress

| Phase | Plans | Status |
|-------|-------|--------|
| 1. Diagnostics & Logging | 1/1 | Complete |
| 2. Tenant Lookup & Email Parsing | 2/2 | Complete |
| 3. Quote Generation Pipeline | 1/1 | Complete |
| 4. Email Sending & Notifications | 1/1 | Complete |
| 5. Helpdesk RAG Enhancement | 2/2 | Complete |
| 6. Integration Testing | 0/1 | Not Started |

---
*Created: 2026-01-16*
*Milestone: v2.0 - Inbound Email & Helpdesk RAG*
