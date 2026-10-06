"""
Check history endpoints (MongoDB version).
"""
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, HTTPException, Query

import store
from schemas.check import CheckResponse
from services.monitor_service import compute_uptime, compute_uptime_segments

router = APIRouter(prefix="/api/monitors", tags=["checks"])


@router.get("/{monitor_id}/checks", response_model=List[CheckResponse])
async def list_checks(
    monitor_id: int,
    limit: int = Query(default=50, ge=1, le=500),
):
    if not await store.get_monitor(monitor_id):
        raise HTTPException(status_code=404, detail="Monitor not found")

    return await store.get_checks_for(monitor_id, limit=limit)


@router.get("/{monitor_id}/uptime")
async def get_uptime(monitor_id: int):
    if not await store.get_monitor(monitor_id):
        raise HTTPException(status_code=404, detail="Monitor not found")

    return {
        "uptime_24h": await compute_uptime(monitor_id, hours=24),
        "uptime_7d": await compute_uptime(monitor_id, hours=168),
        "uptime_30d": await compute_uptime(monitor_id, hours=720),
    }


@router.get("/{monitor_id}/uptime/segments")
async def get_uptime_segments(
    monitor_id: int,
    hours: int = Query(default=24, ge=1, le=720),
):
    if not await store.get_monitor(monitor_id):
        raise HTTPException(status_code=404, detail="Monitor not found")

    return await compute_uptime_segments(monitor_id, hours=hours)


@router.get("/{monitor_id}/chart")
async def get_chart_data(
    monitor_id: int,
    hours: int = Query(default=24, ge=1, le=720),
):
    """Returns response-time data points for charting."""
    if not await store.get_monitor(monitor_id):
        raise HTTPException(status_code=404, detail="Monitor not found")

    since = datetime.utcnow() - timedelta(hours=hours)
    rows = await store.get_checks_since(monitor_id, since)
    return [
        {
            "time": c["checked_at"].isoformat(),
            "responseTime": c["response_time"],
            "success": c["success"],
            "statusCode": c["status_code"],
        }
        for c in rows
    ]
