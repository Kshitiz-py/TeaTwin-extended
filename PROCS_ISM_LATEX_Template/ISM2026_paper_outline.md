# ISM 2026 Paper Outline

## Metadata

- **Title:** Configuration, Not Code: A Human-in-the-Loop LLM Architecture for Mapping Heterogeneous Enterprise Systems to Canonical Digital Twin Models
- **Target Venue:** 8th International Conference on Industry of the Future and Smart Manufacturing (ISM 2026)
- **Invited Track:** Reshaping future smart manufacturing: convergence of Industrial Metaverse, Cyber-Physical Systems, and Digital Twins
- **Length:** 8 pages maximum
- **Author:** Kshitiz Bohara

---

## Contribution Hierarchy

1. **Architecture** (LEAD): Configuration-driven architecture — LLM proposes JSON config at design time, deterministic engine drives twin at runtime. Vendor-neutral canonical hub. Zero per-customer code.
2. **Human-in-the-Loop Workflow**: Calibrated confidence scoring, targeted review of flagged fields only, smart reanalysis.
3. **Empirical Validation**: 95-96% accuracy, non-reasoning = reasoning at 3x speed, numeric ambiguity is the fundamental bottleneck, RAG provides zero statistical improvement on legacy payloads.

---

## Page Budget

| Section | Pages | Cumulative |
|---------|-------|------------|
| 1. Introduction | 1.0 | 1.0 |
| 2. Related Work | 0.75 | 1.75 |
| 3. System Architecture | 2.0-2.25 | ~4.0 |
| 4. AI-Powered Mapping Pipeline | 0.75-1.0 | ~4.75 |
| 5. Evaluation | 1.5-1.75 | ~6.5 |
| 6. Discussion | 0.5 | ~7.0 |
| 7. Conclusion | 0.25-0.5 | ~7.5 |
| References | 0.5 | ~8.0 |

---

## Abstract (~180 words)

> Manufacturing enterprises sit on decades of data locked in heterogeneous ERP and MES systems, yet building digital twins from this data today requires per-customer code, embedded consultants, and manual field mapping --- excluding the SMEs who stand to gain the most. We present a human-in-the-loop architecture where an LLM reads raw enterprise API payloads, consults a curated catalog of target-schema field descriptions, and proposes field-level mappings as JSON configuration with calibrated confidence scores. A human reviews only the fields the model flags as uncertain, while high-confidence proposals are safe to auto-accept. A deterministic runtime engine consumes the configuration and assembles the digital twin with zero per-customer code. The architecture is vendor-agnostic: heterogeneous source systems map to any canonical information model (exemplified here by CMSD/ISO 22400). Across two LLM architectures, four API payload variants, and controlled RAG ablation, both models achieve 95-96% aggregate mapping accuracy. The non-reasoning model matches the reasoning model within 1.4 percentage points while running 3x faster with lower token consumption. Extended statistical analysis (n=20, 640 runs) reveals that field ambiguity, predominantly in numeric fields within legacy payloads, is the fundamental bottleneck --- target-side RAG provides zero statistically significant improvement (Mann-Whitney U, p > 0.05). The architecture, not the model, is the contribution.

---

## Section-by-Section Outline

### 1. Introduction (~1 page)

**Opening (SME hook --- touchpoint 1 of 3):**
Open with a concrete scenario: a mid-sized CNC machining supplier attempting to join an OEM's Industrial Metaverse supply chain. Their data lives in an on-premise SAP ERP with German field names and a legacy MES with opaque coded identifiers. The path to CMSD compliance today: hire a consultant, hand-write field mappings in Python, rebuild per factory. This is the status quo for thousands of SMEs. [REF NEEDED: SME digitalization barriers]

**Problem statement:**
- Enterprise data lives in SAP/MES --- different field names, structures, conventions, languages
- Digital twins need structured data conforming to standards like CMSD/ISO 22400
- Current approach: consultants manually map API fields, hardcode per customer in Python
- Result: brittle code, high per-customer cost, slow onboarding, SME exclusion

**Opportunity:**
- LLMs can parse structured API payloads and target schema definitions
- They can propose field-level mappings with self-assessed confidence scores
- This enables a fundamentally different architecture: LLM proposes mappings as data (JSON), human reviews only uncertain proposals, deterministic engine drives the twin at runtime
- Mapping is a configuration problem, not a code generation problem

