"""
MappingDrivenFactory — builds CMSD entity instances from mapping configuration.
Reads .agent-mappings/*.json, calls APIs, resolves field paths, applies
transformations, and constructs typed CMSD Pydantic model instances.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cmsd-pydantic-master", "src"))
from cmsd_schema.cmsd_document import CMSDDocument
from cmsd_schema.resource_entities import Resource

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.transform import execute_transformation

from .api_client import APIClient

logger = logging.getLogger("cmsd-twin.mapping-factory")


class MappingDrivenFactory:
    """Builds CMSD entity instances from mapping configuration at runtime."""

    # Expanded in Slice 5.3
    ENTITY_REGISTRY: dict[str, type] = {
        "Resource": Resource,
    }

    _FIELD_TYPE_HINTS: dict[str, dict[str, type]] = {}

    def __init__(self):
        self._mappings: list[dict] = []
        self._build_field_type_hints()

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
            url = f"{source.get('base_url', '')}{source.get('endpoint', '')}"
            method = source.get("method", "GET")
            auth = source.get("auth", {"type": "none"})

            # Fetch with retry (Slice 5.3 adds backoff)
            response = None
            last_error = None
            for attempt in range(3):
                try:
                    response = await api_client.fetch(url, method, auth_config=auth)
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
                    "endpoint": url,
                    "error": f"count_path '{count_path}' not found in response",
                })
                continue

            # Build entity instances
            instances, warnings = self._build_entity(mapping, raw_items)
            report["field_warnings"].extend(warnings)
            self._attach_to_document(doc, entity_type, instances)
            report["entities"][entity_type] = {"count": len(instances), "source": "mapping"}

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
                api_path = config.get("api_path", "")
                if not api_path:
                    kwargs[cmsd_field] = None
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

                # Apply transformation
                transformation = config.get("transformation")
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
                instances.append(instance)
            except Exception as e:
                logger.warning(f"Failed to construct {entity_type} (key={key_value}): {e}")
                warnings.append({
                    "entity_type": entity_type,
                    "instance_key": str(key_value or "?"),
                    "field": "(constructor)",
                    "api_path": str(e),
                })

        return instances, warnings

    def _resolve_path(self, obj: Any, path: str) -> Any:
        """Follow a dot-notation path into a dict."""
        if not obj or not path:
            return None
        parts = path.split(".")
        cur = obj
        for part in parts:
            if cur is None or not isinstance(cur, dict):
                return None
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
        """Introspect Pydantic models to build field -> type mappings."""
        for entity_name, model_class in self.ENTITY_REGISTRY.items():
            hints = {}
            for field_name, field_info in model_class.model_fields.items():
                annotation = field_info.annotation
                if annotation is not None:
                    hints[field_name] = self._unwrap_optional(annotation)
            self._FIELD_TYPE_HINTS[entity_name] = hints

    def _attach_to_document(self, doc: CMSDDocument, entity_type: str, instances: list):
        """Attach entity instances to the correct CMSDDocument field."""
        attr_map = {
            "Resource": "resources",
        }
        attr_name = attr_map.get(entity_type)
        if attr_name:
            setattr(doc, attr_name, instances)
