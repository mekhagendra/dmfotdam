"""Monitoring-source models for MongoDB + API.

A "source" is a recurring real-time data stream the system polls. Examples:
  * reddit subreddit
  * rss feed (news site or Telegram-via-RSSHub bridge)
  * url (periodic scrape of a single page)
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    REDDIT = "reddit"
    RSS = "rss"
    TELEGRAM = "telegram"
    URL = "url"


class SourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    url: str = Field(..., min_length=1, max_length=1000)
    source_type: SourceType
    keywords: List[str] = Field(default_factory=list)
    check_interval: int = Field(300, ge=30, le=86_400)


class SourceInDB(BaseModel):
    name: str
    url: str                     # subreddit name, feed URL, or channel slug
    source_type: str             # one of SourceType values
    keywords: List[str] = Field(default_factory=list)
    is_active: bool = True
    check_interval: int = 300
    last_checked: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SourcePublic(BaseModel):
    id: str
    name: str
    url: str
    source_type: str
    keywords: List[str]
    is_active: bool
    check_interval: int
    last_checked: Optional[datetime] = None
    created_at: datetime
