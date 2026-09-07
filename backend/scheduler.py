"""
Pure-asyncio background monitoring scheduler (in-memory store version).

No APScheduler, no Redis, no Celery.
Uses asyncio tasks with per-monitor sleep loops.

Design:
  - One asyncio Task per active monitor, each sleeping for `monitor.interval` between checks.
  - A supervisor task re-syncs jobs every 60 s to pick up new/deleted/updated monitors.
  - All exceptions are caught inside each task so one failing monitor can't crash others.
"""
import asyncio
import logging
from typing import Dict, Optional

import store
from services.monitor_service import execute_check

logger = logging.getLogger(__name__)

# map: monitor_id -> asyncio.Task
_tasks: Dict[int, asyncio.Task] = {}
_supervisor_task: Optional[asyncio.Task] = None


# ---------------------------------------------------------------------------
# Per-monitor worker
# ---------------------------------------------------------------------------

async def _monitor_worker(monitor_id: int, interval: int) -> None:
    """Run checks for a single monitor at its configured interval."""
    logger.info("Worker started for monitor %d (every %ds)", monitor_id, interval)
    # Run the first check immediately (don't wait a full interval)
    try:
        await execute_check(monitor_id)
    except Exception as exc:
        logger.error("Initial check for monitor %d failed: %s", monitor_id, exc)

    while True:
        try:
            await asyncio.sleep(interval)
            await execute_check(monitor_id)
        except asyncio.CancelledError:
            logger.info("Worker cancelled for monitor %d", monitor_id)
            break
        except Exception as exc:
            logger.error("Worker error for monitor %d: %s", monitor_id, exc, exc_info=True)
            # Brief back-off before retrying
            await asyncio.sleep(5)


# ---------------------------------------------------------------------------
# Sync / supervisor
# ---------------------------------------------------------------------------

def _sync_jobs() -> None:
    """
    Synchronise running tasks with current in-memory store state.
    Called at startup and every 60 s.
    """
    active_monitors = {m["id"]: m for m in store.list_monitors_sorted() if m["is_active"]}

    # Cancel tasks for deleted/deactivated monitors
    for mid, task in list(_tasks.items()):
        if mid not in active_monitors:
            task.cancel()
            del _tasks[mid]
            logger.info("Stopped worker for monitor %d", mid)

    # Start tasks for new monitors
    for mid, monitor in active_monitors.items():
        if mid not in _tasks or _tasks[mid].done():
            task = asyncio.ensure_future(
                _monitor_worker(mid, monitor["interval"])
            )
            _tasks[mid] = task


async def _supervisor() -> None:
    """Background supervisor that re-syncs jobs every 60 s."""
    while True:
        try:
            await asyncio.sleep(60)
            _sync_jobs()
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("Supervisor error: %s", exc, exc_info=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start_scheduler() -> None:
    """
    Start the scheduler.
    Must be called from within a running asyncio event loop (FastAPI lifespan).
    """
    global _supervisor_task
    _sync_jobs()
    _supervisor_task = asyncio.ensure_future(_supervisor())
    logger.info("Scheduler started with %d monitor(s)", len(_tasks))


def stop_scheduler() -> None:
    """Cancel all running tasks."""
    global _supervisor_task
    if _supervisor_task:
        _supervisor_task.cancel()
        _supervisor_task = None

    for mid, task in list(_tasks.items()):
        task.cancel()
    _tasks.clear()
    logger.info("Scheduler stopped")


def add_monitor_job(monitor_id: int, interval: int) -> None:
    """Schedule a new monitor immediately (called right after creation via API)."""
    # Cancel existing if running
    remove_monitor_job(monitor_id)
    task = asyncio.ensure_future(_monitor_worker(monitor_id, interval))
    _tasks[monitor_id] = task
    logger.info("Scheduled new monitor %d", monitor_id)


def remove_monitor_job(monitor_id: int) -> None:
    """Cancel and remove a monitor's worker task."""
    task = _tasks.pop(monitor_id, None)
    if task and not task.done():
        task.cancel()
