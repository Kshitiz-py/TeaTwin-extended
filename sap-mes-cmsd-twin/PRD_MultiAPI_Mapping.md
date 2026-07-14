# PRD: Multiple APIs per CMSD Entity — Mapping Tool v2

**Status:** Aligned & Approved
**Date:** 2026-05-26
**Interviews:** 19 design-tree questions resolved

---

## 1. Executive Summary

### Problem
Currently one API endpoint per CMSD data point. A CMSD entity like "Resource" needs data from multiple APIs (e.g., `/resources` for static data + `/resource-status` for live availability + `/incidents` for MTTR/MTBF). Users must manually stitch mappings across endpoints with no tool support.

### Solution
A two-phase mapping tool: **(1) Fetch & Approve** — users add multiple API endpoints, fire them individually or all at once, inspect formatted JSON payloads inline, and approve which ones to use. **(2) Map & Save** — RAG-powered LLM proposes field-to-field mappings with instantiation instructions, users navigate entities one at a time with arrow buttons, manually edit fields, apply preset transformations, then save the config for live deployment.

---

## 2. Current State vs Future State

### Current State (What Exists)

| Component | Status |
|-----------|--------|
| RAG vector store (ChromaDB, 4 collections) | Done |
| `mapping_engine.py` — LLM mapping proposal | Done |
| `routes.py` — multi-endpoint `analyze_mapping` | Done (single combined call) |
| Multi-endpoint fetch loop | Done |
| Mapping queue (confirm → batch → generate code) | Done |
| Code-gen pipeline (Writer → Reviewer → Tester → Git) | Done |
| `.agent-mappings/` JSON file persistence | Done (queue only) |
| `api_explorer.py` — fetch + analyze payload | Done |
| `root_array_path` in mapping response | Done (basic) |
| `type_conversion` field (free-text) | Done |

### Future State (What Changes)

| Feature | Priority |
|---------|----------|
| Split `analyze_mapping` into `fetch` + `map` endpoints | P0 |
| Dynamic endpoint list UI (add/remove rows) | P0 |
| Inline expanded JSON viewer (syntax-highlighted, collapsible) | P0 |
| Per-endpoint fire + fire-all buttons | P0 |
| Per-endpoint approval checkboxes | P0 |
| Entity dropdown selector + arrow navigation | P0 |
| Mapping table + entity preview (side by side) | P0 |
| Dot-notation field paths in mapping schema | P0 |
| Transformation preset catalog (8 presets) | P0 |
| `instances` block in mapping response | P0 |
| Configuration CRUD lifecycle (New/Load/Save/Save As/Download/Publish) | P1 |
| `./shared/mapping_configs/` persistent JSON storage | P1 |
| CMSD twin reload endpoint (`POST /api/cmsd/v1/mapping-configs/reload`) | P1 |

---

## 3. System Architecture

### Service Ownership

```
┌──────────────────────┐     reads configs     ┌──────────────────────┐
│   cmsd-twin-service  │◄──────────────────────│     ai-agent         │
│   (live factory)     │                        │   (mapping tool)     │
│                      │─── reload endpoint ───►│                      │
│  Port: 8000          │                        │  Port: 8003          │
└──────────────────────┘                        └──────────────────────┘
         │                                                │
         │  ./shared/mapping_configs/                     │
         │  (bind-mounted to both services)               │
         └────────────────────┬───────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  web-dashboard     │
                    │  (React + TS)      │
                    │  Port: 5173        │
                    └────────────────────┘
```

- **Mapping tool (ai-agent)** owns the config store — it's the single source of truth
- **CMSD twin service** reads configs from shared directory; reloaded via API notify
- **Frontend** manages all intermediate state (fetched payloads) — backend is stateless
- **Config files** live in `./shared/mapping_configs/` (already bind-mounted to both services)

### Docker Volume Strategy

