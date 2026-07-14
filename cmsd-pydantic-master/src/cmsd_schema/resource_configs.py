# =============================================================================
# RESOURCE COMPOSITION MODELS (CMSD-EXT-03)
# =============================================================================
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field

from .basic_structures import Duration, Length
from .basic_types import DecisionRule


class SourceConfig(BaseModel):
    """Configuration for SOURCE resources (Zhao 2024)"""
    feed_mode: Optional[str] = Field(None, description="Part feeding mode (e.g., 'deterministic', 'stochastic')")
    time_interval: Optional[Duration] = Field(None, description="Inter-arrival time interval")
    arrive_at_time_zero: Optional[bool] = Field(None, description="Whether a part arrives at simulation time zero")
    limit: Optional[int] = Field(None, ge=0, description="Maximum number of parts to create (None = unlimited)")
    part_creation_probability: Optional[Decimal] = Field(None, ge=0, le=1, description="Probability of part creation per interval")


class BufferConfig(BaseModel):
    """Configuration for BUFFER resources (Zhao 2024)"""
    buffer_mode: Optional[str] = Field(None, description="Buffer operating mode (e.g., 'FIFO', 'LIFO', 'priority')")
    maximum_content: Optional[int] = Field(None, ge=0, description="Maximum number of items the buffer can hold")


class DispatcherConfig(BaseModel):
    """Configuration for DISPATCHER resources (Zhao 2024)"""
    resource_priority: Optional[int] = Field(None, description="Priority of this dispatcher relative to others")
    queue_strategy: Optional[DecisionRule] = Field(None, description="Queue sequencing strategy")


class ArticulatedRobotConfig(BaseModel):
    """Configuration for ARTICULATED_ROBOT resources (Zhao 2024)"""
    inverse_kinematics: Optional[str] = Field(None, description="Inverse kinematics solver/algorithm identifier")
    joint_axes: Optional[List[str]] = Field(None, description="List of joint axis identifiers")
    base_frame: Optional[str] = Field(None, description="Robot base coordinate frame identifier")
    tcp_frame: Optional[str] = Field(None, description="Tool center point (TCP) frame identifier")
    tool_connection_interface: Optional[str] = Field(None, description="Tool connection interface type")
    joint_speeds: Optional[List[Decimal]] = Field(None, description="Maximum speeds per joint (rad/s or deg/s)")
    joint_accelerations: Optional[List[Decimal]] = Field(None, description="Maximum accelerations per joint")
    joint_decelerations: Optional[List[Decimal]] = Field(None, description="Maximum decelerations per joint")


class MobileRobotConfig(BaseModel):
    """Configuration for MOBILE_ROBOT / AGV resources (Zhao 2024)"""
    obstacle_avoidance: Optional[bool] = Field(None, description="Whether obstacle avoidance is enabled")
    exclude_obstacle_components: Optional[List[str]] = Field(
        None, description="Component identifiers excluded from obstacle detection"
    )
    pick_offset: Optional[Length] = Field(None, description="Offset applied when picking a load")
    place_offset: Optional[Length] = Field(None, description="Offset applied when placing a load")


class WarehouseConfig(BaseModel):
    """Configuration for AUTOMATED_WAREHOUSE (AKL) resources (sim_param_schema)"""
    access_time: Optional[Duration] = Field(None, description="Time to access a storage location")
    load_time: Optional[Duration] = Field(None, description="Time to load a carrier into the warehouse")
    unload_time: Optional[Duration] = Field(None, description="Time to unload a carrier from the warehouse")
    retrieval_stations: Optional[int] = Field(None, ge=0, description="Number of retrieval/I-O stations")
    empty_carrier_buffer_slots: Optional[int] = Field(None, ge=0, description="Buffer slots for empty carriers")


class GateConfig(BaseModel):
    """Configuration for GATE (TorSchleuse) resources (sim_param_schema)"""
    open_duration: Optional[Duration] = Field(None, description="Time for the gate to open")
    close_duration: Optional[Duration] = Field(None, description="Time for the gate to close")
    cycle_duration: Optional[Duration] = Field(None, description="Full open-close cycle duration")
    passage_capacity: Optional[int] = Field(None, ge=0, description="Number of vehicles that can pass per cycle")


class ChargingStationConfig(BaseModel):
    """Configuration for CHARGING_STATION (Ladestation) resources (sim_param_schema)"""
    setup_time: Optional[Duration] = Field(None, description="Setup/connection time before charging begins")


class EnergyModel(BaseModel):
    """Battery and energy parameters for AGV/mobile resources (sim_param_schema)"""
    battery_capacity_kwh: Optional[Decimal] = Field(None, ge=0, description="Battery capacity in kilowatt-hours")
    charge_current_ampere: Optional[Decimal] = Field(None, ge=0, description="Charging current in amperes")
    charge_duration: Optional[Duration] = Field(None, description="Time required for a full charge")
    standby_consumption_ampere: Optional[Decimal] = Field(None, ge=0, description="Current draw while standing by (A)")
    drive_consumption_ampere: Optional[Decimal] = Field(None, ge=0, description="Current draw while driving (A)")
    battery_swap_duration: Optional[Duration] = Field(None, description="Time required to swap the battery")


class SpeedProfile(BaseModel):
    """Multi-context speed profile for AGV/mobile resources (sim_param_schema)

    Supersedes the single ``speed`` field from Zhao 2024.
    All values are in meters per second unless a unit is specified elsewhere.
    """
    straight: Optional[Decimal] = Field(None, ge=0, description="Speed on straight segments (m/s)")
    curve: Optional[Decimal] = Field(None, ge=0, description="Speed on curved segments (m/s)")
    bay: Optional[Decimal] = Field(None, ge=0, description="Speed inside a bay / narrow aisle (m/s)")
    loaded: Optional[Decimal] = Field(None, ge=0, description="Speed when carrying a load (m/s)")
    default: Optional[Decimal] = Field(None, ge=0, description="Default/fallback speed (m/s)")
