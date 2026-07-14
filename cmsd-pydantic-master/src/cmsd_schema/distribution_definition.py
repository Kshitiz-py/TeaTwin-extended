from __future__ import annotations
from pydantic import Field
from typing import List

from .basic_structures import Distribution
from .identifiable_entity import IdentifiableEntity


# =============================================================================
# DISTRIBUTION DEFINITION (from DistributionDefinition.rng)
# =============================================================================

class DistributionDefinition(IdentifiableEntity):
    """A named, reusable statistical distribution definition"""
    distribution: Distribution = Field(..., description="The statistical distribution")
