# ISM 2026 — Content Briefing

**Title:** Configuration, Not Code: LLM-Driven Assembly of Digital Twins from Enterprise Data
**Target Venue:** 8th International Conference on Industry of the Future and Smart Manufacturing (ISM 2026)
**Invited Tracks:** Reshaping future smart manufacturing: convergence of Industrial Metaverse, Cyber-Physical Systems, and Digital Twins; Generative AI and manufacturing of the future
**Length:** 8 pages maximum

---

## Core Narrative

Manufacturing companies sit on decades of enterprise data locked in SAP and MES systems. Building digital twins from this data today follows a well-worn path: a consultant manually maps each API field to a target schema, hardcodes the mapping per customer, and rebuilds for every new factory. This makes digital twin adoption prohibitively expensive for SMEs — the very companies who stand to gain the most.

**We present a different approach.** An LLM reads raw enterprise API payloads, understands CMSD entity schemas through a curated field catalog, and proposes field-level mappings as JSON configuration. A human reviews only the proposals the model itself flags as uncertain. A deterministic engine consumes the config and assembles the digital twin at runtime — no code generation, no per-customer Python factories, no CMSD expertise required on site.

The architecture connects three converging domains: enterprise IT systems (SAP/MES), a semantic mapping layer (AI + calibrated human review), and a standards-based digital twin core (CMSD/ISO 22400). New customer = new JSON file. No code changes. No redeployment. This is the convergence the Industrial Metaverse track calls for: software architecture that makes AI-enabled digital twins accessible beyond the enterprise elite.

**Experimentally (n=5, 4 API variants, 4 CMSD entities), both models achieve 95-96% aggregate mapping accuracy. Three entity types (Order, ResourceClass, PartType) reach 96-100%. Resource (20 fields, 7 numeric) is the sole bottleneck, dropping to 41-50% on legacy cryptic payloads regardless of model or RAG. The root cause is inherent to the data: string values carry identity cues that the LLM exploits; numeric values do not. The CMSD catalog describes the target side — adding source-side payload field descriptions to RAG is the identified path to resolving the legacy numeric bottleneck.**

---

## Focus Points (7 Claims the Paper Defends)

1. **Configuration, Not Code** — JSON config is the single source of truth. A deterministic MappingDrivenFactory reads it and constructs CMSD instances at runtime. Zero-code customization per customer. No LLM in the production path.

2. **Human-in-the-Loop with Calibrated Confidence** — The LLM scores every proposal (high/medium/low). High-confidence proposals are 95%+ correct and safe to auto-accept. Human review targets only flagged fields. Smart reanalysis re-evaluates only what changed.

3. **SME Accessibility as a First-Order Goal** — Connect APIs, review AI proposals, generate twin. No CMSD expertise needed. No embedded software consultant. Industrial-grade digital twin in minutes, not consultant-weeks.

4. **DAG-Driven Multi-Entity Construction** — Cross-entity references detected automatically (Order → PartType, Job → Resource). Topological sort determines correct build order. Pre-flight validation catches missing dependencies and unreachable APIs before generation begins.

5. **Vendor-Neutral Canonical Hub** — CMSD (ISO 22400) at the center. SAP speaks one dialect, MES another. The AI layer translates both into the canonical format. Architecture generalizes: swap CMSD for AML, AAS, or any proprietary schema.

6. **RAG Content Curation — and Its Limits** — Raw source code retrieval degrades accuracy; a clean CMSD field catalog provides reliable target-side context. But the catalog describes CMSD, not the source API payload. For legacy payloads with opaque field codes, the LLM must infer field identity from values alone — which works for strings (values carry identity cues) but not for numerics (95.0 could be anything). The path forward: RAG catalogs should include source-side payload field descriptions to bridge both sides of the mapping.

7. **Living Twin, Not One-Shot Export** — Continuous polling, change detection, WebSocket push. Every entity carries connection metadata (source API, key field, last fetched). Graceful degradation: stale indicators, partial success, hardcoded factory fallback.

---

## Section-by-Section Content Brief

### 1. Introduction (~1 page)

**Opening paragraph — The Problem:**
- Digital twins need structured data conforming to standards like CMSD/ISO 22400
- Enterprise data lives in SAP (master data: resources, BOMs, orders) and MES (operational data: status, jobs, incidents)
- These systems were never designed to interoperate — different field names, structures, languages, and conventions
- The default solution: a consultant hand-writes field mappings per customer in Python
- Result: brittle code, high per-customer cost, slow onboarding, and SME exclusion from digital twin adoption

**Second paragraph — The Opportunity:**
- LLMs can parse both structured API payloads and target schema definitions
- They can propose field-level mappings with self-assessed confidence scores
- This enables a fundamentally different architecture: the LLM proposes mappings as data (JSON), a human reviews only uncertain proposals, and a deterministic engine drives the twin at runtime
- The key insight: mapping is a configuration problem, not a code generation problem

**Third paragraph — Our Contribution:**
- A reference architecture for LLM-driven digital twin assembly from heterogeneous enterprise APIs
- Core innovation: mapping-as-configuration — a JSON file replaces per-customer Python factories. The engine is generic; the config is specific
- Human-in-the-loop with calibrated AI confidence — the model scores its own uncertainty, minimizing review burden
- DAG-driven multi-entity construction with topological ordering and pre-flight validation
- Continuous synchronization for a living digital twin, not a one-time export

**Fourth paragraph — Key Findings Preview:**
- Both models achieve 95-96% aggregate accuracy. For well-structured entities (Order, ResourceClass, PartType), accuracy reaches 96-100%; the Resource entity (20 fields, 7 numeric) is the sole bottleneck, dropping to 41-50% on legacy cryptic payloads regardless of RAG or model choice
- RAG content curation is decisive: raw source code retrieval degrades accuracy; a clean CMSD field catalog (~2,500 chars) provides reliable target-side context. However, the catalog describes only CMSD — for legacy payloads with opaque source identifiers, the LLM must infer field identity from values alone, which works for strings but not for numerics. Source-side payload documentation in RAG would address this gap
- LLMs map string fields more accurately than numeric fields regardless of RAG — string values carry identity cues ("CNC Machine"); numeric values (95.0) carry none. This inherent data asymmetry, not retrieval quality, is the fundamental bottleneck
- The non-reasoning model (Flash, ~15s/entity) matches the reasoning model (Pro, ~45s/entity) in accuracy at 3× lower latency
- The architecture generalizes beyond CMSD — swap the target schema, retrain the catalog, and the same engine applies

