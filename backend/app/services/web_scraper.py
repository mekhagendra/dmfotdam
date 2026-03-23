"""
Web scraping service for content collection
"""

import re
from typing import Optional
from app.core.logging import get_logger

logger = get_logger(__name__)


class WebScraper:
    """Service for scraping web content for analysis"""

    def fetch_url(self, url: str) -> Optional[dict]:
        """Fetch and parse content from a URL"""
        try:
            import requests
            from bs4 import BeautifulSoup

            response = requests.get(
                url,
                timeout=30,
                headers={"User-Agent": "TDM-Research-Bot/1.0"},
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script and style elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()

            text = soup.get_text(separator="\n", strip=True)
            # Clean whitespace
            text = re.sub(r'\n\s*\n', '\n\n', text)

            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else ""

            return {
                "url": url,
                "title": title,
                "text": text[:50000],  # limit content size
                "status_code": response.status_code,
            }
        except Exception as e:
            logger.error(f"Failed to fetch URL {url}: {e}")
            return None

    def extract_links(self, url: str) -> list[str]:
        """Extract links from a page"""
        try:
            import requests
            from bs4 import BeautifulSoup
            from urllib.parse import urljoin

            response = requests.get(
                url,
                timeout=30,
                headers={"User-Agent": "TDM-Research-Bot/1.0"},
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            links = []
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                full_url = urljoin(url, href)
                if full_url.startswith("http"):
                    links.append(full_url)
            return links
        except Exception as e:
            logger.error(f"Failed to extract links from {url}: {e}")
            return []
