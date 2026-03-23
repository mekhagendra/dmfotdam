"""
Alert database model
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, JSON
from app.core.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    threat_level = Column(String(20), nullable=False)  # low, medium, high, critical
    threat_score = Column(Float, default=0.0)
    source = Column(String(255))  # where the threat was detected
    source_type = Column(String(50))  # document, url, social_media
    details = Column(JSON)
    is_read = Column(Boolean, default=False)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)


class MonitoringSource(Base):
    __tablename__ = "monitoring_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    source_type = Column(String(50), nullable=False)  # website, rss, social_media
    keywords = Column(JSON)  # keywords to monitor
    is_active = Column(Boolean, default=True)
    check_interval = Column(Integer, default=300)  # seconds between checks
    last_checked = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
