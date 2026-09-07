"""
Incident auto-create and auto-resolve logic.

Rules:
- Create incident: 3 consecutive failures on the same monitor.
- Resolve incident: 2 consecutive successes after an ongoing incident.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from models.incident import Incident
from models.check import Check


FAILURE_THRESHOLD = 3    # consecutive failures before incident
RECOVERY_THRESHOLD = 2   # consecutive successes before resolving


def get_ongoing_incident(db: Session, monitor_id: int) -> Optional[Incident]:
    return (
        db.query(Incident)
        .filter(
            Incident.monitor_id == monitor_id,
            Incident.status == "ongoing",
        )
        .order_by(Incident.started_at.desc())
        .first()
    )


def _recent_consecutive_results(db: Session, monitor_id: int, n: int) -> list[bool]:
    """Return the `success` values of the last n checks (most recent first)."""
    rows = (
        db.query(Check.success)
        .filter(Check.monitor_id == monitor_id)
        .order_by(Check.checked_at.desc())
        .limit(n)
        .all()
    )
    return [r.success for r in rows]


def evaluate_incident(db: Session, monitor_id: int, latest_check: Check) -> None:
    """
    Called after every check result is saved.
    Decides whether to open or close an incident.
    """
    ongoing = get_ongoing_incident(db, monitor_id)

    if not latest_check.success:
        # Already has an incident — nothing to do
        if ongoing:
            return

        # Check if we've hit the failure threshold
        recent = _recent_consecutive_results(db, monitor_id, FAILURE_THRESHOLD)
        if len(recent) >= FAILURE_THRESHOLD and all(not s for s in recent):
            reason = latest_check.error_message or (
                f"HTTP {latest_check.status_code}" if latest_check.status_code else "Check failed"
            )
            incident = Incident(
                monitor_id=monitor_id,
                started_at=datetime.utcnow(),
                reason=reason,
                status="ongoing",
            )
            db.add(incident)
            db.commit()
    else:
        # Service is back — can we resolve?
        if not ongoing:
            return

        recent = _recent_consecutive_results(db, monitor_id, RECOVERY_THRESHOLD)
        if len(recent) >= RECOVERY_THRESHOLD and all(s for s in recent):
            ongoing.status = "resolved"
            ongoing.resolved_at = datetime.utcnow()
            db.commit()
