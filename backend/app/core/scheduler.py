"""
Background job scheduling using APScheduler (async).

One shared AsyncIOScheduler lives for the lifetime of the app. Collectors
register periodic jobs through `register_job(...)` on startup.
"""

from __future__ import annotations

from typing import Callable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class _SchedulerState:
    scheduler: Optional[AsyncIOScheduler] = None


_state = _SchedulerState()


def start_scheduler() -> AsyncIOScheduler:
    if _state.scheduler is None:
        tz = get_settings().TIMEZONE
        _state.scheduler = AsyncIOScheduler(timezone=tz)
        _state.scheduler.start()
        logger.info("scheduler.started", timezone=tz)
    return _state.scheduler


def shutdown_scheduler() -> None:
    if _state.scheduler is not None:
        _state.scheduler.shutdown(wait=False)
        _state.scheduler = None
        logger.info("scheduler.stopped")


def register_job(
    func: Callable,
    interval_seconds: int,
    job_id: str,
    run_immediately: bool = True,
) -> None:
    """Register a coroutine to run every `interval_seconds`.
    If run_immediately is true, also schedule it to run once right away.
    """
    scheduler = start_scheduler()
    scheduler.add_job(
        func,
        trigger=IntervalTrigger(seconds=interval_seconds),
        id=job_id,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    if run_immediately:
        # Fire once at next tick (after returning control).
        scheduler.add_job(
            func,
            id=f"{job_id}__bootstrap",
            replace_existing=True,
            misfire_grace_time=60,
        )
    logger.info("scheduler.job_registered", job_id=job_id, interval=interval_seconds)


def get_scheduler() -> Optional[AsyncIOScheduler]:
    return _state.scheduler
