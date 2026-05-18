"""
Web scraping service for content collection
"""

import hashlib
import re
from typing import Optional
from urllib.parse import urljoin, urlparse
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

    def extract_articles(self, page_url: str, max_articles: int = 25) -> list[dict]:
        """
        Fetch a page and extract individual article links as separate items.

        Each article is identified by its canonical URL, so deduplication is
        stable across scans: new articles (new URLs) are always picked up, while
        articles seen before are skipped without re-analysing identical content.

        Falls back to whole-page extraction when no article links are found.
        """
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError:
            logger.error("web_scraper.bs4_not_installed")
            return []

        try:
            response = requests.get(
                page_url,
                timeout=20,
                headers={"User-Agent": "TDM-Research-Bot/1.0"},
            )
            response.raise_for_status()
        except Exception as exc:
            logger.error("web_scraper.fetch_failed", url=page_url, error=str(exc))
            return []

        from bs4 import BeautifulSoup  # noqa: F811
        soup = BeautifulSoup(response.text, "html.parser")
        base_domain = urlparse(page_url).netloc

        # Strip boilerplate before scanning for links.
        for el in soup(["script", "style", "nav", "footer", "aside"]):
            el.decompose()

        # Gather candidate links from semantic article containers first.
        candidate_links: list = []
        for container in soup.find_all(["article", "main", "section"], limit=50):
            candidate_links.extend(container.find_all("a", href=True))
        if not candidate_links:
            candidate_links = soup.find_all("a", href=True)

        _SKIP_PREFIXES = (
            "/tag/", "/category/", "/author/", "/page/", "/topic/",
            "/search", "/login", "/register", "/about", "/contact",
            "/subscribe", "/newsletter", "/rss", "/feed", "/privacy",
            "/terms", "/cookie",
        )

        seen_urls: set[str] = set()
        articles: list[dict] = []

        for a_tag in candidate_links:
            href = (a_tag.get("href") or "").strip()
            if not href:
                continue

            full_url = urljoin(page_url, href)
            parsed = urlparse(full_url)

            # Same domain, http/https only.
            if parsed.scheme not in ("http", "https") or parsed.netloc != base_domain:
                continue

            # Use path-only canonical URL as the stable article ID.
            canonical = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
            if canonical in seen_urls or canonical == page_url.rstrip("/"):
                continue

            # Article paths need at least 2 segments (e.g. /news/story-slug).
            path_parts = [p for p in parsed.path.strip("/").split("/") if p]
            if len(path_parts) < 2:
                continue

            # Skip obvious non-article paths.
            if any(parsed.path.lower().startswith(s) for s in _SKIP_PREFIXES):
                continue

            seen_urls.add(canonical)

            # Title: link text → heading ancestor → skip if too short.
            title = a_tag.get_text(strip=True)
            if not title or len(title) < 8:
                parent_h = a_tag.find_parent(["h1", "h2", "h3", "h4"])
                if parent_h:
                    title = parent_h.get_text(strip=True)
            if not title or len(title) < 8:
                continue

            # Snippet: nearest <p> after the link on the page.
            snippet = ""
            next_p = a_tag.find_next("p")
            if next_p:
                snippet = next_p.get_text(strip=True)[:400]

            ext_id = "url:" + hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:24]
            articles.append({
                "external_id": ext_id,
                "source_type": "url",
                "source": page_url,
                "title": title[:300],
                "text": f"{title}\n\n{snippet}".strip() if snippet else title,
                "url": canonical,
            })

            if len(articles) >= max_articles:
                break

        # Fallback: return the whole page as a single item.
        if not articles:
            for el in soup(["script", "style"]):
                el.decompose()
            text = soup.get_text(separator="\n", strip=True)
            text = re.sub(r"\n\s*\n", "\n\n", text)
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else page_url
            fp = hashlib.sha1(f"{title}\n{text[:500]}".encode("utf-8")).hexdigest()[:16]
            articles.append({
                "external_id": f"url:{page_url}:{fp}",
                "source_type": "url",
                "source": page_url,
                "title": title,
                "text": text[:10000],
                "url": page_url,
            })

        logger.info(
            "web_scraper.articles_extracted",
            url=page_url,
            count=len(articles),
        )
        return articles

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
