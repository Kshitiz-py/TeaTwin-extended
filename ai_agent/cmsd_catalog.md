# CMSD Entity Catalog — Field Reference

This document defines CMSD entities, their fields, types, and descriptions.
Use this as the authoritative reference for field mapping to CMSD.

## Resource
A production resource — machine, station, worker, conveyor, buffer, or transporter.
Resources execute jobs and have capacity, availability, and status.

Hierarchy: top-level — referenced by Job, Connection

| Field | Type | Description |
|-------|------|-------------|
| identifier | str | Unique ID (e.g. MACH-001, RES-CNC-001) |
| name | str | Human-readable name (e.g. CNC Mill #3) |
| description | str | Optional description of the resource |
| resource_type | enum | Type: machine, station, conveyor, buffer, employee, transporter |
| resource_class | reference | Reference to ResourceClass entity |
| capacity | int | How many jobs or parts this resource can handle at once |
| availability | float | Fraction (0.0-1.0) of time this resource is available |
| current_status | enum | Live status: busy, idle, broken, setup, paused, underMaintenance |
| cycle_time | float | Base processing time per unit (seconds) |
| mttr | float | Mean Time To Repair (hours) |
| mtbf | float | Mean Time Between Failures (hours) |
| mcbf | float | Mean Cycles Between Failures |
| reliability | float | Reliability score (0.0-1.0) |
| size | object | Physical dimensions: length, width, height (meters) |
| hourly_rate | float | Cost per hour of operation |
| decision_rule | enum | Dispatching rule: fifo, lifo, earliestDueDate, shortestProcessingTime |
| routing_rule | enum | Routing strategy: roundRobin, shortestQueue, leastUtilized |
| desired_replenishment_time | float | Target time to replenish (seconds) |
| transport_capacity | int | Transport capacity for conveyors/AGVs |
| tow_bar_length | float | Tow bar length for transporters (meters) |
| worker_count | int | Number of workers assigned |

## ResourceClass
A category or type of resource. Groups resources with similar characteristics
(e.g. CNC Machine, Assembly Station). Used to define capabilities.

Hierarchy: top-level — referenced by Resource

| Field | Type | Description |
|-------|------|-------------|
| identifier | str | Unique ID (e.g. CNC-3AXIS) |
| name | str | Human-readable name (e.g. 3-Axis CNC Machine) |
| description | str | Optional description |
| resource_type | enum | The type of resource this class represents |
| hourly_rate | float | Standard hourly rate for resources of this class |
| size | object | Standard physical dimensions |

## PartType
A part classification — the blueprint for a manufactured component.
Defines the part's identity, not a specific physical instance.

Hierarchy: top-level — referenced by OrderLine, BillOfMaterials, InventoryItem

| Field | Type | Description |
|-------|------|-------------|
| identifier | str | Unique part type code (e.g. PT-HOUSING-A) |
| name | str | Human-readable name (e.g. Engine Housing) |
| description | str | Optional description of the part type |
| part_type | str | Category or classification of the part |

## Part
A specific physical instance of a PartType — a real component on the shop floor.

Hierarchy: top-level — references PartType

| Field | Type | Description |
|-------|------|-------------|
| identifier | str | Unique part serial number |
| name | str | Human-readable name |
| part_type | reference | Reference to the PartType this instance belongs to |
| status | enum | Production status: raw, inProgress, completed, scrapped |

## Order
A production order — instruction to manufacture parts by a due date.

Hierarchy: top-level — contains OrderLine. Drives job creation.

| Field | Type | Description |
|-------|------|-------------|
| identifier | str | Unique order ID (e.g. ORD-2026-001) |
| name | str | Human-readable name |
| status | enum | Order status: created, released, inProgress, completed, shipped, cancelled |
| due_date | datetime | Date/time when the order must be fulfilled |
| release_date | datetime | Date/time when the order was released to production |
| order_lines | list | List of OrderLine items |

## OrderLine
A line item within a production Order.

Hierarchy: nested inside Order — references PartType, ProcessPlan

| Field | Type | Description |
|-------|------|-------------|
| identifier | str | Unique line ID |
| part_type | reference | Reference to the PartType to produce |
| quantity | int | Number of units to produce |
| process_plan | reference | Optional reference to ProcessPlan |

## Calendar
A factory calendar defining working days, shifts, breaks, and holidays.

Hierarchy: top-level — contains Shift, Break, Holiday

| Field | Type | Description |
|-------|------|-------------|
| identifier | str | Unique calendar ID (e.g. FACTORY-CAL) |
| name | str | Human-readable name (e.g. Standard Factory Calendar) |
| description | str | Optional description |

## Shift
A work shift within a calendar.

Hierarchy: nested inside Calendar

| Field | Type | Description |
|-------|------|-------------|
| identifier | str | Unique shift ID (e.g. DAY-SHIFT) |
| day_of_week | int | Day of week (1=Monday, 7=Sunday) |
| start_time | time | Shift start time (HH:MM) |
| end_time | time | Shift end time (HH:MM) |

## Break
A scheduled break within a shift.

Hierarchy: nested inside Shift

| Field | Type | Description |
|-------|------|-------------|
| identifier | str | Unique break ID (e.g. LUNCH-BREAK) |
| start_time | time | Break start time |
| end_time | time | Break end time |

## Holiday
A non-working day in the calendar.

Hierarchy: nested inside Calendar

| Field | Type | Description |
|-------|------|-------------|
| identifier | str | Unique holiday ID |
| date | date | Specific date when production is suspended |

## Connection
A physical connection between two resources on the factory layout.

Hierarchy: top-level — references two Resources

| Field | Type | Description |
|-------|------|-------------|
| identifier | str | Unique connection ID (e.g. CONN-001) |
| from_resource | reference | Reference to source Resource |
| to_resource | reference | Reference to destination Resource |
| connection_type | enum | Type: conveyor, footpath, logical |

## Job
A unit of work assigned to a resource at a specific time.

Hierarchy: top-level — references Order, Resource, Process

| Field | Type | Description |
|-------|------|-------------|
| identifier | str | Unique job ID (e.g. JOB-001) |
| status | enum | Status: created, scheduled, inProgress, completed, interrupted, cancelled |
| priority | int | Priority level (1 = highest) |
| start_time | datetime | Scheduled start time |
| end_time | datetime | Actual end time |
| order | reference | Reference to the Order this job belongs to |
| resource | reference | Reference to the Resource executing this job |
| process | reference | Reference to the Process step |

## ProcessPlan
The manufacturing recipe — sequence of Process steps to produce a part.

Hierarchy: top-level — contains Process

| Field | Type | Description |
|-------|------|-------------|
| identifier | str | Unique plan ID (e.g. PP-HOUSING) |
| name | str | Human-readable name (e.g. Housing Manufacturing Plan) |
| description | str | Optional description |

## Process
A single step within a ProcessPlan.

Hierarchy: nested inside ProcessPlan

| Field | Type | Description |
|-------|------|-------------|
| identifier | str | Unique operation ID (e.g. OP-10-MILL) |
| name | str | Human-readable name (e.g. Rough Mill Top Face) |
| duration | float | Time required to complete this step (seconds) |
| setup_time | float | Setup time before processing starts (seconds) |

## BillOfMaterials
The recipe for manufacturing a part — lists all components needed.

Hierarchy: top-level — contains BillOfMaterialsComponent

| Field | Type | Description |
|-------|------|-------------|
| identifier | str | Unique BOM ID (e.g. BOM-HOUSING) |
| name | str | Human-readable name |

## BillOfMaterialsComponent
A single line in a Bill of Materials.

Hierarchy: nested inside BillOfMaterials

| Field | Type | Description |
|-------|------|-------------|
| identifier | str | Unique component ID |
| part_type | reference | Reference to PartType |
| quantity | int | Number of units needed |

## InventoryItem
An inventory record tracking quantity of a part at a location.

Hierarchy: top-level — references PartType

| Field | Type | Description |
|-------|------|-------------|
| identifier | str | Unique inventory ID |
| part_type | reference | Reference to PartType |
| quantity | float | Current quantity on hand |

## MaintenancePlan
A planned maintenance schedule for a resource.

Hierarchy: top-level — references Resource

| Field | Type | Description |
|-------|------|-------------|
| identifier | str | Unique plan ID |
| name | str | Human-readable name |
| description | str | Optional description |
| resource | reference | Reference to Resource this plan applies to |
