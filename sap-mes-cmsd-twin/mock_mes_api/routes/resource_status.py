"""Live Resource Status endpoints (MES)"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from ..database import get_db
from mock_sap_api.models import ResourceStatus

router = APIRouter(tags=["Resource Status"])


@router.get("/resource-status")
def list_resource_status(
    status: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(ResourceStatus)
    if status:
        q = q.filter(ResourceStatus.status == status)
    results = q.all()
    return {"count": len(results), "resource_statuses": [_rs_to_dict(rs) for rs in results]}


@router.get("/resource-status/{resource_identifier}")
def get_resource_status(resource_identifier: str, db: Session = Depends(get_db)):
    rs = (
        db.query(ResourceStatus)
        .join(ResourceStatus.resource_ref)
        .filter(ResourceStatus.resource_ref.has(identifier=resource_identifier))
        .first()
    )
    if not rs:
        raise HTTPException(status_code=404, detail="Resource status not found")
    return _rs_to_dict(rs)


def _rs_to_dict(rs: ResourceStatus) -> dict:
    return {
        "resource_identifier": rs.resource_ref.identifier,
        "resource_name": rs.resource_ref.name,
        "resource_type": rs.resource_ref.resource_type,
        "status": rs.status,
        "current_setup": rs.current_setup,
        "current_job_id": rs.current_job_id,
        "uptime_seconds": rs.uptime_seconds,
        "parts_processed_today": rs.parts_processed_today,
        "last_status_change": rs.last_status_change.isoformat() if rs.last_status_change else None,
    }