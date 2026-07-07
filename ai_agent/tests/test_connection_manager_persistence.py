"""Encrypted-persistence round-trip for the connection_manager source store.

Verifies that, when SAP_CRED_KEY is set, sources are written to disk encrypted and
reloaded on a fresh ConnectionManager — and that no plaintext credentials land on
disk. Side effects are isolated to a tmp dir (the module-level creds path is
monkeypatched). When the key is unset, nothing is written.
"""

import os

import pytest

from ai_agent import connection_manager as cm_mod
from ai_agent.connection_manager import ConnectionManager
from shared.crypto import generate_key


@pytest.fixture
def creds_file(monkeypatch, tmp_path):
    """Redirect the module-level encrypted store to a tmp path."""
    cred_dir = tmp_path / "credentials"
    monkeypatch.setattr(cm_mod, "_CREDENTIALS_DIR", str(cred_dir))
    monkeypatch.setattr(cm_mod, "_CREDENTIALS_FILE", str(cred_dir / "sources.json"))
    return cred_dir / "sources.json"


def test_encrypted_persistence_roundtrip(monkeypatch, creds_file):
    monkeypatch.setenv("SAP_CRED_KEY", generate_key())

    mgr = ConnectionManager()  # _load: file absent -> empty
    assert mgr.list_sources() == []

    added = mgr.add_source({
        "name": "SAP a33p",
        "base_url": "https://a33p.ucc.cloud/sap/opu/odata/sap/API_PRODUCTION_ROUTING",
        "auth_type": "basic",
        "username": "BOHARA",
        "password": "hunter2-pw",
        "sap_client": "200",
    })
    sid = added["id"]

    # The file exists and contains NO plaintext credentials or JSON keys
    assert creds_file.exists()
    raw = creds_file.read_text()
    assert "hunter2-pw" not in raw
    assert "BOHARA" not in raw
    assert "password" not in raw  # whole dict is encrypted; even keys are opaque
    assert raw.startswith("gAAAAA")  # Fernet tokens start with this prefix

    # A fresh manager reloads the encrypted store and decrypts it
    mgr2 = ConnectionManager()
    srcs = mgr2.list_sources()
    assert len(srcs) == 1
    assert srcs[0]["id"] == sid
    assert srcs[0]["username"] == "BOHARA"
    assert srcs[0]["password"] == "hunter2-pw"
    assert srcs[0]["base_url"].endswith("API_PRODUCTION_ROUTING")


def test_no_persistence_without_key(monkeypatch, creds_file):
    monkeypatch.delenv("SAP_CRED_KEY", raising=False)
    mgr = ConnectionManager()
    mgr.add_source({"name": "mock-sap", "base_url": "http://mock-sap-api:8001", "auth_type": "none"})
    # In-memory only — nothing written to disk
    assert not creds_file.exists()
    assert len(mgr.list_sources()) == 1


def test_corrupt_or_rotated_key_starts_empty(monkeypatch, creds_file):
    # Write with one key, then rotate the key — a fresh manager must not crash
    monkeypatch.setenv("SAP_CRED_KEY", generate_key())
    mgr = ConnectionManager()
    mgr.add_source({"name": "s", "base_url": "http://x", "auth_type": "basic", "username": "u", "password": "p"})
    assert creds_file.exists()

    monkeypatch.setenv("SAP_CRED_KEY", generate_key())  # rotate
    mgr2 = ConnectionManager()  # decrypt fails -> warns + starts empty (does not raise)
    assert mgr2.list_sources() == []