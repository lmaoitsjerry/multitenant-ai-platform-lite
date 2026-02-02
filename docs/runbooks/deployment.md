# Deployment Runbook

## Purpose

Standard procedures for deploying the Multi-Tenant AI Travel Platform to production.

---

## 1. Pre-Deployment Checklist

- [ ] All tests pass locally: `pytest tests/ -v --tb=short`
- [ ] CI pipeline is green on the target branch
- [ ] No open SEV1/SEV2 incidents
- [ ] Database migrations reviewed and tested (if applicable)
- [ ] Environment variables updated (if new ones added)
- [ ] Rollback plan confirmed (previous container image tag noted)
- [ ] Team notified in Slack `#deployments`

## 2. Deployment Methods

### 2.1 Automatic (CI/CD Pipeline)

The standard deployment path is via the GitHub Actions CI/CD pipeline.

1. Merge PR to `master` branch.
2. CI runs tests, Bandit SAST scan, and pip-audit.
3. On success, build and push container image.
4. Deploy to Cloud Run with traffic routing.

### 2.2 Manual (Emergency)

For hotfixes when CI is unavailable:

```bash
# 1. Build container image
docker build -t REGISTRY/multitenant-platform:TAG .

# 2. Push to registry
docker push REGISTRY/multitenant-platform:TAG

# 3. Deploy to Cloud Run
gcloud run deploy multitenant-platform \
  --image=REGISTRY/multitenant-platform:TAG \
  --region=REGION \
  --set-env-vars="ENVIRONMENT=production"
```

## 3. Database Migrations

### Before Deploying

1. Review migration SQL in `database/migrations/`.
2. Test migration against a staging database.
3. Take a manual Supabase snapshot before applying.

### Applying Migrations

```bash
# Via Supabase CLI
supabase db push

# Or manually via SQL editor in Supabase Dashboard
```

### Rollback

- Use Supabase PITR if migration causes issues.
- Keep rollback SQL scripts alongside migration files when possible.

## 4. Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SUPABASE_URL` | Supabase project URL | `https://xxx.supabase.co` |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | `eyJ...` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `SENDGRID_API_KEY` | SendGrid API key | `SG....` |
| `ENVIRONMENT` | Deployment environment | `production` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CORS_ORIGINS` | Comma-separated allowed origins | Development defaults |
| `ENABLE_TRACING` | Enable OpenTelemetry tracing | `false` |
| `PII_AUDIT_ENABLED` | Enable PII access audit logging | `true` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `JSON_LOGS` | Enable JSON structured logging | `true` |
| `VITE_SENTRY_DSN` | Frontend Sentry DSN (frontend) | Empty (disabled) |

### Updating Environment Variables

```bash
# Cloud Run
gcloud run services update multitenant-platform \
  --set-env-vars="KEY=VALUE" \
  --region=REGION

# Multiple variables
gcloud run services update multitenant-platform \
  --set-env-vars="KEY1=VALUE1,KEY2=VALUE2" \
  --region=REGION
```

## 5. Post-Deployment Verification

### Health Checks

```bash
# Liveness
curl -f https://API_HOST/health/live

# Readiness (checks database + BigQuery + circuit breakers)
curl -s https://API_HOST/health/ready | python -m json.tool

# Metrics endpoint
curl -s https://API_HOST/metrics | head -20
```

### Smoke Tests

1. **Login:** POST to `/api/v1/auth/login` with test credentials.
2. **Quote list:** GET `/api/v1/quotes` with valid auth token.
3. **Knowledge search:** POST `/api/v1/knowledge/search` with a test query.
4. **Client info:** GET `/api/v1/client/info` with `X-Client-ID` header.

### Monitoring

- Watch Prometheus metrics for error rate spike in first 15 minutes.
- Check structured logs for unexpected errors.
- Verify circuit breakers remain in CLOSED state.

## 6. Rollback Procedure

If post-deployment verification fails:

```bash
# 1. Route traffic to previous revision (instant)
gcloud run services update-traffic multitenant-platform \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region=REGION

# 2. Investigate the issue
# 3. Fix, test, and redeploy
```

## 7. Multi-Tenant Considerations

- **Config changes** affect only the targeted tenant (via `clients/<tenant>/config.yaml`).
- **Schema migrations** affect all tenants sharing the same Supabase instance.
- **Feature flags** (if added) can be used for tenant-specific rollouts.
- Always verify changes with at least two different tenant IDs.

## 8. Frontend Deployment

The React frontend (tenant-dashboard) is deployed separately:

```bash
cd frontend/tenant-dashboard

# Build
npm run build

# Deploy (e.g., to Cloudflare Pages, Vercel, or GCS bucket)
# Specific command depends on hosting provider
```

### Frontend Environment Variables

Set at build time via `.env.production`:

```
VITE_API_BASE_URL=https://API_HOST
VITE_SENTRY_DSN=https://xxx@sentry.io/xxx  # Optional
```
