"""
CMSD Catalog — Introspects CMSD Pydantic models to produce a human-readable
entity catalog with field metadata, reference paths, and dependency info.
"""

import os
import sys
import typing
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cmsd-pydantic-master", "src"))
from cmsd_schema.resource_entities import Resource, ResourceClass
from cmsd_schema.order_entities import Order, OrderLine
from cmsd_schema.part_entities import Part, PartType, BillOfMaterials, BillOfMaterialsComponent
from cmsd_schema.calendar_entities import Calendar, Shift, Break, Holiday
from cmsd_schema.production_operations import Job
from cmsd_schema.process_planning import ProcessPlan, Process
from cmsd_schema.connection_entities import Connection
from cmsd_schema.inventory_entities import InventoryItem
from cmsd_schema.maintenance_entities import MaintenancePlan

ENTITY_REGISTRY: dict[str, type] = {
    "Resource": Resource,
    "ResourceClass": ResourceClass,
    "PartType": PartType,
    "Part": Part,
    "BillOfMaterials": BillOfMaterials,
    "BillOfMaterialsComponent": BillOfMaterialsComponent,
    "ProcessPlan": ProcessPlan,
    "Process": Process,
    "Order": Order,
    "OrderLine": OrderLine,
    "Calendar": Calendar,
    "Shift": Shift,
    "Break": Break,
    "Holiday": Holiday,
    "Connection": Connection,
    "Job": Job,
    "InventoryItem": InventoryItem,
    "MaintenancePlan": MaintenancePlan,
}


def _unwrap_optional(tp: type) -> type:
    origin = typing.get_origin(tp)
    if origin is typing.Union:
        args = typing.get_args(tp)
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return tp


def _is_required(field_info: dict) -> bool:
    """A field is required if it has no default value and is not Optional."""
    return field_info.get("required", False)


def _type_name(tp: type) -> str:
    origin = typing.get_origin(tp)
    if origin is list:
        args = typing.get_args(tp)
        if args:
            inner = _unwrap_optional(args[0])
            return f"List[{inner.__name__}]"
        return "List"
    if origin is typing.Union:
        args = typing.get_args(tp)
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return f"Optional[{_type_name(non_none[0])}]"
    if hasattr(tp, "__name__"):
        return tp.__name__
    return str(tp)


def _is_reference_type(tp: type) -> bool:
    """Check if a type is a CMSD Reference class (e.g. PartTypeReference)."""
    name = tp.__name__ if hasattr(tp, "__name__") else ""
    return name.endswith("Reference") and name != "EntityReference"


def _human_description(entity_name: str) -> str:
    """Return a human-readable description for each CMSD entity."""
    descriptions: dict[str, str] = {
        "Resource": "A production resource — machine, station, worker, conveyor, buffer, or transporter. Resources execute jobs and have capacity, availability, and status.",
        "ResourceClass": "A category or type of resource. Groups resources with similar characteristics (e.g., 'CNC Machine', 'Assembly Station'). Used to define capabilities and requirements.",
        "PartType": "A part classification — the blueprint or catalog entry for a manufactured component. Defines the part's identity, not a specific physical instance.",
        "Part": "A specific physical instance of a PartType — a real component on the shop floor with production status and location.",
        "BillOfMaterials": "The recipe for manufacturing a part. Lists all components (raw materials, sub-assemblies) needed to produce one unit of a PartType.",
        "BillOfMaterialsComponent": "A single line in a Bill of Materials — one component with a quantity. References either a PartType or specific Part instances.",
        "ProcessPlan": "The manufacturing recipe — a sequence of Process steps needed to produce a PartType. Defines routing, duration, and resource requirements.",
        "Process": "A single step within a ProcessPlan — one operation (e.g., 'Mill', 'Drill', 'Assemble') with duration, setup time, and required resources.",
        "Order": "A production order — the instruction to manufacture a quantity of parts by a due date. Contains order lines specifying what to make.",
        "OrderLine": "A line item within a production Order — specifies what PartType to produce, how many, and optionally which ProcessPlan to use.",
        "Calendar": "A factory calendar defining working days, shifts, breaks, and holidays. Controls when resources are available for production.",
        "Shift": "A work shift within a calendar — defines start/end times and which days of the week it applies to.",
        "Break": "A scheduled break within a shift — defines a start and end time when resources are unavailable.",
        "Holiday": "A non-working day in the calendar — a specific date when production is suspended.",
        "Connection": "A physical connection between two resources on the factory layout — e.g., a conveyor between Machine A and Machine B.",
        "Job": "A unit of work assigned to a resource at a specific time. Links an Order (what), a Resource (where), and a Process (how).",
        "InventoryItem": "An inventory record — tracks quantity of a PartType at a specific location.",
        "MaintenancePlan": "A planned maintenance schedule for a resource — defines preventive maintenance intervals and procedures.",
    }
    return descriptions.get(entity_name, f"CMSD {entity_name} entity.")


