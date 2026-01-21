"""
Rate Limiting Middleware for Multi-Tenant API

Provides per-tenant rate limiting with configurable limits.
Uses in-memory storage for development, Redis for production.

Usage:
    from src.middleware.rate_limiter import RateLimiter, rate_limit
    
    # Add to FastAPI app
    app.add_middleware(RateLimitMiddleware)
    
    # Or use decorator on specific endpoints
    @rate_limit(requests=10, window=60)
    async def my_endpoint():
        pass
"""

import time
import logging
from typing import Dict, Optional, Callable
from functools import wraps
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import Request, HTTPException, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitStore:
    """Base class for rate limit storage"""
    
    def get_count(self, key: str) -> int:
        raise NotImplementedError
    
    def increment(self, key: str, window_seconds: int) -> int:
        raise NotImplementedError
    
    def reset(self, key: str):
        raise NotImplementedError


class InMemoryRateLimitStore(RateLimitStore):
    """In-memory rate limit storage (for development)"""
    
    def __init__(self):
        self._counts: Dict[str, int] = defaultdict(int)
        self._expiry: Dict[str, float] = {}
    
    def _clean_expired(self):
        """Remove expired entries"""
        now = time.time()
        expired = [k for k, exp in self._expiry.items() if exp < now]
        for k in expired:
            del self._counts[k]
            del self._expiry[k]
    
    def get_count(self, key: str) -> int:
        self._clean_expired()
        if key in self._expiry and self._expiry[key] < time.time():
            del self._counts[key]
            del self._expiry[key]
            return 0
        return self._counts.get(key, 0)
    
    def increment(self, key: str, window_seconds: int) -> int:
        self._clean_expired()
        now = time.time()
        
        # If key doesn't exist or expired, start fresh
        if key not in self._expiry or self._expiry[key] < now:
            self._counts[key] = 1
            self._expiry[key] = now + window_seconds
            return 1
        
        # Increment existing
        self._counts[key] += 1
        return self._counts[key]
    
    def reset(self, key: str):
        if key in self._counts:
            del self._counts[key]
        if key in self._expiry:
            del self._expiry[key]


