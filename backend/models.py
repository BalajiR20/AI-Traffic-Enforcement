"""
ORM models:
    - Violation: one row per detected violation case
    - BlacklistEntry: flagged plate numbers
"""
from sqlalchemy import Column, String, Float, DateTime, Boolean
from sqlalchemy.sql import func

from backend.database import Base


class Violation(Base):
    __tablename__ = "violations"

    case_id = Column(String, primary_key=True, index=True)
    vehicle_number = Column(String, index=True, default="UNREADABLE")
    violation_type = Column(String, index=True)
    timestamp = Column(String)  # stored as ISO string from the pipeline
    location = Column(String)
    camera_id = Column(String)
    confidence = Column(Float, default=0.0)
    evidence_image_path = Column(String)
    evidence_hash = Column(String)
    status = Column(String, default="pending")       # pending | approved | rejected
    rejection_reason = Column(String, nullable=True)
    blacklist_alert = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BlacklistEntry(Base):
    __tablename__ = "blacklist"

    plate_number = Column(String, primary_key=True, index=True)
    reason = Column(String, nullable=True)
