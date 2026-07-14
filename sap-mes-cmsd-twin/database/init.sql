-- =============================================================================
-- SAP/MES → CMSD Digital Twin — MySQL Database Schema
-- Covers both SAP Master Data and MES Operational Data
-- =============================================================================

CREATE DATABASE IF NOT EXISTS factory_digital_twin
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE factory_digital_twin;

-- =============================================================================
-- SAP MASTER DATA TABLES
-- =============================================================================

-- Resource Classes (groups of similar machines)
CREATE TABLE resource_classes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    resource_type ENUM(
        'carrier','conveyor','crane','employee','fixture','machine',
        'path','powerAndFree','station','tool','transporter','other',
        'buffer','source','sink','elevator','articulatedRobot','gripper',
        'mobileRobot','warehouseRack','dispatcher','chargingStation','gate',
        'automatedWarehouse'
    ) NOT NULL,
    hourly_rate DECIMAL(10,2) DEFAULT NULL,
    size_length DECIMAL(10,3) DEFAULT NULL,
    size_width DECIMAL(10,3) DEFAULT NULL,
    size_height DECIMAL(10,3) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Resources (individual machine/worker instances)
CREATE TABLE resources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    resource_class_id INT DEFAULT NULL,
    resource_type ENUM(
        'carrier','conveyor','crane','employee','fixture','machine',
        'path','powerAndFree','station','tool','transporter','other',
        'buffer','source','sink','elevator','articulatedRobot','gripper',
        'mobileRobot','warehouseRack','dispatcher','chargingStation','gate',
        'automatedWarehouse'
    ) NOT NULL,
    -- Capacity & Reliability
    capacity INT DEFAULT NULL,
    availability DECIMAL(5,2) DEFAULT NULL COMMENT 'Technical availability % (0-100)',
    mttr_seconds INT DEFAULT NULL COMMENT 'Mean Time To Repair in seconds',
    mtbf_seconds INT DEFAULT NULL COMMENT 'Mean Time Between Failures in seconds',
    mcbf INT DEFAULT NULL COMMENT 'Mean Cycles Between Failures',
    reliability DECIMAL(5,2) DEFAULT NULL COMMENT 'Reliability/waste rate % (0-100)',
    -- Timing
    cycle_time_seconds INT DEFAULT NULL COMMENT 'Takt time in seconds',
    desired_replenishment_time_seconds INT DEFAULT NULL,
    -- Transport
    transport_capacity INT DEFAULT NULL,
    tow_bar_length DECIMAL(10,3) DEFAULT NULL,
    -- Worker
    worker_count INT DEFAULT NULL,
    -- Decision / Routing
    decision_rule ENUM('fifo','lifo','koz','loz','sst','hcm','slack','random') DEFAULT NULL,
    routing_rule ENUM('sst','roundRobin','random') DEFAULT NULL,
    -- Dimensions
    size_length DECIMAL(10,3) DEFAULT NULL,
    size_width DECIMAL(10,3) DEFAULT NULL,
    size_height DECIMAL(10,3) DEFAULT NULL,
    hourly_rate DECIMAL(10,2) DEFAULT NULL,
    -- Buffer config
    buffer_type ENUM('fifo','lifo','priority') DEFAULT NULL,
    buffer_capacity INT DEFAULT NULL,
    -- Conveyor config
    conveyor_speed DECIMAL(10,3) DEFAULT NULL,
    conveyor_length DECIMAL(10,3) DEFAULT NULL,
    conveyor_accumulating TINYINT(1) DEFAULT 1,
    -- Energy
    energy_working_kw DECIMAL(10,3) DEFAULT NULL,
    energy_standby_kw DECIMAL(10,3) DEFAULT NULL,
    energy_failed_kw DECIMAL(10,3) DEFAULT NULL,
    energy_off_kw DECIMAL(10,3) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (resource_class_id) REFERENCES resource_classes(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- Part Types (part master data)
CREATE TABLE part_types (
    id INT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    -- Physical dimensions
    size_length DECIMAL(10,3) DEFAULT NULL,
    size_width DECIMAL(10,3) DEFAULT NULL,
    size_height DECIMAL(10,3) DEFAULT NULL,
    weight_kg DECIMAL(10,4) DEFAULT NULL,
    -- Visual
    color VARCHAR(30) DEFAULT NULL,
    shape_3d VARCHAR(100) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Parts (individual part instances)
CREATE TABLE parts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(100) NOT NULL UNIQUE,
    part_type_id INT NOT NULL,
    production_status ENUM('unknown','workInProcess','finishedGood') DEFAULT 'unknown',
    location_x DECIMAL(10,3) DEFAULT NULL,
    location_y DECIMAL(10,3) DEFAULT NULL,
    location_z DECIMAL(10,3) DEFAULT NULL,
    lot_number VARCHAR(50) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (part_type_id) REFERENCES part_types(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Bills of Materials
CREATE TABLE bills_of_materials (
    id INT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) DEFAULT NULL,
    description TEXT,
    part_type_id INT DEFAULT NULL COMMENT 'Which part type this BOM is for',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (part_type_id) REFERENCES part_types(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- BOM Components (recursive via parent_component_id)
CREATE TABLE bom_components (
    id INT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(100) NOT NULL UNIQUE,
    bom_id INT NOT NULL,
    part_type_id INT DEFAULT NULL,
    quantity DECIMAL(10,3) NOT NULL DEFAULT 1.000,
    parent_component_id INT DEFAULT NULL COMMENT 'NULL = top-level component',
    sequence_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (bom_id) REFERENCES bills_of_materials(id) ON DELETE CASCADE,
    FOREIGN KEY (part_type_id) REFERENCES part_types(id) ON DELETE SET NULL,
    FOREIGN KEY (parent_component_id) REFERENCES bom_components(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Process Plans (Routings)
CREATE TABLE process_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    part_type_id INT DEFAULT NULL COMMENT 'Which part this routing is for',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (part_type_id) REFERENCES part_types(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- Process Steps (operations within a process plan)
CREATE TABLE processes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    process_plan_id INT NOT NULL,
    sequence_order INT NOT NULL DEFAULT 0,
    -- Timing
    duration_seconds INT DEFAULT NULL,
    setup_time_seconds INT DEFAULT NULL,
    load_time_seconds INT DEFAULT NULL,
    unload_time_seconds INT DEFAULT NULL,
    pick_time_seconds INT DEFAULT NULL,
    place_time_seconds INT DEFAULT NULL,
    -- Grouping (for branching logic)
    group_type ENUM('sequence','concurrent','decision') DEFAULT 'sequence',
    parent_process_id INT DEFAULT NULL COMMENT 'For nested process groups',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (process_plan_id) REFERENCES process_plans(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_process_id) REFERENCES processes(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Process-Resource assignments (which machines can do which steps)
CREATE TABLE process_resources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    process_id INT NOT NULL,
    resource_id INT NOT NULL,
    minimum_number INT DEFAULT 1,
    maximum_number INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (process_id) REFERENCES processes(id) ON DELETE CASCADE,
    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE,
    UNIQUE KEY unique_process_resource (process_id, resource_id)
) ENGINE=InnoDB;

-- Calendars (Shift schedules)
CREATE TABLE calendars (
    id INT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    production_days_per_year INT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Shifts
CREATE TABLE shifts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(100) NOT NULL UNIQUE,
    calendar_id INT NOT NULL,
    day_of_week ENUM('sunday','monday','tuesday','wednesday','thursday','friday','saturday') NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (calendar_id) REFERENCES calendars(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Breaks within shifts
CREATE TABLE breaks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(100) NOT NULL UNIQUE,
    shift_id INT NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    name VARCHAR(100) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shift_id) REFERENCES shifts(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Holidays
CREATE TABLE holidays (
    id INT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(100) NOT NULL UNIQUE,
    calendar_id INT NOT NULL,
    holiday_date DATE NOT NULL,
    name VARCHAR(255) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (calendar_id) REFERENCES calendars(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Shutdown periods (Betriebsferien)
CREATE TABLE shutdown_periods (
    id INT AUTO_INCREMENT PRIMARY KEY,
    calendar_id INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    description VARCHAR(255) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (calendar_id) REFERENCES calendars(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Resource-Shift assignments
CREATE TABLE resource_shift_assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    resource_id INT NOT NULL,
    calendar_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE,
    FOREIGN KEY (calendar_id) REFERENCES calendars(id) ON DELETE CASCADE,
    UNIQUE KEY unique_resource_calendar (resource_id, calendar_id)
) ENGINE=InnoDB;

-- Orders (Production orders)
CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(100) NOT NULL UNIQUE,
    status ENUM('created','released','completed','shipped','cancelled','unknown') DEFAULT 'created',
    due_date DATETIME DEFAULT NULL,
    release_date DATETIME DEFAULT NULL,
    priority VARCHAR(50) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Order Lines
CREATE TABLE order_lines (
    id INT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(100) NOT NULL UNIQUE,
    order_id INT NOT NULL,
    part_type_id INT DEFAULT NULL,
    quantity INT NOT NULL DEFAULT 1,
    due_date DATETIME DEFAULT NULL,
    release_date DATETIME DEFAULT NULL,
    process_plan_id INT DEFAULT NULL,
    status ENUM('created','released','completed','shipped','cancelled','unknown') DEFAULT 'created',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (part_type_id) REFERENCES part_types(id) ON DELETE SET NULL,
    FOREIGN KEY (process_plan_id) REFERENCES process_plans(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- Layouts
CREATE TABLE layouts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    coordinate_system ENUM('centerBased','upperLeftBased') DEFAULT 'upperLeftBased',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Placements (where resources sit in the layout)
CREATE TABLE placements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    layout_id INT NOT NULL,
    resource_id INT NOT NULL,
    x DECIMAL(10,3) NOT NULL DEFAULT 0.000,
    y DECIMAL(10,3) NOT NULL DEFAULT 0.000,
    z DECIMAL(10,3) NOT NULL DEFAULT 0.000,
    rotation_x_deg DECIMAL(6,2) DEFAULT 0.00,
    rotation_y_deg DECIMAL(6,2) DEFAULT 0.00,
    rotation_z_deg DECIMAL(6,2) DEFAULT 0.00,
    scale_x_percent DECIMAL(6,2) DEFAULT 100.00,
    scale_y_percent DECIMAL(6,2) DEFAULT 100.00,
    scale_z_percent DECIMAL(6,2) DEFAULT 100.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (layout_id) REFERENCES layouts(id) ON DELETE CASCADE,
    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE,
    UNIQUE KEY unique_layout_resource (layout_id, resource_id)
) ENGINE=InnoDB;

-- Connections (predecessor/successor between resources)
CREATE TABLE connections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(100) NOT NULL UNIQUE,
    from_resource_id INT NOT NULL,
    to_resource_id INT NOT NULL,
    connection_type ENUM('input','output') DEFAULT 'output',
    connection_name ENUM('conveyor','footpath','logical','transporter') DEFAULT 'conveyor',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (from_resource_id) REFERENCES resources(id) ON DELETE CASCADE,
    FOREIGN KEY (to_resource_id) REFERENCES resources(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Cost allocation data
CREATE TABLE cost_allocation (
    id INT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(100) NOT NULL UNIQUE,
    resource_id INT DEFAULT NULL,
    cost_category ENUM('labor','material','equipment','indirect','other') NOT NULL,
    cost_type ENUM('fixed','variable') NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'EUR',
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- =============================================================================
-- MES OPERATIONAL DATA TABLES (Dynamic / Real-time)
-- =============================================================================

-- Current resource status (live from MES)
CREATE TABLE resource_status (
    id INT AUTO_INCREMENT PRIMARY KEY,
    resource_id INT NOT NULL UNIQUE,
    status ENUM('busy','idle','broken','underMaintenance','unknown','setup','paused','charging') NOT NULL DEFAULT 'idle',
    current_setup VARCHAR(100) DEFAULT NULL,
    current_job_id INT DEFAULT NULL,
    uptime_seconds INT DEFAULT 0,
    parts_processed_today INT DEFAULT 0,
    last_status_change TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Jobs (work orders in execution — MES tracked)
CREATE TABLE jobs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(100) NOT NULL UNIQUE,
    order_line_id INT DEFAULT NULL,
    process_plan_id INT DEFAULT NULL,
    status ENUM('released','started','unknown','completed','cancelled','blocked') NOT NULL DEFAULT 'released',
    priority VARCHAR(50) DEFAULT NULL,
    release_date DATETIME DEFAULT NULL,
    start_time DATETIME DEFAULT NULL,
    end_time DATETIME DEFAULT NULL,
    due_date DATETIME DEFAULT NULL,
    current_process_id INT DEFAULT NULL COMMENT 'Current process step being executed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (order_line_id) REFERENCES order_lines(id) ON DELETE SET NULL,
    FOREIGN KEY (process_plan_id) REFERENCES process_plans(id) ON DELETE SET NULL,
    FOREIGN KEY (current_process_id) REFERENCES processes(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- Job precedence constraints
CREATE TABLE job_constraints (
    id INT AUTO_INCREMENT PRIMARY KEY,
    predecessor_job_id INT NOT NULL,
    successor_job_id INT NOT NULL,
    relationship ENUM('SS','SF','FS','FF') NOT NULL DEFAULT 'FS',
    time_lag_seconds INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (predecessor_job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    FOREIGN KEY (successor_job_id) REFERENCES jobs(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Job effort (planned vs actual)
CREATE TABLE job_effort (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_id INT NOT NULL,
    effort_type ENUM('planned','actual') NOT NULL DEFAULT 'planned',
    processing_time_seconds INT DEFAULT NULL,
    setup_time_seconds INT DEFAULT NULL,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parts_produced INT DEFAULT 0,
    parts_scrapped INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Inventory (current stock levels — MES)
CREATE TABLE inventory (
    id INT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(100) NOT NULL UNIQUE,
    part_type_id INT NOT NULL,
    quantity DECIMAL(12,3) NOT NULL DEFAULT 0.000,
    min_threshold DECIMAL(12,3) DEFAULT NULL,
    max_threshold DECIMAL(12,3) DEFAULT NULL,
    location_id INT DEFAULT NULL COMMENT 'Which buffer/resource holds this',
    lot_number VARCHAR(50) DEFAULT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (part_type_id) REFERENCES part_types(id) ON DELETE CASCADE,
    FOREIGN KEY (location_id) REFERENCES resources(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- Incidents / Failures
CREATE TABLE incidents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(100) NOT NULL UNIQUE,
    resource_id INT NOT NULL,
    incident_type VARCHAR(100) NOT NULL COMMENT 'toolBreakage, motorFailure, electricalFault, etc.',
    severity ENUM('low','medium','high','critical') DEFAULT 'medium',
    status ENUM('open','acknowledged','inProgress','resolved') DEFAULT 'open',
    start_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_time DATETIME DEFAULT NULL,
    description TEXT,
    resolution_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Maintenance Plans
CREATE TABLE maintenance_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(100) NOT NULL UNIQUE,
    resource_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    interval_seconds INT DEFAULT NULL COMMENT 'Time-based interval',
    interval_cycles INT DEFAULT NULL COMMENT 'Cycle-based interval',
    duration_seconds INT DEFAULT NULL COMMENT 'Expected maintenance duration',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =============================================================================
-- CHANGE LOG (for CMSD Twin Service diff tracking)
-- =============================================================================

CREATE TABLE change_events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL COMMENT 'resource, order, job, part, etc.',
    entity_identifier VARCHAR(100) NOT NULL,
    entity_name VARCHAR(255) DEFAULT NULL,
    field_name VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    event_type ENUM('created','updated','deleted') NOT NULL DEFAULT 'updated',
    -- Timestamp of the change detection, not the actual event
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    poll_cycle_id VARCHAR(50) DEFAULT NULL COMMENT 'Groups changes from same poll cycle',
    acknowledged TINYINT(1) DEFAULT 0,
    INDEX idx_entity (entity_type, entity_identifier),
    INDEX idx_detected (detected_at),
    INDEX idx_poll_cycle (poll_cycle_id)
) ENGINE=InnoDB;

-- Poll cycle tracking
CREATE TABLE poll_cycles (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    cycle_id VARCHAR(50) NOT NULL UNIQUE,
    start_time TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    end_time TIMESTAMP(3) NULL DEFAULT NULL,
    sap_api_calls INT DEFAULT 0,
    mes_api_calls INT DEFAULT 0,
    changes_detected INT DEFAULT 0,
    status ENUM('running','completed','failed') DEFAULT 'running',
    error_message TEXT DEFAULT NULL,
    INDEX idx_start_time (start_time)
) ENGINE=InnoDB;

-- =============================================================================
-- SKILL DEFINITIONS (for worker qualification management)
-- =============================================================================

CREATE TABLE skill_definitions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE employee_skills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    resource_id INT NOT NULL COMMENT 'The employee resource',
    skill_id INT NOT NULL,
    proficiency_level ENUM('basic','intermediate','advanced','expert') DEFAULT 'intermediate',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skill_definitions(id) ON DELETE CASCADE,
    UNIQUE KEY unique_employee_skill (resource_id, skill_id)
) ENGINE=InnoDB;