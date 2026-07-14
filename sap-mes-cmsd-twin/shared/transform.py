"""
Shared transformation logic for CMSD field mappings.
Used by both the AI agent (mapping preview) and the CMSD Twin Service (runtime factory).
"""

import json
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

TRANSFORMATION_PRESETS = {
    "none": {"label": "None", "params": []},
    "unit_conversion": {"label": "Unit Conversion", "params": ["from", "to", "factor"]},
    "enum_map": {"label": "Enum Map", "params": ["mapping"]},
    "to_decimal": {"label": "To Decimal", "params": ["precision"]},
    "to_integer": {"label": "To Integer", "params": []},
    "string_template": {"label": "String Template", "params": ["template"]},
    "divide_by": {"label": "Divide By", "params": ["divisor"]},
    "multiply_by": {"label": "Multiply By", "params": ["factor"]},
    "default_value": {"label": "Default Value", "params": ["value"]},
}

VALID_TRANSFORMATIONS = set(TRANSFORMATION_PRESETS.keys())


def validate_transformation(transform: dict | None) -> dict | None:
    """Validate a transformation object. Returns error dict if invalid, None if valid."""
    if transform is None:
        return None
    ttype = transform.get("type", "none")
    if ttype not in VALID_TRANSFORMATIONS:
        return {"error": f"Unknown transformation type: {ttype}",
                "valid_types": sorted(VALID_TRANSFORMATIONS)}
    required = TRANSFORMATION_PRESETS.get(ttype, {}).get("params", [])
    params = transform.get("params", {})
    missing = [p for p in required if p not in params or params[p] == ""]
    if missing:
        return {"error": f"'{ttype}' requires params: {', '.join(required)}",
                "missing_params": missing}
    return None


def execute_transformation(raw_value: str, transformation: dict | None) -> dict:
    """Deterministically execute a transformation. No LLM involved."""
    if not transformation or transformation.get("type", "none") == "none":
        return {"converted_value": raw_value, "success": True, "error": None}

    ttype = transformation.get("type", "none")
    params = transformation.get("params", {})

    try:
        if ttype == "unit_conversion":
            factor = float(params.get("factor", 1))
            converted = float(raw_value) * factor
            return {"converted_value": str(converted), "success": True, "error": None}

        elif ttype == "enum_map":
            mapping_str = params.get("mapping", "{}")
            mapping = json.loads(mapping_str) if isinstance(mapping_str, str) else mapping_str
            return {"converted_value": str(mapping.get(raw_value, raw_value)),
                    "success": True, "error": None}

        elif ttype == "to_decimal":
            precision = int(params.get("precision", 2))
            d = Decimal(raw_value)
            quantized = d.quantize(Decimal(10) ** -precision, rounding=ROUND_HALF_UP)
            return {"converted_value": str(quantized), "success": True, "error": None}

        elif ttype == "to_integer":
            converted = int(float(raw_value))
            return {"converted_value": str(converted), "success": True, "error": None}

        elif ttype == "string_template":
            template = params.get("template", "{value}")
            return {"converted_value": template.replace("{value}", raw_value),
                    "success": True, "error": None}

        elif ttype == "divide_by":
            divisor = float(params.get("divisor", 1))
            if divisor == 0:
                return {"converted_value": None, "success": False,
                        "error": "Division by zero"}
            return {"converted_value": str(float(raw_value) / divisor),
                    "success": True, "error": None}

        elif ttype == "multiply_by":
            factor = float(params.get("factor", 1))
            return {"converted_value": str(float(raw_value) * factor),
                    "success": True, "error": None}

        elif ttype == "default_value":
            return {"converted_value": str(params.get("value", raw_value)),
                    "success": True, "error": None}

        else:
            return {"converted_value": None, "success": False,
                    "error": f"Unknown transformation type: {ttype}"}

    except (ValueError, TypeError) as e:
        return {"converted_value": None, "success": False,
                "error": f"Invalid value for '{ttype}': {e}"}
    except Exception as e:
        return {"converted_value": None, "success": False, "error": str(e)}
