"""
MappingDrivenFactory — builds CMSD entity instances from mapping configuration.
Reads .agent-mappings/*.json, calls APIs, resolves field paths, applies
transformations, and constructs typed CMSD Pydantic model instances.
"""

import asyncio
import json
import logging
import os
import re
import sys
import typing
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cmsd-pydantic-master", "src"))
from cmsd_schema.cmsd_document import CMSDDocument
from cmsd_schema.resource_entities import Resource, ResourceClass
from cmsd_schema.order_entities import Order, OrderLine
from cmsd_schema.part_entities import Part, PartType, BillOfMaterials, BillOfMaterialsComponent
from cmsd_schema.calendar_entities import Calendar, Shift, Break, Holiday
from cmsd_schema.production_operations import Job
from cmsd_schema.process_planning import ProcessPlan, Process
from cmsd_schema.connection_entities import Connection
from cmsd_schema.inventory_entities import InventoryItem
from cmsd_schema.maintenance_entities import MaintenancePlan
from cmsd_schema.entity_reference_definition import (
    EntityReference,
    PartTypeReference, PartReference,
    ResourceClassReference, ResourceReference,
    ProcessPlanReference, ProcessReference,
    BillOfMaterialsReference, JobReference,
    CalendarReference,
    MaintenancePlanReference, InventoryItemClassReference,
    OrderInformationReference,
    SkillReference, SetupDefinitionReference, SetupChangeoverReference,
    LayoutElementReference, ReferenceMaterialReference,
    PropertyDescriptionReference, EventReference,
)
from cmsd_schema.part_entities import BillOfMaterialsComponentReference

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.transform import execute_transformation

from .api_client import APIClient

logger = logging.getLogger("cmsd-twin.mapping-factory")


