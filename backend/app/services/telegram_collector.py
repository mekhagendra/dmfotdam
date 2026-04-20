"""
Telegram collector — fetches public channel messages via an RSS bridge
(RSSHub or similar). We never use the Telegram client API directly, so no
user session / phone number is required.

Given a channel slug (e.g., "durov") we construct:
    {TELEGRAM_RSS_BRIDGE}/{slug}
and parse the feed with the shared `rss_collector`.
"""

from __future__ import annotations

from typing import Any, Dict

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.rss_collector import fetch_feed

logger = get_logger(__name__)
_settings = get_settings()


async def fetch_channel(channel: str, limit: int = 30) -> list[Dict[str, Any]]:
    """
    Fetch recent posts from a public Telegram channel.

    Args:
        channel: Channel slug or full bridge URL.
                 If it looks like a URL, we use it verbatim.
    """
    url = (
        channel
        if channel.startswith("http")
        else _settings.TELEGRAM_RSS_BRIDGE.rstrip("/") + "/" + channel.lstrip("/")
    )
    items = await fetch_feed(url, source_type="telegram", limit=limit)
    # Overwrite the per-item "source" with a friendlier channel identifier.
    for item in items:
        item["source"] = f"t.me/{channel.lstrip('/')}"
    return items