No new volumes needed. The existing `./shared` bind mount already serves both services:
- `ai-agent`: `./shared:/app/git-repo/shared` (line 91, writable)
- `cmsd-twin-service`: `./shared:/app/sap-mes-cmsd-twin/shared` (line 139, reload)

Config files: `./shared/mapping_configs/{config_name}.json`

---

## 4. Backend API Design

### 4.1 Split Endpoints

**OLD (to be removed):**
```
POST /api/agent/v1/mapping/analyze
  Body: { source_id, data_point_name, cmsd_entity, api_endpoint, endpoints[], method }
  → Fetches payloads + runs mapping in one call
```

**NEW:**

#### Phase 1: Fetch Only
```
POST /api/agent/v1/mapping/fetch
  Body: {
    endpoints: [
      { source_id: "sap", endpoint: "/resources", method: "GET", label: "SAP Resources" },
      { source_id: "mes", endpoint: "/resource-status", method: "GET", label: "MES Status" }
    ]
  }
  
  Response: {
    success: true,
    payloads: [
      {
        endpoint: "/resources",
        source_id: "sap",
        label: "SAP Resources",
        url: "http://mock-sap-api:8001/api/sap/v1/resources",
        status: "success",
        status_code: 200,
        size_bytes: 4521,
        raw_payload: { ... }
      },
      {
        endpoint: "/resource-status",
        source_id: "mes",
        label: "MES Status",
        url: "http://mock-mes-api:8002/api/mes/v1/resource-status",
        status: "error",
        status_code: 500,
        error_message: "Internal Server Error",
        raw_payload: null
      }
    ]
  }
```

**Key behaviors:**
- Fires all endpoints concurrently (`asyncio.gather`)
- **Partial success:** each payload has its own `status: "success" | "error"`
- No mapping happens — raw payloads only
- `_truncate_payload` applies (5000 byte limit for display)
- State lives entirely in frontend after this call

#### Phase 2: Map Only
```
POST /api/agent/v1/mapping/analyze
  Body: {
    data_point_name: "Factory Resources",
    cmsd_entity: "Resource",
    approved_payloads: [
      {
        endpoint: "/resources",
        source_id: "sap",
        label: "SAP Resources",
        raw_payload: { ... }
      },
      {
        endpoint: "/resource-status",
        source_id: "mes",
        label: "MES Status",
        raw_payload: { ... }
      }
    ]
  }
  
  Response: {
    success: true,
    cmsd_entity: "Resource",
    mapping: {
      "identifier": {
        api_path: "resource_id",
        source_endpoint: "/resources",
        type_conversion: "none",
        raw_value: "R001",
        converted_value: "R001",
        confidence: "high"
      },
      "name": {
        api_path: "resource_name",
        source_endpoint: "/resources",
        type_conversion: "none",
        raw_value: "CNC Machine 1",
        converted_value: "CNC Machine 1",
        confidence: "high"
      },
      "availability": {
        api_path: "uptime_percent",
        source_endpoint: "/resource-status",
        type_conversion: "divide_by",
        raw_value: 95.5,
        converted_value: 0.955,
        confidence: "medium",
        transformation: {
          type: "divide_by",
          params: { divisor: 100 }
        }
      },
      "mttr": {
        api_path: "mean_time_to_repair_seconds",
        source_endpoint: "/incidents",
        type_conversion: "unit_conversion",
        raw_value: 3600,
        converted_value: 60,
        confidence: "medium",
        transformation: {
          type: "unit_conversion",
          params: { from: "seconds", to: "minutes", factor: 0.0166667 }
        }
      }
    },
    instances: {
      count_path: "$.machines[*]",
      count: 5,
      key_field: "resource_id"
    },
    unmapped_fields: ["mtbf", "mcbf", "reliability"],
    requires_manual_review: true,
    rag_context: "/* retrieved RAG chunks */"
  }
```

