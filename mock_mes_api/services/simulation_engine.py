"""
MES Simulation Engine — Randomly mutates operational data to simulate a live factory.
Runs as a background thread, periodically updating resource statuses, jobs, inventory.
This creates the "live data stream" that the CMSD Twin Service polls and detects changes from.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import random
import threading
import time
import logging
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.config import config as app_config
from mock_sap_api.models import (
    Resource, ResourceStatus, Job, JobEffort, Inventory, Incident,
    Process, ProcessPlan,
)

logger = logging.getLogger("mes-simulation-engine")

STATUS_POOL = ["busy", "idle", "setup", "paused"]
RARE_STATUSES = ["broken", "underMaintenance"]
INCIDENT_TYPES = ["toolBreakage", "motorFailure", "electricalFault", "sensorError", "softwareGlitch", "wearAndTear"]
SEVERITIES = ["low", "medium", "high", "critical"]


class MESSimulationEngine:
    """Background engine that mutates MES data to simulate live factory operations."""

    def __init__(self, interval_seconds: float = 5.0):
        self.interval = interval_seconds
        self._thread: threading.Thread | None = None
        self._running = False
        self.engine = create_engine(app_config.database.url, pool_pre_ping=True)
        self.Session = sessionmaker(bind=self.engine)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="MES-SimEngine")
        self._thread.start()
        logger.info(f"MES Simulation Engine started (interval={self.interval}s)")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("MES Simulation Engine stopped")

    def _run_loop(self):
        while self._running:
            try:
                self._tick()
            except Exception as e:
                logger.error(f"Simulation engine tick error: {e}")
            time.sleep(self.interval)

    def _tick(self):
        session = self.Session()
        try:
            # 1. Randomly cycle resource statuses
            self._mutate_resource_statuses(session)

            # 2. Progress active jobs
            self._progress_jobs(session)

            # 3. Fluctuate inventory
            self._fluctuate_inventory(session)

            # 4. Possibly create/update incidents
            self._manage_incidents(session)

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _mutate_resource_statuses(self, session):
        """Flip some resource statuses randomly."""
        statuses = session.query(ResourceStatus).all()
        for rs in statuses:
            # 15% chance to change status
            if random.random() < 0.15:
                # 5% chance of rare status (broken / underMaintenance)
                if random.random() < 0.05:
                    rs.status = random.choice(RARE_STATUSES)
                else:
                    rs.status = random.choice(STATUS_POOL)
                rs.last_status_change = datetime.utcnow()
                rs.uptime_seconds += int(self.interval * random.randint(1, 10))
                if rs.status == "busy":
                    rs.parts_processed_today += random.randint(0, 3)

    def _progress_jobs(self, session):
        """Advance active jobs through their process steps."""
        active_jobs = session.query(Job).filter(Job.status.in_(["started", "released"])).all()
        for job in active_jobs:
            if job.status == "released" and random.random() < 0.20:
                # Start the job
                job.status = "started"
                job.start_time = datetime.utcnow()
                plan = job.process_plan_ref
                if plan and plan.processes:
                    first = sorted(plan.processes, key=lambda p: p.sequence_order)[0]
                    job.current_process_id = first.id

            elif job.status == "started" and random.random() < 0.25:
                # Advance to next process step
                plan = job.process_plan_ref
                if plan and plan.processes:
                    steps = sorted(plan.processes, key=lambda p: p.sequence_order)
                    current_idx = 0
                    if job.current_process_ref:
                        for i, s in enumerate(steps):
                            if s.id == job.current_process_id:
                                current_idx = i
                                break
                    next_idx = current_idx + 1
                    if next_idx < len(steps):
                        job.current_process_id = steps[next_idx].id
                    else:
                        # Job complete
                        job.status = "completed"
                        job.end_time = datetime.utcnow()
                        job.current_process_id = None
                        # Create actual effort record
                        effort = session.query(JobEffort).filter(
                            JobEffort.job_id == job.id,
                            JobEffort.effort_type == "actual"
                        ).first()
                        if not effort:
                            effort = JobEffort(job_id=job.id, effort_type="actual")
                            session.add(effort)
                        planned = session.query(JobEffort).filter(
                            JobEffort.job_id == job.id,
                            JobEffort.effort_type == "planned"
                        ).first()
                        if planned:
                            effort.processing_time_seconds = planned.processing_time_seconds + random.randint(-60, 120)
                            effort.setup_time_seconds = planned.setup_time_seconds + random.randint(-30, 60)
                            effort.parts_produced = planned.parts_produced
                            effort.parts_scrapped = random.randint(0, max(1, planned.parts_produced // 20))
                        effort.update_time = datetime.utcnow()

    def _fluctuate_inventory(self, session):
        """Slightly modify inventory quantities."""
        items = session.query(Inventory).all()
        for inv in items:
            if random.random() < 0.10:
                delta = random.uniform(-5, 5)
                inv.quantity = max(0, inv.quantity + delta)
                inv.last_updated = datetime.utcnow()

    def _manage_incidents(self, session):
        """Create new incidents or resolve existing ones."""
        # 10% chance to create a new incident
        if random.random() < 0.10:
            resources = session.query(Resource).filter(
                Resource.resource_type.in_(["machine", "conveyor", "station"])
            ).all()
            if resources:
                r = random.choice(resources)
                incident = Incident(
                    identifier=f"INC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{random.randint(1000,9999)}",
                    resource_id=r.id,
                    incident_type=random.choice(INCIDENT_TYPES),
                    severity=random.choice(SEVERITIES),
                    status="open",
                    start_time=datetime.utcnow(),
                    description=f"Automated simulation incident on {r.name}",
                )
                session.add(incident)
                # Also update the resource status
                rs = session.query(ResourceStatus).filter(ResourceStatus.resource_id == r.id).first()
                if rs:
                    rs.status = "broken"
                    rs.last_status_change = datetime.utcnow()

        # 30% chance to resolve an open incident
        open_incidents = session.query(Incident).filter(
            Incident.status.in_(["open", "acknowledged"])
        ).all()
        for inc in open_incidents:
            if random.random() < 0.30:
                inc.status = "resolved"
                inc.end_time = datetime.utcnow()
                inc.resolution_notes = f"Simulated repair completed at {datetime.utcnow().isoformat()}"
                rs = session.query(ResourceStatus).filter(ResourceStatus.resource_id == inc.resource_id).first()
                if rs and rs.status == "broken":
                    rs.status = random.choice(["idle", "busy", "setup"])
                    rs.last_status_change = datetime.utcnow()


# Singleton for easy import
simulation_engine = MESSimulationEngine(interval_seconds=5.0)