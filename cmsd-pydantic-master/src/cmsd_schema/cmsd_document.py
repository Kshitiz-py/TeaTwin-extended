"""
CMSD (Core Manufacturing Simulation Data) Pydantic Models
Based on CMSD v1.0 RELAX NG Schema

This module provides Pydantic models that mirror the CMSD XML schema structure,
enabling structured output generation and validation for manufacturing simulation data.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List

from .part_entities import PartType, Part, BillOfMaterials
from .process_planning import ProcessPlan
from .production_operations import Job
from .resource_entities import ResourceClass, Resource
from .layout import Layout
from .calendar_entities import Calendar
from .schedule_entities import Schedule
from .order_entities import Order
from .inventory_entities import InventoryItem, InventoryItemClass
from .setup_entities import SetupDefinition, SetupChangeoverDefinition
from .skill_entities import SkillDefinition
from .distribution_definition import DistributionDefinition
from .maintenance_entities import MaintenancePlan
from .reference_material import ReferenceMaterial
from .cost_allocation import CostAllocationData
from .connection_entities import Connection


# =============================================================================
# CMSD DOCUMENT ROOT
# =============================================================================

class CMSDDocument(BaseModel):
    """Root CMSD document containing all manufacturing data"""
    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "part_types": [{
                    "identifier": "PT_Widget_001",
                    "name": "Standard Widget",
                    "description": "Standard widget part type"
                }],
                "resources": [{
                    "identifier": "RES_CNC_001",
                    "resource_type": "machine",
                    "name": "CNC Mill #1",
                    "current_status": "idle"
                }]
            }
        }
    )

    # Parts and Bill of Materials
    part_types: List[PartType] = Field(default_factory=list)
    parts: List[Part] = Field(default_factory=list)
    bills_of_materials: List[BillOfMaterials] = Field(default_factory=list)

    # Resources
    resource_classes: List[ResourceClass] = Field(default_factory=list)
    resources: List[Resource] = Field(default_factory=list)

    # Process Planning
    process_plans: List[ProcessPlan] = Field(default_factory=list)

    # Production Operations
    jobs: List[Job] = Field(default_factory=list)

    # Layout
    layouts: List[Layout] = Field(default_factory=list)

    # Calendar
    calendars: List[Calendar] = Field(default_factory=list)

    # Schedules
    schedules: List[Schedule] = Field(default_factory=list)

    # Orders
    orders: List[Order] = Field(default_factory=list)

    # Inventory
    inventory_item_classes: List[InventoryItemClass] = Field(default_factory=list)
    inventory_items: List[InventoryItem] = Field(default_factory=list)

    # Setup
    setup_definitions: List[SetupDefinition] = Field(default_factory=list)
    setup_changeover_definitions: List[SetupChangeoverDefinition] = Field(default_factory=list)

    # Skills
    skill_definitions: List[SkillDefinition] = Field(default_factory=list)

    # Distributions
    distribution_definitions: List[DistributionDefinition] = Field(default_factory=list)

    # Maintenance
    maintenance_plans: List[MaintenancePlan] = Field(default_factory=list)

    # Reference Materials
    reference_materials: List[ReferenceMaterial] = Field(default_factory=list)

    # Cost Allocation
    cost_allocation_data: List[CostAllocationData] = Field(default_factory=list)

    # Connections
    connections: List[Connection] = Field(default_factory=list)
