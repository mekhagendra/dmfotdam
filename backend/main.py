"""
Main application entry point for the Terrorism Detection and Monitoring System
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
import os
import uvicorn

# Ensure working directory is the backend folder
os.chdir(os.path.dirname(os.path.abspath(__file__)))

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
    await seed_admin_user()

    # Pre-load ML models so first request isn't slow
    from app.services.ml_service import MLService
    ml = MLService()
    ml.load_models()

    yield
    # Shutdown - cleanup tasks if needed


async def seed_admin_user():
    """Ensure the default admin user exists with correct credentials."""
    from app.core.database import async_session
    from app.core.security import get_password_hash
    from app.models.user import User
    from sqlalchemy import select

    async with async_session() as session:
        result = await session.execute(select(User).where(User.username == "admin"))
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                username="admin",
                email="admin@tdm.com",
                hashed_password=get_password_hash("Admin@123"),
                full_name="System Administrator",
                role="admin",
                is_active=True,
            )
            session.add(user)
        else:
            # Update existing admin user to match expected credentials
            user.email = "admin@tdm.com"
            user.hashed_password = get_password_hash("Admin@123")
            user.role = "admin"
            user.is_active = True

        await session.commit()


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