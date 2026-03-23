"""
File upload endpoints
"""

import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import get_settings
from app.core.security import get_current_user_id
from app.models.document import Document
from app.models.analysis import Analysis
from app.utils.file_handler import save_upload_file, validate_file_type, DATA_FILE_EXTENSIONS
from app.services.text_analyzer import TextAnalyzer

router = APIRouter()
settings = get_settings()


class DocumentResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_type: str
    file_size: int | None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    document: DocumentResponse
    analysis_id: int
    message: str


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv", ".xlsx", ".xls", ".json"}


@router.post("/document", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document for threat analysis"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Validate file type
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    validate_file_type(file.filename)

    # Read file content
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {settings.MAX_FILE_SIZE // (1024*1024)}MB",
        )

    # Save file
    safe_filename = f"{uuid.uuid4().hex}{file_ext}"
    file_path = save_upload_file(content, safe_filename, settings.UPLOAD_DIR)

    # Create document record
    document = Document(
        filename=safe_filename,
        original_filename=file.filename,
        file_type=file_ext.lstrip("."),
        file_size=len(content),
        file_path=file_path,
        status="processing",
        uploaded_by=user_id,
    )
    db.add(document)
    await db.flush()
    await db.refresh(document)

    # Create analysis record
    analysis = Analysis(
        document_id=document.id,
        user_id=user_id,
        analysis_type="document",
        status="processing",
    )
    db.add(analysis)
    await db.flush()
    await db.refresh(analysis)

    # Run analysis
    try:
        analyzer = TextAnalyzer()
        file_type_str = file_ext.lstrip(".")

        if file_ext in DATA_FILE_EXTENSIONS:
            # Structured data file: run data profiling + threat analysis
            result = analyzer.analyze_data(file_path, file_type_str)
            threat_result = result["threat_analysis"]
            analysis.threat_score = threat_result["threat_score"]
            analysis.threat_level = threat_result["threat_level"]
            analysis.summary = threat_result["summary"]
            analysis.details = {
                "data_profile": result["data_profile"],
                **threat_result.get("details", {}),
            }
            analysis.keywords = threat_result["keywords"]
            analysis.sentiment = threat_result["sentiment"]
            analysis.language = threat_result.get("language", "en")
            analysis.analysis_type = "data_profiling"
        else:
            # Text-based file: standard threat analysis
            text = analyzer.extract_text_from_file(file_path, file_type_str)
            result = analyzer.analyze(text)
            analysis.threat_score = result["threat_score"]
            analysis.threat_level = result["threat_level"]
            analysis.summary = result["summary"]
            analysis.details = result["details"]
            analysis.keywords = result["keywords"]
            analysis.sentiment = result["sentiment"]
            analysis.language = result.get("language", "en")

        analysis.status = "completed"
        analysis.completed_at = datetime.now(timezone.utc)
        document.status = "completed"
    except Exception:
        analysis.status = "failed"
        document.status = "failed"

    return UploadResponse(
        document=document,
        analysis_id=analysis.id,
        message="Document uploaded and analysis started",
    )


@router.get("/history", response_model=list[DocumentResponse])
async def get_upload_history(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get upload history for the current user"""
    result = await db.execute(
        select(Document)
        .where(Document.uploaded_by == user_id)
        .order_by(desc(Document.created_at))
        .limit(50)
    )
    return result.scalars().all()


@router.get("/status/{document_id}")
async def get_upload_status(
    document_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Check the status of an uploaded document"""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id, Document.uploaded_by == user_id
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"id": doc.id, "status": doc.status, "filename": doc.original_filename}
