from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CheckResponse(BaseModel):
    id: int
    monitor_id: int
    status_code: Optional[int]
    response_time: Optional[float]
    success: bool
    error_message: Optional[str]
    content_check_passed: Optional[bool]
    checked_at: datetime

    model_config = {"from_attributes": True}


class IncidentResponse(BaseModel):
    id: int
    monitor_id: int
    started_at: datetime
    resolved_at: Optional[datetime]
    reason: str
    status: str
    monitor_name: Optional[str] = None
    monitor_url: Optional[str] = None

    model_config = {"from_attributes": True}


class AnalyticsResponse(BaseModel):
    avg_response_time: Optional[float]
    p95_response_time: Optional[float]
    uptime_percent: Optional[float]
    total_checks: int
    total_failures: int
    total_incidents: int
