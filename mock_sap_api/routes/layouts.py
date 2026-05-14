"""Layouts and Placements endpoints"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Layout

router = APIRouter(tags=["Layouts"])


@router.get("/layouts")
def list_layouts(db: Session = Depends(get_db)):
    results = db.query(Layout).all()
    return {"count": len(results), "layouts": [_layout_to_dict(l) for l in results]}


@router.get("/layouts/{identifier}")
def get_layout(identifier: str, db: Session = Depends(get_db)):
    layout = db.query(Layout).filter(Layout.identifier == identifier).first()
    if not layout:
        raise HTTPException(status_code=404, detail="Layout not found")
    data = _layout_to_dict(layout)
    data["placements"] = [
        {
            "resource_identifier": p.resource_ref.identifier,
            "resource_name": p.resource_ref.name,
            "x": p.x, "y": p.y, "z": p.z,
            "rotation": {"x_deg": p.rotation_x_deg, "y_deg": p.rotation_y_deg, "z_deg": p.rotation_z_deg},
            "scale": {"x_percent": p.scale_x_percent, "y_percent": p.scale_y_percent, "z_percent": p.scale_z_percent},
        }
        for p in layout.placements
    ]
    return data


def _layout_to_dict(l: Layout) -> dict:
    return {
        "identifier": l.identifier,
        "name": l.name,
        "description": l.description,
        "coordinate_system": l.coordinate_system,
        "placement_count": len(l.placements),
    }