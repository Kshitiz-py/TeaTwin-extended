"""Auth helpers for OData/SAP sources.

``build_auth_headers`` turns a *normalized* auth dict into HTTP headers. The
normalized shape is exactly what
``cmsd_twin_service.api_client._build_auth_headers`` already reads on the runtime
fetch path::

    {"type": "basic"|"bearer"|"apikey"|"none",
     ...per-type credential keys: username/password | token | header+key}

``normalize_auth`` (added in Slice 3) maps the connection_manager's flat
``SourceConfig`` fields (``auth_type``/``username``/``password``/``token``/
``api_key``/``api_key_header``) into this normalized shape before it is encrypted
at rest, so the OData client and the runtime fetch path agree on the wire format.
"""
from __future__ import annotations

import base64


def build_auth_headers(auth: dict | None) -> dict:
    """Build HTTP Authorization/auth headers from a normalized auth dict.

    Supported types: ``bearer``, ``basic``, ``apikey``, ``none``. Mirrors
    ``cmsd_twin_service/api_client.py:_build_auth_headers`` so the deterministic
    OData client and the runtime fetch path produce identical headers.
    """
    auth = auth or {}
    t = str(auth.get("type", "")).lower()
    if t == "bearer":
        return {"Authorization": f"Bearer {auth.get('token', '')}"}
    if t == "basic":
        raw = f"{auth.get('username', '')}:{auth.get('password', '')}".encode("utf-8")
        return {"Authorization": f"Basic {base64.b64encode(raw).decode('ascii')}"}
    if t == "apikey":
        header = auth.get("header", "X-API-Key")
        return {header: auth.get("key", "")}
    # none / unknown
    return {}


def normalize_auth(source: dict | None) -> dict:
    """Map a connection_manager source (flat ``auth_type``/``username``/``password``/
    ``token``/``api_key``/``api_key_header`` fields) into the normalized auth dict that
    ``build_auth_headers`` (OData client) and ``api_client._build_auth_headers``
    (runtime fetch) both expect::

        basic  -> {"type": "basic",  "username": ..., "password": ...}
        bearer -> {"type": "bearer", "token": ...}
        api_key-> {"type": "apikey", "header": ..., "key": ...}
        none   -> {"type": "none"}
    """
    source = source or {}
    t = str(source.get("auth_type", "none")).lower()
    if t == "basic":
        return {"type": "basic", "username": source.get("username", ""), "password": source.get("password", "")}
    if t == "bearer":
        return {"type": "bearer", "token": source.get("token", "")}
    if t == "api_key":
        return {"type": "apikey", "header": source.get("api_key_header", "X-API-Key"), "key": source.get("api_key", "")}
    return {"type": "none"}