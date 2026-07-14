# Data Requirements for Automated Simulation Model Generation (ASMG)

This specification outlines the exhaustive data necessary to generate a "high-fidelity" Digital Twin. The requirements are systematically categorized into **Technical**, **Organizational**, and **System Load** data to align with the **Layout Generation $\rightarrow$ Parameterization $\rightarrow$ Execution** workflow identified in the system architecture.

![Data Requirements Overview](resources/data-requirements.png)

---

## 1. Technical Data (Factory Structure & Layout)
**Phase:** Layout Generation  
**Source:** SAP Master Data + CAD/Layout File  
**Description:** This data defines the static physical "Topology of Plants" and allows the Python interpreter to instantiate and place objects in the correct spatial relationship.

*   **Object Class Mapping**
    *   **Description:** A mapping table linking SAP Work Center types to Plant Simulation classes.
    *   *Example:* "MillingMachine" $\rightarrow$ `.MaterialFlow.SingleProc`.
*   **Object Identifier**
    *   **Description:** Unique ID (e.g., Work Center ID) to name instances programmatically.
*   **Geometric Coordinates (X, Y, Z)**
    *   **X, Y Position:** Required for the command `createObject(target, x, y)` to prevent object stacking. *Note: Usually missing in SAP; requires CAD/Layout merging*.
    *   **Rotation/Orientation:** Angle of the machine (0, 90, 180 degrees) for correct visualization and conveyor connections.
    *   **Dimension/Scaling:** Length/width of objects to ensure they fit within layout boundaries.
*   **Path/Connection Logic**
    *   **Predecessor/Successor IDs:** Required to execute the `.connect(obj1, obj2)` command.
    *   **Connection Type:** Specification of the link type (e.g., "Conveyor", "Footpath", or "Logical Connector").

---

## 2. Technical Data (Operational Resources & Incidents)
**Phase:** Parameterization  
**Source:** SAP Equipment Records & Maintenance Logs  
**Description:** This covers "Manufacturing Data," "Material Flow Data," and "Incident Data," defining the capabilities, capacities, and constraints of the machinery.

*   **Processing Parameters**
    *   **Processing Time:** (Constant or Distribution) Time per part. Maps to `.ProcTime`.
    *   **Setup Time:** Time required to change between part types. Maps to `.SetupTime`.
    *   **Recovery Time:** Time required after processing before the machine is ready again. Maps to `.RecoveryTime`.
*   **Reliability & Incident Data**
    *   **Availability:** Operational percentage (e.g., 95%). Maps to `.Availability`.
    *   **MTTR (Mean Time To Repair):** Average duration of a "Functional Fault".
    *   **Failure Profile:** Type of failure (e.g., "Tool Breakage" vs. "Motor Failure") to assign specific repair resources.
*   **Capacity Constraints (Material Flow)**
    *   **Buffer Size:** Number of slots in a buffer or store. Maps to `.Capacity`.
    *   **Conveyor Attributes:** Speed (`.Speed`), Length (`.Length`), and accumulating behavior (`.Accumulating`).
    *   **Parallel Processing:** Number of parallel stations (e.g., `.xDim` in ParallelProc).

---

## 3. Organizational Data (Workflow & Resources)
**Phase:** Parameterization  
**Source:** SAP HR/Shift Planning  
**Description:** This encompasses "Working Time Organization" and "Workflow Organization," dictating how the system manages resources, shifts, and decision-making rules.

*   **Workforce Management**
    *   **Shift Models:** Exact start/end times, Break Time Regulations, and Holiday calendars. Maps to `ShiftCalendar`.
    *   **Service Requirements:** Definitions of which machine requires a worker for "Setup," "Processing," or "Repair".
    *   **Worker Pool:** Number of available operators and their efficiency/walking speeds.
*   **Workflow Strategies**
    *   **Dispatching Rules:** Logic for prioritizing tasks at a machine (e.g., FIFO, Earliest Due Date, Shortest Processing Time).
    *   **Incident Management Policies:** Logic defining how the system reacts to faults (e.g., "Scrap part", "Rework", or "Wait for Repair").
*   **Energy Data** (Industry 5.0)
    *   **Power Consumption:** Wattage used in different states (Working, Standby, Failed, Off).

---

## 4. System Load Data (The Input)
**Phase:** Execution  
**Source:** SAP Transactional Data (Orders) & Material Master  
**Description:** This is the variable input that drives the simulation run. It is distinct from the static factory data and dictates *what* is produced and *when*.

### A. Order Loading (Transactional)
*Defines the schedule and volume.*
*   **Production Orders:** Specific instructions to produce a quantity of material.
    *   *Usage:* Populates the **DeliveryTable** of the `Source` object.
    *   *Attributes:* Order ID, Target Quantity, Start Date.
*   **Deadlines:** The "Due Date" attached to an order.
    *   *Usage:* Used to sort the production sequence (Priority).
*   **Transport Orders:** Instructions for moving materials between locations.
    *   *Usage:* Drives AGV/Transporter logic.

### B. Product Data (Master)
*Defines the "recipe" and physical properties.*
*   **Work Plans (Routings):** The sequence of operations specific to a material number.
*   **Bill of Materials (BOM):** Hierarchical list of component parts required to build the product.
    *   *Usage:* Critical for **AssemblyStation** logic (defines predecessor MUs).
*   **Product Definition (MUs):**
    *   **Physical Dimensions:** Length/Width/Height of the part. Critical for calculating dynamic buffer capacities.
    *   **Visual Attributes:** Color or 3D shape for identification during simulation.

---

## 5. Experiment Data
definition of KPI and input parameters to be varied
**Phase:** Execution  
**Source:** User Configuration  
**Description:** This data configures the simulation experiment itself, ensuring the model runs within the correct temporal context.

*   **Simulation Horizon**
    *   **Start Date/Time:** The virtual calendar date when the simulation begins (must align with SAP Production Plan start).
    *   **Simulation Duration:** The total time to simulate (e.g., "8 Hours," "5 Days," or "Until all orders finished").
    *   **Warm-up Period:** Time to run the model to reach a steady state before recording statistics.
*   **Statistical Configuration**
    *   **Replications:** Number of times to run the simulation (required if using stochastic distributions for failures).
    *   **Random Seed:** Configuration to ensure reproducibility of results.
