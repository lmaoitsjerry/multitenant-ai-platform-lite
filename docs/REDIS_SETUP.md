# Redis Setup for Rate Limiting

This document explains how to configure Redis for production rate limiting on Cloud Run.

## Why Redis?

The rate limiter uses in-memory storage by default, which works for single-instance deployments.
For production with multiple Cloud Run instances, Redis provides shared state so rate limits
work correctly across all instances.

## Options

### Option 1: Google Cloud Memorystore (Recommended for GCP)

[Google Cloud Memorystore for Redis](https://cloud.google.com/memorystore/docs/redis) provides
a fully managed Redis service.

**Setup:**
1. Create a Memorystore instance in the same region as Cloud Run
2. Configure VPC connector for Cloud Run to access Memorystore
3. Set REDIS_URL environment variable

```bash
# Create Memorystore instance
gcloud redis instances create zorah-rate-limit \
  --size=1 \
  --region=us-central1 \
  --redis-version=redis_7_0

# Get the IP address
gcloud redis instances describe zorah-rate-limit --region=us-central1 --format="value(host)"

# Set in Cloud Run
gcloud run services update zorah-api \
  --set-env-vars="REDIS_URL=redis://10.x.x.x:6379"
```

**Cost:** ~$35/month for basic tier (1GB)

### Option 2: Upstash (Serverless Redis)

[Upstash](https://upstash.com/) provides serverless Redis with pay-per-request pricing.
No VPC configuration needed - uses HTTPS.

**Setup:**
1. Create account at upstash.com
2. Create a Redis database
3. Copy the connection string
4. Set REDIS_URL in Cloud Run

```bash
gcloud run services update zorah-api \
  --set-env-vars="REDIS_URL=rediss://default:xxx@xxx.upstash.io:6379"
```

**Cost:** Free tier available (10K commands/day), then $0.2/100K commands

### Option 3: Redis Cloud

[Redis Cloud](https://redis.com/cloud/overview/) by Redis Labs offers managed Redis.

**Setup:** Similar to Upstash - create database, get connection string, set env var.

**Cost:** Free tier (30MB), paid plans from $5/month

## Configuration

Set the `REDIS_URL` environment variable in your Cloud Run service:

```bash
# Format: redis://[username:password@]host:port[/db]
REDIS_URL=redis://10.0.0.5:6379
REDIS_URL=rediss://user:pass@host:6379  # TLS (note: rediss with double s)
```

## Verifying Redis Connection

Check the `/health` endpoint or logs for rate limiter status:

```json
{
  "backend": "redis",
  "redis_connected": true,
  "message": "Redis rate limiting active"
}
```

You can also call the status programmatically:

```python
from src.middleware.rate_limiter import get_rate_limit_store_info
print(get_rate_limit_store_info())
```

If Redis is not available, the system automatically falls back to in-memory rate limiting
with a warning in logs.

## Fallback Behavior

If Redis is unavailable:
1. Rate limiter falls back to in-memory storage
2. Warning logged: "Redis not available, falling back to in-memory"
3. Rate limits work but only per-instance (not shared across instances)

This means the system degrades gracefully - API remains functional, just with
potentially higher effective rate limits during Redis outages.

## Testing Locally

```bash
# Start Redis locally
docker run -d -p 6379:6379 redis:7

# Set environment variable
export REDIS_URL=redis://localhost:6379

# Run the application
python main.py
# Should see: "Connected to Redis for rate limiting"
```

## Security Considerations

1. **Password Protection:** Always use authenticated Redis in production
2. **TLS:** Use `rediss://` (with double s) for encrypted connections
3. **Logging:** The rate limiter masks passwords in log output
4. **VPC:** For Memorystore, use VPC connector to keep traffic private
