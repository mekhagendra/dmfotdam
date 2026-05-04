"""Analysis result models for MongoDB + API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AnalyzeTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=200_000)
    model: str = Field("distilbert", description="ML model to use: 'rf', 'sgd', 'linsvc', 'distilbert', or 'all'")
    models: Optional[List[str]] = Field(None, description="List of model IDs to use (overrides 'model' if provided)")


class RowResult(BaseModel):
    """Per-row analysis result for CSV/Excel documents."""
    row: int
    message: str
    threat_score: float
    threat_level: str
    model_scores: Optional[Dict[str, float]] = None


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
    row_results: Optional[List[Dict[str, Any]]] = None
    model_scores: Optional[Dict[str, float]] = None
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
    row_results: Optional[List[Dict[str, Any]]] = None
    model_scores: Optional[Dict[str, float]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
