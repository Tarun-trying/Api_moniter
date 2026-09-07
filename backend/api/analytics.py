"""
Analytics aggregate endpoint.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models.check import Check
from models.incident import Incident
from models.monitor import Monitor

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("")
def get_analytics(
    hours: int = Query(default=24, ge=1, le=720),
    db: Session = Depends(get_db),
):
    since = datetime.utcnow() - timedelta(hours=hours)

    # Total checks & failures
    total_checks = (
        db.query(func.count(Check.id))
        .filter(Check.checked_at >= since)
        .scalar()
        or 0
    )
    total_failures = (
        db.query(func.count(Check.id))
        .filter(Check.checked_at >= since, Check.success == False)
        .scalar()
        or 0
    )

    # Uptime
    uptime_percent = None
    if total_checks > 0:
        uptime_percent = round((total_checks - total_failures) / total_checks * 100, 4)

    # Response times (successes only)
    rt_rows = (
        db.query(Check.response_time)
        .filter(
            Check.checked_at >= since,
            Check.success == True,
            Check.response_time.isnot(None),
        )
        .all()
    )
    rt_values = sorted([r.response_time for r in rt_rows])

    avg_response_time = None
    p95_response_time = None
    if rt_values:
        avg_response_time = round(sum(rt_values) / len(rt_values), 2)
        p95_idx = max(0, int(len(rt_values) * 0.95) - 1)
        p95_response_time = round(rt_values[p95_idx], 2)

    # Incidents
    total_incidents = (
        db.query(func.count(Incident.id))
        .filter(Incident.started_at >= since)
        .scalar()
        or 0
    )

    # Per-monitor uptime for bar chart
    monitors = db.query(Monitor).filter(Monitor.is_active == True).all()
    monitor_uptime = []
    for m in monitors:
        total = (
            db.query(func.count(Check.id))
            .filter(Check.monitor_id == m.id, Check.checked_at >= since)
            .scalar()
            or 0
        )
        if total == 0:
            continue
        success = (
            db.query(func.count(Check.id))
            .filter(
                Check.monitor_id == m.id,
                Check.checked_at >= since,
                Check.success == True,
            )
            .scalar()
            or 0
        )
        monitor_uptime.append({
            "id": m.id,
            "name": m.name,
            "uptime": round(success / total * 100, 2),
        })

    # Response time over time (hourly buckets)
    response_over_time = _bucket_response_time(db, since, hours)

    # Failures over time
    failure_over_time = _bucket_failures(db, since, hours)

    return {
        "avg_response_time": avg_response_time,
        "p95_response_time": p95_response_time,
        "uptime_percent": uptime_percent,
        "total_checks": total_checks,
        "total_failures": total_failures,
        "total_incidents": total_incidents,
        "monitor_uptime": monitor_uptime,
        "response_over_time": response_over_time,
        "failure_over_time": failure_over_time,
    }


def _bucket_response_time(db: Session, since: datetime, hours: int) -> list:
    """Compute average response time bucketed by hour (or 6h if range > 7d)."""
    bucket_hours = 6 if hours > 168 else 1

    rows = (
        db.query(Check.checked_at, Check.response_time)
        .filter(
            Check.checked_at >= since,
            Check.success == True,
            Check.response_time.isnot(None),
        )
        .all()
    )

    buckets: dict[str, list[float]] = {}
    for row in rows:
        # Truncate to bucket
        ts = row.checked_at
        truncated = ts.replace(
            minute=(ts.minute // (60 * bucket_hours // 1)) * (60 * bucket_hours // 1),
            second=0,
            microsecond=0,
        )
        # For multi-hour buckets, also truncate hour
        if bucket_hours > 1:
            truncated = truncated.replace(hour=(ts.hour // bucket_hours) * bucket_hours, minute=0)
        key = truncated.isoformat()
        buckets.setdefault(key, []).append(row.response_time)

    return [
        {"time": k, "avg": round(sum(v) / len(v), 2)}
        for k, v in sorted(buckets.items())
    ]


def _bucket_failures(db: Session, since: datetime, hours: int) -> list:
    """Count failures per hour bucket."""
    bucket_hours = 6 if hours > 168 else 1

    rows = (
        db.query(Check.checked_at, Check.success)
        .filter(Check.checked_at >= since, Check.success == False)
        .all()
    )

    buckets: dict[str, int] = {}
    for row in rows:
        ts = row.checked_at
        if bucket_hours > 1:
            truncated = ts.replace(hour=(ts.hour // bucket_hours) * bucket_hours, minute=0, second=0, microsecond=0)
        else:
            truncated = ts.replace(minute=0, second=0, microsecond=0)
        key = truncated.isoformat()
        buckets[key] = buckets.get(key, 0) + 1

    return [{"time": k, "failures": v} for k, v in sorted(buckets.items())]
