# =============================================================================
# RESOURCE ENTITIES (from Resource.rng)
# =============================================================================
from decimal import Decimal
from typing import Optional, List

from pydantic import Field, BaseModel, model_validator

from .basic_structures import Currency, GrossDimensions, Duration, Length
from .basic_types import ResourceType, ResourceStatus, DecisionRule, RoutingRule
from .resource_configs import (
    SourceConfig, BufferConfig, DispatcherConfig, ArticulatedRobotConfig,
    MobileRobotConfig, WarehouseConfig, GateConfig, ChargingStationConfig,
    EnergyModel, SpeedProfile,
)
from .entity_reference_definition import ResourceClassReference, ResourceReference, SetupDefinitionReference, \
    SkillReference, CalendarReference
from .identifiable_entity import IdentifiableEntity


class ResourceClass(IdentifiableEntity):
    """Resource class definition"""
    resource_type: ResourceType = Field(..., description="Type of resource")
    hourly_rate: Optional[Currency] = None
    size: Optional[GrossDimensions] = None


class ResourcesRequired(BaseModel):
    """Resources required for an operation"""
    description: Optional[str] = None
    resource_class: Optional[ResourceClassReference] = None
    minimum_number: Optional[int] = Field(None, ge=0)
    maximum_number: Optional[int] = Field(None, ge=0)
    resources: List[ResourceReference] = Field(default_factory=list)
    allowable_setups: List[SetupDefinitionReference] = Field(default_factory=list)
    required_employee_skills: List[SkillReference] = Field(default_factory=list)

    @model_validator(mode='after')
    def check_at_least_one_field(self):
        if not any([
            self.description,
            self.resource_class,
            self.minimum_number is not None,
            self.maximum_number is not None,
            self.resources,
            self.allowable_setups,
            self.required_employee_skills
        ]):
            raise ValueError("At least one field must be specified")
        return self


class Resource(IdentifiableEntity):
    """Resource instance"""
    resource_type: ResourceType = Field(..., description="Type of resource")
    resource_class: Optional[ResourceClassReference] = None
    current_status: Optional[ResourceStatus] = None
    current_setup: Optional[SetupDefinitionReference] = None
    shift_assignments: List[CalendarReference] = Field(default_factory=list)
    associated_resources: List[ResourceReference] = Field(default_factory=list)
    hourly_rate: Optional[Currency] = None
    employee_skills: List[SkillReference] = Field(default_factory=list)
    size: Optional[GrossDimensions] = None

    # Capacity and reliability fields
    capacity: Optional[int] = Field(None, ge=0, description="Maximum number of items/entities the resource can hold or process simultaneously")
    availability: Optional[Decimal] = Field(None, ge=0, le=100, description="Technical availability as a percentage (0–100)")
    mttr: Optional[Duration] = Field(None, description="Mean time to repair")
    mtbf: Optional[Duration] = Field(None, description="Mean time between failures")
    mcbf: Optional[int] = Field(None, ge=0, description="Mean cycles between failures")
    reliability: Optional[Decimal] = Field(None, ge=0, le=100, description="Reliability/waste rate as a percentage (0–100)")

    # Decision and routing rules
    decision_rule: Optional[DecisionRule] = Field(None, description="Buffer exit sequencing rule")
    routing_rule: Optional[RoutingRule] = Field(None, description="Buffer exit routing rule")

    # Skill references
    repair_skill: Optional[SkillReference] = Field(None, description="Skill required to repair this resource")

    # Timing fields
    cycle_time: Optional[Duration] = Field(None, description="Cycle time (takt time) of the resource")
    desired_replenishment_time: Optional[Duration] = Field(None, description="Desired replenishment time")

    # Transport fields
    transport_capacity: Optional[int] = Field(None, ge=0, description="Transport capacity (number of items)")
    tow_bar_length: Optional[Length] = Field(None, description="Tow bar length for trailer-type resources")

    # Worker fields
    worker_count: Optional[int] = Field(None, ge=0, description="Number of workers assigned to this resource")
    worker_qualification: Optional[SkillReference] = Field(None, description="Required worker qualification")

    # Composition configs
    source_config: Optional[SourceConfig] = None
    buffer_config: Optional[BufferConfig] = None
    dispatcher_config: Optional[DispatcherConfig] = None
    warehouse_config: Optional[WarehouseConfig] = None
    gate_config: Optional[GateConfig] = None
    charging_station_config: Optional[ChargingStationConfig] = None
    energy_model: Optional[EnergyModel] = None
    speed_profile: Optional[SpeedProfile] = None
    articulated_robot_config: Optional[ArticulatedRobotConfig] = None
    mobile_robot_config: Optional[MobileRobotConfig] = None

    @model_validator(mode='after')
    def check_employee_constraints(self):
        _skill_bearing_types = {
            ResourceType.EMPLOYEE,
            ResourceType.MOBILE_ROBOT,
            ResourceType.DISPATCHER,
        }
        if self.employee_skills and self.resource_type not in _skill_bearing_types:
            raise ValueError(
                f"employee_skills can only be specified for resource types: "
                f"{', '.join(t.value for t in _skill_bearing_types)}"
            )
        if self.employee_skills and self.resource_type != ResourceType.EMPLOYEE:
            raise ValueError("employee_skills can only be specified when resource_type is 'employee'")
        if self.current_setup and self.resource_type == ResourceType.EMPLOYEE:
            raise ValueError("current_setup cannot be specified when resource_type is 'employee'")
        return self