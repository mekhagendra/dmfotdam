"""API endpoint routers — imported by main.py and mounted under /api/v1."""

from app.api.endpoints import auth, detection, monitoring, reddit, upload

__all__ = ["auth", "detection", "monitoring", "reddit", "upload"]
