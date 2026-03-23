"""
File handling utilities
"""

import os
from fastapi import HTTPException

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv", ".xlsx", ".xls", ".json"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/json",
}

DATA_FILE_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json"}


def validate_file_type(filename: str) -> None:
    """Validate that the file has an allowed extension"""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )


def save_upload_file(content: bytes, filename: str, upload_dir: str) -> str:
    """Save uploaded file content to disk securely"""
    os.makedirs(upload_dir, exist_ok=True)

    # Ensure safe filename (already UUID-based from caller)
    safe_name = os.path.basename(filename)
    file_path = os.path.join(upload_dir, safe_name)

    with open(file_path, "wb") as f:
        f.write(content)

    return file_path


def delete_file(file_path: str) -> bool:
    """Delete a file from disk"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except OSError:
        return False
