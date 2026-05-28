"""
SAP Master Data — Production Orders & Order Lines.

Serves production order definitions from SAP ERP. An Order is a manufacturing
request specifying what to produce, how much, and by when. Each Order contains
OrderLines that link a PartType to a ProcessPlan, forming the demand signal
that drives CMSD simulation job generation.

CMSD Entity Mapping:
  - ``Order``        → CMSD **Order** (header: status, due date, priority)
  - ``OrderLine``    → CMSD **Order Line** (line item: PartType + ProcessPlan + quantity)
  - OrderLine → PartType      → resolves the CMSD Part Type to produce
  - OrderLine → ProcessPlan   → resolves the CMSD Process Plan (routing recipe)

Key Endpoints:
  | Method | Path            | Description                                        |
  |--------|-----------------|----------------------------------------------------|
  | GET    | /orders         | List orders (filterable by status, priority)        |
  | GET    | /orders/{id}    | Single order with all order lines                   |
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models import Order

router = APIRouter(tags=["Orders"])


@router.get("/orders")
def list_orders(
    status: Optional[str] = Query(None, description="Filter by status (created, released, completed, shipped, cancelled)"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    db: Session = Depends(get_db),
):
    """List production Orders, optionally filtered by status or priority.

    Returns ``count`` and ``orders`` array with identifier, status, due/release
    dates, priority, and line_count.

    CMSD relevance: Provides the demand catalog for the digital twin.
    Each Order represents a unit of demand that drives job scheduling
    and material reservation in CMSD simulation.
    """
    q = db.query(Order)
    if status:
        q = q.filter(Order.status == status)
    if priority:
        q = q.filter(Order.priority == priority)
    results = q.all()
    return {"count": len(results), "orders": [_order_to_dict(o) for o in results]}


@router.get("/orders/{identifier}")
def get_order(identifier: str, db: Session = Depends(get_db)):
    """Get a single Order with all OrderLines.

    Each OrderLine includes the PartType to produce, quantity, due/release
    dates, status, and the ProcessPlan (routing) reference. This complete
    demand-to-routing chain is essential for CMSD job creation.

    CMSD relevance: Directly feeds CMSD Order → OrderLine entities.
    The ProcessPlan reference on each line enables the orchestrator to
    generate CMSD Jobs with the correct routing.
    """
    o = db.query(Order).filter(Order.identifier == identifier).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    data = _order_to_dict(o)
    data["order_lines"] = [
        {
            "identifier": ol.identifier,
            "part_type_identifier": ol.part_type_ref.identifier if ol.part_type_ref else None,
            "quantity": ol.quantity,
            "due_date": ol.due_date.isoformat() if ol.due_date else None,
            "release_date": ol.release_date.isoformat() if ol.release_date else None,
            "status": ol.status,
            "process_plan_identifier": ol.process_plan_ref.identifier if ol.process_plan_ref else None,
        }
        for ol in o.order_lines
    ]
    return data


def _order_to_dict(o: Order) -> dict:
    """Serialize an Order ORM model to a JSON-safe dict.

    Includes order-level attributes: status, scheduling dates, priority,
    and a count of child order lines for quick demand visibility.
    """
    return {
        "identifier": o.identifier,
        "status": o.status,
        "due_date": o.due_date.isoformat() if o.due_date else None,
        "release_date": o.release_date.isoformat() if o.release_date else None,
        "priority": o.priority,
        "line_count": len(o.order_lines),
    }
