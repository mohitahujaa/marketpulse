"""
Async SQLAlchemy engine and session factory.
All DB operations use async/await — never block the event loop.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("database")

# Create async engine — pool_pre_ping detects stale connections automatically
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",  # SQL logging in dev only
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Session factory — expire_on_commit=False keeps objects usable after commit
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def init_db() -> None:
    """Create all tables on startup and ensure default admin user exists."""
    from app.models import user, watchlist  # noqa: F401 — ensure models are registered

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified.")
    
    # Create default admin user if none exists
    await _create_default_admin()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a DB session per request.
    Automatically rolls back on exception and closes the session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Alias for external use
async_session_maker = AsyncSessionLocal


async def _create_default_admin() -> None:
    """
    Create default admin user if it doesn't exist.
    
    Credentials:
    - Email: admin@marketpulse.com
    - Password: Admin@123456 (CHANGE IN PRODUCTION!)
    - Role: ADMIN
    """
    from sqlalchemy import select
    from app.models.user import User, UserRole
    from app.core.security import hash_password
    
    default_admin_email = "admin@marketpulse.com"
    
    async with AsyncSessionLocal() as session:
        try:
            # Check if this specific admin user exists
            result = await session.execute(
                select(User).where(User.email == default_admin_email)
            )
            existing_admin = result.scalar_one_or_none()
            
            if existing_admin:
                logger.info(f"Default admin user already exists: {default_admin_email}")
                return
            
            # Create default admin user
            admin_user = User(
                email=default_admin_email,
                username="admin",
                hashed_password=hash_password("Admin@123456"),
                role=UserRole.ADMIN,
                is_active=True
            )
            
            session.add(admin_user)
            await session.commit()
            
            logger.info("=" * 60)
            logger.info("🎉 DEFAULT ADMIN USER CREATED")
            logger.info("=" * 60)
            logger.info("Email:    admin@marketpulse.com")
            logger.info("Password: Admin@123456")
            logger.info("Role:     ADMIN")
            logger.info("=" * 60)
            logger.warning("⚠️  CHANGE THIS PASSWORD IN PRODUCTION!")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Failed to create default admin user: {e}")
            await session.rollback()
