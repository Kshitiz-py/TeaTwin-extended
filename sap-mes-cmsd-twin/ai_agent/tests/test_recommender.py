"""Deterministic tests for the EndpointRecommender (fakes injected — no chromadb/LLM).

Verifies:
  * Phase 1 retrieves candidates per CMSD field, filtered to source-schema + the
    requested source_id.
  * Phase 2 builds a prompt containing CMSD field names + retrieved source metadata
    (and no row data), then parses + normalizes the LLM output (count_path default,
    endpoint default, markdown-fence stripping, string-or-dict handling).
  * Unknown CMSD entity raises ValueError.
"""
import asyncio

import pytest

from ai_agent.recommender import EndpointRecommender


class FakeRetriever:
    def __init__(self, hits):
        self.hits = hits
        self.calls = []

    def retrieve(self, query, top_k=5, collections=None):
        self.calls.append({"query": query, "top_k": top_k, "collections": collections})
        return self.hits


class FakeLLM:
    def __init__(self, response):
        self.response = response
        self.last_prompt = None

    def chat_json(self, system_prompt, user_prompt, temperature=0.1):
        self.last_prompt = user_prompt
        return self.response


CATALOG = {"entities": {"Process": {
    "name": "Process",
    "description": "A process step in a routing",
    "fields": [
        {"name": "identifier", "type": "str", "required": True, "is_reference": False, "description": "Unique ID"},
        {"name": "duration", "type": "Optional[Duration]", "required": False, "is_reference": False, "description": "Process duration"},
    ],
    "references": [],
}}}

SOURCE_HITS = [
    {"metadata": {"collection": "source-schema", "source_id": "sap-a33p",
                  "entity_set": "ProductionRoutingOperation", "entity_type": "ProductionRoutingOperationType"},
     "content": "SAP OData EntitySet: ProductionRoutingOperation\nProperties:\n"
                "- Operation (Edm.String) — sap:label=\"Operation\"\n"
                "- StandardWorkQuantity1 (Edm.Decimal) — sap:label=\"Standard Work Quantity 1\", "
                "sap:unit=StandardWorkQuantityUnit1",
     "score": 0.91},
    {"metadata": {"collection": "source-schema", "source_id": "sap-a33p",
                  "entity_set": "WorkCenter", "entity_type": "WorkCenterType"},
     "content": "SAP OData EntitySet: WorkCenter\n- WorkCenter (Edm.String)",
     "score": 0.55},
]

LLM_RESPONSE = {
    "cmsd_entity": "Process",
    "covering_endpoints": [
        {"entity_set": "ProductionRoutingOperation", "endpoint": "/ProductionRoutingOperation",
         "role": "primary", "key_field": "Operation"},
    ],
    "field_attribution": {
        "identifier": {"entity_set": "ProductionRoutingOperation", "property": "Operation", "confidence": "high"},
        "duration": {"entity_set": "ProductionRoutingOperation", "property": "StandardWorkQuantity1",
                     "confidence": "high",
                     "unit_from_field": {"unit_path": "StandardWorkQuantityUnit1", "target_unit": "second"}},
    },
    "join_keys": [],
    "coverage_gaps": [],
    "proposed_relations": [],
    "notes": "Single endpoint covers both fields.",
}


def test_recommend_builds_prompt_from_metadata_and_parses_output():
    retriever = FakeRetriever(SOURCE_HITS)
    llm = FakeLLM(LLM_RESPONSE)
    rec = EndpointRecommender(retriever=retriever, catalog=CATALOG, llm_client=llm)
    result = asyncio.run(rec.recommend("sap-a33p", "Process"))

    # Phase 1: one retrieve() per CMSD field, all against the source-schema corpus
    assert len(retriever.calls) == 2
    assert all(c["collections"] == ["source-schema"] for c in retriever.calls)

    # Phase 2: the LLM prompt carries CMSD field names + retrieved source metadata
    assert "duration" in llm.last_prompt
    assert "ProductionRoutingOperation" in llm.last_prompt
    assert "StandardWorkQuantity1" in llm.last_prompt
    assert "sap:unit=StandardWorkQuantityUnit1" in llm.last_prompt

    # Output parsed + normalized (count_path default, endpoint preserved)
    assert result["cmsd_entity"] == "Process"
    assert result["covering_endpoints"][0]["count_path"] == "$.d.results"
    assert result["covering_endpoints"][0]["endpoint"] == "/ProductionRoutingOperation"
    assert result["field_attribution"]["duration"]["unit_from_field"]["unit_path"] == "StandardWorkQuantityUnit1"


def test_recommend_filters_other_sources():
    other = [{"metadata": {"collection": "source-schema", "source_id": "OTHER", "entity_set": "X"},
              "content": "y", "score": 0.9}]
    retriever = FakeRetriever(other)
    llm = FakeLLM({"covering_endpoints": [], "field_attribution": {},
                   "coverage_gaps": ["identifier", "duration"]})
    rec = EndpointRecommender(retriever=retriever, catalog=CATALOG, llm_client=llm)
    result = asyncio.run(rec.recommend("sap-a33p", "Process"))
    # No candidates for sap-a33p -> the prompt says so; the LLM's coverage_gaps pass through
    assert "no source-schema matches retrieved" in llm.last_prompt
    assert result["coverage_gaps"] == ["identifier", "duration"]


def test_recommend_parses_markdown_fenced_string():
    raw = '```json\n{"covering_endpoints":[{"entity_set":"ProductionRoutingOperation"}], '
    raw += '"field_attribution":{}, "coverage_gaps":[]}\n```'
    llm = FakeLLM(raw)
    rec = EndpointRecommender(retriever=FakeRetriever(SOURCE_HITS), catalog=CATALOG, llm_client=llm)
    result = asyncio.run(rec.recommend("sap-a33p", "Process"))
    assert result["covering_endpoints"][0]["entity_set"] == "ProductionRoutingOperation"
    # count_path + endpoint defaults applied during normalization
    assert result["covering_endpoints"][0]["count_path"] == "$.d.results"
    assert result["covering_endpoints"][0]["endpoint"] == "/ProductionRoutingOperation"


def test_recommend_unknown_entity_raises():
    rec = EndpointRecommender(retriever=FakeRetriever([]), catalog=CATALOG, llm_client=FakeLLM({}))
    with pytest.raises(ValueError):
        asyncio.run(rec.recommend("sap-a33p", "Nonexistent"))