---

### 2. Related Work (~0.75 page)

Organize into 5 clusters, 3-4 references each:

**Digital Twin Automation:**
- Automated generation of simulation models from enterprise data sources
- Existing approaches: hardcoded factory classes, rule-based mapping engines, template-driven code generation
- Gap: all require per-customer customization by someone who knows both the source APIs and the target schema

**Schema Mapping and Ontology Alignment:**
- Traditional: rule-based matchers, dictionary-based string similarity, heuristic structural matching
- Recent: LLM-based zero-shot and few-shot schema mapping across database schemas and knowledge graphs
- Our position: LLM + human-in-the-loop with calibrated confidence is the right balance for industrial settings where correctness matters

**RAG in Manufacturing and Industrial Applications:**
- Retrieval-augmented generation applied to maintenance manuals, compliance documents, design specifications
- What's been tried: embedding technical documentation for question answering, retrieving procedures for operator guidance
- Our contribution: systematic analysis of how retrieval content quality affects mapping accuracy — and the finding that curation matters more than retrieval sophistication

**Human-in-the-Loop AI for Data Integration:**
- Interactive machine learning for schema matching and entity resolution
- Confidence-calibrated review systems that minimize human annotation effort
- Our position: calibrated confidence scoring + smart reanalysis (re-evaluate only what changed) minimizes the human bottleneck

**CMSD and ISO 22400 in Practice:**
- Core Manufacturing Simulation Data standard — structure, entities, adoption landscape
- Existing implementations: simulation tool integration, data exchange formats
- Our contribution: the first LLM-driven field mapper targeting CMSD as the canonical hub in a multi-source enterprise integration

**Smart Manufacturing & SME Digitalization:**
- Barriers to digital twin adoption for small and medium manufacturers
- Low-code and no-code approaches to industrial system integration
- Our position: configuration-driven architecture specifically addresses the SME cost and expertise gap

---

### 3. System Architecture (~2 pages) — THE CORE CONTRIBUTION

#### 3.1 Architecture Overview

**Five-service design, single Docker Compose deployment:**

```
┌─────────────────────────────────────────────────────────┐
│                  Web Dashboard (React)                    │
│           Guided Mapping UI + Twin Monitor                │
└──────────────────────┬──────────────────────────────────┘
                       │ REST + WebSocket
┌──────────────────────▼──────────────────────────────────┐
│              AI Agent (FastAPI, Port 8003)                │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ LLM      │  │ RAG Retriever│  │ Mapping Engine    │  │
│  │ Client   │  │ (ChromaDB)   │  │ (propose+validate)│  │
│  └────┬─────┘  └──────┬───────┘  └───────────────────┘  │
│       │               │                                  │
│  DeepSeek API    Ollama Embed (qwen3-embedding:4b)       │
└──────────────────────┬──────────────────────────────────┘
                       │ Shared Volume (mapping JSONs)
┌──────────────────────▼──────────────────────────────────┐
│          CMSD Twin Service (FastAPI, Port 8000)           │
│  ┌────────────┐  ┌──────────┐  ┌────────────────────┐   │
│  │MappingDriven│  │ChangeDet │  │ EventBus → WS Push │   │
│  │Factory     │  │ector     │  │                    │   │
│  └────────────┘  └──────────┘  └────────────────────┘   │
└──────┬───────────────────────────────┬──────────────────┘
       │                               │
┌──────▼──────┐                 ┌──────▼──────┐
│ Mock SAP API│                 │ Mock MES API│
│ (Port 8001) │                 │ (Port 8002) │
└─────────────┘                 └─────────────┘
```

**Each service, briefly:**
- **Mock SAP API** — serves master data (resources, BOMs, orders, part types) with realistic nested JSON
- **Mock MES API** — serves operational data (resource status, job execution, incidents) with different field conventions
- **AI Agent** — orchestrates LLM calls, RAG retrieval, mapping proposal, confidence scoring, and smart reanalysis
- **CMSD Twin Service** — polling, MappingDrivenFactory, change detection, event bus, WebSocket push
- **Web Dashboard** — guided mapping wizard with progressive disclosure: Fetch → Approve → Map → Edit → Generate
- **ChromaDB** — vector store with 2 CMSD knowledge collections (field catalog + ASMG requirements doc)
- **Ollama** — local embedding model (qwen3-embedding:4b, 2,560-dimensional vectors)

**Key architectural decisions:**
- Single Docker Compose — `docker compose up` deploys everything
- Shared volume for mapping configs between AI Agent and CMSD Twin Service
- Provider-agnostic LLM interface (OpenAI, Anthropic, Ollama, DeepSeek — any OpenAI-compatible API)
- Separate chat provider (cloud LLM) and embedding provider (local Ollama) — configured independently
- No LLM in the runtime path — mapping proposal uses LLM; twin generation uses deterministic engine only

#### 3.2 Mapping as Configuration — The Central Idea

**The traditional approach** (brittle, per-customer code):
```python
# Per-customer hardcoded factory — must be rewritten for every new factory
if customer == "AcmeCorp":
    resource.availability = payload["uptime_pct"] / 100
elif customer == "GlobalMfg":
    resource.availability = payload["AVAIL_PCT"] / 100
# ... 300+ lines of conditional field mappings
```

**Our approach** (configuration-driven, zero code changes):
```json
{
  "mapping_id": "map-abc123",
  "cmsd_entity": "Resource",
  "source_endpoints": ["sap:/resources", "mes:/resource-status"],
  "mapping": {
    "availability": {
      "api_path": "uptime_pct",
      "source": "sap:/resources",
      "transformation": {"type": "divide_by", "params": {"divisor": 100}},
      "confidence": "high"
    },
    "current_state": {
      "api_path": "state",
      "source": "mes:/resource-status",
      "transformation": {"type": "enum_map", "params": {"ACTIVE": "busy", "IDLE": "idle"}},
      "confidence": "high"
    }
  },
  "instances": {
    "count_path": "$.machines[*]",
    "key_field": "resource_id"
  }
}
```