class RedisRateLimitStore(RateLimitStore):
    """Redis-based rate limit storage (for production)"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self._fallback = InMemoryRateLimitStore()
        try:
            import redis
            # Log connection (mask password)
            safe_url = redis_url.split('@')[-1] if '@' in redis_url else redis_url
            logger.info(f"Connecting to Redis at {safe_url}")

            self._redis = redis.from_url(redis_url)
            self._redis.ping()
            logger.info("Connected to Redis for rate limiting")
        except Exception as e:
            logger.warning(f"Redis not available, falling back to in-memory: {e}")
            self._redis = None

    def is_healthy(self) -> bool:
        """Check if Redis connection is healthy."""
        if not self._redis:
            return False
        try:
            self._redis.ping()
            return True
        except Exception:
            return False
    
    def get_count(self, key: str) -> int:
        if not self._redis:
            return self._fallback.get_count(key)
        
        count = self._redis.get(key)
        return int(count) if count else 0
    
    def increment(self, key: str, window_seconds: int) -> int:
        if not self._redis:
            return self._fallback.increment(key, window_seconds)
        
        pipe = self._redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds)
        results = pipe.execute()
        return results[0]
    
    def reset(self, key: str):
        if not self._redis:
            return self._fallback.reset(key)
        self._redis.delete(key)


# Global store instance
_store: Optional[RateLimitStore] = None


def get_store() -> RateLimitStore:
    """Get or create the rate limit store"""
    global _store
    if _store is None:
        # Try Redis first, fall back to in-memory
        import os
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            _store = RedisRateLimitStore(redis_url)
        else:
            _store = InMemoryRateLimitStore()
            logger.info("Using in-memory rate limiting (set REDIS_URL for production)")
    return _store


def get_rate_limit_store_info() -> dict:
    """Get information about the current rate limit store."""
    store = get_store()
    is_redis = isinstance(store, RedisRateLimitStore)
    redis_healthy = is_redis and store.is_healthy()
    return {
        "backend": "redis" if redis_healthy else "memory",
        "redis_connected": redis_healthy,
        "message": "Redis rate limiting active" if redis_healthy else "In-memory rate limiting (single instance only)"
    }


# ==================== Rate Limit Configuration ====================

class RateLimitConfig:
    """Rate limit configuration per endpoint type"""
    
    # Default limits (10x base)
    DEFAULT_REQUESTS_PER_MINUTE = 600
    DEFAULT_REQUESTS_PER_DAY = 10000
    
    # Endpoint-specific limits (requests, window_seconds)
    LIMITS = {
        # Quote endpoints (10x)
        '/api/v1/quotes/generate': (200, 3600),     # 200 per hour
        '/api/v1/quotes/chat': (1000, 3600),        # 1000 per hour
        '/api/v1/quotes': (600, 60),                # 600 per minute (list)
        
        # CRM endpoints (10x)
        '/api/v1/crm/clients': (600, 60),           # 600 per minute
        
        # Helpdesk (10x)
        '/api/v1/helpdesk/chat': (1200, 3600),      # 1200 per hour
        
        # Outbound calls (10x)
        '/api/v1/outbound/queue': (300, 3600),      # 300 per hour
        
        # Webhooks (10x - higher limits)
        '/webhooks/email': (2000, 60),              # 2000 per minute
        '/webhooks/vapi': (2000, 60),               # 2000 per minute
        
        # Onboarding (10x)
        '/api/v1/onboarding/phone': (50, 3600),     # 50 per hour (buying numbers)
    }
    
    # Daily limits by resource type
    DAILY_LIMITS = {
        'quotes': 1000,          # 10x (was 100)
        'emails': 1500,          # Custom (was 500)
        'vapi_calls': 150,       # Custom (was 50)
        'api_requests': 100000,  # 10x (was 10000)
    }
    
    @classmethod
    def get_limit(cls, path: str) -> tuple:
        """Get rate limit for a path (requests, window_seconds)"""
        # Check exact match first
        if path in cls.LIMITS:
            return cls.LIMITS[path]
        
        # Check prefix match
        for pattern, limit in cls.LIMITS.items():
            if path.startswith(pattern):
                return limit
        
        # Default
        return (cls.DEFAULT_REQUESTS_PER_MINUTE, 60)
    
    @classmethod
    def get_daily_limit(cls, resource_type: str) -> int:
        """Get daily limit for a resource type"""
        return cls.DAILY_LIMITS.get(resource_type, 1000)


# ==================== Rate Limiter ====================

class RateLimiter:
    """Rate limiter for tenant requests"""
    
    def __init__(self, store: RateLimitStore = None):
        self.store = store or get_store()
    
    def _make_key(self, tenant_id: str, endpoint: str, window: str = "minute") -> str:
        """Create rate limit key"""
        # Include time bucket for windowed counting
        if window == "minute":
            bucket = datetime.utcnow().strftime("%Y%m%d%H%M")
        elif window == "hour":
            bucket = datetime.utcnow().strftime("%Y%m%d%H")
        elif window == "day":
            bucket = datetime.utcnow().strftime("%Y%m%d")
        else:
            bucket = datetime.utcnow().strftime("%Y%m%d%H%M")
        
        return f"ratelimit:{tenant_id}:{endpoint}:{bucket}"
    
    def check_rate_limit(
        self,
        tenant_id: str,
        endpoint: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple:
        """
        Check if request is within rate limit
        
        Returns:
            (allowed: bool, current_count: int, limit: int, reset_time: int)
        """
        # Determine window type
        if window_seconds >= 86400:
            window = "day"
        elif window_seconds >= 3600:
            window = "hour"
        else:
            window = "minute"
        
        key = self._make_key(tenant_id, endpoint, window)
        current = self.store.increment(key, window_seconds)
        
        allowed = current <= max_requests
        reset_time = window_seconds  # Simplified; actual reset depends on bucket
        
        return (allowed, current, max_requests, reset_time)
    
    def is_allowed(
        self,
        tenant_id: str,
        endpoint: str,
        max_requests: int = None,
        window_seconds: int = None
    ) -> bool:
        """Simple check if request is allowed"""
        if max_requests is None or window_seconds is None:
            max_requests, window_seconds = RateLimitConfig.get_limit(endpoint)
        
        allowed, _, _, _ = self.check_rate_limit(
            tenant_id, endpoint, max_requests, window_seconds
        )
        return allowed
    
    def get_usage(self, tenant_id: str, resource_type: str = "api_requests") -> Dict:
        """Get current usage for a tenant"""
        today = datetime.utcnow().strftime("%Y%m%d")
        key = f"ratelimit:{tenant_id}:{resource_type}:{today}"
        
        current = self.store.get_count(key)
        limit = RateLimitConfig.get_daily_limit(resource_type)
        
        return {
            'resource': resource_type,
            'current': current,
            'limit': limit,
            'remaining': max(0, limit - current),
            'reset': 'midnight UTC'
        }
    
    def track_resource(self, tenant_id: str, resource_type: str, count: int = 1):
        """Track resource usage (for daily limits)"""
        today = datetime.utcnow().strftime("%Y%m%d")
        key = f"ratelimit:{tenant_id}:{resource_type}:{today}"
        
        for _ in range(count):
            self.store.increment(key, 86400)  # 24 hours


# ==================== Middleware ====================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting"""
    
    # Paths to skip rate limiting
    SKIP_PATHS = {
        '/health',
        '/health/ready',
        '/health/live',
        '/docs',
        '/openapi.json',
        '/redoc',
        '/',
    }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip certain paths
        path = request.url.path
        if path in self.SKIP_PATHS:
            return await call_next(request)
        
        # Get tenant ID
        tenant_id = request.headers.get('X-Client-ID')
        if not tenant_id:
            import os
            tenant_id = os.getenv('CLIENT_ID', 'default')
        
        # Get rate limit for this endpoint
        max_requests, window_seconds = RateLimitConfig.get_limit(path)
        
        # Check rate limit
        limiter = RateLimiter()
        allowed, current, limit, reset = limiter.check_rate_limit(
            tenant_id, path, max_requests, window_seconds
        )
        
        # Add rate limit headers
        headers = {
            'X-RateLimit-Limit': str(limit),
            'X-RateLimit-Remaining': str(max(0, limit - current)),
            'X-RateLimit-Reset': str(reset),
        }
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for {tenant_id} on {path}")
            return JSONResponse(
                status_code=429,
                content={
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Limit: {limit} per {window_seconds}s',
                    'retry_after': reset
                },
                headers=headers
            )
        
        # Process request
        response = await call_next(request)
        
        # Add headers to response
        for key, value in headers.items():
            response.headers[key] = value
        
        return response


