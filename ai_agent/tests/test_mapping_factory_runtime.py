"""Deterministic runtime tests for MappingDrivenFactory's SAP OData support.

Covers the Slice 4 additions:
  * ``_resolve_auth`` — plaintext fallback + Fernet-encrypted decrypt + graceful
    fallback when the runtime key is missing.
  * ``_build_entity`` — ``unit_from_field`` resolution (OData ``sap:unit``): reads
    the SAP unit code from the companion property, looks up the factor, synthesizes
    a ``unit_conversion``, and the existing coercion wraps it into a CMSD ``Duration``.
  * ``build_all`` — threads ``source.headers`` / ``source.params`` / decrypted auth
    into ``api_client.fetch`` and extracts the OData v2 ``d.results`` array via
    ``instances.count_path``.

No network, no ChromaDB. Uses a fake api_client returning a canned OData v2 response.
"""
import os
import sys

# cmsd_schema lives in the sibling cmsd-pydantic-master repo — pip-installed in
# Docker (so `from cmsd_schema...` just works there), but on disk at
# 04_Playground/cmsd-pydantic-master/src. Add it to sys.path so this test can
# import cmsd_twin_service.mapping_factory locally without a pip install.
_CMSD_SRC = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "cmsd-pydantic-master", "src")
)
if os.path.isdir(_CMSD_SRC) and _CMSD_SRC not in sys.path:
    sys.path.insert(0, _CMSD_SRC)

import asyncio
from decimal import Decimal

import pytest

from cmsd_twin_service.mapping_factory import MappingDrivenFactory
from cmsd_schema.basic_types import TimeUnit
from shared.crypto import generate_key, encrypt_dict


def _factory() -> MappingDrivenFactory:
    f = MappingDrivenFactory()
    assert f._FIELD_TYPE_HINTS, "type hints should be built in __init__"
    return f


def _process_mapping() -> dict:
    return {
        "_id": "proc-test",
        "cmsd_entity": "Process",
        "source": {
            "type": "generic",
            "base_url": "https://a33p.ucc.cloud/sap/opu/odata/sap/API_PRODUCTION_ROUTING",
            "endpoint": "/ProductionRoutingOperation",
            "method": "GET",
            "auth": {"type": "basic", "username": "u", "password": "p"},
            "headers": {"Accept": "application/json", "DataServiceVersion": "2.0"},
            "params": {"sap-client": "200", "$format": "json"},
        },
        "instances": {"count_path": "$.d.results", "key_field": "Operation"},
        "mapping": {
            "identifier": {"api_path": "Operation"},
            "duration": {
                "api_path": "StandardWorkQuantity1",
                "unit_from_field": {"unit_path": "StandardWorkQuantityUnit1", "target_unit": "second"},
            },
        },
    }


# ─── _resolve_auth ───────────────────────────────────────────────────────────

def test_resolve_auth_plaintext_fallback():
    f = _factory()
    assert f._resolve_auth({}) == {"type": "none"}
    assert f._resolve_auth({"auth": {"type": "none"}}) == {"type": "none"}
    assert f._resolve_auth({"auth": {"type": "basic", "username": "u", "password": "p"}}) == \
        {"type": "basic", "username": "u", "password": "p"}


def test_resolve_auth_encrypted(monkeypatch):
    monkeypatch.setenv("SAP_CRED_KEY", generate_key())
    enc = encrypt_dict({"type": "basic", "username": "BOHARA", "password": "secret"})
    f = _factory()
    assert f._resolve_auth({"auth_encrypted": enc, "auth": None}) == \
        {"type": "basic", "username": "BOHARA", "password": "secret"}


def test_resolve_auth_encrypted_but_no_runtime_key(monkeypatch):
    # Mapping was encrypted, but the runtime has no SAP_CRED_KEY -> graceful fallback
    # to {"type":"none"} (fetch will fail auth, but the factory must not crash).
    monkeypatch.delenv("SAP_CRED_KEY", raising=False)
    f = _factory()
    assert f._resolve_auth({"auth_encrypted": "gAAAAA-some-token", "auth": None}) == {"type": "none"}