**Key behaviors:**
- Backend does NOT fetch APIs — it receives pre-approved payloads
- RAG retrieval runs against 4 collections (data-requirements, cmsd-schema, codebase, api-docs)
- LLM proposes mapping with confidence scores
- `instances` block tells orchestrator how many entities to create
- `unmapped_fields` flags CMSD fields with no API match

### 4.2 Mapping Edits (Existing — Unchanged)
```
POST /api/agent/v1/mapping/edit
  Body: { current_mapping: {...}, edits: {...} }
  → Applies manual user edits, sets confidence to "manual"
```

### 4.3 Smart Reanalyze (Existing — Unchanged)
```
POST /api/agent/v1/mapping/smart-reanalyze
  Body: { data_point_name, cmsd_entity, current_mapping, user_guidance, endpoints[] }
  → Refines mapping based on user chat guidance
```

### 4.4 Configuration CRUD (NEW)

```
GET    /api/agent/v1/configs                    → List all saved configs
POST   /api/agent/v1/configs                    → Create new config (save)
GET    /api/agent/v1/configs/{name}             → Load a config
PUT    /api/agent/v1/configs/{name}             → Update existing config
DELETE /api/agent/v1/configs/{name}             → Delete a config
POST   /api/agent/v1/configs/{name}/publish     → Publish to CMSD service
GET    /api/agent/v1/configs/cmsd/active         → Download active config from CMSD service
```

**Storage:** `./shared/mapping_configs/{name}.json`

**Publish flow:**
1. Save config JSON to `./shared/mapping_configs/`
2. `POST http://cmsd-twin-service:8000/api/cmsd/v1/mapping-configs/reload`
3. CMSD service re-reads the config directory and activates changes

### 4.5 CMSD Twin Service — New Reload Endpoint
```
POST /api/cmsd/v1/mapping-configs/reload
  → Re-reads ./shared/mapping_configs/ directory
  → Validates configs against CMSD Pydantic schema
  → Activates configs for next poll cycle
  
  Response: {
    success: true,
    configs_loaded: ["resource_mapping", "job_mapping"],
    errors: []
  }
```

### 4.6 Backend State: Stateless

All intermediate state (fetched payloads, edited mappings before save) lives in the **frontend only**. The backend never holds session state between fetch and map calls. Each `/mapping/analyze` request is self-contained.

---

## 5. Frontend UI Design

### 5.1 Overall Layout (Two-Phase Flow)

