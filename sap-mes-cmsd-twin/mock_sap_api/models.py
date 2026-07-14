"""
SQLAlchemy ORM models reflecting the factory_digital_twin MySQL schema.
Used by both Mock SAP API and Mock MES API.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, Time, Date,
    ForeignKey, Enum as SQLEnum, Boolean, DECIMAL, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from datetime import datetime, date, time
from typing import Optional, List

Base = declarative_base()


# =============================================================================
# SAP MASTER DATA MODELS
# =============================================================================

class ResourceClass(Base):
    __tablename__ = "resource_classes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    resource_type = Column(String(50), nullable=False)
    hourly_rate = Column(Float, nullable=True)
    size_length = Column(Float, nullable=True)
    size_width = Column(Float, nullable=True)
    size_height = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    resources = relationship("Resource", back_populates="resource_class_ref", lazy="selectin")


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    resource_class_id = Column(Integer, ForeignKey("resource_classes.id", ondelete="SET NULL"), nullable=True)
    resource_type = Column(String(50), nullable=False)
    capacity = Column(Integer, nullable=True)
    availability = Column(Float, nullable=True)
    mttr_seconds = Column(Integer, nullable=True)
    mtbf_seconds = Column(Integer, nullable=True)
    mcbf = Column(Integer, nullable=True)
    reliability = Column(Float, nullable=True)
    cycle_time_seconds = Column(Integer, nullable=True)
    desired_replenishment_time_seconds = Column(Integer, nullable=True)
    transport_capacity = Column(Integer, nullable=True)
    tow_bar_length = Column(Float, nullable=True)
    worker_count = Column(Integer, nullable=True)
    decision_rule = Column(String(50), nullable=True)
    routing_rule = Column(String(50), nullable=True)
    size_length = Column(Float, nullable=True)
    size_width = Column(Float, nullable=True)
    size_height = Column(Float, nullable=True)
    hourly_rate = Column(Float, nullable=True)
    buffer_type = Column(String(50), nullable=True)
    buffer_capacity = Column(Integer, nullable=True)
    conveyor_speed = Column(Float, nullable=True)
    conveyor_length = Column(Float, nullable=True)
    conveyor_accumulating = Column(Boolean, nullable=True, default=True)
    energy_working_kw = Column(Float, nullable=True)
    energy_standby_kw = Column(Float, nullable=True)
    energy_failed_kw = Column(Float, nullable=True)
    energy_off_kw = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    resource_class_ref = relationship("ResourceClass", back_populates="resources", lazy="selectin")
    resource_status = relationship("ResourceStatus", back_populates="resource_ref", uselist=False, lazy="selectin")
    placements = relationship("Placement", back_populates="resource_ref", lazy="selectin")


class PartType(Base):
    __tablename__ = "part_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    size_length = Column(Float, nullable=True)
    size_width = Column(Float, nullable=True)
    size_height = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    color = Column(String(30), nullable=True)
    shape_3d = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    boms = relationship("BillOfMaterials", back_populates="part_type_ref", lazy="selectin")
    process_plans = relationship("ProcessPlan", back_populates="part_type_ref", lazy="selectin")


class Part(Base):
    __tablename__ = "parts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(100), unique=True, nullable=False, index=True)
    part_type_id = Column(Integer, ForeignKey("part_types.id", ondelete="CASCADE"), nullable=False)
    production_status = Column(String(50), nullable=True, default="unknown")
    location_x = Column(Float, nullable=True)
    location_y = Column(Float, nullable=True)
    location_z = Column(Float, nullable=True)
    lot_number = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    part_type_ref = relationship("PartType", lazy="selectin")


class BillOfMaterials(Base):
    __tablename__ = "bills_of_materials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    part_type_id = Column(Integer, ForeignKey("part_types.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    part_type_ref = relationship("PartType", back_populates="boms", lazy="selectin")
    components = relationship("BOMComponent", back_populates="bom_ref", lazy="selectin",
                              primaryjoin="BillOfMaterials.id == BOMComponent.bom_id")


class BOMComponent(Base):
    __tablename__ = "bom_components"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(100), unique=True, nullable=False, index=True)
    bom_id = Column(Integer, ForeignKey("bills_of_materials.id", ondelete="CASCADE"), nullable=False)
    part_type_id = Column(Integer, ForeignKey("part_types.id", ondelete="SET NULL"), nullable=True)
    quantity = Column(Float, nullable=False, default=1.0)
    parent_component_id = Column(Integer, ForeignKey("bom_components.id", ondelete="CASCADE"), nullable=True)
    sequence_order = Column(Integer, nullable=True, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    bom_ref = relationship("BillOfMaterials", back_populates="components", lazy="selectin")
    part_type_ref = relationship("PartType", lazy="selectin")
    children = relationship("BOMComponent", back_populates="parent", lazy="selectin",
                            foreign_keys=[parent_component_id])
    parent = relationship("BOMComponent", back_populates="children", remote_side=[id], lazy="selectin")


class ProcessPlan(Base):
    __tablename__ = "process_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    part_type_id = Column(Integer, ForeignKey("part_types.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    part_type_ref = relationship("PartType", back_populates="process_plans", lazy="selectin")
    processes = relationship("Process", back_populates="process_plan_ref", lazy="selectin",
                             primaryjoin="ProcessPlan.id == Process.process_plan_id")


class Process(Base):
    __tablename__ = "processes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    process_plan_id = Column(Integer, ForeignKey("process_plans.id", ondelete="CASCADE"), nullable=False)
    sequence_order = Column(Integer, nullable=False, default=0)
    duration_seconds = Column(Integer, nullable=True)
    setup_time_seconds = Column(Integer, nullable=True)
    load_time_seconds = Column(Integer, nullable=True)
    unload_time_seconds = Column(Integer, nullable=True)
    pick_time_seconds = Column(Integer, nullable=True)
    place_time_seconds = Column(Integer, nullable=True)
    group_type = Column(String(50), nullable=True, default="sequence")
    parent_process_id = Column(Integer, ForeignKey("processes.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    process_plan_ref = relationship("ProcessPlan", back_populates="processes", lazy="selectin")
    process_resources = relationship("ProcessResource", back_populates="process_ref", lazy="selectin")


class ProcessResource(Base):
    __tablename__ = "process_resources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    process_id = Column(Integer, ForeignKey("processes.id", ondelete="CASCADE"), nullable=False)
    resource_id = Column(Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False)
    minimum_number = Column(Integer, nullable=True, default=1)
    maximum_number = Column(Integer, nullable=True, default=1)
    created_at = Column(DateTime, server_default=func.now())

    process_ref = relationship("Process", back_populates="process_resources", lazy="selectin")
    resource_ref = relationship("Resource", lazy="selectin")


class Calendar(Base):
    __tablename__ = "calendars"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    production_days_per_year = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    shifts = relationship("Shift", back_populates="calendar_ref", lazy="selectin")
    holidays = relationship("Holiday", back_populates="calendar_ref", lazy="selectin")
    shutdown_periods = relationship("ShutdownPeriod", back_populates="calendar_ref", lazy="selectin")


class Shift(Base):
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(100), unique=True, nullable=False, index=True)
    calendar_id = Column(Integer, ForeignKey("calendars.id", ondelete="CASCADE"), nullable=False)
    day_of_week = Column(String(20), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    calendar_ref = relationship("Calendar", back_populates="shifts", lazy="selectin")
    breaks = relationship("Break", back_populates="shift_ref", lazy="selectin")


class Break(Base):
    __tablename__ = "breaks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(100), unique=True, nullable=False, index=True)
    shift_id = Column(Integer, ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    name = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    shift_ref = relationship("Shift", back_populates="breaks", lazy="selectin")


class Holiday(Base):
    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(100), unique=True, nullable=False, index=True)
    calendar_id = Column(Integer, ForeignKey("calendars.id", ondelete="CASCADE"), nullable=False)
    holiday_date = Column(Date, nullable=False)
    name = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    calendar_ref = relationship("Calendar", back_populates="holidays", lazy="selectin")


class ShutdownPeriod(Base):
    __tablename__ = "shutdown_periods"

    id = Column(Integer, primary_key=True, autoincrement=True)
    calendar_id = Column(Integer, ForeignKey("calendars.id", ondelete="CASCADE"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    calendar_ref = relationship("Calendar", back_populates="shutdown_periods", lazy="selectin")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(String(50), nullable=True, default="created")
    due_date = Column(DateTime, nullable=True)
    release_date = Column(DateTime, nullable=True)
    priority = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    order_lines = relationship("OrderLine", back_populates="order_ref", lazy="selectin")


class OrderLine(Base):
    __tablename__ = "order_lines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(100), unique=True, nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    part_type_id = Column(Integer, ForeignKey("part_types.id", ondelete="SET NULL"), nullable=True)
    quantity = Column(Integer, nullable=False, default=1)
    due_date = Column(DateTime, nullable=True)
    release_date = Column(DateTime, nullable=True)
    process_plan_id = Column(Integer, ForeignKey("process_plans.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), nullable=True, default="created")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    order_ref = relationship("Order", back_populates="order_lines", lazy="selectin")
    part_type_ref = relationship("PartType", lazy="selectin")
    process_plan_ref = relationship("ProcessPlan", lazy="selectin")


class Layout(Base):
    __tablename__ = "layouts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    coordinate_system = Column(String(50), nullable=True, default="upperLeftBased")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    placements = relationship("Placement", back_populates="layout_ref", lazy="selectin")


class Placement(Base):
    __tablename__ = "placements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    layout_id = Column(Integer, ForeignKey("layouts.id", ondelete="CASCADE"), nullable=False)
    resource_id = Column(Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False)
    x = Column(Float, nullable=False, default=0.0)
    y = Column(Float, nullable=False, default=0.0)
    z = Column(Float, nullable=False, default=0.0)
    rotation_x_deg = Column(Float, nullable=True, default=0.0)
    rotation_y_deg = Column(Float, nullable=True, default=0.0)
    rotation_z_deg = Column(Float, nullable=True, default=0.0)
    scale_x_percent = Column(Float, nullable=True, default=100.0)
    scale_y_percent = Column(Float, nullable=True, default=100.0)
    scale_z_percent = Column(Float, nullable=True, default=100.0)
    created_at = Column(DateTime, server_default=func.now())

    layout_ref = relationship("Layout", back_populates="placements", lazy="selectin")
    resource_ref = relationship("Resource", back_populates="placements", lazy="selectin")


class Connection(Base):
    __tablename__ = "connections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(100), unique=True, nullable=False, index=True)
    from_resource_id = Column(Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False)
    to_resource_id = Column(Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False)
    connection_type = Column(String(50), nullable=True, default="output")
    connection_name = Column(String(50), nullable=True, default="conveyor")
    created_at = Column(DateTime, server_default=func.now())

    from_resource = relationship("Resource", foreign_keys=[from_resource_id], lazy="selectin")
    to_resource = relationship("Resource", foreign_keys=[to_resource_id], lazy="selectin")


# =============================================================================
# MES OPERATIONAL DATA MODELS
# =============================================================================

class ResourceStatus(Base):
    __tablename__ = "resource_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_id = Column(Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False, unique=True)
    status = Column(String(50), nullable=False, default="idle")
    current_setup = Column(String(100), nullable=True)
    current_job_id = Column(Integer, nullable=True)
    uptime_seconds = Column(Integer, nullable=True, default=0)
    parts_processed_today = Column(Integer, nullable=True, default=0)
    last_status_change = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime, server_default=func.now())

    resource_ref = relationship("Resource", back_populates="resource_status", lazy="selectin")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(100), unique=True, nullable=False, index=True)
    order_line_id = Column(Integer, ForeignKey("order_lines.id", ondelete="SET NULL"), nullable=True)
    process_plan_id = Column(Integer, ForeignKey("process_plans.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), nullable=False, default="released")
    priority = Column(String(50), nullable=True)
    release_date = Column(DateTime, nullable=True)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    current_process_id = Column(Integer, ForeignKey("processes.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    order_line_ref = relationship("OrderLine", lazy="selectin")
    process_plan_ref = relationship("ProcessPlan", lazy="selectin")
    current_process_ref = relationship("Process", lazy="selectin")
    job_efforts = relationship("JobEffort", back_populates="job_ref", lazy="selectin")


class JobEffort(Base):
    __tablename__ = "job_effort"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    effort_type = Column(String(50), nullable=False, default="planned")
    processing_time_seconds = Column(Integer, nullable=True)
    setup_time_seconds = Column(Integer, nullable=True)
    update_time = Column(DateTime, server_default=func.now())
    parts_produced = Column(Integer, nullable=True, default=0)
    parts_scrapped = Column(Integer, nullable=True, default=0)
    created_at = Column(DateTime, server_default=func.now())

    job_ref = relationship("Job", back_populates="job_efforts", lazy="selectin")


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(100), unique=True, nullable=False, index=True)
    part_type_id = Column(Integer, ForeignKey("part_types.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Float, nullable=False, default=0.0)
    min_threshold = Column(Float, nullable=True)
    max_threshold = Column(Float, nullable=True)
    location_id = Column(Integer, ForeignKey("resources.id", ondelete="SET NULL"), nullable=True)
    lot_number = Column(String(50), nullable=True)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime, server_default=func.now())

    part_type_ref = relationship("PartType", lazy="selectin")
    location_ref = relationship("Resource", lazy="selectin")


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(100), unique=True, nullable=False, index=True)
    resource_id = Column(Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False)
    incident_type = Column(String(100), nullable=False)
    severity = Column(String(50), nullable=True, default="medium")
    status = Column(String(50), nullable=True, default="open")
    start_time = Column(DateTime, nullable=False, server_default=func.now())
    end_time = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    resource_ref = relationship("Resource", lazy="selectin")


class SkillDefinition(Base):
    __tablename__ = "skill_definitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class EmployeeSkill(Base):
    __tablename__ = "employee_skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_id = Column(Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skill_definitions.id", ondelete="CASCADE"), nullable=False)
    proficiency_level = Column(String(50), nullable=True, default="intermediate")
    created_at = Column(DateTime, server_default=func.now())

    resource_ref = relationship("Resource", lazy="selectin")
    skill_ref = relationship("SkillDefinition", lazy="selectin")


class ChangeEvent(Base):
    __tablename__ = "change_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(50), nullable=False)
    entity_identifier = Column(String(100), nullable=False)
    entity_name = Column(String(255), nullable=True)
    field_name = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    event_type = Column(String(50), nullable=False, default="updated")
    detected_at = Column(DateTime, server_default=func.now())
    poll_cycle_id = Column(String(50), nullable=True)
    acknowledged = Column(Boolean, nullable=True, default=False)


class PollCycle(Base):
    __tablename__ = "poll_cycles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cycle_id = Column(String(50), unique=True, nullable=False)
    start_time = Column(DateTime, server_default=func.now())
    end_time = Column(DateTime, nullable=True)
    sap_api_calls = Column(Integer, nullable=True, default=0)
    mes_api_calls = Column(Integer, nullable=True, default=0)
    changes_detected = Column(Integer, nullable=True, default=0)
    status = Column(String(50), nullable=True, default="running")
    error_message = Column(Text, nullable=True)