"""
DEPRECATED — kept only for import compatibility.

The real Reddit pipeline now lives in:
    * app/services/reddit_collector.py   (PRAW fetching)
    * app/services/collector_manager.py  (orchestration + MongoDB persistence)
"""

from app.services import reddit_collector  # noqa: F401

fetch_subreddit = reddit_collector.fetch_subreddit