**What this enables:**
- JSON config is the single source of truth — human-readable, version-controllable, diffable
- MappingDrivenFactory is entirely generic — reads any valid config, produces CMSD instances
- 9 transformation presets cover 90%+ of real-world conversion needs (unit conversion, enum mapping, division, multiplication, string templates, type casting, defaults)
- No LLM in the runtime path — factory is pure deterministic Python
- New customer = new JSON file = zero code changes = zero redeployment
- Config CRUD lifecycle: New, Save, Load, Publish, Download — all managed through CMSD Twin Service

#### 3.3 The Neutral Format Hub

**The problem:** SAP and MES speak different "dialects":
- SAP: `resource_id`, `resource_name`, `uptime_pct`, `RESOURCE_TYPE`
- MES: `machineId`, `status`, `currentJob`, `MTTR_VALUE`
- Same domain concepts, incompatible naming conventions

**The solution:** CMSD (ISO 22400) as the canonical center:
- Both source systems map to the same target vocabulary
- The AI layer translates each source dialect into CMSD
- The twin only knows CMSD — source heterogeneity is abstracted away

**Why this generalizes:**
- CMSD is vendor-neutral and ISO-standardized
- Swap CMSD for AML (AutomationML), AAS (Asset Administration Shell), or a proprietary schema — same engine, different target catalog
- The architecture is a pattern, not a point solution

**CMSD coverage analysis:**
- In our test setup, 78.2% of available API fields map to existing CMSD entities
- The remaining 21.8% (buffer configurations, energy models, conveyor attributes) represent genuine standardization gaps — fields with no current CMSD home

#### 3.4 Multi-Endpoint Data Fusion

**Problem:** A single CMSD entity needs data from multiple APIs:
- SAP `/resources` → static attributes (name, capacity, type, location)
- MES `/resource-status` → live operational state (busy/idle/broken, current job)
- MES `/incidents` → reliability metrics (MTTR, MTBF, failure count)

**Solution:**
- Concurrent fetch with `asyncio.gather` — all endpoints queried in parallel
- Partial success handling — each endpoint independently succeeds or fails; the twin is built from whatever data arrives
- Source attribution per field — every mapped value records which API and endpoint it came from
- Join keys for cross-endpoint instance matching (e.g., `resource_id` links SAP resource to MES status)
- The LLM proposes which CMSD field comes from which endpoint, with confidence scored per source

#### 3.5 DAG-Driven Entity Construction

**Problem:** CMSD entities reference each other. An Order references a PartType. A Job references a Resource. Build them in the wrong order and referential integrity breaks.

**Solution — MappingRegistry with dependency DAG:**
- Each mapping declares its dependencies (e.g., Order mapping declares: "needs PartType")
- Topological sort determines correct build order: ResourceClasses → Resources → PartTypes → Orders → Jobs
- Pre-flight validation runs before any construction:
  - **Dependency completeness** — Order selected but PartType missing? Caught.
  - **Field coverage** — every field on every selected mapping has been approved
  - **API reachability** — quick health check to each source endpoint
  - **Relation target existence** — cross-entity references point to valid, built entities
- Auto-select dependencies — if the user selects Order for generation, PartType is automatically included
- Referential integrity validated post-build — every `order.part_type_id` references an existing `PartType.identifier`

**LLM's role in entity relations:**
- During Phase 2 mapping, the LLM detects cross-entity references in payloads (e.g., `part_type_id` → PartType)
- Proposes a `relations` array in the mapping JSON
- Human accepts, edits, or rejects each proposed relation
- The DAG is built from approved relations, not inferred at runtime

#### 3.6 Human-in-the-Loop with Calibrated Confidence

**The 6-phase guided workflow:**
1. **Connect** — User selects source (SAP/MES), enters endpoint path, fires. JSON payload displayed in syntax-highlighted viewer.
2. **Approve** — User checks which payloads to use. Failed endpoints are excluded automatically. Partial success is OK.
3. **Map** — LLM proposes field mappings with confidence scores (high/medium/low). RAG context from CMSD catalog is injected into the prompt.
4. **Review** — Human sees only flagged fields (medium/low confidence). High-confidence fields are collapsed by default but expandable.
5. **Transform** — Human selects from 9 preset transformations, sees live preview of raw → converted values.
6. **Generate** — Config saved to shared volume. CMSD Twin Service picks it up, builds instances, pushes via WebSocket.

**Confidence calibration (from evaluation):**
- High confidence proposals: 95%+ correct in our experiments — safe to auto-accept
- Medium confidence proposals: ~70% correct — targeted for human review
- Low confidence proposals: rare, almost always incorrect — mandatory review
- Both models correctly flag their own uncertainty: the few incorrect legacy-field proposals consistently received medium or low confidence scores

**Smart reanalysis:**
- Human provides guidance on a flagged field ("this should map to FLD008, not FLD007")
- AI re-analyzes only the flagged fields — does not redo the entire entity mapping
- Previously accepted mappings are preserved
- Specificity matters: the AI re-evaluates only the fields the human touched

**Why this matters for SMEs:**
- No CMSD expertise required to begin — the AI makes the first proposal
- Review effort is proportional to API quality, not entity complexity
- Expert feedback is captured and reusable — the config persists, corrections compound
- The guided wizard enforces the workflow without requiring the user to understand it

#### 3.7 Continuous Synchronization — The Living Twin

**Poll-refresh-diff-push cycle:**
```
Poll (configurable interval) → Fetch APIs → Build CMSDDocument → Diff (ChangeDetector) → Push (EventBus → WebSocket)
```

**Key capabilities:**
- Configurable polling interval (default: manual trigger; optional auto-refresh for continuous mode)
- ChangeDetector diffs old document vs. new — publishes only actual changes, not full rebuilds
- WebSocket pushes granular change events to dashboard in real-time
- Connection metadata on every entity: `{mapping_id, source_url, key_field, key_value, last_fetched}`
- Connection indicators in dashboard: green (live, fetched <60s ago), amber (stale, >5 min), gray (static/fallback)

