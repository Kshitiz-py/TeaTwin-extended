"""Symmetric (Fernet) encryption for SAP credentials at rest.

Key: the ``SAP_CRED_KEY`` environment variable — a urlsafe-base64 32-byte Fernet
key (generate one with ``generate_key()``). When set, credentials are encrypted
before being written to disk — both the connection_manager source store
(``.agent-mappings/credentials/sources.json``) and the mapping ``source.auth_encrypted``
block — and decrypted on read. Both the ai-agent (encrypts on source-add / confirm)
and the cmsd-twin-service (decrypts at runtime fetch) share the same key via env.

When ``SAP_CRED_KEY`` is unset, encryption is disabled and the system falls back to
a plaintext normalized ``source.auth`` block (dev / no-key mode). Production
deployments must set ``SAP_CRED_KEY``.
"""
from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger("shared.crypto")


def is_enabled() -> bool:
    """True when ``SAP_CRED_KEY`` is set (encryption at rest is active)."""
    return bool(os.getenv("SAP_CRED_KEY"))


def _fernet():
    """Build a Fernet from ``SAP_CRED_KEY``, or return None when unset.

    ``cryptography`` is imported lazily so importing this module is cheap and works
    even if the optional crypto backend is absent (the dev/no-key path never calls
    this). Built per call (cheap) to avoid stale-key bugs when env changes in tests.
    """
    key = os.getenv("SAP_CRED_KEY")
    if not key:
        return None
    from cryptography.fernet import Fernet
    return Fernet(key.encode("utf-8"))


def encrypt_dict(data: dict) -> str | None:
    """Encrypt a dict to a Fernet token string. Returns None if encryption is disabled."""
    f = _fernet()
    if f is None:
        return None
    token = f.encrypt(json.dumps(data, default=str).encode("utf-8"))
    return token.decode("ascii")


def decrypt_dict(token: str) -> dict | None:
    """Decrypt a Fernet token string back to a dict. Returns None if disabled."""
    f = _fernet()
    if f is None:
        return None
    raw = f.decrypt(token.encode("utf-8"))
    return json.loads(raw.decode("utf-8"))


def generate_key() -> str:
    """Generate a new Fernet key (urlsafe-base64 32-byte) for ``SAP_CRED_KEY``."""
    from cryptography.fernet import Fernet
    return Fernet.generate_key().decode("ascii")