-- =============================================================================
-- SAP/MES → CMSD Digital Twin — Mock Seed Data
-- Represents a realistic manufacturing factory producing mechanical assemblies
-- =============================================================================

USE factory_digital_twin;

-- =============================================================================
-- PART TYPES
-- =============================================================================
INSERT INTO part_types (identifier, name, description, size_length, size_width, size_height, weight_kg, color, shape_3d) VALUES
('PT-RAW-001', 'Steel Block 100mm', 'Raw steel block for machining', 100.0, 100.0, 50.0, 3.925, 'gray', 'box'),
('PT-RAW-002', 'Aluminum Sheet 200mm', 'Aluminum sheet for stamping', 200.0, 150.0, 2.0, 0.162, 'silver', 'box'),
('PT-RAW-003', 'Plastic Granulate', 'Raw plastic granulate for injection molding', NULL, NULL, NULL, NULL, 'white', 'granulate'),
('PT-RAW-004', 'Steel Rod 500mm', 'Steel rod for turning', 500.0, 30.0, 30.0, 3.534, 'gray', 'cylinder'),
('PT-RAW-005', 'Electronic PCB Blank', 'Bare PCB for assembly', 100.0, 80.0, 1.6, 0.035, 'green', 'box'),
('PT-RAW-006', 'Bearing 6205', 'Standard ball bearing', 52.0, 52.0, 15.0, 0.128, 'silver', 'cylinder'),
('PT-RAW-007', 'M8 Bolt Set', 'M8x30 bolt with nut and washer', 30.0, 8.0, 8.0, 0.018, 'silver', 'cylinder'),
('PT-RAW-008', 'Oil Seal 30mm', 'Rubber oil seal', 30.0, 30.0, 7.0, 0.005, 'black', 'cylinder'),
('PT-INT-001', 'Machined Housing', 'Milled steel housing', 150.0, 120.0, 80.0, 4.500, 'gray', 'box'),
('PT-INT-002', 'Stamped Cover Plate', 'Stamped aluminum cover', 180.0, 130.0, 1.5, 0.140, 'silver', 'box'),
('PT-INT-003', 'Injection Molded Casing', 'Plastic casing for electronics', 200.0, 120.0, 60.0, 0.250, 'white', 'box'),
('PT-INT-004', 'Turned Shaft Assembly', 'Precision turned shaft with bearing seat', 300.0, 25.0, 25.0, 1.200, 'gray', 'cylinder'),
('PT-INT-005', 'Assembled PCB', 'PCB with components soldered', 100.0, 80.0, 25.0, 0.080, 'green', 'box'),
('PT-FG-001', 'Electric Motor Assembly 2kW', 'Final assembled 2kW electric motor', 350.0, 200.0, 200.0, 15.000, 'blue', 'cylinder'),
('PT-FG-002', 'Pump Unit Complete', 'Final assembled pump unit', 400.0, 250.0, 250.0, 22.000, 'red', 'box');

-- =============================================================================
-- RESOURCE CLASSES
-- =============================================================================
INSERT INTO resource_classes (identifier, name, description, resource_type, hourly_rate, size_length, size_width, size_height) VALUES
('RC-CNC-MILL', 'CNC Milling Machines', '5-axis CNC milling centers', 'machine', 85.00, 4000.0, 3000.0, 2500.0),
('RC-CNC-LATHE', 'CNC Turning Centers', 'CNC lathe machines', 'machine', 75.00, 3500.0, 2000.0, 2000.0),
('RC-STAMPING', 'Stamping Presses', 'Hydraulic stamping presses', 'machine', 65.00, 5000.0, 3000.0, 3500.0),
('RC-INJECTION', 'Injection Molding Machines', 'Plastic injection molding', 'machine', 55.00, 4500.0, 2500.0, 3000.0),
('RC-PICK-PLACE', 'Pick & Place Robots', 'Automated pick and place stations', 'station', 40.00, 2000.0, 1500.0, 2000.0),
('RC-ASSEMBLY', 'Assembly Stations', 'Manual/semi-automated assembly', 'station', 35.00, 3000.0, 2000.0, 2000.0),
('RC-TESTING', 'Testing Stations', 'Quality testing equipment', 'station', 50.00, 2000.0, 1500.0, 1800.0),
('RC-CONVEYOR', 'Conveyor Systems', 'Belt/roller conveyors', 'conveyor', 5.00, NULL, NULL, NULL),
('RC-BUFFER', 'Buffer/Storage', 'Intermediate storage buffers', 'buffer', 2.00, 3000.0, 2000.0, 1500.0),
('RC-OPERATOR', 'Human Operators', 'Skilled manufacturing operators', 'employee', 28.00, NULL, NULL, NULL),
('RC-TRANSPORTER', 'Forklift/AGV', 'Material transport vehicles', 'transporter', 20.00, 2500.0, 1200.0, 2200.0),
('RC-SOURCE', 'Raw Material Source', 'Input point for raw materials', 'source', 0.00, 2000.0, 1000.0, 1500.0),
('RC-SINK', 'Finished Goods Sink', 'Output point for finished goods', 'sink', 0.00, 2000.0, 1000.0, 1500.0);

-- =============================================================================
-- RESOURCES
-- =============================================================================
INSERT INTO resources (identifier, name, description, resource_class_id, resource_type, capacity, availability, mttr_seconds, mtbf_seconds, cycle_time_seconds, size_length, size_width, size_height, hourly_rate, decision_rule, routing_rule) VALUES
-- CNC Mills
('RES-CNC-001', 'CNC Mill #1 (DMG Mori)', '5-axis CNC milling for housing',
 (SELECT id FROM resource_classes WHERE identifier='RC-CNC-MILL'), 'machine', 1, 95.00, 7200, 360000, 300, 4200.0, 3100.0, 2600.0, 85.00, 'fifo', 'roundRobin'),
('RES-CNC-002', 'CNC Mill #2 (Haas)', '5-axis CNC milling secondary ops',
 (SELECT id FROM resource_classes WHERE identifier='RC-CNC-MILL'), 'machine', 1, 93.00, 5400, 320000, 280, 4100.0, 3000.0, 2550.0, 85.00, 'fifo', 'roundRobin'),
-- CNC Lathes
('RES-CNC-003', 'CNC Lathe #1 (Mazak)', 'CNC turning for shaft production',
 (SELECT id FROM resource_classes WHERE identifier='RC-CNC-LATHE'), 'machine', 1, 96.00, 4800, 400000, 240, 3600.0, 2100.0, 2100.0, 75.00, 'fifo', 'roundRobin'),