```
┌─────────────────────────────────────────────────────┐
│  PHASE 1: Fetch & Approve                            │
│                                                       │
│  ┌──────────────────────────────────────────────┐    │
│  │ [+ Add Endpoint]                              │    │
│  │                                               │    │
│  │ ┌─ Row 1 ───────────────────────────────┐    │    │
│  │ │ [Source ▼] [Endpoint /resources    ]  │    │    │
│  │ │ [Method GET ▼] [Label: SAP Resources] │    │    │
│  │ │ [▶ Fire]  [☐ Approve]  [✕ Remove]     │    │    │
│  │ │ ┌─ Expanded JSON (when fired) ──────┐ │    │    │
│  │ │ │ { "machines": [...] }             │ │    │    │
│  │ │ │ ▲ collapsible, syntax-highlighted │ │    │    │
│  │ │ └────────────────────────────────────┘ │    │    │
│  │ └────────────────────────────────────────┘    │    │
│  │                                               │    │
│  │ ┌─ Row 2 ───────────────────────────────┐    │    │
│  │ │ [Source ▼] [Endpoint /res-status   ]  │    │    │
│  │ │ [▶ Fire]  [☐ Approve]  [✕ Remove]     │    │    │
│  │ │ ┌─ Error state ─────────────────────┐ │    │    │
│  │ │ │ ⚠ 500 Internal Server Error       │ │    │    │
│  │ │ │ [🔄 Retry]                        │ │    │    │
│  │ │ └────────────────────────────────────┘ │    │    │
│  │ └────────────────────────────────────────┘    │    │
│  │                                               │    │
│  │ [🔥 Fire All]                                 │    │
│  │                                               │    │
│  └──────────────────────────────────────────────┘    │
│                                                       │
│  ───────────── [✅ Approve Selected & Map] ─────────  │
│                                                       │
├─────────────────────────────────────────────────────┤
│  PHASE 2: Map & Edit                                 │
│                                                       │
│  ┌─ Entity: [Resource ▼]  ◄ ► (arrow navigation) ─┐  │
│  │                                                  │  │
│  │ ┌─ Mapping Table ───────────────────────────┐   │  │
│  │ │ CMSD Field    │ API Path      │ Transform  │   │  │
│  │ │ identifier    │ resource_id   │ none       │   │  │
│  │ │ availability  │ uptime_pct    │ ÷100    ✎  │   │  │
│  │ │ mttr          │ mttr_seconds  │ s→min   ✎  │   │  │
│  │ └────────────────────────────────────────────┘   │  │
│  │                                                  │  │
│  │ ┌─ Entity Preview ──────────────────────────┐   │  │
│  │ │ {                                           │   │  │
│  │ │   "identifier": "R001",    // ← /resources  │   │  │
│  │ │   "availability": 0.955,   // ← /res-status │   │  │
│  │ │   "mttr": {                // ← /incidents  │   │  │
│  │ │     "value": 60,                            │   │  │
│  │ │     "unit": "minutes"                       │   │  │
│  │ │   }                                         │   │  │
│  │ │ }                                           │   │  │
│  │ └─────────────────────────────────────────────┘   │  │
│  │                                                  │  │
│  │ Instances: 5 machines from $.machines[*]         │  │
│  └──────────────────────────────────────────────────┘  │
│                                                       │
│  ─ [Save] [Save As] [Download from CMSD] [Publish] ─  │
└─────────────────────────────────────────────────────┘
```

### 5.2 UI Component Tree (New Components)

```
MappingWizard (new page/route)
├── Phase1Fetch
│   ├── EndpointList
│   │   └── EndpointRow[]           (dynamic, add/remove)
│   │       ├── SourceSelector      (dropdown, existing sources)
│   │       ├── EndpointInput       (text input)
│   │       ├── MethodSelector      (GET/POST dropdown)
│   │       ├── LabelInput          (optional friendly name)
│   │       ├── FireButton          (individual fire)
│   │       ├── ApproveCheckbox     (☐ per endpoint)
│   │       ├── RemoveButton        (✕)
│   │       └── PayloadViewer       (inline expanded)
│   │           ├── SuccessState    (syntax-highlighted JSON, collapsible)
│   │           └── ErrorState      (error message + retry button)
│   ├── AddEndpointButton           (+)
│   ├── FireAllButton               (global)
│   └── ApproveAndMapButton         (bridge to Phase 2)
│
├── Phase2Mapping
│   ├── EntitySelector              (dropdown, 25 CMSD entities)
│   ├── EntityNavArrows             (◄ ►)
│   ├── MappingTable
│   │   └── MappingRow[]
│   │       ├── CmsdFieldName       (read-only label)
│   │       ├── ApiPathInput        (editable)
│   │       ├── SourceEndpointBadge (colored badge)
│   │       ├── TransformSelector   (dropdown, 8 presets)
│   │       ├── TransformParams     (dynamic params per preset)
│   │       ├── RawValueDisplay     
│   │       ├── ConvertedValueDisplay
│   │       └── ConfidenceBadge     (high/medium/low/manual)
│   ├── EntityPreview               (live JSON with source annotations)
│   ├── InstancesInfo               (count + key field display)
│   └── ConfigToolbar
│       ├── NewButton
│       ├── LoadButton
│       ├── SaveButton
│       ├── SaveAsButton
│       ├── DownloadFromCmsdButton
│       └── PublishButton
│
└── ConfigListModal                  (for Load / Save As)
    ├── ConfigListTable
    └── SearchFilter
```

### 5.3 UI State Machine