# ==================== Decorator ====================

def rate_limit(requests: int = 60, window: int = 60):
    """
    Decorator for rate limiting specific endpoints
    
    Usage:
        @rate_limit(requests=10, window=60)
        async def my_endpoint(request: Request):
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find request in args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get('request')
            
            if request:
                tenant_id = request.headers.get('X-Client-ID', 'default')
                endpoint = request.url.path
                
                limiter = RateLimiter()
                if not limiter.is_allowed(tenant_id, endpoint, requests, window):
                    raise HTTPException(
                        status_code=429,
                        detail={
                            'error': 'Rate limit exceeded',
                            'limit': requests,
                            'window': window
                        }
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# ==================== API Endpoints for Usage Stats ====================

def get_rate_limit_router():
    """Get router for rate limit endpoints"""
    from fastapi import APIRouter, Depends
    from config.loader import ClientConfig
    
    router = APIRouter(prefix="/api/v1/usage", tags=["Usage"])
    
    @router.get("/limits")
    async def get_usage_limits(
        tenant_id: str = None,
        x_client_id: str = None
    ):
        """Get current usage and limits for tenant"""
        import os
        tenant = tenant_id or x_client_id or os.getenv('CLIENT_ID', 'default')
        
        limiter = RateLimiter()
        
        return {
            'tenant_id': tenant,
            'usage': {
                'api_requests': limiter.get_usage(tenant, 'api_requests'),
                'quotes': limiter.get_usage(tenant, 'quotes'),
                'emails': limiter.get_usage(tenant, 'emails'),
                'vapi_calls': limiter.get_usage(tenant, 'vapi_calls'),
            },
            'limits': {
                'per_minute': RateLimitConfig.DEFAULT_REQUESTS_PER_MINUTE,
                'per_day': RateLimitConfig.DEFAULT_REQUESTS_PER_DAY,
                'daily_quotes': RateLimitConfig.DAILY_LIMITS['quotes'],
                'daily_emails': RateLimitConfig.DAILY_LIMITS['emails'],
                'daily_vapi_calls': RateLimitConfig.DAILY_LIMITS['vapi_calls'],
            }
        }
    
    return router
