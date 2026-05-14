"""
CMSDOrchestrator — Manages the single CMSDDocument instance, polls SAP/MES APIs,
detects changes, publishes events. Runs as a persistent background service.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from .api_client import APIClient
from .factory import CMSDFactory
from .change_detector import ChangeDetector, ChangeEvent
from .event_bus import EventBus
from .config import POLL_INTERVAL

logger = logging.getLogger("cmsd-twin.orchestrator")


class CMSDOrchestrator:
    """
    Persistent service that:
    1. Holds the live CMSDDocument (digital twin) in memory
    2. Polls SAP + MES APIs on a configurable interval
    3. Builds fresh CMSDDocument from API data
    4. Diffs against stored document
    5. Publishes ChangeEvents via EventBus
    6. Replaces stored document with new version
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.factory = CMSDFactory()
        self.detector = ChangeDetector()

        # The live digital twin — starts as None until initial build
        self._current_doc = None
        self._last_poll_time: str | None = None
        self._poll_count = 0
        self._total_changes = 0
        self._running = False
        self._task: asyncio.Task | None = None

    @property
    def current_document(self):
        return self._current_doc

    @property
    def last_poll_time(self) -> str | None:
        return self._last_poll_time

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "poll_count": self._poll_count,
            "total_changes": self._total_changes,
            "last_poll_time": self._last_poll_time,
            "running": self._running,
            "document_loaded": self._current_doc is not None,
        }

    async def start(self):
        """Start the background polling loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("CMSDOrchestrator started")

    async def stop(self):
        """Stop the background polling loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("CMSDOrchestrator stopped")

    async def force_rebuild(self) -> dict[str, Any]:
        """Manually trigger a full rebuild (accessible via API)."""
        return await self._perform_poll(is_initial=False)

    async def _poll_loop(self):
        """Main loop — initial build then periodic polling."""
        # Initial build
        logger.info("Performing initial CMSD digital twin build...")
        try:
            await self._perform_poll(is_initial=True)
        except Exception as e:
            logger.error(f"Initial build failed: {e}")

        # Periodic polling
        while self._running:
            await asyncio.sleep(POLL_INTERVAL)
            try:
                await self._perform_poll(is_initial=False)
            except Exception as e:
                logger.error(f"Poll cycle failed: {e}")

    async def _perform_poll(self, is_initial: bool = False) -> dict[str, Any]:
        """
        Execute one complete polling cycle:
        FETCH → BUILD → DIFF → PUBLISH → REPLACE
        """
        poll_cycle_id = f"poll-{uuid.uuid4().hex[:12]}"
        start_time = datetime.now(timezone.utc)
        sap_calls = 0
        mes_calls = 0
        changes_count = 0

        # ─── FETCH ──────────────────────────────────────────
        async with APIClient() as client:
            # SAP Master Data
            sap_data: dict[str, Any] = {}
            try:
                sap_data["resources"] = await client.get_resources()
                sap_calls += 1
                sap_data["resource_classes"] = await client.get_resource_classes()
                sap_calls += 1
                sap_data["part_types"] = await client.get_part_types()
                sap_calls += 1
                sap_data["parts"] = await client.get_parts()
                sap_calls += 1
                sap_data["boms"] = await client.get_boms()
                sap_calls += 1
                sap_data["process_plans"] = await client.get_process_plans()
                sap_calls += 1
                sap_data["orders"] = await client.get_orders()
                sap_calls += 1
                sap_data["calendars"] = await client.get_calendars()
                sap_calls += 1
                # Fetch layouts WITH placements (detail endpoint per layout)
                layouts_list = await client.get_layouts()
                sap_calls += 1
                sap_data["layouts"] = layouts_list  # keep original list structure
                # Fetch detail for each layout to get placements
                for layout_item in layouts_list.get("layouts", []):
                    detail = await client.get_layout(layout_item["identifier"])
                    sap_calls += 1
                    layout_item["placements"] = detail.get("placements", [])
                sap_data["connections"] = await client.get_connections()
                sap_calls += 1
            except Exception as e:
                logger.warning(f"SAP data fetch error (will use cached): {e}")

            # MES Operational Data
            mes_data: dict[str, Any] = {}
            try:
                mes_data["resource_statuses"] = await client.get_resource_statuses()
                mes_calls += 1
                mes_data["jobs"] = await client.get_jobs()
                mes_calls += 1
                mes_data["inventory"] = await client.get_inventory()
                mes_calls += 1
                mes_data["incidents"] = await client.get_incidents(active_only=True)
                mes_calls += 1
            except Exception as e:
                logger.warning(f"MES data fetch error (will use cached): {e}")

        # ─── BUILD ──────────────────────────────────────────
        new_doc = self.factory.build(sap_data, mes_data)

        # ─── DIFF ───────────────────────────────────────────
        events: list[ChangeEvent] = []
        if self._current_doc is not None and not is_initial:
            events = self.detector.diff(self._current_doc, new_doc)
            changes_count = len(events)

        # ─── PUBLISH ────────────────────────────────────────
        if events:
            await self.event_bus.publish(events, poll_cycle_id)

        # ─── REPLACE ────────────────────────────────────────
        self._current_doc = new_doc
        self._poll_count += 1
        self._total_changes += changes_count
        self._last_poll_time = datetime.now(timezone.utc).isoformat()

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(
            f"Poll #{self._poll_count} complete: {changes_count} changes, "
            f"{sap_calls} SAP + {mes_calls} MES calls, {elapsed:.2f}s"
        )

        return {
            "poll_cycle_id": poll_cycle_id,
            "poll_number": self._poll_count,
            "changes_detected": changes_count,
            "sap_api_calls": sap_calls,
            "mes_api_calls": mes_calls,
            "elapsed_seconds": elapsed,
            "is_initial": is_initial,
            "timestamp": self._last_poll_time,
        }