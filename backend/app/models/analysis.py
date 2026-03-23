"""
Analysis result database model
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    analysis_type = Column(String(50), nullable=False)  # document, text, url
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    threat_score = Column(Float, default=0.0)  # 0.0 to 1.0
    threat_level = Column(String(20), default="low")  # low, medium, high, critical
    summary = Column(Text)
    details = Column(JSON)  # detailed analysis results
    keywords = Column(JSON)  # extracted keywords
    entities = Column(JSON)  # named entities
    sentiment = Column(String(20))  # positive, negative, neutral
    language = Column(String(10))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    document = relationship("Document", back_populates="analyses")
    user = relationship("User", back_populates="analyses")