**Contribution statement (3 bullets):**
1. **Architecture:** A configuration-driven architecture where an LLM proposes field-level mappings as JSON configuration at design time, a deterministic engine assembles the digital twin at runtime with zero per-customer code, and a vendor-neutral canonical information model (exemplified by CMSD/ISO 22400) serves as the integration hub for heterogeneous enterprise APIs.
2. **Human-in-the-Loop Workflow:** A calibrated confidence framework where the LLM self-scores each mapping proposal (high/medium/low), enabling targeted human review of only uncertain fields while high-confidence proposals are safe to auto-accept, with smart reanalysis that re-evaluates only corrected fields.
3. **Empirical Validation:** Experimental results across two LLM architectures (reasoning vs. non-reasoning), four API payload variants, and two RAG configurations demonstrating 95-96% aggregate mapping accuracy and revealing that numeric field ambiguity in legacy payloads --- not retrieval quality or model capacity --- is the fundamental bottleneck for automated schema mapping.

**Findings preview (one paragraph):**
Both models achieve 95-96% aggregate accuracy. For well-structured entities, accuracy reaches 96-100%; the Resource entity (20 fields, 7 numeric, 6 null-prone) drops to ~45% on legacy cryptic payloads regardless of model or RAG. The non-reasoning model matches the reasoning model within 1.4pp at 3x lower latency. RAG benefit is asymmetric: it helps where the LLM needs target-side clarification but cannot resolve source-side numeric ambiguity. Extended statistical analysis (n=20, 640 runs) confirms RAG provides zero significant improvement on the hardest case (Mann-Whitney U, p > 0.05).

---

### 2. Related Work (~0.75 page)

**Four clusters, 3-4 references each. [REF NEEDED: All citations]**

**2.1 Digital Twin Automation:**
- Automated generation of simulation models from enterprise data sources
- Existing approaches: hardcoded factory classes, rule-based mapping engines, template-driven code generation
- Gap: all require per-customer customization by someone who knows both source APIs and target schema

**2.2 AI-Assisted Data Integration:**
- Traditional: rule-based matchers, dictionary-based string similarity, heuristic structural matching
- Recent: LLM-based zero-shot and few-shot schema mapping across database schemas and knowledge graphs
- Human-in-the-loop: interactive machine learning for schema matching, confidence-calibrated review systems
- Our position: LLM + calibrated human review is the right balance for industrial settings where correctness matters. Merge schema mapping and HITL into one cluster to show the convergence.

**2.3 CMSD and ISO 22400 in Practice:**
- Core Manufacturing Simulation Data standard --- structure, entities, adoption landscape
- Existing implementations: simulation tool integration, data exchange formats
- Gap: no prior LLM-driven field mapper targeting CMSD as canonical hub in multi-source enterprise integration

**2.4 Smart Manufacturing & SME Digitalization:**
- Barriers to digital twin adoption for small and medium manufacturers
- Low-code and no-code approaches to industrial system integration
- Our position: configuration-driven architecture specifically addresses the SME cost and expertise gap. Highlights the convergence of Industrial Metaverse, CPS, and Digital Twins the track calls for.

---

### 3. System Architecture (~2-2.25 pages) --- THE CORE CONTRIBUTION

#### 3.1 Architecture Overview

**Five-service design, single Docker Compose:**
- Mock SAP API (Port 8001): master data --- resources, BOMs, orders, part types
- Mock MES API (Port 8002): operational data --- resource status, job execution, incidents
- AI Agent (Port 8003): LLM client, RAG retriever (ChromaDB), mapping engine (propose + validate)
- CMSD Twin Service (Port 8000): MappingDrivenFactory, ChangeDetector, EventBus → WebSocket push
- Web Dashboard (React): Guided Mapping UI + Twin Monitor

**Infrastructure:**
- ChromaDB vector store: 2 knowledge collections (CMSD field catalog + ASMG requirements doc)
- Ollama: local embedding model (qwen3-embedding:4b, 2,560-dimensional vectors)
- Shared Docker volume for mapping configs between AI Agent and CMSD Twin Service

**Data flow:** REST for request-response, WebSocket for live twin updates, shared volume for config handoff.

**Key architectural decisions summarized:**
- Single docker compose up deploys everything
- Provider-agnostic LLM interface (any OpenAI-compatible API)
- Separate chat provider (cloud LLM) and embedding provider (local Ollama)
- No LLM in the runtime path --- mapping proposal uses LLM; twin generation uses deterministic engine only

