"""Endpoint recommender — proposes a covering set of SAP OData endpoints per CMSD entity.

Two phases:
  Phase 1 (deterministic, no LLM): for each CMSD field, retrieve candidate SAP source
    properties from the ``source-schema`` RAG corpus (vector match: CMSD field
    description vs ``sap:label``/type). Only metadata is retrieved — never row data.
  Phase 2 (LLM-over-RAG): assemble a COVERING SET of OData endpoints with per-field
    attribution, join keys (from navigation-property referential constraints),
    coverage gaps, and proposed ``relations[]``.

The LLM sees METADATA ONLY (retrieved source-schema chunks + the CMSD catalog). It never
connects to SAP, never receives credentials, and never sees row data.

Dependencies (retriever / cmsd_catalog / llm_client) are injected for testability and
lazy-loaded from the real singletons only when not provided, so importing this module is
cheap and does not require chromadb / an LLM provider.
"""
from __future__ import annotations

import json
import logging

logger = logging.getLogger("ai-agent.recommender")


COVERING_SET_SYSTEM_PROMPT = """You are an expert manufacturing data integration architect.

Given a CMSD (ISO 22400) entity and the METADATA of available SAP OData entity sets
(entity/property names, sap:label, types, keys, navigation properties — retrieved from
the OData $metadata document), propose a COVERING SET of OData endpoints that together
supply the CMSD entity's fields. A single CMSD entity's attributes may be scattered
across multiple OData entity sets — your covering set must span all of them.

SECURITY: You see METADATA ONLY. You have NO access to SAP, NO credentials, and NO row
data. Never attempt to connect to SAP or request data.

Rules:
1. For each CMSD field, attribute which OData entity set + property supplies it, with a
   confidence: high | medium | low.
2. If a CMSD field has no source across any entity set, list it in coverage_gaps.
3. Where two endpoints must be joined, give the join keys (from the navigation properties'
   referential constraints: "this.<prop> = target.<prop>").
4. Propose cross-entity relations[] for CMSD reference fields, with a cmsd_path, target
   entity, and match_key (source.api_path + target.field).
5. For any source property that has a sap:unit companion (the metadata shows
   "sap:unit=<companion_property>"), propose unit_from_field {unit_path, target_unit:"second"}
   on that field's attribution — do NOT propose a transformation or compute a factor. The
   runtime resolves the factor deterministically from the SAP unit code.
6. Each covering endpoint's count_path is "$.d.results" (SAP OData v2 convention) and its
   endpoint is "/<EntitySetName>".

Output ONLY a JSON object with this shape:
{
  "cmsd_entity": "...",
  "covering_endpoints": [
    {"entity_set": "...", "endpoint": "/EntitySetName", "role": "primary"|"secondary",
     "key_field": "...", "count_path": "$.d.results"}
  ],
  "field_attribution": {
    "cmsd_field": {"entity_set": "...", "property": "PropertyName", "confidence": "high|medium|low",
                   "transform": "optional transform type",
                   "unit_from_field": {"unit_path": "companion_property", "target_unit": "second"}}
  },
  "join_keys": [
    {"from": {"entity_set": "...", "property": "..."}, "to": {"entity_set": "...", "property": "..."}, "via_nav": "..."}
  ],
  "coverage_gaps": ["cmsd_field", "..."],
  "proposed_relations": [
    {"cmsd_path": "...", "target_entity": "...",
     "match_key": {"source": {"api_path": "..."}, "target": {"field": "identifier"}}, "confidence": "high|medium"}
  ],
  "notes": "..."
}
IMPORTANT: Output ONLY the JSON object. No markdown, no explanation.
"""


