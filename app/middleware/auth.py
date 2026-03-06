"""
FastAPI dependencies for authentication and role-based access control.

JWT token authentication via Authorization: Bearer header.
"""
import uuid

from fastapi import Depends, Request
from typing import Optional
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract and validate the JWT from Authorization: Bearer header.
    
    Returns the authenticated User ORM object.
    """
    # Get token from Authorization header
    token = credentials.credentials if credentials else None
    
    if not token:
        raise UnauthorizedException("Authentication required. Please log in.")

    try:
        payload = decode_token(token)
    except JWTError:
        raise UnauthorizedException("Invalid or expired token.")

    if payload.get("type") != "access":
        raise UnauthorizedException("Refresh tokens cannot be used for API access.")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException("Token is missing subject claim.")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedException("Malformed token subject.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedException("User no longer exists.")
    if not user.is_active:
        raise UnauthorizedException("Account is deactivated.")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Alias for cleaner route signatures."""
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Guard: only allow admin-role users."""
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenException()
    return current_user
