"""
API module initialization
"""

from fastapi import APIRouter
from .endpoints import detection, monitoring, upload, auth, reddit

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(upload.router, prefix="/upload", tags=["file-upload"])
api_router.include_router(detection.router, prefix="/detection", tags=["threat-detection"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["live-monitoring"])
api_router.include_router(reddit.router, prefix="/reddit", tags=["reddit-monitoring"])