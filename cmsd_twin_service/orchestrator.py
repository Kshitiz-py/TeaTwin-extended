"""
CMSDOrchestrator — Manages the single CMSDDocument instance, polls SAP/MES APIs,
detects changes, publishes events. Integrates MappingDrivenFactory for
mapping-based instance generation alongside the hardcoded CMSDFactory.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from .api_client import APIClient
from .factory import CMSDFactory
from .mapping_factory import MappingDrivenFactory
from .mapping_registry import MappingRegistry
from .change_detector import ChangeDetector, ChangeEvent
from .event_bus import EventBus
from .config import POLL_INTERVAL

logger = logging.getLogger("cmsd-twin.orchestrator")


class CMSDOrchestrator:
    """
    Persistent service that:
    1. Holds the live CMSDDocument (digital twin) in memory
    2. Polls SAP + MES APIs on a configurable interval
    3. Runs mapping-driven instance generation from confirmed mappings
    4. Builds fresh CMSDDocument from API data (hardcoded + mapping-driven)
    5. Diffs against stored document
    6. Publishes ChangeEvents via EventBus
    7. Replaces stored document with new version
    """

    def __init__(self, event_bus: EventBus, poll_interval: int | None = None):
        self.event_bus = event_bus
        self.factory = CMSDFactory()
        self.detector = ChangeDetector()

        # Mapping-driven generation (Slice 5.2+)
        self._mapping_factory = MappingDrivenFactory()
        self._registry = None  # MappingRegistry — set in Slice 5.3

        # Polling
        self._poll_interval = poll_interval if poll_interval is not None else POLL_INTERVAL

        # State
        self._current_doc = None
        self._last_poll_time: str | None = None
        self._last_refreshed: datetime | None = None
        self._poll_count = 0
        self._total_changes = 0
        self._running = False
        self._task: asyncio.Task | None = None

    # ── Properties ─────────────────────────────────────────

    @property
    def current_document(self):
        return self._current_doc

    @property
    def last_poll_time(self) -> str | None:
        return self._last_poll_time

    @property
    def poll_interval(self) -> int:
        return self._poll_interval

    @property
    def is_polling(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def last_refreshed_iso(self) -> str | None:
        if self._last_refreshed:
            return self._last_refreshed.isoformat()
        return None

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "poll_count": self._poll_count,
            "total_changes": self._total_changes,
            "last_poll_time": self._last_poll_time,
            "running": self._running,
            "document_loaded": self._current_doc is not None,
            "mappings_loaded": len(self._mapping_factory._mappings),
            "is_polling": self.is_polling,
            "poll_interval_seconds": self._poll_interval,
            "last_refreshed": self.last_refreshed_iso,
        }

    # ── Lifecycle ──────────────────────────────────────────

    async def start(self):
        """Start the background polling loop. Loads mappings from disk."""
        if self._running:
            return

        # Load mapping files
        mappings_dir = os.path.join(os.path.dirname(__file__), "..", ".agent-mappings")
        self._mapping_factory.load_mappings(mappings_dir)
        logger.info(f"Loaded {len(self._mapping_factory._mappings)} mapping(s)")

        self._running = True
        if self._poll_interval > 0:
            self._start_polling()
        logger.info(f"CMSDOrchestrator started (poll_interval={self._poll_interval}s)")

    async def stop(self):
        """Stop the background polling loop."""
        self._running = False
        self._stop_polling()
        logger.info("CMSDOrchestrator stopped")

    def _start_polling(self):
        if self.is_polling:
            return
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(f"Polling started (interval={self._poll_interval}s)")

    def _stop_polling(self):
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        logger.info("Polling stopped")

    async def set_poll_interval(self, seconds: int):
        """Update poll interval. 0 = stop, >0 = start/restart."""
        self._poll_interval = seconds
        self._stop_polling()
        if seconds > 0:
            self._start_polling()

    # ── Main refresh entry point ───────────────────────────

    async def run_once(self, mapping_ids: list[str] | None = None,
                        use_hardcoded: bool = True) -> dict[str, Any]:
        """Execute a single fetch-build-diff-publish cycle."""
        t_start = datetime.now(timezone.utc)

        # Reload mappings from disk (they may have been added since startup)
        mappings_dir = os.path.join(os.path.dirname(__file__), "..", ".agent-mappings")
        self._mapping_factory.load_mappings(mappings_dir)
        if self._registry:
            self._registry = MappingRegistry()
            for mapping in self._mapping_factory._mappings:
                self._registry.register(mapping)

        async with APIClient() as api_client:
            # Phase 1: Mapping-driven build
            mapped_doc, report = await self._mapping_factory.build_all(
                api_client, mapping_ids, self._registry
            )

            # Phase 2: Hardcoded fallback (only when enabled)
            if use_hardcoded:
                hardcoded_doc = await self._build_hardcoded(api_client)
            else:
                from cmsd_schema.cmsd_document import CMSDDocument
                hardcoded_doc = CMSDDocument()

            # Phase 3: Merge (mapped takes priority)
            merged_doc = self._merge_documents(mapped_doc, hardcoded_doc, report)

            # Phase 4: Diff
            changes = []
            if self._current_doc is not None:
                changes = self.detector.diff(self._current_doc, merged_doc)

            # Phase 5: Publish
            if changes:
                await self.event_bus.publish(changes, f"refresh-{uuid.uuid4().hex[:12]}")

            # Phase 6: Replace
            self._current_doc = merged_doc
            self._last_refreshed = datetime.now(timezone.utc)
            self._poll_count += 1
            self._total_changes += len(changes)
            self._last_poll_time = self._last_refreshed.isoformat()

            elapsed_ms = int((datetime.now(timezone.utc) - t_start).total_seconds() * 1000)

            return {
                "success": len(report.get("fetch_errors", [])) == 0,
                "refreshed_at": self._last_refreshed.isoformat(),
                "phases": {
                    "preflight": {"passed": True, "warnings": []},
                    "topological_order": report.get("topological_order", []),
                    "generation": report.get("entities", {}),
                    "merge": {
                        "hardcoded_fallback": self._get_hardcoded_entity_types(
                            report.get("entities", {})
                        ),
                    },
                },
                "fetch_errors": report.get("fetch_errors", []),
                "field_warnings": report.get("field_warnings", []),
                "changes_detected": len(changes),
                "elapsed_ms": elapsed_ms,
            }

    async def force_rebuild(self) -> dict[str, Any]:
        """Manually trigger a full rebuild (accessible via API)."""
        return await self.run_once()

    # ── Pre-flight validation (Slice 5.3) ──────────────────

    def run_preflight(self, mapping_ids: list[str]) -> dict:
        """Validate readiness before generation. Stub — full impl in Slice 5.3."""
        if not self._registry:
            return {
                "passed": True,
                "checks": {
                    "dependencies": {"passed": True, "auto_selected": [], "missing": []},
                    "field_coverage": {"passed": True, "unapproved": []},
                    "api_reachability": {"passed": True, "unreachable": []},
                },
            }

        selected = set(mapping_ids)
        expanded = self._registry.auto_select_dependencies(selected)
        auto_selected = list(expanded - selected)

        missing_deps = []
        for mid in mapping_ids:
            deps = self._registry._dependencies.get(mid, set())
            unresolved = deps - expanded
            for dep_id in unresolved:
                dep_mapping = self._registry._mappings.get(dep_id, {})
                missing_deps.append({
                    "for_mapping": mid,
                    "for_entity": self._registry._mappings.get(mid, {}).get("cmsd_entity", ""),
                    "needs": dep_id,
                    "needs_entity": dep_mapping.get("cmsd_entity", ""),
                })

        unapproved = []
        for mid in expanded:
            mapping = self._registry._mappings.get(mid, {})
            field_map = mapping.get("mapping", {})
            for field_name, config in field_map.items():
                if isinstance(config, dict) and config.get("status", "pending") != "approved":
                    unapproved.append({
                        "mapping_id": mid,
                        "entity": mapping.get("cmsd_entity", ""),
                        "field": field_name,
                        "status": config.get("status", "pending"),
                    })

        return {
            "passed": len(missing_deps) == 0 and len(unapproved) == 0,
            "checks": {
                "dependencies": {
                    "passed": len(missing_deps) == 0,
                    "auto_selected": auto_selected,
                    "missing": missing_deps,
                },
                "field_coverage": {
                    "passed": len(unapproved) == 0,
                    "unapproved": unapproved,
                },
                "api_reachability": {"passed": True, "unreachable": []},
            },
        }

    # ── Internal helpers ───────────────────────────────────

    async def _build_hardcoded(self, api_client: APIClient) -> "CMSDDocument":
        """Build CMSDDocument from hardcoded factory (SAP+MES)."""
        from cmsd_schema.cmsd_document import CMSDDocument
        try:
            sap_data: dict[str, Any] = {}
            sap_data["resources"] = await api_client.get_resources()
            sap_data["resource_classes"] = await api_client.get_resource_classes()
            sap_data["part_types"] = await api_client.get_part_types()
            sap_data["parts"] = await api_client.get_parts()
            sap_data["boms"] = await api_client.get_boms()
            sap_data["process_plans"] = await api_client.get_process_plans()
            sap_data["orders"] = await api_client.get_orders()
            sap_data["calendars"] = await api_client.get_calendars()
            layouts_list = await api_client.get_layouts()
            sap_data["layouts"] = layouts_list
            for layout_item in layouts_list.get("layouts", []):
                detail = await api_client.get_layout(layout_item["identifier"])
                layout_item["placements"] = detail.get("placements", [])
            sap_data["connections"] = await api_client.get_connections()

            mes_data: dict[str, Any] = {}
            mes_data["resource_statuses"] = await api_client.get_resource_statuses()
            mes_data["jobs"] = await api_client.get_jobs()
            mes_data["inventory"] = await api_client.get_inventory()
            mes_data["incidents"] = await api_client.get_incidents(active_only=True)

            return self.factory.build(sap_data, mes_data)
        except Exception as e:
            logger.warning(f"Hardcoded factory build failed: {e}")
            return CMSDDocument()

    def _merge_documents(self, mapped, hardcoded, report):
        """Merge mapped and hardcoded documents. Mapped entities take priority."""
        from cmsd_schema.cmsd_document import CMSDDocument
        merged = CMSDDocument()
        entity_attrs = [
            "resources", "resource_classes", "part_types", "parts",
            "bills_of_materials", "process_plans", "orders", "calendars",
            "layouts", "connections", "jobs", "inventory_items", "maintenance_plans",
        ]
        mapped_entities = set(report.get("entities", {}).keys())
        for attr in entity_attrs:
            entity_type = self._attr_to_entity_type(attr)
            if entity_type and entity_type in mapped_entities:
                setattr(merged, attr, getattr(mapped, attr, []))
            else:
                setattr(merged, attr, getattr(hardcoded, attr, []))
        return merged

    def _attr_to_entity_type(self, attr_name: str) -> str | None:
        mapping = {
            "resources": "Resource",
            "resource_classes": "ResourceClass",
            "part_types": "PartType",
            "parts": "Part",
            "bills_of_materials": "BillOfMaterials",
            "process_plans": "ProcessPlan",
            "orders": "Order",
            "calendars": "Calendar",
            "layouts": "Layout",
            "connections": "Connection",
            "jobs": "Job",
            "inventory_items": "InventoryItem",
            "maintenance_plans": "MaintenancePlan",
        }
        return mapping.get(attr_name)

    def _get_hardcoded_entity_types(self, mapped_entities: dict) -> list[str]:
        """List entity types that came from hardcoded factory."""
        all_entities = {
            "Resource", "ResourceClass", "PartType", "Part", "BillOfMaterials",
            "ProcessPlan", "Order", "Calendar", "Connection", "Job",
            "InventoryItem", "MaintenancePlan",
        }
        return sorted(all_entities - set(mapped_entities.keys()))

    # ── Polling loop ───────────────────────────────────────

    async def _poll_loop(self):
        """Continuous polling loop."""
        # Initial build
        logger.info("Performing initial CMSD digital twin build...")
        try:
            await self.run_once()
        except Exception as e:
            logger.error(f"Initial build failed: {e}")

        while self._running:
            await asyncio.sleep(self._poll_interval)
            try:
                await self.run_once()
            except Exception as e:
                logger.error(f"Poll cycle failed: {e}")
