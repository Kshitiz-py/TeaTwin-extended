"""Unit tests for shared.crypto (Fernet-at-rest for SAP credentials)."""

import os

import pytest

from shared.crypto import encrypt_dict, decrypt_dict, is_enabled, generate_key


@pytest.fixture
def key_env(monkeypatch):
    """Provide a valid SAP_CRED_KEY for the test, cleaned up afterward."""
    monkeypatch.setenv("SAP_CRED_KEY", generate_key())
    yield
    monkeypatch.delenv("SAP_CRED_KEY", raising=False)


def test_roundtrip(key_env):
    data = {"type": "basic", "username": "u", "password": "s3cret!"}
    token = encrypt_dict(data)
    assert isinstance(token, str) and token != ""
    # The token must not leak the plaintext secret
    assert "s3cret!" not in token
    assert "basic" not in token
    assert decrypt_dict(token) == data
    assert is_enabled() is True


def test_disabled_when_no_key(monkeypatch):
    monkeypatch.delenv("SAP_CRED_KEY", raising=False)
    assert is_enabled() is False
    assert encrypt_dict({"a": 1}) is None
    assert decrypt_dict("anything") is None


def test_invalid_key_raises(monkeypatch):
    monkeypatch.setenv("SAP_CRED_KEY", "not-a-valid-fernet-key")
    with pytest.raises(Exception):
        encrypt_dict({"a": 1})
    monkeypatch.delenv("SAP_CRED_KEY", raising=False)


def test_wrong_key_fails_to_decrypt(monkeypatch):
    monkeypatch.setenv("SAP_CRED_KEY", generate_key())
    token = encrypt_dict({"secret": "x"})
    # Rotate the key — decryption must fail (InvalidToken), not return garbage
    monkeypatch.setenv("SAP_CRED_KEY", generate_key())
    with pytest.raises(Exception):
        decrypt_dict(token)
    monkeypatch.delenv("SAP_CRED_KEY", raising=False)