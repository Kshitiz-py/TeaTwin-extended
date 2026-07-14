from __future__ import annotations
from datetime import datetime
from pydantic import Field, model_validator
from typing import Optional, List

from .basic_structures import Duration
from .entity_reference_definition import (
    JobReference, ProcessPlanReference, ProcessReference, ResourceReference
)
from .identifiable_entity import IdentifiableEntity
from .part_entities import PartGroup
from .resource_entities import ResourcesRequired


# =============================================================================
# SCHEDULE ENTITIES (from Schedule.rng)
# =============================================================================

class ScheduleItemEffortDescription(IdentifiableEntity):
    """Planned or actual effort for a schedule item"""
    update_time: Optional[datetime] = None
    parts_produced: List[PartGroup] = Field(default_factory=list)
    parts_consumed: List[PartGroup] = Field(default_factory=list)
    resources_required: List[ResourcesRequired] = Field(default_factory=list)
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
            self.start_time,
            self.end_time,
            self.setup_time,
            self.processing_time,
            self.process_plan,
            self.current_process_plan_step,
        ]):
            raise ValueError("At least one field must be specified")
        return self


class ScheduleItem(IdentifiableEntity):
    """A single item in a schedule (planned or actual)"""
    job: Optional[JobReference] = None
    planned_effort: Optional[ScheduleItemEffortDescription] = None
    actual_effort: Optional[ScheduleItemEffortDescription] = None

    @model_validator(mode='after')
    def check_at_least_one_effort(self):
        if self.planned_effort is None and self.actual_effort is None:
            raise ValueError("At least one of planned_effort or actual_effort must be specified")
        return self


class Schedule(IdentifiableEntity):
    """A schedule consisting of ordered schedule items"""
    items: List[ScheduleItem] = Field(default_factory=list, description="Schedule items")
