"""Production Orders endpoints"""

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
    q = db.query(Order)
    if status:
        q = q.filter(Order.status == status)
    if priority:
        q = q.filter(Order.priority == priority)
    results = q.all()
    return {"count": len(results), "orders": [_order_to_dict(o) for o in results]}


@router.get("/orders/{identifier}")
def get_order(identifier: str, db: Session = Depends(get_db)):
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
    return {
        "identifier": o.identifier,
        "status": o.status,
        "due_date": o.due_date.isoformat() if o.due_date else None,
        "release_date": o.release_date.isoformat() if o.release_date else None,
        "priority": o.priority,
        "line_count": len(o.order_lines),
    }