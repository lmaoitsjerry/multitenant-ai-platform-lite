# Incident Response Runbook

## Purpose

Step-by-step guide for handling production incidents affecting the Multi-Tenant AI Travel Platform.

---

## 1. Severity Levels

| Level | Definition | Response Time | Examples |
|-------|-----------|---------------|----------|
| **SEV1** | Complete service outage; all tenants affected | 15 minutes | API unreachable, database down |
| **SEV2** | Major feature broken; multiple tenants affected | 30 minutes | Quote generation failing, email not sending |
| **SEV3** | Minor feature degraded; single tenant affected | 2 hours | Slow BigQuery queries, one tenant's config error |
| **SEV4** | Cosmetic or non-urgent issue | Next business day | UI glitch, log noise |

## 2. Detection

### Automated Alerts

- **Prometheus/Alertmanager:** High error rate, latency spikes (see `docs/alerting-rules.yaml`)
- **Uptime Monitor:** `/health/live` and `/health/ready` checks
- **Circuit Breakers:** `/health/ready` response includes circuit breaker states

### Manual Detection

- Customer reports via support email
- Internal team observation
- Log analysis via structured JSON logs

## 3. Response Procedure

### Step 1: Acknowledge

- Acknowledge the alert in the monitoring system.
- Post in Slack `#incidents`: "Investigating [brief description]".
- Assign an Incident Commander (IC).

### Step 2: Assess

- Check `/health/ready` for component status.
- Check `/metrics` for error rates and latency.
- Review structured logs (filter by `request_id` or `tenant_id`).
- Determine severity level.

### Step 3: Communicate

- Update Slack `#incidents` with severity and estimated scope.
- For SEV1/SEV2: Notify management and affected tenants.

### Step 4: Mitigate

- **If deployment-related:** Roll back to previous container image.
  ```bash
  # List recent revisions
  gcloud run revisions list --service=multitenant-platform --region=REGION

  # Route traffic to previous revision
  gcloud run services update-traffic multitenant-platform \
    --to-revisions=PREVIOUS_REVISION=100 --region=REGION
  ```

- **If database-related:** Check Supabase dashboard; consider PITR restore.

- **If external service (SendGrid, Travel Platform):**
  - Circuit breakers will auto-isolate the failing service.
  - Check `/health/ready` for circuit breaker state.
  - Manual circuit breaker reset: restart the application.

- **If single tenant:** Check tenant configuration in `clients/<tenant>/config.yaml`.

### Step 5: Resolve

- Confirm the fix via health checks and monitoring.
- Clear any manual overrides (DNS changes, traffic routing).

### Step 6: Post-Incident

- Post resolution update in Slack `#incidents`.
- Create post-incident review document within 48 hours.
- Template: [Post-Incident Review Template](#post-incident-review-template)

## 4. Rollback Procedure

### Application Rollback

```bash
# 1. Identify the last known good commit
git log --oneline -10

# 2. Deploy previous version
# (via CI/CD pipeline or manual Cloud Run deploy)
gcloud run deploy multitenant-platform \
  --image=REGISTRY/multitenant-platform:PREVIOUS_TAG \
  --region=REGION
```

### Database Rollback

1. Go to Supabase Dashboard > Database > Backups.
2. Select point-in-time before the incident.
3. Restore to a new project for verification.
4. If verified, restore to production.

**WARNING:** Database rollback may cause data loss for transactions after the restore point.

## 5. Common Issues & Quick Fixes

| Symptom | Likely Cause | Quick Fix |
|---------|-------------|-----------|
| 429 on login | Account lockout (10 failures) | Wait 15 min or restart server to clear in-memory state |
| 503 on `/health/ready` | Database or BigQuery unreachable | Check Supabase/GCP status pages |
| Circuit breaker OPEN | Repeated failures to external service | Wait for recovery timeout; check service status |
| CORS errors in browser | Missing origin in CORS config | Add origin to `CORS_ORIGINS` env var |
| 413 Request Too Large | Payload exceeds 10MB/50MB limit | Check file size; adjust `RequestSizeMiddleware` if needed |
| JWT "invalid audience" | Token missing `aud: authenticated` | Verify Supabase auth config; check token generation |

## 6. Useful Commands

```bash
# Check application health
curl https://API_HOST/health/ready

# View Prometheus metrics
curl https://API_HOST/metrics

# Tail structured logs (Cloud Run)
gcloud run services logs read multitenant-platform --region=REGION --limit=50

# Check recent deployments
gcloud run revisions list --service=multitenant-platform --region=REGION
```

---

## Post-Incident Review Template

```markdown
# Post-Incident Review: [Title]

**Date:** YYYY-MM-DD
**Severity:** SEV[1-4]
**Duration:** X hours Y minutes
**Incident Commander:** [Name]

## Summary
[1-2 sentence description of what happened]

## Timeline
- HH:MM - [Event]
- HH:MM - [Event]

## Root Cause
[What caused the incident]

## Impact
- Tenants affected: [count]
- Duration of impact: [time]
- Data loss: [yes/no, details]

## Resolution
[What was done to fix it]

## Action Items
- [ ] [Preventive measure 1]
- [ ] [Preventive measure 2]

## Lessons Learned
[What we learned and would do differently]
```
