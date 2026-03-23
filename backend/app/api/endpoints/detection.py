"""
Threat detection endpoints
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.analysis import Analysis
from app.services.text_analyzer import TextAnalyzer

router = APIRouter()


class TextAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=50000)


class AnalysisResponse(BaseModel):
    id: int
    analysis_type: str
    status: str
    threat_score: float | None
    threat_level: str | None
    summary: str | None
    details: dict | None
    keywords: list | None
    sentiment: str | None
    language: str | None
    created_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True


@router.post("/analyze-text", response_model=AnalysisResponse)
async def analyze_text(
    request: TextAnalysisRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Analyze text content for potential threats"""
    analysis = Analysis(
        user_id=user_id,
        analysis_type="text",
        status="processing",
    )
    db.add(analysis)
    await db.flush()
    await db.refresh(analysis)

    try:
        analyzer = TextAnalyzer()
        result = analyzer.analyze(request.text)

        analysis.threat_score = result["threat_score"]
        analysis.threat_level = result["threat_level"]
        analysis.summary = result["summary"]
        analysis.details = result["details"]
        analysis.keywords = result["keywords"]
        analysis.sentiment = result["sentiment"]
        analysis.language = result.get("language", "en")
        analysis.status = "completed"
        analysis.completed_at = datetime.now(timezone.utc)
    except Exception as e:
        analysis.status = "failed"
        analysis.summary = str(e)

    await db.flush()
    await db.refresh(analysis)
    return analysis


@router.get("/results/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis_results(
    analysis_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get results of a specific analysis"""
    result = await db.execute(
        select(Analysis).where(
            Analysis.id == analysis_id, Analysis.user_id == user_id
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@router.get("/reports", response_model=list[AnalysisResponse])
async def list_reports(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all analysis reports for the current user"""
    result = await db.execute(
        select(Analysis)
        .where(Analysis.user_id == user_id)
        .order_by(desc(Analysis.created_at))
        .limit(100)
    )
    return result.scalars().all()


@router.get("/data-profile/{analysis_id}")
async def get_data_profile(
    analysis_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get data profiling results for a structured data upload (CSV/Excel/JSON)"""
    result = await db.execute(
        select(Analysis).where(
            Analysis.id == analysis_id, Analysis.user_id == user_id
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    details = analysis.details or {}
    data_profile = details.get("data_profile")

    return {
        "id": analysis.id,
        "analysis_type": analysis.analysis_type,
        "status": analysis.status,
        "threat_score": analysis.threat_score,
        "threat_level": analysis.threat_level,
        "summary": analysis.summary,
        "data_profile": data_profile,
        "keywords": analysis.keywords,
        "sentiment": analysis.sentiment,
        "created_at": analysis.created_at,
    }