# ─── unit_from_field -> Duration conversion ───────────────────────────────────

def test_build_entity_unit_from_field_conversion():
    f = _factory()
    raw_items = [
        {"Operation": "0010", "StandardWorkQuantity1": "5", "StandardWorkQuantityUnit1": "MIN"},
        {"Operation": "0020", "StandardWorkQuantity1": "2", "StandardWorkQuantityUnit1": "HUR"},
        {"Operation": "0030", "StandardWorkQuantity1": "30", "StandardWorkQuantityUnit1": "SEC"},
    ]
    instances, warnings = f._build_entity(_process_mapping(), raw_items)
    assert len(instances) == 3, f"expected 3, got {len(instances)}; warnings={warnings}"
    assert instances[0].identifier == "0010"
    # 5 MIN -> 300 seconds
    assert instances[0].duration is not None
    assert instances[0].duration.unit == TimeUnit.SECOND
    assert instances[0].duration.value == Decimal("300")
    # 2 HUR -> 7200 seconds
    assert instances[1].duration.value == Decimal("7200")
    # 30 SEC -> 30 seconds
    assert instances[2].duration.value == Decimal("30")
    # Provenance points at real SAP
    assert instances[0]._connection["source_url"].endswith("/ProductionRoutingOperation")


def test_build_entity_unknown_unit_leaves_value_and_warns():
    f = _factory()
    raw_items = [{"Operation": "0040", "StandardWorkQuantity1": "99", "StandardWorkQuantityUnit1": "KG"}]
    instances, warnings = f._build_entity(_process_mapping(), raw_items)
    assert len(instances) == 1
    # Unknown unit (KG, a weight code not in the time-units table) -> no transform
    # synthesized -> value passes through as 99 seconds (no crash, no guess).
    assert instances[0].duration is not None
    assert instances[0].duration.value == Decimal("99")
    assert any(w.get("field") == "duration" and "KG" in w.get("warning", "") for w in warnings)


# ─── build_all: headers/params/auth threading + d.results extraction ──────────

class FakeApiClient:
    """Records fetch() calls; returns a canned OData v2 d.results response."""
    def __init__(self, response: dict):
        self.response = response
        self.calls: list[dict] = []

    async def fetch(self, url, method="GET", headers=None, auth_config=None, params=None):
        self.calls.append({"url": url, "method": method, "headers": headers,
                           "auth_config": auth_config, "params": params})
        return self.response


def test_build_all_threads_headers_params_auth_and_extracts_d_results(monkeypatch):
    monkeypatch.setenv("SAP_CRED_KEY", generate_key())
    mapping = _process_mapping()
    # Encrypt the auth so we exercise _resolve_auth's decrypt path end-to-end
    mapping["source"]["auth_encrypted"] = encrypt_dict(mapping["source"].pop("auth"))
    mapping["source"]["auth"] = None

    f = _factory()
    f._mappings = [mapping]

    response = {"d": {"results": [
        {"Operation": "0010", "StandardWorkQuantity1": "5", "StandardWorkQuantityUnit1": "MIN"},
    ]}}
    fake = FakeApiClient(response)

    doc, report = asyncio.run(f.build_all(fake, mapping_ids=["proc-test"], registry=None))

    # The fetch call threaded headers/params + decrypted auth
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["url"].endswith("/ProductionRoutingOperation")
    assert call["headers"] == {"Accept": "application/json", "DataServiceVersion": "2.0"}
    assert call["params"] == {"sap-client": "200", "$format": "json"}
    assert call["auth_config"] == {"type": "basic", "username": "u", "password": "p"}

    # d.results extracted via count_path="$.d.results"; one Process built + converted
    assert report["fetch_errors"] == []
    assert report["entities"]["Process"]["count"] == 1
    assert report["field_warnings"] == []  # conversion succeeded, no gaps
    assert report["relation_errors"] == []