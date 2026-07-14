"""
CMSDFactory — Converts SAP/MES API responses into a CMSDDocument (Pydantic model).
This is the bridge from raw API data to the typed CMSD digital twin.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cmsd-pydantic-master", "src"))

from decimal import Decimal
from typing import Any

from cmsd_schema.cmsd_document import CMSDDocument
from cmsd_schema.resource_entities import Resource, ResourceClass
from cmsd_schema.part_entities import PartType, Part, BillOfMaterials, BillOfMaterialsComponent
from cmsd_schema.process_planning import ProcessPlan, Process
from cmsd_schema.order_entities import Order, OrderLine, OrderLinePartDescription
from cmsd_schema.calendar_entities import Calendar, Shift, Break, Holiday
from cmsd_schema.basic_structures import Duration, GrossDimensions
from cmsd_schema.basic_types import ResourceType, ResourceStatus, Day, OrderStatus, JobStatus
from cmsd_schema.production_operations import Job, JobEffortDescription
from cmsd_schema.inventory_entities import InventoryItem
from cmsd_schema.maintenance_entities import MaintenancePlan
from cmsd_schema.connection_entities import Connection


class CMSDFactory:
    """Builds a complete CMSDDocument from SAP + MES API data."""

    def build(self, sap_data: dict[str, Any], mes_data: dict[str, Any]) -> CMSDDocument:
        doc = CMSDDocument()

        # SAP Master Data
        doc.resource_classes = self._build_resource_classes(sap_data.get("resource_classes", {}))
        doc.resources = self._build_resources(sap_data.get("resources", {}))
        doc.part_types = self._build_part_types(sap_data.get("part_types", {}))
        doc.parts = self._build_parts(sap_data.get("parts", {}))
        doc.bills_of_materials = self._build_boms(sap_data.get("boms", {}))
        doc.process_plans = self._build_process_plans(sap_data.get("process_plans", {}))
        doc.orders = self._build_orders(sap_data.get("orders", {}))
        doc.calendars = self._build_calendars(sap_data.get("calendars", {}))
        # layouts stored as generic list
        doc.layouts = sap_data.get("layouts", {}).get("layouts", [])
        doc.connections = self._build_connections(sap_data.get("connections", {}))

        # MES Operational Data
        self._apply_mes_status(doc, mes_data.get("resource_statuses", {}))
        doc.jobs = self._build_jobs(mes_data.get("jobs", {}))
        doc.inventory_items = self._build_inventory(mes_data.get("inventory", {}))
        doc.maintenance_plans = self._build_maintenance(mes_data.get("incidents", {}))

        return doc

    def _build_resource_classes(self, data: dict) -> list[ResourceClass]:
        results = []
        for item in data.get("resource_classes", []):
            results.append(ResourceClass(
                identifier=item["identifier"],
                name=item["name"],
                description=item.get("description"),
                resource_type=ResourceType(item["resource_type"]),
            ))
        return results

    def _build_resources(self, data: dict) -> list[Resource]:
        results = []
        for item in data.get("resources", []):
            results.append(Resource(
                identifier=item["identifier"],
                name=item["name"],
                description=item.get("description"),
                resource_type=ResourceType(item["resource_type"]),
                capacity=item.get("capacity"),
                availability=_to_decimal(item.get("availability")),
                mttr=_to_duration(item.get("mttr_seconds")),
                mtbf=_to_duration(item.get("mtbf_seconds")),
                mcbf=item.get("mcbf"),
                reliability=_to_decimal(item.get("reliability")),
                cycle_time=_to_duration(item.get("cycle_time_seconds")),
                size=_to_dimensions(item.get("size")),
                decision_rule=item.get("decision_rule"),
                routing_rule=item.get("routing_rule"),
                transport_capacity=item.get("transport_capacity"),
                worker_count=item.get("worker_count"),
            ))
        return results

    def _build_part_types(self, data: dict) -> list[PartType]:
        results = []
        for item in data.get("part_types", []):
            results.append(PartType(
                identifier=item["identifier"],
                name=item["name"],
                description=item.get("description"),
                size=_to_dimensions(item.get("size")),
                weight=_to_weight(item.get("weight_kg")),
            ))
        return results

    def _build_parts(self, data: dict) -> list[Part]:
        results = []
        for item in data.get("parts", []):
            results.append(Part(
                identifier=item["identifier"],
                production_status=item.get("production_status"),
                size=_to_dimensions(item.get("size")),
            ))
        return results

    def _build_boms(self, data: dict) -> list[BillOfMaterials]:
        results = []
        for item in data.get("bills_of_materials", []):
            bom = BillOfMaterials(
                identifier=item["identifier"],
                name=item.get("name"),
                description=item.get("description"),
            )
            for comp in item.get("components", []):
                bom.components.append(BillOfMaterialsComponent(
                    identifier=comp["identifier"],
                    quantity=Decimal(str(comp.get("quantity", 1))),
                ))
            results.append(bom)
        return results

    def _build_process_plans(self, data: dict) -> list[ProcessPlan]:
        results = []
        for item in data.get("process_plans", []):
            pp = ProcessPlan(
                identifier=item["identifier"],
                name=item["name"],
                description=item.get("description"),
            )
            for proc in item.get("processes", []):
                pp.processes.append(Process(
                    identifier=proc["identifier"],
                    name=proc["name"],
                    description=proc.get("description"),
                    duration=_to_duration(proc.get("duration_seconds")),
                    setup_time=_to_duration(proc.get("setup_time_seconds")),
                    load_time=_to_duration(proc.get("load_time_seconds")),
                    unload_time=_to_duration(proc.get("unload_time_seconds")),
                ))
            results.append(pp)
        return results

    def _build_orders(self, data: dict) -> list[Order]:
        results = []
        for item in data.get("orders", []):
            order = Order(
                identifier=item["identifier"],
                status=OrderStatus(item["status"]) if item.get("status") else None,
                due_date=item.get("due_date"),
                release_date=item.get("release_date"),
            )
            for ol in item.get("order_lines", []):
                order.order_lines.append(OrderLine(
                    identifier=ol["identifier"],
                    status=OrderStatus(ol["status"]) if ol.get("status") else None,
                    due_date=ol.get("due_date"),
                    release_date=ol.get("release_date"),
                    part_description=OrderLinePartDescription(
                        identifier=f"pd-{ol['identifier']}",
                        quantity=ol.get("quantity", 0),
                    ) if ol.get("part_type_identifier") else None,
                ))
            results.append(order)
        return results

    def _build_calendars(self, data: dict) -> list[Calendar]:
        results = []
        for item in data.get("calendars", []):
            cal = Calendar(
                identifier=item["identifier"],
                name=item["name"],
                description=item.get("description"),
                production_days_per_year=item.get("production_days_per_year"),
            )
            for s in item.get("shifts", []):
                shift = Shift(
                    identifier=s["identifier"],
                    day_of_week=Day(s["day_of_week"]),
                    start_time=s["start_time"],
                    end_time=s["end_time"],
                )
                for b in s.get("breaks", []):
                    shift.breaks.append(Break(
                        identifier=b["identifier"],
                        start_time=b["start_time"],
                        end_time=b["end_time"],
                    ))
                cal.shifts.append(shift)
            for h in item.get("holidays", []):
                cal.holidays.append(Holiday(
                    identifier=h["identifier"],
                    holiday_date=h["date"],
                ))
            results.append(cal)
        return results

    def _build_connections(self, data: dict) -> list[Connection]:
        results = []
        for item in data.get("connections", []):
            results.append(Connection(
                identifier=item["identifier"],
                from_resource_id=item["from_resource"]["identifier"],
                to_resource_id=item["to_resource"]["identifier"],
                connection_type=item.get("connection_type", "output"),
            ))
        return results

    def _apply_mes_status(self, doc: CMSDDocument, data: dict):
        status_map = {rs["resource_identifier"]: rs for rs in data.get("resource_statuses", [])}
        for resource in doc.resources:
            if resource.identifier in status_map:
                rs = status_map[resource.identifier]
                resource.current_status = ResourceStatus(rs["status"]) if rs.get("status") else None

    def _build_jobs(self, data: dict) -> list[Job]:
        results = []
        for item in data.get("jobs", []):
            job = Job(
                identifier=item["identifier"],
                status=JobStatus(item["status"]),
                priority=item.get("priority"),
            )
            if item.get("start_time"):
                job.planned_effort = JobEffortDescription(start_time=item["start_time"])
            results.append(job)
        return results

    def _build_inventory(self, data: dict) -> list[InventoryItem]:
        results = []
        for item in data.get("inventory", []):
            results.append(InventoryItem(
                identifier=item["identifier"],
                quantity=Decimal(str(item.get("quantity", 0))),
            ))
        return results

    def _build_maintenance(self, data: dict) -> list[MaintenancePlan]:
        results = []
        for item in data.get("incidents", []):
            if item.get("status") not in ("resolved",):
                results.append(MaintenancePlan(
                    identifier=f"MP-{item['identifier']}",
                    name=f"Incident: {item.get('incident_type', 'Unknown')}",
                    description=item.get("description"),
                ))
        return results


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _to_duration(seconds: Any) -> Duration | None:
    if seconds is None:
        return None
    return Duration(unit="second", value=Decimal(str(seconds)))


def _to_weight(value: Any):
    """Convert to CMSD Weight dict format."""
    if value is None:
        return None
    return {"value": Decimal(str(value)), "unit": "kilogram"}


def _to_dimensions(size: dict | None) -> GrossDimensions | None:
    if not size:
        return None
    length = size.get("length")
    width = size.get("width")
    height = size.get("height")
    if length is None and width is None and height is None:
        return None
    return GrossDimensions(
        length=Decimal(str(length or 0)),
        width=Decimal(str(width or 0)),
        height=Decimal(str(height or 0)),
    )