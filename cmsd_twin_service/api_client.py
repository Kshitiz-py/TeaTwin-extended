"""
HTTP client for fetching data from Mock SAP and MES APIs.
All methods are async using httpx.
"""

import base64
import httpx
import logging
from typing import Any

from .config import SAP_API_BASE, MES_API_BASE

logger = logging.getLogger("cmsd-twin.api-client")


class APIClient:
    """Async HTTP client wrapping calls to SAP and MES APIs."""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    async def _get(self, url: str) -> dict[str, Any]:
        if not self._client:
            raise RuntimeError("APIClient not opened via async context manager")
        resp = await self._client.get(url)
        resp.raise_for_status()
        return resp.json()

    # ─── Generic fetch (for mapping-driven factory) ──────────

    async def fetch(self, url: str, method: str = "GET",
                    headers: dict | None = None,
                    auth_config: dict | None = None,
                    params: dict | None = None) -> dict[str, Any]:
        """Generic fetch for any URL with optional auth + query params.

        ``params`` is passed through to httpx as URL query parameters — used by the
        OData runtime path for ``sap-client``/``$format``/``$top``/``$select``.
        """
        if not self._client:
            raise RuntimeError("APIClient not opened via async context manager")

        request_headers = {}
        if auth_config:
            request_headers.update(self._build_auth_headers(auth_config))
        if headers:
            request_headers.update(headers)

        if method.upper() == "GET":
            resp = await self._client.get(url, headers=request_headers, params=params)
        elif method.upper() == "POST":
            resp = await self._client.post(url, headers=request_headers, params=params)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        resp.raise_for_status()
        return resp.json()

    def _build_auth_headers(self, auth_config: dict) -> dict:
        """Build authentication headers from auth config."""
        auth_type = auth_config.get("type", "").lower()
        if auth_type == "bearer":
            return {"Authorization": f"Bearer {auth_config['token']}"}
        elif auth_type == "basic":
            creds = base64.b64encode(
                f"{auth_config['username']}:{auth_config['password']}".encode()
            ).decode()
            return {"Authorization": f"Basic {creds}"}
        elif auth_type == "apikey":
            header_name = auth_config.get("header", "X-API-Key")
            return {header_name: auth_config["key"]}
        elif auth_type == "none" or not auth_type:
            return {}
        else:
            logger.warning(f"Unknown auth type: {auth_type}")
            return {}

    # ─── SAP Endpoints ──────────────────────────────────────────

    async def get_resources(self) -> dict:
        return await self._get(f"{SAP_API_BASE}/resources")

    async def get_resource(self, identifier: str) -> dict:
        return await self._get(f"{SAP_API_BASE}/resources/{identifier}")

    async def get_resource_classes(self) -> dict:
        return await self._get(f"{SAP_API_BASE}/resource-classes")

    async def get_part_types(self) -> dict:
        return await self._get(f"{SAP_API_BASE}/part-types")

    async def get_parts(self) -> dict:
        return await self._get(f"{SAP_API_BASE}/parts")

    async def get_boms(self) -> dict:
        return await self._get(f"{SAP_API_BASE}/boms")

    async def get_process_plans(self) -> dict:
        return await self._get(f"{SAP_API_BASE}/process-plans")

    async def get_process_plan(self, identifier: str) -> dict:
        return await self._get(f"{SAP_API_BASE}/process-plans/{identifier}")

    async def get_calendars(self) -> dict:
        return await self._get(f"{SAP_API_BASE}/calendars")

    async def get_orders(self) -> dict:
        return await self._get(f"{SAP_API_BASE}/orders")

    async def get_layouts(self) -> dict:
        return await self._get(f"{SAP_API_BASE}/layouts")

    async def get_layout(self, identifier: str) -> dict:
        return await self._get(f"{SAP_API_BASE}/layouts/{identifier}")

    async def get_connections(self) -> dict:
        return await self._get(f"{SAP_API_BASE}/connections")

    # ─── MES Endpoints ──────────────────────────────────────────

    async def get_resource_statuses(self) -> dict:
        return await self._get(f"{MES_API_BASE}/resource-status")

    async def get_jobs(self) -> dict:
        return await self._get(f"{MES_API_BASE}/jobs")

    async def get_inventory(self) -> dict:
        return await self._get(f"{MES_API_BASE}/inventory")

    async def get_incidents(self, active_only: bool = False) -> dict:
        url = f"{MES_API_BASE}/incidents"
        if active_only:
            url += "?active_only=true"
        return await self._get(url)