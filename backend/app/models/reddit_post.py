"""
Reddit post database model — stores flagged content from Reddit monitoring.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, JSON
from app.core.database import Base


class RedditPost(Base):
    __tablename__ = "reddit_posts"

    id = Column(Integer, primary_key=True, index=True)
    reddit_id = Column(String(20), unique=True, index=True, nullable=False)
    subreddit = Column(String(100), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    text = Column(Text, default="")
    author = Column(String(100), default="[deleted]")
    url = Column(String(500), default="")
    score = Column(Integer, default=0)
    num_comments = Column(Integer, default=0)

    # Threat analysis results
    threat_score = Column(Float, default=0.0, index=True)
    threat_level = Column(String(20), default="low", index=True)
    analysis_details = Column(JSON, nullable=True)

    # Timestamps
    posted_at = Column(DateTime, nullable=True)
    scanned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    is_reviewed = Column(Boolean, default=False)
    reviewed_at = Column(DateTime, nullable=True)
