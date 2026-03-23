"""
Live monitoring service for continuous threat detection
"""

from datetime import datetime, timezone
from typing import Optional

from app.core.logging import get_logger
from app.services.web_scraper import WebScraper
from app.services.text_analyzer import TextAnalyzer

logger = get_logger(__name__)


class LiveMonitor:
    """Service for continuous monitoring of web sources"""

    def __init__(self):
        self.scraper = WebScraper()
        self.analyzer = TextAnalyzer()

    def check_source(self, url: str, keywords: Optional[list[str]] = None) -> dict:
        """Check a single source for threat content"""
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

        # Run analysis
        analysis = self.analyzer.analyze(text)

        # Check for specific keywords if provided
        keyword_matches = []
        if keywords:
            text_lower = text.lower()
            keyword_matches = [kw for kw in keywords if kw.lower() in text_lower]

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

    def should_alert(self, result: dict, threshold: float = 0.5) -> bool:
        """Determine if a monitoring result should generate an alert"""
        return result.get("threat_score", 0) >= threshold