```
[Initial] → Phase 1 (Fetch)
  │  User adds endpoints, fires them
  │  Some succeed, some may fail (partial success)
  │  User checks ☐ approved boxes
  │
  ▼
[Approve & Map] → Phase 2 (Mapping)
  │  Frontend sends approved_payloads to /mapping/analyze
  │  RAG + LLM returns proposed mapping
  │  User navigates entities with ◄ ►
  │  User edits fields, adds transformations
  │
  ▼
[Save / Publish]
  │  Save → POST /configs → writes to shared/mapping_configs/
  │  Publish → POST /configs/{name}/publish → notifies CMSD service
  │
  ▼
[Done] → User can Load config later, Download from CMSD, or start New
```

---

## 6. Configuration File Schema

### 6.1 File Location
```
./shared/mapping_configs/{config_name}.json
```

### 6.2 Schema

```json
{
  "$schema": "https://cmsd-twin.local/schemas/mapping-config-v1.json",
  "name": "factory_resource_mapping",
  "version": 1,
  "created_at": "2026-05-26T10:00:00Z",
  "updated_at": "2026-05-26T12:00:00Z",
  "entities": {
    "Resource": {
      "endpoints": [
        {
          "url": "/resources",
          "source_id": "sap",
          "label": "SAP Resources",
          "method": "GET",
          "status": "active",
          "fields": {
            "identifier": {
              "api_path": "resource_id",
              "transformation": null
            },
            "name": {
              "api_path": "resource_name",
              "transformation": null
            },
            "resource_type": {
              "api_path": "type",
              "transformation": {
                "type": "enum_map",
                "params": {
                  "mapping": {
                    "MACHINE": "machine",
                    "EMPLOYEE": "employee"
                  }
                }
              }
            },
            "size.width": {
              "api_path": "dimensions.width_mm",
              "transformation": {
                "type": "unit_conversion",
                "params": {
                  "from": "millimeter",
                  "to": "meter",
                  "factor": 0.001
                }
              }
            },
            "availability": {
              "api_path": "uptime_percent",
              "transformation": {
                "type": "divide_by",
                "params": { "divisor": 100 }
              }
            }
          },
          "instances": {
            "count_path": "$.machines[*]",
            "key_field": "resource_id"
          }
        },
        {
          "url": "/resource-status",
          "source_id": "mes",
          "label": "MES Resource Status",
          "method": "GET",
          "status": "active",
          "fields": {
            "current_status": {
              "api_path": "state",
              "transformation": {
                "type": "enum_map",
                "params": {
                  "mapping": {
                    "ACTIVE": "busy",
                    "IDLE": "idle",
                    "DOWN": "broken"
                  }
                }
              }
            },
            "mttr.value": {
              "api_path": "mean_time_to_repair_seconds",
              "transformation": {
                "type": "unit_conversion",
                "params": {
                  "from": "seconds",
                  "to": "minutes",
                  "factor": 0.0166667
                }
              }
            },
            "mttr.unit": {
              "api_path": null,
              "transformation": {
                "type": "default_value",
                "params": { "value": "minute" }
              }
            }
          }
        }
      ]
    },
    "Job": {
      "endpoints": [
        {
          "url": "/orders",
          "source_id": "sap",
          "label": "SAP Orders",
          "method": "GET",
          "status": "active",
          "fields": {
            "identifier": {
              "api_path": "order_id",
              "transformation": null
            },
            "status": {
              "api_path": "order_status",
              "transformation": {
                "type": "enum_map",
                "params": {
                  "mapping": {
                    "RELEASED": "released",
                    "IN_PROGRESS": "started"
                  }
                }
              }
            }
          },
          "instances": {
            "count_path": "$.orders[*]",
            "key_field": "order_id"
          }
        }
      ]
    }
  }
}
```

