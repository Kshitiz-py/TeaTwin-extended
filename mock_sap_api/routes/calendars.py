"""Calendars, Shifts, Breaks, Holidays endpoints"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Calendar

router = APIRouter(tags=["Calendars"])


@router.get("/calendars")
def list_calendars(db: Session = Depends(get_db)):
    results = db.query(Calendar).all()
    return {"count": len(results), "calendars": [_cal_to_dict(c) for c in results]}


@router.get("/calendars/{identifier}")
def get_calendar(identifier: str, db: Session = Depends(get_db)):
    cal = db.query(Calendar).filter(Calendar.identifier == identifier).first()
    if not cal:
        raise HTTPException(status_code=404, detail="Calendar not found")
    data = _cal_to_dict(cal)
    data["shifts"] = [
        {
            "identifier": s.identifier,
            "day_of_week": s.day_of_week,
            "start_time": str(s.start_time),
            "end_time": str(s.end_time),
            "breaks": [
                {"identifier": b.identifier, "name": b.name, "start_time": str(b.start_time), "end_time": str(b.end_time)}
                for b in s.breaks
            ],
        }
        for s in cal.shifts
    ]
    data["holidays"] = [{"identifier": h.identifier, "name": h.name, "date": str(h.holiday_date)} for h in cal.holidays]
    data["shutdown_periods"] = [
        {"start_date": str(sp.start_date), "end_date": str(sp.end_date), "description": sp.description}
        for sp in cal.shutdown_periods
    ]
    return data


def _cal_to_dict(c: Calendar) -> dict:
    return {
        "identifier": c.identifier,
        "name": c.name,
        "description": c.description,
        "production_days_per_year": c.production_days_per_year,
    }