def _field_description(entity_name: str, field_name: str) -> str:
    """Human-readable description for a specific field."""
    field_descriptions: dict[str, dict[str, str]] = {
        "Resource": {
            "identifier": "Unique ID (e.g. 'MACH-001')",
            "name": "Human-readable name (e.g. 'CNC Mill #3')",
            "resource_type": "Type: machine, station, conveyor, buffer, employee, transporter",
            "capacity": "How many jobs this resource can handle at once",
            "availability": "Percentage (0-100) of time this resource is available",
            "current_status": "Live status: busy, idle, broken, setup, paused, underMaintenance",
            "cycle_time": "Base time per unit processed",
            "mttr": "Mean Time To Repair (hours)",
            "mtbf": "Mean Time Between Failures (hours)",
        },
        "ResourceClass": {
            "identifier": "Unique ID (e.g. 'CNC-3AXIS')",
            "name": "Human-readable name (e.g. '3-Axis CNC Machine')",
            "resource_type": "The type of resource this class represents",
        },
        "PartType": {
            "identifier": "Unique ID (e.g. 'PT-HOUSING-A')",
            "name": "Human-readable name (e.g. 'Engine Housing')",
        },
        "Order": {
            "identifier": "Unique ID (e.g. 'ORD-2026-001')",
            "status": "Order status: created, released, completed, shipped, cancelled",
            "due_date": "Date/time when the order must be fulfilled",
            "release_date": "Date/time when the order was released to production",
        },
        "Job": {
            "identifier": "Unique ID",
            "status": "Job status: created, scheduled, in_progress, completed, interrupted, cancelled",
            "priority": "Priority level (1 = highest)",
            "start_time": "Scheduled start time",
        },
        "Calendar": {
            "identifier": "Unique ID (e.g. 'FACTORY-CAL')",
            "name": "Human-readable name (e.g. 'Standard Factory Calendar')",
        },
        "Shift": {
            "identifier": "Unique ID (e.g. 'DAY-SHIFT')",
            "day_of_week": "Day of the week (1=Monday, 7=Sunday)",
            "start_time": "Shift start time (HH:MM)",
            "end_time": "Shift end time (HH:MM)",
        },
        "ProcessPlan": {
            "identifier": "Unique ID (e.g. 'PP-HOUSING')",
            "name": "Human-readable name (e.g. 'Housing Manufacturing Plan')",
        },
        "Process": {
            "identifier": "Unique ID (e.g. 'OP-10-MILL')",
            "name": "Human-readable name (e.g. 'Rough Mill Top Face')",
            "duration": "Time required to complete this process step",
            "setup_time": "Setup time before the process can start",
        },
        "BillOfMaterials": {
            "identifier": "Unique ID (e.g. 'BOM-HOUSING')",
            "name": "Human-readable name",
        },
        "BillOfMaterialsComponent": {
            "identifier": "Unique ID",
            "quantity": "Number of units of this component needed",
        },
        "InventoryItem": {
            "identifier": "Unique ID",
            "quantity": "Current quantity on hand",
        },
        "MaintenancePlan": {
            "identifier": "Unique ID",
            "name": "Human-readable name",
        },
    }
    entity_fields = field_descriptions.get(entity_name, {})
    return entity_fields.get(field_name, "")


def _entity_example(entity_name: str) -> dict:
    """Return a minimal API payload example that could map to this entity."""
    examples: dict[str, dict] = {
        "Resource": {
            "id": "MACH-001",
            "name": "CNC Mill #3",
            "type": "machine",
            "capacity": 2,
            "availability_pct": 95,
            "status": "idle",
        },
        "ResourceClass": {
            "id": "CNC-3AXIS",
            "name": "3-Axis CNC Machine",
            "type": "machine",
        },
        "PartType": {
            "part_code": "PT-HOUSING-A",
            "part_name": "Engine Housing",
        },
        "Order": {
            "order_id": "ORD-2026-001",
            "status": "released",
            "due_date": "2026-06-15T00:00:00Z",
        },
        "Calendar": {
            "id": "FACTORY-CAL",
            "name": "Standard Factory Calendar",
        },
        "Shift": {
            "id": "DAY-SHIFT",
            "day": 1,
            "start": "06:00",
            "end": "14:00",
        },
        "Job": {
            "job_id": "JOB-001",
            "status": "in_progress",
            "priority": 1,
        },
        "ProcessPlan": {
            "id": "PP-HOUSING",
            "name": "Housing Manufacturing Plan",
        },
        "Process": {
            "op_id": "OP-10",
            "op_name": "Rough Mill Top Face",
            "duration_seconds": 120,
        },
        "BillOfMaterials": {
            "bom_id": "BOM-HOUSING",
            "name": "Housing BOM",
        },
        "BillOfMaterialsComponent": {
            "comp_id": "COMP-001",
            "part_type_code": "PT-HOUSING-A",
            "quantity": 1,
        },
        "InventoryItem": {
            "item_id": "INV-001",
            "qty": 500,
        },
        "MaintenancePlan": {
            "plan_id": "MP-001",
            "plan_name": "CNC Preventive Maintenance",
        },
        "OrderLine": {
            "line_id": "LINE-001",
            "part_type_code": "PT-HOUSING-A",
            "quantity": 100,
            "status": "released",
        },
        "Break": {
            "id": "LUNCH-BREAK",
            "start": "12:00",
            "end": "12:30",
        },
        "Holiday": {
            "id": "HOL-2026-01-01",
            "date": "2026-01-01",
        },
        "Connection": {
            "id": "CONN-001",
            "from_id": "MACH-001",
            "to_id": "MACH-002",
            "type": "conveyor",
        },
    }
    return examples.get(entity_name, {"id": "example-id", "name": "Example Name"})


