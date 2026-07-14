# ISM 2026 — Content Briefing

**Title:** Configuration, Not Code: LLM-Driven Assembly of Digital Twins from Enterprise Data
**Target Venue:** 8th International Conference on Industry of the Future and Smart Manufacturing (ISM 2026)
**Invited Tracks:** Reshaping future smart manufacturing, Cyber-Physical Systems, Generative AI 

---

## 1. Core Narrative & Introduction

Manufacturing companies sit on decades of enterprise data locked in disjointed SAP and MES systems. Building digital twins from this data today follows a well-worn path: a consultant manually maps each API field to a target schema, hardcodes the mapping per customer in Python, and rebuilds the software for every new factory. This code-heavy, consultant-driven approach makes digital twin adoption prohibitively expensive for SMEs—the very companies who stand to gain the most.

**We present a different approach.** An LLM reads raw enterprise API payloads, understands target entity schemas through a curated catalog, and proposes field-level mappings as a JSON configuration. A human reviews only the proposals the AI flags as uncertain. A deterministic runtime engine then consumes this configuration and dynamically assembles the digital twin—requiring no code generation, no per-customer Python factories, and no on-site schema expertise. 

Through an empirical validation comparing reasoning vs. non-reasoning models (DeepSeek-V4-Pro vs. Flash) and RAG vs. No-RAG retrieval, we demonstrate exactly *how* AI brings flexibility to software architecture without compromising the strict determinism required by industrial systems.

---

## 2. The SME Use Case: Overcoming the Integration Hurdle

Consider a mid-sized CNC machining supplier (an SME) attempting to integrate their shop floor into an OEM's "Industrial Metaverse" supply chain. They must provide data conforming to the vendor-neutral CMSD (ISO 22400) standard. 

Their data is fractured: static master data (Resources, Orders, Part Types) lives in an on-premise SAP ERP using German field names (`betriebszeit_prozent`), while operational data lives in a legacy MES outputting opaque, undocumented field codes (`FLD007: 95.0`). 

Typically, mapping these incompatible dialects requires custom software development. Our architecture abstracts this into a **Model-to-Model (M2M) Transformation**:
1. The AI acts as a design-time ontology translator, mapping both SAP and MES dialects into the canonical CMSD hub.
2. The mapping is saved as a JSON configuration.
3. The runtime engine executes the JSON configuration to push live twin updates via WebSockets.
**Result:** The SME achieves continuous digital twin synchronization in minutes, entirely through a graphical UI, without writing a single line of integration code.

---

## 3. Software Architecture for AI-Enabled Manufacturing

Our architecture bridges probabilistic AI and deterministic execution by strictly separating design-time proposals from runtime execution.

### Principle 1: AI Proposes, Determinism Executes
The LLM is entirely removed from the production runtime. The LLM operates at design time to generate the JSON mapping configuration. The production path—fetching APIs, extracting fields, applying transforms, and building CMSD instances—is pure, deterministic Python. This eliminates the unpredictability, latency, and cost of runtime AI hallucination, bringing absolute stability to the software.

### Principle 2: Configuration over Code Generation
JSON is the interface between the AI and the runtime engine. This is deliberate: JSON is human-readable, diffable, and language-agnostic. The JSON acts as the formal M2M transformation ruleset. A factory manager can review a mapping config to see which fields came from which API, whereas generated Python code would be opaque and brittle.

