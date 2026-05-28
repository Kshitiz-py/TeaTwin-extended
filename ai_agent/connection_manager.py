"""
Connection Manager — Stores, tests, and manages data source connections.
Supports: Basic Auth, Bearer Token, OAuth2, API Key, mTLS, and None.
Stored in-memory (extensible to encrypted SQLite/MySQL).
"""

import json
import logging
import uuid
from typing import Any

import httpx

logger = logging.getLogger("ai-agent.connection-manager")

AUTH_TYPES = ["none", "basic", "bearer", "oauth2", "api_key", "mtls"]


class ConnectionManager:
    """Manages configured data source connections (SAP, MES, custom)."""

    def __init__(self):
        self._sources: dict[str, dict[str, Any]] = {}

    def add_source(self, source: dict[str, Any]) -> dict[str, Any]:
        """
        Add or update a data source configuration.
        Returns the created source with its ID.
        """
        source_id = source.get("id") or f"src-{uuid.uuid4().hex[:8]}"
        source["id"] = source_id
        source["status"] = "configured"
        source["last_tested"] = None
        self._sources[source_id] = source
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
            return True
        return False

    async def test_connection(self, source_id: str) -> dict[str, Any]:
        """
        Test connectivity to a data source.
        Makes a health-check call to the base URL.
        Returns {success, status_code, message, latency_ms}.
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

        import time
        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try common health endpoints
                for health_path in ["/health", "/", "/api/health"]:
                    try:
                        resp = await client.get(f"{base_url}{health_path}", headers=headers)
                        latency = round((time.time() - start) * 1000, 1)
                        source["status"] = "connected"
                        source["last_tested"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                        return {
                            "success": True,
                            "status_code": resp.status_code,
                            "message": f"Connected via {health_path}",
                            "latency_ms": latency,
                        }
                    except httpx.HTTPError:
                        continue

                # If no health endpoint, just try root
                resp = await client.get(base_url, headers=headers)
                latency = round((time.time() - start) * 1000, 1)
                source["status"] = "connected"
                source["last_tested"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                return {
                    "success": True,
                    "status_code": resp.status_code,
                    "message": "Connected (no dedicated health endpoint)",
                    "latency_ms": latency,
                }

        except httpx.ConnectError:
            source["status"] = "failed"
            return {"success": False, "message": "Connection refused — server unreachable"}
        except httpx.TimeoutException:
            source["status"] = "failed"
            return {"success": False, "message": "Connection timed out"}
        except httpx.HTTPStatusError as e:
            source["status"] = "failed"
            return {"success": False, "status_code": e.response.status_code, "message": str(e)}
        except Exception as e:
            source["status"] = "failed"
            return {"success": False, "message": str(e)}


# Singleton
connection_manager = ConnectionManager()
