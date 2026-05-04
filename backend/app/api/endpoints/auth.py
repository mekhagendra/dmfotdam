"""
Authentication endpoints — register (with OTP), login, Google OAuth, current-user.
"""

from __future__ import annotations

import asyncio
import random
import string
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.api.dependencies import get_current_user, user_to_public
from app.core.config import get_settings
from app.core.database import get_db, users_col
from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.models.user import (
    GoogleLoginRequest,
    OTPRequest,
    OTPVerifyAndRegister,
    PasswordResetConfirmRequest,
    PasswordResetOTPRequest,
    UserLogin,
    UserPublic,
    TokenResponse,
)
from app.services.email_service import send_email

router = APIRouter(prefix="/auth", tags=["auth"])
_settings = get_settings()


# --------------- helpers ---------------

def _otp_col():
    """Return the `otp_codes` MongoDB collection."""
    return get_db()["otp_codes"]


def _generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def _otp_lookup(email: str, purpose: str) -> dict:
    return {"email": email, "purpose": purpose}


async def _send_email(to: str, subject: str, body: str) -> None:
    """Send an email via SMTP. Raises HTTPException on failure."""
    if not _settings.SMTP_USER or not _settings.SMTP_PASSWORD:
        raise HTTPException(
            status_code=503,
            detail="SMTP not configured — cannot send OTP email",
        )
    ok = await send_email(to=to, subject=subject, body=body)
    if not ok:
        raise HTTPException(
            status_code=502,
            detail="Failed to send email — check SMTP configuration",
        )


# --------------- OTP flow ---------------

