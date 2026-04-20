"""Alert models for MongoDB + API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AlertInDB(BaseModel):
    title: str
    description: Optional[str] = None
    threat_level: str                      # low | medium | high | critical
    threat_score: float = 0.0
    source: Optional[str] = None           # URL or identifier
    source_type: Optional[str] = None      # reddit | rss | telegram | document | url
    details: Optional[Dict[str, Any]] = None
    is_read: bool = False
    is_resolved: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None


class AlertPublic(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    threat_level: str
    threat_score: float
    source: Optional[str] = None
    source_type: Optional[str] = None
    is_read: bool
    is_resolved: bool
    created_at: datetime
