"""Admin user-management and model-training endpoints."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_admin_user, user_to_public
from app.core.database import users_col
from app.models.user import UserAdminUpdate, UserPublic

router = APIRouter(prefix="/users", tags=["users"])

# ---------------------------------------------------------------------------
# In-memory training job tracker
# ---------------------------------------------------------------------------
_training_jobs: Dict[str, Dict[str, Any]] = {}
_training_lock = threading.Lock()


@router.get("", response_model=list[UserPublic])
async def list_users(_: dict = Depends(get_current_admin_user)) -> list[UserPublic]:
    """Return all users for admin management screens."""
    cursor = users_col().find({}).sort("created_at", -1)
    users = await cursor.to_list(length=500)
    return [UserPublic(**user_to_public(user)) for user in users]


@router.patch("/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: str,
    payload: UserAdminUpdate,
    current_admin: dict = Depends(get_current_admin_user),
) -> UserPublic:
    """Update user role/status (admin only)."""
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")

    target_user = await users_col().find_one({"_id": oid})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    updates = {}

    if payload.role is not None:
        if str(target_user["_id"]) == str(current_admin["_id"]) and payload.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot remove your own admin role",
            )
        updates["role"] = payload.role

    if payload.status is not None:
        if str(target_user["_id"]) == str(current_admin["_id"]) and payload.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own account",
            )
        updates["status"] = payload.status
        updates["is_active"] = payload.status == "active"

    if not updates:
        raise HTTPException(status_code=400, detail="No changes provided")

    updates["updated_at"] = datetime.now(timezone.utc)
    await users_col().update_one({"_id": oid}, {"$set": updates})

    updated_user = await users_col().find_one({"_id": oid})
    return UserPublic(**user_to_public(updated_user))


# ---------------------------------------------------------------------------
# Model training endpoints (admin only)
# ---------------------------------------------------------------------------

def _run_training_job(job_id: str, script_path: str) -> None:
    """Execute the training script in a background thread and update job status."""
    with _training_lock:
        _training_jobs[job_id]["status"] = "running"
        _training_jobs[job_id]["started_at"] = datetime.now(timezone.utc).isoformat()

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour max
        )
        with _training_lock:
            if result.returncode == 0:
                _training_jobs[job_id]["status"] = "completed"
                _training_jobs[job_id]["output"] = result.stdout[-4000:] if result.stdout else ""
            else:
                _training_jobs[job_id]["status"] = "failed"
                _training_jobs[job_id]["error"] = result.stderr[-2000:] if result.stderr else "Unknown error"
                _training_jobs[job_id]["output"] = result.stdout[-2000:] if result.stdout else ""
    except subprocess.TimeoutExpired:
        with _training_lock:
            _training_jobs[job_id]["status"] = "failed"
            _training_jobs[job_id]["error"] = "Training timed out after 1 hour"
    except Exception as exc:
        with _training_lock:
            _training_jobs[job_id]["status"] = "failed"
            _training_jobs[job_id]["error"] = str(exc)
    finally:
        with _training_lock:
            _training_jobs[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()

        # After training completes, reload sklearn models from disk
        try:
            from app.services.ml_service import reload_sklearn_models
            reload_sklearn_models()
        except Exception:
            pass


@router.post("/train-models")
async def train_models(
    _: dict = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """Trigger retraining of all ML models (admin only).
    
    Runs the train_models.py script in the background.
    Returns a job_id that can be polled for status.
    """
    # Prevent concurrent training runs
    with _training_lock:
        running = [j for j in _training_jobs.values() if j["status"] == "running"]
        if running:
            return {
                "status": "already_running",
                "job_id": running[0]["job_id"],
                "message": "A training job is already in progress",
            }

    # Locate training script
    script_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "scripts", "train_models.py",
    )
    if not os.path.exists(script_path):
        raise HTTPException(
            status_code=500,
            detail=f"Training script not found at: {script_path}",
        )

    job_id = uuid.uuid4().hex
    with _training_lock:
        _training_jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "started_at": None,
            "completed_at": None,
            "output": None,
            "error": None,
        }

    thread = threading.Thread(target=_run_training_job, args=(job_id, script_path), daemon=True)
    thread.start()

    return {
        "status": "started",
        "job_id": job_id,
        "message": "Model training started in the background. Poll /users/train-status/{job_id} for updates.",
    }


@router.get("/train-status/{job_id}")
async def training_status(
    job_id: str,
    _: dict = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """Poll training job status (admin only)."""
    with _training_lock:
        job = _training_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    return job


@router.get("/train-history")
async def training_history(
    _: dict = Depends(get_current_admin_user),
) -> list:
    """Return all training jobs (most recent first)."""
    with _training_lock:
        jobs = list(_training_jobs.values())
    return sorted(jobs, key=lambda j: j.get("started_at") or "", reverse=True)[:20]
