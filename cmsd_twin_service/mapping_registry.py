"""
MappingRegistry — manages mapping metadata, dependency resolution,
topological sort, and referential integrity validation for the
MappingDrivenFactory.
"""

import logging
from graphlib import TopologicalSorter
from typing import Any

logger = logging.getLogger("cmsd-twin.mapping-registry")


class MappingRegistry:
    """Tracks mappings and their cross-entity dependencies."""

    def __init__(self):
        self._mappings: dict[str, dict] = {}           # mapping_id -> mapping dict
        self._entity_keys: dict[str, set[str]] = {}    # entity_type -> set of key_values produced
        self._dependencies: dict[str, set[str]] = {}   # mapping_id -> set of mapping_ids it depends on
        self._entity_to_mapping: dict[str, str] = {}   # entity_type -> mapping_id (first one)

    def register(self, mapping: dict):
        """Register a mapping and infer its dependencies."""
        mapping_id = mapping.get("_id", "")
        entity_type = mapping.get("cmsd_entity", "")

        if not mapping_id:
            return

        self._mappings[mapping_id] = mapping
        if entity_type not in self._entity_to_mapping:
            self._entity_to_mapping[entity_type] = mapping_id

        deps = self._infer_dependencies(mapping)
        if deps:
            self._dependencies[mapping_id] = deps
            logger.info(f"Mapping '{mapping_id}' ({entity_type}) depends on: {deps}")

    def _infer_dependencies(self, mapping: dict) -> set[str]:
        """
        Hybrid dependency inference:
        1. Check explicit 'depends_on' in mapping JSON
        2. Introspect CMSD model field types for entity references
        3. Apply naming conventions ({entity}_id -> {Entity})
        """
        deps = set()

        # 1. Explicit dependencies
        explicit = mapping.get("depends_on", [])
        if explicit:
            deps.update(explicit)

        # 2. Schema introspection (from factory's ENTITY_REGISTRY + field hints)
        from .mapping_factory import MappingDrivenFactory
        entity_type = mapping.get("cmsd_entity", "")
        field_hints = MappingDrivenFactory._FIELD_TYPE_HINTS.get(entity_type, {})

        for field_name, field_type in field_hints.items():
            type_name = getattr(field_type, "__name__", "")
            if type_name in MappingDrivenFactory.ENTITY_REGISTRY:
                ref_mapping_id = self._entity_to_mapping.get(type_name)
                if ref_mapping_id and ref_mapping_id != mapping.get("_id"):
                    deps.add(ref_mapping_id)

        # 3. Naming convention heuristic
        field_map = mapping.get("mapping", {})
        for field_name in field_map:
            if field_name.endswith("_id"):
                entity_hint = (
                    field_name.replace("_id", "")
                    .replace("_", " ")
                    .title()
                    .replace(" ", "")
                )
                if entity_hint in MappingDrivenFactory.ENTITY_REGISTRY:
                    ref_mapping_id = self._entity_to_mapping.get(entity_hint)
                    if ref_mapping_id and ref_mapping_id != mapping.get("_id"):
                        deps.add(ref_mapping_id)

        return deps

    def topological_order(self, mapping_ids: list[str]) -> list[str]:
        """Return mapping_ids sorted so dependencies come first."""
        if len(mapping_ids) <= 1:
            return list(mapping_ids)

        dag: dict[str, set[str]] = {}
        for mid in mapping_ids:
            dag[mid] = self._dependencies.get(mid, set()) & set(mapping_ids)

        try:
            ts = TopologicalSorter(dag)
            return list(ts.static_order())
        except Exception as e:
            logger.error(f"Dependency cycle detected: {e}")
            return list(mapping_ids)

    def validate_referential_integrity(self, mapping_ids: list[str]) -> dict:
        """Check that all cross-entity references can be resolved."""
        issues = []
        for mid in mapping_ids:
            deps = self._dependencies.get(mid, set())
            missing = deps - set(mapping_ids)
            for dep_id in missing:
                dep_mapping = self._mappings.get(dep_id, {})
                issues.append({
                    "mapping_id": mid,
                    "entity": self._mappings.get(mid, {}).get("cmsd_entity", ""),
                    "depends_on": dep_id,
                    "depends_on_entity": dep_mapping.get("cmsd_entity", ""),
                    "resolved": False,
                })

        return {"passed": len(issues) == 0, "issues": issues}

    def auto_select_dependencies(self, selected_ids: set[str]) -> set[str]:
        """Return expanded set including dependencies of selected mappings."""
        expanded = set(selected_ids)
        changed = True
        while changed:
            changed = False
            for mid in list(expanded):
                deps = self._dependencies.get(mid, set())
                for dep_id in deps:
                    if dep_id not in expanded:
                        expanded.add(dep_id)
                        changed = True
        return expanded

    def get_dependency_graph(self, mapping_ids: list[str]) -> dict:
        """Return dependency graph for visualization."""
        nodes = []
        edges = []
        for mid in mapping_ids:
            m = self._mappings.get(mid, {})
            nodes.append({
                "id": mid,
                "entity": m.get("cmsd_entity", ""),
                "data_point": m.get("data_point", ""),
            })
            for dep_id in self._dependencies.get(mid, set()):
                if dep_id in set(mapping_ids):
                    edges.append({"from": dep_id, "to": mid})
        return {"nodes": nodes, "edges": edges}
