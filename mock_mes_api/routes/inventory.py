"""
MES Operational Data — Live Inventory (WIP Buffers & Storage Locations).

Serves live inventory levels from the Mock MES. Each InventoryItem tracks
the quantity of a PartType at a specific storage Location (resource acting
as a buffer or warehouse), with configurable min/max thresholds for
replenishment alerts and lot-level traceability.

SAP vs MES Distinction:
  - **SAP (Master Data):** Parts are *static* instances with a location and
    production status — a snapshot of what exists.
  - **MES (Operational Data):** Inventory is *dynamic* — quantities rise and
    fall in real time as production consumes or produces parts. Min/max
    thresholds enable automatic replenishment signals.

  The digital twin uses SAP Part definitions as the catalog and MES
  Inventory levels as the live material-availability state for CMSD
  simulation.

CMSD Entity Mapping:
  - ``InventoryItem``              → CMSD **Inventory Item**
  - Inventory → PartType           → resolves which CMSD Part Type is tracked
  - Inventory → Location (Resource) → resolves the CMSD buffer/warehouse resource

Key Endpoints:
  | Method | Path                 | Description                                      |
  |--------|----------------------|--------------------------------------------------|
  | GET    | /inventory           | List inventory (filterable by part, location, threshold) |
  | GET    | /inventory/{id}      | Single inventory record with PartType & location  |
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from mock_sap_api.models import Inventory

router = APIRouter(tags=["Inventory"])


@router.get("/inventory")
def list_inventory(
    part_type_id: int | None = Query(None),
    location_id: int | None = Query(None),
    below_threshold: bool = Query(False, description="Only items below min threshold"),
    db: Session = Depends(get_db),
):
    """List live inventory records with optional filters.

    Filter by PartType (part_type_id), storage Location (location_id), or
    threshold alerts (below_threshold=True returns only items at or below
    their min_threshold).

    Returns ``count`` and ``inventory`` array with quantity, thresholds,
    PartType references, Location references, lot number, and last_updated
    timestamp.

    CMSD relevance: Provides real-time material availability for the digital
    twin. Low-threshold items can trigger replenishment logic in CMSD
    simulation, and quantity levels feed WIP tracking dashboards.
    """
    q = db.query(Inventory)
    if part_type_id:
        q = q.filter(Inventory.part_type_id == part_type_id)
    if location_id:
        q = q.filter(Inventory.location_id == location_id)
    if below_threshold:
        q = q.filter(Inventory.quantity <= Inventory.min_threshold)
    results = q.all()
    return {"count": len(results), "inventory": [_inv_to_dict(i) for i in results]}


@router.get("/inventory/{identifier}")
def get_inventory_item(identifier: str, db: Session = Depends(get_db)):
    """Get a single InventoryItem by identifier.

    Returns the PartType details, current quantity, min/max thresholds,
    storage Location (buffer/warehouse resource), lot number, and last
    update timestamp.

    CMSD relevance: Each record maps directly to a CMSD **Inventory Item**
    entity, providing the per-location, per-part-type stock level that
    drives material-availability calculations in simulation.
    """
    inv = db.query(Inventory).filter(Inventory.identifier == identifier).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return _inv_to_dict(inv)


def _inv_to_dict(i: Inventory) -> dict:
    """Serialize an Inventory ORM model to a JSON-safe dict.

    Includes the PartType reference (what material), current quantity,
    configurable min/max thresholds for replenishment logic, storage
    Location reference (buffer/warehouse), lot number for traceability,
    and the last_updated timestamp for freshness checks.
    """
    return {
        "identifier": i.identifier,
        "part_type_identifier": i.part_type_ref.identifier,
        "part_type_name": i.part_type_ref.name,
        "quantity": i.quantity,
        "min_threshold": i.min_threshold,
        "max_threshold": i.max_threshold,
        "location_identifier": i.location_ref.identifier if i.location_ref else None,
        "location_name": i.location_ref.name if i.location_ref else None,
        "lot_number": i.lot_number,
        "last_updated": i.last_updated.isoformat() if i.last_updated else None,
    }
