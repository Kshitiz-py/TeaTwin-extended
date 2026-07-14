"""
Generate API payload variants for paper evaluation.

Fetches real data from running mock APIs, then creates transformed variants:
  - clean:    Original field names (baseline)
  - legacy:   Obfuscated cryptic field names (FLD001, FLD002...)
  - german:   German-language field names
  - deep:     Data wrapped in deeply nested envelope structure

Usage: python tests/generate_variants.py
Output: tests/fixtures/variants/{variant}/{entity}.json
"""

import json
import os
import sys
import copy

import httpx

BASE = "http://localhost:8001/api/sap/v1"
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "variants")

ENTITIES = {
    "Resource": "/resources",
    "ResourceClass": "/resource-classes",
    "Order": "/orders",
    "PartType": "/part-types",
}

# --- Field name transformations ---

# Legacy: map each field to a cryptic code
LEGACY_MAP = {
    # Resource fields
    "identifier": "FLD001",
    "name": "FLD002",
    "description": "FLD003",
    "resource_type": "FLD004",
    "resource_class_id": "FLD005",
    "capacity": "FLD006",
    "availability": "FLD007",
    "mttr_seconds": "FLD008",
    "mtbf_seconds": "FLD009",
    "mcbf": "FLD010",
    "reliability": "FLD011",
    "cycle_time_seconds": "FLD012",
    "desired_replenishment_time_seconds": "FLD013",
    "transport_capacity": "FLD014",
    "tow_bar_length": "FLD015",
    "worker_count": "FLD016",
    "decision_rule": "FLD017",
    "routing_rule": "FLD018",
    "size": "FLD019",
    "hourly_rate": "FLD020",
    "buffer_type": "FLD021",
    "buffer_capacity": "FLD022",
    "conveyor_speed": "FLD023",
    "conveyor_length": "FLD024",
    "conveyor_accumulating": "FLD025",
    "energy": "FLD026",
    # ResourceClass fields
    # "identifier" already mapped above — reuse
    # "name" already mapped
    # "description" already mapped
    # "resource_type" already mapped
    # "hourly_rate" already mapped
    # "size" already mapped
    # Order fields
    "status": "FLD101",
    "due_date": "FLD102",
    "release_date": "FLD103",
    "priority": "FLD104",
    "line_count": "FLD105",
    # PartType fields
    "weight_kg": "FLD201",
    "color": "FLD202",
    "shape_3d": "FLD203",
    # Nested size fields
    "length": "FLD301",
    "width": "FLD302",
    "height": "FLD303",
    # Nested energy fields
    "working_kw": "FLD401",
    "standby_kw": "FLD402",
    "failed_kw": "FLD403",
    "off_kw": "FLD404",
}

GERMAN_MAP = {
    "identifier": "kennung",
    "name": "bezeichnung",
    "description": "beschreibung",
    "resource_type": "maschinentyp",
    "resource_class_id": "maschinenklasse_id",
    "capacity": "kapazitaet",
    "availability": "verfuegbarkeit",
    "mttr_seconds": "mttr_sekunden",
    "mtbf_seconds": "mtbf_sekunden",
    "mcbf": "mcbf",
    "reliability": "zuverlaessigkeit",
    "cycle_time_seconds": "zykluszeit_sekunden",
    "desired_replenishment_time_seconds": "nachfuellzeit_sekunden",
    "transport_capacity": "transportkapazitaet",
    "tow_bar_length": "zugdeichsel_laenge",
    "worker_count": "mitarbeiter_anzahl",
    "decision_rule": "entscheidungsregel",
    "routing_rule": "routing_regel",
    "size": "abmessungen",
    "hourly_rate": "stundensatz",
    "buffer_type": "puffertyp",
    "buffer_capacity": "pufferkapazitaet",
    "conveyor_speed": "foerdergeschwindigkeit",
    "conveyor_length": "foerderlaenge",
    "conveyor_accumulating": "foerder_akkumulierend",
    "energy": "energie",
    "status": "status",
    "due_date": "faelligkeitsdatum",
    "release_date": "freigabedatum",
    "priority": "prioritaet",
    "line_count": "positionsanzahl",
    "weight_kg": "gewicht_kg",
    "color": "farbe",
    "shape_3d": "3d_form",
    "length": "laenge",
    "width": "breite",
    "height": "hoehe",
    "working_kw": "arbeitend_kw",
    "standby_kw": "standby_kw",
    "failed_kw": "fehler_kw",
    "off_kw": "aus_kw",
}


