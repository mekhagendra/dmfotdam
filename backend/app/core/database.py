"""
MongoDB Atlas connection + collection accessors.

Uses Motor (async driver). A single client is created at startup and reused.
Call `connect_to_mongo()` on app startup and `close_mongo_connection()` on
shutdown.

Collections used:
    users, documents, analyses, alerts, sources, collected_items
"""

from __future__ import annotations

from typing import Optional

import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class _MongoState:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None


_state = _MongoState()


async def connect_to_mongo() -> None:
    """Create the global Motor client and verify the connection."""
    settings = get_settings()
    if _state.client is not None:
        return

    logger.info("mongo.connecting", url_masked=_masked(settings.MONGODB_URL))
    _state.client = AsyncIOMotorClient(
        settings.MONGODB_URL,
        serverSelectionTimeoutMS=10_000,
        uuidRepresentation="standard",
        tlsCAFile=certifi.where(),
    )
    _state.db = _state.client[settings.MONGODB_DB_NAME]

    # Ping to surface bad credentials / bad URL early.
    try:
        await _state.client.admin.command("ping")
    except Exception as exc:
        logger.error("mongo.ping_failed", error=str(exc))
        raise

    await _ensure_indexes(_state.db)
    logger.info("mongo.connected", db=settings.MONGODB_DB_NAME)


async def close_mongo_connection() -> None:
    if _state.client is not None:
        _state.client.close()
        _state.client = None
        _state.db = None
        logger.info("mongo.disconnected")


def get_db() -> AsyncIOMotorDatabase:
    """Return the live database handle. Raises if not connected."""
    if _state.db is None:
        raise RuntimeError(
            "MongoDB not connected. Did you forget to call connect_to_mongo()?"
        )
    return _state.db


# ---------- Collection helpers ----------


def users_col():
    return get_db().users


def documents_col():
    return get_db().documents


def analyses_col():
    return get_db().analyses


def alerts_col():
    return get_db().alerts


def sources_col():
    return get_db().sources


def collected_items_col():
    return get_db().collected_items


# ---------- Index setup ----------


async def _ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    """Idempotently create the indexes we rely on."""
    await db.users.create_index("username", unique=True)
    await db.users.create_index("email", unique=True)

    await db.documents.create_index("uploaded_by")
    await db.documents.create_index("created_at")

    await db.analyses.create_index("document_id")
    await db.analyses.create_index("user_id")
    await db.analyses.create_index("created_at")

    await db.alerts.create_index("created_at")
    await db.alerts.create_index("is_resolved")
    await db.alerts.create_index("threat_level")
    await db.alerts.create_index("owner_id")

    # Migrate old global unique index on name -> per-owner unique names.
    # This allows different users to have sources with the same display name
    # (e.g. "Reddit r/worldnews") while still preventing duplicates per user.
    indexes = await db.sources.index_information()
    if "name_1" in indexes:
        await db.sources.drop_index("name_1")
    await db.sources.create_index(
        [("owner_id", 1), ("name", 1)],
        unique=True,
        name="uniq_owner_source_name",
    )
    await db.sources.create_index("source_type")
    await db.sources.create_index("is_active")
    await db.sources.create_index("owner_id")

    await db.collected_items.create_index(
        [("external_id", 1), ("source_type", 1)],
        unique=True,
        name="uniq_source_item",
    )
    await db.collected_items.create_index("collected_at")
    await db.collected_items.create_index("threat_score")


def _masked(url: str) -> str:
    """Hide credentials from a Mongo URL for logging."""
    if "@" not in url:
        return url
    prefix, _, tail = url.partition("://")
    creds, _, host = tail.rpartition("@")
    return f"{prefix}://***:***@{host}" if creds else url
