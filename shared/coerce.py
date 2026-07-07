"""
Shared CMSD type coercion logic.
Used by both the AI agent (mapping validation) and the CMSD Twin Service (runtime factory).
Introspects Pydantic models directly — no hardcoded type maps.
"""

import sys, os, typing
from decimal import Decimal
from typing import Any


def _unwrap_optional(tp: type) -> type:
    """If tp is Optional[X], return X. Otherwise return tp unchanged."""
    origin = typing.get_origin(tp)
    if origin is typing.Union:
        args = typing.get_args(tp)
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return tp


def _get_pydantic_field_types(entity_class: type) -> dict[str, type]:
    """Introspect a Pydantic model to get field_name -> unwrapped type mapping."""
    hints = {}
    for field_name, field_info in entity_class.model_fields.items():
        annotation = field_info.annotation
        if annotation is not None:
            hints[field_name] = _unwrap_optional(annotation)
    return hints


# Lazy-loaded cache of entity_name -> field_types
_ENTITY_TYPE_CACHE: dict[str, dict[str, type]] = {}


def _load_entity_types(entity_type: str) -> dict[str, type]:
    """Load field types for a CMSD entity by introspecting its Pydantic model."""
    if entity_type in _ENTITY_TYPE_CACHE:
        return _ENTITY_TYPE_CACHE[entity_type]

    # Map entity names to their model classes
    try:
        base = os.path.join(os.path.dirname(__file__), "..", "cmsd-pydantic-master", "src")
        sys.path.insert(0, base)
        from cmsd_schema.resource_entities import Resource, ResourceClass
        from cmsd_schema.order_entities import Order, OrderLine
        from cmsd_schema.part_entities import Part, PartType, BillOfMaterials, BillOfMaterialsComponent
        from cmsd_schema.process_planning import ProcessPlan, Process
        from cmsd_schema.calendar_entities import Calendar, Shift, Break, Holiday
        from cmsd_schema.production_operations import Job
        from cmsd_schema.inventory_entities import InventoryItem
        from cmsd_schema.maintenance_entities import MaintenancePlan
        from cmsd_schema.connection_entities import Connection

        REGISTRY: dict[str, type] = {
            "Resource": Resource,
            "ResourceClass": ResourceClass,
            "Order": Order,
            "OrderLine": OrderLine,
            "Part": Part,
            "PartType": PartType,
            "BillOfMaterials": BillOfMaterials,
            "BillOfMaterialsComponent": BillOfMaterialsComponent,
            "ProcessPlan": ProcessPlan,
            "Process": Process,
            "Calendar": Calendar,
            "Shift": Shift,
            "Break": Break,
            "Holiday": Holiday,
            "Job": Job,
            "InventoryItem": InventoryItem,
            "MaintenancePlan": MaintenancePlan,
            "Connection": Connection,
        }

        model_class = REGISTRY.get(entity_type)
        if model_class:
            hints = _get_pydantic_field_types(model_class)
            _ENTITY_TYPE_CACHE[entity_type] = hints
            return hints
    except Exception:
        pass

    return {}


def try_coerce(value: Any, expected_type: type) -> tuple[bool, str, Any]:
    """
    Try to coerce a raw value to the given Python type.
    Returns (success, error_message, coerced_value).
    """
    if value is None:
        return (True, "", None)

    # Unwrap Optional
    inner = _unwrap_optional(expected_type)
    type_name = getattr(inner, "__name__", str(inner))

    try:
        if inner is str:
            return (True, "", str(value))
        if inner is int:
            return (True, "", int(float(str(value))))
        if inner is float:
            return (True, "", float(str(value)))
        if inner is Decimal:
            return (True, "", Decimal(str(value)))
        if inner is bool:
            if isinstance(value, str):
                return (True, "", value.lower() in ("true", "1", "yes"))
            return (True, "", bool(value))

        # Enum types (ResourceType, OrderStatus, etc.)
        if isinstance(inner, type) and hasattr(inner, "__members__"):
            return (True, "", str(value))

        # Duration — expect numeric seconds
        if type_name == "Duration":
            float(str(value))  # validate it's numeric
            return (True, "", f"Duration(second, {value})")

        # Unknown type — pass through
        return (True, "", value)

    except (ValueError, TypeError) as e:
        return (False, f"Cannot coerce '{value}' to {type_name}: {e}", None)
    except Exception as e:
        return (False, str(e), None)


def validate_mapping_types(mapping: dict, entity_type: str) -> dict:
    """
    Validate all fields in a mapping against Pydantic model field types.
    Introspects the actual CMSD model — no hardcoded type hints.
    Returns per-field validation results with fix suggestions.
    """
    field_types = _load_entity_types(entity_type)
    field_map = mapping.get("mapping", {})
    results: dict[str, dict] = {}

    for field_name, config in field_map.items():
        if not isinstance(config, dict):
            continue

        raw_value = config.get("raw_value", config.get("sample_value", ""))
        api_path = config.get("api_path", "")
        expected_type = field_types.get(field_name, str)
        expected_name = getattr(expected_type, "__name__", str(expected_type))

        # Apply transformation if present
        effective_value = raw_value
        transform = config.get("transformation")
        if transform and isinstance(transform, dict) and transform.get("type", "none") != "none":
            from shared.transform import execute_transformation
            result = execute_transformation(str(raw_value) if raw_value is not None else "", transform)
            if result.get("success"):
                effective_value = result["converted_value"]

        ok, error, _ = try_coerce(effective_value, expected_type)

        # Determine if this type is unit-sensitive
        unit_sensitive = expected_name in ("Duration", "Decimal")
        assumed_unit = ""
        if expected_name == "Duration":
            assumed_unit = "second"
        elif expected_name == "Decimal":
            assumed_unit = "raw numeric value"

        suggestion = ""
        if not ok:
            suggestion = _suggest_fix(field_name, expected_name, raw_value)

        results[field_name] = {
            "api_path": api_path,
            "raw_value": raw_value,
            "expected_type": expected_name,
            "valid": ok,
            "error": error,
            "suggestion": suggestion,
            "unit_sensitive": unit_sensitive,
            "assumed_unit": assumed_unit,
        }

    return {
        "entity_type": entity_type,
        "fields": results,
        "all_valid": all(r["valid"] for r in results.values()),
    }


def _suggest_fix(field_name: str, expected_type: str, raw_value: Any) -> str:
    """Generate a deterministic fix suggestion."""
    if expected_type == "Duration" and raw_value is not None:
        try:
            seconds = float(str(raw_value))
            if seconds >= 3600:
                return f"Use 'divide_by' transform with divisor=3600 ({seconds}s → hours)"
            return "Use 'to_integer' transform or set a default value"
        except ValueError:
            pass
    if expected_type == "Decimal" and raw_value is not None:
        return "Use 'to_decimal' transform (e.g. precision=2)"
    if expected_type == "int" and raw_value is not None:
        try:
            float(str(raw_value))
            return "Use 'to_integer' transform"
        except ValueError:
            pass
    if raw_value is None:
        return "Set a 'default_value' transform or fix API path"
    return f"Value cannot be coerced to {expected_type}"