('RES-CNC-004', 'CNC Lathe #2 (Okuma)', 'CNC turning secondary ops',
 (SELECT id FROM resource_classes WHERE identifier='RC-CNC-LATHE'), 'machine', 1, 94.00, 6000, 340000, 260, 3550.0, 2050.0, 2050.0, 75.00, 'fifo', 'roundRobin'),
-- Stamping
('RES-STAMP-001', 'Stamping Press #1 (Schuler)', '800T hydraulic stamping press',
 (SELECT id FROM resource_classes WHERE identifier='RC-STAMPING'), 'machine', 1, 92.00, 9000, 280000, 60, 5200.0, 3200.0, 3700.0, 65.00, 'fifo', 'sst'),
-- Injection Molders
('RES-INJ-001', 'Injection Molder #1 (Engel)', '220T injection molding machine',
 (SELECT id FROM resource_classes WHERE identifier='RC-INJECTION'), 'machine', 1, 90.00, 10800, 260000, 45, 4700.0, 2600.0, 3200.0, 55.00, 'fifo', 'sst'),
('RES-INJ-002', 'Injection Molder #2 (Arburg)', '180T injection molding machine',
 (SELECT id FROM resource_classes WHERE identifier='RC-INJECTION'), 'machine', 1, 91.00, 9600, 270000, 50, 4600.0, 2500.0, 3100.0, 55.00, 'fifo', 'sst'),
-- Assembly
('RES-ASM-001', 'Assembly Station #1 (Motor)', 'Motor final assembly station',
 (SELECT id FROM resource_classes WHERE identifier='RC-ASSEMBLY'), 'station', 1, 98.00, 3600, 500000, 600, 3200.0, 2200.0, 2100.0, 35.00, 'fifo', 'roundRobin'),
('RES-ASM-002', 'Assembly Station #2 (Pump)', 'Pump final assembly station',
 (SELECT id FROM resource_classes WHERE identifier='RC-ASSEMBLY'), 'station', 1, 97.00, 4200, 480000, 540, 3100.0, 2100.0, 2100.0, 35.00, 'fifo', 'roundRobin'),
('RES-ASM-003', 'PCB Assembly Station', 'Electronic PCB assembly & soldering',
 (SELECT id FROM resource_classes WHERE identifier='RC-ASSEMBLY'), 'station', 1, 96.00, 5400, 420000, 360, 2800.0, 1800.0, 1900.0, 35.00, 'fifo', 'sst'),
-- Testing
('RES-TEST-001', 'Testing Station #1', 'Motor & pump performance testing',
 (SELECT id FROM resource_classes WHERE identifier='RC-TESTING'), 'station', 1, 99.00, 2400, 600000, 480, 2200.0, 1700.0, 1900.0, 50.00, 'fifo', 'roundRobin'),
-- Pick & Place
('RES-PNP-001', 'Pick & Place Robot #1', 'Material handling for CNC area',
 (SELECT id FROM resource_classes WHERE identifier='RC-PICK-PLACE'), 'station', 1, 99.50, 3600, 700000, 30, 2100.0, 1600.0, 2100.0, 40.00, 'fifo', 'sst'),
('RES-PNP-002', 'Pick & Place Robot #2', 'Material handling for assembly area',
 (SELECT id FROM resource_classes WHERE identifier='RC-PICK-PLACE'), 'station', 1, 99.50, 3600, 700000, 30, 2100.0, 1600.0, 2100.0, 40.00, 'fifo', 'sst'),
-- Conveyors
('RES-CONV-001', 'Main Conveyor Line #1', 'Machining to Assembly conveyor',
 (SELECT id FROM resource_classes WHERE identifier='RC-CONVEYOR'), 'conveyor', 10, 99.90, 1800, 800000, NULL, NULL, NULL, NULL, 5.00, NULL, NULL),
('RES-CONV-002', 'Assembly to Testing Conveyor', 'Assembly to test area conveyor',
 (SELECT id FROM resource_classes WHERE identifier='RC-CONVEYOR'), 'conveyor', 8, 99.90, 1800, 800000, NULL, NULL, NULL, NULL, 5.00, NULL, NULL),
('RES-CONV-003', 'Raw Material Intake Conveyor', 'Incoming material conveyor',
 (SELECT id FROM resource_classes WHERE identifier='RC-CONVEYOR'), 'conveyor', 15, 99.90, 1800, 800000, NULL, NULL, NULL, NULL, 5.00, NULL, NULL),
('RES-CONV-004', 'Finished Goods Outfeed Conveyor', 'Testing to shipping conveyor',
 (SELECT id FROM resource_classes WHERE identifier='RC-CONVEYOR'), 'conveyor', 10, 99.90, 1800, 800000, NULL, NULL, NULL, NULL, 5.00, NULL, NULL),
-- Buffers
('RES-BUF-001', 'Raw Material Buffer', 'Incoming raw material storage',
 (SELECT id FROM resource_classes WHERE identifier='RC-BUFFER'), 'buffer', 200, 100.00, NULL, NULL, NULL, 3200.0, 2200.0, 1600.0, 2.00, 'fifo', NULL),
('RES-BUF-002', 'Machining Output Buffer', 'Buffer after CNC operations',
 (SELECT id FROM resource_classes WHERE identifier='RC-BUFFER'), 'buffer', 50, 100.00, NULL, NULL, NULL, 3100.0, 2100.0, 1550.0, 2.00, 'fifo', NULL),
('RES-BUF-003', 'Assembly Input Buffer', 'Buffer before assembly stations',
 (SELECT id FROM resource_classes WHERE identifier='RC-BUFFER'), 'buffer', 30, 100.00, NULL, NULL, NULL, 3100.0, 2100.0, 1550.0, 2.00, 'fifo', NULL),
('RES-BUF-004', 'Finished Goods Buffer', 'Buffer before shipping',
 (SELECT id FROM resource_classes WHERE identifier='RC-BUFFER'), 'buffer', 100, 100.00, NULL, NULL, NULL, 3100.0, 2100.0, 1550.0, 2.00, 'fifo', NULL),
-- Source and Sink
('RES-SRC-001', 'Raw Material Intake', 'Entry point for raw materials',
 (SELECT id FROM resource_classes WHERE identifier='RC-SOURCE'), 'source', NULL, 100.00, NULL, NULL, 120, 2200.0, 1200.0, 1600.0, 0.00, NULL, NULL),