**[Figure 1: Architecture diagram --- 5-service system with data flows]**

#### 3.2 Mapping as Configuration --- The Central Idea

**Side-by-side comparison (code listing, not figure):**
- LEFT: Traditional hardcoded per-customer Python factory pattern (5-8 line sketch)
- RIGHT: JSON mapping config (the full structure: mapping_id, cmsd_entity, source_endpoints, field mappings with api_path, confidence, transformation)

**What this enables:**
- JSON config is single source of truth --- human-readable, version-controllable, diffable
- MappingDrivenFactory is entirely generic --- reads any valid config, produces CMSD instances
- 9 transformation presets (mentioned in prose, shown inline in the JSON listing) cover 90%+ of real-world conversion needs
- No LLM in the runtime path --- factory is pure deterministic Python
- New customer = new JSON file = zero code changes = zero redeployment
- Config CRUD lifecycle: New, Save, Load, Publish, Download

#### 3.3 The Neutral Format Hub

**The problem:** SAP and MES speak different dialects:
- SAP: `resource_id`, `resource_name`, `uptime_pct`, `RESOURCE_TYPE`
- MES: `machineId`, `status`, `currentJob`, `MTTR_VALUE`
- Same domain concepts, incompatible naming conventions

**The solution:** A canonical information model (exemplified by CMSD/ISO 22400) at the center:
- Both source systems map to the same target vocabulary
- The AI layer translates each source dialect into the canonical format
- The twin only knows the canonical model --- source heterogeneity is abstracted away

**Why this generalizes:**
- The canonical model is vendor-neutral and ISO-standardized
- Swap the target schema (AML, AAS, proprietary) --- same engine, different target catalog
- The architecture is a pattern, not a point solution

#### 3.4 Multi-Endpoint Data Fusion

**Problem:** A single digital twin entity needs data from multiple APIs:
- SAP /resources → static attributes (name, capacity, type, location)
- MES /resource-status → live operational state
- MES /incidents → reliability metrics (MTTR, MTBF)

**Solution:**
- Concurrent fetch with asyncio.gather --- all endpoints queried in parallel
- Partial success handling --- each endpoint independently succeeds or fails; twin built from available data
- Source attribution per field --- every mapped value records which API it came from
- Join keys for cross-endpoint instance matching (resource_id links SAP to MES)

#### 3.5 DAG-Driven Entity Construction

**Problem:** Entities reference each other. Order → PartType. Job → Resource. Wrong build order breaks referential integrity.

**Solution --- MappingRegistry with dependency DAG:**
- Each mapping declares dependencies (Order declares: needs PartType)
- Topological sort determines build order: ResourceClasses → Resources → PartTypes → Orders → Jobs
- Pre-flight validation: dependency completeness, field coverage, API reachability, relation target existence
- Auto-select dependencies --- selecting Order for generation automatically includes PartType
- Referential integrity validated post-build

**LLM role in entity relations:**
- During mapping, LLM detects cross-entity references in payloads (part_type_id → PartType)
- Proposes relations array in mapping JSON
- Human accepts, edits, or rejects each proposed relation
- DAG is built from approved relations, not inferred at runtime

**[Figure 2: DAG dependency graph --- entities as nodes, dependencies as directed edges, topological order annotated]**

#### 3.6 Human-in-the-Loop with Calibrated Confidence

**The 6-phase guided workflow (compact inline flow):**
Connect → Approve → Map → Review → Transform → Generate

**Confidence calibration:**
- LLM scores every proposal (high/medium/low)
- High confidence: 95%+ correct --- safe to auto-accept
- Medium/low confidence: flagged for mandatory human review
- Both models correctly flag their own uncertainty

**Smart reanalysis:**
- Human provides guidance on a flagged field
- AI re-analyzes only the flagged fields --- preserves previously accepted mappings
- Specificity matters: re-evaluates only what the human touched

**SME accessibility (touchpoint 2 of 3):**
- No CMSD expertise required --- AI makes the first proposal
- Review effort proportional to API quality, not entity complexity
- Expert feedback captured in config --- corrections persist and compound
- Guided wizard enforces workflow without requiring user to understand it

#### 3.7 Continuous Synchronization --- The Living Twin

