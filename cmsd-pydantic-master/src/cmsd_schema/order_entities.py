from __future__ import annotations
from datetime import datetime
from pydantic import Field, model_validator
from typing import Optional, List

from .basic_structures import Currency
from .basic_types import OrderStatus
from .entity_reference_definition import PartTypeReference, ProcessPlanReference
from .identifiable_entity import IdentifiableEntity


# =============================================================================
# ORDER ENTITIES (from Order.rng)
# =============================================================================

class OrderLinePartDescription(IdentifiableEntity):
    """Description of parts associated with an order line"""
    part_type: Optional[PartTypeReference] = None
    quantity: Optional[int] = Field(None, ge=0, description="Part quantity")
    process_plan: Optional[ProcessPlanReference] = None


class OrderLineServiceDescription(IdentifiableEntity):
    """Description of a service associated with an order line"""
    service_description: Optional[str] = None
    unit_price: Optional[Currency] = None


class OrderLine(IdentifiableEntity):
    """A line item within an order"""
    status: Optional[OrderStatus] = None
    due_date: Optional[datetime] = None
    release_date: Optional[datetime] = None
    part_description: Optional[OrderLinePartDescription] = None
    service_description: Optional[OrderLineServiceDescription] = None

    @model_validator(mode='after')
    def check_has_description(self):
        if self.part_description is None and self.service_description is None:
            raise ValueError("At least one of part_description or service_description must be specified")
        return self


class Order(IdentifiableEntity):
    """A customer or production order"""
    status: Optional[OrderStatus] = None
    due_date: Optional[datetime] = None
    release_date: Optional[datetime] = None
    order_lines: List[OrderLine] = Field(default_factory=list, description="Lines of this order")
