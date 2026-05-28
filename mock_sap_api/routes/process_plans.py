"""
SAP Master Data — Process Plans & Processes.

Serves routing and process definitions from SAP ERP. A ProcessPlan is the
manufacturing recipe that sequences individual Process steps, each linked to
required resources and timing parameters. Together they form the routing
backbone for CMSD workflow simulation.

CMSD Entity Mapping:
  - ``ProcessPlan``       → CMSD **Process Plan** (the complete routing)
  - ``Process``           → CMSD **Process** (one sequential step)
  - ``Process.resources`` → resolves the CMSD **Resource** pool required per step

Key Endpoints:
  | Method | Path                  | Description                                       |
  |--------|-----------------------|---------------------------------------------------|
  | GET    | /process-plans        | List all process plan definitions                  |
  | GET    | /process-plans/{id}   | Single plan with sequenced Process steps           |
  | GET    | /processes/{id}       | Single process step with assigned resource pool    |
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ProcessPlan, Process

router = APIRouter(tags=["Process Plans"])


@router.get("/process-plans")
def list_process_plans(db: Session = Depends(get_db)):
    """List all ProcessPlan definitions.

    Returns ``count`` and ``process_plans`` array with identifier, name,
    description, and the PartType identifier this routing produces.

    CMSD relevance: Provides the factory's routing catalog for assigning
    work to resources in the digital twin.
    """
    results = db.query(ProcessPlan).all()
    return {"count": len(results), "process_plans": [_pp_to_dict(pp) for pp in results]}


@router.get("/process-plans/{identifier}")
def get_process_plan(identifier: str, db: Session = Depends(get_db)):
    """Get a single ProcessPlan with all Process steps in sequence order.

    Steps are sorted by ``sequence_order``, providing the ordered workflow
    that defines how a part moves through the factory.

    CMSD relevance: Directly maps to the CMSD ProcessPlan → Process list,
    enabling step-by-step simulation of production routing.
    """
    pp = db.query(ProcessPlan).filter(ProcessPlan.identifier == identifier).first()
    if not pp:
        raise HTTPException(status_code=404, detail="Process plan not found")
    data = _pp_to_dict(pp)
    data["processes"] = [_process_to_dict(p) for p in sorted(pp.processes, key=lambda x: x.sequence_order)]
    return data


@router.get("/processes/{identifier}")
def get_process(identifier: str, db: Session = Depends(get_db)):
    """Get a single Process step with its assigned Resource pool.

    Returns the process timing parameters (duration, setup, load, unload,
    pick, place) and the list of resources that can execute this step,
    including minimum/maximum resource counts.

    CMSD relevance: Each Process maps to a CMSD **Process** entity with
    linked resources, enabling resource allocation and workload simulation.
    """
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
    """Serialize a ProcessPlan ORM model to a JSON-safe dict.

    Includes the parent PartType reference that this routing applies to.
    """
    return {
        "identifier": pp.identifier,
        "name": pp.name,
        "description": pp.description,
        "part_type_identifier": pp.part_type_ref.identifier if pp.part_type_ref else None,
    }


def _process_to_dict(p: Process) -> dict:
    """Serialize a Process ORM model to a JSON-safe dict.

    Includes all timing parameters (duration, setup, load/unload, pick/place),
    group type for parallel operations, and the parent process plan reference.
    These timing values are critical inputs for CMSD duration calculations.
    """
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