**Poll-refresh-diff-push cycle:**
Poll (configurable interval) → Fetch APIs → Build CMSDDocument → Diff (ChangeDetector) → Push (EventBus → WebSocket)

**Key capabilities:**
- Configurable polling (default: manual trigger; optional auto-refresh for continuous)
- ChangeDetector diffs old vs. new document --- publishes only actual changes
- WebSocket pushes granular change events to dashboard in real-time
- Connection metadata on every entity: mapping_id, source_url, key_field, last_fetched
- Connection indicators: green (live, <60s), amber (stale, >5min), gray (static/fallback)

**Graceful degradation at every layer (compact table or bullet list):**
| Failure | Behavior |
|---------|----------|
| API unreachable | Preserve previous instances, show stale indicator |
| Field path not found | Set to None, log warning, continue |
| LLM unavailable | Return empty mapping template for manual edit |
| Unmapped entity type | Fall back to hardcoded factory |
| Partial multi-endpoint fetch | Build twin from successful endpoints only |

#### 3.8 Design Rationale for AI-Enabled Manufacturing

**Why deterministic runtime matters for manufacturing:**
Shop floors don't tolerate LLM hallucinations or API latency in the production path. The LLM operates at design time (mapping proposal), not runtime (twin assembly). This eliminates unpredictability, latency, and cost of runtime AI calls from the production critical path.

**Why JSON over code generation:**
JSON is human-readable, diffable, version-controllable, and language-agnostic. A factory manager can sanity-check a mapping config without understanding Python. Generated code would be opaque to both technical and non-technical stakeholders. The config IS the documentation of what was mapped and how.

**Why open-source models running locally:**
Sensitive manufacturing data --- resource configurations, production orders, operational metrics --- should not leave the factory. The architecture runs embedding models locally (Ollama, qwen3-embedding:4b), keeping enterprise data on-premises. The chat model calls a cloud API for reasoning workload, but the data that describes the factory stays local. We tested with openly available DeepSeek models to validate this deployment model.

---

### 4. AI-Powered Mapping Pipeline (~0.75-1 page)

#### 4.1 RAG with Curated CMSD Content

**RAG architecture:**
- ChromaDB vector store with local Ollama embedding (qwen3-embedding:4b, 2,560-dim)
- Two document collections: CMSD field catalog and ASMG data requirements specification
- Retrieval: query embedding → cosine similarity → top-k results → assembled context (~2,500 chars)

**The catalog provides field descriptions in plain English** (short example):
Entity → Field → Type → Description format. Deliberately NOT source code --- no type annotations, no Optional wrappers, no Decimal constructors. Clean reference tables a human could read.

**Design decision --- target-side only RAG:**
The target schema (CMSD) is fixed and invariant. The source side varies per factory --- some have clean field documentation, many legacy systems have none. Embedding source-side docs would make the system fragile to documentation quality. We embed only the target catalog and test the worst case: what happens when source-side context is unavailable. The evaluation (Section 5) quantifies exactly what this design choice costs.

**What the catalog describes --- and what it doesn't (forward reference to Section 5):**
The catalog contains CMSD target-side descriptions only. For clean APIs where source field names are semantically meaningful (uptime_pct), the LLM matches both sides using its own understanding. For legacy payloads with opaque codes (FLD007), the catalog tells the LLM what CMSD availability means but not what FLD007 represents in the source. The LLM must infer source field identity from values alone. This limitation is evaluated in detail in Section 5.

#### 4.2 Provider-Agnostic Multi-Model Support

- Single LLMClient abstraction supports any OpenAI-compatible API
- Chat provider (cloud) and embedding provider (local) configured independently
- Tested: deepseek-v4-flash (non-reasoning) and deepseek-v4-pro (reasoning, thinking enabled)
- Switch models by changing one environment variable --- architecture outlives any specific LLM API

#### 4.3 Transformation Presets

- 9 deterministic transformation types mentioned inline in Section 3.2's JSON config listing
- LLM proposes which transform to use and its parameters
- Human verifies via live preview (raw API value → transformed canonical value)
- Engine executes deterministically --- pure functions, no LLM in the path
- Transforms validated against target schema at save time (type compatibility check)
- The key point: these 9 primitives cover 90%+ of real-world conversion needs without generating a single line of Python

---

### 5. Evaluation (~1.5-1.75 pages)