('RES-SNK-001', 'Finished Goods Outfeed', 'Exit point for finished products',
 (SELECT id FROM resource_classes WHERE identifier='RC-SINK'), 'sink', NULL, 100.00, NULL, NULL, 60, 2200.0, 1200.0, 1600.0, 0.00, NULL, NULL),
-- Workers
('RES-WKR-001', 'Operator Miller (Max)', 'Senior CNC milling operator',
 (SELECT id FROM resource_classes WHERE identifier='RC-OPERATOR'), 'employee', NULL, 95.00, NULL, NULL, NULL, NULL, NULL, NULL, 28.00, NULL, NULL),
('RES-WKR-002', 'Operator Turner (Klaus)', 'CNC turning specialist',
 (SELECT id FROM resource_classes WHERE identifier='RC-OPERATOR'), 'employee', NULL, 95.00, NULL, NULL, NULL, NULL, NULL, NULL, 28.00, NULL, NULL),
('RES-WKR-003', 'Assembler (Lisa)', 'Assembly station operator',
 (SELECT id FROM resource_classes WHERE identifier='RC-OPERATOR'), 'employee', NULL, 95.00, NULL, NULL, NULL, NULL, NULL, NULL, 28.00, NULL, NULL),
('RES-WKR-004', 'Quality Inspector (Hans)', 'Testing and quality control',
 (SELECT id FROM resource_classes WHERE identifier='RC-OPERATOR'), 'employee', NULL, 95.00, NULL, NULL, NULL, NULL, NULL, NULL, 28.00, NULL, NULL),
-- AGV
('RES-AGV-001', 'AGV #1', 'Automated guided vehicle for material transport',
 (SELECT id FROM resource_classes WHERE identifier='RC-TRANSPORTER'), 'transporter', 4, 98.00, 3600, 500000, 180, 2600.0, 1300.0, 2300.0, 20.00, 'sst', 'random');

-- =============================================================================
-- BILLS OF MATERIALS
-- =============================================================================
INSERT INTO bills_of_materials (identifier, name, description, part_type_id) VALUES
('BOM-EM-001', 'Electric Motor BOM', 'BOM for 2kW Electric Motor',
 (SELECT id FROM part_types WHERE identifier='PT-FG-001')),
('BOM-PUMP-001', 'Pump Unit BOM', 'BOM for complete pump unit',
 (SELECT id FROM part_types WHERE identifier='PT-FG-002')),
('BOM-SHAFT-001', 'Shaft Assembly BOM', 'BOM for turned shaft',
 (SELECT id FROM part_types WHERE identifier='PT-INT-004')),
('BOM-PCB-001', 'PCB Assembly BOM', 'BOM for assembled PCB',
 (SELECT id FROM part_types WHERE identifier='PT-INT-005'));

-- BOM Components for Electric Motor
INSERT INTO bom_components (identifier, bom_id, part_type_id, quantity, parent_component_id, sequence_order) VALUES
('BOMC-EM-HOUSING', (SELECT id FROM bills_of_materials WHERE identifier='BOM-EM-001'),
 (SELECT id FROM part_types WHERE identifier='PT-INT-001'), 1.0, NULL, 1),
('BOMC-EM-COVER', (SELECT id FROM bills_of_materials WHERE identifier='BOM-EM-001'),
 (SELECT id FROM part_types WHERE identifier='PT-INT-002'), 2.0, NULL, 2),
('BOMC-EM-SHAFT', (SELECT id FROM bills_of_materials WHERE identifier='BOM-EM-001'),
 (SELECT id FROM part_types WHERE identifier='PT-INT-004'), 1.0, NULL, 3),
('BOMC-EM-BEARING', (SELECT id FROM bills_of_materials WHERE identifier='BOM-EM-001'),
 (SELECT id FROM part_types WHERE identifier='PT-RAW-006'), 2.0, NULL, 4),
('BOMC-EM-BOLT', (SELECT id FROM bills_of_materials WHERE identifier='BOM-EM-001'),
 (SELECT id FROM part_types WHERE identifier='PT-RAW-007'), 8.0, NULL, 5),
('BOMC-EM-SEAL', (SELECT id FROM bills_of_materials WHERE identifier='BOM-EM-001'),
 (SELECT id FROM part_types WHERE identifier='PT-RAW-008'), 2.0, NULL, 6);

-- BOM Components for Pump Unit
INSERT INTO bom_components (identifier, bom_id, part_type_id, quantity, parent_component_id, sequence_order) VALUES
('BOMC-PUMP-CASING', (SELECT id FROM bills_of_materials WHERE identifier='BOM-PUMP-001'),
 (SELECT id FROM part_types WHERE identifier='PT-INT-003'), 1.0, NULL, 1),
('BOMC-PUMP-SHAFT', (SELECT id FROM bills_of_materials WHERE identifier='BOM-PUMP-001'),
 (SELECT id FROM part_types WHERE identifier='PT-INT-004'), 1.0, NULL, 2),
('BOMC-PUMP-BEARING', (SELECT id FROM bills_of_materials WHERE identifier='BOM-PUMP-001'),
 (SELECT id FROM part_types WHERE identifier='PT-RAW-006'), 2.0, NULL, 3),
('BOMC-PUMP-SEAL', (SELECT id FROM bills_of_materials WHERE identifier='BOM-PUMP-001'),
 (SELECT id FROM part_types WHERE identifier='PT-RAW-008'), 3.0, NULL, 4),
('BOMC-PUMP-BOLT', (SELECT id FROM bills_of_materials WHERE identifier='BOM-PUMP-001'),
 (SELECT id FROM part_types WHERE identifier='PT-RAW-007'), 12.0, NULL, 5);

-- BOM Components for Shaft Assembly
INSERT INTO bom_components (identifier, bom_id, part_type_id, quantity, parent_component_id, sequence_order) VALUES
('BOMC-SHAFT-ROD', (SELECT id FROM bills_of_materials WHERE identifier='BOM-SHAFT-001'),
 (SELECT id FROM part_types WHERE identifier='PT-RAW-004'), 1.0, NULL, 1);

-- BOM Components for PCB Assembly
INSERT INTO bom_components (identifier, bom_id, part_type_id, quantity, parent_component_id, sequence_order) VALUES
('BOMC-PCB-BLANK', (SELECT id FROM bills_of_materials WHERE identifier='BOM-PCB-001'),
 (SELECT id FROM part_types WHERE identifier='PT-RAW-005'), 1.0, NULL, 1);

-- =============================================================================
-- PROCESS PLANS
-- =============================================================================
INSERT INTO process_plans (identifier, name, description, part_type_id) VALUES
('PP-MACHINED-HOUSING', 'Machined Housing Routing', 'Process plan for milling steel housing',
 (SELECT id FROM part_types WHERE identifier='PT-INT-001')),
