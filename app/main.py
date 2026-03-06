"""
MarketPulse API - Main Application Entry Point

Phase 1 Security Improvements:
- Bearer token JWT authentication
- Security headers middleware (OWASP compliance)
- Redis-backed rate limiting (horizontally scalable)
- Account lockout protection
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.db.session import init_db
from app.middleware.redis_rate_limit import RedisRateLimitMiddleware
from security.headers import SecurityHeadersMiddleware

logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting MarketPulse API...")
    await init_db()
    logger.info("Database initialized.")
    yield
    logger.info("Shutting down MarketPulse API...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="""
## MarketPulse API

A production-ready REST API for tracking crypto market data and managing personal watchlists.

### Features
- 🔐 JWT Authentication with refresh tokens
- 👥 Role-based access control (user / admin)
- 📈 Live crypto prices via CoinGecko (with retries & timeouts)
- 📋 Personal watchlist CRUD
- 📝 Structured logging & error handling
- ✅ Full test coverage
""",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Register exception handlers for consistent error responses
register_exception_handlers(app)

# CORS - with credentials support
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,  # Allow credentials in requests
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)

# Security headers (OWASP recommendations)
app.add_middleware(SecurityHeadersMiddleware)

# Rate limiting (Redis-backed for horizontal scaling)
try:
    app.add_middleware(RedisRateLimitMiddleware)
    logger.info("Redis rate limiting enabled")
except Exception as e:
    logger.warning(f"Failed to initialize Redis rate limiter, falling back to in-memory: {e}")
    # Fallback to in-memory if Redis unavailable
    from app.middleware.rate_limit import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)

# Mount versioned router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - provides API information and documentation links."""
    return {
        "message": "Welcome to MarketPulse API",
        "version": "1.0.0",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": f"{settings.API_V1_STR}/openapi.json"
        },
        "endpoints": {
            "health": "/health",
            "auth": f"{settings.API_V1_STR}/auth",
            "watchlists": f"{settings.API_V1_STR}/watchlists",
            "market": f"{settings.API_V1_STR}/market",
            "admin": f"{settings.API_V1_STR}/admin"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for deployment monitoring."""
    return {"status": "healthy", "version": "1.0.0"}
