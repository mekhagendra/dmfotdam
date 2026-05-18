"""
Threat-detection endpoints — analyze arbitrary text and fetch results.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from app.api.dependencies import get_current_user
from app.core.database import analyses_col
from app.core.logging import get_logger
from app.models.analysis import AnalysisPublic, AnalyzeTextRequest
from app.services.email_service import build_scan_report_email, send_email
from app.services.ml_service import get_available_models
from app.services.text_analyzer import TextAnalyzer

router = APIRouter(prefix="/detection", tags=["detection"])
logger = get_logger(__name__)


def _model_scores_from_doc(doc: dict) -> dict | None:
    """Best-effort model score extraction for legacy analysis records."""
    current = doc.get("model_scores")
    if isinstance(current, dict) and current:
        out = {}
        for k, v in current.items():
            try:
                out[str(k)] = float(v)
            except Exception:
                continue
        if out:
            return out

    details = doc.get("details") or {}
    ml = details.get("ml") if isinstance(details, dict) else {}
    if isinstance(ml, dict):
        per_model = ml.get("per_model_scores")
        if isinstance(per_model, dict) and per_model:
            out = {}
            for k, v in per_model.items():
                try:
                    out[str(k)] = float(v)
                except Exception:
                    continue
            if out:
                return out

        model_name = ml.get("model")
        try:
            score = float(doc.get("threat_score"))
        except Exception:
            score = None
        if model_name and score is not None:
            return {str(model_name): score}

    return None


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
        row_results=doc.get("row_results"),
        model_scores=_model_scores_from_doc(doc),
        created_at=doc.get("created_at"),
        completed_at=doc.get("completed_at"),
    )


@router.get("/models", response_model=list[dict])
async def list_models(_: dict = Depends(get_current_user)) -> list[dict]:
    """Return available ML models."""
    return get_available_models()


@router.post("/analyze-text", response_model=AnalysisPublic)
async def analyze_text(
    payload: AnalyzeTextRequest,
    background_tasks: BackgroundTasks,
    explain: bool = Query(False, description="Include SHAP token-level explanation"),
    current=Depends(get_current_user),
) -> AnalysisPublic:
    analyzer = TextAnalyzer()
    # Use models list if provided, otherwise fall back to single model
    if payload.models and len(payload.models) > 0:
        result = await analyzer.analyze(payload.text, models=payload.models)
    else:
        result = await analyzer.analyze(payload.text, explain=explain, model=payload.model)
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
        "model_scores": result.get("model_scores"),
        "created_at": now,
        "completed_at": now,
    }
    ins = await analyses_col().insert_one(doc)
    doc["_id"] = ins.inserted_id

    # Fire-and-forget post-scan report email to the logged-in user
    user_email = current.get("email")
    if user_email:
        snippet = (payload.text or "").strip().replace("\n", " ")
        if len(snippet) > 80:
            snippet = snippet[:80] + "…"
        models_label = ",".join(payload.models) if payload.models else payload.model
        subject, plain, html = build_scan_report_email(
            user_name=current.get("full_name") or current.get("username") or "there",
            scan_type="text",
            source_label=f'Text input: "{snippet}"' if snippet else "Text input",
            threat_score=float(result.get("threat_score") or 0.0),
            threat_level=str(result.get("threat_level") or "low"),
            summary=str(result.get("summary") or "—"),
            keywords=result.get("keywords") or [],
            model_used=models_label,
        )
        background_tasks.add_task(send_email, user_email, subject, plain, html)

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
