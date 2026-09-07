"""
High-level monitor operations:

- execute_check(monitor_id): run a check, persist results, update monitor cache, evaluate incidents
- compute_uptime(monitor_id, hours): percentage uptime over last N hours
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from database import SessionLocal
from models.monitor import Monitor
from models.check import Check
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
    Opens its own DB session so it can be called from any context.
    Returns the result dict or None if monitor not found.
    """
    db: Session = SessionLocal()
    try:
        monitor: Optional[Monitor] = db.query(Monitor).filter(Monitor.id == monitor_id).first()
        if not monitor or not monitor.is_active:
            return None

        result = await run_check(
            url=monitor.url,
            method=monitor.method,
            timeout=monitor.timeout,
            expected_status=monitor.expected_status,
            expected_content=monitor.expected_content,
        )

        now = datetime.utcnow()

        # Persist check record
        check = Check(
            monitor_id=monitor_id,
            status_code=result["status_code"],
            response_time=result["response_time"],
            success=result["success"],
            error_message=result["error_message"],
            content_check_passed=result["content_check_passed"],
            checked_at=now,
        )
        db.add(check)
        db.flush()   # assign check.id before evaluating incident

        # Update monitor cache
        monitor.last_status = _determine_status(result["success"], result["content_check_passed"])
        monitor.last_response_time = result["response_time"]
        monitor.last_checked_at = now
        monitor.last_status_code = result["status_code"]
        monitor.last_error = result["error_message"]
        monitor.updated_at = now

        db.commit()
        db.refresh(check)

        # Evaluate incident after commit
        evaluate_incident(db, monitor_id, check)

        return result

    except Exception as exc:
        logger.error("execute_check(%d) failed: %s", monitor_id, exc, exc_info=True)
        db.rollback()
        return None
    finally:
        db.close()


def compute_uptime(db: Session, monitor_id: int, hours: int = 24) -> Optional[float]:
    """Return uptime % over the last `hours` hours, or None if no checks exist."""
    since = datetime.utcnow() - timedelta(hours=hours)
    rows = (
        db.query(Check.success)
        .filter(Check.monitor_id == monitor_id, Check.checked_at >= since)
        .all()
    )
    if not rows:
        return None
    successes = sum(1 for r in rows if r.success)
    return round(successes / len(rows) * 100, 4)


def compute_uptime_segments(db: Session, monitor_id: int, hours: int = 24) -> list[dict]:
    """
    Return list of check results as segments for the uptime bar visualization.
    Each item: {checked_at, success, status_code, response_time}
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    rows = (
        db.query(Check)
        .filter(Check.monitor_id == monitor_id, Check.checked_at >= since)
        .order_by(Check.checked_at.asc())
        .all()
    )
    return [
        {
            "checked_at": r.checked_at.isoformat(),
            "success": r.success,
            "status_code": r.status_code,
            "response_time": r.response_time,
        }
        for r in rows
    ]