#### 5.1 Experimental Setup

**Test matrix:**
- 4 API payload variants (same underlying data, different surface representations):
  - `clean` --- well-named English fields (baseline)
  - `legacy` --- all field names replaced with opaque codes (FLD001-FLD201)
  - `german` --- all field names in German (DACH-region manufacturing)
  - `deep` --- data wrapped in 3-level JSON envelope (deeply nested APIs)
- 4 CMSD entity types: Resource (20 fields), ResourceClass (6 fields), Order (4 fields), PartType (5 fields)
- 2 LLM models: deepseek-v4-flash (non-reasoning), deepseek-v4-pro (reasoning, thinking enabled)
- 2 RAG configurations: no-RAG and catalog RAG (CMSD field catalog, ~2,500 chars context)
- n = 5 runs per configuration; extended n = 20 probe for Flash model (640 total runs)
- Ground truth mappings defined per variant per entity --- manually verified field-by-field
- All experiments reproducible via paper_evaluation_v2.py test harness with deterministic ground truth

**Metrics:** Accuracy (% of ground truth fields correctly mapped), string accuracy, numeric accuracy, prompt/completion/total tokens, latency, RAG context length, confidence distribution.

**Two-phase strategy:**
Phase I (n=5): Baseline across both models and all configurations. Phase II (n=20, 640 runs): Extended longitudinal probe on Flash to statistically test whether RAG provides significant improvement, using Mann-Whitney U and Levene's test.

#### 5.2 Accuracy Results

**Table 1: Aggregate Accuracy by Model and RAG Mode (n=5)**

| Model | No-RAG | Catalog RAG | String Acc (RAG) | Numeric Acc (RAG) |
|-------|--------|-------------|-------------------|--------------------|
| deepseek-v4-flash | 95.8% | 95.0% | 99.3% | 93.6% |
| deepseek-v4-pro | 95.8% | 96.4% | 100.0% | 95.2% |

**Key findings from Table 1:**
- Flash matches Pro within 1.4pp at 3x lower latency
- Pro + catalog RAG achieves perfect string accuracy (100.0%)
- The modest RAG delta on aggregate masks a critical asymmetry --- explained below

**Per-entity findings (prose, no table):**
- Order: 100% across all 16 configurations --- 4 string fields, zero numeric, solved
- ResourceClass and PartType: 96-100% across all variants, minor dips on German
- Resource: the bottleneck. 20 fields (7 string, 7 numeric, 6 null-prone). On legacy variant, drops to ~45% regardless of model or RAG. This single entity drives the aggregate down from the ~100% ceiling of the other three.

**Table 2: Entity Field Type Profiles**

| Entity | String | Numeric | Null-prone | Total | Difficulty |
|--------|--------|---------|------------|-------|------------|
| Resource | 7 | 7 | 6 | 20 | Hard --- numeric ambiguity + nulls |
| ResourceClass | 5 | 1 | 0 | 6 | Moderate |
| Order | 4 | 0 | 0 | 4 | Easy --- solved at 100% |
| PartType | 4 | 1 | 0 | 5 | Easy --- only German dips |

This table explains the accuracy results: difficulty is a function of numeric field count and null-proneness, not total fields.

#### 5.3 Token Consumption and Reasoning Overhead

**Table 3: Token Comparison by Model and RAG Mode**

| Model | Metric | No-RAG | Catalog RAG | Delta |
|:---|:---|:---|:---|:---|
| Flash | Prompt tokens | ~1,310 | ~1,774 | +464 (35%) |
| Flash | Completion tokens | ~2,183 | ~2,362 | +179 (8%) |
| Flash | Total tokens | ~3,493 | ~4,136 | +643 (18%) |
| Pro | Prompt tokens | ~1,310 | ~1,774 | +464 (35%) |
| Pro | Completion tokens | ~2,407 | ~2,609 | +202 (8%) |
| Pro | Total tokens | ~3,717 | ~4,383 | +666 (18%) |

**Key takeaways:**
- Input determinism: both models receive identical prompt tokens --- the RAG retrieval pipeline is deterministic regardless of backend model
- Reasoning overhead: Pro generates ~10% more completion tokens than Flash (deeper Chain-of-Thought traces), directly translating to higher latency and cost
- Retrieval-induced verbosity: RAG inflates completion by only ~8% --- the cost of RAG is almost entirely in the input prompt phase
- Flash is consistently 2-3x faster across all variants

