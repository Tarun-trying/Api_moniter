from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class Monitor(Base):
    __tablename__ = "monitors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    url = Column(String(2048), nullable=False)
    method = Column(String(16), nullable=False, default="GET")
    interval = Column(Integer, nullable=False, default=300)   # seconds
    timeout = Column(Integer, nullable=False, default=10)      # seconds
    expected_status = Column(Integer, nullable=True, default=200)
    expected_content = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Current cached status (updated after each check)
    last_status = Column(String(32), nullable=True)          # "up" | "down" | "degraded" | "checking"
    last_response_time = Column(Integer, nullable=True)       # ms
    last_checked_at = Column(DateTime, nullable=True)
    last_status_code = Column(Integer, nullable=True)
    last_error = Column(Text, nullable=True)

    # Relationships
    checks = relationship("Check", back_populates="monitor", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="monitor", cascade="all, delete-orphan")
