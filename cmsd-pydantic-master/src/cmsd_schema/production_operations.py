# =============================================================================
# PRODUCTION OPERATIONS (from ProductionOperations.rng)
# =============================================================================
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, model_validator

from .basic_structures import Duration
from .basic_types import PrecedenceRelationship, JobStatus
from .entity_reference_definition import JobReference, ProcessPlanReference, ProcessReference
from .identifiable_entity import IdentifiableEntity
from .part_entities import PartGroup
from .resource_entities import ResourcesRequired


class JobConstraint(BaseModel):
    """Precedence constraint between jobs"""
    predecessor_job: JobReference = Field(..., description="Job that must precede")
    relationship: PrecedenceRelationship = Field(..., description="Type of precedence relationship")
    time_lag: Optional[Duration] = Field(None, description="Time lag between jobs")


class JobEffortDescription(BaseModel):
    """Description of effort for a job (planned or actual)"""
    update_time: Optional[datetime] = None
    parts_produced: List[PartGroup] = Field(default_factory=list)
    parts_consumed: List[PartGroup] = Field(default_factory=list)
    resources_required: List[ResourcesRequired] = Field(default_factory=list)
    due_date: Optional[datetime] = None
    release_date: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    setup_time: Optional[Duration] = None
    processing_time: Optional[Duration] = None
    process_plan: Optional[ProcessPlanReference] = None
    current_process_plan_step: Optional[ProcessReference] = None

    @model_validator(mode='after')
    def check_at_least_one_field(self):
        if not any([
            self.update_time,
            self.parts_produced,
            self.parts_consumed,
            self.resources_required,
            self.due_date,
            self.release_date,
            self.start_time,
            self.end_time,
            self.setup_time,
            self.processing_time,
            self.process_plan,
            self.current_process_plan_step
        ]):
            raise ValueError("At least one field must be specified")
        return self


class Job(IdentifiableEntity):
    """Job (work order) definition"""
    status: JobStatus = Field(..., description="Current job status")
    update_time: Optional[datetime] = None
    priority: Optional[str] = None
    precedence_constraints: List[JobConstraint] = Field(default_factory=list)
    sub_jobs: List[JobReference] = Field(default_factory=list)
    planned_effort: Optional[JobEffortDescription] = None
    actual_effort: Optional[JobEffortDescription] = None
