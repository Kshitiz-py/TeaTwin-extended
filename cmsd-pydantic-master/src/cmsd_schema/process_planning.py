from __future__ import annotations
from pydantic import Field
from typing import Optional, List, Union
from .basic_structures import Duration
from .basic_types import ProcessGroupType
from .entity_reference_definition import PartTypeReference
from .identifiable_entity import IdentifiableEntity
from .part_entities import PartGroup
from .resource_entities import ResourcesRequired


# =============================================================================
# PROCESS PLANNING (from ProductionPlanning.rng)
# =============================================================================

class Process(IdentifiableEntity):
    """Process step definition"""
    duration: Optional[Duration] = None
    resources_required: List[ResourcesRequired] = Field(default_factory=list)
    parts_produced: List[PartGroup] = Field(default_factory=list)
    parts_consumed: List[PartGroup] = Field(default_factory=list)
    setup_time: Optional[Duration] = None
    load_time: Optional[Duration] = None
    unload_time: Optional[Duration] = None
    pick_time: Optional[Duration] = None
    place_time: Optional[Duration] = None


class ProcessGroup(IdentifiableEntity):
    """Group of processes with a branching type (sequence, concurrent, decision)"""
    group_type: ProcessGroupType = Field(..., description="How processes in this group are executed")
    processes: List[Union[Process, ProcessGroup]] = Field(
        default_factory=list,
        description="Ordered list of processes or nested process groups"
    )


# Resolve forward reference introduced by the self-referential ProcessGroup
ProcessGroup.model_rebuild()


class ProcessPlan(IdentifiableEntity):
    """Process plan (routing) definition"""
    part_type: Optional[PartTypeReference] = None
    processes: List[Union[Process, ProcessGroup]] = Field(
        default_factory=list,
        description="Sequence of process steps or process groups"
    )
