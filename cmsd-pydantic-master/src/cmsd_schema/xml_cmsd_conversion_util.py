"""
CMSD XML Conversion Utilities

This module provides functions to convert Pydantic CMSD models to valid XML
that conforms to the CMSD v1.0 RELAX NG schema.
"""

from enum import Enum
from typing import Any, List, Optional
from decimal import Decimal
from datetime import datetime, date, time
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from .cmsd_document import CMSDDocument
from .part_entities import PartType, Part, BillOfMaterials, PartGroup
from .resource_entities import ResourceClass, Resource, ResourcesRequired
from .process_planning import ProcessPlan, Process, ProcessGroup
from .production_operations import Job
from .basic_structures import Property, GrossDimensions, Weight, Duration, ElapsedTime, Currency
from .calendar_entities import Calendar, Shift, ShiftSchedule, Holiday, AvailabilityException, Break
from .schedule_entities import Schedule, ScheduleItem, ScheduleItemEffortDescription
from .order_entities import Order, OrderLine
from .inventory_entities import InventoryItem, InventoryItemClass
from .setup_entities import SetupDefinition, SetupChangeoverDefinition
from .skill_entities import SkillDefinition, SkillLevel
from .distribution_definition import DistributionDefinition
from .maintenance_entities import MaintenancePlan, MaintenanceProcess
from .reference_material import ReferenceMaterial
from .cost_allocation import CostAllocationData
from .connection_entities import Connection
from .layout import Layout, LayoutObject, Placement


# CMSD namespace
CMSD_NAMESPACE = "urn:cmsd:main"
CMSD_NS = f"{{{CMSD_NAMESPACE}}}"