### 6.3 Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| `entities: { "Resource": {...}, "Job": {...} }` | One config covers multiple CMSD entities from shared endpoints |
| Dot-notation paths (`"size.width"`, `"mttr.unit"`) | Handles nested CMSD structures without mirroring full Pydantic tree |
| `transformation: null` = passthrough | Clean distinction from "no transformation" |
| Per-endpoint `status: "active" | "inactive"` | Disable without deleting |
| Version field | Future schema migrations |
| `instances` per endpoint | An endpoint may return an array; tells orchestrator how to iterate |

---

## 7. Transformation Presets Catalog (v1)

| # | Preset `type` | Params | Example Use Case |
|---|---------------|--------|------------------|
| 1 | `none` | — | Direct pass-through, no conversion |
| 2 | `unit_conversion` | `from`, `to`, `factor` | mm → meter (×0.001), seconds → minutes (÷60) |
| 3 | `enum_map` | `mapping: {from: to}` | `"ACTIVE"` → `"busy"`, `"DOWN"` → `"broken"` |
| 4 | `to_decimal` | `precision` (optional) | `"42"` → `Decimal("42.00")` |
| 5 | `to_integer` | — | `"42.7"` → `43` |
| 6 | `string_template` | `template` | `"{first_name} {last_name}"` → full name |
| 7 | `divide_by` | `divisor` | uptime_seconds ÷ 3600 → hours; percent ÷ 100 → decimal |
| 8 | `multiply_by` | `factor` | 0.955 × 100 → 95.5 (%) |
| 9 | `default_value` | `value` | Field not in API → `"unknown"`, `0`, or `"minute"` |

**v2 candidates:** `date_parse`, `extract_from_array`, `duration_construct`, `regex_extract`, `conditional`

### Transformation Application Order

When a field has a transformation, the mapping engine applies:
1. Extract `raw_value` from API payload at `api_path`
2. If transformation exists, apply it → `converted_value`
3. Store both for traceability

---

## 8. RAG Integration

### Collections Used
| Collection | Content | Retrieval Query |
|------------|---------|-----------------|
| `data-requirements` | `Data_requirements_for_ASMG.md` | `"{data_point_name} data requirements CMSD mapping"` |
| `cmsd-schema` | CMSD Pydantic model source files | `"CMSD schema definition for {cmsd_entity} class fields"` |
| `codebase` | `cmsd_twin_service/` source code | `"CMSD factory build method mapping {cmsd_entity} _build_{entity}"` |
| `api-docs` | API endpoint implementations | `"API endpoint implementation {endpoint}"` |

### Retrieval Flow
1. `POST /mapping/analyze` receives approved payloads
2. `mapping_engine.analyze_rag()` queries all 4 collections
3. Assembled RAG context (≤4000 chars) is injected into LLM system prompt
4. LLM receives: RAG context + CMSD field list + payload structure → proposes mapping
5. `_validate_mapping()` cross-references against `CMSD_ENTITY_FIELDS`

---

## 9. Instantiation Model

### Response Structure
```json
"instances": {
  "count_path": "$.machines[*]",
  "count": 5,
  "key_field": "resource_id"
}
```

### How It Works
1. LLM analyzes the approved payload and identifies array structures
2. Returns `count_path` (JSONPath to the array) and `key_field` (unique identifier within each array item)
3. The orchestrator uses this to know:
   - How many CMSD entities to create (5 Resources)
   - Which field uniquely identifies each instance
   - Where to iterate in the payload
4. The UI displays: "Instances: 5 machines from `$.machines[*]`" so the user can verify before approving

### Multi-Endpoint Scenarios
When two endpoints both contribute to instantiation:
- `/resources` returns `{machines: [{id: "R001", ...}, {id: "R002", ...}]}` (5 items)
- `/resource-status` returns `{statuses: [{resource_id: "R001", ...}, ...]}` (5 items)

The LLM identifies the join key (`resource_id`) and includes it in the mapping notes. The orchestrator matches by key during entity construction.

---

## 10. Error Handling

