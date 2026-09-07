from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from database import Base


class Check(Base):
    __tablename__ = "checks"

    id = Column(Integer, primary_key=True, index=True)
    monitor_id = Column(Integer, ForeignKey("monitors.id"), nullable=False, index=True)
    status_code = Column(Integer, nullable=True)
    response_time = Column(Float, nullable=True)   # milliseconds
    success = Column(Boolean, nullable=False, default=False)
    error_message = Column(Text, nullable=True)
    content_check_passed = Column(Boolean, nullable=True)  # None = not configured
    checked_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    monitor = relationship("Monitor", back_populates="checks")
