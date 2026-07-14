"""
SAP Master Data — Calendars, Shifts, Breaks, Holidays & Shutdowns.

Serves time-availability master data from SAP ERP. A Calendar aggregates the
working-time pattern for a factory or resource group: weekly Shifts, recurring
Breaks within shifts, annual Holidays, and exceptional Shutdown periods.
Together these define resource availability windows for CMSD simulation.

CMSD Entity Mapping:
  - ``Calendar``         → CMSD **Calendar** (aggregate time pattern)
  - ``Shift``            → CMSD **Shift** (recurring working periods per weekday)
  - ``Break``            → CMSD **Break** (recurring pauses within a shift)
  - ``Holiday``          → CMSD **Holiday** (annual full-day exceptions)
  - ``ShutdownPeriod``   → CMSD **Shutdown Period** (multi-day maintenance blocks)

Key Endpoints:
  | Method | Path                | Description                                      |
  |--------|---------------------|--------------------------------------------------|
  | GET    | /calendars          | List all calendar definitions                     |
  | GET    | /calendars/{id}     | Single calendar with shifts, breaks, holidays     |
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Calendar

router = APIRouter(tags=["Calendars"])


@router.get("/calendars")
def list_calendars(db: Session = Depends(get_db)):
    """List all Calendar definitions.

    Returns ``count`` and ``calendars`` array with identifier, name,
    description, and production days per year.

    CMSD relevance: Calendars define when resources are available for
    production, directly feeding CMSD Calendar → Shift time windows
    used in simulation scheduling.
    """
    results = db.query(Calendar).all()
    return {"count": len(results), "calendars": [_cal_to_dict(c) for c in results]}


@router.get("/calendars/{identifier}")
def get_calendar(identifier: str, db: Session = Depends(get_db)):
    """Get a single Calendar with all shifts, breaks, holidays, and shutdowns.

    Returns the full time-availability hierarchy:
      - Shifts: day-of-week + start/end time + nested Breaks
      - Holidays: annual date-based exceptions
      - Shutdown periods: multi-day maintenance/closure windows

    CMSD relevance: This complete time pattern directly populates the
    CMSD Calendar → Shift → Break → Holiday → ShutdownPeriod chain,
    enabling accurate resource scheduling in simulation.
    """
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
    """Serialize a Calendar ORM model to a JSON-safe dict.

    Includes the production_days_per_year summary metric used for
    annual capacity calculations in CMSD simulation.
    """
    return {
        "identifier": c.identifier,
        "name": c.name,
        "description": c.description,
        "production_days_per_year": c.production_days_per_year,
    }
