"""
Reddit collector — pulls new posts + comments from a subreddit via PRAW.

Requires REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET / REDDIT_USER_AGENT to be
set. If credentials are missing the collector yields nothing and logs a
single warning per cold boot.

Falls back to Reddit's public JSON API when PRAW authentication fails.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Dict, Optional

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
_settings = get_settings()

_warned = False


def _reddit_client():
    """Build a read-only PRAW client. Returns None if creds are missing."""
    global _warned
    if not _settings.REDDIT_CLIENT_ID or not _settings.REDDIT_CLIENT_SECRET:
        if not _warned:
            logger.warning(
                "reddit.credentials_missing",
                hint="Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env",
            )
            _warned = True
        return None

    try:
        import praw
    except ImportError:
        logger.error("reddit.praw_not_installed")
        return None

    return praw.Reddit(
        client_id=_settings.REDDIT_CLIENT_ID,
        client_secret=_settings.REDDIT_CLIENT_SECRET,
        user_agent=_settings.REDDIT_USER_AGENT,
        check_for_async=False,
    )


# ---------------------------------------------------------------------------
# Public JSON fallback (no auth needed)
# ---------------------------------------------------------------------------


def _fetch_public_json(subreddit_name: str, limit: int = 25) -> list[Dict[str, Any]]:
    """Fetch posts via Reddit's public JSON API (no authentication required)."""
    import requests

    url = f"https://www.reddit.com/r/{subreddit_name}/new.json"
    headers = {"User-Agent": _settings.REDDIT_USER_AGENT or "TDM-Research-Bot/1.0"}
    params = {"limit": min(limit, 100)}

    items: list[Dict[str, Any]] = []
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            body = post.get("selftext", "")
            title = post.get("title", "")
            text = f"{title}\n\n{body}".strip()
            items.append(
                {
                    "external_id": f"reddit:{post.get('id', '')}",
                    "source_type": "reddit",
                    "source": f"r/{subreddit_name}",
                    "title": title,
                    "text": text,
                    "url": f"https://www.reddit.com{post.get('permalink', '')}",
                    "author": post.get("author"),
                    "score": int(post.get("score", 0)),
                    "num_comments": int(post.get("num_comments", 0)),
                    "created_utc": float(post.get("created_utc", 0)),
                }
            )
        logger.info(
            "reddit.public_json_fetched",
            subreddit=subreddit_name,
            count=len(items),
        )
    except Exception as exc:
        logger.error(
            "reddit.public_json_failed",
            subreddit=subreddit_name,
            error=str(exc),
        )

    return items


def _fetch_sync(subreddit_name: str, limit: int = 25) -> list[Dict[str, Any]]:
    """Synchronously fetch the N newest posts for a subreddit."""
    client = _reddit_client()
    if client is None:
        # No credentials — go straight to public JSON
        return _fetch_public_json(subreddit_name, limit)

    items: list[Dict[str, Any]] = []
    try:
        subreddit = client.subreddit(subreddit_name)
        for post in subreddit.new(limit=limit):
            try:
                body = post.selftext or ""
                text = f"{post.title}\n\n{body}".strip()
                items.append(
                    {
                        "external_id": f"reddit:{post.id}",
                        "source_type": "reddit",
                        "source": f"r/{subreddit_name}",
                        "title": post.title,
                        "text": text,
                        "url": f"https://www.reddit.com{post.permalink}",
                        "author": str(post.author) if post.author else None,
                        "score": int(post.score) if post.score is not None else 0,
                        "num_comments": int(getattr(post, "num_comments", 0)),
                        "created_utc": float(post.created_utc or 0),
                    }
                )
            except Exception as exc:  # single-post failures shouldn't kill the loop
                logger.warning("reddit.post_parse_failed", error=str(exc))
    except Exception as exc:
        logger.error("reddit.fetch_failed", subreddit=subreddit_name, error=str(exc))
        # PRAW failed (401, network, etc.) — fall back to public JSON
        if not items:
            logger.info("reddit.falling_back_to_public_json", subreddit=subreddit_name)
            items = _fetch_public_json(subreddit_name, limit)

    return items


async def fetch_subreddit(
    subreddit_name: str, limit: int = 25
) -> list[Dict[str, Any]]:
    """Async wrapper around the blocking PRAW call."""
    return await asyncio.to_thread(_fetch_sync, subreddit_name, limit)


async def stream_subreddits(
    subreddits: list[str], limit_per_sub: int = 25
) -> AsyncIterator[Dict[str, Any]]:
    """Fetch the newest posts for each subreddit in sequence."""
    for sub in subreddits:
        items = await fetch_subreddit(sub, limit=limit_per_sub)
        for item in items:
            yield item