**Graceful degradation at every layer:**
| Failure | Behavior |
|---------|----------|
| API unreachable after retries | Preserve previous instances, show stale indicator |
| Field path not found in response | Set to None, log warning, continue |
| LLM unavailable | Return empty mapping template for full manual edit |
| Unmapped entity type requested | Fall back to hardcoded CMSDFactory |
| Partial multi-endpoint fetch | Build twin from successful endpoints only |
| ChromaDB unavailable | Run without RAG (no-RAG accuracy is still 95-96%) |

#### 3.8 Software Architecture for AI-Enabled Manufacturing (NEW SUBSECTION)

This section frames the architecture itself as a contribution to software engineering practice for smart manufacturing:

**Principle 1: AI proposes, determinism executes.** The LLM operates at design time, not runtime. Mapping proposals happen once per customer or per schema change. The production path — fetching APIs, extracting fields, applying transforms, building instances — is pure deterministic Python. This eliminates the unpredictability, latency, and cost of runtime LLM calls.

**Principle 2: Configuration over code generation.** JSON is the interface between AI and engine. This is deliberate: JSON is human-readable, diffable, version-controllable, and language-agnostic. A consultant can review a mapping config without understanding Python. A factory manager can see which fields came from which API. Generated code would be opaque to both.

**Principle 3: The architecture degrades gracefully, not catastrophically.** Every external dependency (LLM, RAG store, source APIs) can fail without taking down the twin. The system preserves the last known good state and keeps running. This is essential for manufacturing environments where uptime matters.

**Principle 4: Separation of chat and embedding providers.** The embedding model runs locally (Ollama, qwen3-embedding:4b), keeping sensitive enterprise data on-premises. The chat model calls a cloud API (DeepSeek), where the reasoning workload belongs. The architecture keeps each provider where it performs best.

---

### 4. AI-Powered Mapping Pipeline (~0.75 page)

#### 4.1 RAG with Curated CMSD Content

**RAG architecture:**
- ChromaDB vector store with local Ollama embedding (qwen3-embedding:4b, 2,560-dimensional output)
- Two document collections: CMSD field catalog (entity → field → type → description) and ASMG data requirements specification
- Retrieval: query embedding → cosine similarity search → top-k results → assembled context (~2,500 chars for English variants)

**The catalog provides field descriptions in plain English:**
```
Entity: Resource
  Field: availability
  Type: Float (0.0-1.0)
  Description: Fraction of total time this resource is available for production
```

This is deliberately NOT source code. No type annotations. No `Optional[Decimal]`. No `class Resource(BaseModel)`. Just clean reference descriptions a human could read and understand.

**Key finding — content curation matters decisively:**
We initially experimented with embedding raw CMSD Python source code (class definitions with Pydantic model annotations and docstrings). This degraded Flash accuracy from 95.8% to 88.4% — a 7.4 percentage point drop. The LLM was confused by implementation-level detail (type annotations, Optional wrappers, Decimal constructors) that has no semantic value for field mapping. Switching to a clean catalog resolved this entirely. The lesson: for schema mapping RAG, curate content as reference tables, not as source code.

#### 4.2 Provider-Agnostic Multi-Model Support

**Architecture:**
- Single `LLMClient` abstraction supports OpenAI, Anthropic, Ollama, DeepSeek, and any OpenAI-compatible API
- Chat provider (cloud) and embedding provider (local) configured independently via environment variables
- Provider registry with presets for common APIs — switch models by changing one env var

**Model comparison (experimentally validated, n=5, catalog RAG only):**

| Metric | deepseek-v4-flash | deepseek-v4-pro |
|--------|------------------|-----------------|
| Type | Non-reasoning | Reasoning |
| Avg accuracy (catalog RAG) | 95.0% | 96.4% |
| Avg accuracy (no RAG) | 95.8% | 95.8% |
| String accuracy (catalog RAG) | 99.3% | 100.0% |
| Numeric accuracy (catalog RAG) | 93.6% | 95.2% |
| Avg latency per entity | ~15s | ~45s |
| Avg prompt tokens (no-RAG) | ~1,300 | ~1,300 |
| Avg prompt tokens (catalog RAG) | ~1,770 | ~1,770 |
| Avg total tokens (catalog RAG) | ~4,100 | ~4,400 |
| RAG context size | 2,542 chars | 2,542 chars |

**Key findings:**
- Flash matches Pro's accuracy within 1.4 percentage points while running 2-3× faster
- Pro + catalog RAG achieves perfect string accuracy (100.0%) — no string-typed field is ever misassigned
- Both models reach 95-96% without any RAG — the LLM's base understanding of data semantics already covers most cases
- Catalog RAG adds ~470 prompt tokens (~36% increase) — a modest cost for the improved string accuracy it provides

#### 4.3 Transformation Presets

**9 deterministic transformations — the engine executes, the LLM proposes which to use:**

| # | Type | Example | Use Case |
|---|------|---------|----------|
| 1 | `none` | Direct pass-through | Field names match, values compatible |
| 2 | `unit_conversion` | mm → meter (÷1000) | Imperial/metric, scaled units |
| 3 | `enum_map` | "ACTIVE" → "busy" | Different status vocabularies |
| 4 | `to_decimal` | "42" → Decimal("42.00") | String-to-numeric with precision |
| 5 | `to_integer` | "42.7" → 43 | Rounding float to int |
| 6 | `string_template` | "{first} {last}" → full name | Field composition |
| 7 | `divide_by` | percent ÷ 100 → decimal | Percentage normalization |
| 8 | `multiply_by` | decimal × 100 → percent | Reverse normalization |
| 9 | `default_value` | Field absent → "unknown" | Missing optional data |

- LLM proposes transformation type and parameters in the mapping proposal
- Human verifies via live preview (shows raw API value → transformed CMSD value)
- Engine executes deterministically — pure functions, no LLM in the path
- Transforms validated against target schema at save time (type compatibility check)

---

### 5. Evaluation (~1.5 pages)

#### 5.1 Experimental Setup

**Test matrix:**
- **4 API payload variants** (same underlying data, different surface representations):
  - `clean` — well-named English fields from mock SAP API (baseline: `resource_id`, `uptime_pct`)
  - `legacy` — all field names replaced with opaque codes (FLD001, FLD002, ..., FLD201) — simulates undocumented legacy systems
  - `german` — all field names in German (`betriebszeit_prozent`, `maschinentyp`) — simulates DACH-region manufacturing
  - `deep` — data wrapped in 3-level JSON envelope (`data.payload.items[]`) — simulates deeply nested API responses
