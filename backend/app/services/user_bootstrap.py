"""User bootstrap helpers (seed data) executed during application startup."""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.config import get_settings
from app.core.database import users_col
from app.core.logging import get_logger
from app.core.security import get_password_hash

logger = get_logger(__name__)


async def ensure_seed_admin_user() -> None:
    """Create the initial admin user if it does not already exist."""
    settings = get_settings()

    existing_admin = await users_col().find_one({"email": settings.SEED_ADMIN_EMAIL})
    if existing_admin:
        updates = {}

        if existing_admin.get("role") != "admin":
            updates["role"] = "admin"
        if existing_admin.get("status") != "active":
            updates["status"] = "active"
        if existing_admin.get("is_active") is not True:
            updates["is_active"] = True

        if updates:
            updates["updated_at"] = datetime.now(timezone.utc)
            await users_col().update_one({"_id": existing_admin["_id"]}, {"$set": updates})
            logger.info("users.seed_admin_updated", email=settings.SEED_ADMIN_EMAIL)
        return

    now = datetime.now(timezone.utc)
    username = settings.SEED_ADMIN_USERNAME

    counter = 1
    while await users_col().find_one({"username": username}):
        username = f"{settings.SEED_ADMIN_USERNAME}{counter}"
        counter += 1

    await users_col().insert_one(
        {
            "username": username,
            "email": settings.SEED_ADMIN_EMAIL,
            "full_name": settings.SEED_ADMIN_FULL_NAME,
            "hashed_password": get_password_hash(settings.SEED_ADMIN_PASSWORD),
            "role": "admin",
            "status": "active",
            "is_active": True,
            "auth_provider": "local",
            "google_sub": None,
            "created_at": now,
            "updated_at": now,
        }
    )
    logger.info("users.seed_admin_created", email=settings.SEED_ADMIN_EMAIL, username=username)