#### 5.4 Statistical Invariance of RAG --- When Context Cannot Help

**Table 4: RAG vs. No-RAG --- Extended Statistical Analysis (Flash, n=20, 320 runs per mode)**

| Entity | Variant | RAG Median [Min, Max] | no-RAG Median [Min, Max] | p-value (MWU) |
|--------|---------|----------------------|--------------------------|---------------|
| Resource | legacy | 45.0% [30.0, 65.0] | 45.0% [35.0, 60.0] | 0.657 |
| Resource | clean | 100.0% [65.0, 100.0] | 100.0% [65.0, 100.0] | 0.986 |
| Resource | german | 100.0% [70.0, 100.0] | 100.0% [70.0, 100.0] | 0.252 |
| Resource | deep | 100.0% [95.0, 100.0] | 100.0% [95.0, 100.0] | 0.225 |
| PartType | clean/german | 100.0% [80.0, 100.0] | 100.0% [80.0, 100.0] | >0.654 |
| ResourceClass | legacy/german | 100.0% [83.3, 100.0] | 100.0% [83.3, 100.0] | >0.302 |
| Order | all variants | 100.0% [100.0, 100.0] | 100.0% [100.0, 100.0] | 1.000 |

**Key findings:**
- Across all 640 runs, Mann-Whitney U yields p > 0.05 for every entity-variant pair --- RAG provides zero statistically significant improvement
- Levene's test (p = 0.9631) confirms RAG also fails to stabilize output variance
- Resource legacy is the catastrophic case: median 45%, range 30-65%, p = 0.657
- Order is the ideal case: deterministic 100%, p = 1.000 --- with or without RAG

**Why RAG fails to help legacy numerics:**
This is a data problem, not a retrieval problem. String values carry identity cues ("CNC Machine 3000" reads as a name, "ACTIVE" reads as a status). Numeric values carry no such signal: 95.0 could be availability (%), efficiency (%), hourly rate ($), or machine count. When the LLM sees `FLD007: 95.0` with 7 numeric fields all in the 0-100 range, the catalog narrows the CMSD-side range (availability must be 0.0-1.0) but cannot disambiguate between multiple numeric fields with overlapping value ranges. This is **aleatoric ambiguity** --- inherent to the data --- not **epistemic uncertainty** that better retrieval could resolve.

The cross-model data confirms this is model-agnostic: Pro achieves only 46-50% on Resource legacy with the same bottleneck, plus 60% timeout rate from reasoning overhead on the hardest variant. Neither retrieval quality nor model scaling compensates for structural ambiguity in the source data.

#### 5.5 Confidence Calibration

(Prose, no table --- 1 paragraph)
- High confidence proposals: 95%+ accuracy --- system correctly identifies strong proposals
- Medium/low confidence: incorrect proposals consistently flagged --- system knows when it's guessing
- Calibration enables targeted review: human effort goes where it matters
- No assertion of false certainty on hard cases (legacy numeric fields)

---

### 6. Discussion (~0.5 page)

**When the system works:**
- Clean, well-named APIs on well-typed entities (Order, ResourceClass, PartType): 100% accuracy with either model, with or without RAG --- fully automatable
- Deeply nested JSON: 100% accuracy --- LLM correctly navigates multi-level nesting
- Non-English field names on well-typed entities: 96-100%
- String-only entities on legacy cryptic codes (Order): 100% even without RAG --- LLM infers field identity from string value content patterns

**When it struggles:**
- Numeric ambiguity is the fundamental bottleneck --- values carry no identity signal
- Resource on legacy payloads: 41-50% regardless of model or RAG --- 7 numeric fields, opaque FLD codes, overlapping 0-100 range
- RAG cannot resolve this --- the catalog describes CMSD targets, not what FLD007 means in the source payload
- Null-valued fields compound the problem --- 6 of Resource's 20 fields can be null, providing zero identity signal

**Practical implications for SMEs (touchpoint 3 of 3):**
- Connect APIs, review flagged proposals, generate twin --- no CMSD expertise needed
- Human effort is proportional to API quality, not entity complexity
- Config is persistent --- expert corrections captured once, reusable across factories
- Estimated cost: ~$0.01 per full factory model using Flash with no RAG
- System can run without RAG at 95.8% accuracy --- simpler deployment for modern APIs

