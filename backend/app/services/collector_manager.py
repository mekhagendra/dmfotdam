"""
Collector manager — the heart of real-time monitoring.

Responsibilities
----------------
1. Read every active source from `sources` in Mongo.
2. Fan-out to the appropriate collector (Reddit / RSS / Telegram / URL).
3. For each fetched item:
     a. Deduplicate against `collected_items` (by external_id).
     b. Classify the text with MLService.
     c. Store the raw item + score in `collected_items`.
     d. If `threat_score >= ALERT_THRESHOLD`, write an `alerts` document and
        broadcast it to any connected WebSocket clients.
4. Update the source's `last_checked`.

Runs as a periodic APScheduler job (see main.py startup hook).
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.core.config import get_settings
from app.core.database import (
    alerts_col,
    collected_items_col,
    sources_col,
)
from app.core.logging import get_logger
from app.services import rss_collector, telegram_collector
from app.services.ml_service import MLService
from app.services.web_scraper import WebScraper

logger = get_logger(__name__)
_settings = get_settings()

# Shared service instances.
_ml = MLService()
_scraper = WebScraper()


# ---------------------------------------------------------------------------
# WebSocket broadcast hub (populated by the /monitoring/live WS endpoint)
# ---------------------------------------------------------------------------


class _Broadcaster:
    """Very small pub-sub used to push alerts to connected clients."""

    def __init__(self) -> None:
        self._subscribers: set = set()
        self._lock = asyncio.Lock()

    async def subscribe(self, queue: "asyncio.Queue[dict]") -> None:
        async with self._lock:
            self._subscribers.add(queue)

    async def unsubscribe(self, queue: "asyncio.Queue[dict]") -> None:
        async with self._lock:
            self._subscribers.discard(queue)

    async def publish(self, event: Dict[str, Any]) -> None:
        async with self._lock:
            subs = list(self._subscribers)
        for q in subs:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:  # pragma: no cover
                pass


broadcaster = _Broadcaster()


# ---------------------------------------------------------------------------
# Source dispatch
# ---------------------------------------------------------------------------


async def _collect_source(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Dispatch to the right collector based on source.source_type."""
    stype = source.get("source_type")
    url = source.get("url", "")
    if stype == "rss":
        return await rss_collector.fetch_feed(url, source_type="rss", limit=30)
    if stype == "telegram":
        return await telegram_collector.fetch_channel(url, limit=30)
    if stype == "url":
        # One-shot scrape of a page; treat as a single item.
        content = await asyncio.to_thread(_scraper.fetch_url, url)
        if not content or not content.get("text"):
            return []
        fingerprint = hashlib.sha1(
            f"{content.get('title', '')}\n{content.get('text', '')}".encode("utf-8")
        ).hexdigest()[:16]
        return [
            {
                "external_id": f"url:{url}:{fingerprint}",
                "source_type": "url",
                "source": url,
                "title": content.get("title", url),
                "text": content["text"],
                "url": url,
            }
        ]
    logger.warning("collector.unknown_source_type", source_type=stype)
    return []


# ---------------------------------------------------------------------------
# Item processing
# ---------------------------------------------------------------------------


async def _process_item(item: Dict[str, Any], source: Dict[str, Any]) -> None:
    """Classify an item and persist it. Dedup by source_id + external_id."""
    if not item.get("text"):
        return

    source_id = str(source.get("_id", ""))

    existing = await collected_items_col().find_one(
        {
            "source_id": source_id,
            "source_type": item.get("source_type"),
            "external_id": item["external_id"],
        }
    )
    if existing is not None:
        return  # already classified before

    classification = await _ml.classify(item["text"])
    score = float(classification.get("threat_score", 0.0))
    level = classification.get("threat_level", "low")

    doc = {
        **item,
        "threat_score": score,
        "threat_level": level,
        "classification": classification,
        "source_name": source.get("name"),
        "source_id": source_id,
        "collected_at": datetime.now(timezone.utc),
    }

    try:
        await collected_items_col().insert_one(doc)
    except Exception as exc:
        # Duplicate key from the unique index — ignore.
        logger.debug("collector.dedup_insert_skipped", error=str(exc))
        return

    if score >= _settings.ALERT_THRESHOLD:
        await _raise_alert(doc, source)


