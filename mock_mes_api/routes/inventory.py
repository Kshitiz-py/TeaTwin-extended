"""Inventory endpoints (MES)"""

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
    inv = db.query(Inventory).filter(Inventory.identifier == identifier).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return _inv_to_dict(inv)


def _inv_to_dict(i: Inventory) -> dict:
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