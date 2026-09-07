from datetime import datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl, field_validator


class MonitorCreate(BaseModel):
    name: str
    url: str
    method: str = "GET"
    interval: int = 300          # seconds
    timeout: int = 10            # seconds
    expected_status: Optional[int] = 200
    expected_content: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @field_validator("method")
    @classmethod
    def method_must_be_valid(cls, v: str) -> str:
        allowed = {"GET", "POST", "PUT", "PATCH", "HEAD", "OPTIONS"}
        v = v.upper()
        if v not in allowed:
            raise ValueError(f"Method must be one of {allowed}")
        return v

    @field_validator("interval")
    @classmethod
    def interval_in_range(cls, v: int) -> int:
        if v < 30:
            raise ValueError("Interval must be at least 30 seconds")
        if v > 86400:
            raise ValueError("Interval must be at most 86400 seconds (1 day)")
        return v

    @field_validator("timeout")
    @classmethod
    def timeout_in_range(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Timeout must be at least 1 second")
        if v > 60:
            raise ValueError("Timeout must be at most 60 seconds")
        return v


class MonitorUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    method: Optional[str] = None
    interval: Optional[int] = None
    timeout: Optional[int] = None
    expected_status: Optional[int] = None
    expected_content: Optional[str] = None
    is_active: Optional[bool] = None


class MonitorResponse(BaseModel):
    id: int
    name: str
    url: str
    method: str
    interval: int
    timeout: int
    expected_status: Optional[int]
    expected_content: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Live status
    last_status: Optional[str]
    last_response_time: Optional[float]
    last_checked_at: Optional[datetime]
    last_status_code: Optional[int]
    last_error: Optional[str]

    model_config = {"from_attributes": True}
