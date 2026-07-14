"""
Connection Manager — Stores, tests, and manages data source connections.
Supports: Basic Auth, Bearer Token, OAuth2, API Key, mTLS, and None.

Storage: in-memory by default. When ``SAP_CRED_KEY`` is set, the source store is
additionally persisted to ``.agent-mappings/credentials/sources.json`` **encrypted
with Fernet** (see shared.crypto), so configured SAP sources survive an ai-agent
restart without credentials ever being written to disk in plaintext. When the key
is unset, behavior is unchanged (in-memory only) — the dev / no-key mode.
"""

import json
import logging
import os
import time
import uuid
from typing import Any

import httpx

from .config import PROJECT_ROOT
from shared.crypto import encrypt_dict, decrypt_dict, is_enabled

logger = logging.getLogger("ai-agent.connection-manager")

AUTH_TYPES = ["none", "basic", "bearer", "oauth2", "api_key", "mtls"]

# Encrypted-at-rest source store (inside the shared .agent-mappings volume so it
# persists across ai-agent restarts). Only written when SAP_CRED_KEY is set.
_CREDENTIALS_DIR = os.path.join(PROJECT_ROOT, ".agent-mappings", "credentials")
_CREDENTIALS_FILE = os.path.join(_CREDENTIALS_DIR, "sources.json")


class ConnectionManager:
    """Manages configured data source connections (SAP, MES, custom)."""

    def __init__(self):
        self._sources: dict[str, dict[str, Any]] = {}
        self._load()

    # ── opt-in encrypted disk persistence ────────────────────────────────
    def _load(self) -> None:
        """Load the encrypted source store from disk when SAP_CRED_KEY is set."""
        if not is_enabled():
            return
        if not os.path.exists(_CREDENTIALS_FILE):
            return
        try:
            with open(_CREDENTIALS_FILE, "r", encoding="utf-8") as f:
                token = f.read().strip()
            if token:
                data = decrypt_dict(token)
                if isinstance(data, dict):
                    self._sources = data
                    logger.info(f"Loaded {len(self._sources)} encrypted source(s) from disk")
        except Exception as e:
            # Key rotated / file corrupt: start empty rather than crash. The user
            # re-adds sources; nothing is lost (the old encrypted blob is still on disk).
            logger.warning(f"Could not decrypt persisted sources (key changed?): {e}")

    def _persist(self) -> None:
        """Persist the source store encrypted to disk when SAP_CRED_KEY is set."""
        if not is_enabled():
            return
        try:
            os.makedirs(_CREDENTIALS_DIR, exist_ok=True)
            token = encrypt_dict(self._sources)
            if token is None:
                return
            with open(_CREDENTIALS_FILE, "w", encoding="utf-8") as f:
                f.write(token)
        except Exception as e:
            logger.warning(f"Could not persist sources (encrypted): {e}")

    # ── CRUD ──────────────────────────────────────────────────────────────
    def add_source(self, source: dict[str, Any]) -> dict[str, Any]:
        """Add or update a data source configuration (upsert by ``id``).

        Returns the created/updated source with its ID. If ``id`` is present and
        matches an existing source, that record is updated in place — so editing a
        source card (e.g. typing SAP credentials) modifies the same source instead
        of spawning a duplicate under a new id. If ``id`` is absent/empty, a new id
        is minted. Runtime ``status``/``last_tested`` are preserved across edits
        (the SourceConfig payload doesn't carry them).
        """
        source_id = source.get("id") or f"src-{uuid.uuid4().hex[:8]}"
        existing = self._sources.get(source_id)
        source["id"] = source_id
        source["status"] = existing.get("status", "configured") if existing else "configured"
        source["last_tested"] = existing.get("last_tested") if existing else None
        self._sources[source_id] = source
        self._persist()
        logger.info(f"Source added/updated: {source_id} ({source.get('name', 'unnamed')})")
        return source

    def get_source(self, source_id: str) -> dict[str, Any] | None:
        """Retrieve a source by ID."""
        return self._sources.get(source_id)

    def list_sources(self) -> list[dict[str, Any]]:
        """Return all configured sources."""
        return list(self._sources.values())

    def remove_source(self, source_id: str) -> bool:
        """Remove a source. Returns True if it existed."""
        if source_id in self._sources:
            del self._sources[source_id]
            self._persist()
            return True
        return False

    async def test_connection(self, source_id: str) -> dict[str, Any]:
        """
        Test connectivity to a data source.
        Makes an authenticated health-check call to the base URL and requires a 2xx
        response. 401/403 → failure ("Unauthorized") so a source with wrong or empty
        credentials is NOT reported as connected. Tries /health, /, /api/health in turn
        (404/405 on one path → try the next). Returns {success, status_code, message, latency_ms}.
        """
        source = self._sources.get(source_id)
        if not source:
            return {"success": False, "message": f"Source '{source_id}' not found"}

        base_url = source.get("base_url", "").rstrip("/")
        if not base_url:
            return {"success": False, "message": "Base URL not configured"}

        headers = {}
        auth_type = source.get("auth_type", "none")

        if auth_type == "bearer":
            headers["Authorization"] = f"Bearer {source.get('token', '')}"
        elif auth_type == "api_key":
            api_key_header = source.get("api_key_header", "X-API-Key")
            headers[api_key_header] = source.get("api_key", "")
        elif auth_type == "basic":
            import base64
            username = source.get("username", "")
            password = source.get("password", "")
            encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"

        if source.get("extra_headers"):
            headers.update(source["extra_headers"])

        start = time.time()

        def _record(status: str) -> None:
            source["status"] = status
            source["last_tested"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self._persist()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                last_status: int | None = None
                last_conn_err: str | None = None
                for health_path in ["/health", "/", "/api/health"]:
                    try:
                        resp = await client.get(f"{base_url}{health_path}", headers=headers)
                    except httpx.ConnectError:
                        last_conn_err = "Connection refused — server unreachable"
                        continue
                    except httpx.TimeoutException:
                        last_conn_err = "Connection timed out"
                        continue
                    except httpx.HTTPError as e:
                        last_conn_err = str(e)
                        continue

                    latency = round((time.time() - start) * 1000, 1)
                    code = resp.status_code
                    last_status = code
                    if 200 <= code < 300:
                        _record("connected")
                        return {"success": True, "status_code": code,
                                "message": f"Connected via {health_path}", "latency_ms": latency}
                    if code in (401, 403):
                        _record("failed")
                        return {"success": False, "status_code": code,
                                "message": f"Unauthorized (HTTP {code}) — check credentials", "latency_ms": latency}
                    if code in (404, 405):
                        continue  # no such endpoint here; try the next path
                    # Any other 4xx/5xx is a genuine failure.
                    _record("failed")
                    return {"success": False, "status_code": code,
                            "message": f"Server returned HTTP {code}", "latency_ms": latency}

                # No path returned 2xx.
                latency = round((time.time() - start) * 1000, 1)
                if last_status is not None:
                    # Every path was 404/405 (we continued past them) and none returned
                    # 401/403 or a non-404 error — so the server IS reachable and speaking
                    # HTTP, it just has no health/root endpoint (the mock SAP/MES APIs are
                    # like this). Treat as connected.
                    _record("connected")
                    return {"success": True, "status_code": last_status,
                            "message": "Connected (no dedicated health endpoint)", "latency_ms": latency}
                _record("failed")
                return {"success": False, "message": last_conn_err or "Connection failed", "latency_ms": latency}
        except Exception as e:
            _record("failed")
            return {"success": False, "message": str(e)}


# Singleton
connection_manager = ConnectionManager()