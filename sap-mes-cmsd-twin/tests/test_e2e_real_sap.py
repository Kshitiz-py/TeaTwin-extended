"""End-to-end smoke for the SAP OData connector against a RUNNING Docker stack.

Gated: only runs when ``SAP_E2E=1`` is set AND SAP credentials are in the
environment. Otherwise the whole module is skipped, so normal ``pytest`` runs are
unaffected. Requires the stack up:
  - ai-agent on http://localhost:8003 (with an LLM/embedder connected via
    POST /api/agent/v1/agent/connect — the recommender + RAG need it)
  - cmsd-twin-service on http://localhost:8000
  - SAP_CRED_KEY set on the services (for encrypted creds at rest)

This smoke exercises the NEW SAP pieces deterministically where possible:
  POST /sources → POST /sources/{id}/discover → GET /sources/{id}/schema →
  POST /mapping/recommend-endpoints. The confirm → /refresh → /digital-twin/full
  leg (which needs the full map-UI flow) is covered in SAP_ODATA_RUNBOOK.md.

Run::

    SAP_E2E=1 SAP_BASE_URL=https://a33p.ucc.cloud/sap/opu/odata/sap/API_PRODUCTION_ROUTING \\
    SAP_CLIENT=200 SAP_USERNAME=... SAP_PASSWORD=... \\
    python -m pytest tests/test_e2e_real_sap.py -v -s
"""
import os

import pytest

if not os.getenv("SAP_E2E"):
    pytest.skip("Set SAP_E2E=1 to run the real-SAP E2E smoke", allow_module_level=True)

import httpx  # noqa: E402

AGENT = os.getenv("SAP_AGENT_URL", "http://localhost:8003")
SAP_BASE = os.getenv("SAP_BASE_URL", "https://a33p.ucc.cloud/sap/opu/odata/sap/API_PRODUCTION_ROUTING")
SAP_CLIENT = os.getenv("SAP_CLIENT", "200")
SAP_USER = os.getenv("SAP_USERNAME", "")
SAP_PASS = os.getenv("SAP_PASSWORD", "")

if not (SAP_USER and SAP_PASS):
    pytest.skip("SAP_USERNAME/SAP_PASSWORD env required for the real-SAP E2E smoke",
                allow_module_level=True)


@pytest.fixture(scope="module")
def source_id():
    # Health check + create a SAP source (plaintext creds held in-memory by the agent;
    # SAP_CRED_KEY is only needed for confirm-time encryption + persistence).
    with httpx.Client(base_url=AGENT, timeout=120) as c:
        r = c.get("/api/agent/v1/health")
        assert r.status_code == 200, f"ai-agent unreachable: {r.status_code} {r.text}"
        r = c.post("/api/agent/v1/sources", json={
            "name": "E2E SAP",
            "base_url": SAP_BASE,
            "auth_type": "basic",
            "username": SAP_USER,
            "password": SAP_PASS,
            "extra_headers": {"sap-client": SAP_CLIENT},
        })
        assert r.status_code == 200, r.text
        sid = r.json()["id"]
    yield sid
    try:
        with httpx.Client(base_url=AGENT, timeout=30) as c:
            c.delete(f"/api/agent/v1/sources/{sid}")
    except Exception:
        pass


def test_discover_indexes_source_schema(source_id):
    with httpx.Client(base_url=AGENT, timeout=240) as c:
        r = c.post(f"/api/agent/v1/sources/{source_id}/discover", json={"entity_set_filter": None})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["success"] is True
        assert len(data["entity_sets"]) > 0, "no entity sets discovered"
        assert data["chunks_indexed"] > 0, "no source-schema chunks indexed"
        names = [es["name"] for es in data["entity_sets"]]
        assert "ProductionRoutingOperation" in names, f"ProductionRoutingOperation not in {names}"


def test_get_schema_returns_metadata_only(source_id):
    with httpx.Client(base_url=AGENT, timeout=60) as c:
        r = c.get(f"/api/agent/v1/sources/{source_id}/schema")
        assert r.status_code == 200, r.text
        schema = r.json()["source_schema"]
        assert schema["entity_types"], "no entity types in persisted schema"
        # Security: the schema response is metadata only — no row-data markers, no creds
        assert "d.results" not in r.text
        assert SAP_PASS not in r.text, "credentials leaked into the schema response"
        assert SAP_USER not in r.text, "username leaked into the schema response"


def test_recommend_endpoints_returns_covering_set(source_id):
    with httpx.Client(base_url=AGENT, timeout=120) as c:
        st = c.get("/api/agent/v1/agent/status").json()
        if not st.get("connected"):
            pytest.skip("LLM provider not connected — POST /agent/connect first")
        r = c.post("/api/agent/v1/mapping/recommend-endpoints",
                   json={"source_id": source_id, "cmsd_entity": "Process"})
        assert r.status_code == 200, r.text
        rec = r.json()
        assert rec["cmsd_entity"] == "Process"
        assert isinstance(rec["covering_endpoints"], list)
        assert isinstance(rec["field_attribution"], dict)
        assert isinstance(rec["coverage_gaps"], list)
        # Security: no credentials in the recommendation response
        assert SAP_PASS not in r.text