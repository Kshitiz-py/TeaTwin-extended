"""Jobs and Job Effort endpoints (MES)"""

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
    q = db.query(Job)
    if status:
        q = q.filter(Job.status == status)
    results = q.all()
    return {"count": len(results), "jobs": [_job_to_dict(j) for j in results]}


@router.get("/jobs/{identifier}")
def get_job(identifier: str, db: Session = Depends(get_db)):
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