"""Quick test: run one experiment with better output."""
import json, os, httpx

fixtures = os.path.join(os.path.dirname(__file__), "fixtures", "variants", "clean", "Resource.json")
with open(fixtures) as f:
    payload = json.load(f)
resource = payload["resources"][0]

body = {
    "data_point_name": "Test: Resource (clean)",
    "cmsd_entity": "Resource",
    "approved_payloads": [{
        "endpoint": "/resources",
        "source_id": "test",
        "label": "Clean Resource",
        "raw_payload": resource,
    }],
}
print("Sending to ai-agent...")
r = httpx.post("http://localhost:8003/api/agent/v1/mapping/analyze", json=body, timeout=120)
d = r.json()
mapping = d.get("mapping", {})
inner = mapping.get("mapping", {})

if inner and isinstance(inner, dict) and len(inner) > 0:
    print(f"Fields mapped: {len(inner)}")
    timing = mapping.get("_timing_ms", "N/A")
    print(f"Timing: {timing}")
    print("Field mappings:")
    for k, v in list(inner.items())[:15]:
        if isinstance(v, dict):
            path = v.get("api_path", "?")
            conf = v.get("confidence", "?")
            print(f"  {k} -> {path} ({conf})")
else:
    print(f"Top-level keys: {list(mapping.keys())}")
    err = mapping.get("error", "none")
    print(f"Error: {err[:300]}")
