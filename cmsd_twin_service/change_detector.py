"""
ChangeDetector — Compares two CMSDDocuments and produces a list of ChangeEvent dicts.
Uses entity-identifier-based diffing (not array position), critical for correctness.
"""

import json
from typing import Any
from datetime import datetime, timezone


class ChangeEvent:
    """Represents a single field-level change between two snapshots."""
    def __init__(self, entity_type: str, entity_identifier: str, entity_name: str,
                 field_name: str, old_value: Any, new_value: Any, event_type: str = "updated"):
        self.entity_type = entity_type
        self.entity_identifier = entity_identifier
        self.entity_name = entity_name
        self.field_name = field_name
        self.old_value = _serialize(old_value)
        self.new_value = _serialize(new_value)
        self.event_type = event_type
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "entity_type": self.entity_type,
            "entity_identifier": self.entity_identifier,
            "entity_name": self.entity_name,
            "field_name": self.field_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
        }


class ChangeDetector:
    """Deep-compares two CMSDDocument snapshots and returns structured ChangeEvents."""

    # Fields whose changes we publish (subset of full CMSD for meaningful events)
    TRACKED_FIELDS = {
        "resource": ["current_status", "availability", "capacity", "cycle_time", "mttr"],
        "order": ["status", "due_date"],
        "job": ["status", "current_process_id"],
        "part": ["production_status", "location"],
        "inventory_item": ["quantity"],
    }

    def diff(self, old_doc, new_doc) -> list[ChangeEvent]:
        events: list[ChangeEvent] = []

        events.extend(self._diff_list("resource", old_doc.resources if old_doc else [], new_doc.resources))
        events.extend(self._diff_list("order", old_doc.orders if old_doc else [], new_doc.orders))
        events.extend(self._diff_list("job", old_doc.jobs if old_doc else [], new_doc.jobs))
        events.extend(self._diff_list("part", old_doc.parts if old_doc else [], new_doc.parts))
        events.extend(self._diff_list("inventory_item", old_doc.inventory_items if old_doc else [], new_doc.inventory_items))

        return events

    def _diff_list(self, entity_type: str, old_list: list, new_list: list) -> list[ChangeEvent]:
        events: list[ChangeEvent] = []

        old_by_id = {item.identifier: item for item in old_list}
        new_by_id = {item.identifier: item for item in new_list}

        tracked = self.TRACKED_FIELDS.get(entity_type, [])

        # Detect updates and creations
        for ident, new_item in new_by_id.items():
            if ident not in old_by_id:
                # Created
                events.append(ChangeEvent(
                    entity_type=entity_type,
                    entity_identifier=ident,
                    entity_name=getattr(new_item, "name", ident),
                    field_name="__all__",
                    old_value=None,
                    new_value="created",
                    event_type="created",
                ))
            else:
                old_item = old_by_id[ident]
                for field in tracked:
                    old_val = getattr(old_item, field, None)
                    new_val = getattr(new_item, field, None)
                    if _serialize(old_val) != _serialize(new_val):
                        events.append(ChangeEvent(
                            entity_type=entity_type,
                            entity_identifier=ident,
                            entity_name=getattr(new_item, "name", ident),
                            field_name=field,
                            old_value=old_val,
                            new_value=new_val,
                            event_type="updated",
                        ))

        # Detect deletions
        for ident in old_by_id:
            if ident not in new_by_id:
                old_item = old_by_id[ident]
                events.append(ChangeEvent(
                    entity_type=entity_type,
                    entity_identifier=ident,
                    entity_name=getattr(old_item, "name", ident),
                    field_name="__all__",
                    old_value="existed",
                    new_value=None,
                    event_type="deleted",
                ))

        return events


def _serialize(value: Any) -> str | None:
    """Convert any value to a comparable string representation."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    if hasattr(value, "value"):  # Enum
        return str(value.value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    try:
        return json.dumps(value, default=str)
    except (TypeError, ValueError):
        return str(value)