"""
CMSD Twin Service — REST API + WebSocket routes.
Provides access to the digital twin, change events, and orchestrator control.
"""

import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query

from .orchestrator import CMSDOrchestrator
from .event_bus import EventBus
from .api_client import APIClient

logger = logging.getLogger("cmsd-twin.routes")

router = APIRouter(tags=["CMSD Digital Twin"])


# Will be set by main.py at startup
orchestrator: CMSDOrchestrator | None = None
event_bus: EventBus | None = None


def init(orch: CMSDOrchestrator, bus: EventBus):
    global orchestrator, event_bus
    orchestrator = orch
    event_bus = bus


def _serialize_entity(entity) -> dict:
    """Serialize a CMSD entity, including _connection metadata."""
    if hasattr(entity, 'model_dump'):
        data = entity.model_dump()
    elif hasattr(entity, 'dict'):
        data = entity.dict()
    else:
        data = {}
    if hasattr(entity, '_connection'):
        data['_connection'] = entity._connection
    return data


# ─── Digital Twin Queries ────────────────────────────────────

@router.get("/digital-twin/summary")
async def get_summary():
    """High-level summary of the digital twin state."""
    if not orchestrator:
        raise HTTPException(503, "Service not ready")
    doc = orchestrator.current_document
    if doc is None:
        return {"status": "building", "message": "Initial digital twin build in progress"}
    return {
        "status": "ready",
        "resources": len(doc.resources),
        "resource_classes": len(doc.resource_classes),
        "part_types": len(doc.part_types),
        "orders": len(doc.orders),
        "jobs": len(doc.jobs),
        "calendars": len(doc.calendars),
        "connections": len(doc.connections),
        **orchestrator.stats,
    }


@router.get("/digital-twin/resources")
async def get_resources():
    if not orchestrator or not orchestrator.current_document:
        raise HTTPException(503, "Digital twin not yet available")
    doc = orchestrator.current_document
    result = []
    for r in doc.resources:
        data = _serialize_entity(r)
        result.append({
            "identifier": data.get("identifier", r.identifier),
            "name": data.get("name", r.name),
            "resource_type": r.resource_type.value if hasattr(r.resource_type, "value") else str(r.resource_type),
            "current_status": r.current_status.value if r.current_status and hasattr(r.current_status, "value") else str(r.current_status) if r.current_status else None,
            "availability": float(r.availability) if r.availability else None,
            "capacity": r.capacity,
            "_connection": data.get("_connection"),
        })
    return result


@router.get("/digital-twin/orders")
async def get_orders():
    if not orchestrator or not orchestrator.current_document:
        raise HTTPException(503, "Digital twin not yet available")
    doc = orchestrator.current_document
    result = []
    for o in doc.orders:
        data = _serialize_entity(o)
        result.append({
            "identifier": o.identifier,
            "status": o.status.value if o.status and hasattr(o.status, "value") else str(o.status) if o.status else None,
            "due_date": str(o.due_date) if o.due_date else None,
            "line_count": len(o.order_lines),
            "_connection": data.get("_connection"),
        })
    return result


@router.get("/digital-twin/layout")
async def get_layout():
    """Return the first layout with placements from the digital twin."""
    if not orchestrator or not orchestrator.current_document:
        raise HTTPException(503, "Digital twin not yet available")
    doc = orchestrator.current_document
    layouts = doc.layouts or []
    if not layouts:
        return {"layouts": [], "placements": []}
    first = layouts[0]
    return {
        "identifier": first.get("identifier"),
        "name": first.get("name"),
        "placements": first.get("placements", []),
    }


@router.get("/digital-twin/full")
async def get_full_document():
    """Return the complete CMSDDocument as JSON."""
    if not orchestrator or not orchestrator.current_document:
        raise HTTPException(503, "Digital twin not yet available")
    doc = orchestrator.current_document
    return json.loads(doc.model_dump_json())


# ─── Change Events ──────────────────────────────────────────

@router.get("/changes")
async def get_recent_changes(limit: int = Query(50, ge=1, le=500)):
    if not event_bus:
        raise HTTPException(503, "Event bus not ready")
    return event_bus.get_recent_events(limit)


@router.get("/changes/since")
async def get_changes_since(timestamp: str = Query(..., description="ISO timestamp")):
    if not event_bus:
        raise HTTPException(503, "Event bus not ready")
    return event_bus.get_events_since(timestamp)


# ─── Orchestrator Control ────────────────────────────────────

@router.post("/start")
async def start_orchestrator():
    """Manually start the orchestrator polling loop."""
    if not orchestrator:
        raise HTTPException(503, "Service not ready")
    if orchestrator.stats.get("running"):
        return {"status": "already_running"}
    await orchestrator.start()
    logger.info("Orchestrator started via POST /start")
    return {"status": "started"}