def rename_fields(obj, mapping, top_level_only=False):
    """Recursively rename dict keys using mapping. Returns new object."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            new_key = mapping.get(k, k)
            if top_level_only:
                result[new_key] = v
            else:
                result[new_key] = rename_fields(v, mapping)
        return result
    elif isinstance(obj, list):
        return [rename_fields(item, mapping) for item in obj]
    return obj


def wrap_deep(data, entity_key):
    """Wrap data in a deeply nested envelope structure."""
    return {
        "status": "success",
        "data": {
            "payload": {
                "items": data.get(entity_key, data.get("resources", data.get("orders", data.get("part_types", data.get("resource_classes", [])))))
            },
            "metadata": {
                "version": "2.1",
                "generated_at": "2026-05-28T10:00:00Z",
            }
        }
    }


def fetch_entity(client, entity_name):
    """Fetch entity data from mock API."""
    endpoint = ENTITIES[entity_name]
    url = f"{BASE}{endpoint}"
    r = client.get(url, timeout=10)
    r.raise_for_status()
    return r.json()


def get_items_key(entity_name):
    """Get the JSON key for entity items in the API response."""
    key_map = {
        "Resource": "resources",
        "ResourceClass": "resource_classes",
        "Order": "orders",
        "PartType": "part_types",
    }
    return key_map[entity_name]


def main():
    client = httpx.Client()

    for entity_name in ENTITIES:
        print(f"Processing {entity_name}...")
        data = fetch_entity(client, entity_name)
        items_key = get_items_key(entity_name)

        # 1. Clean variant (original)
        clean_dir = os.path.join(FIXTURES_DIR, "clean")
        os.makedirs(clean_dir, exist_ok=True)
        with open(os.path.join(clean_dir, f"{entity_name}.json"), "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"  clean: {len(data.get(items_key, []))} items")

        # 2. Legacy variant (cryptic field names)
        legacy_data = rename_fields(copy.deepcopy(data), LEGACY_MAP)
        legacy_dir = os.path.join(FIXTURES_DIR, "legacy")
        os.makedirs(legacy_dir, exist_ok=True)
        with open(os.path.join(legacy_dir, f"{entity_name}.json"), "w") as f:
            json.dump(legacy_data, f, indent=2, default=str)
        print(f"  legacy: {len(legacy_data.get(items_key, []))} items")

        # 3. German variant
        german_data = rename_fields(copy.deepcopy(data), GERMAN_MAP)
        german_dir = os.path.join(FIXTURES_DIR, "german")
        os.makedirs(german_dir, exist_ok=True)
        with open(os.path.join(german_dir, f"{entity_name}.json"), "w") as f:
            json.dump(german_data, f, indent=2, default=str)
        print(f"  german: {len(german_data.get(items_key, []))} items")

        # 4. Deep variant (nested envelope)
        deep_data = wrap_deep(copy.deepcopy(data), items_key)
        deep_dir = os.path.join(FIXTURES_DIR, "deep")
        os.makedirs(deep_dir, exist_ok=True)
        with open(os.path.join(deep_dir, f"{entity_name}.json"), "w") as f:
            json.dump(deep_data, f, indent=2, default=str)
        inner_key = "data.payload.items"
        items = deep_data.get("data", {}).get("payload", {}).get("items", [])
        print(f"  deep: {len(items)} items (via {inner_key})")

        # Also save variant metadata for reference
        meta = {
            "description": f"{entity_name} {entity_name} variant",
            "item_count": len(data.get(items_key, [])),
            "source_url": f"{BASE}{ENTITIES[entity_name]}",
            "variant_transformation": {
                "clean": "Original field names from mock SAP API",
                "legacy": "Field names obfuscated to cryptic codes (FLD001-FLD404)",
                "german": "Field names translated to German",
                "deep": "Data wrapped in 3-level envelope: data.payload.items[]",
            }
        }
        # Save LEGACY_MAP and GERMAN_MAP as reference for ground truth
        if entity_name == list(ENTITIES.keys())[0]:
            # Save transformation maps once
            with open(os.path.join(FIXTURES_DIR, "legacy_map.json"), "w") as f:
                json.dump(LEGACY_MAP, f, indent=2)
            with open(os.path.join(FIXTURES_DIR, "german_map.json"), "w") as f:
                json.dump(GERMAN_MAP, f, indent=2)

    client.close()
    print("\nDone. Fixtures saved to:", FIXTURES_DIR)


if __name__ == "__main__":
    main()
