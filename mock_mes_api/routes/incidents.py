"""Incidents/Failures endpoints (MES)"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from mock_sap_api.models import Incident

router = APIRouter(tags=["Incidents"])


@router.get("/incidents")
def list_incidents(
    active_only: bool = Query(False, description="Only unresolved incidents"),
    severity: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Incident)
    if active_only:
        q = q.filter(Incident.status.in_(["open", "acknowledged", "inProgress"]))
    if severity:
        q = q.filter(Incident.severity == severity)
    results = q.all()
    return {"count": len(results), "incidents": [_inc_to_dict(i) for i in results]}


@router.get("/incidents/{identifier}")
def get_incident(identifier: str, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.identifier == identifier).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return _inc_to_dict(inc)


def _inc_to_dict(i: Incident) -> dict:
    return {
        "identifier": i.identifier,
        "resource_identifier": i.resource_ref.identifier,
        "resource_name": i.resource_ref.name,
        "incident_type": i.incident_type,
        "severity": i.severity,
        "status": i.status,
        "start_time": i.start_time.isoformat() if i.start_time else None,
        "end_time": i.end_time.isoformat() if i.end_time else None,
        "description": i.description,
        "resolution_notes": i.resolution_notes,
    }