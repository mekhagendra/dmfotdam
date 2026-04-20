"""
Threat-detection endpoints — analyze arbitrary text and fetch results.
"""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_current_user
from app.core.database import analyses_col
from app.models.analysis import AnalysisPublic, AnalyzeTextRequest
from app.services.text_analyzer import TextAnalyzer

router = APIRouter(prefix="/detection", tags=["detection"])


def _to_public(doc: dict) -> AnalysisPublic:
    return AnalysisPublic(
        id=str(doc["_id"]),
        analysis_type=doc.get("analysis_type", "text"),
        status=doc.get("status", "completed"),
        threat_score=doc.get("threat_score"),
        threat_level=doc.get("threat_level"),
        summary=doc.get("summary"),
        details=doc.get("details"),
        keywords=doc.get("keywords"),
        sentiment=doc.get("sentiment"),
        language=doc.get("language"),
        source_url=doc.get("source_url"),
        explanation=doc.get("explanation"),
        created_at=doc.get("created_at"),
        completed_at=doc.get("completed_at"),
    )


@router.post("/analyze-text", response_model=AnalysisPublic)
async def analyze_text(
    payload: AnalyzeTextRequest,
    explain: bool = Query(False, description="Include SHAP token-level explanation"),
    current=Depends(get_current_user),
) -> AnalysisPublic:
    analyzer = TextAnalyzer()
    result = await analyzer.analyze(payload.text, explain=explain)
    now = datetime.now(timezone.utc)

    doc = {
        "user_id": str(current["_id"]),
        "analysis_type": "text",
        "status": "completed",
        "threat_score": result["threat_score"],
        "threat_level": result["threat_level"],
        "summary": result["summary"],
        "details": result["details"],
        "keywords": result["keywords"],
        "sentiment": result.get("sentiment"),
        "language": result.get("language"),
        "explanation": result.get("explanation"),
        "created_at": now,
        "completed_at": now,
    }
    ins = await analyses_col().insert_one(doc)
    doc["_id"] = ins.inserted_id
    return _to_public(doc)


@router.get("/results/{analysis_id}", response_model=AnalysisPublic)
async def get_analysis_result(
    analysis_id: str, current=Depends(get_current_user)
) -> AnalysisPublic:
    try:
        oid = ObjectId(analysis_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid analysis id")

    doc = await analyses_col().find_one(
        {"_id": oid, "user_id": str(current["_id"])}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return _to_public(doc)


@router.get("/reports", response_model=list[AnalysisPublic])
async def list_reports(current=Depends(get_current_user)) -> list[AnalysisPublic]:
    cursor = (
        analyses_col()
        .find({"user_id": str(current["_id"])})
        .sort("created_at", -1)
        .limit(100)
    )
    return [_to_public(doc) async for doc in cursor]