class MappingDrivenFactory:
    """Builds CMSD entity instances from mapping configuration at runtime."""

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

    # Maps entity name → (ReferenceClass, identifier_field_name)
    # Built by convention {Entity}Reference with {snake_entity}_identifier,
    # with explicit overrides for non-standard names.
    REFERENCE_REGISTRY: dict[str, tuple[type, str]] = {
        "Resource": (ResourceReference, "resource_identifier"),
        "ResourceClass": (ResourceClassReference, "resource_class_identifier"),
        "PartType": (PartTypeReference, "part_type_identifier"),
        "Part": (PartReference, "part_identifier"),
        "BillOfMaterials": (BillOfMaterialsReference, "bill_of_materials_identifier"),
        "BillOfMaterialsComponent": (BillOfMaterialsComponentReference, "bill_of_materials_component_identifier"),
        "ProcessPlan": (ProcessPlanReference, "process_plan_identifier"),
        "Process": (ProcessReference, "process_identifier"),
        "Order": (OrderInformationReference, "order_identifier"),
        "OrderLine": (OrderInformationReference, "order_line_identifier"),
        "Calendar": (CalendarReference, "calendar_identifier"),
        "Job": (JobReference, "job_identifier"),
        "InventoryItem": (InventoryItemClassReference, "inventory_item_class_identifier"),
        "MaintenancePlan": (MaintenancePlanReference, "maintenance_plan_identifier"),
    }

    _FIELD_TYPE_HINTS: dict[str, dict[str, type]] = {}
    _REFERENCE_BY_CLASS: dict[type, str] = {}  # ReferenceClass -> identifier_field_name

    def __init__(self):
        self._mappings: list[dict] = []
        self._build_field_type_hints()
        # Build reverse map: Reference class → identifier field name
        for ref_class, id_field in self.REFERENCE_REGISTRY.values():
            self._REFERENCE_BY_CLASS[ref_class] = id_field

    def load_mappings(self, mappings_dir: str = ".agent-mappings"):
        """Load all confirmed mapping JSON files."""
        self._mappings = []
        if not os.path.isdir(mappings_dir):
            logger.warning(f"Mappings directory not found: {mappings_dir}")
            return
        for filename in sorted(os.listdir(mappings_dir)):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(mappings_dir, filename)
            try:
                with open(filepath, "r") as f:
                    mapping = json.load(f)
                mapping["_id"] = filename.replace(".json", "")
                self._mappings.append(mapping)
                logger.info(
                    f"Loaded mapping: {mapping.get('data_point', filename)} "
                    f"-> {mapping.get('cmsd_entity', '?')}"
                )
            except Exception as e:
                logger.error(f"Failed to load mapping {filename}: {e}")

    async def build_all(
        self,
        api_client: APIClient,
        mapping_ids: list[str] | None = None,
        registry: Any | None = None,
    ) -> tuple[CMSDDocument, dict]:
        """Fetch all mapped APIs and build a CMSDDocument."""
        doc = CMSDDocument()
        report: dict[str, Any] = {
            "entities": {},
            "fetch_errors": [],
            "field_warnings": [],
            "relation_errors": [],
            "topological_order": [],
        }

        mappings_to_build = self._mappings
        if mapping_ids:
            id_set = set(mapping_ids)
            mappings_to_build = [m for m in self._mappings if m.get("_id") in id_set]

        # Topological sort (if registry provided — Slice 5.3)
        ordered_ids = [m.get("_id") for m in mappings_to_build]
        if registry and len(ordered_ids) > 1:
            ordered_ids = registry.topological_order(ordered_ids)
            report["topological_order"] = ordered_ids

        id_to_mapping = {m.get("_id"): m for m in mappings_to_build}
        for mid in ordered_ids:
            mapping = id_to_mapping.get(mid)
            if not mapping:
                continue

            entity_type = mapping.get("cmsd_entity", "")
            if entity_type not in self.ENTITY_REGISTRY:
                logger.warning(f"Unknown entity type: {entity_type}, skipping")
                continue

            source = mapping.get("source", {})
            is_manual = source.get("type") == "manual"

            if is_manual:
                # Manual entities: use static raw_payload directly, skip API fetch
                raw_items = mapping.get("endpoints", [{}])[0].get("raw_payload", [])
            else:
                url = f"{source.get('base_url', '')}{source.get('endpoint', '')}"
                method = source.get("method", "GET")
                headers = source.get("headers") or {}
                params = source.get("params") or {}
                auth = self._resolve_auth(source)

                # Fetch with retry (Slice 5.3 adds backoff)
                response = None
                last_error = None
                for attempt in range(3):
                    try:
                        response = await api_client.fetch(
                            url, method, headers=headers, auth_config=auth, params=params
                        )
                        break
                    except Exception as e:
                        last_error = e
                        if attempt < 2:
                            backoff = 2 ** attempt
                            logger.warning(
                                f"Fetch attempt {attempt+1} failed for {entity_type}: {e}. "
                                f"Retrying in {backoff}s"
                            )
                            await asyncio.sleep(backoff)

                if response is None:
                    logger.error(f"Fetch failed for {entity_type} from {url}: {last_error}")
                    report["fetch_errors"].append({
                        "entity_type": entity_type,
                        "mapping_id": mid,
                        "endpoint": url,
                        "error": str(last_error),
                        "retries_exhausted": True,
                    })
                    continue

                # Extract entity array
                count_path = mapping.get("instances", {}).get("count_path", "")
                raw_items = self._extract_array(response, count_path)
                if raw_items is None:
                    report["fetch_errors"].append({
                        "entity_type": entity_type,
                        "mapping_id": mid,
                        "endpoint": url,
                        "error": f"count_path '{count_path}' not found in response",
                    })
                    continue

            # Build entity instances
            instances, warnings = self._build_entity(mapping, raw_items)
            report["field_warnings"].extend(warnings)
            self._attach_to_document(doc, entity_type, instances)
            report["entities"][entity_type] = {"count": len(instances), "source": "mapping"}

        # Post-processing: resolve cross-entity relations (hard errors on failure)
        relation_errors = self._resolve_relations(doc, id_to_mapping)
        # Validate: every Reference field must point to an existing entity instance
        ref_errors = self._validate_references(doc)
        relation_errors.extend(ref_errors)
        report["relation_errors"] = relation_errors

        return doc, report

    def _build_entity(self, mapping: dict, raw_items: list[dict]) -> tuple[list, list]:
        """Build CMSD model instances from raw API items."""
        entity_type = mapping.get("cmsd_entity", "")
        model_class = self.ENTITY_REGISTRY.get(entity_type)
        if not model_class:
            return [], []

        field_map = mapping.get("mapping", {})
        key_field_api = mapping.get("instances", {}).get("key_field", "")
        field_hints = self._FIELD_TYPE_HINTS.get(entity_type, {})
        source = mapping.get("source", {})
        source_url = f"{source.get('base_url', '')}{source.get('endpoint', '')}"

        instances = []
        warnings = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for item in raw_items:
            kwargs: dict[str, Any] = {}
            key_value = self._resolve_path(item, key_field_api) if key_field_api else None

            for cmsd_field, config in field_map.items():
                if not isinstance(config, dict):
                    continue
                # Skip relation-source passthrough fields — they're display-only, not CMSD fields
                if config.get("_is_relation_source"):
                    continue
                api_path = config.get("api_path", "")
                if not api_path:
                    # No path mapped — let the model use its default value
                    continue

                raw_value = self._resolve_path(item, api_path)
                if raw_value is None:
                    kwargs[cmsd_field] = None
                    warnings.append({
                        "entity_type": entity_type,
                        "instance_key": str(key_value or "?"),
                        "field": cmsd_field,
                        "api_path": api_path,
                    })
                    continue

                # Resolve unit_from_field (OData sap:unit): read the SAP unit code from
                # the companion property (deterministic, in-factory — never the LLM),
                # look up the conversion factor, and synthesize a unit_conversion. The
                # LLM only decides *which* companion field holds the unit (metadata);
                # the actual unit value + factor are resolved here at runtime.
                transformation = config.get("transformation")
                unit_from = config.get("unit_from_field")
                if unit_from and not transformation and isinstance(unit_from, dict):
                    unit_path = unit_from.get("unit_path", "")
                    target_unit = unit_from.get("target_unit", "second")
                    if unit_path:
                        unit_value = self._resolve_path(item, unit_path)
                        if unit_value:
                            from shared.odata.units import convert_factor
                            factor = convert_factor(str(unit_value), target_unit)
                            if factor is not None:
                                transformation = {
                                    "type": "unit_conversion",
                                    "params": {"factor": factor, "from": str(unit_value), "to": target_unit},
                                }
                            else:
                                warnings.append({
                                    "entity_type": entity_type,
                                    "instance_key": str(key_value or "?"),
                                    "field": cmsd_field,
                                    "api_path": api_path,
                                    "warning": f"unknown SAP unit '{unit_value}' — value left in raw unit",
                                })

                # Apply transformation
                if transformation and isinstance(transformation, dict):
                    result = execute_transformation(str(raw_value), transformation)
                    if result.get("success"):
                        raw_value = result["converted_value"]

                # Coerce to CMSD type
                expected_type = field_hints.get(cmsd_field)
                kwargs[cmsd_field] = self._coerce_type(raw_value, expected_type)

            # Connection metadata (attached after construction — models don't allow extras)
            conn_meta = {
                "mapping_id": mapping.get("_id", ""),
                "source_url": source_url,
                "key_field": key_field_api,
                "key_value": str(key_value) if key_value is not None else None,
                "last_fetched": now_iso,
            }

            try:
                instance = model_class(**kwargs)
                instance._connection = conn_meta
                # Save raw API item for later relation resolution
                instance._raw_source = item
                instances.append(instance)
            except Exception as e:
                # Extract the specific field that failed from Pydantic errors
                failed_fields = []
                if hasattr(e, 'errors'):
                    for err in e.errors():
                        loc = err.get('loc', ())
                        failed_fields.append('.'.join(str(p) for p in loc))
                field_info = ', '.join(failed_fields) if failed_fields else str(e)
                logger.warning(
                    f"Failed to construct {entity_type} (key={key_value}): "
                    f"fields=[{field_info}]"
                )
                warnings.append({
                    "entity_type": entity_type,
                    "instance_key": str(key_value or "?"),
                    "field": failed_fields[0] if failed_fields else "(constructor)",
                    "api_path": str(e),
                })

        return instances, warnings

    # ─── Relation Resolution (Issue 06) ──────────────────────────

    def _resolve_relations(self, doc: CMSDDocument, id_to_mapping: dict) -> list[dict]:
        """Post-processing pass: resolve cross-entity relations for all entities
        that have a 'relations' array in their mapping JSON.

        Returns a list of error dicts. An empty list means all relations resolved
        successfully. Non-empty means the build has broken cross-entity references
        and should be treated as failed."""
        errors: list[dict] = []
        # Build lookup: entity_type → list of instances (from doc)
        doc_index = self._index_document(doc)

        for mid, mapping in id_to_mapping.items():
            relations = mapping.get("relations", [])
            if not relations:
                continue

            entity_type = mapping.get("cmsd_entity", "")
            instances = doc_index.get(entity_type, [])
            if not instances:
                continue

            for relation in relations:
                target_entity = relation.get("target_entity", "")
                target_mapping_id = relation.get("target_mapping_id", "")
                cmsd_path = relation.get("cmsd_path", "")
                match_key = relation.get("match_key", {})
                source_api_path = match_key.get("source", {}).get("api_path", "")
                target_field = match_key.get("target", {}).get("field", "identifier")
                source_transform = match_key.get("source", {}).get("transform")

                if not target_entity or not cmsd_path or not source_api_path:
                    errors.append({
                        "entity_type": entity_type,
                        "relation": f"{entity_type}→{target_entity}",
                        "field": "(relation)",
                        "error": "incomplete relation definition",
                    })
                    continue

                # Get target instances
                if target_mapping_id:
                    # Look up target by mapping_id first
                    target_instances = []
                    for et, insts in doc_index.items():
                        for inst in insts:
                            conn = getattr(inst, '_connection', None)
                            if conn and conn.get('mapping_id') == target_mapping_id:
                                target_instances.append(inst)
                    if not target_instances:
                        # Fall back to entity-type lookup
                        target_instances = doc_index.get(target_entity, [])
                else:
                    target_instances = doc_index.get(target_entity, [])

                if not target_instances:
                    errors.append({
                        "entity_type": entity_type,
                        "relation": f"{entity_type}→{target_entity}",
                        "field": target_mapping_id or target_entity,
                        "error": f"target entity '{target_entity}' has no instances in document — mapping may not exist",
                    })
                    continue

                # Build target lookup index
                target_by_field: dict[str, Any] = {}
                for t in target_instances:
                    tv = getattr(t, target_field, None)
                    if tv is not None:
                        target_by_field[str(tv)] = t

                for instance in instances:
                    raw = getattr(instance, '_raw_source', None)
                    if not raw:
                        continue

                    source_value = self._resolve_path(raw, source_api_path)
                    if source_value is None:
                        continue

                    # Apply optional source transform
                    lookup_value = str(source_value)
                    if source_transform and isinstance(source_transform, dict):
                        result = execute_transformation(lookup_value, source_transform)
                        if result.get("success"):
                            lookup_value = result["converted_value"]

                    matched = target_by_field.get(lookup_value)
                    if matched is None:
                        errors.append({
                            "entity_type": entity_type,
                            "instance_key": str(getattr(instance, 'identifier', '?')),
                            "field": f"relation→{target_entity}",
                            "error": f"instance '{lookup_value}' not found in {target_entity}.{target_field} — check the {target_entity} mapping",
                        })
                        continue

                    # Build the reference object
                    reference = self._build_reference(target_entity, matched)
                    if reference is None:
                        errors.append({
                            "entity_type": entity_type,
                            "instance_key": str(getattr(instance, 'identifier', '?')),
                            "field": f"relation→{target_entity}",
                            "error": f"cannot build reference object for {target_entity} — no reference class registered",
                        })
                        continue

                    # Deep-set the reference at cmsd_path
                    try:
                        self._deep_set_reference(instance, cmsd_path, reference, doc_index)
                    except Exception as e:
                        errors.append({
                            "entity_type": entity_type,
                            "instance_key": str(getattr(instance, 'identifier', '?')),
                            "field": cmsd_path,
                            "error": f"failed to set reference at '{cmsd_path}': {e}",
                        })

        return errors

    def _validate_references(self, doc: CMSDDocument) -> list[dict]:
        """Post-build validation: check that every Reference field on every entity
        points to an entity that actually exists in the document.

        This catches cases where _coerce_type wraps a scalar into a Reference
        object (e.g. 1 → ResourceClassReference(resource_class_identifier='1'))
        but no target entity with that identifier exists."""
        errors: list[dict] = []
        doc_index = self._index_document(doc)
        if not doc_index:
            return errors

        for entity_type, model_class in self.ENTITY_REGISTRY.items():
            instances = doc_index.get(entity_type, [])
            if not instances:
                continue

            # Get field → type hints for this entity
            hints = self._FIELD_TYPE_HINTS.get(entity_type, {})
            ref_fields = {
                field_name: field_type
                for field_name, field_type in hints.items()
                if hasattr(field_type, '__name__') and field_type.__name__.endswith('Reference')
            }

            if not ref_fields:
                continue

            for instance in instances:
                for field_name, field_type in ref_fields.items():
                    ref_obj = getattr(instance, field_name, None)
                    if ref_obj is None:
                        continue

                    # Extract the identifier from the reference object
                    id_field = self._REFERENCE_BY_CLASS.get(field_type)
                    if not id_field:
                        continue
                    ref_id = getattr(ref_obj, id_field, None)
                    if ref_id is None:
                        continue

                    # Find the target entity type from REFERENCE_REGISTRY
                    target_entity = None
                    for entity_name, (ref_class, _) in self.REFERENCE_REGISTRY.items():
                        if ref_class is field_type:
                            target_entity = entity_name
                            break

                    if not target_entity:
                        continue

                    # Check if the referenced instance exists
                    target_instances = doc_index.get(target_entity, [])
                    found = any(
                        str(getattr(t, 'identifier', '')) == str(ref_id)
                        for t in target_instances
                    )

                    if not found:
                        errors.append({
                            "entity_type": entity_type,
                            "instance_key": str(getattr(instance, 'identifier', '?')),
                            "field": f"{field_name}→{target_entity}",
                            "error": f"referenced {target_entity} '{ref_id}' does not exist — "
                                     f"check the {target_entity} mapping or create a manual {target_entity}",
                        })

        return errors

    def _build_reference(self, target_entity: str, matched_instance: Any) -> Any | None:
        """Build a CMSD Reference object pointing to the matched entity instance."""
        entry = self.REFERENCE_REGISTRY.get(target_entity)
        if not entry:
            logger.warning(f"No reference class registered for entity: {target_entity}")
            return None

        ref_class, id_field = entry
        target_identifier = getattr(matched_instance, 'identifier', None)
        if target_identifier is None:
            return None

        kwargs: dict[str, Any] = {id_field: str(target_identifier)}

        # For OrderLine references, we also need order_identifier
        if target_entity == "OrderLine":
            # The parent Order's identifier — walk up from the OrderLine
            parent_order_id = getattr(matched_instance, 'order_identifier', None)
            if not parent_order_id:
                # If OrderLine is nested, try to find it
                pass
            kwargs["order_identifier"] = str(parent_order_id) if parent_order_id else ""

        # For CalendarReference, default to calendar_identifier if nothing else set
        if ref_class is CalendarReference:
            kwargs.setdefault("calendar_identifier", str(target_identifier))

        # For ProcessReference, at least one identifier is required
        if ref_class is ProcessReference:
            if "process_identifier" not in kwargs:
                kwargs["process_identifier"] = str(target_identifier)

        try:
            return ref_class(**kwargs)
        except Exception as e:
            logger.warning(f"Failed to build {ref_class.__name__}: {e}")
            return None

    def _deep_set_reference(self, entity: Any, cmsd_path: str, reference: Any,
                            doc_index: dict[str, list] | None = None):
        """Walk/create the cmsd_path on the entity and set the leaf to reference.
        Handles list indices ([0]) and nested object attributes.
        When an intermediate entity type exists in doc_index (built earlier by DAG),
        uses that entity instead of creating an empty shell.

        Example path: 'order_lines[0].part_description.part_type'
        """
        segments = self._parse_cmsd_path(cmsd_path)
        cur: Any = entity

        for i, seg in enumerate(segments):
            is_last = (i == len(segments) - 1)
            if seg["type"] == "attr":
                if is_last:
                    setattr(cur, seg["name"], reference)
                else:
                    existing = getattr(cur, seg["name"], None)
                    if existing is None:
                        existing = self._get_or_create_intermediate(
                            type(cur).__name__, seg["name"], doc_index
                        )
                        if existing is not None:
                            setattr(cur, seg["name"], existing)
                    if existing is None:
                        raise ValueError(
                            f"Cannot create intermediate object for {seg['name']} "
                            f"on {type(cur).__name__}"
                        )
                    cur = existing
            elif seg["type"] == "list":
                idx = seg["index"]
                lst = getattr(cur, seg["name"], None)
                if lst is None or not isinstance(lst, list):
                    lst = []
                    setattr(cur, seg["name"], lst)
                # Ensure list is long enough
                while len(lst) <= idx:
                    item_type = self._infer_list_item_type(type(cur).__name__, seg["name"])
                    existing_item = self._get_or_create_intermediate(
                        type(cur).__name__, seg["name"], doc_index
                    )
                    if existing_item is not None:
                        lst.append(existing_item)
                    elif item_type:
                        try:
                            lst.append(item_type())
                        except Exception:
                            lst.append(None)
                    else:
                        lst.append(None)
                if is_last:
                    lst[idx] = reference
                else:
                    cur = lst[idx]
                    if cur is None:
                        raise ValueError(
                            f"List item {seg['name']}[{idx}] is None, "
                            f"cannot traverse deeper into path"
                        )

    def _parse_cmsd_path(self, cmsd_path: str) -> list[dict]:
        """Parse a CMSD path like 'order_lines[0].part_description.part_type'
        into structured segments."""
        segments: list[dict] = []
        parts = cmsd_path.split(".")
        for part in parts:
            m = re.match(r'^(\w+)\[(\d+)\]$', part)
            if m:
                segments.append({"type": "list", "name": m.group(1), "index": int(m.group(2))})
            else:
                segments.append({"type": "attr", "name": part})
        return segments

    def _infer_field_type(self, entity_name: str, field_name: str) -> type | None:
        """Look up the Pydantic type of a field on an entity."""
        hints = self._FIELD_TYPE_HINTS.get(entity_name, {})
        return hints.get(field_name)

    def _infer_list_item_type(self, entity_name: str, field_name: str) -> type | None:
        """Get the item type of a List[...] field."""
        hints = self._FIELD_TYPE_HINTS.get(entity_name, {})
        field_type = hints.get(field_name)
        if field_type is None:
            return None
        origin = typing.get_origin(field_type)
        if origin is list:
            args = typing.get_args(field_type)
            if args:
                return self._unwrap_optional(args[0])
        return None

    def _get_or_create_intermediate(self, parent_entity: str, field_name: str,
                                     doc_index: dict[str, list] | None = None) -> Any | None:
        """Get an existing entity from doc_index or create a new empty instance.
        If the field type is a top-level CMSD entity (in ENTITY_REGISTRY) and instances
        exist in doc_index, use one of those — the DAG already built them. Otherwise,
        create an empty shell for intermediate wrapper types (e.g. OrderLinePartDescription)."""
        field_type = self._infer_field_type(parent_entity, field_name)
        if field_type is None:
            # Try list item type
            field_type = self._infer_list_item_type(parent_entity, field_name)

        if field_type is None:
            return None

        type_name = field_type.__name__

        # If this is a top-level CMSD entity type, check the document first
        if type_name in self.ENTITY_REGISTRY and doc_index:
            existing = doc_index.get(type_name, [])
            if existing:
                # Return the first unclaimed entity of this type
                for inst in existing:
                    conn = getattr(inst, '_connection', None)
                    if conn and conn.get('_claimed_by_relation'):
                        continue
                    # Mark as claimed so another relation doesn't steal it
                    if conn:
                        conn['_claimed_by_relation'] = True
                    return inst
                # All claimed — still return first one (better than nothing)
                return existing[0]
            # Entity type registered but no instances in doc — create empty
            try:
                return field_type()
            except Exception:
                return None

        # Intermediate wrapper type (not a top-level entity) — create new
        try:
            return field_type()
        except Exception:
            return None

    def _index_document(self, doc: CMSDDocument) -> dict[str, list]:
        """Index all entity instances in the document by entity type."""
        index: dict[str, list] = {}
        attr_map = {
            "Resource": "resources", "ResourceClass": "resource_classes",
            "PartType": "part_types", "Part": "parts",
            "BillOfMaterials": "bills_of_materials",
            "BillOfMaterialsComponent": "bills_of_materials_components",
            "ProcessPlan": "process_plans", "Process": "processes",
            "Order": "orders", "OrderLine": "order_lines",
            "Calendar": "calendars", "Shift": "shifts",
            "Break": "breaks", "Holiday": "holidays",
            "Connection": "connections", "Job": "jobs",
            "InventoryItem": "inventory_items",
            "MaintenancePlan": "maintenance_plans",
        }
        for entity_type, attr_name in attr_map.items():
            instances = getattr(doc, attr_name, None)
            if instances:
                index[entity_type] = instances
        return index

    def _resolve_auth(self, source: dict) -> dict:
        """Resolve the auth config for a runtime fetch.

        Decrypts ``source.auth_encrypted`` (Fernet, when ``SAP_CRED_KEY`` is set) into
        the normalized {type, ...} shape that ``api_client._build_auth_headers`` reads.
        Falls back to the plaintext ``source.auth`` block for dev/no-key mode and for
        legacy mock mappings (which store ``auth: {"type":"none"}``).
        """
        enc = source.get("auth_encrypted")
        if enc:
            try:
                from shared.crypto import decrypt_dict
                decrypted = decrypt_dict(enc)
                if isinstance(decrypted, dict):
                    return decrypted
                logger.warning(
                    f"auth_encrypted present but decrypt returned none for "
                    f"{source.get('endpoint', '')} — SAP_CRED_KEY unset at runtime?"
                )
            except Exception as e:
                logger.warning(f"auth decrypt failed for {source.get('endpoint', '')}: {e}")
        return source.get("auth") or {"type": "none"}

    def _resolve_path(self, obj: Any, path: str) -> Any:
        """Follow a dot-notation path into a dict (instance-relative).
        As a safety net for legacy mappings, strips absolute JSONPath prefixes
        where the array is at the first nesting level (e.g. $.resources[*].name).
        For deeper nesting ($.d.results[*].field), rely on confirm-time normalization
        in _normalize_api_paths."""
        if not obj or not path:
            return None

        clean = path.replace("$.", "", 1) if path.startswith("$.") else path

        parts = clean.split(".")
        cur = obj
        for i, part in enumerate(parts):
            if cur is None or not isinstance(cur, dict):
                return None
            # Skip array-access segments and the segment before them (the array name)
            if part == "[*]" or part == "" or part.isdigit():
                continue
            if "[*]" in part:
                continue
            # For first segment after $., if the next segment is [*], skip both
            if i == 0 and len(parts) > 1 and (parts[1] == "[*]" or "[*]" in parts[1]):
                continue
            cur = cur.get(part)
        return cur

    def _extract_array(self, response: dict, count_path: str) -> list[dict] | None:
        """Extract the entity array from the API response using count_path."""
        if not count_path:
            return None
        cleaned = count_path.replace("$.", "").replace("[*]", "")
        parts = [p for p in cleaned.split(".") if p]
        cur = response
        for part in parts:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(part)
            if cur is None:
                return None
        if isinstance(cur, list):
            return cur
        return None

    @staticmethod
    def _unwrap_optional(tp: type) -> type:
        """If tp is Optional[X], return X. Otherwise return tp unchanged."""
        import typing
        origin = typing.get_origin(tp)
        if origin is typing.Union:
            args = typing.get_args(tp)
            non_none = [a for a in args if a is not type(None)]
            if len(non_none) == 1:
                return non_none[0]
        return tp

    def _coerce_type(self, value: Any, expected_type: type | None) -> Any:
        """Coerce a raw value to the expected CMSD field type."""
        if value is None or expected_type is None:
            return value

        # Unwrap Optional[X] -> X
        inner_type = self._unwrap_optional(expected_type)
        if isinstance(value, inner_type):
            return value

        type_name = getattr(inner_type, "__name__", str(inner_type))
        try:
            if inner_type is Decimal:
                return Decimal(str(value))
            if isinstance(inner_type, type) and hasattr(inner_type, "__members__"):
                return inner_type(str(value))
            if type_name == "Duration":
                from cmsd_schema.basic_structures import Duration
                return Duration(unit="second", value=Decimal(str(value)))
            if type_name == "Currency":
                from cmsd_schema.basic_structures import Currency
                if isinstance(value, dict):
                    return Currency(**value)
                return Currency(value=Decimal(str(value)))
            if type_name == "GrossDimensions":
                from cmsd_schema.basic_structures import GrossDimensions
                if isinstance(value, dict):
                    return GrossDimensions(**value)
                return None
            # Handle Reference types: scalar → ReferenceClass(identifier_field=value)
            if type_name.endswith("Reference") and inner_type in self._REFERENCE_BY_CLASS:
                id_field = self._REFERENCE_BY_CLASS[inner_type]
                return inner_type(**{id_field: str(value)})

            # Generic: any Pydantic BaseModel — pass dict through, coerce scalar to first required field
            if hasattr(inner_type, 'model_fields') and isinstance(value, dict):
                return inner_type(**value)
            if hasattr(inner_type, 'model_fields') and not isinstance(value, dict):
                fields = inner_type.model_fields
                for fname, finfo in fields.items():
                    if finfo.is_required() and finfo.annotation in (Decimal, float, int):
                        return inner_type(**{fname: Decimal(str(value))})
            if inner_type is int:
                return int(float(value))
            if inner_type is float:
                return float(value)
            if inner_type is str:
                return str(value)
            if inner_type is bool:
                if isinstance(value, str):
                    return value.lower() in ("true", "1", "yes")
                return bool(value)
        except (ValueError, TypeError) as e:
            logger.warning(f"Type coercion failed: {value} -> {type_name}: {e}")
            return None
        return value

    def _build_field_type_hints(self):
        """Introspect Pydantic models to build field -> type mappings.
        Uses typing.get_type_hints() to resolve forward references (PEP 563)."""
        for entity_name, model_class in self.ENTITY_REGISTRY.items():
            hints = {}
            try:
                resolved = typing.get_type_hints(model_class)
            except Exception:
                resolved = {}
            for field_name, annotation in resolved.items():
                if annotation is not None:
                    hints[field_name] = self._unwrap_optional(annotation)
            self._FIELD_TYPE_HINTS[entity_name] = hints

    def _attach_to_document(self, doc: CMSDDocument, entity_type: str, instances: list):
        """Attach entity instances to the correct CMSDDocument field."""
        attr_map = {
            "Resource": "resources",
            "ResourceClass": "resource_classes",
            "PartType": "part_types",
            "Part": "parts",
            "BillOfMaterials": "bills_of_materials",
            "Order": "orders",
            "Calendar": "calendars",
            "Connection": "connections",
            "Job": "jobs",
            "InventoryItem": "inventory_items",
            "MaintenancePlan": "maintenance_plans",
            "ProcessPlan": "process_plans",
        }
        attr_name = attr_map.get(entity_type)
        if attr_name:
            setattr(doc, attr_name, instances)
