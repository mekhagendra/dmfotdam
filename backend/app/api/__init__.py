"""Aggregate API router — mounted under /api/v1 in main.py."""

from fastapi import APIRouter

from app.api.endpoints import auth, detection, monitoring, reddit, upload, ws

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(upload.router)
api_router.include_router(detection.router)
api_router.include_router(monitoring.router)
api_router.include_router(reddit.router)
api_router.include_router(ws.router)
