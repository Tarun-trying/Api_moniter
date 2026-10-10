"""
Analytics aggregate endpoint (MongoDB version). Auth required.
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Query, Depends

import store
from auth import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("")
async def get_analytics(
    hours: int = Query(default=24, ge=1, le=720),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["_id_str"]
    since = datetime.utcnow() - timedelta(hours=hours)

    all_checks = await store.get_all_checks_since(since, user_id=user_id)

    total_checks = len(all_checks)
    total_failures = sum(1 for c in all_checks if not c["success"])

    # Overall uptime
    uptime_percent = None
    if total_checks > 0:
        uptime_percent = round((total_checks - total_failures) / total_checks * 100, 4)

    # Response times (successes only)
    rt_values = sorted(
        c["response_time"]
        for c in all_checks
        if c["success"] and c["response_time"] is not None
    )

    avg_response_time = None
    p95_response_time = None
    if rt_values:
        avg_response_time = round(sum(rt_values) / len(rt_values), 2)
        p95_idx = max(0, int(len(rt_values) * 0.95) - 1)
        p95_response_time = round(rt_values[p95_idx], 2)

    # Incidents
    all_incidents = await store.get_all_incidents_since(since, user_id=user_id)
    total_incidents = len(all_incidents)

    # Per-monitor uptime for bar chart
    monitor_uptime = []
    for m in await store.list_monitors_sorted(user_id=user_id):
        if not m["is_active"]:
            continue
        mon_checks = [c for c in all_checks if c["monitor_id"] == m["id"]]
        if not mon_checks:
            continue
        success_count = sum(1 for c in mon_checks if c["success"])
        monitor_uptime.append({
            "id": m["id"],
            "name": m["name"],
            "uptime": round(success_count / len(mon_checks) * 100, 2),
        })

    # Response time over time (hourly buckets)
    response_over_time = _bucket_response_time(all_checks, hours)

    # Failures over time
    failure_over_time = _bucket_failures(all_checks, hours)

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


def _bucket_response_time(all_checks: list, hours: int) -> list:
    """Compute average response time bucketed by hour (or 6h if range > 7d)."""
    bucket_hours = 6 if hours > 168 else 1

    buckets: dict[str, list[float]] = {}
    for c in all_checks:
        if not c["success"] or c["response_time"] is None:
            continue
        ts = c["checked_at"]
        if bucket_hours > 1:
            truncated = ts.replace(
                hour=(ts.hour // bucket_hours) * bucket_hours,
                minute=0, second=0, microsecond=0,
            )
        else:
            truncated = ts.replace(minute=0, second=0, microsecond=0)
        key = truncated.isoformat()
        buckets.setdefault(key, []).append(c["response_time"])

    return [
        {"time": k, "avg": round(sum(v) / len(v), 2)}
        for k, v in sorted(buckets.items())
    ]


def _bucket_failures(all_checks: list, hours: int) -> list:
    """Count failures per hour bucket."""
    bucket_hours = 6 if hours > 168 else 1

    buckets: dict[str, int] = {}
    for c in all_checks:
        if c["success"]:
            continue
        ts = c["checked_at"]
        if bucket_hours > 1:
            truncated = ts.replace(
                hour=(ts.hour // bucket_hours) * bucket_hours,
                minute=0, second=0, microsecond=0,
            )
        else:
            truncated = ts.replace(minute=0, second=0, microsecond=0)
        key = truncated.isoformat()
        buckets[key] = buckets.get(key, 0) + 1

    return [{"time": k, "failures": v} for k, v in sorted(buckets.items())]
