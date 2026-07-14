from pydantic import BaseModel, Field, model_validator
from typing import Optional


# =============================================================================
# ENTITY REFERENCES (from EntityReferenceDefinition.rng)
# =============================================================================

class EntityReference(BaseModel):
    """Base class for entity references"""
    document_identifier: Optional[str] = Field(None, description="Document containing the referenced entity")


class PartTypeReference(EntityReference):
    """Reference to a PartType"""
    part_type_identifier: str = Field(..., description="PartType identifier")


class PartReference(EntityReference):
    """Reference to a Part instance"""
    part_identifier: str = Field(..., description="Part identifier")


class ResourceClassReference(EntityReference):
    """Reference to a ResourceClass"""
    resource_class_identifier: str = Field(..., description="ResourceClass identifier")


class ResourceReference(EntityReference):
    """Reference to a Resource"""
    resource_identifier: str = Field(..., description="Resource identifier")


class ProcessPlanReference(EntityReference):
    """Reference to a ProcessPlan"""
    process_plan_identifier: str = Field(..., description="ProcessPlan identifier")


class ProcessReference(EntityReference):
    """Reference to a Process; at least one of process_identifier or process_plan_identifier required"""
    process_identifier: Optional[str] = Field(None, description="Process identifier")
    process_plan_identifier: Optional[str] = Field(None, description="ProcessPlan containing the process")

    @model_validator(mode='after')
    def check_at_least_one_identifier(self):
        if not self.process_identifier and not self.process_plan_identifier:
            raise ValueError("At least one of process_identifier or process_plan_identifier must be specified")
        return self


class BillOfMaterialsReference(EntityReference):
    """Reference to a BillOfMaterials"""
    bill_of_materials_identifier: str = Field(..., description="BillOfMaterials identifier")


class JobReference(EntityReference):
    """Reference to a Job"""
    job_identifier: str = Field(..., description="Job identifier")


class SetupDefinitionReference(EntityReference):
    """Reference to a SetupDefinition"""
    setup_definition_identifier: str = Field(..., description="Setup identifier")


class SetupChangeoverReference(EntityReference):
    """Reference to a SetupChangeoverDefinition"""
    setup_changeover_identifier: str = Field(..., description="SetupChangeover identifier")


class SkillReference(EntityReference):
    """Reference to a Skill/SkillDefinition"""
    skill_identifier: str = Field(..., description="Skill identifier")
    skill_level_identifier: Optional[str] = Field(None, description="Specific skill level identifier")


class CalendarReference(EntityReference):
    """Reference to a Calendar entity; exactly one of the *_identifier fields must be set"""
    calendar_identifier: Optional[str] = Field(None, description="Calendar identifier")
    shift_identifier: Optional[str] = Field(None, description="Shift identifier")
    shift_schedule_identifier: Optional[str] = Field(None, description="ShiftSchedule identifier")
    holiday_identifier: Optional[str] = Field(None, description="Holiday identifier")

    @model_validator(mode='after')
    def check_mutual_exclusivity(self):
        set_fields = sum([
            self.calendar_identifier is not None,
            self.shift_identifier is not None,
            self.shift_schedule_identifier is not None,
            self.holiday_identifier is not None,
        ])
        if set_fields != 1:
            raise ValueError(
                "Exactly one of calendar_identifier, shift_identifier, "
                "shift_schedule_identifier, or holiday_identifier must be specified"
            )
        return self


class LayoutElementReference(EntityReference):
    """Reference to a LayoutElement"""
    layout_element_identifier: str = Field(..., description="LayoutElement identifier")


class ReferenceMaterialReference(EntityReference):
    """Reference to a ReferenceMaterial"""
    reference_material_identifier: str = Field(..., description="ReferenceMaterial identifier")


class OrderInformationReference(EntityReference):
    """Reference to an Order or OrderLine"""
    order_identifier: str = Field(..., description="Order identifier")
    order_line_identifier: Optional[str] = Field(None, description="OrderLine identifier within the order")


class ScheduleInformationReference(EntityReference):
    """Reference to a Schedule or ScheduleItem"""
    schedule_identifier: str = Field(..., description="Schedule identifier")
    schedule_item_identifier: Optional[str] = Field(None, description="ScheduleItem identifier within the schedule")


class MaintenancePlanReference(EntityReference):
    """Reference to a MaintenancePlan"""
    maintenance_plan_identifier: str = Field(..., description="MaintenancePlan identifier")


class InventoryItemClassReference(EntityReference):
    """Reference to an InventoryItemClass"""
    inventory_item_class_identifier: str = Field(..., description="InventoryItemClass identifier")


class PropertyDescriptionReference(EntityReference):
    """Reference to a property description by name"""
    property_name: str = Field(..., description="Name of the referenced property description")


class EventReference(EntityReference):
    """Reference to an Event entity"""
    event_identifier: str = Field(..., description="Event identifier")
