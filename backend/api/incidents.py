"""
Incidents endpoints (in-memory store version).
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

import store

router = APIRouter(tags=["incidents"])


def _enrich(incident: dict) -> dict:
    monitor = store.get_monitor(incident["monitor_id"])
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
):
    incidents = store.list_incidents(status_filter=status, limit=limit)
    return [_enrich(i) for i in incidents]


@router.get("/api/monitors/{monitor_id}/incidents")
async def list_monitor_incidents(
    monitor_id: int,
    limit: int = Query(default=20, ge=1, le=100),
):
    if not store.get_monitor(monitor_id):
        raise HTTPException(status_code=404, detail="Monitor not found")

    incidents = store.get_incidents_for(monitor_id, limit=limit)
    return [_enrich(i) for i in incidents]
