from __future__ import annotations
from datetime import datetime
from pydantic import Field
from typing import Optional

from .basic_types import EventType
from .entity_reference_definition import ResourceReference, JobReference
from .identifiable_entity import IdentifiableEntity


# =============================================================================
# EVENT ENTITIES (from EventEntities.rng / Bergmann §4–5)
# =============================================================================

class Event(IdentifiableEntity):
    """A discrete event in the simulation, referencing a resource or job"""
    event_type: EventType = Field(..., description="Type of the event")
    timestamp: Optional[datetime] = Field(None, description="When the event occurred or is scheduled")
    resource_reference: Optional[ResourceReference] = Field(
        None, description="Resource this event is associated with"
    )
    job_reference: Optional[JobReference] = Field(
        None, description="Job this event is associated with"
    )
