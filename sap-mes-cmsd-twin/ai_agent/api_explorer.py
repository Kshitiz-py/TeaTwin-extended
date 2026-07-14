"""
API Explorer — Makes live API calls to user-specified endpoints,
parses the response payload, and extracts field paths, types, and sample values.
Used by the mapping engine to analyze real API responses.
"""

import json
import logging
import httpx
from typing import Any

from .connection_manager import connection_manager

logger = logging.getLogger("ai-agent.api-explorer")

# Row cap when firing a SAP OData entity set via /mapping/fetch (analysis only — the
# runtime factory re-fetches at full scale). 100 rows is plenty for field-path extraction
# + sample values without pulling a whole SAP table.
ODATA_FETCH_TOP = 100


class APIExplorer:
    """Fetches and analyzes live API payloads from data sources."""

    def __init__(self):
        self._conn_manager = connection_manager

    async def fetch_payload(
        self,
        source_id: str,
        endpoint: str,
        method: str = "GET",
        body: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        """
        Fetch a live payload from a configured data source.
        Returns the JSON response and metadata.

        SAP OData sources are routed through ``ODataClient`` (adds ``$format=json``,
        ``sap-client``, ``DataServiceVersion: 2.0``, proper Basic auth). A generic GET
        would get Atom/XML (the OData v2 default) and ``resp.json()`` would raise
        "Expecting value: line 1 column 1 (char 0)".
        """
        source = self._conn_manager.get_source(source_id)
        if not source:
            raise ValueError(f"Source '{source_id}' not configured")

        base_url = source.get("base_url", "").rstrip("/")
        if not base_url:
            raise ValueError(f"Source '{source_id}' has no base_url")

        # SAP OData v2 → use the OData client so the response is JSON, not Atom/XML.
        if "/sap/opu/odata/" in base_url.lower():
            from shared.odata.client import ODataClient
            from shared.odata.auth import normalize_auth
            entity_set = endpoint.strip("/").split("?")[0]
            if not entity_set:
                raise ValueError("OData endpoint has no entity set name")
            sap_client = (source.get("sap_client")
                          or source.get("extra_headers", {}).get("sap-client") or "200")
            client = ODataClient(base_url, normalize_auth(source), sap_client=sap_client, timeout=30.0)
            data = await client.fetch_entity_set(entity_set, top=ODATA_FETCH_TOP)
            return {
                "status_code": 200,
                "url": f"{base_url}/{entity_set}",
                "method": method,
                "payload": data,
                "payload_size_bytes": len(json.dumps(data, default=str)),
            }

        full_url = f"{base_url}{endpoint}" if endpoint.startswith("/") else f"{base_url}/{endpoint}"

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

        async with httpx.AsyncClient(timeout=30.0) as client:
            if method.upper() == "GET":
                resp = await client.get(full_url, headers=headers, params=params)
            elif method.upper() == "POST":
                resp = await client.post(full_url, headers=headers, json=body)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            resp.raise_for_status()
            payload = resp.json()

        return {
            "status_code": resp.status_code,
            "url": full_url,
            "method": method,
            "payload": payload,
            "payload_size_bytes": len(json.dumps(payload)),
        }

    def analyze_payload(self, payload: Any, max_depth: int = 3) -> dict[str, Any]:
        """
        Analyze a JSON payload to extract its schema-like structure.
        Returns field paths, types, and sample values.
        """
        return self._analyze_node(payload, "$", 0, max_depth)

    def _analyze_node(self, node: Any, path: str, depth: int, max_depth: int) -> dict[str, Any]:
        """Recursively analyze a JSON node."""
        node_type = type(node).__name__

        result = {
            "path": path,
            "type": node_type,
            "sample": self._truncate_sample(node),
        }

        if depth >= max_depth:
            result["children"] = "..."
            return result

        if isinstance(node, dict):
            result["children"] = {}
            for key, value in node.items():
                child_path = f"{path}.{key}"
                result["children"][key] = self._analyze_node(value, child_path, depth + 1, max_depth)

        elif isinstance(node, list) and len(node) > 0:
            # Analyze first element as representative
            result["length"] = len(node)
            result["children"] = self._analyze_node(node[0], f"{path}[*]", depth + 1, max_depth)

        return result

    def extract_field_paths(self, analysis: dict) -> list[dict[str, str]]:
        """
        Flatten the payload analysis into a list of field paths.
        Returns [{path, type, sample}, ...].
        """
        paths = []

        def flatten(node):
            if not isinstance(node, dict):
                return
            if node.get("type") not in ("dict", "list"):
                paths.append({
                    "path": node["path"],
                    "type": node["type"],
                    "sample": str(node.get("sample", ""))[:200],
                })
            children = node.get("children")
            if isinstance(children, dict):
                # Check if children is a child node itself (has "type" key)
                # vs a dict-of-children (values are nodes)
                if "type" in children:
                    flatten(children)
                else:
                    for child in children.values():
                        flatten(child)
            elif isinstance(children, str):
                pass  # truncated

        flatten(analysis)
        return paths

    @staticmethod
    def _truncate_sample(value: Any) -> Any:
        """Truncate long string/int values for display."""
        if isinstance(value, str) and len(value) > 100:
            return value[:100] + "..."
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
        if isinstance(value, list):
            return f"[{len(value)} items]"
        if isinstance(value, dict):
            return f"{{{len(value)} keys}}"
        return value


# Singleton
api_explorer = APIExplorer()
