"""
Monitor CRUD endpoints + manual trigger (in-memory store version).
"""
import asyncio
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status

import store
from schemas.monitor import MonitorCreate, MonitorUpdate, MonitorResponse
from services.checker import validate_url
from services.monitor_service import execute_check
import scheduler as sched

router = APIRouter(prefix="/api/monitors", tags=["monitors"])


def _to_response(m: dict) -> dict:
    """Return a dict that satisfies MonitorResponse."""
    return m


@router.get("", response_model=List[MonitorResponse])
async def list_monitors():
    return store.list_monitors_sorted()


@router.post("", response_model=MonitorResponse, status_code=status.HTTP_201_CREATED)
async def create_monitor(payload: MonitorCreate):
    # Validate URL (SSRF protection)
    ssrf_error = validate_url(payload.url)
    if ssrf_error:
        raise HTTPException(status_code=400, detail=ssrf_error)

    monitor = store.make_monitor(
        name=payload.name,
        url=payload.url,
        method=payload.method,
        interval=payload.interval,
        timeout=payload.timeout,
        expected_status=payload.expected_status,
        expected_content=payload.expected_content,
    )

    # Schedule immediately
    sched.add_monitor_job(monitor["id"], monitor["interval"])

    return monitor


@router.get("/{monitor_id}", response_model=MonitorResponse)
async def get_monitor(monitor_id: int):
    monitor = store.get_monitor(monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return monitor


@router.put("/{monitor_id}", response_model=MonitorResponse)
async def update_monitor(monitor_id: int, payload: MonitorUpdate):
    monitor = store.get_monitor(monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    updates: dict = {}

    if payload.url is not None:
        ssrf_error = validate_url(payload.url)
        if ssrf_error:
            raise HTTPException(status_code=400, detail=ssrf_error)
        updates["url"] = payload.url

    if payload.name is not None:
        updates["name"] = payload.name
    if payload.method is not None:
        updates["method"] = payload.method.upper()
    if payload.timeout is not None:
        updates["timeout"] = payload.timeout
    if payload.expected_status is not None:
        updates["expected_status"] = payload.expected_status
    if payload.expected_content is not None:
        updates["expected_content"] = payload.expected_content
    if payload.is_active is not None:
        updates["is_active"] = payload.is_active

    interval_changed = (
        payload.interval is not None and payload.interval != monitor["interval"]
    )
    if payload.interval is not None:
        updates["interval"] = payload.interval

    store.update_monitor_cache(monitor_id, **updates)
    monitor = store.get_monitor(monitor_id)

    # Reschedule if interval changed
    if interval_changed:
        sched.add_monitor_job(monitor_id, monitor["interval"])

    if payload.is_active:
        sched.add_monitor_job(monitor_id, monitor["interval"])
    elif payload.is_active is False:
        sched.remove_monitor_job(monitor_id)

    return monitor


@router.delete("/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_monitor(monitor_id: int):
    if not store.get_monitor(monitor_id):
        raise HTTPException(status_code=404, detail="Monitor not found")

    sched.remove_monitor_job(monitor_id)
    store.delete_monitor(monitor_id)


@router.post("/{monitor_id}/check")
async def trigger_check(monitor_id: int):
    """Manually trigger an immediate check and wait for the result."""
    if not store.get_monitor(monitor_id):
        raise HTTPException(status_code=404, detail="Monitor not found")

    result = await execute_check(monitor_id)
    if result is None:
        raise HTTPException(status_code=500, detail="Check execution failed")

    return {"message": "Check completed", "result": result}