('PP-STAMPED-COVER', 'Stamped Cover Routing', 'Process plan for stamping aluminum cover',
 (SELECT id FROM part_types WHERE identifier='PT-INT-002')),
('PP-MOLDED-CASING', 'Injection Molded Casing Routing', 'Process plan for plastic casing',
 (SELECT id FROM part_types WHERE identifier='PT-INT-003')),
('PP-TURNED-SHAFT', 'Turned Shaft Routing', 'Process plan for turned shaft',
 (SELECT id FROM part_types WHERE identifier='PT-INT-004')),
('PP-PCB-ASSEMBLY', 'PCB Assembly Routing', 'Process plan for PCB assembly',
 (SELECT id FROM part_types WHERE identifier='PT-INT-005')),
('PP-MOTOR-ASSEMBLY', 'Motor Assembly Routing', 'Final assembly of electric motor',
 (SELECT id FROM part_types WHERE identifier='PT-FG-001')),
('PP-PUMP-ASSEMBLY', 'Pump Assembly Routing', 'Final assembly of pump unit',
 (SELECT id FROM part_types WHERE identifier='PT-FG-002'));

-- Process Steps
INSERT INTO processes (identifier, name, description, process_plan_id, sequence_order, duration_seconds, setup_time_seconds, load_time_seconds, unload_time_seconds, group_type) VALUES
-- Housing Machining
('PROC-HOUSING-MILL1', 'Rough Milling', 'Rough milling of steel block',
 (SELECT id FROM process_plans WHERE identifier='PP-MACHINED-HOUSING'), 1, 240, 600, 30, 20, 'sequence'),
('PROC-HOUSING-MILL2', 'Finish Milling', 'Finish milling to final dimensions',
 (SELECT id FROM process_plans WHERE identifier='PP-MACHINED-HOUSING'), 2, 180, 300, 25, 20, 'sequence'),
('PROC-HOUSING-DRILL', 'Drilling & Tapping', 'Drill and tap mounting holes',
 (SELECT id FROM process_plans WHERE identifier='PP-MACHINED-HOUSING'), 3, 120, 180, 20, 15, 'sequence'),
('PROC-HOUSING-INSPECT', 'Quality Inspection', 'Dimensional inspection of housing',
 (SELECT id FROM process_plans WHERE identifier='PP-MACHINED-HOUSING'), 4, 90, 60, 15, 15, 'sequence'),
-- Stamped Cover
('PROC-COVER-STAMP', 'Stamping', 'Stamp aluminum sheet into cover shape',
 (SELECT id FROM process_plans WHERE identifier='PP-STAMPED-COVER'), 1, 20, 900, 10, 5, 'sequence'),
('PROC-COVER-DEBURR', 'Deburring', 'Remove sharp edges and burrs',
 (SELECT id FROM process_plans WHERE identifier='PP-STAMPED-COVER'), 2, 30, 60, 10, 10, 'sequence'),
('PROC-COVER-INSPECT', 'Visual Inspection', 'Visual quality check of cover',
 (SELECT id FROM process_plans WHERE identifier='PP-STAMPED-COVER'), 3, 15, 30, 5, 5, 'sequence'),
-- Injection Molded Casing
('PROC-CASING-MOLD', 'Injection Molding', 'Inject plastic into mold',
 (SELECT id FROM process_plans WHERE identifier='PP-MOLDED-CASING'), 1, 40, 1200, 15, 10, 'sequence'),
('PROC-CASING-TRIM', 'Trimming', 'Remove flash and gates',
 (SELECT id FROM process_plans WHERE identifier='PP-MOLDED-CASING'), 2, 25, 120, 10, 10, 'sequence'),
('PROC-CASING-INSPECT', 'Quality Check', 'Dimensional and visual inspection',
 (SELECT id FROM process_plans WHERE identifier='PP-MOLDED-CASING'), 3, 20, 60, 5, 5, 'sequence'),
-- Turned Shaft
('PROC-SHAFT-ROUGH', 'Rough Turning', 'Rough turning of steel rod',
 (SELECT id FROM process_plans WHERE identifier='PP-TURNED-SHAFT'), 1, 180, 480, 25, 20, 'sequence'),
('PROC-SHAFT-FINISH', 'Finish Turning', 'Finish turning to tolerance',
 (SELECT id FROM process_plans WHERE identifier='PP-TURNED-SHAFT'), 2, 150, 300, 20, 20, 'sequence'),
('PROC-SHAFT-GRIND', 'Grinding', 'Precision grinding of bearing seats',
 (SELECT id FROM process_plans WHERE identifier='PP-TURNED-SHAFT'), 3, 120, 240, 20, 15, 'sequence'),
('PROC-SHAFT-INSPECT', 'Dimensional Inspection', 'Check runout and dimensions',
 (SELECT id FROM process_plans WHERE identifier='PP-TURNED-SHAFT'), 4, 60, 120, 15, 10, 'sequence'),
-- PCB Assembly
('PROC-PCB-PLACE', 'Component Placement', 'Place electronic components on PCB',
 (SELECT id FROM process_plans WHERE identifier='PP-PCB-ASSEMBLY'), 1, 120, 480, 30, 25, 'sequence'),
('PROC-PCB-SOLDER', 'Soldering', 'Reflow soldering of components',
 (SELECT id FROM process_plans WHERE identifier='PP-PCB-ASSEMBLY'), 2, 90, 300, 15, 15, 'sequence'),
('PROC-PCB-TEST', 'Electrical Test', 'Functional test of assembled PCB',
 (SELECT id FROM process_plans WHERE identifier='PP-PCB-ASSEMBLY'), 3, 60, 120, 15, 15, 'sequence'),
-- Motor Assembly
('PROC-MOTOR-PREP', 'Component Preparation', 'Prepare all components for assembly',
 (SELECT id FROM process_plans WHERE identifier='PP-MOTOR-ASSEMBLY'), 1, 120, 180, NULL, NULL, 'sequence'),
('PROC-MOTOR-SUB1', 'Bearing Press', 'Press bearings onto shaft',
 (SELECT id FROM process_plans WHERE identifier='PP-MOTOR-ASSEMBLY'), 2, 90, 120, NULL, NULL, 'sequence'),
('PROC-MOTOR-SUB2', 'Rotor Insertion', 'Insert rotor assembly into housing',
 (SELECT id FROM process_plans WHERE identifier='PP-MOTOR-ASSEMBLY'), 3, 150, 60, NULL, NULL, 'sequence'),
