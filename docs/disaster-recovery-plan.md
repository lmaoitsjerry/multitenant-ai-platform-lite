# Disaster Recovery Plan

## Overview

This document outlines the disaster recovery (DR) procedures for the Multi-Tenant AI Travel Platform. It covers data backup, service restoration, and communication protocols.

**Last Updated:** 2026-02-02
**Owner:** Platform Engineering
**Review Cadence:** Quarterly

---

## 1. Service Architecture

| Component | Provider | Region | DR Strategy |
|-----------|----------|--------|-------------|
| API Server | Google Cloud Run | TBD | Multi-region deployment |
| Database | Supabase (PostgreSQL) | TBD | Supabase point-in-time recovery |
| File Storage | Google Cloud Storage | TBD | Multi-region buckets |
| BigQuery | Google BigQuery | TBD | Dataset snapshots |
| Email | SendGrid | N/A | Provider-managed redundancy |
| Vector Search | FAISS (in-memory) | N/A | Rebuilt from source documents |
| DNS | Cloudflare | Global | Anycast, automatic failover |

## 2. Recovery Objectives

| Metric | Target | Current |
|--------|--------|---------|
| **RTO** (Recovery Time Objective) | < 1 hour | TBD - measure during DR drill |
| **RPO** (Recovery Point Objective) | < 15 minutes | Supabase continuous backup |
| **MTTR** (Mean Time To Recovery) | < 30 minutes | TBD |

## 3. Backup Strategy

### 3.1 Database (Supabase/PostgreSQL)

- **Automatic:** Supabase provides point-in-time recovery (PITR) with WAL archiving.
- **Manual Snapshots:** Take manual snapshot before major deployments via Supabase dashboard.
- **Retention:** 30 days (Supabase Pro plan).
- **Verification:** Monthly restore test to a staging environment.

### 3.2 Application Code

- **Source:** Git repository (GitHub) with branch protection on `master`.
- **Container Images:** Stored in Google Artifact Registry with 90-day retention.
- **Configuration:** Client YAML configs stored in repository. Secrets in environment variables (never in code).

### 3.3 File Storage (GCS)

- **Strategy:** Versioned buckets with lifecycle policy.
- **Cross-Region:** Enable multi-region storage class for critical buckets.
- **Retention:** 90 days for deleted objects.

### 3.4 BigQuery

- **Strategy:** Dataset snapshots before schema migrations.
- **Export:** Weekly export to GCS as Parquet files.

## 4. Disaster Scenarios

### Scenario A: Database Corruption/Loss

1. **Detect:** Health check `/health/ready` returns `database: unhealthy`.
2. **Assess:** Check Supabase dashboard for incident status.
3. **Restore:** Use Supabase PITR to restore to last known good state.
4. **Verify:** Run `/health/ready` and spot-check recent quotes/invoices.
5. **Communicate:** Notify affected tenants via email.

### Scenario B: Cloud Run Service Outage

1. **Detect:** Health check `/health/live` unreachable; uptime monitor triggers alert.
2. **Assess:** Check GCP status dashboard.
3. **Failover:** Deploy to secondary region if primary is down.
4. **DNS:** Update Cloudflare DNS to point to secondary deployment.
5. **Verify:** Run smoke tests against new endpoint.

### Scenario C: SendGrid Outage

1. **Detect:** Circuit breaker opens for SendGrid (visible in `/health/ready`).
2. **Impact:** Email sending paused; quotes/invoices queued but not delivered.
3. **Mitigate:** Circuit breaker auto-retries after recovery timeout.
4. **Fallback:** If prolonged, configure alternative SMTP provider.

### Scenario D: Complete Data Center Loss

1. Follow Scenario A + B simultaneously.
2. Restore database from Supabase PITR.
3. Deploy application to alternate GCP region.
4. Restore GCS files from multi-region replicas.
5. Update DNS records.

## 5. Communication Plan

| Audience | Channel | Timing |
|----------|---------|--------|
| Engineering Team | Slack #incidents | Immediately on detection |
| Management | Email + Slack | Within 15 minutes |
| Affected Tenants | Email notification | Within 30 minutes |
| All Tenants | Status page update | Within 1 hour |

## 6. DR Testing

- **Frequency:** Quarterly
- **Scope:** Full restore drill including database recovery and service failover.
- **Documentation:** Record results in `docs/dr-drill-results/` with date stamp.
- **Improvements:** Action items from each drill tracked in project issues.

## 7. Escalation Contacts

| Role | Name | Contact |
|------|------|---------|
| Primary On-Call | TBD | TBD |
| Secondary On-Call | TBD | TBD |
| Engineering Lead | TBD | TBD |
| Supabase Support | N/A | support@supabase.io |
| GCP Support | N/A | GCP Console |

---

**Action Items:**
- [ ] Fill in region assignments after deployment topology is finalized
- [ ] Schedule first DR drill
- [ ] Set up uptime monitoring for `/health/live` and `/health/ready`
- [ ] Configure Supabase PITR and verify backup retention
- [ ] Populate escalation contacts
