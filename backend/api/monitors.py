"""
Monitor CRUD endpoints + manual trigger.
"""
import asyncio
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.monitor import Monitor
from schemas.monitor import MonitorCreate, MonitorUpdate, MonitorResponse
from services.checker import validate_url
from services.monitor_service import execute_check
import scheduler as sched

router = APIRouter(prefix="/api/monitors", tags=["monitors"])


@router.get("", response_model=List[MonitorResponse])
def list_monitors(db: Session = Depends(get_db)):
    return db.query(Monitor).order_by(Monitor.created_at.desc()).all()


@router.post("", response_model=MonitorResponse, status_code=status.HTTP_201_CREATED)
def create_monitor(payload: MonitorCreate, db: Session = Depends(get_db)):
    # Validate URL (SSRF protection)
    ssrf_error = validate_url(payload.url)
    if ssrf_error:
        raise HTTPException(status_code=400, detail=ssrf_error)

    monitor = Monitor(
        name=payload.name,
        url=payload.url,
        method=payload.method,
        interval=payload.interval,
        timeout=payload.timeout,
        expected_status=payload.expected_status,
        expected_content=payload.expected_content,
        last_status="checking",
    )
    db.add(monitor)
    db.commit()
    db.refresh(monitor)

    # Schedule immediately
    sched.add_monitor_job(monitor.id, monitor.interval)

    return monitor


@router.get("/{monitor_id}", response_model=MonitorResponse)
def get_monitor(monitor_id: int, db: Session = Depends(get_db)):
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return monitor


@router.put("/{monitor_id}", response_model=MonitorResponse)
def update_monitor(monitor_id: int, payload: MonitorUpdate, db: Session = Depends(get_db)):
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    if payload.url is not None:
        ssrf_error = validate_url(payload.url)
        if ssrf_error:
            raise HTTPException(status_code=400, detail=ssrf_error)
        monitor.url = payload.url

    if payload.name is not None:
        monitor.name = payload.name
    if payload.method is not None:
        monitor.method = payload.method.upper()
    if payload.timeout is not None:
        monitor.timeout = payload.timeout
    if payload.expected_status is not None:
        monitor.expected_status = payload.expected_status
    if payload.expected_content is not None:
        monitor.expected_content = payload.expected_content
    if payload.is_active is not None:
        monitor.is_active = payload.is_active

    interval_changed = payload.interval is not None and payload.interval != monitor.interval
    if payload.interval is not None:
        monitor.interval = payload.interval

    db.commit()
    db.refresh(monitor)

    # Reschedule if interval changed
    if interval_changed:
        sched.add_monitor_job(monitor.id, monitor.interval)

    # If re-activated, also schedule
    if payload.is_active:
        sched.add_monitor_job(monitor.id, monitor.interval)
    elif payload.is_active is False:
        sched.remove_monitor_job(monitor.id)

    return monitor


@router.delete("/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_monitor(monitor_id: int, db: Session = Depends(get_db)):
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    sched.remove_monitor_job(monitor_id)
    db.delete(monitor)
    db.commit()


@router.post("/{monitor_id}/check")
async def trigger_check(monitor_id: int, db: Session = Depends(get_db)):
    """Manually trigger an immediate check and wait for the result."""
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    result = await execute_check(monitor_id)
    if result is None:
        raise HTTPException(status_code=500, detail="Check execution failed")

    return {"message": "Check completed", "result": result}