def prettify_xml(elem: Element) -> str:
    """Return a pretty-printed XML string."""
    rough_string = tostring(elem, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def add_optional_element(parent: Element, tag: str, value: Any, namespace: str = ""):
    """Add an element only if value is not None."""
    if value is not None:
        ns_tag = f"{namespace}{tag}" if namespace else tag
        elem = SubElement(parent, ns_tag)

        if isinstance(value, (datetime, date, time)):
            elem.text = value.isoformat()
        elif isinstance(value, Decimal):
            elem.text = str(value)
        elif isinstance(value, bool):
            elem.text = "true" if value else "false"
        elif isinstance(value, Enum):
            elem.text = value.value
        else:
            elem.text = str(value)
        return elem
    return None


def add_properties(parent: Element, properties: List[Property]):
    """Add Property elements to parent."""
    for prop in properties:
        prop_elem = SubElement(parent, "Property")
        add_optional_element(prop_elem, "Name", prop.name)
        if prop.description:
            add_optional_element(prop_elem, "Description", prop.description)
        if prop.unit:
            add_optional_element(prop_elem, "Unit", prop.unit)
        if prop.value:
            add_optional_element(prop_elem, "Value", prop.value)
        elif prop.distribution:
            add_distribution(prop_elem, "Distribution", prop.distribution)


def add_gross_dimensions(parent: Element, tag: str, dimensions: GrossDimensions):
    """Add GrossDimensions element."""
    dim_elem = SubElement(parent, tag)
    if dimensions.unit:
        add_optional_element(dim_elem, "Unit", dimensions.unit)
    add_optional_element(dim_elem, "Width", dimensions.width)
    add_optional_element(dim_elem, "Depth", dimensions.depth)
    add_optional_element(dim_elem, "Height", dimensions.height)


def add_weight(parent: Element, tag: str, weight: Weight):
    """Add Weight element."""
    weight_elem = SubElement(parent, tag)
    if weight.unit:
        add_optional_element(weight_elem, "Unit", weight.unit)
    add_optional_element(weight_elem, "Value", weight.value)


def add_duration(parent: Element, tag: str, duration: Duration):
    """Add Duration element."""
    dur_elem = SubElement(parent, tag)
    if duration.unit:
        add_optional_element(dur_elem, "Unit", duration.unit)

    if duration.value is not None:
        add_optional_element(dur_elem, "Value", duration.value)
    elif duration.distribution:
        add_distribution(dur_elem, "Distribution", duration.distribution)
    elif duration.distribution_reference:
        ref_elem = SubElement(dur_elem, "DistributionReference")
        add_optional_element(ref_elem, "DistributionDefinitionIdentifier", duration.distribution_reference)


def add_distribution(parent: Element, tag: str, distribution):
    """Add Distribution element."""
    dist_elem = SubElement(parent, tag)
    add_optional_element(dist_elem, "Name", distribution.name)
    if distribution.description:
        add_optional_element(dist_elem, "Description", distribution.description)

    for param in distribution.distribution_parameters:
        param_elem = SubElement(dist_elem, "DistributionParameter")
        add_optional_element(param_elem, "Name", param.name)
        if param.description:
            add_optional_element(param_elem, "Description", param.description)
        add_optional_element(param_elem, "Value", param.value)


def add_reference(parent: Element, tag: str, reference):
    """Add a reference element using model_fields for reliable field introspection."""
    ref_elem = SubElement(parent, tag)

    if hasattr(reference, 'document_identifier') and reference.document_identifier:
        add_optional_element(ref_elem, "DocumentIdentifier", reference.document_identifier)

    for field_name in reference.model_fields:
        if field_name == 'document_identifier':
            continue
        value = getattr(reference, field_name, None)
        if value is not None:
            xml_name = ''.join(word.capitalize() for word in field_name.split('_'))
            add_optional_element(ref_elem, xml_name, value)


def add_part_group(parent: Element, tag: str, part_group: PartGroup):
    """Add PartGroup element."""
    pg_elem = SubElement(parent, tag)

    if part_group.description:
        add_optional_element(pg_elem, "Description", part_group.description)

    if part_group.part_type:
        add_reference(pg_elem, "PartType", part_group.part_type)

    if part_group.part_quantity is not None:
        add_optional_element(pg_elem, "PartQuantity", part_group.part_quantity)

    for part_ref in part_group.part_instances:
        add_reference(pg_elem, "PartInstance", part_ref)


def add_resources_required(parent: Element, tag: str, resources_req: ResourcesRequired):
    """Add ResourcesRequired element."""
    rr_elem = SubElement(parent, tag)

    if resources_req.description:
        add_optional_element(rr_elem, "Description", resources_req.description)

    if resources_req.resource_class:
        add_reference(rr_elem, "ResourceClass", resources_req.resource_class)

    add_optional_element(rr_elem, "MinimumNumber", resources_req.minimum_number)
    add_optional_element(rr_elem, "MaximumNumber", resources_req.maximum_number)

    for res_ref in resources_req.resources:
        add_reference(rr_elem, "Resource", res_ref)

    for setup_ref in resources_req.allowable_setups:
        add_reference(rr_elem, "AllowableSetup", setup_ref)

    for skill_ref in resources_req.required_employee_skills:
        add_reference(rr_elem, "RequiredEmployeeSkill", skill_ref)


def add_identifiable_entity_fields(parent: Element, entity):
    """Add common IdentifiableEntity fields (Identifier, Name, Description, Properties)."""
    add_optional_element(parent, "Identifier", entity.identifier)
    add_optional_element(parent, "Name", entity.name)
    add_optional_element(parent, "Description", entity.description)
    for rm_id in entity.reference_materials:
        add_optional_element(parent, "ReferenceMaterialIdentifier", rm_id)


# =============================================================================
# PART / BOM CONVERTERS
# =============================================================================

def part_type_to_xml(parent: Element, part_type: PartType):
    pt_elem = SubElement(parent, "PartType")
    add_identifiable_entity_fields(pt_elem, part_type)

    if part_type.bill_of_materials:
        add_reference(pt_elem, "BillOfMaterials", part_type.bill_of_materials)
    if part_type.process_plan:
        add_reference(pt_elem, "ProcessPlan", part_type.process_plan)
    if part_type.size:
        add_gross_dimensions(pt_elem, "Size", part_type.size)
    if part_type.weight:
        add_weight(pt_elem, "Weight", part_type.weight)
    add_properties(pt_elem, part_type.properties)


def part_to_xml(parent: Element, part: Part):
    part_elem = SubElement(parent, "Part")
    add_identifiable_entity_fields(part_elem, part)

    if part.part_type:
        add_reference(part_elem, "PartType", part.part_type)
    add_optional_element(part_elem, "ProductionStatus", part.production_status)

    if part.location:
        loc_elem = SubElement(part_elem, "Location")
        add_optional_element(loc_elem, "FacilityLocation", part.location.facility_location)
        add_optional_element(loc_elem, "WithinFacilityLocation", part.location.within_facility_location)
        if part.location.resource_location:
            add_reference(loc_elem, "ResourceLocation", part.location.resource_location)

    if part.bill_of_materials:
        add_reference(part_elem, "BillOfMaterials", part.bill_of_materials)
    if part.process_plan:
        add_reference(part_elem, "ProcessPlan", part.process_plan)
    if part.last_finished_process_step:
        add_reference(part_elem, "LastFinishedProcessStep", part.last_finished_process_step)
    if part.size:
        add_gross_dimensions(part_elem, "Size", part.size)
    if part.weight:
        add_weight(part_elem, "Weight", part.weight)

    if part.lot:
        lot_elem = SubElement(part_elem, "Lot")
        add_optional_element(lot_elem, "LotNumber", part.lot.lot_number)
        add_optional_element(lot_elem, "ParentLotNumber", part.lot.parent_lot_number)
        add_optional_element(lot_elem, "Description", part.lot.description)

    add_properties(part_elem, part.properties)


def bom_component_to_xml(parent: Element, component):
    comp_elem = SubElement(parent, "BillOfMaterialsComponent")
    add_identifiable_entity_fields(comp_elem, component)
    add_optional_element(comp_elem, "Quantity", component.quantity)
    if component.part_type:
        add_reference(comp_elem, "PartType", component.part_type)
    for part_ref in component.part_instances:
        add_reference(comp_elem, "PartInstance", part_ref)
    for sub_ref in component.sub_components:
        add_reference(comp_elem, "SubComponent", sub_ref)
    add_properties(comp_elem, component.properties)


def bom_to_xml(parent: Element, bom: BillOfMaterials):
    bom_elem = SubElement(parent, "BillOfMaterials")
    add_identifiable_entity_fields(bom_elem, bom)

    if bom.part_type:
        add_reference(bom_elem, "PartType", bom.part_type)
    if bom.part_instance:
        add_reference(bom_elem, "PartInstance", bom.part_instance)
    if bom.main_component:
        add_reference(bom_elem, "MainComponent", bom.main_component)

    for component in bom.components:
        bom_component_to_xml(bom_elem, component)

    add_properties(bom_elem, bom.properties)


# =============================================================================
# RESOURCE CONVERTERS
# =============================================================================

def resource_class_to_xml(parent: Element, resource_class: ResourceClass):
    rc_elem = SubElement(parent, "ResourceClass")
    add_identifiable_entity_fields(rc_elem, resource_class)
    add_optional_element(rc_elem, "ResourceType", resource_class.resource_type)

    if resource_class.hourly_rate:
        hr_elem = SubElement(rc_elem, "HourlyRate")
        if resource_class.hourly_rate.unit:
            add_optional_element(hr_elem, "Unit", resource_class.hourly_rate.unit)
        add_optional_element(hr_elem, "Value", resource_class.hourly_rate.value)

    if resource_class.size:
        add_gross_dimensions(rc_elem, "Size", resource_class.size)
    add_properties(rc_elem, resource_class.properties)


def resource_to_xml(parent: Element, resource: Resource):
    res_elem = SubElement(parent, "Resource")
    add_identifiable_entity_fields(res_elem, resource)
    add_optional_element(res_elem, "ResourceType", resource.resource_type)

    if resource.resource_class:
        add_reference(res_elem, "ResourceClass", resource.resource_class)

    add_optional_element(res_elem, "CurrentStatus", resource.current_status)

    if resource.current_setup:
        add_reference(res_elem, "CurrentSetup", resource.current_setup)

    for shift_ref in resource.shift_assignments:
        add_reference(res_elem, "ShiftAssignment", shift_ref)

    for assoc_res in resource.associated_resources:
        add_reference(res_elem, "AssociatedResource", assoc_res)

    if resource.hourly_rate:
        hr_elem = SubElement(res_elem, "HourlyRate")
        if resource.hourly_rate.unit:
            add_optional_element(hr_elem, "Unit", resource.hourly_rate.unit)
        add_optional_element(hr_elem, "Value", resource.hourly_rate.value)

    for skill_ref in resource.employee_skills:
        add_reference(res_elem, "EmployeeSkill", skill_ref)

    if resource.size:
        add_gross_dimensions(res_elem, "Size", resource.size)
    add_properties(res_elem, resource.properties)


# =============================================================================
# PROCESS PLAN CONVERTERS
# =============================================================================

def process_to_xml(parent: Element, process: Process):
    proc_elem = SubElement(parent, "Process")
    add_identifiable_entity_fields(proc_elem, process)

    if process.duration:
        add_duration(proc_elem, "Duration", process.duration)

    for rr in process.resources_required:
        add_resources_required(proc_elem, "ResourcesRequired", rr)

    for part_group in process.parts_produced:
        add_part_group(proc_elem, "PartsProduced", part_group)

    for part_group in process.parts_consumed:
        add_part_group(proc_elem, "PartsConsumed", part_group)

    if process.setup_time:
        add_duration(proc_elem, "SetupTime", process.setup_time)

    if process.load_time:
        add_duration(proc_elem, "LoadTime", process.load_time)

    if process.unload_time:
        add_duration(proc_elem, "UnloadTime", process.unload_time)

    if process.pick_time:
        add_duration(proc_elem, "PickTime", process.pick_time)

    if process.place_time:
        add_duration(proc_elem, "PlaceTime", process.place_time)

    add_properties(proc_elem, process.properties)


def process_group_to_xml(parent: Element, group: ProcessGroup):
    pg_elem = SubElement(parent, "ProcessGroup")
    add_identifiable_entity_fields(pg_elem, group)
    add_optional_element(pg_elem, "GroupType", group.group_type)

    for item in group.processes:
        if isinstance(item, ProcessGroup):
            process_group_to_xml(pg_elem, item)
        else:
            process_to_xml(pg_elem, item)


def process_plan_to_xml(parent: Element, process_plan: ProcessPlan):
    pp_elem = SubElement(parent, "ProcessPlan")
    add_identifiable_entity_fields(pp_elem, process_plan)

    if process_plan.part_type:
        add_reference(pp_elem, "PartType", process_plan.part_type)

    for item in process_plan.processes:
        if isinstance(item, ProcessGroup):
            process_group_to_xml(pp_elem, item)
        else:
            process_to_xml(pp_elem, item)

    add_properties(pp_elem, process_plan.properties)


# =============================================================================
# JOB CONVERTER
# =============================================================================

def add_job_effort(parent: Element, tag: str, effort):
    effort_elem = SubElement(parent, tag)
    add_optional_element(effort_elem, "UpdateTime", effort.update_time)

    for part_group in effort.parts_produced:
        add_part_group(effort_elem, "PartsProduced", part_group)

    for part_group in effort.parts_consumed:
        add_part_group(effort_elem, "PartsConsumed", part_group)

    for resources_req in effort.resources_required:
        add_resources_required(effort_elem, "ResourcesRequired", resources_req)

    add_optional_element(effort_elem, "DueDate", effort.due_date)
    add_optional_element(effort_elem, "ReleaseDate", effort.release_date)
    add_optional_element(effort_elem, "StartTime", effort.start_time)
    add_optional_element(effort_elem, "EndTime", effort.end_time)

    if effort.setup_time:
        add_duration(effort_elem, "SetupTime", effort.setup_time)
    if effort.processing_time:
        add_duration(effort_elem, "ProcessingTime", effort.processing_time)
    if effort.process_plan:
        add_reference(effort_elem, "ProcessPlan", effort.process_plan)
    if effort.current_process_plan_step:
        add_reference(effort_elem, "CurrentProcessPlanStep", effort.current_process_plan_step)


def job_to_xml(parent: Element, job: Job):
    job_elem = SubElement(parent, "Job")
    add_identifiable_entity_fields(job_elem, job)
    add_optional_element(job_elem, "Status", job.status)
    add_optional_element(job_elem, "UpdateTime", job.update_time)
    add_optional_element(job_elem, "Priority", job.priority)

    for constraint in job.precedence_constraints:
        const_elem = SubElement(job_elem, "PrecedenceConstraint")
        add_reference(const_elem, "PredecessorJob", constraint.predecessor_job)
        add_optional_element(const_elem, "Relationship", constraint.relationship)
        if constraint.time_lag:
            add_duration(const_elem, "TimeLag", constraint.time_lag)

    for sub_job_ref in job.sub_jobs:
        add_reference(job_elem, "SubJob", sub_job_ref)

    if job.planned_effort:
        add_job_effort(job_elem, "PlannedEffort", job.planned_effort)
    if job.actual_effort:
        add_job_effort(job_elem, "ActualEffort", job.actual_effort)

    add_properties(job_elem, job.properties)


# =============================================================================
# CALENDAR CONVERTERS
# =============================================================================

def break_to_xml(parent: Element, brk: Break):
    brk_elem = SubElement(parent, "Break")
    add_identifiable_entity_fields(brk_elem, brk)
    add_optional_element(brk_elem, "StartTime", brk.start_time)
    add_optional_element(brk_elem, "EndTime", brk.end_time)
    add_properties(brk_elem, brk.properties)


def shift_to_xml(parent: Element, shift: Shift):
    sh_elem = SubElement(parent, "Shift")
    add_identifiable_entity_fields(sh_elem, shift)
    add_optional_element(sh_elem, "DayOfWeek", shift.day_of_week)
    add_optional_element(sh_elem, "StartTime", shift.start_time)
    add_optional_element(sh_elem, "EndTime", shift.end_time)
    for brk in shift.breaks:
        break_to_xml(sh_elem, brk)
    add_properties(sh_elem, shift.properties)


def shift_schedule_to_xml(parent: Element, ss: ShiftSchedule):
    ss_elem = SubElement(parent, "ShiftSchedule")
    add_identifiable_entity_fields(ss_elem, ss)
    for shift in ss.shifts:
        shift_to_xml(ss_elem, shift)
    add_properties(ss_elem, ss.properties)


def holiday_to_xml(parent: Element, holiday: Holiday):
    h_elem = SubElement(parent, "Holiday")
    add_identifiable_entity_fields(h_elem, holiday)
    add_optional_element(h_elem, "HolidayDate", holiday.holiday_date)
    add_properties(h_elem, holiday.properties)


def availability_exception_to_xml(parent: Element, exc: AvailabilityException):
    exc_elem = SubElement(parent, "AvailabilityException")
    add_identifiable_entity_fields(exc_elem, exc)
    add_optional_element(exc_elem, "ExceptionDate", exc.exception_date)
    add_optional_element(exc_elem, "Available", exc.available)
    add_optional_element(exc_elem, "StartTime", exc.start_time)
    add_optional_element(exc_elem, "EndTime", exc.end_time)
    add_properties(exc_elem, exc.properties)


def calendar_to_xml(parent: Element, calendar: Calendar):
    cal_elem = SubElement(parent, "Calendar")
    add_identifiable_entity_fields(cal_elem, calendar)
    for ss in calendar.shift_schedules:
        shift_schedule_to_xml(cal_elem, ss)
    for shift in calendar.shifts:
        shift_to_xml(cal_elem, shift)
    for holiday in calendar.holidays:
        holiday_to_xml(cal_elem, holiday)
    for exc in calendar.availability_exceptions:
        availability_exception_to_xml(cal_elem, exc)
    add_properties(cal_elem, calendar.properties)


# =============================================================================
# SCHEDULE CONVERTERS
# =============================================================================

def schedule_item_effort_to_xml(parent: Element, tag: str, effort: ScheduleItemEffortDescription):
    eff_elem = SubElement(parent, tag)
    add_identifiable_entity_fields(eff_elem, effort)
    add_optional_element(eff_elem, "UpdateTime", effort.update_time)
    for pg in effort.parts_produced:
        add_part_group(eff_elem, "PartsProduced", pg)
    for pg in effort.parts_consumed:
        add_part_group(eff_elem, "PartsConsumed", pg)
    for rr in effort.resources_required:
        add_resources_required(eff_elem, "ResourcesRequired", rr)
    add_optional_element(eff_elem, "StartTime", effort.start_time)
    add_optional_element(eff_elem, "EndTime", effort.end_time)
    if effort.setup_time:
        add_duration(eff_elem, "SetupTime", effort.setup_time)
    if effort.processing_time:
        add_duration(eff_elem, "ProcessingTime", effort.processing_time)
    if effort.process_plan:
        add_reference(eff_elem, "ProcessPlan", effort.process_plan)
    if effort.current_process_plan_step:
        add_reference(eff_elem, "CurrentProcessPlanStep", effort.current_process_plan_step)
    add_properties(eff_elem, effort.properties)


def schedule_item_to_xml(parent: Element, item: ScheduleItem):
    item_elem = SubElement(parent, "ScheduleItem")
    add_identifiable_entity_fields(item_elem, item)
    if item.job:
        add_reference(item_elem, "Job", item.job)
    if item.planned_effort:
        schedule_item_effort_to_xml(item_elem, "PlannedEffort", item.planned_effort)
    if item.actual_effort:
        schedule_item_effort_to_xml(item_elem, "ActualEffort", item.actual_effort)
    add_properties(item_elem, item.properties)


def schedule_to_xml(parent: Element, schedule: Schedule):
    sch_elem = SubElement(parent, "Schedule")
    add_identifiable_entity_fields(sch_elem, schedule)
    for item in schedule.items:
        schedule_item_to_xml(sch_elem, item)
    add_properties(sch_elem, schedule.properties)


# =============================================================================
# ORDER CONVERTERS
# =============================================================================

def order_line_to_xml(parent: Element, line: OrderLine):
    line_elem = SubElement(parent, "OrderLine")
    add_identifiable_entity_fields(line_elem, line)
    add_optional_element(line_elem, "Status", line.status)
    add_optional_element(line_elem, "DueDate", line.due_date)
    add_optional_element(line_elem, "ReleaseDate", line.release_date)

    if line.part_description:
        pd_elem = SubElement(line_elem, "PartDescription")
        add_identifiable_entity_fields(pd_elem, line.part_description)
        if line.part_description.part_type:
            add_reference(pd_elem, "PartType", line.part_description.part_type)
        add_optional_element(pd_elem, "Quantity", line.part_description.quantity)
        if line.part_description.process_plan:
            add_reference(pd_elem, "ProcessPlan", line.part_description.process_plan)
        add_properties(pd_elem, line.part_description.properties)

    if line.service_description:
        sd_elem = SubElement(line_elem, "ServiceDescription")
        add_identifiable_entity_fields(sd_elem, line.service_description)
        add_optional_element(sd_elem, "ServiceDescription", line.service_description.service_description)
        if line.service_description.unit_price:
            price_elem = SubElement(sd_elem, "UnitPrice")
            if line.service_description.unit_price.unit:
                add_optional_element(price_elem, "Unit", line.service_description.unit_price.unit)
            add_optional_element(price_elem, "Value", line.service_description.unit_price.value)
        add_properties(sd_elem, line.service_description.properties)

    add_properties(line_elem, line.properties)


def order_to_xml(parent: Element, order: Order):
    ord_elem = SubElement(parent, "Order")
    add_identifiable_entity_fields(ord_elem, order)
    add_optional_element(ord_elem, "Status", order.status)
    add_optional_element(ord_elem, "DueDate", order.due_date)
    add_optional_element(ord_elem, "ReleaseDate", order.release_date)
    for line in order.order_lines:
        order_line_to_xml(ord_elem, line)
    add_properties(ord_elem, order.properties)


# =============================================================================
# INVENTORY CONVERTERS
# =============================================================================

def inventory_item_class_to_xml(parent: Element, iic: InventoryItemClass):
    iic_elem = SubElement(parent, "InventoryItemClass")
    add_identifiable_entity_fields(iic_elem, iic)
    add_optional_element(iic_elem, "ItemType", iic.item_type)
    if iic.part_type:
        add_reference(iic_elem, "PartType", iic.part_type)
    if iic.resource_class:
        add_reference(iic_elem, "ResourceClass", iic.resource_class)
    add_properties(iic_elem, iic.properties)


def inventory_item_to_xml(parent: Element, item: InventoryItem):
    item_elem = SubElement(parent, "InventoryItem")
    add_identifiable_entity_fields(item_elem, item)
    if item.item_class:
        add_reference(item_elem, "ItemClass", item.item_class)
    add_optional_element(item_elem, "QuantityOnHand", item.quantity_on_hand)
    add_optional_element(item_elem, "QuantityReserved", item.quantity_reserved)
    add_optional_element(item_elem, "ReorderPoint", item.reorder_point)
    add_optional_element(item_elem, "ReorderQuantity", item.reorder_quantity)
    add_properties(item_elem, item.properties)


# =============================================================================
# SETUP CONVERTERS
# =============================================================================

def setup_definition_to_xml(parent: Element, sd: SetupDefinition):
    sd_elem = SubElement(parent, "SetupDefinition")
    add_identifiable_entity_fields(sd_elem, sd)
    for rc_ref in sd.applicable_resource_classes:
        add_reference(sd_elem, "ApplicableResourceClass", rc_ref)
    for res_ref in sd.applicable_resources:
        add_reference(sd_elem, "ApplicableResource", res_ref)
    add_properties(sd_elem, sd.properties)


def setup_changeover_to_xml(parent: Element, scd: SetupChangeoverDefinition):
    scd_elem = SubElement(parent, "SetupChangeoverDefinition")
    add_identifiable_entity_fields(scd_elem, scd)
    add_optional_element(scd_elem, "FromSetupIdentifier", scd.from_setup_identifier)
    add_optional_element(scd_elem, "ToSetupIdentifier", scd.to_setup_identifier)
    if scd.changeover_time:
        add_duration(scd_elem, "ChangeoverTime", scd.changeover_time)
    for rc_ref in scd.applicable_resource_classes:
        add_reference(scd_elem, "ApplicableResourceClass", rc_ref)
    for res_ref in scd.applicable_resources:
        add_reference(scd_elem, "ApplicableResource", res_ref)
    add_properties(scd_elem, scd.properties)


# =============================================================================
# SKILL CONVERTERS
# =============================================================================

def skill_definition_to_xml(parent: Element, skill: SkillDefinition):
    sk_elem = SubElement(parent, "SkillDefinition")
    add_identifiable_entity_fields(sk_elem, skill)
    for level in skill.levels:
        lv_elem = SubElement(sk_elem, "SkillLevel")
        add_identifiable_entity_fields(lv_elem, level)
        add_optional_element(lv_elem, "LevelValue", level.level_value)
        add_properties(lv_elem, level.properties)
    add_properties(sk_elem, skill.properties)


# =============================================================================
# DISTRIBUTION DEFINITION CONVERTER
# =============================================================================

def distribution_definition_to_xml(parent: Element, dd: DistributionDefinition):
    dd_elem = SubElement(parent, "DistributionDefinition")
    add_identifiable_entity_fields(dd_elem, dd)
    add_distribution(dd_elem, "Distribution", dd.distribution)
    add_properties(dd_elem, dd.properties)


# =============================================================================
# MAINTENANCE CONVERTERS
# =============================================================================

def maintenance_process_to_xml(parent: Element, mp: MaintenanceProcess):
    mp_elem = SubElement(parent, "MaintenanceProcess")
    add_identifiable_entity_fields(mp_elem, mp)
    if mp.duration:
        add_duration(mp_elem, "Duration", mp.duration)
    for rc_ref in mp.applicable_resource_classes:
        add_reference(mp_elem, "ApplicableResourceClass", rc_ref)
    for res_ref in mp.applicable_resources:
        add_reference(mp_elem, "ApplicableResource", res_ref)
    add_properties(mp_elem, mp.properties)


def maintenance_plan_to_xml(parent: Element, plan: MaintenancePlan):
    plan_elem = SubElement(parent, "MaintenancePlan")
    add_identifiable_entity_fields(plan_elem, plan)
    add_optional_element(plan_elem, "ScheduledDate", plan.scheduled_date)
    for mp in plan.processes:
        maintenance_process_to_xml(plan_elem, mp)
    add_properties(plan_elem, plan.properties)


# =============================================================================
# REFERENCE MATERIAL CONVERTER
# =============================================================================

def reference_material_to_xml(parent: Element, rm: ReferenceMaterial):
    rm_elem = SubElement(parent, "ReferenceMaterial")
    add_identifiable_entity_fields(rm_elem, rm)
    add_optional_element(rm_elem, "URI", rm.uri)
    add_optional_element(rm_elem, "MediaType", rm.media_type)
    add_properties(rm_elem, rm.properties)


# =============================================================================
# COST ALLOCATION CONVERTER
# =============================================================================

def cost_allocation_to_xml(parent: Element, ca: CostAllocationData):
    ca_elem = SubElement(parent, "CostAllocationData")
    add_identifiable_entity_fields(ca_elem, ca)
    add_optional_element(ca_elem, "CostCategory", ca.cost_category)
    add_optional_element(ca_elem, "CostType", ca.cost_type)
    if ca.amount:
        amt_elem = SubElement(ca_elem, "Amount")
        if ca.amount.unit:
            add_optional_element(amt_elem, "Unit", ca.amount.unit)
        add_optional_element(amt_elem, "Value", ca.amount.value)
    if ca.job:
        add_reference(ca_elem, "Job", ca.job)
    if ca.resource:
        add_reference(ca_elem, "Resource", ca.resource)
    add_properties(ca_elem, ca.properties)


# =============================================================================
# CONNECTION CONVERTER
# =============================================================================

def connection_to_xml(parent: Element, conn: Connection):
    conn_elem = SubElement(parent, "Connection")
    add_identifiable_entity_fields(conn_elem, conn)
    add_optional_element(conn_elem, "ConnectionType", conn.connection_type)
    if conn.from_resource:
        add_reference(conn_elem, "FromResource", conn.from_resource)
    if conn.to_resource:
        add_reference(conn_elem, "ToResource", conn.to_resource)
    add_properties(conn_elem, conn.properties)


# =============================================================================
# LAYOUT CONVERTER
# =============================================================================

def layout_to_xml(parent: Element, layout: Layout):
    layout_elem = SubElement(parent, "Layout")
    add_optional_element(layout_elem, "Identifier", layout.identifier)
    add_optional_element(layout_elem, "Name", layout.name)
    add_optional_element(layout_elem, "Description", layout.description)

    if layout.associated_resource:
        add_reference(layout_elem, "AssociatedResource", layout.associated_resource)

    for rm_ref in layout.reference_materials:
        add_reference(layout_elem, "ReferenceMaterial", rm_ref)

    for placement in layout.placements:
        pl_elem = SubElement(layout_elem, "Placement")
        add_reference(pl_elem, "LayoutElement", placement.layout_element)
        loc = placement.location
        loc_elem = SubElement(pl_elem, "Location")
        add_optional_element(loc_elem, "X", loc.x)
        add_optional_element(loc_elem, "Y", loc.y)
        add_optional_element(loc_elem, "Z", loc.z)

    add_properties(layout_elem, layout.properties)


# =============================================================================
# ROOT DOCUMENT CONVERTER
# =============================================================================

def cmsd_document_to_xml(doc: CMSDDocument, pretty_print: bool = True) -> str:
    """
    Convert a CMSDDocument Pydantic model to CMSD XML string.

    Args:
        doc: CMSDDocument instance
        pretty_print: If True, format with indentation

    Returns:
        XML string conforming to CMSD schema
    """
    root = Element("CMSDDocument")
    root.set("xmlns", CMSD_NAMESPACE)

    for rm in doc.reference_materials:
        reference_material_to_xml(root, rm)

    for part_type in doc.part_types:
        part_type_to_xml(root, part_type)

    for part in doc.parts:
        part_to_xml(root, part)

    for bom in doc.bills_of_materials:
        bom_to_xml(root, bom)

    for rc in doc.resource_classes:
        resource_class_to_xml(root, rc)

    for resource in doc.resources:
        resource_to_xml(root, resource)

    for pp in doc.process_plans:
        process_plan_to_xml(root, pp)

    for job in doc.jobs:
        job_to_xml(root, job)

    for cal in doc.calendars:
        calendar_to_xml(root, cal)

    for sched in doc.schedules:
        schedule_to_xml(root, sched)

    for order in doc.orders:
        order_to_xml(root, order)

    for iic in doc.inventory_item_classes:
        inventory_item_class_to_xml(root, iic)

    for item in doc.inventory_items:
        inventory_item_to_xml(root, item)

    for sd in doc.setup_definitions:
        setup_definition_to_xml(root, sd)

    for scd in doc.setup_changeover_definitions:
        setup_changeover_to_xml(root, scd)

    for skill in doc.skill_definitions:
        skill_definition_to_xml(root, skill)

    for dd in doc.distribution_definitions:
        distribution_definition_to_xml(root, dd)

    for plan in doc.maintenance_plans:
        maintenance_plan_to_xml(root, plan)

    for ca in doc.cost_allocation_data:
        cost_allocation_to_xml(root, ca)

    for conn in doc.connections:
        connection_to_xml(root, conn)

    for layout in doc.layouts:
        layout_to_xml(root, layout)

    if pretty_print:
        return prettify_xml(root)
    return tostring(root, encoding='unicode')


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def save_cmsd_xml(doc: CMSDDocument, filename: str, pretty_print: bool = True):
    """Save a CMSDDocument as an XML file."""
    xml_string = cmsd_document_to_xml(doc, pretty_print)
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(xml_string)