('PROC-MOTOR-SUB3', 'End Cover Assembly', 'Attach end covers with bolts',
 (SELECT id FROM process_plans WHERE identifier='PP-MOTOR-ASSEMBLY'), 4, 180, 90, NULL, NULL, 'sequence'),
('PROC-MOTOR-TEST', 'Performance Test', 'Run motor and test performance',
 (SELECT id FROM process_plans WHERE identifier='PP-MOTOR-ASSEMBLY'), 5, 300, 240, NULL, NULL, 'sequence'),
-- Pump Assembly
('PROC-PUMP-PREP', 'Component Preparation', 'Prepare pump components',
 (SELECT id FROM process_plans WHERE identifier='PP-PUMP-ASSEMBLY'), 1, 90, 150, NULL, NULL, 'sequence'),
('PROC-PUMP-IMPELLER', 'Impeller Mounting', 'Mount impeller on shaft',
 (SELECT id FROM process_plans WHERE identifier='PP-PUMP-ASSEMBLY'), 2, 120, 90, NULL, NULL, 'sequence'),
('PROC-PUMP-CASING', 'Casing Assembly', 'Assemble casing around impeller',
 (SELECT id FROM process_plans WHERE identifier='PP-PUMP-ASSEMBLY'), 3, 150, 120, NULL, NULL, 'sequence'),
('PROC-PUMP-SEAL', 'Seal Installation', 'Install mechanical seals',
 (SELECT id FROM process_plans WHERE identifier='PP-PUMP-ASSEMBLY'), 4, 90, 60, NULL, NULL, 'sequence'),
('PROC-PUMP-TEST', 'Hydrostatic Test', 'Pressure test pump assembly',
 (SELECT id FROM process_plans WHERE identifier='PP-PUMP-ASSEMBLY'), 5, 240, 300, NULL, NULL, 'sequence');

-- =============================================================================
-- PROCESS-RESOURCE ASSIGNMENTS
-- =============================================================================
INSERT INTO process_resources (process_id, resource_id, minimum_number, maximum_number)
SELECT p.id, r.id, 1, 1 FROM processes p, resources r
WHERE p.identifier LIKE 'PROC-HOUSING-%' AND r.identifier IN ('RES-CNC-001', 'RES-CNC-002');

INSERT INTO process_resources (process_id, resource_id, minimum_number, maximum_number)
SELECT p.id, r.id, 1, 1 FROM processes p, resources r
WHERE p.identifier LIKE 'PROC-SHAFT-%' AND r.identifier IN ('RES-CNC-003', 'RES-CNC-004');

INSERT INTO process_resources (process_id, resource_id, minimum_number, maximum_number)
SELECT p.id, r.id, 1, 1 FROM processes p, resources r
WHERE p.identifier LIKE 'PROC-COVER-%' AND r.identifier = 'RES-STAMP-001';

INSERT INTO process_resources (process_id, resource_id, minimum_number, maximum_number)
SELECT p.id, r.id, 1, 1 FROM processes p, resources r
WHERE p.identifier LIKE 'PROC-CASING-%' AND r.identifier IN ('RES-INJ-001', 'RES-INJ-002');

INSERT INTO process_resources (process_id, resource_id, minimum_number, maximum_number)
SELECT p.id, r.id, 1, 1 FROM processes p, resources r
WHERE p.identifier LIKE 'PROC-PCB-%' AND r.identifier = 'RES-ASM-003';

INSERT INTO process_resources (process_id, resource_id, minimum_number, maximum_number)
SELECT p.id, r.id, 1, 1 FROM processes p, resources r
WHERE p.identifier LIKE 'PROC-MOTOR-%' AND r.identifier = 'RES-ASM-001';

INSERT INTO process_resources (process_id, resource_id, minimum_number, maximum_number)
SELECT p.id, r.id, 1, 1 FROM processes p, resources r
WHERE p.identifier LIKE 'PROC-PUMP-%' AND r.identifier = 'RES-ASM-002';

INSERT INTO process_resources (process_id, resource_id, minimum_number, maximum_number)
SELECT p.id, r.id, 1, 1 FROM processes p, resources r
WHERE p.identifier IN ('PROC-MOTOR-TEST', 'PROC-PUMP-TEST') AND r.identifier = 'RES-TEST-001';

-- =============================================================================
-- CALENDARS
-- =============================================================================
INSERT INTO calendars (identifier, name, description, production_days_per_year) VALUES
('CAL-STANDARD', 'Standard Production Calendar', '2-shift operation Mon-Fri', 250);

INSERT INTO shifts (identifier, calendar_id, day_of_week, start_time, end_time) VALUES
('SHIFT-EARLY', (SELECT id FROM calendars WHERE identifier='CAL-STANDARD'), 'monday', '06:00:00', '14:00:00'),
('SHIFT-LATE', (SELECT id FROM calendars WHERE identifier='CAL-STANDARD'), 'monday', '14:00:00', '22:00:00');

-- Add breaks to early shift
INSERT INTO breaks (identifier, shift_id, start_time, end_time, name) VALUES
('BRK-EARLY-1', (SELECT id FROM shifts WHERE identifier='SHIFT-EARLY'), '09:00:00', '09:15:00', 'Morning Break'),
('BRK-EARLY-2', (SELECT id FROM shifts WHERE identifier='SHIFT-EARLY'), '12:00:00', '12:30:00', 'Lunch Break');

-- Add breaks to late shift
INSERT INTO breaks (identifier, shift_id, start_time, end_time, name) VALUES
('BRK-LATE-1', (SELECT id FROM shifts WHERE identifier='SHIFT-LATE'), '17:00:00', '17:15:00', 'Afternoon Break'),
('BRK-LATE-2', (SELECT id FROM shifts WHERE identifier='SHIFT-LATE'), '19:30:00', '20:00:00', 'Dinner Break');

-- Holidays
INSERT INTO holidays (identifier, calendar_id, holiday_date, name) VALUES
('HOL-NEWYEAR', (SELECT id FROM calendars WHERE identifier='CAL-STANDARD'), '2026-01-01', 'New Year Day'),
('HOL-MAYDAY', (SELECT id FROM calendars WHERE identifier='CAL-STANDARD'), '2026-05-01', 'Labour Day'),
('HOL-CHRISTMAS', (SELECT id FROM calendars WHERE identifier='CAL-STANDARD'), '2026-12-25', 'Christmas Day'),
('HOL-CHRISTMAS2', (SELECT id FROM calendars WHERE identifier='CAL-STANDARD'), '2026-12-26', 'Boxing Day');