@router.post("/send-otp", status_code=200)
async def send_otp(payload: OTPRequest) -> dict:
    """Generate a 6-digit OTP, persist it, and email it to the user."""
    # Fail-fast checks — email and username must be free
    if await users_col().find_one({"email": payload.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    if await users_col().find_one({"username": payload.username}):
        raise HTTPException(status_code=400, detail="Username already taken")

    otp = _generate_otp()
    expires_at = datetime.now(timezone.utc).timestamp() + (
        _settings.OTP_EXPIRE_MINUTES * 60
    )

    # Upsert — one pending OTP per email at a time
    await _otp_col().update_one(
        _otp_lookup(payload.email, "register"),
        {
            "$set": {
                "otp": otp,
                "purpose": "register",
                "username": payload.username,
                "expires_at": expires_at,
                "verified": False,
                "created_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )

    subject = "TDM — Your verification code"
    body = (
        f"Hello {payload.username},\n\n"
        f"Your one-time verification code is: {otp}\n\n"
        f"This code expires in {_settings.OTP_EXPIRE_MINUTES} minutes.\n"
        f"If you did not request this, please ignore this email.\n"
    )
    await _send_email(payload.email, subject, body)

    return {"message": "OTP sent — check your email"}


@router.post("/verify-otp-register", response_model=UserPublic, status_code=201)
async def verify_otp_register(payload: OTPVerifyAndRegister) -> UserPublic:
    """Verify the OTP, then create the user in pending state."""
    record = await _otp_col().find_one(_otp_lookup(payload.email, "register"))
    if not record:
        raise HTTPException(status_code=400, detail="No OTP found for this email — request one first")

    # Check expiry
    if datetime.now(timezone.utc).timestamp() > record["expires_at"]:
        await _otp_col().delete_one(_otp_lookup(payload.email, "register"))
        raise HTTPException(status_code=400, detail="OTP expired — request a new one")

    # Check code
    if record["otp"] != payload.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # Re-check uniqueness (race-condition guard)
    if await users_col().find_one({"email": payload.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    if await users_col().find_one({"username": payload.username}):
        raise HTTPException(status_code=400, detail="Username already taken")

    now = datetime.now(timezone.utc)
    doc = {
        "username": payload.username,
        "email": payload.email,
        "full_name": payload.full_name,
        "hashed_password": get_password_hash(payload.password),
        "role": "customer",
        "status": "pending",
        "is_active": False,
        "auth_provider": "local",
        "google_sub": None,
        "created_at": now,
        "updated_at": now,
    }
    result = await users_col().insert_one(doc)
    doc["_id"] = result.inserted_id

    # Clean up OTP
    await _otp_col().delete_one(_otp_lookup(payload.email, "register"))

    return UserPublic(**user_to_public(doc))


@router.post("/forgot-password/send-otp", status_code=200)
async def send_password_reset_otp(payload: PasswordResetOTPRequest) -> dict:
    """Generate a password-reset OTP and email it when the account exists."""
    user = await users_col().find_one({"email": payload.email})
    if not user:
        return {"message": "If an account exists for that email, an OTP has been sent"}

    otp = _generate_otp()
    expires_at = datetime.now(timezone.utc).timestamp() + (
        _settings.OTP_EXPIRE_MINUTES * 60
    )

    await _otp_col().update_one(
        _otp_lookup(payload.email, "password_reset"),
        {
            "$set": {
                "otp": otp,
                "purpose": "password_reset",
                "expires_at": expires_at,
                "verified": False,
                "created_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )

    subject = "TDM — Your password reset code"
    body = (
        f"Hello {user.get('full_name') or user.get('username') or 'user'},\n\n"
        f"Your one-time password reset code is: {otp}\n\n"
        f"This code expires in {_settings.OTP_EXPIRE_MINUTES} minutes.\n"
        f"If you did not request a password reset, you can ignore this email.\n"
    )
    await _send_email(payload.email, subject, body)

    return {"message": "If an account exists for that email, an OTP has been sent"}


@router.post("/forgot-password/reset-password", status_code=200)
async def reset_password(payload: PasswordResetConfirmRequest) -> dict:
    """Verify a password-reset OTP and update the stored password hash."""
    record = await _otp_col().find_one(_otp_lookup(payload.email, "password_reset"))
    if not record:
        raise HTTPException(status_code=400, detail="No password reset request found for this email")

    if datetime.now(timezone.utc).timestamp() > record["expires_at"]:
        await _otp_col().delete_one(_otp_lookup(payload.email, "password_reset"))
        raise HTTPException(status_code=400, detail="OTP expired — request a new one")

    if record["otp"] != payload.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    user = await users_col().find_one({"email": payload.email})
    if not user:
        await _otp_col().delete_one(_otp_lookup(payload.email, "password_reset"))
        raise HTTPException(status_code=400, detail="Account not found")

    await users_col().update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "hashed_password": get_password_hash(payload.new_password),
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    await _otp_col().delete_one(_otp_lookup(payload.email, "password_reset"))

    return {"message": "Password updated successfully. You can sign in now."}


# --------------- Google OAuth ---------------

@router.post("/google", response_model=TokenResponse)
async def google_login(payload: GoogleLoginRequest) -> TokenResponse:
    """
    Accept a Google ID-token from the frontend, verify it, and either
    log in an existing user or create a new account.
    """
    if not _settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")

    try:
        id_info = await asyncio.to_thread(
            google_id_token.verify_oauth2_token,
            payload.credential,
            google_requests.Request(),
            _settings.GOOGLE_CLIENT_ID,
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Google token verification failed: {exc}")

    google_sub: str = id_info["sub"]
    email: str = id_info.get("email", "")
    full_name: str = id_info.get("name", "")

    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    # Look up by google_sub first, then by email
    user = await users_col().find_one({"google_sub": google_sub})
    if not user:
        user = await users_col().find_one({"email": email})

    if user:
        # Existing user — update google_sub if missing (link accounts)
        if not user.get("google_sub"):
            await users_col().update_one(
                {"_id": user["_id"]},
                {"$set": {"google_sub": google_sub, "auth_provider": "google"}},
            )
        user_status = user.get("status")
        is_active = user.get("is_active", True)
        if user_status is None:
            user_status = "active" if is_active else "pending"

        if user_status != "active" or not is_active:
            raise HTTPException(status_code=403, detail="Your account is pending admin approval")
    else:
        # New user — auto-register
        now = datetime.now(timezone.utc)
        # Derive a unique username from the email local part
        base_username = email.split("@")[0][:40]
        username = base_username
        counter = 1
        while await users_col().find_one({"username": username}):
            username = f"{base_username}{counter}"
            counter += 1

        doc = {
            "username": username,
            "email": email,
            "full_name": full_name or None,
            "hashed_password": "",  # no password for Google-only users
            "role": "customer",
            "status": "pending",
            "is_active": False,
            "auth_provider": "google",
            "google_sub": google_sub,
            "created_at": now,
            "updated_at": now,
        }
        result = await users_col().insert_one(doc)
        doc["_id"] = result.inserted_id
        user = doc

        raise HTTPException(
            status_code=403,
            detail="Account created and pending admin approval",
        )

    token = create_access_token(subject=str(user["_id"]))
    return TokenResponse(
        access_token=token,
        user=UserPublic(**user_to_public(user)),
    )


# --------------- Classic login / register (kept for backward compat) ---------------

@router.post("/register", response_model=UserPublic, status_code=201)
async def register_legacy(payload: OTPVerifyAndRegister) -> UserPublic:
    """
    Legacy register path — still requires a valid OTP.
    Prefer /auth/verify-otp-register which also returns a JWT.
    """
    return await verify_otp_register(payload)


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin) -> TokenResponse:
    user = await users_col().find_one({"username": payload.username})
    if not user or not user.get("hashed_password"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    if not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    user_status = user.get("status")
    is_active = user.get("is_active", True)
    if user_status is None:
        user_status = "active" if is_active else "pending"

    if user_status != "active" or not is_active:
        raise HTTPException(status_code=403, detail="Your account is pending admin approval")

    token = create_access_token(subject=str(user["_id"]))
    return TokenResponse(
        access_token=token,
        user=UserPublic(**user_to_public(user)),
    )


@router.get("/me", response_model=UserPublic)
async def me(current=Depends(get_current_user)) -> UserPublic:
    return UserPublic(**user_to_public(current))


@router.post("/logout")
async def logout() -> dict:
    return {"message": "Logged out"}
