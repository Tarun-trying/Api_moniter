"""
Incidents endpoints.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models.incident import Incident
from models.monitor import Monitor
from schemas.check import IncidentResponse

router = APIRouter(tags=["incidents"])


def _enrich(incident: Incident) -> dict:
    return {
        "id": incident.id,
        "monitor_id": incident.monitor_id,
        "started_at": incident.started_at,
        "resolved_at": incident.resolved_at,
        "reason": incident.reason,
        "status": incident.status,
        "monitor_name": incident.monitor.name if incident.monitor else None,
        "monitor_url": incident.monitor.url if incident.monitor else None,
    }


@router.get("/api/incidents")
def list_all_incidents(
    status: Optional[str] = Query(default=None, pattern="^(ongoing|resolved)$"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Incident)
    if status:
        q = q.filter(Incident.status == status)
    incidents = q.order_by(Incident.started_at.desc()).limit(limit).all()
    return [_enrich(i) for i in incidents]


@router.get("/api/monitors/{monitor_id}/incidents")
def list_monitor_incidents(
    monitor_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    incidents = (
        db.query(Incident)
        .filter(Incident.monitor_id == monitor_id)
        .order_by(Incident.started_at.desc())
        .limit(limit)
        .all()
    )
    return [_enrich(i) for i in incidents]
