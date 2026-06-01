"""Check if API docs appear in the actual RAG context during mapping."""
import httpx, json, os

fixtures = os.path.join(os.path.dirname(__file__), "fixtures", "variants", "legacy", "Resource.json")
with open(fixtures) as f:
    payload = json.load(f)
resource = payload["resources"][0]

body = {
    "data_point_name": "Legacy Test",
    "cmsd_entity": "Resource",
    "approved_payloads": [{
        "endpoint": "/legacy/r",
        "source_id": "legacy",
        "label": "Legacy",
        "raw_payload": resource,
    }],
}
r = httpx.post("http://localhost:8003/api/agent/v1/mapping/analyze", json=body, timeout=120)
rag = r.json().get("rag_context", "")
print(f"RAG length: {len(rag)} chars")

idx = rag.find("### API Documentation")
if idx >= 0:
    print(f"FOUND at position {idx}:")
    print(rag[idx:idx+1000])
else:
    print("API Documentation section NOT FOUND in RAG context")
    print()
    print("Last 1000 chars of RAG:")
    print(rag[-1000:])
