"""Admin user-management endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_admin_user, user_to_public
from app.core.database import users_col
from app.models.user import UserAdminUpdate, UserPublic

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserPublic])
async def list_users(_: dict = Depends(get_current_admin_user)) -> list[UserPublic]:
    """Return all users for admin management screens."""
    cursor = users_col().find({}).sort("created_at", -1)
    users = await cursor.to_list(length=500)
    return [UserPublic(**user_to_public(user)) for user in users]


@router.patch("/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: str,
    payload: UserAdminUpdate,
    current_admin: dict = Depends(get_current_admin_user),
) -> UserPublic:
    """Update user role/status (admin only)."""
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")

    target_user = await users_col().find_one({"_id": oid})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    updates = {}

    if payload.role is not None:
        if str(target_user["_id"]) == str(current_admin["_id"]) and payload.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot remove your own admin role",
            )
        updates["role"] = payload.role

    if payload.status is not None:
        if str(target_user["_id"]) == str(current_admin["_id"]) and payload.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own account",
            )
        updates["status"] = payload.status
        updates["is_active"] = payload.status == "active"

    if not updates:
        raise HTTPException(status_code=400, detail="No changes provided")

    updates["updated_at"] = datetime.now(timezone.utc)
    await users_col().update_one({"_id": oid}, {"$set": updates})

    updated_user = await users_col().find_one({"_id": oid})
    return UserPublic(**user_to_public(updated_user))
