"""
Redis-backed rate limiting middleware for horizontal scalability.

Replaces in-memory rate limiting with distributed Redis storage,
enabling rate limiting across multiple API instances.
"""
import time
from typing import Optional

import redis.asyncio as redis
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("redis_rate_limiter")


class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Distributed rate limiter using Redis sliding window.
    
    Advantages over in-memory:
    - Works across multiple API instances
    - Survives server restarts
    - Automatic TTL management
    - Better performance at scale
    """
    
    def __init__(
        self,
        app,
        redis_url: str = settings.REDIS_URL,
        calls: int = settings.RATE_LIMIT_PER_MINUTE,
        period: int = 60,
    ):
        super().__init__(app)
        self.redis_url = redis_url
        self.calls = calls
        self.period = period
        self._redis_client: Optional[redis.Redis] = None
    
    async def _get_redis(self) -> redis.Redis:
        """Lazy initialization of Redis connection."""
        if not self._redis_client:
            self._redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
        return self._redis_client
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        ip = request.client.host if request.client else "unknown"
        key = f"rate_limit:{ip}"
        now = time.time()
        
        try:
            redis_client = await self._get_redis()
            
            # Use Redis sorted set for sliding window
            # Score is timestamp, member is unique request ID
            request_id = f"{now}:{id(request)}"
            
            # Start pipeline for atomic operations
            pipe = redis_client.pipeline()
            
            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, now - self.period)
            
            # Count current requests in window
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {request_id: now})
            
            # Set expiry on the key
            pipe.expire(key, self.period)
            
            # Execute pipeline
            results = await pipe.execute()
            current_count = results[1]  # Result of zcard
            
            # Check if rate limit exceeded
            if current_count >= self.calls:
                logger.warning(
                    "Rate limit exceeded",
                    extra={"ip": ip, "path": str(request.url.path), "count": current_count}
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": f"Too many requests. Limit: {self.calls} per {self.period} seconds."
                        }
                    },
                    headers={"Retry-After": str(self.period)}
                )
            
            # Add rate limit info to response headers
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(self.calls)
            response.headers["X-RateLimit-Remaining"] = str(self.calls - current_count - 1)
            response.headers["X-RateLimit-Reset"] = str(int(now + self.period))
            
            return response
            
        except redis.RedisError as e:
            # Fallback: allow request if Redis is down (fail open)
            # In production, you might want to fail closed instead
            logger.error(f"Redis error in rate limiter: {e}", extra={"ip": ip})
            return await call_next(request)
    
    async def __del__(self):
        """Clean up Redis connection."""
        if self._redis_client:
            await self._redis_client.close()
