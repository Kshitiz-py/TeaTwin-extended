"""Verifies the shared.coerce entity registry backfill (11 -> 18 entities).

Before the backfill, ``_load_entity_types`` silently returned {} for the 7 missing
entities (ResourceClass, BillOfMaterialsComponent, Process, OrderLine, Shift, Break,
Holiday), so ``/mapping/validate-types`` degraded to treating every field as str.
"""
import os
import sys

# cmsd_schema lives in the sibling cmsd-pydantic-master repo (pip-installed in Docker;
# on disk at 04_Playground/cmsd-pydantic-master/src). Add it so this test can exercise
# the lazy cmsd_schema import inside _load_entity_types without a pip install.
_CMSD_SRC = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "cmsd-pydantic-master", "src")
)
if os.path.isdir(_CMSD_SRC) and _CMSD_SRC not in sys.path:
    sys.path.insert(0, _CMSD_SRC)

from shared.coerce import _load_entity_types


# Entities that were MISSING before the backfill
_BACKFILLED = ["ResourceClass", "BillOfMaterialsComponent", "Process",
               "OrderLine", "Shift", "Break", "Holiday"]
# The original 11 that already worked
_ORIGINAL = ["Resource", "Order", "Part", "PartType", "BillOfMaterials", "ProcessPlan",
             "Calendar", "Job", "InventoryItem", "MaintenancePlan", "Connection"]


def test_backfilled_entities_resolve_to_hints():
    for entity in _BACKFILLED:
        hints = _load_entity_types(entity)
        assert hints, f"{entity} should resolve to non-empty hints after the backfill"


def test_original_entities_still_resolve():
    for entity in _ORIGINAL:
        assert _load_entity_types(entity), f"{entity} should still resolve"


def test_process_duration_hint_is_duration():
    hints = _load_entity_types("Process")
    assert "duration" in hints
    assert hints["duration"].__name__ == "Duration"


def test_unknown_entity_returns_empty_without_raising():
    assert _load_entity_types("Nonexistent") == {}