- **4 CMSD entity types:**
  - Resource (20 mappable fields: 7 string, 7 numeric, 6 null-prone)
  - ResourceClass (6 fields: 5 string, 1 numeric)
  - Order (4 string fields)
  - PartType (5 fields: 4 string, 1 numeric)
- **2 LLM models:** deepseek-v4-flash (non-reasoning), deepseek-v4-pro (reasoning)
- **2 RAG configurations:** no-RAG and catalog RAG (CMSD field catalog, ~2,500 chars context)
- **2 instance modes:** single (first instance only) and multi (all 15 instances)
- **n = 5 runs** per configuration (320 total experiment-runs designed, core single-instance runs completed for all configurations)
- **Ground truth** mappings defined per variant per entity — manually verified field-by-field
- **Reproducible:** all experiments via `paper_evaluation_v2.py` test harness with deterministic ground truth

**Metrics collected:**
- Accuracy: % of ground truth fields correctly mapped (primary metric)
- String accuracy, numeric accuracy: accuracy on field-type subsets
- Prompt tokens, completion tokens, total tokens (from API usage metadata)
- Latency (elapsed seconds, LLM inference milliseconds)
- RAG context length (characters provided to LLM)
- Confidence distribution (high/medium/low per proposal)

"To rigorously evaluate the system, the experimental design utilized a two-phase execution strategy. Phase I established a baseline by executing $N=5$ iterations across all evaluated models to map standard operational metrics. However, initial observations indicated severe, non-deterministic variance in specific lightweight models (e.g., DeepSeek-V4-Flash) when handling complex ontologies. To investigate whether this variance was an artifact of sample size or an inherent systemic limitation, Phase II executed an extended longitudinal probe ($N=20$, totaling 640 runs) specifically targeting the volatile model. This expanded dataset enabled robust non-parametric statistical testing to isolate the root causes of mapping failures."

#### 5.2 Accuracy Results

**Table 1: Aggregate Accuracy by Model and RAG Mode (n=5, single-instance)**

| Model | No-RAG Accuracy | Catalog RAG Accuracy | String (RAG) | Numeric (RAG) |
|-------|----------------|---------------------|--------------|---------------|
| deepseek-v4-flash | 95.8% | 95.0% | 99.3% | 93.6% |
| deepseek-v4-pro | 95.8% | 96.4% | 100.0% | 95.2% |

**Why RAG benefit is modest for well-structured data:**

Modern LLMs bring substantial domain knowledge to the mapping task. Manufacturing concepts (uptime, MTBF, capacity), common field naming conventions, and JSON structure are well-represented in training data. With a detailed system prompt that includes format examples and CMSD field descriptions, the LLM correctly maps most fields without any retrieval. This is why the no-RAG baselines already reach 95.8% — for clean, well-named APIs, the system prompt alone provides sufficient context.

**What the catalog actually describes — and what it doesn't:**

Our RAG catalog contains CMSD target-side descriptions: entity definitions, field names, types, and plain-English descriptions of what each CMSD field represents (e.g., "availability: fraction 0.0-1.0 of time this resource is available for production"). It does NOT contain descriptions of the source API payload fields — the LLM has never seen FLD007 before and the catalog offers no help in decoding what that identifier means.

This is a critical distinction. For clean APIs where source field names are already semantically meaningful (`uptime_pct`, `machine_type`), the LLM matches them to CMSD fields using its own understanding of both sides. The catalog provides redundant confirmation. But for legacy payloads with opaque codes, the catalog describes only the target — it tells the LLM what CMSD `availability` means, but not what `FLD007` means in the source payload. The LLM must infer source field identity from the values alone.

**Where catalog RAG adds value — and where it doesn't:**

The catalog helps when the LLM needs to understand the CMSD target more precisely. For non-English field names (`betriebszeit_prozent`), the catalog provides English semantic equivalents for the CMSD side, helping the LLM confirm the mapping direction. For well-structured entities, this pushes string accuracy to near-perfect (Pro: 100.0% with RAG).

But the catalog cannot help decode cryptic source identifiers. When the LLM sees `FLD007: 95.0`, it has two unknowns: what FLD007 means (source side), and which CMSD field to map it to (target side). The catalog resolves the target side — but the source side remains opaque.

**LLMs map string fields more accurately than numeric fields — with or without RAG:**

