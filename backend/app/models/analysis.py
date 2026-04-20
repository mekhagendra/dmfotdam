"""Analysis result models for MongoDB + API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AnalyzeTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=200_000)


class AnalysisInDB(BaseModel):
    document_id: Optional[str] = None
    user_id: Optional[str] = None
    analysis_type: str                     # document | text | url | reddit | rss | telegram
    status: str = "completed"              # pending | processing | completed | failed
    threat_score: float = 0.0
    threat_level: str = "low"              # low | medium | high | critical
    summary: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    keywords: Optional[List[str]] = None
    sentiment: Optional[str] = None
    language: Optional[str] = None
    source_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class AnalysisPublic(BaseModel):
    id: str
    analysis_type: str
    status: str
    threat_score: Optional[float] = None
    threat_level: Optional[str] = None
    summary: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    keywords: Optional[List[str]] = None
    sentiment: Optional[str] = None
    language: Optional[str] = None
    source_url: Optional[str] = None
    explanation: Optional[Dict[str, Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
