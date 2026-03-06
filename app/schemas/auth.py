"""
Auth schemas — request/response validation for registration and login.
Pydantic v2 with strict validators.
"""
import re
import uuid
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=72)

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username may only contain letters, digits, and underscores.")
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit.")
        # Ensure password doesn't exceed bcrypt's 72-byte limit
        if len(v.encode('utf-8')) > 72:
            raise ValueError("Password is too long (max 72 bytes).")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    refresh_token: str


class UserPublic(BaseModel):
    """Safe user representation — never expose hashed_password."""
    id: uuid.UUID
    email: str
    username: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}
