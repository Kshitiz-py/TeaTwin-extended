from __future__ import annotations
from pydantic import Field
from typing import Optional, List, TYPE_CHECKING

from .basic_types import InventoryItemType
from .entity_reference_definition import (
    PartTypeReference, ResourceClassReference, InventoryItemClassReference
)
from .identifiable_entity import IdentifiableEntity


# =============================================================================
# INVENTORY ENTITIES (from Inventory.rng)
# =============================================================================

class InventoryItemClass(IdentifiableEntity):
    """Classification of inventory items"""
    item_type: InventoryItemType = Field(..., description="Whether this class covers parts or resources")
    part_type: Optional[PartTypeReference] = Field(
        None, description="Part type (when item_type is PART)"
    )
    resource_class: Optional[ResourceClassReference] = Field(
        None, description="Resource class (when item_type is RESOURCE)"
    )


class InventoryItem(IdentifiableEntity):
    """An inventory item instance"""
    item_class: Optional[InventoryItemClassReference] = None
    quantity_on_hand: Optional[int] = Field(None, ge=0, description="Current quantity in inventory")
    quantity_reserved: Optional[int] = Field(None, ge=0, description="Quantity reserved for orders")
    reorder_point: Optional[int] = Field(None, ge=0, description="Reorder trigger level")
    reorder_quantity: Optional[int] = Field(None, ge=0, description="Quantity to order when reorder is triggered")
