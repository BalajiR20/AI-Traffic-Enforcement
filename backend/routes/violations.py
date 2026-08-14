"""
Violations endpoints:
    POST   /violations              -> create a new violation record (called by pipeline)
    GET    /violations              -> list, filterable by status/type
    GET    /violations/{case_id}    -> single case detail
    POST   /violations/{case_id}/review -> approve/reject with optional reason
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.database import get_db
from backend.models import Violation
from backend.schemas import ViolationCreate, ViolationOut, ReviewDecision

router = APIRouter(prefix="/violations", tags=["violations"])


@router.post("", response_model=ViolationOut)
def create_violation(payload: ViolationCreate, db: Session = Depends(get_db)):
    existing = db.query(Violation).filter(Violation.case_id == payload.case_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="case_id already exists")

    record = Violation(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=list[ViolationOut])
def list_violations(
    status: Optional[str] = None,
    violation_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Violation)
    if status:
        query = query.filter(Violation.status == status)
    if violation_type:
        query = query.filter(Violation.violation_type == violation_type)
    return query.order_by(desc(Violation.created_at)).all()


@router.get("/{case_id}", response_model=ViolationOut)
def get_violation(case_id: str, db: Session = Depends(get_db)):
    record = db.query(Violation).filter(Violation.case_id == case_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="case not found")
    return record


@router.post("/{case_id}/review", response_model=ViolationOut)
def review_violation(case_id: str, decision: ReviewDecision, db: Session = Depends(get_db)):
    record = db.query(Violation).filter(Violation.case_id == case_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="case not found")
    if decision.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="status must be 'approved' or 'rejected'")

    record.status = decision.status
    record.rejection_reason = decision.rejection_reason if decision.status == "rejected" else None
    db.commit()
    db.refresh(record)
    return record
