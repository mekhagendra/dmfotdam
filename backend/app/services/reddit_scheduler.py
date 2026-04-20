"""
DEPRECATED — kept only for import compatibility.

Scheduling is now handled generically by `app.core.scheduler` and
`app.services.collector_manager.run_all_sources`. See `main.py` for wiring.
"""

from app.core.scheduler import register_job, start_scheduler, shutdown_scheduler  # noqa: F401
from app.services.collector_manager import run_all_sources  # noqa: F401
