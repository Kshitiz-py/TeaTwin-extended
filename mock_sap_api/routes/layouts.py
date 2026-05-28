"""
SAP Master Data — Factory Layouts & Resource Placements.

Serves spatial layout definitions from SAP ERP. A Layout defines the factory
floor coordinate system and maps each Resource to a physical position (x, y, z),
rotation, and scale. Together with Connections, layouts form the spatial
topology that enables CMSD material-flow and distance-based simulation.

CMSD Entity Mapping:
  - ``Layout``                     → CMSD **Layout** (coordinate system + extents)
  - ``ResourcePlacement`` (via Placement table) → CMSD **Resource Placement**
  - Placement → Resource           → resolves which CMSD Resource is at each position

Coordinate Systems Supported:
  - ``upperLeftBased``  — origin at upper-left corner (common in 2D factory plans)
  - ``lowerLeftBased``  — origin at lower-left corner (standard CAD convention)
  - ``centerBased``     — origin at layout center

Key Endpoints:
  | Method | Path               | Description                                          |
  |--------|--------------------|------------------------------------------------------|
  | GET    | /layouts           | List all layout definitions                           |
  | GET    | /layouts/{id}      | Single layout with all resource placements            |
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Layout

router = APIRouter(tags=["Layouts"])


@router.get("/layouts")
def list_layouts(db: Session = Depends(get_db)):
    """List all Layout definitions.

    Returns ``count`` and ``layouts`` array with identifier, name, description,
    coordinate system type, and the number of resource placements.

    CMSD relevance: Provides the spatial canvas for the digital twin's
    factory topology visualization and distance-based routing calculations.
    """
    results = db.query(Layout).all()
    return {"count": len(results), "layouts": [_layout_to_dict(l) for l in results]}


@router.get("/layouts/{identifier}")
def get_layout(identifier: str, db: Session = Depends(get_db)):
    """Get a single Layout with all Resource Placements.

    Each placement includes the Resource reference, 3D position (x, y, z),
    rotation angles (x/y/z degrees), and scale percentages. This provides
    the complete spatial map of the factory floor.

    CMSD relevance: Directly populates CMSD Layout → ResourcePlacement
    entities, enabling spatial visualization, distance calculations between
    resources, and transport-time estimation in simulation.
    """
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
    """Serialize a Layout ORM model to a JSON-safe dict.

    Includes the coordinate_system enum value (upperLeftBased, lowerLeftBased,
    or centerBased) and the count of resource placements in this layout.
    """
    return {
        "identifier": l.identifier,
        "name": l.name,
        "description": l.description,
        "coordinate_system": l.coordinate_system,
        "placement_count": len(l.placements),
    }