@router.post("/stop")
async def stop_orchestrator():
    """Manually stop the orchestrator polling loop."""
    if not orchestrator:
        raise HTTPException(503, "Service not ready")
    await orchestrator.stop()
    logger.info("Orchestrator stopped via POST /stop")
    return {"status": "stopped"}


@router.post("/rebuild")
async def force_rebuild():
    if not orchestrator:
        raise HTTPException(503, "Service not ready")
    result = await orchestrator.force_rebuild()
    return result


@router.get("/health")
async def health():
    if not orchestrator:
        return {"status": "starting", "service": "cmsd-twin-service"}
    return {
        "status": "healthy",
        "service": "cmsd-twin-service",
        **orchestrator.stats,
    }


# ─── Refresh (Mapping-Driven Instance Generation) ──────────

@router.post("/refresh")
async def refresh_instances(body: dict | None = None):
    """Trigger a fetch-build-diff-publish cycle using confirmed mappings."""
    if not orchestrator:
        raise HTTPException(503, "Service not ready")
    mapping_ids = body.get("mapping_ids") if body else None
    use_hardcoded = body.get("use_hardcoded", True) if body else True
    try:
        report = await orchestrator.run_once(mapping_ids, use_hardcoded=use_hardcoded)
        return report
    except Exception as e:
        logger.exception("Refresh cycle failed")
        raise HTTPException(status_code=500, detail=f"Refresh failed: {e}")


@router.post("/refresh/validate")
async def validate_preflight(body: dict):
    """Run pre-flight check without generating."""
    if not orchestrator:
        raise HTTPException(503, "Service not ready")
    mapping_ids = body.get("mapping_ids", [])
    preflight = orchestrator.run_preflight(mapping_ids)

    # Async API reachability check
    if orchestrator._registry:
        async with APIClient() as client:
            for mid in mapping_ids:
                mapping = orchestrator._registry._mappings.get(mid, {})
                source = mapping.get("source", {})
                url = f"{source.get('base_url', '')}{source.get('endpoint', '')}"
                try:
                    await client.fetch(url, source.get("method", "GET"),
                                       auth_config=source.get("auth", {"type": "none"}))
                except Exception as e:
                    preflight["checks"]["api_reachability"]["unreachable"].append({
                        "mapping_id": mid, "url": url, "error": str(e),
                    })
                    preflight["checks"]["api_reachability"]["passed"] = False

        preflight["passed"] = (
            preflight["checks"]["dependencies"]["passed"] and
            preflight["checks"]["relations"]["passed"] and
            preflight["checks"]["field_coverage"]["passed"] and
            preflight["checks"]["api_reachability"]["passed"]
        )

    return preflight


@router.get("/refresh/status")
async def get_refresh_status():
    """Get current refresh status."""
    if not orchestrator:
        raise HTTPException(503, "Service not ready")
    return {
        "is_polling": orchestrator.is_polling,
        "poll_interval_seconds": orchestrator.poll_interval,
        "last_refreshed": orchestrator.last_refreshed_iso,
        "mappings_loaded": len(orchestrator._mapping_factory._mappings),
    }


@router.post("/refresh/polling")
async def set_polling(body: dict):
    """Configure polling. {"interval_seconds": 30} to start, 0 to stop."""
    if not orchestrator:
        raise HTTPException(503, "Service not ready")
    interval = body.get("interval_seconds", 0)
    if not isinstance(interval, int) or interval < 0:
        raise HTTPException(status_code=422, detail="interval_seconds must be a non-negative integer")
    await orchestrator.set_poll_interval(interval)
    return {
        "success": True,
        "is_polling": orchestrator.is_polling,
        "poll_interval_seconds": orchestrator.poll_interval,
    }


@router.post("/refresh/reload-mappings")
async def reload_mappings():
    """Reload mapping configuration from disk without restarting."""
    if not orchestrator:
        raise HTTPException(503, "Service not ready")
    import os
    mappings_dir = os.path.join(os.path.dirname(__file__), "..", ".agent-mappings")
    orchestrator._mapping_factory.load_mappings(mappings_dir)
    return {
        "success": True,
        "message": f"{len(orchestrator._mapping_factory._mappings)} mapping(s) reloaded",
    }


# ─── WebSocket ──────────────────────────────────────────────

@router.websocket("/ws/events")
async def websocket_events(ws: WebSocket):
    """Real-time change event stream via WebSocket."""
    if not event_bus:
        await ws.close(code=1011, reason="Event bus not ready")
        return

    await ws.accept()
    queue = event_bus.subscribe()
    logger.info("WebSocket client connected")

    try:
        # Send initial connection confirmation
        await ws.send_json({
            "event_type": "connected",
            "message": "Subscribed to CMSD change events",
            "timestamp": asyncio.get_event_loop().time(),
        })

        while True:
            event = await queue.get()
            await ws.send_json(event)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        event_bus.unsubscribe(queue)
        try:
            await ws.close()
        except Exception:
            pass