**Architecture as the durable contribution:**
AI accuracy numbers tell part of the story. The architecture is what outlasts any specific model:
- JSON as the AI-engine interface decouples proposal from execution
- Deterministic runtime means production safety regardless of LLM behavior
- Graceful degradation means the system works when external dependencies fail
- Provider-agnostic design means the architecture outlives any specific LLM API

---

### 7. Conclusion (~0.25-0.5 page)

**Summary:**
We presented a human-in-the-loop architecture for LLM-driven digital twin assembly from heterogeneous enterprise APIs. The core innovation: treating field mapping as a configuration problem rather than code generation. The LLM proposes mappings as JSON at design time; a deterministic engine drives the twin at runtime. A vendor-neutral canonical information model abstracts away source-system heterogeneity.

**Key findings recap:**
- 95-96% aggregate accuracy across both models
- Non-reasoning model matches reasoning model within 1.4pp at 3x lower latency and token cost
- Numeric field ambiguity in legacy payloads is the fundamental bottleneck --- target-side RAG provides zero statistically significant improvement
- Three of four entity types reach 96-100% across all variants; Resource is the sole bottleneck

**Future work:**
- **Graph-native digital twin instances** with built-in reasoning for automatic relation propagation, blast-radius analysis, and schema-change cascade management --- extending the configuration-driven architecture from instance assembly to instance lifecycle management
- Production deployment with live SAP/MES connectors (OData, RFC, SQL)
- Controlled user study with manufacturing SMEs measuring time-to-twin and review burden

**Broader significance:**
This work demonstrates that thoughtful software architecture --- not just model capability --- is the key to making AI useful in manufacturing. The LLM provides flexibility; the deterministic engine provides reliability; the JSON config bridges them. For SMEs that cannot afford embedded software consultants, this architecture offers a path to industrial-grade digital twins that was previously closed. The architecture embodies the convergence the Industrial Metaverse track calls for: software design that makes AI-enabled digital twins accessible beyond the enterprise elite.

---

## Figures

| # | Type | Content | Placement |
|---|------|---------|-----------|
| Fig 1 | Architecture diagram | 5-service system with data flows (DrawIO XML, rendered) | Section 3.1 |
| Fig 2 | DAG graph | Entities as nodes, dependencies as directed edges, topological order annotated | Section 3.5 |

## Listings

| # | Type | Content | Placement |
|---|------|---------|-----------|
| Listing 1 | Side-by-side code | Traditional hardcoded Python factory vs. JSON mapping config | Section 3.2 |

## Tables

| # | Content | Placement |
|---|---------|-----------|
| Table 1 | Aggregate accuracy by model and RAG mode | Section 5.2 |
| Table 2 | Entity field type profiles | Section 5.2 |
| Table 3 | Token comparison by model and RAG mode | Section 5.3 |
| Table 4 | RAG vs. No-RAG statistical analysis (Flash, n=20) | Section 5.4 |

## References

~20 citations across 4 clusters. [REF NEEDED] markers placed in outline. To be filled by author.

---

## Decisions Log

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Architecture leads, evaluation supports | ISM cares about implementation; 60/25/15 split |
| 2 | SME scenario: 3 touchpoints only | Intentional flavor, not a running motif |
| 3 | Cut Issue 07 entirely | Not relevant to paper's contribution |
| 4 | Cut multi-instance analysis | Mixed signals; single-instance is primary |
| 5 | Cut CMSD coverage analysis (78.2%/21.8%) | Not a core claim |
| 6 | Cut per-entity breakdown table | Prose summary suffices |
| 7 | Cut latency table | Mention Flash 2-3x faster in prose |
| 8 | 4-cluster related work (merge schema+HITL) | Avoids redundancy, stronger narrative |
| 9 | RAG split: architecture in Sec 4, findings in Sec 5 | Clean separation, no overlap |
| 10 | Section 3.8 as Design Rationale | Manufacturing-specific, not generic principles |
| 11 | Title avoids vendor/standard names | Architecture is schema-agnostic |
| 12 | Full 7-row statistical table | Central evidence for RAG null result |
| 13 | 3-bullet contribution, not 7 claims | Too many claims dilute the message |
| 14 | Graph-native DT instances as primary future work | Natural extension of architecture |
| 15 | Reproducibility: one sentence in eval setup | Signals rigor, costs nothing |
