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

logger = logging.getLogger("cmsd-twin.routes")

router = APIRouter(tags=["CMSD Digital Twin"])


# Will be set by main.py at startup
orchestrator: CMSDOrchestrator | None = None
event_bus: EventBus | None = None


def init(orch: CMSDOrchestrator, bus: EventBus):
    global orchestrator, event_bus
    orchestrator = orch
    event_bus = bus


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
    return [
        {
            "identifier": r.identifier,
            "name": r.name,
            "resource_type": r.resource_type.value if hasattr(r.resource_type, "value") else str(r.resource_type),
            "current_status": r.current_status.value if r.current_status and hasattr(r.current_status, "value") else str(r.current_status) if r.current_status else None,
            "availability": float(r.availability) if r.availability else None,
            "capacity": r.capacity,
        }
        for r in doc.resources
    ]


@router.get("/digital-twin/orders")
async def get_orders():
    if not orchestrator or not orchestrator.current_document:
        raise HTTPException(503, "Digital twin not yet available")
    doc = orchestrator.current_document
    return [
        {
            "identifier": o.identifier,
            "status": o.status.value if o.status and hasattr(o.status, "value") else str(o.status) if o.status else None,
            "due_date": str(o.due_date) if o.due_date else None,
            "line_count": len(o.order_lines),
        }
        for o in doc.orders
    ]


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