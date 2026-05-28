"""
SAP Master Data — Resource Connections (Material-Flow Graph).

Serves the factory's material-flow network from SAP ERP. A Connection defines a
directed edge (from_resource → to_resource) between two manufacturing
resources, forming a directed graph that describes how material, parts, and
assemblies traverse the production line. Combined with Layout placements,
connections complete the full spatial-material topology for CMSD simulation.

CMSD Entity Mapping:
  - ``Connection``                    → CMSD **Connection** (directed arc)
  - Connection.from_resource         → CMSD **Resource** (source node)
  - Connection.to_resource           → CMSD **Resource** (sink node)
  - connection_type + connection_name → categorise the CMSD **Material Flow Link**

Together, Layouts + Connections enable:
  - Shortest-path routing between any two resources
  - Transport-time estimation for material movement
  - Bottleneck analysis on the material-flow graph

Key Endpoints:
  | Method | Path                 | Description                                    |
  |--------|----------------------|------------------------------------------------|
  | GET    | /connections         | List all directed connections                  |
  | GET    | /connections/{id}    | Single connection with from/to resource details |
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Connection

router = APIRouter(tags=["Connections"])


@router.get("/connections")
def list_connections(db: Session = Depends(get_db)):
    """List all material-flow Connections.

    Returns ``count`` and ``connections`` array, each with from_resource and
    to_resource details (identifier, name, resource_type), connection_type,
    and connection_name.

    CMSD relevance: Provides the complete adjacency list for the factory's
    directed material-flow graph, enabling path-finding and flow analysis
    in the digital twin.
    """
    results = db.query(Connection).all()
    return {"count": len(results), "connections": [_conn_to_dict(c) for c in results]}


@router.get("/connections/{identifier}")
def get_connection(identifier: str, db: Session = Depends(get_db)):
    """Get a single Connection with full from/to Resource details.

    Returns both endpoints of the directed arc — the source resource (where
    material departs) and the sink resource (where material arrives) — along
    with the connection type and name.

    CMSD relevance: Each connection directly maps to a CMSD **Connection**
    entity linking two CMSD Resources. The connection type can be used to
    select transport mode (conveyor, AGV, manual) in simulation.
    """
    conn = db.query(Connection).filter(Connection.identifier == identifier).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    return _conn_to_dict(conn)


def _conn_to_dict(c: Connection) -> dict:
    """Serialize a Connection ORM model to a JSON-safe dict.

    Includes both endpoint Resources (identifier, name, resource_type),
    the connection_type (e.g. conveyor, AGV path, pipe), and a human-readable
    connection_name for graph visualisation and query labels.
    """
    return {
        "identifier": c.identifier,
        "from_resource": {
            "identifier": c.from_resource.identifier,
            "name": c.from_resource.name,
            "resource_type": c.from_resource.resource_type,
        },
        "to_resource": {
            "identifier": c.to_resource.identifier,
            "name": c.to_resource.name,
            "resource_type": c.to_resource.resource_type,
        },
        "connection_type": c.connection_type,
        "connection_name": c.connection_name,
    }
