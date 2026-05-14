"""Bills of Materials endpoints"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import BillOfMaterials, BOMComponent

router = APIRouter(tags=["BOMs"])


@router.get("/boms")
def list_boms(db: Session = Depends(get_db)):
    results = db.query(BillOfMaterials).all()
    return {"count": len(results), "bills_of_materials": [_bom_to_dict(b) for b in results]}


@router.get("/boms/{identifier}")
def get_bom(identifier: str, db: Session = Depends(get_db)):
    bom = db.query(BillOfMaterials).filter(BillOfMaterials.identifier == identifier).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found")
    data = _bom_to_dict(bom)
    # Build component tree (top-level only, then recursively resolve children)
    top_level = [c for c in bom.components if c.parent_component_id is None]
    data["components"] = [_component_tree(c) for c in top_level]
    return data


def _component_tree(comp: BOMComponent) -> dict:
    node = _comp_to_dict(comp)
    if comp.children:
        node["sub_components"] = [_component_tree(child) for child in comp.children]
    return node


def _bom_to_dict(bom: BillOfMaterials) -> dict:
    return {
        "identifier": bom.identifier,
        "name": bom.name,
        "description": bom.description,
        "part_type_identifier": bom.part_type_ref.identifier if bom.part_type_ref else None,
    }


def _comp_to_dict(c: BOMComponent) -> dict:
    return {
        "identifier": c.identifier,
        "part_type_identifier": c.part_type_ref.identifier if c.part_type_ref else None,
        "part_type_name": c.part_type_ref.name if c.part_type_ref else None,
        "quantity": c.quantity,
        "sequence_order": c.sequence_order,
    }