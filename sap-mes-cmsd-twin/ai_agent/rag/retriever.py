"""
Retriever — High-level RAG retrieval with context assembly for agent prompts.
"""

import logging
from typing import List, Dict, Any

from .vector_store import vector_store

logger = logging.getLogger("ai-agent.retriever")


class Retriever:
    """RAG retriever that queries the vector store and assembles context for LLM prompts."""

    def __init__(self):
        self.vs = vector_store

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        collections: list[str] | None = None,
    ) -> list[dict]:
        """
        Retrieve relevant documents for a query.
        Optionally filter by collection names.
        """
        results = self.vs.query(query, n_results=top_k * 3)

        # Filter by collections if specified
        if collections:
            results = [r for r in results if r.get("metadata", {}).get("collection") in collections]

        return results[:top_k]

    def retrieve_for_mapping(
        self,
        data_point_name: str,
        cmsd_entity: str,
        api_endpoint: str | None = None,
        api_payload_sample: str | None = None,
    ) -> str:
        """
        Specialized retrieval for field mapping.
        Assembles context from multiple collections relevant to mapping a data point.
        Returns a formatted context string for the LLM prompt.
        """
        context_parts = []

        # 1. Search data requirements for this data point
        req_results = self.retrieve(
            f"{data_point_name} data requirements CMSD mapping",
            top_k=2,
            collections=["data-requirements"],
        )
        if req_results:
            context_parts.append("### Relevant Data Requirements")
            for r in req_results:
                context_parts.append(f"**Source**: {r['metadata'].get('header', 'Unknown')}\n{r['content'][:500]}")

        # 2. Search CMSD schema for the entity
        schema_results = self.retrieve(
            f"CMSD schema definition for {cmsd_entity} class fields",
            top_k=3,
            collections=["cmsd-schema"],
        )
        if schema_results:
            context_parts.append("### CMSD Schema Reference")
            for r in schema_results:
                context_parts.append(f"**File**: {r['metadata'].get('filename', 'Unknown')}\n{r['content'][:600]}")

        # 3. Search codebase for existing mapping patterns
        code_results = self.retrieve(
            f"CMSD factory build method mapping {cmsd_entity} _build_{cmsd_entity.lower()}",
            top_k=2,
            collections=["codebase"],
        )
        if code_results:
            context_parts.append("### Existing Code Patterns")
            for r in code_results:
                context_parts.append(f"**File**: {r['metadata'].get('filename', 'Unknown')}\n{r['content'][:400]}")

        # 4. Search API docs for endpoint info
        if api_endpoint:
            api_results = self.retrieve(
                f"API endpoint implementation {api_endpoint} route handler",
                top_k=2,
                collections=["api-docs"],
            )
            if api_results:
                context_parts.append("### API Documentation")
                for r in api_results:
                    context_parts.append(f"**File**: {r['metadata'].get('filename', 'Unknown')}\n{r['content'][:400]}")

        return "\n\n".join(context_parts) if context_parts else "No relevant documents found in the knowledge base."

    def retrieve_code_context(self, file_paths: list[str]) -> dict[str, str]:
        """
        Retrieve the full content of specific files from the codebase.
        Used by the Writer agent to see existing code before generating.
        Returns {file_path: content}.
        """
        result = {}
        for fp in file_paths:
            results = self.vs.query(fp, n_results=5)
            results = [r for r in results if r.get("metadata", {}).get("collection") == "codebase"]
            if results:
                best = results[0]
                result[fp] = best.get("content", "")
        return result


# Singleton
retriever = Retriever()