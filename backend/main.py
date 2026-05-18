"""
FastAPI entrypoint for the Terrorism Detection & Monitoring System.

Startup flow:
  1. setup_logging()
  2. connect_to_mongo()
  3. ensure_default_sources()        – seed RSS feeds if empty
  4. start the APScheduler job that polls every source on COLLECTOR_INTERVAL_SECONDS

Shutdown flow:
  * stop the scheduler
  * close the Mongo client
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure CWD is the backend folder regardless of how the server was launched.
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from app.api import api_router
from app.core.config import get_settings
from app.core.database import close_mongo_connection, connect_to_mongo
from app.core.logging import get_logger, setup_logging
from app.core.scheduler import (
    register_job,
    shutdown_scheduler,
    start_scheduler,
)
from app.services.collector_manager import (
    ensure_default_sources,
    run_all_sources,
)
from app.services.user_bootstrap import ensure_seed_admin_user

setup_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- startup
    logger.info("app.starting", environment=settings.ENVIRONMENT)
    await connect_to_mongo()
    await ensure_seed_admin_user()
    await ensure_default_sources()
    
    # Pre-load ML model in background thread so it's ready before first request
    import asyncio
    from app.services.ml_service import get_pipeline
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, get_pipeline)
    
    start_scheduler()
    register_job(
        run_all_sources,
        interval_seconds=settings.COLLECTOR_INTERVAL_SECONDS,
        job_id="collector.run_all_sources",
        run_immediately=True,
    )
    logger.info("app.started")

    yield

    # ---- shutdown
    logger.info("app.shutting_down")
    shutdown_scheduler()
    await close_mongo_connection()
    logger.info("app.stopped")


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="Real-time web data mining for online terrorism detection & monitoring.",
        version="2.0.0",
        docs_url="/api/docs" if settings.ENVIRONMENT == "development" else None,
        redoc_url="/api/redoc" if settings.ENVIRONMENT == "development" else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    return app


app = create_application()


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "healthy", "service": "tdm-backend", "version": app.version}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=(settings.ENVIRONMENT == "development"),
        log_level="info",
    )
