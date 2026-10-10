"""
Incidents endpoints (MongoDB version). Auth required.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends

import store
from auth import get_current_user

router = APIRouter(tags=["incidents"])


async def _enrich(incident: dict) -> dict:
    monitor = await store.get_monitor(incident["monitor_id"])
    return {
        "id": incident["id"],
        "monitor_id": incident["monitor_id"],
        "started_at": incident["started_at"],
        "resolved_at": incident["resolved_at"],
        "reason": incident["reason"],
        "status": incident["status"],
        "monitor_name": monitor["name"] if monitor else None,
        "monitor_url": monitor["url"] if monitor else None,
    }


@router.get("/api/incidents")
async def list_all_incidents(
    status: Optional[str] = Query(default=None, pattern="^(ongoing|resolved)$"),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    incidents = await store.list_incidents(
        status_filter=status, limit=limit, user_id=current_user["_id_str"]
    )
    return [await _enrich(i) for i in incidents]


@router.get("/api/monitors/{monitor_id}/incidents")
async def list_monitor_incidents(
    monitor_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    if not await store.get_monitor(monitor_id, user_id=current_user["_id_str"]):
        raise HTTPException(status_code=404, detail="Monitor not found")

    incidents = await store.get_incidents_for(monitor_id, limit=limit)
    return [await _enrich(i) for i in incidents]