def _entity_hierarchy(entity_name: str) -> str:
    """Describe where this entity sits in the CMSD hierarchy."""
    hierarchy: dict[str, str] = {
        "ResourceClass": "top-level — referenced by Resource",
        "Resource": "top-level — references ResourceClass. Referenced by Job, Connection",
        "PartType": "top-level — referenced by OrderLine, BillOfMaterials, BillOfMaterialsComponent, InventoryItem",
        "Part": "top-level — references PartType. Referenced by BillOfMaterialsComponent",
        "BillOfMaterials": "top-level — references PartType or Part. Contains BillOfMaterialsComponent",
        "BillOfMaterialsComponent": "nested inside BillOfMaterials — references PartType or Part",
        "ProcessPlan": "top-level — referenced by OrderLine, Job. Contains Process",
        "Process": "nested inside ProcessPlan — references resources via JobEffortDescription",
        "Order": "top-level — contains OrderLine. Drives job creation",
        "OrderLine": "nested inside Order — references PartType, ProcessPlan",
        "Calendar": "top-level — contains Shift, Break, Holiday. Referenced by Resource, Job",
        "Shift": "nested inside Calendar",
        "Break": "nested inside Shift",
        "Holiday": "nested inside Calendar",
        "Connection": "top-level — references two Resources",
        "Job": "top-level — references Order, Resource, Process",
        "InventoryItem": "top-level — references PartType",
        "MaintenancePlan": "top-level — references Resource",
    }
    return hierarchy.get(entity_name, "top-level entity")


def _entity_references(entity_name: str) -> list[str]:
    """Return other entity types that this entity can reference in CMSD."""
    refs: dict[str, list[str]] = {
        "Resource": ["ResourceClass"],
        "Order": ["OrderLine"],
        "OrderLine": ["PartType", "ProcessPlan"],
        "BillOfMaterials": ["PartType", "Part", "BillOfMaterialsComponent"],
        "BillOfMaterialsComponent": ["PartType", "Part", "BillOfMaterialsComponent"],
        "ProcessPlan": ["Process"],
        "Process": ["Resource", "ResourceClass"],
        "Job": ["Order", "Resource", "ResourceClass", "Process"],
        "InventoryItem": ["PartType"],
        "MaintenancePlan": ["Resource"],
        "Connection": ["Resource", "ResourceClass"],
    }
    return refs.get(entity_name, [])


def build_catalog() -> dict:
    """Introspect all registered CMSD entities and return catalog metadata."""
    entities: dict[str, dict] = {}

    for entity_name, model_class in ENTITY_REGISTRY.items():
        fields: list[dict] = []

        try:
            resolved = typing.get_type_hints(model_class)
        except Exception:
            resolved = {}

        for field_name, annotation in resolved.items():
            if field_name.startswith("_"):
                continue
            inner = _unwrap_optional(annotation)
            origin = typing.get_origin(annotation)
            is_required = True
            has_default = False

            # Check if field has a default value
            if hasattr(model_class, "model_fields"):
                pydantic_field = model_class.model_fields.get(field_name)
                if pydantic_field is not None:
                    if pydantic_field.default is not None or pydantic_field.default_factory is not None:
                        has_default = True
                        is_required = False
                    # If the field is Optional, it's also not required
                    if origin is typing.Union and type(None) in (typing.get_args(annotation) or ()):
                        is_required = False

            is_ref = _is_reference_type(inner)

            fields.append({
                "name": field_name,
                "type": _type_name(annotation),
                "required": is_required,
                "has_default": has_default,
                "is_reference": is_ref,
                "description": _field_description(entity_name, field_name),
            })

        entities[entity_name] = {
            "name": entity_name,
            "description": _human_description(entity_name),
            "fields": fields,
            "references": _entity_references(entity_name),
            "hierarchy": _entity_hierarchy(entity_name),
            "example": _entity_example(entity_name),
        }

    return {"entities": entities}


# Cache at module load time — catalog is static
_catalog_cache: dict | None = None


def get_catalog() -> dict:
    global _catalog_cache
    if _catalog_cache is None:
        _catalog_cache = build_catalog()
    return _catalog_cache