async def _raise_alert(item: Dict[str, Any], source: Dict[str, Any]) -> None:
    """Persist + broadcast an alert for a high-scoring item."""
    title = item.get("title") or (item.get("text") or "")[:120]
    owner_id = source.get("owner_id")
    owner_id_str = str(owner_id) if owner_id is not None else None
    alert_doc = {
        "title": title,
        "description": (item.get("text") or "")[:1000],
        "threat_level": item.get("threat_level", "medium"),
        "threat_score": item.get("threat_score", 0.0),
        "source": item.get("url") or item.get("source"),
        "source_type": item.get("source_type"),
        "owner_id": owner_id_str,
        "details": {
            "source_name": source.get("name"),
            "external_id": item.get("external_id"),
            "classification": item.get("classification"),
        },
        "is_read": False,
        "is_resolved": False,
        "created_at": datetime.now(timezone.utc),
    }
    result = await alerts_col().insert_one(alert_doc)
    alert_doc["id"] = str(result.inserted_id)
    alert_doc["_id"] = None  # don't broadcast the raw ObjectId
    logger.info(
        "alert.created",
        level=alert_doc["threat_level"],
        score=alert_doc["threat_score"],
        source=alert_doc["source"],
    )
    # Broadcast via old pub-sub hub (existing WS in monitoring.py)
    await broadcaster.publish(
        {
            "event": "alert",
            "alert": {
                **{k: v for k, v in alert_doc.items() if k != "_id"},
                "created_at": alert_doc["created_at"].isoformat(),
            },
        }
    )
    # Broadcast via new WebSocket endpoint (ws.py)
    try:
        from app.api.endpoints.ws import broadcast_alert as ws_broadcast_alert
        await ws_broadcast_alert(
            {
                **{k: v for k, v in alert_doc.items() if k != "_id"},
                "created_at": alert_doc["created_at"].isoformat(),
            }
        )
    except Exception as exc:
        logger.debug("ws.broadcast_alert_failed", error=str(exc))


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


async def run_one_source(source: Dict[str, Any]) -> Dict[str, Any]:
    """Collect + classify every new item for a single source."""
    logger.info(
        "collector.running_source",
        name=source.get("name"),
        source_type=source.get("source_type"),
        url=source.get("url"),
    )
    items = await _collect_source(source)
    new_count = 0
    source_id = str(source.get("_id", ""))
    for item in items:
        before = await collected_items_col().count_documents(
            {
                "source_id": source_id,
                "source_type": item.get("source_type"),
                "external_id": item["external_id"],
            }
        )
        await _process_item(item, source)
        if before == 0:
            new_count += 1

    await sources_col().update_one(
        {"_id": source["_id"]},
        {"$set": {"last_checked": datetime.now(timezone.utc)}},
    )
    return {
        "source": source.get("name"),
        "fetched": len(items),
        "new": new_count,
    }


async def run_all_sources(owner_id: ObjectId | None = None) -> Dict[str, Any]:
    """Poll active sources once.

    If owner_id is provided, only poll that user's active sources.
    """
    query: Dict[str, Any] = {"is_active": True}
    if owner_id is not None:
        query["owner_id"] = owner_id

    cursor = sources_col().find(query)
    sources = [s async for s in cursor]
    if not sources:
        logger.debug("collector.no_active_sources")
        return {"sources_polled": 0, "results": []}

    results = []
    for src in sources:
        try:
            results.append(await run_one_source(src))
        except Exception as exc:
            logger.error(
                "collector.source_failed",
                name=src.get("name"),
                error=str(exc),
            )
            results.append({"source": src.get("name"), "error": str(exc)})
    return {"sources_polled": len(sources), "results": results}


async def ensure_default_sources() -> None:
    """On first boot, seed default RSS feeds so the
    system starts producing data without requiring manual configuration.
    """
    existing = await sources_col().count_documents({})
    if existing > 0:
        return

    defaults: List[Dict[str, Any]] = []

    for feed in _settings.DEFAULT_RSS_FEEDS:
        defaults.append(
            {
                "name": f"RSS {feed}",
                "url": feed,
                "source_type": "rss",
                "keywords": [],
                "is_active": True,
                "check_interval": _settings.COLLECTOR_INTERVAL_SECONDS,
                "last_checked": None,
                "created_at": datetime.now(timezone.utc),
            }
        )

    if defaults:
        await sources_col().insert_many(defaults)
        logger.info("collector.default_sources_seeded", count=len(defaults))