-- =============================================================================
-- RESOURCE-SHIFT ASSIGNMENTS
-- =============================================================================
INSERT INTO resource_shift_assignments (resource_id, calendar_id)
SELECT r.id, c.id FROM resources r, calendars c
WHERE c.identifier = 'CAL-STANDARD' AND r.resource_type IN ('machine', 'station', 'conveyor', 'buffer');

-- =============================================================================
-- ORDERS
-- =============================================================================
INSERT INTO orders (identifier, status, due_date, release_date, priority) VALUES
('ORD-2026-001', 'released', '2026-05-20 00:00:00', '2026-05-10 06:00:00', 'high'),
('ORD-2026-002', 'released', '2026-05-22 00:00:00', '2026-05-12 06:00:00', 'medium'),
('ORD-2026-003', 'released', '2026-05-25 00:00:00', '2026-05-13 06:00:00', 'medium'),
('ORD-2026-004', 'created', '2026-06-01 00:00:00', '2026-05-20 06:00:00', 'low');

-- Order Lines
INSERT INTO order_lines (identifier, order_id, part_type_id, quantity, due_date, process_plan_id, status) VALUES
('OL-001-1', (SELECT id FROM orders WHERE identifier='ORD-2026-001'),
 (SELECT id FROM part_types WHERE identifier='PT-FG-001'), 50, '2026-05-20 00:00:00',
 (SELECT id FROM process_plans WHERE identifier='PP-MOTOR-ASSEMBLY'), 'released'),
('OL-001-2', (SELECT id FROM orders WHERE identifier='ORD-2026-001'),
 (SELECT id FROM part_types WHERE identifier='PT-FG-002'), 20, '2026-05-20 00:00:00',
 (SELECT id FROM process_plans WHERE identifier='PP-PUMP-ASSEMBLY'), 'released'),
('OL-002-1', (SELECT id FROM orders WHERE identifier='ORD-2026-002'),
 (SELECT id FROM part_types WHERE identifier='PT-FG-001'), 30, '2026-05-22 00:00:00',
 (SELECT id FROM process_plans WHERE identifier='PP-MOTOR-ASSEMBLY'), 'released'),
('OL-003-1', (SELECT id FROM orders WHERE identifier='ORD-2026-003'),
 (SELECT id FROM part_types WHERE identifier='PT-FG-002'), 15, '2026-05-25 00:00:00',
 (SELECT id FROM process_plans WHERE identifier='PP-PUMP-ASSEMBLY'), 'released'),
('OL-004-1', (SELECT id FROM orders WHERE identifier='ORD-2026-004'),
 (SELECT id FROM part_types WHERE identifier='PT-FG-001'), 100, '2026-06-01 00:00:00',
 (SELECT id FROM process_plans WHERE identifier='PP-MOTOR-ASSEMBLY'), 'created');

-- =============================================================================
-- LAYOUT
-- =============================================================================
INSERT INTO layouts (identifier, name, description, coordinate_system) VALUES
('LAYOUT-MAIN', 'Main Factory Floor', 'ASMG Main Manufacturing Floor Layout', 'upperLeftBased');

-- Placements (machines positioned on the factory floor)
INSERT INTO placements (layout_id, resource_id, x, y, z, rotation_z_deg) VALUES
((SELECT id FROM layouts WHERE identifier='LAYOUT-MAIN'), (SELECT id FROM resources WHERE identifier='RES-SRC-001'), 1.0, 2.0, 0.0, 0.0),
((SELECT id FROM layouts WHERE identifier='LAYOUT-MAIN'), (SELECT id FROM resources WHERE identifier='RES-BUF-001'), 3.0, 2.0, 0.0, 0.0),
((SELECT id FROM layouts WHERE identifier='LAYOUT-MAIN'), (SELECT id FROM resources WHERE identifier='RES-CNC-001'), 7.0, 2.0, 0.0, 90.0),
((SELECT id FROM layouts WHERE identifier='LAYOUT-MAIN'), (SELECT id FROM resources WHERE identifier='RES-CNC-002'), 10.0, 2.0, 0.0, 90.0),
((SELECT id FROM layouts WHERE identifier='LAYOUT-MAIN'), (SELECT id FROM resources WHERE identifier='RES-CNC-003'), 13.0, 2.0, 0.0, 90.0),
((SELECT id FROM layouts WHERE identifier='LAYOUT-MAIN'), (SELECT id FROM resources WHERE identifier='RES-CNC-004'), 16.0, 2.0, 0.0, 90.0),
((SELECT id FROM layouts WHERE identifier='LAYOUT-MAIN'), (SELECT id FROM resources WHERE identifier='RES-STAMP-001'), 7.0, 8.0, 0.0, 0.0),
((SELECT id FROM layouts WHERE identifier='LAYOUT-MAIN'), (SELECT id FROM resources WHERE identifier='RES-INJ-001'), 12.0, 8.0, 0.0, 0.0),
((SELECT id FROM layouts WHERE identifier='LAYOUT-MAIN'), (SELECT id FROM resources WHERE identifier='RES-INJ-002'), 15.0, 8.0, 0.0, 0.0),
((SELECT id FROM layouts WHERE identifier='LAYOUT-MAIN'), (SELECT id FROM resources WHERE identifier='RES-ASM-003'), 7.0, 14.0, 0.0, 0.0),
((SELECT id FROM layouts WHERE identifier='LAYOUT-MAIN'), (SELECT id FROM resources WHERE identifier='RES-BUF-002'), 20.0, 2.0, 0.0, 0.0),
((SELECT id FROM layouts WHERE identifier='LAYOUT-MAIN'), (SELECT id FROM resources WHERE identifier='RES-CONV-001'), 22.0, 2.0, 0.0, 0.0),
((SELECT id FROM layouts WHERE identifier='LAYOUT-MAIN'), (SELECT id FROM resources WHERE identifier='RES-ASM-001'), 27.0, 2.0, 0.0, 0.0),
((SELECT id FROM layouts WHERE identifier='LAYOUT-MAIN'), (SELECT id FROM resources WHERE identifier='RES-ASM-002'), 27.0, 6.0, 0.0, 0.0),
((SELECT id FROM layouts WHERE identifier='LAYOUT-MAIN'), (SELECT id FROM resources WHERE identifier='RES-CONV-002'), 27.0, 10.0, 0.0, 90.0),
((SELECT id FROM layouts WHERE identifier='LAYOUT-MAIN'), (SELECT id FROM resources WHERE identifier='RES-TEST-001'), 22.0, 10.0, 0.0, 0.0),
((SELECT id FROM layouts WHERE identifier='LAYOUT-MAIN'), (SELECT id FROM resources WHERE identifier='RES-CONV-004'), 18.0, 10.0, 0.0, 0.0),
((SELECT id FROM layouts WHERE identifier='LAYOUT-MAIN'), (SELECT id FROM resources WHERE identifier='RES-BUF-004'), 14.0, 10.0, 0.0, 0.0),
((SELECT id FROM layouts WHERE identifier='LAYOUT-MAIN'), (SELECT id FROM resources WHERE identifier='RES-SNK-001'), 10.0, 10.0, 0.0, 0.0),
((SELECT id FROM layouts WHERE identifier='LAYOUT-MAIN'), (SELECT id FROM resources WHERE identifier='RES-PNP-001'), 10.0, 5.0, 0.0, 0.0),
((SELECT id FROM layouts WHERE identifier='LAYOUT-MAIN'), (SELECT id FROM resources WHERE identifier='RES-PNP-002'), 25.0, 5.0, 0.0, 0.0);

