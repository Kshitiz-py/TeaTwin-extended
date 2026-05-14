"""Parts and Part Types endpoints"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models import PartType, Part

router = APIRouter(tags=["Parts"])


@router.get("/part-types")
def list_part_types(db: Session = Depends(get_db)):
    results = db.query(PartType).all()
    return {"count": len(results), "part_types": [_pt_to_dict(pt) for pt in results]}


@router.get("/part-types/{identifier}")
def get_part_type(identifier: str, db: Session = Depends(get_db)):
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
    q = db.query(Part)
    if part_type_id:
        q = q.filter(Part.part_type_id == part_type_id)
    if production_status:
        q = q.filter(Part.production_status == production_status)
    results = q.all()
    return {"count": len(results), "parts": [_part_to_dict(p) for p in results]}


@router.get("/parts/{identifier}")
def get_part(identifier: str, db: Session = Depends(get_db)):
    p = db.query(Part).filter(Part.identifier == identifier).first()
    if not p:
        raise HTTPException(status_code=404, detail="Part not found")
    data = _part_to_dict(p)
    if p.part_type_ref:
        data["part_type"] = _pt_to_dict(p.part_type_ref)
    return data


def _pt_to_dict(pt: PartType) -> dict:
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
    return {
        "identifier": p.identifier,
        "part_type_id": p.part_type_id,
        "production_status": p.production_status,
        "location": {"x": p.location_x, "y": p.location_y, "z": p.location_z},
        "lot_number": p.lot_number,
    }