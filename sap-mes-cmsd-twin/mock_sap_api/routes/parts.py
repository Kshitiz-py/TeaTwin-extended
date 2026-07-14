"""
SAP Master Data — Parts & Part Types.

Serves Part Type definitions (product templates) and Part instances (physical
units) from SAP ERP, mapped to the CMSD (Core Manufacturing Simulation Data)
information model.

CMSD Entity Mapping:
  - ``PartType`` → CMSD **Part Type** (dimensions, weight, color, 3D shape)
  - ``Part``     → CMSD **Part** (instance with location, lot, production status)

Key Endpoints:
  | Method | Path                   | Description                                      |
  |--------|------------------------|--------------------------------------------------|
  | GET    | /part-types            | List all part type definitions                    |
  | GET    | /part-types/{id}       | Single part type with linked BOMs & process plans |
  | GET    | /parts                 | List part instances (filterable by type, status)  |
  | GET    | /parts/{id}            | Single part instance with parent PartType          |
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models import PartType, Part

router = APIRouter(tags=["Parts"])


@router.get("/part-types")
def list_part_types(db: Session = Depends(get_db)):
    """List all PartType definitions.

    Returns a JSON object with ``count`` and ``part_types`` array.
    Each entry includes identifier, name, description, physical dimensions,
    weight, color, and 3D shape reference.

    CMSD relevance: Feeds Part Type entities into the digital twin.
    """
    results = db.query(PartType).all()
    return {"count": len(results), "part_types": [_pt_to_dict(pt) for pt in results]}


@router.get("/part-types/{identifier}")
def get_part_type(identifier: str, db: Session = Depends(get_db)):
    """Get a single PartType by identifier.

    Returns the full PartType record with linked BOMs and process plans,
    allowing the twin to resolve which recipes and routings apply to this part.

    CMSD relevance: Resolves the PartType → BOM → ProcessPlan chain for
    building the complete CMSD production model.
    """
    pt = db.query(PartType).filter(PartType.identifier == identifier).first()
    if not pt:
        raise HTTPException(status_code=404, detail="Part type not found")
    data = _pt_to_dict(pt)
    data["boms"] = [{"identifier": b.identifier, "name": b.name} for b in pt.boms]
    data["process_plans"] = [{"identifier": pp.identifier, "name": pp.name} for pp in pt.process_plans]
    return data


@router.get("/parts")
def list_parts(
    part_type_id: Optional[int] = None,
    production_status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List Part instances, optionally filtered by part_type_id or status.

    Returns ``count`` and ``parts`` array with identifier, part_type_id,
    production status, 3D location, and lot number.

    CMSD relevance: Part instances represent WIP inventory in the digital twin.
    Filtering by status supports order-tracking and location-based queries.
    """
    q = db.query(Part)
    if part_type_id:
        q = q.filter(Part.part_type_id == part_type_id)
    if production_status:
        q = q.filter(Part.production_status == production_status)
    results = q.all()
    return {"count": len(results), "parts": [_part_to_dict(p) for p in results]}


@router.get("/parts/{identifier}")
def get_part(identifier: str, db: Session = Depends(get_db)):
    """Get a single Part instance by identifier.

    Returns the part with its PartType parent details, combining instance
    state (location, lot, status) with the template definition.

    CMSD relevance: Provides the full Part + PartType context needed for
    CMSD Part entities in the digital twin.
    """
    p = db.query(Part).filter(Part.identifier == identifier).first()
    if not p:
        raise HTTPException(status_code=404, detail="Part not found")
    data = _part_to_dict(p)
    if p.part_type_ref:
        data["part_type"] = _pt_to_dict(p.part_type_ref)
    return data


def _pt_to_dict(pt: PartType) -> dict:
    """Serialize a PartType ORM model to a JSON-safe dict.

    Includes physical dimensions (size, weight), visual attributes (color, 3D shape),
    and metadata. Used internally to construct CMSD PartType representations.
    """
    return {
        "identifier": pt.identifier,
        "name": pt.name,
        "description": pt.description,
        "size": {"length": pt.size_length, "width": pt.size_width, "height": pt.size_height},
        "weight_kg": pt.weight_kg,
        "color": pt.color,
        "shape_3d": pt.shape_3d,
    }


def _part_to_dict(p: Part) -> dict:
    """Serialize a Part ORM model to a JSON-safe dict.

    Includes instance-level fields: PartType reference, production status,
    3D location in the factory layout, and lot number for traceability.
    """
    return {
        "identifier": p.identifier,
        "part_type_id": p.part_type_id,
        "production_status": p.production_status,
        "location": {"x": p.location_x, "y": p.location_y, "z": p.location_z},
        "lot_number": p.lot_number,
    }
