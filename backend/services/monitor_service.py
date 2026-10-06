"""
High-level monitor operations (MongoDB version).

- execute_check(monitor_id): run a check, persist results to store, evaluate incidents
- compute_uptime(monitor_id, hours): percentage uptime over last N hours
- compute_uptime_segments(monitor_id, hours): segment list for uptime bar
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

import store
from services.checker import run_check
from services.incident_service import evaluate_incident

logger = logging.getLogger(__name__)


def _determine_status(success: bool, content_check_passed: Optional[bool]) -> str:
    if not success:
        if content_check_passed is False:
            return "degraded"
        return "down"
    if content_check_passed is False:
        return "degraded"
    return "up"


async def execute_check(monitor_id: int) -> Optional[dict]:
    """
    Run a single check for the given monitor id.
    Returns the result dict or None if monitor not found / inactive.
    """
    monitor = await store.get_monitor(monitor_id)
    if not monitor or not monitor["is_active"]:
        return None

    try:
        result = await run_check(
            url=monitor["url"],
            method=monitor["method"],
            timeout=monitor["timeout"],
            expected_status=monitor["expected_status"],
            expected_content=monitor["expected_content"],
        )

        now = datetime.utcnow()

        # Persist check record
        check = await store.add_check(
            monitor_id=monitor_id,
            status_code=result["status_code"],
            response_time=result["response_time"],
            success=result["success"],
            error_message=result["error_message"],
            content_check_passed=result["content_check_passed"],
            checked_at=now,
        )

        # Update monitor cached status
        await store.update_monitor_cache(
            monitor_id,
            last_status=_determine_status(result["success"], result["content_check_passed"]),
            last_response_time=result["response_time"],
            last_checked_at=now,
            last_status_code=result["status_code"],
            last_error=result["error_message"],
        )

        # Evaluate incident
        await evaluate_incident(monitor_id, check)

        return result

    except Exception as exc:
        logger.error("execute_check(%d) failed: %s", monitor_id, exc, exc_info=True)
        return None


async def compute_uptime(monitor_id: int, hours: int = 24) -> Optional[float]:
    """Return uptime % over the last `hours` hours, or None if no checks exist."""
    since = datetime.utcnow() - timedelta(hours=hours)
    rows = await store.get_checks_since(monitor_id, since)
    if not rows:
        return None
    successes = sum(1 for c in rows if c["success"])
    return round(successes / len(rows) * 100, 4)


async def compute_uptime_segments(monitor_id: int, hours: int = 24) -> list[dict]:
    """
    Return list of check results as segments for the uptime bar visualization.
    Each item: {checked_at, success, status_code, response_time}
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    rows = await store.get_checks_since(monitor_id, since)
    return [
        {
            "checked_at": c["checked_at"].isoformat(),
            "success": c["success"],
            "status_code": c["status_code"],
            "response_time": c["response_time"],
        }
        for c in rows
    ]
