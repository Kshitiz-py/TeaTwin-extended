from __future__ import annotations
from pydantic import Field
from typing import Optional, List

from .basic_structures import Duration
from .entity_reference_definition import ResourceReference, ResourceClassReference, SkillReference
from .identifiable_entity import IdentifiableEntity


# =============================================================================
# SETUP ENTITIES (from Setup.rng)
# =============================================================================

class SetupDefinition(IdentifiableEntity):
    """Definition of a setup state for a resource"""
    applicable_resource_classes: List[ResourceClassReference] = Field(
        default_factory=list,
        description="Resource classes this setup applies to"
    )
    applicable_resources: List[ResourceReference] = Field(
        default_factory=list,
        description="Specific resources this setup applies to"
    )
    setup_skill: Optional[SkillReference] = Field(
        None, description="Skill required to perform this setup (Bergmann Table 3)"
    )


class SetupChangeoverDefinition(IdentifiableEntity):
    """Definition of the changeover time between two setups"""
    from_setup_identifier: str = Field(..., description="Source setup identifier")
    to_setup_identifier: str = Field(..., description="Target setup identifier")
    changeover_time: Optional[Duration] = Field(None, description="Time required for the changeover")
    applicable_resource_classes: List[ResourceClassReference] = Field(
        default_factory=list,
        description="Resource classes this changeover applies to"
    )
    applicable_resources: List[ResourceReference] = Field(
        default_factory=list,
        description="Specific resources this changeover applies to"
    )
