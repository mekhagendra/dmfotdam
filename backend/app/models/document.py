"""Document (uploaded file) models for MongoDB."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class DocumentInDB(BaseModel):
    filename: str
    original_filename: str
    file_type: str
    file_size: Optional[int] = None
    file_path: str
    status: str = "pending"          # pending | processing | completed | failed
    uploaded_by: str                 # user id (ObjectId string)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DocumentPublic(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_type: str
    file_size: Optional[int] = None
    status: str
    created_at: datetime
