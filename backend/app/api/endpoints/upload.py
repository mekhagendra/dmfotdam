"""
File-upload endpoints — accept documents, classify them, persist results.

Documents must be CSV or Excel format:
  - First row is the header (automatically discarded by pandas).
  - First column must contain the message/text to analyse.
  - All other columns are ignored.
  - Each row is analysed independently and per-row scores are returned.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, Query, status
from pydantic import BaseModel

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.database import analyses_col, documents_col
from app.models.analysis import AnalysisPublic
from app.models.document import DocumentPublic
from app.services.email_service import build_scan_report_email, send_email
from app.services.text_analyzer import TextAnalyzer
from app.utils.file_handler import save_upload_file

router = APIRouter(prefix="/upload", tags=["upload"])
_settings = get_settings()

# Only CSV and Excel are accepted — document must have message in first column
ALLOWED_EXT = {".csv", ".xlsx", ".xls"}


class UploadResponse(BaseModel):
    document: DocumentPublic
    analysis_id: str
    message: str


def _doc_public(doc: dict) -> DocumentPublic:
    return DocumentPublic(
        id=str(doc["_id"]),
        filename=doc["filename"],
        original_filename=doc["original_filename"],
        file_type=doc["file_type"],
        file_size=doc.get("file_size"),
        status=doc.get("status", "completed"),
        created_at=doc["created_at"],
    )


def _to_analysis_public(doc: dict) -> AnalysisPublic:
    return AnalysisPublic(
        id=str(doc["_id"]),
        analysis_type=doc.get("analysis_type", "document"),
        status=doc.get("status", "completed"),
        threat_score=doc.get("threat_score"),
        threat_level=doc.get("threat_level"),
        summary=doc.get("summary"),
        details=doc.get("details"),
        keywords=doc.get("keywords"),
        sentiment=doc.get("sentiment"),
        language=doc.get("language"),
        row_results=doc.get("row_results"),
        model_scores=doc.get("model_scores"),
        created_at=doc.get("created_at"),
        completed_at=doc.get("completed_at"),
    )


@router.post("/document", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    models: Optional[str] = Query(
        None,
        description="Comma-separated model IDs to use, e.g. 'sgd,rf,linsvc'. Leave empty for default ensemble.",
    ),
    current=Depends(get_current_user),
) -> UploadResponse:
    """Upload a CSV or Excel document for row-by-row threat analysis.
    
    Requirements:
    - File must be .csv, .xlsx, or .xls
    - First row is treated as header and discarded
    - First column must contain the message/text for each row
    - All other columns are ignored
    - Each row is analysed independently
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            status_code=400,
            detail=(
                "Only CSV and Excel files are accepted for document analysis. "
                f"Allowed: {', '.join(sorted(ALLOWED_EXT))}. "
                "The file must have the message text in the first column; "
                "the first row (header) will be discarded automatically."
            ),
        )

    content = await file.read()
    if len(content) > _settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {_settings.MAX_FILE_SIZE // (1024*1024)} MB",
        )

    # Parse model IDs from query param
    model_ids: Optional[List[str]] = None
    if models:
        model_ids = [m.strip() for m in models.split(",") if m.strip()]

    safe_name = f"{uuid.uuid4().hex}{ext}"
    file_path = save_upload_file(content, safe_name, _settings.UPLOAD_DIR)

    now = datetime.now(timezone.utc)
    doc = {
        "filename": safe_name,
        "original_filename": file.filename,
        "file_type": ext.lstrip("."),
        "file_size": len(content),
        "file_path": file_path,
        "status": "processing",
        "uploaded_by": str(current["_id"]),
        "created_at": now,
    }
    doc_ins = await documents_col().insert_one(doc)
    doc["_id"] = doc_ins.inserted_id

    analyzer = TextAnalyzer()
    try:
        result = await analyzer.analyze_document_rows(file_path, doc["file_type"], models=model_ids)
        status_ = "completed"
    except Exception as exc:
        result = {
            "threat_score": 0.0,
            "threat_level": "low",
            "summary": f"Analysis failed: {exc}",
            "details": {"error": str(exc)},
            "keywords": [],
            "sentiment": None,
            "language": "unknown",
            "row_results": None,
            "model_scores": None,
        }
        status_ = "failed"

    await documents_col().update_one({"_id": doc["_id"]}, {"$set": {"status": status_}})
    doc["status"] = status_

    analysis_doc = {
        "document_id": str(doc["_id"]),
        "user_id": str(current["_id"]),
        "analysis_type": "document",
        "status": status_,
        "threat_score": result["threat_score"],
        "threat_level": result["threat_level"],
        "summary": result["summary"],
        "details": result["details"],
        "keywords": result["keywords"],
        "sentiment": result.get("sentiment"),
        "language": result.get("language"),
        "row_results": result.get("row_results"),
        "model_scores": result.get("model_scores"),
        "created_at": now,
        "completed_at": datetime.now(timezone.utc),
    }
    ana_ins = await analyses_col().insert_one(analysis_doc)

    # Fire-and-forget post-scan report email
    user_email = current.get("email")
    if user_email:
        subject, plain, html = build_scan_report_email(
            user_name=current.get("full_name") or current.get("username") or "there",
            scan_type="document",
            source_label=f'File: {file.filename}',
            threat_score=float(result.get("threat_score") or 0.0),
            threat_level=str(result.get("threat_level") or "low"),
            summary=str(result.get("summary") or "—"),
            keywords=result.get("keywords") or [],
            model_used=",".join(model_ids) if model_ids else "distilbert",
        )
        background_tasks.add_task(send_email, user_email, subject, plain, html)

    return UploadResponse(
        document=_doc_public(doc),
        analysis_id=str(ana_ins.inserted_id),
        message="Document uploaded and analysed",
    )


@router.get("/analysis/{analysis_id}", response_model=AnalysisPublic)
async def get_document_analysis(
    analysis_id: str,
    current=Depends(get_current_user),
) -> AnalysisPublic:
    """Retrieve full analysis result (including per-row results) for a document."""
    try:
        oid = ObjectId(analysis_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid analysis id")
    doc = await analyses_col().find_one(
        {"_id": oid, "user_id": str(current["_id"])}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return _to_analysis_public(doc)


@router.get("/history", response_model=list[DocumentPublic])
async def upload_history(current=Depends(get_current_user)) -> list[DocumentPublic]:
    cursor = (
        documents_col()
        .find({"uploaded_by": str(current["_id"])})
        .sort("created_at", -1)
        .limit(50)
    )
    return [_doc_public(doc) async for doc in cursor]


@router.get("/status/{document_id}")
async def upload_status(document_id: str, current=Depends(get_current_user)) -> dict:
    try:
        oid = ObjectId(document_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid document id")
    doc = await documents_col().find_one(
        {"_id": oid, "uploaded_by": str(current["_id"])}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "id": str(doc["_id"]),
        "status": doc.get("status"),
        "filename": doc.get("original_filename"),
    }
