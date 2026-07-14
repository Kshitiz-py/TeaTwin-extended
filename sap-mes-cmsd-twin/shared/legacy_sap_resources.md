# API Endpoint Implementation: Legacy SAP Resource Factory — GET /api/legacy/v1/machines

Route handler for legacy SAP R/3 manufacturing resource data. Returns machine master data with system-generated ABAP field codes. Below is the complete field mapping from FLD codes to business meanings for CMSD Resource entity integration.

## Complete Field Reference (FLD Codes → CMSD Resource Fields)

| FLD Code | CMSD Field / Business Meaning | Type | Example |
|----------|------------------------------|------|---------|
| FLD001 | identifier (Resource unique ID) | string | "RES-CNC-001" |
| FLD002 | name (Human-readable machine name) | string | "CNC Mill #1 (DMG Mori)" |
| FLD003 | description (Free-text machine description) | string | "5-axis CNC milling for housing" |
| FLD004 | resource_type (Resource type enum: machine, station, conveyor, buffer, employee, transporter, source, sink) | enum | "machine" |
| FLD005 | resource_class (Foreign key to resource_class table → maps to ResourceClassReference) | integer | 1 |
| FLD006 | capacity (Maximum concurrent operations) | integer | 1 |
| FLD007 | availability (Uptime percentage 0-100, divide by 100 for CMSD Decimal) | float | 95.0 |
| FLD008 | mttr (Mean Time To Repair in seconds → CMSD Duration) | integer | 7200 |
| FLD009 | mtbf (Mean Time Between Failures in seconds → CMSD Duration) | integer | 360000 |
| FLD010 | mcbf (Mean Cycles Between Failures, nullable) | integer | null |
| FLD011 | reliability (Reliability score 0-100, nullable, divide by 100 for Decimal) | float | null |
| FLD012 | cycle_time (Standard cycle time in seconds → CMSD Duration) | integer | 300 |
| FLD013 | desired_replenishment_time (Target replenishment seconds, nullable → Duration) | integer | null |
| FLD014 | transport_capacity (Max transport load, nullable) | integer | null |
| FLD015 | tow_bar_length (Tow bar length mm, nullable → Length) | integer | null |
| FLD016 | worker_count (Assigned workers, nullable) | integer | null |
| FLD017 | decision_rule (Queue discipline: fifo, lifo, earliestDueDate, shortestProcessingTime, priorityBased) | enum | "fifo" |
| FLD018 | routing_rule (Selection strategy: roundRobin, shortestQueue, leastUtilized, nearestNeighbor) | enum | "roundRobin" |
| FLD019 | size (Physical dimensions → GrossDimensions, nested: length=FLD301, width=FLD302, height=FLD303) | object | {length:4200, width:3100, height:2600} |
| FLD020 | hourly_rate (Cost per hour EUR → Currency) | float | 85.0 |
| FLD021 | buffer_type (Buffer config type, nullable — not mapped to base CMSD Resource) | string | null |
| FLD022 | buffer_capacity (Buffer capacity units, nullable — not mapped) | integer | null |
| FLD023 | conveyor_speed (Conveyor speed mm/s, nullable — not mapped) | float | null |
| FLD024 | conveyor_length (Conveyor length mm, nullable — not mapped) | float | null |
| FLD025 | conveyor_accumulating (Accumulating conveyor flag — not mapped) | bool | true |
| FLD026 | energy_model (Energy consumption → EnergyModel, nested: working_kw=FLD401, standby_kw=FLD402, failed_kw=FLD403, off_kw=FLD404, nullable — not mapped) | object | null |

## Nested Sub-Fields

**FLD019 (size → GrossDimensions):**
- FLD301 = length (mm)
- FLD302 = width (mm)
- FLD303 = height (mm)

**FLD026 (energy → EnergyModel, not mapped to base Resource):**
- FLD401 = working_kw
- FLD402 = standby_kw
- FLD403 = failed_kw
- FLD404 = off_kw

## Instance Info
- Entity type: Resource
- Instance count: 28 machines
- JSONPath: $.machines[*]
- Key field: FLD001
