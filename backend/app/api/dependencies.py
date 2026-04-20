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
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )
    return user


def user_to_public(user: Dict[str, Any]) -> Dict[str, Any]:
    """Strip sensitive fields and convert ObjectId → str for API output."""
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "email": user["email"],
        "full_name": user.get("full_name"),
        "role": user.get("role", "analyst"),
        "is_active": user.get("is_active", True),
        "created_at": user["created_at"],
    }
