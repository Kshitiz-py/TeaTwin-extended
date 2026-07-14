"""
SAP Master Data — Bills of Materials (BOMs).

Serves BOM definitions from SAP ERP — the structured recipes that specify which
parts and sub-assemblies go into a finished product. Each BOM is a tree of
components linked to PartTypes, forming the product structure that drives
material flow in CMSD simulation.

CMSD Entity Mapping:
  - ``BillOfMaterials``      → CMSD **Bill of Materials** (root recipe)
  - ``BOMComponent``         → CMSD **BOM Component** (node in the tree)
  - Component → PartType link → resolves the CMSD Part Type consumed at each node

Key Endpoints:
  | Method | Path            | Description                                   |
  |--------|-----------------|-----------------------------------------------|
  | GET    | /boms           | List all BOM root definitions                  |
  | GET    | /boms/{id}      | Single BOM with full recursive component tree  |
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import BillOfMaterials, BOMComponent

router = APIRouter(tags=["BOMs"])


@router.get("/boms")
def list_boms(db: Session = Depends(get_db)):
    """List all BillOfMaterials root definitions.

    Returns ``count`` and ``bills_of_materials`` array with identifier, name,
    description, and the part_type_identifier the BOM produces.

    CMSD relevance: Provides the full catalog of product recipes for the
    digital twin, driving material requirement calculations in simulation.
    """
    results = db.query(BillOfMaterials).all()
    return {"count": len(results), "bills_of_materials": [_bom_to_dict(b) for b in results]}


@router.get("/boms/{identifier}")
def get_bom(identifier: str, db: Session = Depends(get_db)):
    """Get a single BOM with its full recursive component tree.

    Resolves top-level components and recursively nests sub-components,
    providing the complete hierarchical recipe. Each component references
    a PartType with quantity and sequence order.

    CMSD relevance: The component tree directly feeds the CMSD
    BillOfMaterialsComponent list, enabling material-flow simulation.
    """
    bom = db.query(BillOfMaterials).filter(BillOfMaterials.identifier == identifier).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found")
    data = _bom_to_dict(bom)
    # Build component tree (top-level only, then recursively resolve children)
    top_level = [c for c in bom.components if c.parent_component_id is None]
    data["components"] = [_component_tree(c) for c in top_level]
    return data


def _component_tree(comp: BOMComponent) -> dict:
    """Recursively build a nested component tree dict from a BOMComponent node.

    Args:
        comp: The BOMComponent ORM instance at the current tree level.

    Returns:
        A dict with all component fields plus a ``sub_components`` list
        containing child nodes resolved recursively.
    """
    node = _comp_to_dict(comp)
    if comp.children:
        node["sub_components"] = [_component_tree(child) for child in comp.children]
    return node


def _bom_to_dict(bom: BillOfMaterials) -> dict:
    """Serialize a BillOfMaterials ORM model to a JSON-safe dict.

    Includes the parent PartType reference that this BOM produces.
    """
    return {
        "identifier": bom.identifier,
        "name": bom.name,
        "description": bom.description,
        "part_type_identifier": bom.part_type_ref.identifier if bom.part_type_ref else None,
    }


def _comp_to_dict(c: BOMComponent) -> dict:
    """Serialize a BOMComponent ORM model to a JSON-safe dict.

    Includes the referenced PartType (what material is consumed), quantity
    needed, and sequence order for assembly sequencing.
    """
    return {
        "identifier": c.identifier,
        "part_type_identifier": c.part_type_ref.identifier if c.part_type_ref else None,
        "part_type_name": c.part_type_ref.name if c.part_type_ref else None,
        "quantity": c.quantity,
        "sequence_order": c.sequence_order,
    }
