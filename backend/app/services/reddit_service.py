"""
Reddit data mining service for real-time extremism monitoring.

Uses the Reddit API (via PRAW) to:
  - Monitor configurable subreddits for extremism-related content
  - Analyse new posts/comments through the ML threat detection pipeline
  - Store flagged content with threat scores and metadata
  - Generate daily trend data (post counts, threat levels, top subreddits)

Requires a Reddit app with API credentials:
  1. Go to https://www.reddit.com/prefs/apps
  2. Create a "script" type application
  3. Set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT in .env
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

# Default subreddits to monitor (public, research-appropriate)
DEFAULT_SUBREDDITS = [
    "worldnews",
    "news",
    "geopolitics",
    "terrorism",
    "CredibleDefense",
    "IntelligenceNews",
    "extremism",
]

# Keywords that boost priority in scanning
PRIORITY_KEYWORDS = [
    "extremist", "extremism", "radical", "radicalization", "radicalisation",
    "terror", "terrorism", "terrorist", "militant", "insurgent",
    "propaganda", "recruitment", "jihad", "fundamentalist",
    "bomb", "attack", "threat", "violence", "weapon",
    "lone wolf", "cell", "sleeper", "martyrdom",
]


class RedditService:
    """Service for mining Reddit content and analyzing for extremism threats."""

    def __init__(self):
        self._reddit = None
        self._initialized = False

    def _get_reddit(self):
        """Lazy-initialize PRAW Reddit instance."""
        if self._reddit is not None:
            return self._reddit

        try:
            import praw
        except ImportError:
            logger.error("praw not installed. Run: pip install praw")
            return None

        from app.core.config import get_settings
        settings = get_settings()

        client_id = settings.REDDIT_CLIENT_ID
        client_secret = settings.REDDIT_CLIENT_SECRET
        user_agent = settings.REDDIT_USER_AGENT

        if not client_id or not client_secret:
            logger.warning(
                "Reddit API credentials not configured. "
                "Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env"
            )
            return None

        try:
            self._reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
            )
            self._reddit.read_only = True
            # Verify credentials by making a lightweight API call
            self._reddit.user.me()
            logger.info("Reddit API connected (read-only mode)")
            self._initialized = True
            return self._reddit
        except Exception as e:
            logger.error("Failed to initialize Reddit API – check your REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env", error=str(e))
            self._reddit = None
            return None

    @property
    def is_available(self) -> bool:
        return self._get_reddit() is not None

    # ── Fetch posts from subreddits ──────────────────────────────────
    def fetch_recent_posts(
        self,
        subreddits: Optional[list[str]] = None,
        limit: int = 50,
        time_filter: str = "day",
    ) -> list[dict]:
        """
        Fetch recent posts from specified subreddits.

        Args:
            subreddits: List of subreddit names (without r/). Uses defaults if None.
            limit: Max posts per subreddit.
            time_filter: "hour", "day", "week", "month", "year", "all"

        Returns:
            List of post dicts with id, title, text, subreddit, author, url, score, etc.
        """
        reddit = self._get_reddit()
        if reddit is None:
            return []

        if subreddits is None:
            subreddits = DEFAULT_SUBREDDITS

        posts = []
        for sub_name in subreddits:
            try:
                subreddit = reddit.subreddit(sub_name)
                for submission in subreddit.new(limit=limit):
                    # Combine title and selftext for analysis
                    full_text = f"{submission.title}. {submission.selftext}" if submission.selftext else submission.title

                    posts.append({
                        "reddit_id": submission.id,
                        "subreddit": sub_name,
                        "title": submission.title,
                        "text": full_text,
                        "selftext": submission.selftext or "",
                        "author": str(submission.author) if submission.author else "[deleted]",
                        "url": f"https://reddit.com{submission.permalink}",
                        "score": submission.score,
                        "num_comments": submission.num_comments,
                        "created_utc": datetime.fromtimestamp(
                            submission.created_utc, tz=timezone.utc
                        ).isoformat(),
                        "is_self": submission.is_self,
                        "link_url": submission.url if not submission.is_self else None,
                    })

                logger.info(f"Fetched {limit} posts from r/{sub_name}")
            except Exception as e:
                logger.warning(f"Failed to fetch from r/{sub_name}", error=str(e))

        return posts

    def fetch_comments_for_post(self, post_id: str, limit: int = 20) -> list[dict]:
        """Fetch top-level comments for a Reddit post."""
        reddit = self._get_reddit()
        if reddit is None:
            return []

        try:
            submission = reddit.submission(id=post_id)
            submission.comments.replace_more(limit=0)

            comments = []
            for comment in submission.comments[:limit]:
                comments.append({
                    "reddit_id": comment.id,
                    "post_id": post_id,
                    "text": comment.body,
                    "author": str(comment.author) if comment.author else "[deleted]",
                    "score": comment.score,
                    "created_utc": datetime.fromtimestamp(
                        comment.created_utc, tz=timezone.utc
                    ).isoformat(),
                })
            return comments
        except Exception as e:
            logger.warning(f"Failed to fetch comments for {post_id}", error=str(e))
            return []

    def search_reddit(
        self,
        query: str,
        subreddits: Optional[list[str]] = None,
        limit: int = 25,
        time_filter: str = "day",
        sort: str = "relevance",
    ) -> list[dict]:
        """
        Search Reddit for specific terms.

        Args:
            query: Search query string
            subreddits: Limit search to these subreddits (None = all)
            limit: Maximum results
            time_filter: Time period filter
            sort: "relevance", "hot", "top", "new", "comments"
        """
        reddit = self._get_reddit()
        if reddit is None:
            return []

        posts = []
        try:
            if subreddits:
                sub_str = "+".join(subreddits)
                subreddit = reddit.subreddit(sub_str)
            else:
                subreddit = reddit.subreddit("all")

            for submission in subreddit.search(
                query, limit=limit, time_filter=time_filter, sort=sort
            ):
                full_text = f"{submission.title}. {submission.selftext}" if submission.selftext else submission.title
                posts.append({
                    "reddit_id": submission.id,
                    "subreddit": str(submission.subreddit),
                    "title": submission.title,
                    "text": full_text,
                    "selftext": submission.selftext or "",
                    "author": str(submission.author) if submission.author else "[deleted]",
                    "url": f"https://reddit.com{submission.permalink}",
                    "score": submission.score,
                    "num_comments": submission.num_comments,
                    "created_utc": datetime.fromtimestamp(
                        submission.created_utc, tz=timezone.utc
                    ).isoformat(),
                })

            logger.info(f"Search '{query}' returned {len(posts)} results")
        except Exception as e:
            logger.warning(f"Reddit search failed for '{query}'", error=str(e))

        return posts

    # ── Analyze and score posts ──────────────────────────────────────
    def analyze_posts(self, posts: list[dict]) -> list[dict]:
        """
        Run each post through the ML threat analysis pipeline.
        Returns posts augmented with threat_score, threat_level, and analysis details.
        """
        from app.services.text_analyzer import TextAnalyzer
        analyzer = TextAnalyzer()

        analyzed = []
        for post in posts:
            text = post.get("text", "")
            if not text or len(text.strip()) < 10:
                post["threat_score"] = 0.0
                post["threat_level"] = "low"
                post["analysis"] = None
                analyzed.append(post)
                continue

            try:
                result = analyzer.analyze(text)
                post["threat_score"] = result["threat_score"]
                post["threat_level"] = result["threat_level"]
                post["analysis"] = {
                    "summary": result.get("summary", ""),
                    "keyword_hits": result.get("details", {}).get("keyword_hits", {}),
                    "categories_detected": result.get("details", {}).get("categories_detected", []),
                    "sentiment": result.get("sentiment"),
                    "analysis_method": result.get("details", {}).get("analysis_method", "unknown"),
                }
            except Exception as e:
                logger.warning(f"Analysis failed for post {post.get('reddit_id')}", error=str(e))
                post["threat_score"] = 0.0
                post["threat_level"] = "low"
                post["analysis"] = None

            analyzed.append(post)

        return analyzed

    def has_priority_keywords(self, text: str) -> list[str]:
        """Check which priority keywords appear in text."""
        text_lower = text.lower()
        return [kw for kw in PRIORITY_KEYWORDS if kw in text_lower]

    # ── Full scan pipeline ───────────────────────────────────────────
    def run_scan(
        self,
        subreddits: Optional[list[str]] = None,
        limit: int = 50,
        threat_threshold: float = 0.3,
    ) -> dict:
        """
        Complete scan pipeline:
        1. Fetch recent posts from subreddits
        2. Analyze each post for threats
        3. Filter and return flagged content

        Returns dict with:
          - all_posts: all analyzed posts
          - flagged_posts: posts above threat threshold
          - scan_summary: counts and stats
          - scan_time: ISO timestamp
        """
        logger.info("Starting Reddit scan", subreddits=subreddits or DEFAULT_SUBREDDITS)

        posts = self.fetch_recent_posts(subreddits=subreddits, limit=limit)
        if not posts:
            return {
                "all_posts": [],
                "flagged_posts": [],
                "scan_summary": {"total": 0, "flagged": 0, "avg_threat_score": 0},
                "scan_time": datetime.now(timezone.utc).isoformat(),
            }

        analyzed = self.analyze_posts(posts)
        flagged = [p for p in analyzed if p["threat_score"] >= threat_threshold]

        # Sort flagged by threat score descending
        flagged.sort(key=lambda p: p["threat_score"], reverse=True)

        scores = [p["threat_score"] for p in analyzed]
        avg_score = sum(scores) / len(scores) if scores else 0

        summary = {
            "total": len(analyzed),
            "flagged": len(flagged),
            "avg_threat_score": round(avg_score, 4),
            "subreddits_scanned": list(set(p["subreddit"] for p in analyzed)),
            "threat_levels": {
                "high": len([p for p in analyzed if p["threat_level"] == "high"]),
                "low": len([p for p in analyzed if p["threat_level"] == "low"]),
            },
        }

        logger.info(
            "Reddit scan complete",
            total=summary["total"],
            flagged=summary["flagged"],
            avg_score=summary["avg_threat_score"],
        )

        return {
            "all_posts": analyzed,
            "flagged_posts": flagged,
            "scan_summary": summary,
            "scan_time": datetime.now(timezone.utc).isoformat(),
        }
