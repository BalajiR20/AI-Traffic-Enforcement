"""
Blacklist endpoints:
    GET  /blacklist            -> list flagged plates
    POST /blacklist            -> add a flagged plate
    GET  /blacklist/check/{plate} -> quick lookup used by dashboard/manual checks
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import BlacklistEntry
from backend.schemas import BlacklistCreate

router = APIRouter(prefix="/blacklist", tags=["blacklist"])


@router.get("")
def list_blacklist(db: Session = Depends(get_db)):
    return db.query(BlacklistEntry).all()


@router.post("")
def add_blacklist(payload: BlacklistCreate, db: Session = Depends(get_db)):
    plate = payload.plate_number.upper()
    existing = db.query(BlacklistEntry).filter(BlacklistEntry.plate_number == plate).first()
    if existing:
        raise HTTPException(status_code=409, detail="plate already blacklisted")
    entry = BlacklistEntry(plate_number=plate, reason=payload.reason)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/check/{plate}")
def check_blacklist(plate: str, db: Session = Depends(get_db)):
    entry = db.query(BlacklistEntry).filter(BlacklistEntry.plate_number == plate.upper()).first()
    return {"plate_number": plate.upper(), "flagged": entry is not None,
            "reason": entry.reason if entry else None}
