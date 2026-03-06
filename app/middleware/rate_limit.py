"""
Simple in-process rate limiter using a sliding window per IP.
For production, replace with Redis-backed rate limiting (e.g. slowapi + Redis).
"""
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("rate_limiter")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter: max N requests per IP per 60 seconds.
    Health check endpoint is excluded.
    """

    def __init__(self, app, calls: int = settings.RATE_LIMIT_PER_MINUTE, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self._requests: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = self._requests[ip]

        # Remove timestamps outside the current window
        while window and window[0] < now - self.period:
            window.popleft()

        if len(window) >= self.calls:
            logger.warning("Rate limit exceeded", extra={"ip": ip, "path": str(request.url.path)})
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Too many requests. Limit: {self.calls} per {self.period}s.",
                    },
                },
                headers={"Retry-After": str(self.period)},
            )

        window.append(now)
        return await call_next(request)
