"""SAP Resources & Resource Classes endpoints"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models import Resource, ResourceClass

router = APIRouter(tags=["Resources"])


# ─── Resource Classes ───────────────────────────────────────────

@router.get("/resource-classes")
def list_resource_classes(
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    db: Session = Depends(get_db),
):
    q = db.query(ResourceClass)
    if resource_type:
        q = q.filter(ResourceClass.resource_type == resource_type)
    results = q.all()
    return {
        "count": len(results),
        "resource_classes": [_resource_class_to_dict(rc) for rc in results],
    }


@router.get("/resource-classes/{identifier}")
def get_resource_class(identifier: str, db: Session = Depends(get_db)):
    rc = db.query(ResourceClass).filter(ResourceClass.identifier == identifier).first()
    if not rc:
        raise HTTPException(status_code=404, detail="Resource class not found")
    data = _resource_class_to_dict(rc)
    data["resources"] = [
        {"identifier": r.identifier, "name": r.name, "resource_type": r.resource_type}
        for r in rc.resources
    ]
    return data


# ─── Resources ───────────────────────────────────────────────────

@router.get("/resources")
def list_resources(
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_class_id: Optional[int] = Query(None, description="Filter by resource class id"),
    db: Session = Depends(get_db),
):
    q = db.query(Resource)
    if resource_type:
        q = q.filter(Resource.resource_type == resource_type)
    if resource_class_id:
        q = q.filter(Resource.resource_class_id == resource_class_id)
    results = q.all()
    return {
        "count": len(results),
        "resources": [_resource_to_dict(r) for r in results],
    }


@router.get("/resources/{identifier}")
def get_resource(identifier: str, db: Session = Depends(get_db)):
    r = db.query(Resource).filter(Resource.identifier == identifier).first()
    if not r:
        raise HTTPException(status_code=404, detail="Resource not found")
    data = _resource_to_dict(r)

    # Include resource class info
    if r.resource_class_ref:
        data["resource_class"] = _resource_class_to_dict(r.resource_class_ref)

    # Include live status if available
    if r.resource_status:
        data["current_status"] = {
            "status": r.resource_status.status,
            "current_setup": r.resource_status.current_setup,
            "uptime_seconds": r.resource_status.uptime_seconds,
            "parts_processed_today": r.resource_status.parts_processed_today,
            "last_status_change": r.resource_status.last_status_change.isoformat() if r.resource_status.last_status_change else None,
        }

    # Include layout placement
    if r.placements:
        data["placements"] = [
            {
                "layout_id": p.layout_id,
                "x": p.x,
                "y": p.y,
                "z": p.z,
                "rotation_z_deg": p.rotation_z_deg,
            }
            for p in r.placements
        ]

    return data


# ─── Helpers ─────────────────────────────────────────────────────

def _resource_class_to_dict(rc: ResourceClass) -> dict:
    return {
        "identifier": rc.identifier,
        "name": rc.name,
        "description": rc.description,
        "resource_type": rc.resource_type,
        "hourly_rate": rc.hourly_rate,
        "size": {
            "length": rc.size_length,
            "width": rc.size_width,
            "height": rc.size_height,
        },
    }


def _resource_to_dict(r: Resource) -> dict:
    return {
        "identifier": r.identifier,
        "name": r.name,
        "description": r.description,
        "resource_type": r.resource_type,
        "resource_class_id": r.resource_class_id,
        "capacity": r.capacity,
        "availability": r.availability,
        "mttr_seconds": r.mttr_seconds,
        "mtbf_seconds": r.mtbf_seconds,
        "mcbf": r.mcbf,
        "reliability": r.reliability,
        "cycle_time_seconds": r.cycle_time_seconds,
        "desired_replenishment_time_seconds": r.desired_replenishment_time_seconds,
        "transport_capacity": r.transport_capacity,
        "tow_bar_length": r.tow_bar_length,
        "worker_count": r.worker_count,
        "decision_rule": r.decision_rule,
        "routing_rule": r.routing_rule,
        "size": {
            "length": r.size_length,
            "width": r.size_width,
            "height": r.size_height,
        },
        "hourly_rate": r.hourly_rate,
        "buffer_type": r.buffer_type,
        "buffer_capacity": r.buffer_capacity,
        "conveyor_speed": r.conveyor_speed,
        "conveyor_length": r.conveyor_length,
        "conveyor_accumulating": r.conveyor_accumulating,
        "energy": {
            "working_kw": r.energy_working_kw,
            "standby_kw": r.energy_standby_kw,
            "failed_kw": r.energy_failed_kw,
            "off_kw": r.energy_off_kw,
        },
    }