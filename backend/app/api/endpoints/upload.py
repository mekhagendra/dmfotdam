"""
File-upload endpoints — accept documents, classify them, persist results.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.database import analyses_col, documents_col
from app.models.document import DocumentPublic
from app.services.email_service import build_scan_report_email, send_email
from app.services.text_analyzer import TextAnalyzer
from app.utils.file_handler import save_upload_file

router = APIRouter(prefix="/upload", tags=["upload"])
_settings = get_settings()

ALLOWED_EXT = {".pdf", ".docx", ".txt", ".csv", ".xlsx", ".xls", ".json"}


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


@router.post("/document", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current=Depends(get_current_user),
) -> UploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXT))}",
        )

    content = await file.read()
    if len(content) > _settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {_settings.MAX_FILE_SIZE // (1024*1024)} MB",
        )

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
        result = await analyzer.analyze_file(file_path, doc["file_type"])
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
        "created_at": now,
        "completed_at": datetime.now(timezone.utc),
    }
    ana_ins = await analyses_col().insert_one(analysis_doc)

    # Fire-and-forget post-scan report email to the logged-in user
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
            model_used=(result.get("details") or {}).get("model"),
        )
        background_tasks.add_task(send_email, user_email, subject, plain, html)

    return UploadResponse(
        document=_doc_public(doc),
        analysis_id=str(ana_ins.inserted_id),
        message="Document uploaded and analyzed",
    )


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
