"""Deterministic SAP unit-code -> CMSD unit + conversion-factor table.

Read ONLY by deterministic runtime code (``cmsd_twin_service.mapping_factory``).
The LLM never uses this module. The LLM proposes ``unit_from_field`` — a
metadata-level decision about *which* companion OData property holds the SAP
unit code. At runtime the factory reads that property's actual *value* from the
fetched row and resolves the conversion factor here. This keeps unit values
(in-factory row data) out of the LLM prompt entirely.

CMSD ``TimeUnit`` values are lowercase strings (see
``cmsd_schema.basic_types.TimeUnit``): second, minute, hour, day, week, month,
year. ``mapping_factory._coerce_type`` builds ``Duration(unit="second", value=...)``,
so the default target is ``"second"``.

The table currently covers the SAP internal time-unit codes confirmed against the
real system (SEC/MIN/HUR/DAY — the same set used by the 03_Pipeline validator).
Weight/length/currency codes are a deliberate coverage gap: an unknown code
returns ``None`` and the runtime leaves the value in its raw SAP unit, recording a
``field_warning`` rather than guessing. Extend the table as more units are needed.
"""
from __future__ import annotations

# SAP unit code -> (cmsd TimeUnit name, factor_to_seconds)
_TIME_UNITS: dict[str, tuple[str, float]] = {
    "SEC": ("second", 1.0),
    "MIN": ("minute", 60.0),
    "HUR": ("hour", 3600.0),
    "DAY": ("day", 86400.0),
}

_CMSD_TIME_TO_SECONDS: dict[str, float] = {
    "second": 1.0,
    "minute": 60.0,
    "hour": 3600.0,
    "day": 86400.0,
    "week": 604800.0,
    "month": 2629800.0,   # ~30.44 days
    "year": 31557600.0,   # ~365.25 days
}


def convert_factor(sap_unit_code: str, target_unit: str = "second") -> float | None:
    """Multiplicative factor to convert a value FROM the SAP unit code TO ``target_unit``.

    Returns ``None`` if the SAP unit or the target unit is unknown (a coverage gap).
    The runtime treats ``None`` as "leave the value in its raw SAP unit" and emits a
    ``field_warning`` — it never guesses a factor.
    """
    if not sap_unit_code:
        return None
    src = _TIME_UNITS.get(str(sap_unit_code).strip().upper())
    if src is None:
        return None
    _cmsd_name, factor_to_seconds = src
    target_secs = _CMSD_TIME_TO_SECONDS.get(str(target_unit).strip().lower())
    if target_secs is None:
        return None
    return factor_to_seconds / target_secs


def unit_name_for(sap_unit_code: str) -> str | None:
    """The CMSD ``TimeUnit`` name (e.g. ``"minute"``) for a SAP unit code, or ``None``."""
    if not sap_unit_code:
        return None
    src = _TIME_UNITS.get(str(sap_unit_code).strip().upper())
    return src[0] if src else None