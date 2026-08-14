"""
Analytics endpoints:
    GET /analytics/summary   -> total/pending/approved/rejected counts
    GET /analytics/by-type   -> violation counts grouped by type
    GET /analytics/by-location -> violation counts grouped by location (for heatmap)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database import get_db
from backend.models import Violation

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    total = db.query(Violation).count()
    pending = db.query(Violation).filter(Violation.status == "pending").count()
    approved = db.query(Violation).filter(Violation.status == "approved").count()
    rejected = db.query(Violation).filter(Violation.status == "rejected").count()
    return {"total": total, "pending": pending, "approved": approved, "rejected": rejected}


@router.get("/by-type")
def by_type(db: Session = Depends(get_db)):
    rows = (
        db.query(Violation.violation_type, func.count(Violation.case_id))
        .group_by(Violation.violation_type)
        .all()
    )
    return [{"violation_type": t, "count": c} for t, c in rows]


@router.get("/by-location")
def by_location(db: Session = Depends(get_db)):
    rows = (
        db.query(Violation.location, func.count(Violation.case_id))
        .group_by(Violation.location)
        .all()
    )
    return [{"location": loc, "count": c} for loc, c in rows]


@router.get("/rejection-reasons")
def rejection_reasons(db: Session = Depends(get_db)):
    """Feeds the 'hard examples' feedback loop — see which reasons come up most."""
    rows = (
        db.query(Violation.rejection_reason, func.count(Violation.case_id))
        .filter(Violation.status == "rejected", Violation.rejection_reason.isnot(None))
        .group_by(Violation.rejection_reason)
        .all()
    )
    return [{"reason": r, "count": c} for r, c in rows]
