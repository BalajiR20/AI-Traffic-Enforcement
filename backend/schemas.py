"""
Pydantic schemas for request validation and response serialization.
"""
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ViolationCreate(BaseModel):
    case_id: str
    vehicle_number: str = "UNREADABLE"
    violation_type: str
    timestamp: str
    location: str
    camera_id: str
    confidence: float = 0.0
    evidence_image_path: str
    evidence_hash: str
    status: str = "pending"
    blacklist_alert: bool = False


class ViolationOut(ViolationCreate):
    model_config = ConfigDict(from_attributes=True)

    rejection_reason: Optional[str] = None


class ReviewDecision(BaseModel):
    status: str                      # "approved" or "rejected"
    rejection_reason: Optional[str] = None


class BlacklistCreate(BaseModel):
    plate_number: str
    reason: Optional[str] = None
