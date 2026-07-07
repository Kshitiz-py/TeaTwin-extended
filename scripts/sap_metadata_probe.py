"""Standalone probe: fetch real SAP OData $metadata and parse it.

Verifies ``shared.odata`` (ODataClient + EdmxParser) against a live SAP S/4HANA
system. Reads credentials from ``.env.sap`` (checked at the repo root, then at
``../03_Pipeline/.env.sap``). No ChromaDB, no LLM — pure deterministic fetch +
parse, so it runs without the service stack.

Usage::

    python scripts/sap_metadata_probe.py [service_path]
    # service_path default: /sap/opu/odata/sap/API_PRODUCTION_ROUTING
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from shared.odata.client import ODataClient
from shared.odata.parser import EdmxParser


def load_env() -> tuple[dict, Path | None]:
    # .env.sap may live at the repo root, the 04_Playground level, or in the
    # sibling 03_Pipeline (where it ships today, alongside test_sap_connection.py).
    candidates = [
        REPO / ".env.sap",
        REPO.parent / ".env.sap",
        REPO.parent.parent / "03_Pipeline" / ".env.sap",
    ]
    for p in candidates:
        if p.exists():
            creds: dict[str, str] = {}
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                creds[k.strip()] = v.strip()
            return creds, p
    return {}, None


async def main() -> int:
    service_path = sys.argv[1] if len(sys.argv) > 1 else "/sap/opu/odata/sap/API_PRODUCTION_ROUTING"
    creds, env_path = load_env()
    base = creds.get("SAP_BASE_URL", "https://a33p.ucc.cloud").rstrip("/") + service_path
    sap_client = creds.get("SAP_CLIENT", "200")
    auth = {
        "type": "basic",
        "username": creds.get("SAP_USERNAME", ""),
        "password": creds.get("SAP_PASSWORD", ""),
    }
    print(f"[*] {base}  client={sap_client}  env={env_path}")
    if not auth["username"] or not auth["password"]:
        print("[!] SAP_USERNAME/SAP_PASSWORD missing in .env.sap")
        return 2

    client = ODataClient(base, auth, sap_client=sap_client, timeout=60.0)
    xml = await client.fetch_metadata()
    print(f"[*] $metadata fetched: {len(xml)} bytes")

    schema = EdmxParser().parse(xml, service_url=base)
    print(f"[*] namespace={schema.namespace!r}  entity_types={len(schema.entity_types)}\n")
    print(f"{'EntitySet':36s} {'EntityType':40s} props keys nav sap:unit_fields")
    print("-" * 110)
    for et in schema.entity_types:
        unit_fields = [p.name for p in et.properties if p.sap_unit]
        print(f"{et.entity_set_name:36s} {et.name:40s} "
              f"{len(et.properties):5d} {len(et.keys):4d} {len(et.navigation_properties):3d} {unit_fields}")

    # Drill into ProductionRoutingOperation (the entity used by the test + Slice 4)
    pr = next((et for et in schema.entity_types if et.entity_set_name == "ProductionRoutingOperation"), None)
    if pr:
        swq = next((p for p in pr.properties if p.sap_unit), None)
        print("\n[*] ProductionRoutingOperation first sap:unit field:",
              (swq.name + " -> " + swq.sap_unit) if swq else None)
        nav = next((n for n in pr.navigation_properties if n.to_entity_type), None)
        if nav:
            print(f"[*] sample navigation: {nav.name} -> {nav.to_entity_type}  join={nav.referential_constraints}")
    else:
        print("\n[!] ProductionRoutingOperation not found in this service's entity sets")

    # Security sanity: chunks must be metadata-only (no row-data markers)
    chunks = schema.to_chunks(source_id="probe")
    assert chunks, "expected at least one source-schema chunk"
    assert all(c.metadata["collection"] == "source-schema" for c in chunks)
    assert "d.results" not in chunks[0].content, "row-data marker leaked into metadata chunk"
    print(f"\n[OK] {len(chunks)} source-schema chunks; metadata-only (no row-data markers).")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))