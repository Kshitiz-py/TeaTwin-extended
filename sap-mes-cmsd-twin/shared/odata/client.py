"""OData v2 HTTP client — the ONLY code that connects to SAP.

This module holds credentials (decrypted in-memory for the duration of a call) and
performs GET requests: ``$metadata`` (EDMX XML), the service document, and
entity-set rows (``d.results``). The LLM never calls this client and never receives
credentials. Row data fetched here flows only to deterministic consumers
(``MappingDrivenFactory`` at runtime; the local-only ``/sources/{id}/sample`` UI
preview).

GET-only. Writes (POST/PUT/MERGE/DELETE) require a SAP CSRF token and are out of
scope for this slice; the digital twin is a read-only consumer of SAP data.
"""
from __future__ import annotations

from urllib.parse import quote

import httpx

from .auth import build_auth_headers


class ODataClient:
    def __init__(self, base_url: str, auth: dict | None = None,
                 sap_client: str = "200", timeout: float = 30.0):
        self.base_url = (base_url or "").rstrip("/")
        self.auth = auth or {"type": "none"}
        self.sap_client = sap_client
        self.timeout = timeout

    # ── URL/header building (pure, unit-testable) ─────────────────────────
    def _common_params(self) -> dict:
        return {"sap-client": self.sap_client}

    def _request_headers(self, accept: str, data_version: bool = False) -> dict:
        h = {"Accept": accept}
        if data_version:
            h["DataServiceVersion"] = "2.0"
        h.update(build_auth_headers(self.auth))
        return h

    def _build_url(self, path: str, params: dict | None = None) -> str:
        path = path if path.startswith("/") else f"/{path}"
        q = self._common_params()
        if params:
            q.update(params)
        # Preserve OData "$" query keys literally (SAP + the working test use "$top",
        # "$format", "$select"); only quote the *values*.
        query = "&".join(f"{k}={quote(str(v), safe='')}" for k, v in q.items())
        return f"{self.base_url}{path}?{query}"

    # ── Live GETs (called by the deterministic ingestor / runtime) ──────────
    async def fetch_metadata(self) -> str:
        url = self._build_url("$metadata")
        headers = self._request_headers("application/xml")
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.get(url, headers=headers)
            r.raise_for_status()
            return r.text

    async def fetch_service_document(self) -> dict:
        url = self._build_url("", {"$format": "json"})
        headers = self._request_headers("application/json", data_version=True)
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.get(url, headers=headers)
            r.raise_for_status()
            return r.json()

    async def fetch_entity_set(self, entity_set: str, top: int = 5,
                              select: str | None = None) -> dict:
        params = {"$format": "json", "$top": str(top)}
        if select:
            params["$select"] = select
        url = self._build_url(entity_set, params)
        headers = self._request_headers("application/json", data_version=True)
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.get(url, headers=headers)
            r.raise_for_status()
            return r.json()