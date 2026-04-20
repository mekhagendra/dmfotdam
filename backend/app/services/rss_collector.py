"""
RSS collector — fetches entries from any RSS/Atom feed using feedparser.

Used for both:
  * news feeds (BBC, Reuters, NYTimes, ...)
  * public Telegram channels via RSS-bridge URLs (e.g., rsshub.app/telegram/...)
"""

from __future__ import annotations

import asyncio
import hashlib
from typing import Any, Dict, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


def _hash_id(url: str, title: str, published: Optional[str]) -> str:
    h = hashlib.sha1()
    h.update(url.encode("utf-8"))
    h.update(b"|")
    h.update((title or "").encode("utf-8"))
    h.update(b"|")
    h.update((published or "").encode("utf-8"))
    return h.hexdigest()[:24]


def _fetch_sync(
    feed_url: str, source_type: str = "rss", limit: int = 30
) -> list[Dict[str, Any]]:
    try:
        import feedparser
    except ImportError:
        logger.error("rss.feedparser_not_installed")
        return []

    try:
        parsed = feedparser.parse(feed_url)
    except Exception as exc:
        logger.error("rss.parse_failed", url=feed_url, error=str(exc))
        return []

    if parsed.bozo and not parsed.entries:
        logger.warning(
            "rss.feed_malformed",
            url=feed_url,
            error=str(getattr(parsed, "bozo_exception", "")),
        )
        return []

    items: list[Dict[str, Any]] = []
    for entry in parsed.entries[:limit]:
        title = getattr(entry, "title", "") or ""
        summary = getattr(entry, "summary", "") or ""
        link = getattr(entry, "link", "") or feed_url
        published = getattr(entry, "published", None) or getattr(
            entry, "updated", None
        )
        guid = getattr(entry, "id", None) or link or title

        text = f"{title}\n\n{summary}".strip()
        ext_id = f"{source_type}:{_hash_id(guid, title, published)}"
        items.append(
            {
                "external_id": ext_id,
                "source_type": source_type,
                "source": feed_url,
                "title": title,
                "text": text,
                "url": link,
                "author": getattr(entry, "author", None),
                "published": published,
            }
        )
    return items


async def fetch_feed(
    feed_url: str, source_type: str = "rss", limit: int = 30
) -> list[Dict[str, Any]]:
    return await asyncio.to_thread(_fetch_sync, feed_url, source_type, limit)
