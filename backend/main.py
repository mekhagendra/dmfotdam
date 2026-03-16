"""
Main application entry point for the Terrorism Detection and Monitoring System
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
import uvicorn

from app.core.config import get_settings
from app.core.database import create_db_and_tables
from app.api import api_router
from app.core.logging import setup_logging

# Setup logging
setup_logging()

# Security
security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    await create_db_and_tables()
    yield
    # Shutdown - cleanup tasks if needed


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""
    settings = get_settings()
    
    app = FastAPI(
        title="Terrorism Detection & Monitoring System",
        description="Web data mining application for terrorism detection and monitoring",
        version="1.0.0",
        docs_url="/api/docs" if settings.ENVIRONMENT == "development" else None,
        redoc_url="/api/redoc" if settings.ENVIRONMENT == "development" else None,
        lifespan=lifespan
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API router
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_application()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "tdm-backend"}


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level="info"
    )