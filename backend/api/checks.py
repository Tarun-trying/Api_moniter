"""
Check history endpoints.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models.check import Check
from models.monitor import Monitor
from schemas.check import CheckResponse
from services.monitor_service import compute_uptime, compute_uptime_segments

router = APIRouter(prefix="/api/monitors", tags=["checks"])


@router.get("/{monitor_id}/checks", response_model=List[CheckResponse])
def list_checks(
    monitor_id: int,
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    checks = (
        db.query(Check)
        .filter(Check.monitor_id == monitor_id)
        .order_by(Check.checked_at.desc())
        .limit(limit)
        .all()
    )
    return checks


@router.get("/{monitor_id}/uptime")
def get_uptime(monitor_id: int, db: Session = Depends(get_db)):
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    return {
        "uptime_24h": compute_uptime(db, monitor_id, hours=24),
        "uptime_7d": compute_uptime(db, monitor_id, hours=168),
        "uptime_30d": compute_uptime(db, monitor_id, hours=720),
    }


@router.get("/{monitor_id}/uptime/segments")
def get_uptime_segments(
    monitor_id: int,
    hours: int = Query(default=24, ge=1, le=720),
    db: Session = Depends(get_db),
):
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    return compute_uptime_segments(db, monitor_id, hours=hours)


@router.get("/{monitor_id}/chart")
def get_chart_data(
    monitor_id: int,
    hours: int = Query(default=24, ge=1, le=720),
    db: Session = Depends(get_db),
):
    """Returns response-time data points for charting."""
    from datetime import datetime, timedelta

    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    since = datetime.utcnow() - timedelta(hours=hours)
    rows = (
        db.query(Check)
        .filter(Check.monitor_id == monitor_id, Check.checked_at >= since)
        .order_by(Check.checked_at.asc())
        .all()
    )
    return [
        {
            "time": r.checked_at.isoformat(),
            "responseTime": r.response_time,
            "success": r.success,
            "statusCode": r.status_code,
        }
        for r in rows
    ]
