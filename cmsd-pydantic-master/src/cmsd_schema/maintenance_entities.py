from __future__ import annotations
from datetime import datetime
from pydantic import Field
from typing import Optional, List

from .basic_structures import Duration
from .entity_reference_definition import ResourceReference, ResourceClassReference
from .identifiable_entity import IdentifiableEntity


# =============================================================================
# MAINTENANCE ENTITIES (from Maintenance.rng)
# =============================================================================

class MaintenanceProcess(IdentifiableEntity):
    """A maintenance activity to be performed"""
    duration: Optional[Duration] = Field(None, description="Expected duration of this maintenance process")
    applicable_resource_classes: List[ResourceClassReference] = Field(
        default_factory=list,
        description="Resource classes this maintenance process applies to"
    )
    applicable_resources: List[ResourceReference] = Field(
        default_factory=list,
        description="Specific resources this maintenance process applies to"
    )


class MaintenancePlan(IdentifiableEntity):
    """A plan grouping one or more maintenance processes"""
    scheduled_date: Optional[datetime] = Field(None, description="When the maintenance is planned")
    periodicity: Optional[Duration] = Field(
        None, description="Maintenance interval / wartungsintervall_sek (RELAX NG: <wartungsintervall>)"
    )
    processes: List[MaintenanceProcess] = Field(
        default_factory=list,
        description="Maintenance processes in this plan"
    )