### Fetch Phase (Partial Success)
| Scenario | Behavior |
|----------|----------|
| All succeed | All `status: "success"`, all payloads shown |
| Some fail | Mixed `status: "success"` / `"error"`, checkboxes only enabled for successes |
| All fail | All `status: "error"`, user must fix endpoints to proceed |
| Timeout (>30s) | Per-endpoint timeout, returns `status: "error"` with timeout message |

### Map Phase
| Scenario | Behavior |
|----------|----------|
| LLM unavailable | Return `requires_manual_review: true` with empty mapping |
| RAG returns no results | Proceed with mapping using only payload structure (lower confidence) |
| Payload too large | Truncated to 5000 bytes for display; full payload still used for mapping |
| Invalid entity name | 400 Bad Request with list of valid entity names |

### Publish Phase
| Scenario | Behavior |
|----------|----------|
| CMSD service unreachable | Config saved to disk; user can retry publish later |
| Config validation fails | 400 with specific validation errors from CMSD Pydantic schema |
| Config already active | 200 — idempotent reload |

---

## 11. Implementation Phases

### Phase 1 — Core Split (P0)
**Backend:**
- [ ] Create `POST /mapping/fetch` endpoint (concurrent fetch, partial success)
- [ ] Refactor `POST /mapping/analyze` to accept `approved_payloads` instead of fetching
- [ ] Add dot-notation support to `_validate_mapping`
- [ ] Add transformation preset validation
- [ ] Add `instances` block to LLM system prompt and response parsing

**Frontend:**
- [ ] Create `MappingWizard` page with phase state machine
- [ ] Build `EndpointList` + `EndpointRow` with Fire/FireAll
- [ ] Build `PayloadViewer` (syntax-highlighted, collapsible JSON)
- [ ] Wire up fetch → approve → map flow

### Phase 2 — Config Lifecycle (P1)
**Backend:**
- [ ] Create `./shared/mapping_configs/` directory
- [ ] Implement Config CRUD endpoints in ai-agent routes
- [ ] Add `POST /api/cmsd/v1/mapping-configs/reload` to CMSD twin service
- [ ] Implement Publish endpoint (save + notify CMSD service)

**Frontend:**
- [ ] Build `ConfigToolbar` (New/Load/Save/Save As/Download/Publish)
- [ ] Build `ConfigListModal` for Load/Save As
- [ ] Build entity navigation arrows

### Phase 3 — Polish (P2)
- [ ] Collapsible nodes in JSON viewer (DevTools-style)
- [ ] Transformation preview (show raw → converted inline)
- [ ] Undo/redo for mapping edits
- [ ] Diff view when loading a config vs current state

---

## 12. Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `ai_agent/routes.py` | **Modify** | Split `analyze_mapping` → add `fetch` endpoint, refactor `analyze`, add Config CRUD |
| `ai_agent/mapping_engine.py` | **Modify** | Dot-notation paths, transformation presets, `instances` block, enhanced LLM prompts |
| `ai_agent/api_explorer.py` | **Modify** | Concurrent fetch support (`asyncio.gather`), per-endpoint error handling |
| `cmsd_twin_service/routes.py` | **Modify** | Add `POST /mapping-configs/reload` endpoint |
| `shared/` | **New dir** | `mapping_configs/` subdirectory for JSON config files |
| `web_dashboard/src/` | **New/Modify** | `MappingWizard` page, `EndpointRow`, `PayloadViewer`, `MappingTable`, `EntityPreview`, `ConfigToolbar` components |
| `shared/config.py` | **Modify** | Add `MAPPING_CONFIGS_DIR` path constant |

---

## 13. Non-Goals (Explicitly Out of Scope for v1)

- Full custom expression language for transformations
- Real-time collaboration (multiple users editing same mapping)
- Mapping version history / diff (beyond the version field)
- Automatic polling/refresh of API payloads
- WebSocket streaming of mapping analysis
- Configuration export to formats other than JSON
- Role-based access control for publish
