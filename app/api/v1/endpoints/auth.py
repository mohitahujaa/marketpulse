"""
Auth endpoints: register, login, token refresh, logout, and current user profile.

Security improvements:
- Bearer token authentication with JWT
- Account lockout after failed attempts
- Secure token handling
"""
from fastapi import APIRouter, Depends, Request, Response, status
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.middleware.auth import get_current_active_user
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserPublic
from app.services import auth as auth_service
from app.utils.response import success_response
from security.lockout import login_tracker

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    payload: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new user account.

    - Email and username must be unique
    - Password requires at least 8 characters, 1 uppercase, 1 digit
    - Auto-login after registration
    """
    user = await auth_service.register_user(payload, db)
    
    # Auto-login: generate tokens
    tokens = await auth_service.login_user(payload.email, payload.password, db)
    
    return success_response(
        data={
            "user": UserPublic.model_validate(user, from_attributes=True),
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "token_type": "bearer"
        },
        message="Account created successfully.",
        status_code=status.HTTP_201_CREATED,
    )


@router.post("/login", summary="Login and receive access tokens")
async def login(
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate with email/password.

    Security features:
    - Account lockout after 5 failed attempts (15 min)
    - Tokens returned in response body for Bearer authentication
    """
    # Check for account lockout and record attempt
    login_tracker.record_failed_attempt(payload.email)  # Will raise if locked
    
    try:
        tokens = await auth_service.login_user(payload.email, payload.password, db)
        
        # Successful login - clear failed attempts
        login_tracker.record_successful_login(payload.email)
        
        # Return tokens in response body (Authorization header method)
        return success_response(
            data={
                "access_token": tokens.access_token,
                "refresh_token": tokens.refresh_token,
                "token_type": "bearer"
            },
            message="Login successful."
        )
    except Exception as e:
        # Record failed attempt (login_user already validated)
        # We don't call record_failed_attempt again here to avoid double-counting
        raise e


@router.post("/refresh", summary="Refresh access token")
async def refresh_token(
    refresh_token_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    
    Request body: {"refresh_token": "your_refresh_token"}
    """
    refresh_token = refresh_token_data.get("refresh_token")
    if not refresh_token:
        from app.core.exceptions import UnauthorizedException
        raise UnauthorizedException("Refresh token required in request body")
    
    tokens = await auth_service.refresh_access_token(refresh_token, db)
    
    return success_response(
        data={
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "token_type": "bearer"
        },
        message="Token refreshed."
    )


@router.post("/logout", summary="Logout")
async def logout(response: Response):
    """
    Logout user.
    
    Client should clear tokens from memory.
    """
    return success_response(message="Logged out successfully")


@router.get("/me", summary="Get current user profile")
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Returns the profile of the currently authenticated user."""
    return success_response(data=UserPublic.model_validate(current_user, from_attributes=True))
