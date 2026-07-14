"""
MES Operational Data — Incidents & Downtime Events.

Serves downtime and failure incident records from the Mock MES. Incidents
capture equipment failures, quality stops, and other production disruptions
as they occur on the shop floor. Each incident tracks the affected Resource,
incident type, severity, status lifecycle (open → acknowledged →
inProgress → closed), and resolution notes.

SAP vs MES Distinction:
  - **SAP (Master Data):** Resources have static reliability attributes
    (MTBF, MTTR, MCBF) — the *expected* failure profile.
  - **MES (Operational Data):** Incidents are *actual* disruptions —
    recorded start/end times, real downtime durations, and root-cause
    descriptions that feed into CMSD Maintenance Plan entities.

  Together, SAP reliability data predicts failure likelihood while MES
  incident data provides the ground-truth event log for CMSD maintenance
  and availability simulation.

CMSD Entity Mapping:
  - ``Incident``                → CMSD **Maintenance Plan** (derived from incident history)
  - Incident → Resource         → resolves which CMSD Resource was affected
  - Incident severity + type    → categorises CMSD maintenance type (corrective, preventive)
  - active_only filter          → isolates currently-open disruptions for live dashboards

Key Endpoints:
  | Method | Path                 | Description                                          |
  |--------|----------------------|------------------------------------------------------|
  | GET    | /incidents           | List incidents (filterable by active_only, severity) |
  | GET    | /incidents/{id}      | Single incident with full detail + resolution notes  |
"""

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
    """List incident records with optional filters.

    When ``active_only=True``, returns only unresolved incidents
    (status in: open, acknowledged, inProgress). Optionally filter by
    severity level (e.g. 'critical', 'high', 'medium', 'low').

    Returns ``count`` and ``incidents`` array with resource reference,
    incident type, severity, status, start/end times, description,
    and resolution notes.

    CMSD relevance: Incident history feeds CMSD MaintenancePlan entities.
    Active incidents directly impact resource availability in simulation,
    triggering downtime logic and affecting throughput KPIs.
    """
    q = db.query(Incident)
    if active_only:
        q = q.filter(Incident.status.in_(["open", "acknowledged", "inProgress"]))
    if severity:
        q = q.filter(Incident.severity == severity)
    results = q.all()
    return {"count": len(results), "incidents": [_inc_to_dict(i) for i in results]}


@router.get("/incidents/{identifier}")
def get_incident(identifier: str, db: Session = Depends(get_db)):
    """Get a single Incident by identifier.

    Returns the full incident record: affected Resource (identifier, name),
    incident type, severity, lifecycle status, start/end timestamps,
    human-readable description, and resolution notes if the incident
    has been closed.

    CMSD relevance: Each incident maps to a CMSD maintenance event,
    contributing to resource availability calculations and MTBF/MTTR
    statistics in the digital twin.
    """
    inc = db.query(Incident).filter(Incident.identifier == identifier).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return _inc_to_dict(inc)


def _inc_to_dict(i: Incident) -> dict:
    """Serialize an Incident ORM model to a JSON-safe dict.

    Includes the affected Resource reference (identifier, name), incident
    classification (type, severity), lifecycle status, precise start/end
    timestamps for downtime calculation, and free-text description plus
    resolution notes for root-cause analysis.
    """
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