class EndpointRecommender:
    """Recommends a covering set of SAP OData endpoints for a CMSD entity."""

    def __init__(self, retriever=None, catalog: dict | None = None, llm_client=None):
        self._retriever = retriever
        self._catalog = catalog
        self._llm = llm_client

    # ── lazy singleton accessors (only used when not injected) ─────────────
    def _get_retriever(self):
        if self._retriever is None:
            from .rag.retriever import retriever as r
            self._retriever = r
        return self._retriever

    def _get_catalog(self) -> dict:
        if self._catalog is None:
            from .cmsd_catalog import get_catalog
            self._catalog = get_catalog()
        return self._catalog

    def _get_llm(self):
        if self._llm is None:
            from .llm import llm_client
            self._llm = llm_client
        return self._llm

    # ── main entrypoint ────────────────────────────────────────────────────
    async def recommend(self, source_id: str, cmsd_entity: str) -> dict:
        catalog = self._get_catalog()
        entity_meta = catalog.get("entities", {}).get(cmsd_entity)
        if not entity_meta:
            raise ValueError(f"Unknown CMSD entity: {cmsd_entity}")

        fields = entity_meta.get("fields", [])

        # Phase 1 — deterministic candidate retrieval per CMSD field (metadata only)
        retriever = self._get_retriever()
        candidates: dict[str, list[dict]] = {}
        for field in fields:
            q = (
                f"{field.get('name', '')} {field.get('description', '')} "
                f"{field.get('type', '')} SAP OData source field"
            )
            hits = retriever.retrieve(q, top_k=5, collections=["source-schema"])
            candidates[field.get("name", "")] = self._hits_for_source(hits, source_id)

        # Phase 2 — LLM-over-RAG assembly (metadata only)
        user_prompt = self._build_user_prompt(cmsd_entity, entity_meta, candidates)
        llm = self._get_llm()
        raw = llm.chat_json(
            system_prompt=COVERING_SET_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,
        )
        return self._parse_recommendation(raw, cmsd_entity)

    # ── helpers ───────────────────────────────────────────────────────────
    @staticmethod
    def _hits_for_source(hits: list[dict], source_id: str) -> list[dict]:
        """Keep only source-schema chunks belonging to the requested source."""
        out: list[dict] = []
        for h in hits or []:
            meta = h.get("metadata", {}) or {}
            if meta.get("collection") != "source-schema":
                continue
            if source_id and meta.get("source_id") != source_id:
                continue
            out.append({
                "entity_set": meta.get("entity_set", ""),
                "entity_type": meta.get("entity_type", ""),
                "score": round(float(h.get("score", 0.0)), 3),
                "content": (h.get("content") or "")[:700],
            })
        return out

    def _build_user_prompt(self, cmsd_entity: str, entity_meta: dict,
                           candidates: dict[str, list[dict]]) -> str:
        parts = [
            f"## Target CMSD Entity: {cmsd_entity}",
            f"## Description: {entity_meta.get('description', '')}",
            "## CMSD fields to cover:",
        ]
        for f in entity_meta.get("fields", []):
            ref = " [reference]" if f.get("is_reference") else ""
            parts.append(f"- {f.get('name', '')} ({f.get('type', '')}){ref}: {f.get('description', '')}")
        parts.append("")
        parts.append("## Available SAP OData source properties (METADATA ONLY — no row data):")
        for fname, hits in candidates.items():
            parts.append(f"### Candidates for CMSD field '{fname}':")
            if not hits:
                parts.append("  (no source-schema matches retrieved)")
                continue
            for h in hits[:3]:
                parts.append(f"- EntitySet {h['entity_set']} (score {h['score']}):")
                parts.append(f"  {h['content']}")
        parts.append("")
        parts.append("Propose the covering set of OData endpoints for this CMSD entity. "
                     "Output ONLY the JSON object.")
        return "\n".join(parts)

    def _parse_recommendation(self, raw, cmsd_entity: str) -> dict:
        if isinstance(raw, dict):
            rec = raw
        else:
            text = str(raw)
            if "```" in text:
                segments = text.split("```")
                if len(segments) >= 3:
                    text = segments[1]
                if text.lstrip().lower().startswith(("json", "javascript")):
                    text = text.lstrip().split("\n", 1)[-1]
            start, end = text.find("{"), text.rfind("}")
            if start >= 0 and end > start:
                text = text[start:end + 1]
            rec = json.loads(text)
        # Normalize: every covering endpoint gets the OData v2 count_path + endpoint defaults
        for ep in rec.get("covering_endpoints", []) or []:
            if isinstance(ep, dict):
                ep.setdefault("count_path", "$.d.results")
                if not ep.get("endpoint") and ep.get("entity_set"):
                    ep["endpoint"] = f"/{ep['entity_set']}"
        rec.setdefault("cmsd_entity", cmsd_entity)
        return rec


# Singleton (uses the real retriever/catalog/llm_client lazily when called)
endpoint_recommender = EndpointRecommender()