-- =============================================================================
-- CONNECTIONS (Material flow path)
-- =============================================================================
INSERT INTO connections (identifier, from_resource_id, to_resource_id, connection_type, connection_name) VALUES
('CONN-001', (SELECT id FROM resources WHERE identifier='RES-SRC-001'), (SELECT id FROM resources WHERE identifier='RES-BUF-001'), 'output', 'conveyor'),
('CONN-002', (SELECT id FROM resources WHERE identifier='RES-BUF-001'), (SELECT id FROM resources WHERE identifier='RES-CNC-001'), 'output', 'conveyor'),
('CONN-003', (SELECT id FROM resources WHERE identifier='RES-BUF-001'), (SELECT id FROM resources WHERE identifier='RES-CNC-002'), 'output', 'conveyor'),
('CONN-004', (SELECT id FROM resources WHERE identifier='RES-BUF-001'), (SELECT id FROM resources WHERE identifier='RES-CNC-003'), 'output', 'conveyor'),
('CONN-005', (SELECT id FROM resources WHERE identifier='RES-BUF-001'), (SELECT id FROM resources WHERE identifier='RES-CNC-004'), 'output', 'conveyor'),
('CONN-006', (SELECT id FROM resources WHERE identifier='RES-CNC-001'), (SELECT id FROM resources WHERE identifier='RES-BUF-002'), 'output', 'conveyor'),
('CONN-007', (SELECT id FROM resources WHERE identifier='RES-CNC-002'), (SELECT id FROM resources WHERE identifier='RES-BUF-002'), 'output', 'conveyor'),
('CONN-008', (SELECT id FROM resources WHERE identifier='RES-CNC-003'), (SELECT id FROM resources WHERE identifier='RES-BUF-002'), 'output', 'conveyor'),
('CONN-009', (SELECT id FROM resources WHERE identifier='RES-CNC-004'), (SELECT id FROM resources WHERE identifier='RES-BUF-002'), 'output', 'conveyor'),
('CONN-010', (SELECT id FROM resources WHERE identifier='RES-STAMP-001'), (SELECT id FROM resources WHERE identifier='RES-BUF-002'), 'output', 'conveyor'),
('CONN-011', (SELECT id FROM resources WHERE identifier='RES-INJ-001'), (SELECT id FROM resources WHERE identifier='RES-BUF-002'), 'output', 'conveyor'),
('CONN-012', (SELECT id FROM resources WHERE identifier='RES-INJ-002'), (SELECT id FROM resources WHERE identifier='RES-BUF-002'), 'output', 'conveyor'),
('CONN-013', (SELECT id FROM resources WHERE identifier='RES-ASM-003'), (SELECT id FROM resources WHERE identifier='RES-BUF-002'), 'output', 'conveyor'),
('CONN-014', (SELECT id FROM resources WHERE identifier='RES-BUF-002'), (SELECT id FROM resources WHERE identifier='RES-CONV-001'), 'output', 'conveyor'),
('CONN-015', (SELECT id FROM resources WHERE identifier='RES-CONV-001'), (SELECT id FROM resources WHERE identifier='RES-ASM-001'), 'output', 'conveyor'),
('CONN-016', (SELECT id FROM resources WHERE identifier='RES-CONV-001'), (SELECT id FROM resources WHERE identifier='RES-ASM-002'), 'output', 'conveyor'),
('CONN-017', (SELECT id FROM resources WHERE identifier='RES-ASM-001'), (SELECT id FROM resources WHERE identifier='RES-CONV-002'), 'output', 'conveyor'),
('CONN-018', (SELECT id FROM resources WHERE identifier='RES-ASM-002'), (SELECT id FROM resources WHERE identifier='RES-CONV-002'), 'output', 'conveyor'),
('CONN-019', (SELECT id FROM resources WHERE identifier='RES-CONV-002'), (SELECT id FROM resources WHERE identifier='RES-TEST-001'), 'output', 'conveyor'),
('CONN-020', (SELECT id FROM resources WHERE identifier='RES-TEST-001'), (SELECT id FROM resources WHERE identifier='RES-CONV-004'), 'output', 'conveyor'),
('CONN-021', (SELECT id FROM resources WHERE identifier='RES-CONV-004'), (SELECT id FROM resources WHERE identifier='RES-BUF-004'), 'output', 'conveyor'),
('CONN-022', (SELECT id FROM resources WHERE identifier='RES-BUF-004'), (SELECT id FROM resources WHERE identifier='RES-SNK-001'), 'output', 'conveyor');

-- =============================================================================
-- MES OPERATIONAL DATA
-- =============================================================================

-- Resource Status (initial states)
INSERT INTO resource_status (resource_id, status, uptime_seconds, parts_processed_today) VALUES
((SELECT id FROM resources WHERE identifier='RES-CNC-001'), 'busy', 18000, 45),
((SELECT id FROM resources WHERE identifier='RES-CNC-002'), 'idle', 15000, 32),
((SELECT id FROM resources WHERE identifier='RES-CNC-003'), 'busy', 20000, 60),
((SELECT id FROM resources WHERE identifier='RES-CNC-004'), 'idle', 14000, 28),
((SELECT id FROM resources WHERE identifier='RES-STAMP-001'), 'setup', 8000, 120),
((SELECT id FROM resources WHERE identifier='RES-INJ-001'), 'busy', 22000, 200),
((SELECT id FROM resources WHERE identifier='RES-INJ-002'), 'busy', 21000, 185),
((SELECT id FROM resources WHERE identifier='RES-ASM-001'), 'busy', 16000, 15),
((SELECT id FROM resources WHERE identifier='RES-ASM-002'), 'idle', 12000, 10),
((SELECT id FROM resources WHERE identifier='RES-ASM-003'), 'busy', 14000, 40),
((SELECT id FROM resources WHERE identifier='RES-TEST-001'), 'busy', 18000, 20),
((SELECT id FROM resources WHERE identifier='RES-PNP-001'), 'busy', 24000, 500),
((SELECT id FROM resources WHERE identifier='RES-PNP-002'), 'idle', 20000, 380),
((SELECT id FROM resources WHERE identifier='RES-AGV-001'), 'busy', 22000, 80);

