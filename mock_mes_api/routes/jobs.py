"""
MES Operational Data — Jobs & Job Efforts (Live Shop-Floor Execution).

Serves live job execution data from the Mock MES. Jobs represent the
real-time execution of production orders on the shop floor — they are the
operational counterpart to SAP Order/OrderLine master data.

SAP vs MES Distinction:
  - **SAP (Master Data):** Orders and OrderLines are *planned* — they define
    *what* to produce, *when* it is due, and *which* ProcessPlan to follow.
  - **MES (Operational Data):** Jobs are *live* — they track *actual*
    execution status, start/end timestamps, current process step, and
    real effort measurements (processing time, parts produced/scrapped).

  The digital twin consumes both layers: SAP Order data provides the demand
  signal; MES Job data provides the real-time state that drives CMSD
  production simulation.

CMSD Entity Mapping:
  - ``Job``                        → CMSD **Job** (live execution record)
  - ``JobEffort``                  → CMSD **Job Effort Description**
  - Job → OrderLine (SAP)          → links the live job back to planned demand
  - Job → ProcessPlan              → resolves the routing for simulation
  - Job → current_process_ref      → active CMSD **Process** step

Key Endpoints:
  | Method | Path                     | Description                               |
  |--------|--------------------------|-------------------------------------------|
  | GET    | /jobs                    | List jobs (filterable by status)          |
  | GET    | /jobs/{id}              | Single job with effort records            |
  | GET    | /jobs/{id}/progress     | Step-by-step progress through the routing |
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from mock_sap_api.models import Job, JobEffort

router = APIRouter(tags=["Jobs"])


@router.get("/jobs")
def list_jobs(
    status: str | None = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
):
    """List live Jobs, optionally filtered by execution status.

    Returns ``count`` and ``jobs`` array with identifier, status, priority,
    scheduling dates (release, start, end, due), and references to the parent
    OrderLine, ProcessPlan, and current Process step.

    CMSD relevance: Provides the live job queue for the digital twin.
    Job status drives real-time resource allocation and KPI calculation
    in CMSD simulation.
    """
    q = db.query(Job)
    if status:
        q = q.filter(Job.status == status)
    results = q.all()
    return {"count": len(results), "jobs": [_job_to_dict(j) for j in results]}


@router.get("/jobs/{identifier}")
def get_job(identifier: str, db: Session = Depends(get_db)):
    """Get a single live Job with all JobEffort records.

    Each effort record captures measured processing time, setup time, and
    quality metrics (parts produced vs. scrapped). These real measurements
    feed CMSD JobEffortDescription entities, enabling performance analysis
    and variance-from-plan calculations.

    CMSD relevance: Populates the CMSD Job → JobEffortDescription chain,
    providing actual-vs-planned comparison data for simulation.
    """
    job = db.query(Job).filter(Job.identifier == identifier).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    data = _job_to_dict(job)
    data["efforts"] = [
        {
            "effort_type": e.effort_type,
            "processing_time_seconds": e.processing_time_seconds,
            "setup_time_seconds": e.setup_time_seconds,
            "parts_produced": e.parts_produced,
            "parts_scrapped": e.parts_scrapped,
        }
        for e in job.job_efforts
    ]
    return data


@router.get("/jobs/{identifier}/progress")
def get_job_progress(identifier: str, db: Session = Depends(get_db)):
    """Get step-by-step progress of a Job through its ProcessPlan.

    Calculates total steps in the routing, current step index, current
    process name, and percentage complete. Useful for progress bars and
    remaining-work estimation in the dashboard.

    CMSD relevance: Progress data feeds CMSD Job status monitoring,
    enabling real-time WIP tracking and throughput prediction.
    """
    job = db.query(Job).filter(Job.identifier == identifier).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    plan = job.process_plan_ref
    total_steps = len(plan.processes) if plan else 0
    current_idx = 0
    if job.current_process_ref:
        for i, p in enumerate(sorted(plan.processes, key=lambda x: x.sequence_order)):
            if p.identifier == job.current_process_ref.identifier:
                current_idx = i + 1
                break
    return {
        "job_identifier": job.identifier,
        "status": job.status,
        "total_steps": total_steps,
        "current_step": current_idx,
        "current_process_name": job.current_process_ref.name if job.current_process_ref else None,
        "percent_complete": round((current_idx / total_steps) * 100, 1) if total_steps > 0 else 0,
    }


def _job_to_dict(j: Job) -> dict:
    """Serialize a Job ORM model to a JSON-safe dict.

    Includes all scheduling timestamps, status, priority, and the chain of
    references: parent OrderLine → ProcessPlan → current Process. Each missing
    reference gracefully resolves to None.
    """
    return {
        "identifier": j.identifier,
        "status": j.status,
        "priority": j.priority,
        "release_date": j.release_date.isoformat() if j.release_date else None,
        "start_time": j.start_time.isoformat() if j.start_time else None,
        "end_time": j.end_time.isoformat() if j.end_time else None,
        "due_date": j.due_date.isoformat() if j.due_date else None,
        "order_line_identifier": j.order_line_ref.identifier if j.order_line_ref else None,
        "process_plan_identifier": j.process_plan_ref.identifier if j.process_plan_ref else None,
        "current_process_identifier": j.current_process_ref.identifier if j.current_process_ref else None,
    }


