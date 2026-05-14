"""Resource Connections (material flow) endpoints"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Connection

router = APIRouter(tags=["Connections"])


@router.get("/connections")
def list_connections(db: Session = Depends(get_db)):
    results = db.query(Connection).all()
    return {"count": len(results), "connections": [_conn_to_dict(c) for c in results]}


@router.get("/connections/{identifier}")
def get_connection(identifier: str, db: Session = Depends(get_db)):
    conn = db.query(Connection).filter(Connection.identifier == identifier).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    return _conn_to_dict(conn)


def _conn_to_dict(c: Connection) -> dict:
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