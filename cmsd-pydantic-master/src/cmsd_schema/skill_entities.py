from __future__ import annotations
from pydantic import Field
from typing import Optional, List

from .identifiable_entity import IdentifiableEntity


# =============================================================================
# SKILL ENTITIES (from Skill.rng)
# =============================================================================

class SkillLevel(IdentifiableEntity):
    """A proficiency level within a skill definition"""
    level_value: Optional[int] = Field(None, ge=0, description="Numeric level indicator (higher = more proficient)")


class SkillDefinition(IdentifiableEntity):
    """Definition of a skill that can be assigned to employees/resources"""
    levels: List[SkillLevel] = Field(default_factory=list, description="Proficiency levels for this skill")
