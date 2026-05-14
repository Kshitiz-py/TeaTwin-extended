"""Process Plans and Processes endpoints"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ProcessPlan, Process

router = APIRouter(tags=["Process Plans"])


@router.get("/process-plans")
def list_process_plans(db: Session = Depends(get_db)):
    results = db.query(ProcessPlan).all()
    return {"count": len(results), "process_plans": [_pp_to_dict(pp) for pp in results]}


@router.get("/process-plans/{identifier}")
def get_process_plan(identifier: str, db: Session = Depends(get_db)):
    pp = db.query(ProcessPlan).filter(ProcessPlan.identifier == identifier).first()
    if not pp:
        raise HTTPException(status_code=404, detail="Process plan not found")
    data = _pp_to_dict(pp)
    data["processes"] = [_process_to_dict(p) for p in sorted(pp.processes, key=lambda x: x.sequence_order)]
    return data


@router.get("/processes/{identifier}")
def get_process(identifier: str, db: Session = Depends(get_db)):
    p = db.query(Process).filter(Process.identifier == identifier).first()
    if not p:
        raise HTTPException(status_code=404, detail="Process not found")
    data = _process_to_dict(p)
    data["resources"] = [
        {
            "identifier": pr.resource_ref.identifier,
            "name": pr.resource_ref.name,
            "minimum_number": pr.minimum_number,
            "maximum_number": pr.maximum_number,
        }
        for pr in p.process_resources
    ]
    return data


def _pp_to_dict(pp: ProcessPlan) -> dict:
    return {
        "identifier": pp.identifier,
        "name": pp.name,
        "description": pp.description,
        "part_type_identifier": pp.part_type_ref.identifier if pp.part_type_ref else None,
    }


def _process_to_dict(p: Process) -> dict:
    return {
        "identifier": p.identifier,
        "name": p.name,
        "description": p.description,
        "sequence_order": p.sequence_order,
        "duration_seconds": p.duration_seconds,
        "setup_time_seconds": p.setup_time_seconds,
        "load_time_seconds": p.load_time_seconds,
        "unload_time_seconds": p.unload_time_seconds,
        "pick_time_seconds": p.pick_time_seconds,
        "place_time_seconds": p.place_time_seconds,
        "group_type": p.group_type,
        "process_plan_identifier": p.process_plan_ref.identifier if p.process_plan_ref else None,
    }