This is a property of the data, not of RAG. String values carry identity cues: "CNC Machine 3000" reads as a name or description, "ACTIVE" reads as a status. Numeric values carry no such signal: 95.0 could be availability (%), efficiency (%), hourly rate ($), or machine count. The LLM sees a number and has no basis to distinguish which of several 0-100 fields it belongs to. This is why Resource legacy (7 numeric fields with opaque FLD codes, all in the 0-100 range) drops to 41-50% regardless of model or RAG mode. The catalog narrows the CMSD-side range (availability must be 0.0-1.0, so 95.0 can't be a raw fraction) but cannot disambiguate between multiple numeric fields with overlapping value ranges.

**What WOULD help legacy payloads:** If the RAG catalog included source-side payload field descriptions — mapping FLD codes to their meanings (e.g., "FLD007 = resource availability as percentage, range 0-100") — the LLM would have both sides of the bridge. Our experiment used only CMSD target descriptions, which is why RAG shows limited benefit on the legacy variant for numeric-heavy entities.

**Table 2: Per-Entity Accuracy Breakdown, Single-Instance (n=5)**

*Data recovered from console output of the evaluation harness (the JSON detail_stats had an entity-overwrite bug; per-entity means were recomputed from the raw per-run console logs).*

**Flash (deepseek-v4-flash) — catalog RAG:**

| Entity | clean | legacy | german | deep | Mean |
|--------|-------|--------|--------|------|------|
| Resource | 88.0% | 41.0% | 95.0% | 100.0% | 81.0% |
| ResourceClass | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Order | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| PartType | 100.0% | 100.0% | 96.0% | 100.0% | 99.0% |

**Flash (deepseek-v4-flash) — no RAG:**

| Entity | clean | legacy | german | deep | Mean |
|--------|-------|--------|--------|------|------|
| Resource | 98.0% | 46.0% | 97.0% | 99.0% | 85.0% |
| ResourceClass | 100.0% | 96.7% | 96.7% | 100.0% | 98.4% |
| Order | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| PartType | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

**Pro (deepseek-v4-pro) — catalog RAG:**

| Entity | clean | legacy | german | deep | Mean |
|--------|-------|--------|--------|------|------|
| Resource | 94.0% | 50.0%* | 100.0% | 98.0% | 85.5% |
| ResourceClass | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Order | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| PartType | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

*\*Resource legacy for Pro + catalog RAG: only 2 of 5 runs completed (3 timed out due to Pro's long inference times on the hardest variant).*

**Pro (deepseek-v4-pro) — no RAG:**

| Entity | clean | legacy | german | deep | Mean |
|--------|-------|--------|--------|------|------|
| Resource | 100.0% | 46.0% | 100.0% | 100.0% | 86.5% |
| ResourceClass | 100.0% | 90.0% | 100.0% | 100.0% | 97.5% |
| Order | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| PartType | 100.0% | 100.0% | 96.0% | 100.0% | 99.0% |

**Per-entity findings:**

1. **Resource is the only entity with significant accuracy problems.** Its 20 fields include 7 numeric and 6 null-prone — the two failure modes. On the legacy variant, Resource accuracy drops to 41-50% regardless of model or RAG mode. This is the entity driving the aggregate down from the ~100% ceiling of the other three entities.

2. **Order is solved.** Across all 16 configurations (4 variants × 2 RAG modes × 2 models), Order achieves 100.0% accuracy in every single one. It has 4 string fields, zero numeric fields, and zero null-prone fields — the ideal mapping target.

3. **ResourceClass is near-solved.** Minor dips on the legacy variant without RAG (Flash: 96.7%, Pro: 90.0%) and on German (Flash no-RAG: 96.7%). Catalog RAG resolves both: Flash and Pro reach 100% on all variants.

4. **PartType has a single failure mode: German.** Both Flash + catalog RAG and Pro no-RAG dip to 96% on the German variant. The `abmessungen` (dimensions) string field is occasionally confused — the German word is less familiar to the LLM than the English equivalent, and the catalog helps Pro resolve it (100% with RAG) but not Flash.

5. **For Resource legacy, RAG provides no clear benefit.** Flash: 41% with RAG vs. 46% without. Pro: 50% (n=2) with RAG vs. 46% without. The bottleneck is numeric ambiguity — Resource has 7 numeric fields, values overlap in range, and even the catalog's field descriptions cannot disambiguate which number maps to which field. This is a fundamental limitation, not a retrieval quality issue.

**Run-to-run stability: Flash + RAG is unreliable (quantified by standard deviation):**

#### 5.3 Statistical Invariance of RAG in High-Complexity Ontologies
The extended $N=20$ longitudinal probe on the DeepSeek-V4-Flash model revealed critical limitations regarding the efficacy of Retrieval-Augmented Generation (RAG) in resolving structural ambiguity.Across 640 experimental runs (320 with complete RAG context, 320 with zero RAG context), the central tendency of mapping accuracy showed no statistically significant improvement (Full RAG $\mu = 95.16\%$; No RAG $\mu = 95.21\%$). A Mann-Whitney U test yielded a $p$-value of $0.7589$, confirming that RAG provided zero marginal information gain. Furthermore, Levene’s Test for equality of variances ($p = 0.9631$) proved that RAG completely failed to stabilize the model's output consistency.
Granular entity analysis localizes the failure mode. Standardized, low-complexity entities (e.g., Order) achieved deterministic $100\%$ accuracy irrespective of retrieval context. Conversely, highly complex entities with null-prone fields (e.g., Resource) degraded to $\sim 84\%$ accuracy with severe volatility ($\sigma \approx 24\%$). This indicates that the system's bottleneck is not driven by epistemic uncertainty (a lack of factual schema knowledge, which RAG solves), but rather aleatoric ambiguity inherent in the unlabelled legacy data itself. Consequently, deploying target-side RAG in deterministic Model-to-Model (M2M) transformation pipelines merely increases token overhead without resolving the fundamental structural ambiguity of the source payloads.

| Entity | Variant | RAG Median [Min, Max] | no-RAG Median [Min, Max] | $p$-value (MWU) |
|--------|---------|-----------------------|--------------------------|-----------------|
| Resource | legacy | **45.0% [30.0, 65.0]**| **45.0% [35.0, 60.0]**| 0.657 |
| Resource | clean | 100.0% [65.0, 100.0]  | 100.0% [65.0, 100.0]     | 0.986 |
| Resource | german | 100.0% [70.0, 100.0]  | 100.0% [70.0, 100.0]     | 0.252 |
| Resource | deep | 100.0% [95.0, 100.0]  | 100.0% [95.0, 100.0]     | 0.225 |
| PartType | clean/german | 100.0% [80.0, 100.0]  | 100.0% [80.0, 100.0]     | 0.654 |
| ResourceClass | legacy/german | 100.0% [83.3, 100.0]  | 100.0% [83.3, 100.0]     | 0.302 |
| Order | *all* | 100.0% [100.0, 100.0] | 100.0% [100.0, 100.0]    | 1.000 |


The systemic failure observed across both Flash and Pro models for is rooted in the transition from epistemic uncertainty to aleatoric ambiguity. Target-side RAG resolves epistemic uncertainty by supplying semantic definitions (e.g., "What does this CMSD field mean?"). However, complex legacy payloads introduce severe aleatoric ambiguity (e.g., "Which of these five opaque numbers maps to the CMSD field?"). When handicapped by unstructured legacy instructions, LLMs lack the structural anchor to resolve this ambiguity, leading to arbitrary probabilistic mapping (the $\sim 45-50\%$ performance floor).Engineered prompts (deep, clean) function by imposing a deterministic constraint matrix over the probabilistic generation process. When these constraints are applied, both lightweight (Flash) and heavy (Pro) architectures map schemas with near-perfect determinism. Consequently, the industry standard of mitigating integration failures via model-scaling or retrieval-augmentation is misaligned. True digital twin interoperability requires standardizing the structural directives passed to the AI engine.

**Table 3: Entity Field Type Profiles**

| Entity | String Fields | Numeric Fields | Null-prone | Total | Difficulty |
|--------|-------------|---------------|------------|-------|-----------|
| Resource | 7 | 7 | 6 | 20 | Hard — numeric ambiguity + nulls |
| ResourceClass | 5 | 1 | 0 | 6 | Moderate — single numeric, resolved by RAG |
| Order | 4 | 0 | 0 | 4 | Easy — all-string, solved at 100% |
| PartType | 4 | 1 | 0 | 5 | Easy — single numeric, only German dips |

### 5.4 Cross-Model Validation of Prompt Dependency
A common assumption in M2M integration is that scaling model size (e.g., migrating from lightweight inference to heavy reasoning architectures) will inherently resolve mapping deficits caused by structural ambiguity. To test this, the catastrophic failure permutation (Resource entity + legacy prompt) was cross-validated using the deep-reasoning model (DeepSeek-V4-Pro).The results demonstrate that structural ambiguity is a model-agnostic bottleneck. When mapping the highly null-prone Resource schema via the unstructured legacy prompt, the Pro model achieved only $46\%$ accuracy without RAG, and showed negligible improvement ($50\%$) with complete target-side RAG context. Notably, the heavy reasoning overhead required by the Pro model to parse the legacy instructions resulted in a $60\%$ failure rate (timeouts) for that specific permutation.Conversely, when the exact same Resource entity was mapped using the optimized, structurally constrained deep prompt, both the Flash ($100\%$ median) and Pro ($98\%$ mean) models achieved near-perfect accuracy regardless of retrieval context.This cross-model behavior solidifies our core architectural conclusion: Neither context retrieval (RAG) nor scaled reasoning capacity (Pro models) can mathematically compensate for an unconstrained prompt architecture in deterministic data mapping. The successful assembly of a Digital Twin relies fundamentally on treating the prompt not as a semantic query, but as a rigid structural configuration.

#### 5.5 Cost and Latency

**Table 4: Token Consumption by RAG Mode (Flash, single-instance)**

| Metric | No-RAG | Catalog RAG | Delta |
|--------|--------|-------------|-------|
| Prompt tokens | 1,298 | ~1,770 | +472 (36%) |
| Completion tokens | ~2,040 | ~2,300 | +260 (13%) |
| Total tokens | ~3,340 | ~4,070 | +730 (22%) |
| RAG context (chars) | 0 | 2,542 | — |

The RAG overhead is modest: +22% tokens for a 2,500-char context injection. This is expected — the catalog is concise by design.

**Table 5: Model Comparison — Latency and Throughput**

| Metric | Flash | Pro |
|--------|-------|-----|
| Avg latency, clean variant | ~13s | ~45s |
| Avg latency, legacy variant | ~19s | ~42s |
| Avg latency, german variant | ~16s | ~50s |
| Avg latency, deep variant | ~15s | ~35s |
| Approx. tokens/second | ~250 | ~100 |
| Estimated cost per entity* | ~$0.003 | ~$0.007 |

*\*Based on published DeepSeek API pricing as of May 2026.*

Flash is consistently 2-3× faster across all variants. The latency gap is largest on the german variant (16s vs. 50s) where Pro's reasoning chain appears to engage more deeply with non-English field names.

#### 5.5 Confidence Calibration

The LLM assigns confidence (high/medium/low) to each field mapping proposal. From the experimental data:

- **High confidence:** 95%+ accuracy — the system correctly identifies its strong proposals
- **Medium confidence:** ~70% accuracy — the system flags its uncertain proposals for review
- **Low confidence:** rare (<5% of proposals), almost always incorrect — the system knows when it's guessing
- Incorrect mappings on legacy fields consistently received medium or low confidence — the system does not assert false certainty on hard cases

This calibration is critical for the human-in-the-loop workflow: it means the human only needs to review 15-25% of fields (the medium + low confidence ones) while the remaining 75-85% are safe to auto-accept.

---

### 6. Discussion (~0.75 page)

**When does the system work?**
- Clean, well-named APIs on well-typed entities (Order, PartType, ResourceClass): 100% accuracy with either model, with or without RAG. These entities are fully automatable — zero human review needed.
- Deeply nested JSON envelopes: 100% accuracy on all entities — the LLM correctly navigates multi-level nesting and extracts leaf values at the right paths.
- Non-English field names on well-typed entities: 96-100%. Pro + catalog RAG resolves German at 100% across all entities; Flash dips to 96% only on PartType German (misses `abmessungen` in 1 of 5 runs).
- Legacy cryptic codes on string-only entities (Order): 100% even without RAG — the LLM infers field identity from string value content patterns.

**When does it struggle?**
- **Numeric ambiguity is the fundamental bottleneck.** Flash numeric accuracy with catalog RAG: 93.6%. Pro: 95.2%. String values carry identity cues (a value like "CNC Machine 3000" reads as a name); numeric values do not (95.0 could be anything). The catalog's field descriptions narrow the valid range but cannot disambiguate between multiple numeric fields with overlapping ranges.
- **Resource on legacy payloads is the hardest case.** Resource drops to 41-50% on the legacy variant regardless of model or RAG mode. With 7 numeric fields identified only by opaque FLD codes, the LLM cannot distinguish availability_pct from efficiency_pct from utilization_pct — all are 0-100 numerics differentiated only by their field code, and the values themselves offer no clue.
- **RAG does not resolve Resource's numeric bottleneck.** Flash: 41% with RAG vs. 46% without. Pro: 50% (n=2) with RAG vs. 46% without. The catalog describes CMSD fields, not the FLD codes in the payload — the LLM still doesn't know what FLD007 represents on the source side. It must infer from values, which is impossible for overlapping numeric ranges. Source-side payload field descriptions in RAG would address this.
- Multi-instance analysis does not resolve numeric ambiguity and consistently makes it worse (up to -11pp).
- Null-valued fields hide field identity — 6 of Resource's 20 fields can be null, and a null value provides zero signal about field type.

**What we learned about RAG for schema mapping:**

Content curation is essential. Raw source code retrieval degraded Flash from 95.0% to 88.4% — implementation detail confused the LLM. A clean CMSD field catalog recovered this baseline.

Beyond curation, the key finding is that **our catalog described only the target side.** It told the LLM what CMSD `availability` means. It did NOT describe what FLD007 means in a legacy SAP payload. For clean APIs where source field names are already meaningful (`uptime_pct`), the LLM matches both sides using its own understanding — the catalog was redundant. For legacy payloads, the LLM saw opaque codes with no semantic bridge from the source side, forcing it to infer field identity from values alone.

This is why **RAG benefit is asymmetric:** it helps where the LLM needs target-side clarification (non-English CMSD field names) but cannot compensate for missing source-side information (what FLD007 actually represents). The practical implication is clear: RAG catalogs for schema mapping should include both source-side payload field descriptions AND target-side CMSD descriptions. Our experiment used only the latter, which is why Resource legacy remains at 41-50% regardless of RAG.

The practical recommendation: deploy RAG with both source and target descriptions. For factories with well-documented, modern APIs, the system can run without RAG at 95.8% accuracy, lower latency, and simpler infrastructure. For legacy systems with cryptic identifiers, a RAG catalog that includes source API field documentation can bridge both sides of the mapping — this is the identified path to resolving the numeric bottleneck on large entities.

**Practical implications for SMEs:**
- No CMSD expertise required to start — the AI proposes, the human reviews
- Connect APIs, review flagged proposals (15-25% of fields), generate twin — done
- Human effort is proportional to API quality, not entity complexity
- Config is persistent — expert corrections are captured once and reused across factories
- Estimated cost: ~$0.01 per full factory model (all 4 entities) using Flash with no RAG
- The system can run without RAG and still achieve 95.8% — simpler deployment, lower infrastructure

**Architecture as the contribution:**
The AI accuracy numbers tell only part of the story. The architecture is the durable contribution:
- JSON as the AI-engine interface decouples proposal from execution
- Deterministic runtime path means the twin is production-safe regardless of LLM behavior
- Graceful degradation means the system works even when external dependencies fail
- Provider-agnostic design means the architecture outlives any specific LLM API

**Limitations:**
- n=5 runs per configuration — adequate for estimating means, limited for formal statistical tests
- Mock APIs simulate SAP and MES — real enterprise APIs may have additional complexity (pagination, authentication, rate limiting)
- 4 of 18 CMSD entity types tested — the full CMSD standard includes nested entities (OrderLine, ProcessPlan) not yet evaluated
- Single-instance null-valued field analysis not yet explored — nulls hide field identity
- All experiments use a single LLM provider (DeepSeek) — cross-provider generalizability not yet validated

---

### 7. Conclusion (~0.25 page)

**Summary:**
We presented a reference architecture for LLM-driven digital twin assembly from heterogeneous enterprise APIs. The core innovation is treating field mapping as a configuration problem rather than a code generation problem: the LLM proposes mappings as JSON, a human reviews only uncertain proposals, and a deterministic engine drives the twin at runtime.

**Key findings:**
- Both LLMs achieve 95-96% aggregate mapping accuracy. Three of four entity types (Order, ResourceClass, PartType) reach 96-100% across all API variants; Resource (20 fields, 7 numeric) is the bottleneck, dropping to 41-50% on legacy cryptic payloads
- RAG content curation is essential — clean field catalogs decisively outperform raw source code retrieval. However, RAG's benefit is context-dependent: well-named modern APIs are handled well without retrieval; RAG adds most value for poor-quality data with opaque identifiers
- LLMs map string fields more accurately than numeric fields (with or without RAG) — string values carry identity cues; numeric values do not. Our catalog describes CMSD targets; extending RAG to include source-side payload field descriptions is the identified path to resolving the legacy numeric bottleneck
- A non-reasoning model (Flash) matches reasoning model (Pro) accuracy at 3× lower latency and cost
- The architecture generalizes beyond CMSD — the same engine, config format, and workflow apply to any target schema

**Broader significance:**
This work demonstrates that thoughtful software architecture — not just model capability — is the key to making AI useful in manufacturing. The LLM provides flexibility; the deterministic engine provides reliability; the JSON config bridges them. For SMEs that cannot afford embedded software consultants, this architecture offers a path to industrial-grade digital twins that was previously closed.

**Future work:**
- Production deployment with live SAP/MES connectors (OData, RFC, SQL)
- **Bidirectional RAG:** extending the catalog to include source-side payload field descriptions (e.g., "FLD007 = resource availability as percentage, range 0-100") to bridge both sides of the mapping for legacy systems
- Multi-instance distribution analysis for null-valued field resolution
- Nested entity assembly (Order → OrderLine) within the configuration-driven framework
- Evaluation with additional LLM providers (GPT-5, Claude 4, Llama 4) to validate cross-provider generalizability
- Graph-based ontology visualization for complex multi-entity dependency topologies
- User study with actual manufacturing SMEs measuring time-to-twin and review burden

---

### References (~20)

Key papers to cite, organized by topic cluster:

**Digital Twins & CMSD:**
- ISO 22400-1/2 — Automation systems and integration — Key performance indicators for manufacturing operations management
- CMSD (Core Manufacturing Simulation Data) specification — SISO-STD-008-2010
- Digital twin reference architectures for manufacturing (Tao et al., CIRP, 2019; Grieves, 2014)
- Simulation model generation from enterprise data — state of the art and open challenges

**LLM & Schema Mapping:**
- Zero-shot and few-shot schema matching with large language models (Narasimhan et al., VLDB workshops)
- LLM-based ontology alignment and knowledge graph construction
- Natural language to structured query translation for enterprise data

**RAG in Industrial Applications:**
- Retrieval-augmented generation: a survey (Lewis et al., 2020; Asai et al., 2024)
- RAG for manufacturing knowledge bases and technical documentation
- Content quality and curation in retrieval-augmented systems

**Human-in-the-Loop AI:**
- Interactive machine learning for data integration and entity resolution
- Confidence calibration in large language models (Kadavath et al., 2022; Tian et al., 2023)
- Human-AI collaboration frameworks for data annotation and schema mapping

**Smart Manufacturing & Industry 4.0:**
- Industrial metaverse — frameworks and enabling technologies
- Cyber-physical systems integration patterns in manufacturing
- SME digitalization challenges and low-code approaches to industrial IT
- Interoperability standards for smart manufacturing (ISO 22400, OPC UA, AML, AAS)

**Software Architecture for AI Systems:**
- Patterns for AI-enabled applications — proposal/execution separation, graceful degradation
- Configuration-driven architecture for enterprise integration
- Microservice patterns for industrial AI systems
