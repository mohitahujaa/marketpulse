"""
Auth service — business logic for user registration and login.
Keeps route handlers thin: handlers validate input, services do work.
"""
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    decode_token,
)
from app.models.user import User, UserRole
from app.schemas.auth import RegisterRequest, TokenResponse

logger = get_logger("auth_service")


async def register_user(payload: RegisterRequest, db: AsyncSession) -> User:
    """
    Register a new user.

    Raises:
        ConflictException: If email or username already exists.
    """
    # Check for duplicate email
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise ConflictException("A user with this email already exists.")

    # Check for duplicate username
    result = await db.execute(select(User).where(User.username == payload.username))
    if result.scalar_one_or_none():
        raise ConflictException("This username is already taken.")

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role=UserRole.USER,
    )
    db.add(user)
    await db.flush()  # Get the generated ID without committing yet

    logger.info("User registered", extra={"user_id": str(user.id), "email": user.email})
    return user


async def login_user(email: str, password: str, db: AsyncSession) -> TokenResponse:
    """
    Authenticate a user and issue JWT tokens.

    Raises:
        UnauthorizedException: On invalid credentials (deliberately vague to prevent enumeration).
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    # Always call verify_password even if user not found to prevent timing attacks
    _dummy_hash = "$2b$12$KIX/dummy/hash/to/prevent/timing/attack/aaaaaaaaaa"
    valid = verify_password(password, user.hashed_password if user else _dummy_hash)

    if not user or not valid or not user.is_active:
        raise UnauthorizedException("Invalid email or password.")

    access_token = create_access_token(
        subject=str(user.id),
        role=user.role.value,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    logger.info("User logged in", extra={"user_id": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def refresh_access_token(refresh_token: str, db: AsyncSession) -> TokenResponse:
    """Exchange a valid refresh token for a new access token."""
    from jose import JWTError

    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise UnauthorizedException("Invalid or expired refresh token.")

    if payload.get("type") != "refresh":
        raise UnauthorizedException("Access tokens cannot be used to refresh.")

    import uuid
    user_id = uuid.UUID(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise UnauthorizedException("User not found or deactivated.")

    new_access = create_access_token(subject=str(user.id), role=user.role.value)
    new_refresh = create_refresh_token(subject=str(user.id))

    logger.info("Token refreshed", extra={"user_id": str(user.id)})

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
