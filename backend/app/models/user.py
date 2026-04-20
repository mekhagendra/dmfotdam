"""User models — both persisted (Mongo) and API-level (public / request)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=200)
    full_name: Optional[str] = Field(None, max_length=100)


class UserLogin(BaseModel):
    username: str
    password: str


class UserInDB(BaseModel):
    """Shape of a user document stored in MongoDB."""

    username: str
    email: EmailStr
    hashed_password: str
    full_name: Optional[str] = None
    role: str = "analyst"  # admin | analyst | viewer
    is_active: bool = True
    auth_provider: str = "local"  # "local" | "google"
    google_sub: Optional[str] = None  # Google subject ID
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserPublic(BaseModel):
    """Safe user payload returned by the API (no password hash)."""

    id: str
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


# ---------- OTP ----------


class OTPRequest(BaseModel):
    """Request body for sending an OTP to an email address."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)


class OTPVerifyAndRegister(BaseModel):
    """Verify OTP, then register the user in a single step."""
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=200)
    full_name: Optional[str] = Field(None, max_length=100)


class GoogleLoginRequest(BaseModel):
    """Frontend sends the Google credential (ID-token string)."""
    credential: str
