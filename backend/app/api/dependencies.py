"""
FastAPI dependency injection — current-user resolver backed by MongoDB.
"""

from __future__ import annotations

from typing import Any, Dict

from bson import ObjectId
from fastapi import Depends, HTTPException, status

from app.core.database import users_col
from app.core.security import get_current_user_id


async def get_current_user(
    user_id: str = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """Return the full user document for the JWT-authenticated caller."""
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user id in token",
        )

    user = await users_col().find_one({"_id": oid})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    user_status = user.get("status")
    is_active = user.get("is_active", True)

    if user_status is None:
        user_status = "active" if is_active else "pending"

    if user_status != "active" or not is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending admin approval",
        )
    return user


async def get_current_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Require the caller to be an admin."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def user_to_public(user: Dict[str, Any]) -> Dict[str, Any]:
    """Strip sensitive fields and convert ObjectId → str for API output."""
    status = user.get("status")
    is_active = user.get("is_active", True)
    if status is None:
        status = "active" if is_active else "pending"

    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "email": user["email"],
        "full_name": user.get("full_name"),
        "role": user.get("role", "customer"),
        "status": status,
        "is_active": is_active,
        "created_at": user["created_at"],
    }