-- Jobs
INSERT INTO jobs (identifier, order_line_id, process_plan_id, status, priority, release_date, start_time, due_date, current_process_id) VALUES
('JOB-001-MOTOR', (SELECT id FROM order_lines WHERE identifier='OL-001-1'),
 (SELECT id FROM process_plans WHERE identifier='PP-MOTOR-ASSEMBLY'), 'started', 'high',
 '2026-05-10 06:00:00', '2026-05-13 07:00:00', '2026-05-20 00:00:00',
 (SELECT id FROM processes WHERE identifier='PROC-MOTOR-SUB2')),
('JOB-001-PUMP', (SELECT id FROM order_lines WHERE identifier='OL-001-2'),
 (SELECT id FROM process_plans WHERE identifier='PP-PUMP-ASSEMBLY'), 'released', 'high',
 '2026-05-10 06:00:00', NULL, '2026-05-20 00:00:00', NULL),
('JOB-002-MOTOR', (SELECT id FROM order_lines WHERE identifier='OL-002-1'),
 (SELECT id FROM process_plans WHERE identifier='PP-MOTOR-ASSEMBLY'), 'released', 'medium',
 '2026-05-12 06:00:00', NULL, '2026-05-22 00:00:00', NULL);

-- Job Effort
INSERT INTO job_effort (job_id, effort_type, processing_time_seconds, setup_time_seconds, parts_produced, parts_scrapped) VALUES
((SELECT id FROM jobs WHERE identifier='JOB-001-MOTOR'), 'planned', 840, 690, 50, 0),
((SELECT id FROM jobs WHERE identifier='JOB-001-MOTOR'), 'actual', 920, 750, 22, 1),
((SELECT id FROM jobs WHERE identifier='JOB-001-PUMP'), 'planned', 690, 720, 20, 0),
((SELECT id FROM jobs WHERE identifier='JOB-002-MOTOR'), 'planned', 840, 690, 30, 0);

-- Inventory
INSERT INTO inventory (identifier, part_type_id, quantity, min_threshold, max_threshold, location_id) VALUES
('INV-RAW-001', (SELECT id FROM part_types WHERE identifier='PT-RAW-001'), 150.0, 20.0, 300.0, (SELECT id FROM resources WHERE identifier='RES-BUF-001')),
('INV-RAW-002', (SELECT id FROM part_types WHERE identifier='PT-RAW-002'), 500.0, 50.0, 800.0, (SELECT id FROM resources WHERE identifier='RES-BUF-001')),
('INV-RAW-003', (SELECT id FROM part_types WHERE identifier='PT-RAW-003'), 2000.0, 500.0, 5000.0, (SELECT id FROM resources WHERE identifier='RES-BUF-001')),
('INV-RAW-004', (SELECT id FROM part_types WHERE identifier='PT-RAW-004'), 200.0, 30.0, 400.0, (SELECT id FROM resources WHERE identifier='RES-BUF-001')),
('INV-RAW-005', (SELECT id FROM part_types WHERE identifier='PT-RAW-005'), 100.0, 10.0, 200.0, (SELECT id FROM resources WHERE identifier='RES-BUF-001')),
('INV-RAW-006', (SELECT id FROM part_types WHERE identifier='PT-RAW-006'), 300.0, 50.0, 500.0, (SELECT id FROM resources WHERE identifier='RES-BUF-003')),
('INV-RAW-007', (SELECT id FROM part_types WHERE identifier='PT-RAW-007'), 2000.0, 200.0, 5000.0, (SELECT id FROM resources WHERE identifier='RES-BUF-003')),
('INV-RAW-008', (SELECT id FROM part_types WHERE identifier='PT-RAW-008'), 150.0, 30.0, 300.0, (SELECT id FROM resources WHERE identifier='RES-BUF-003')),
('INV-FG-001', (SELECT id FROM part_types WHERE identifier='PT-FG-001'), 8.0, 5.0, 50.0, (SELECT id FROM resources WHERE identifier='RES-BUF-004')),
('INV-FG-002', (SELECT id FROM part_types WHERE identifier='PT-FG-002'), 3.0, 2.0, 30.0, (SELECT id FROM resources WHERE identifier='RES-BUF-004'));

-- =============================================================================
-- SKILL DEFINITIONS
-- =============================================================================
INSERT INTO skill_definitions (identifier, name, description) VALUES
('SKILL-CNC-MILL', 'CNC Milling Operation', 'Ability to operate 5-axis CNC mills'),
('SKILL-CNC-LATHE', 'CNC Turning Operation', 'Ability to operate CNC lathes'),
('SKILL-ASSEMBLY', 'Mechanical Assembly', 'Ability to assemble mechanical components'),
('SKILL-QC', 'Quality Control', 'Ability to perform quality inspections'),
('SKILL-MAINTENANCE', 'Machine Maintenance', 'Ability to repair and maintain machines');

INSERT INTO employee_skills (resource_id, skill_id, proficiency_level) VALUES
((SELECT id FROM resources WHERE identifier='RES-WKR-001'), (SELECT id FROM skill_definitions WHERE identifier='SKILL-CNC-MILL'), 'expert'),
((SELECT id FROM resources WHERE identifier='RES-WKR-001'), (SELECT id FROM skill_definitions WHERE identifier='SKILL-MAINTENANCE'), 'intermediate'),
((SELECT id FROM resources WHERE identifier='RES-WKR-002'), (SELECT id FROM skill_definitions WHERE identifier='SKILL-CNC-LATHE'), 'expert'),
((SELECT id FROM resources WHERE identifier='RES-WKR-003'), (SELECT id FROM skill_definitions WHERE identifier='SKILL-ASSEMBLY'), 'expert'),
((SELECT id FROM resources WHERE identifier='RES-WKR-004'), (SELECT id FROM skill_definitions WHERE identifier='SKILL-QC'), 'expert');