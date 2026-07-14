from __future__ import annotations
from pydantic import Field
from typing import Optional, List

from .basic_structures import Currency
from .basic_types import CostCategoryType, CostType
from .entity_reference_definition import JobReference, ResourceReference
from .identifiable_entity import IdentifiableEntity


# =============================================================================
# COST ALLOCATION DATA (from CostAllocation.rng)
# =============================================================================

class CostAllocationData(IdentifiableEntity):
    """Cost allocation data for a manufacturing activity"""
    cost_category: Optional[CostCategoryType] = Field(None, description="Category of cost")
    cost_type: Optional[CostType] = Field(None, description="Whether the cost is fixed or variable")
    amount: Optional[Currency] = Field(None, description="Cost amount")
    job: Optional[JobReference] = Field(None, description="Job this cost is allocated to")
    resource: Optional[ResourceReference] = Field(None, description="Resource this cost is associated with")
