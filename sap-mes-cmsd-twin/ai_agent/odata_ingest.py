"""Deterministic SAP OData $metadata ingestion -> SourceSchema -> source-schema RAG.

This is the secure bridge between SAP and the LLM. It:

  1. holds the (decrypted, in-memory) SAP credentials for the duration of a call,
  2. fetches ``$metadata`` (EDMX XML) — the only live SAP call,
  3. parses it into a metadata-only ``SourceSchema`` (no row data),
  4. persists the schema JSON (for UI browsing + the recommender), and
  5. indexes metadata-only chunks into the ``source-schema`` ChromaDB corpus.

The LLM never runs here, never receives credentials, and never sees row data. It
later consumes the indexed metadata via RAG retrieval only.
"""
from __future__ import annotations

import json
import logging
import os

from .config import PROJECT_ROOT
from .connection_manager import connection_manager
from .rag.vector_store import vector_store

from shared.odata.client import ODataClient
from shared.odata.parser import EdmxParser
from shared.odata.source_schema import SourceSchema
from shared.odata.auth import normalize_auth

logger = logging.getLogger("ai-agent.odata-ingest")

# Persisted schema JSON lives inside the shared .agent-mappings volume so it is
# available to both services and survives restarts. {source_id}.json per source.
SCHEMAS_DIR = os.path.join(PROJECT_ROOT, ".agent-mappings", "schemas")


def _ensure_dir() -> str:
    os.makedirs(SCHEMAS_DIR, exist_ok=True)
    return SCHEMAS_DIR


def _schema_path(source_id: str) -> str:
    return os.path.join(_ensure_dir(), f"{source_id}.json")


def _sap_client_of(source: dict) -> str:
    # sap-client may be stored as a top-level field or inside extra_headers
    return str(source.get("sap_client") or source.get("extra_headers", {}).get("sap-client") or "200")


class ODataIngestor:
    """Deterministic ingestion of OData $metadata into a source-schema RAG corpus."""

    async def discover(self, source_id: str, entity_set_filter: list[str] | None = None) -> dict:
        """Fetch $metadata for a source, parse, persist, and index the source-schema corpus."""
        source = connection_manager.get_source(source_id)
        if not source:
            raise ValueError(f"Source '{source_id}' not found")
        base_url = source.get("base_url", "")
        if not base_url:
            raise ValueError(f"Source '{source_id}' has no base_url")

        client = ODataClient(base_url, normalize_auth(source), sap_client=_sap_client_of(source))
        xml = await client.fetch_metadata()
        logger.info(f"discovered $metadata for {source_id}: {len(xml)} bytes")

        schema = EdmxParser().parse(xml, service_url=base_url)
        if entity_set_filter:
            wanted = set(entity_set_filter)
            schema.entity_types = [et for et in schema.entity_types if et.entity_set_name in wanted]

        # Persist metadata-only schema JSON (shared volume)
        with open(_schema_path(source_id), "w", encoding="utf-8") as f:
            json.dump(schema.to_dict(), f, indent=2)

        # Index metadata-only chunks into the source-schema RAG corpus. SchemaChunk is
        # compatible with vector_store.index_documents (exposes .content + .metadata).
        chunks = schema.to_chunks(source_id=source_id)
        indexed = vector_store.index_documents(chunks) if chunks else 0
        logger.info(f"indexed {indexed} source-schema chunks for {source_id}")

        return {
            "success": True,
            "source_schema_id": source_id,
            "entity_sets": [self._summary(et) for et in schema.entity_types],
            "chunks_indexed": indexed,
        }

    def load_schema(self, source_id: str, entity_set: str | None = None) -> SourceSchema | None:
        """Load a persisted SourceSchema; optionally filter to one entity set."""
        path = _schema_path(source_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            schema = SourceSchema.from_dict(json.load(f))
        if entity_set:
            schema.entity_types = [et for et in schema.entity_types if et.entity_set_name == entity_set]
        return schema

    async def sample(self, source_id: str, entity_set: str, top: int = 3) -> dict:
        """Fetch a few rows from a SAP OData entity set for LOCAL UI preview only.

        Row data is returned to the browser; it is NEVER sent to the LLM and NEVER
        indexed in RAG. This is the only ingestor method that returns row data.
        """
        source = connection_manager.get_source(source_id)
        if not source:
            raise ValueError(f"Source '{source_id}' not found")
        client = ODataClient(source["base_url"], normalize_auth(source), sap_client=_sap_client_of(source))
        data = await client.fetch_entity_set(entity_set, top=top)
        rows = []
        if isinstance(data, dict):
            d = data.get("d", data)
            rows = d.get("results", []) if isinstance(d, dict) else []
        return {"rows": rows[:top], "count": len(rows), "entity_set": entity_set}

    @staticmethod
    def _summary(et) -> dict:
        return {
            "name": et.entity_set_name,
            "entity_type": et.name,
            "sap_label": et.sap_label,
            "key_fields": list(et.keys),
            "property_count": len(et.properties),
            "navigation_count": len(et.navigation_properties),
        }


# Singleton
odata_ingestor = ODataIngestor()