# =============================================================================
# PART ENTITIES (from Part.rng)
# =============================================================================
from decimal import Decimal
from typing import Optional, List

from pydantic import Field, BaseModel, model_validator

from .basic_structures import GrossDimensions, Weight, LocationDefinition, LotInformation
from .basic_types import PartProductionStatus
from .entity_reference_definition import BillOfMaterialsReference, ProcessPlanReference, PartTypeReference, \
    ProcessReference, PartReference, EntityReference
from .identifiable_entity import IdentifiableEntity
from .basic_structures import Property



class PartType(IdentifiableEntity):
    """Part type definition"""
    bill_of_materials: Optional[BillOfMaterialsReference] = None
    process_plan: Optional[ProcessPlanReference] = None
    size: Optional[GrossDimensions] = None
    weight: Optional[Weight] = None


class Part(IdentifiableEntity):
    """Part instance"""
    part_type: Optional[PartTypeReference] = Field(None, description="Reference to part type")
    production_status: Optional[PartProductionStatus] = None
    location: Optional[LocationDefinition] = None
    bill_of_materials: Optional[BillOfMaterialsReference] = None
    process_plan: Optional[ProcessPlanReference] = None
    last_finished_process_step: Optional[ProcessReference] = None
    size: Optional[GrossDimensions] = None
    weight: Optional[Weight] = None
    lot: Optional[LotInformation] = None


class PartGroup(BaseModel):
    """Group of parts (either by type with quantity or specific instances)"""
    description: Optional[str] = None
    part_type: Optional[PartTypeReference] = Field(None, description="Part type for quantity-based group")
    part_quantity: Optional[int] = Field(None, ge=0, description="Quantity of parts")
    part_instances: List[PartReference] = Field(default_factory=list, description="Specific part instances")

    @model_validator(mode='after')
    def check_part_group_validity(self):
        has_quantity = self.part_quantity is not None
        has_type = self.part_type is not None
        has_instances = len(self.part_instances) > 0

        if not (has_instances or (has_quantity and has_type)):
            raise ValueError("Must specify either part instances or both part_type and part_quantity")

        if has_quantity and not has_type:
            raise ValueError("If part_quantity is specified, part_type must also be specified")

        return self


class BillOfMaterialsComponent(IdentifiableEntity):
    """Component in a bill of materials"""
    quantity: Decimal = Field(..., description="Quantity of this component")
    part_type: Optional[PartTypeReference] = None
    part_instances: List[PartReference] = Field(default_factory=list)
    sub_components: List['BillOfMaterialsComponentReference'] = Field(default_factory=list)

    @model_validator(mode='after')
    def check_has_part_or_subcomponent(self):
        if not self.part_type and not self.sub_components:
            raise ValueError("Must have either part_type or sub_components")
        return self


class BillOfMaterialsComponentReference(EntityReference):
    """Reference to a BillOfMaterials component"""
    bill_of_materials_component_identifier: str


class BillOfMaterials(IdentifiableEntity):
    """Bill of materials definition"""
    part_type: Optional[PartTypeReference] = None
    part_instance: Optional[PartReference] = None
    main_component: Optional[BillOfMaterialsComponentReference] = None
    components: List[BillOfMaterialsComponent] = Field(default_factory=list)

# Update forward references
BillOfMaterialsComponent.model_rebuild()