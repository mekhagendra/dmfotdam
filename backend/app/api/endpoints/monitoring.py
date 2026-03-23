"""
Live monitoring endpoints
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel, Field, HttpUrl

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.alert import Alert, MonitoringSource

router = APIRouter()


class SourceCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    url: HttpUrl
    source_type: str = Field(..., pattern="^(website|rss|social_media)$")
    keywords: list[str] = []
    check_interval: int = Field(300, ge=60, le=86400)


class SourceResponse(BaseModel):
    id: int
    name: str
    url: str
    source_type: str
    keywords: list | None
    is_active: bool
    check_interval: int
    last_checked: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    id: int
    title: str
    description: str | None
    threat_level: str
    threat_score: float
    source: str | None
    source_type: str | None
    is_read: bool
    is_resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DashboardMetrics(BaseModel):
    total_analyses: int
    total_alerts: int
    critical_alerts: int
    high_alerts: int
    active_sources: int
    avg_threat_score: float


@router.post("/sources", response_model=SourceResponse, status_code=201)
async def create_source(
    request: SourceCreateRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Configure a new monitoring source"""
    source = MonitoringSource(
        name=request.name,
        url=str(request.url),
        source_type=request.source_type,
        keywords=request.keywords,
        check_interval=request.check_interval,
    )
    db.add(source)
    await db.flush()
    await db.refresh(source)
    return source


@router.get("/sources", response_model=list[SourceResponse])
async def list_sources(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all monitoring sources"""
    result = await db.execute(
        select(MonitoringSource).order_by(desc(MonitoringSource.created_at))
    )
    return result.scalars().all()


@router.delete("/sources/{source_id}", status_code=204)
async def delete_source(
    source_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a monitoring source"""
    result = await db.execute(
        select(MonitoringSource).where(MonitoringSource.id == source_id)
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    await db.delete(source)


@router.get("/alerts", response_model=list[AlertResponse])
async def get_alerts(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get recent alerts"""
    result = await db.execute(
        select(Alert).order_by(desc(Alert.created_at)).limit(100)
    )
    return result.scalars().all()


@router.patch("/alerts/{alert_id}/read")
async def mark_alert_read(
    alert_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Mark an alert as read"""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_read = True
    return {"message": "Alert marked as read"}


@router.patch("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Resolve an alert"""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_resolved = True
    alert.resolved_at = datetime.now(timezone.utc)
    return {"message": "Alert resolved"}


@router.get("/dashboard/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get dashboard metrics"""
    from sqlalchemy import func
    from app.models.analysis import Analysis

    # Total analyses
    total_analyses = (
        await db.execute(select(func.count()).select_from(Analysis))
    ).scalar() or 0

    # Alerts counts
    total_alerts = (
        await db.execute(select(func.count()).select_from(Alert))
    ).scalar() or 0

    critical_alerts = (
        await db.execute(
            select(func.count())
            .select_from(Alert)
            .where(Alert.threat_level == "critical", Alert.is_resolved == False)  # noqa: E712
        )
    ).scalar() or 0

    high_alerts = (
        await db.execute(
            select(func.count())
            .select_from(Alert)
            .where(Alert.threat_level == "high", Alert.is_resolved == False)  # noqa: E712
        )
    ).scalar() or 0

    # Active sources
    active_sources = (
        await db.execute(
            select(func.count())
            .select_from(MonitoringSource)
            .where(MonitoringSource.is_active == True)  # noqa: E712
        )
    ).scalar() or 0

    # Avg threat score
    avg_score = (
        await db.execute(
            select(func.avg(Analysis.threat_score)).where(
                Analysis.status == "completed"
            )
        )
    ).scalar() or 0.0

    return DashboardMetrics(
        total_analyses=total_analyses,
        total_alerts=total_alerts,
        critical_alerts=critical_alerts,
        high_alerts=high_alerts,
        active_sources=active_sources,
        avg_threat_score=round(float(avg_score), 4),
    )
