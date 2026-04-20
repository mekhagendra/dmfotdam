"""
Live monitor — on-demand check of a single URL or subreddit.

The periodic polling logic lives in `collector_manager`; this module exposes
synchronous-style helpers for the API (e.g., "check this URL right now").
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.logging import get_logger
from app.services.text_analyzer import TextAnalyzer
from app.services.web_scraper import WebScraper

logger = get_logger(__name__)


class LiveMonitor:
    def __init__(self) -> None:
        self.scraper = WebScraper()
        self.analyzer = TextAnalyzer()

    async def check_url(
        self, url: str, keywords: Optional[list[str]] = None
    ) -> Dict[str, Any]:
        """Fetch + classify a single URL immediately. Returns the analysis."""
        content = self.scraper.fetch_url(url)
        if not content:
            return {
                "url": url,
                "status": "error",
                "message": "Failed to fetch content",
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }

        text = content.get("text", "")
        if not text:
            return {
                "url": url,
                "status": "empty",
                "message": "No text content found",
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }

        analysis = await self.analyzer.analyze(text)
        keyword_matches = (
            [kw for kw in (keywords or []) if kw.lower() in text.lower()]
            if keywords
            else []
        )
        return {
            "url": url,
            "title": content.get("title", ""),
            "status": "checked",
            "threat_score": analysis["threat_score"],
            "threat_level": analysis["threat_level"],
            "summary": analysis["summary"],
            "keyword_matches": keyword_matches,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    def should_alert(self, result: Dict[str, Any], threshold: float = 0.6) -> bool:
        return result.get("threat_score", 0) >= threshold