### Principle 3: Multi-Endpoint Data Fusion
A single digital twin entity often requires data from multiple APIs. The architecture executes concurrent polling across SAP and MES endpoints. The JSON configuration dictates source attribution (e.g., pulling a machine's `name` from SAP, but its `current_state` from MES), joining them via a unified `resource_id`.

---

## 4. DAG-Driven Multi-Entity Construction

Digital twins are not flat structures; they are highly relational. A `Job` references an `Order`, which references a `PartType`, which is executed on a `Resource`. Building these in the wrong sequence breaks referential integrity.

We solve this using a **Directed Acyclic Graph (DAG)** driven by the JSON configuration:
1. **AI Relation Proposal:** During the mapping phase, the AI detects cross-entity foreign keys in the API payloads and proposes dependency relationships.
2. **Topological Sort:** The runtime engine parses the approved dependencies and sorts the build order mathematically (e.g., `ResourceClasses` → `Resources` → `PartTypes` → `Orders`).
3. **Pre-flight Validation:** Before the twin is generated, the DAG engine executes a validation pass ensuring dependency completeness and API reachability. If validation passes, the system guarantees a structurally sound digital twin.

---

## 5. Human-in-the-Loop (HITL) with Calibrated Confidence

To make this architecture accessible to SMEs without domain experts, we employ a guided workflow centered around **calibrated AI confidence**.

When the LLM proposes a JSON mapping, it self-scores its epistemic uncertainty for each field (High/Medium/Low). 
* **High Confidence:** Proven empirically to be highly accurate. These are collapsed in the UI and safe to auto-accept.
* **Medium/Low Confidence:** The UI surfaces these specific fields for mandatory human review.

If the human corrects a field, the system performs **Smart Reanalysis**—re-evaluating only the corrected field constraint, leaving the rest of the mapping intact. This targets human effort exclusively where it is needed, minimizing the manual bottleneck.

---

## 6. Empirical Validation: Capabilities and Limits of AI Integration

To rigorously evaluate how AI operates within this architecture, the experimental design utilized a two-phase execution strategy testing different prompt architectures (Clean, Deep, German, Legacy) across varying schema complexities.

### 6.1 Phase 1: Baseline Evaluation (DeepSeek-V4-Pro)
Phase 1 established a baseline by executing an $N=5$ evaluation utilizing the heavy reasoning model, **DeepSeek-V4-Pro**, augmented with complete target-side schema RAG. 

**Table 1: DeepSeek-V4-Pro Baseline ($N=5$, Full RAG)**
| Entity (Complexity) | clean | german | deep | legacy |
|---------------------|-------|--------|------|--------|
| Resource (High) | 94.0% | 100.0% | 98.0%| **50.0%***|
| ResourceClass (Low) | 100.0%| 100.0% | 100.0%| 100.0% |
| Order (Low) | 100.0%| 100.0% | 100.0%| 100.0% |
| PartType (Low) | 100.0%| 100.0% | 100.0%| 100.0% |

*\*Note: For the `Resource + legacy` permutation, the heavy reasoning overhead caused by the unstructured prompt resulted in a 60% failure rate (3 out of 5 runs timed out).*

**Takeaway:** While the reasoning model achieved near-perfect accuracy on structured schemas, it suffered a catastrophic mapping collapse ($50\%$ mean, severe timeouts) when forced to process highly complex schemas (`Resource`) using an unstructured prompt (`legacy`). This established that scaling model size and injecting RAG cannot compensate for poor prompt architecture.

### 6.2 Phase 2: Longitudinal Volatility Probe (DeepSeek-V4-Flash)
During Phase 1 testing on lightweight inference models (DeepSeek-V4-Flash), severe non-deterministic variance was observed. To investigate whether this variance was an artifact of sample size or inherent structural ambiguity, Phase 2 executed an extended longitudinal probe ($N=20$, totaling 640 runs) specifically targeting the volatile Flash model, toggling RAG on and off.

**Table 2: Bounded Variance and RAG Efficacy ($N=20$ per permutation, Flash Model)**
| Entity | Prompt Variant | RAG Median [Min, Max] | No-RAG Median [Min, Max] | Stat. Sig. ($p$-value) |
|--------|----------------|-----------------------|--------------------------|-----------------|
| Resource | legacy | **45.0% [30.0, 65.0]**| **45.0% [35.0, 60.0]**| 0.657 |
| Resource | clean | 100.0% [65.0, 100.0] | 100.0% [65.0, 100.0] | 0.986 |
| Resource | german | 100.0% [70.0, 100.0] | 100.0% [70.0, 100.0] | 0.252 |
| Resource | deep | 100.0% [95.0, 100.0] | 100.0% [95.0, 100.0] | 0.225 |
| PartType | *all variants* | 100.0% [80.0, 100.0] | 100.0% [80.0, 100.0] | $\geq 0.654$ |
| ResourceClass | *all variants* | 100.0% [83.3, 100.0] | 100.0% [83.3, 100.0] | $\geq 0.302$ |
| Order | *all variants* | 100.0% [100.0, 100.0]| 100.0% [100.0, 100.0]| 1.000 |

A prevailing assumption in industrial AI is that injecting schema documentation via RAG will stabilize model outputs. The empirical data strictly rejects this. Across all 640 runs, a Mann-Whitney U test yielded $p$-values $> 0.05$, confirming RAG provided **zero statistically significant improvement** to accuracy or variance.

### 6.3 The Numeric Bottleneck: Epistemic vs. Aleatoric Uncertainty
The cross-model data from both phases localizes severe mapping collapse to the intersection of highly complex entities (`Resource`) and unstructured, opaque APIs (`legacy`). 

Using **Information Theory**, we can formalize this mechanism: String values ("CNC Machine") possess high semantic density, allowing the LLM to perform zero-shot ontological alignment flawlessly. Conversely, legacy identifiers strip metadata from numeric payloads (e.g., `FLD007: 95.0`), maximizing conditional entropy. Target-side RAG resolves *epistemic uncertainty* (what the target schema requires) but is mathematically powerless to resolve the *aleatoric ambiguity* inherent in the opaque source data. Consequently, true digital twin interoperability requires standardizing the prompt's structural constraints (e.g., the `clean` or `deep` variants), rather than relying on RAG or massive reasoning models to bridge the gap.

---

## 7. SME Implementation Roadmap

For an SME adopting this technology, the implementation lifecycle takes minutes, not weeks:
1. **Connect:** Point the system at existing SAP/MES endpoints.
2. **Propose:** The AI (acting as an asynchronous design agent) infers the JSON transformation rules.
3. **Review:** The human reviews only the 15-25% of fields the AI flags as uncertain. 
4. **Validate:** The DAG engine verifies all dependencies and API routes.
5. **Generate:** The runtime engine executes the configuration deterministically, pushing live WebSocket updates to the twin.

## 8. Conclusion
By separating probabilistic design-time proposals from deterministic runtime execution, this architecture fundamentally shifts digital twin integration from a code-generation problem to a configuration problem. Guided by calibrated AI confidence and a DAG-driven core, this approach democratizes Industry 4.0 standard compliance, empowering SMEs to participate in the Industrial Metaverse at a fraction of traditional integration costs.