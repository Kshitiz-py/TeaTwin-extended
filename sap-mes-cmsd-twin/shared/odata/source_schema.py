"""SourceSchema — structured representation of a parsed OData $metadata document.

METADATA ONLY. These structures never hold SAP row data; they are derived solely
from the ``$metadata`` EDMX/CSDL document (entity/property names, types,
``sap:label``, keys, navigation properties, referential constraints).

A ``SourceSchema`` is:
  * persisted to ``.agent-schemas/{source_id}.json`` for UI browsing, and
  * turned into RAG chunks (``to_chunks``) so the LLM can map with source-side
    semantics (metadata only — never row data).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class ODataProperty:
    name: str
    type: str                       # "Edm.String", "Edm.Decimal", ...
    nullable: bool = True
    is_key: bool = False
    sap_label: str = ""             # sap:label — human-readable field name
    sap_unit: str = ""             # sap:unit — companion property holding the unit code
    sap_semantics: str = ""        # sap:semantics (e.g. "amount", "currency")
    max_length: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ODataProperty":
        return cls(**{
            "name": d.get("name", ""),
            "type": d.get("type", ""),
            "nullable": d.get("nullable", True),
            "is_key": d.get("is_key", False),
            "sap_label": d.get("sap_label", ""),
            "sap_unit": d.get("sap_unit", ""),
            "sap_semantics": d.get("sap_semantics", ""),
            "max_length": d.get("max_length"),
        })


@dataclass
class ODataNavigationProperty:
    name: str
    to_entity_type: str = ""
    from_role: str = ""
    to_role: str = ""
    relationship: str = ""          # "Namespace.AssociationName"
    # Oriented join keys: (property_on_this_type, property_on_target_type)
    referential_constraints: list[tuple[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        # tuples serialize as lists; keep them as lists for JSON-friendliness
        d["referential_constraints"] = [list(x) for x in self.referential_constraints]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ODataNavigationProperty":
        return cls(
            name=d.get("name", ""),
            to_entity_type=d.get("to_entity_type", ""),
            from_role=d.get("from_role", ""),
            to_role=d.get("to_role", ""),
            relationship=d.get("relationship", ""),
            referential_constraints=[tuple(x) for x in d.get("referential_constraints", [])],
        )


@dataclass
class ODataEntityType:
    name: str                       # EntityType name, e.g. "ProductionRoutingOperationType"
    entity_set_name: str = ""       # EntitySet name, e.g. "ProductionRoutingOperation"
    properties: list[ODataProperty] = field(default_factory=list)
    keys: list[str] = field(default_factory=list)
    navigation_properties: list[ODataNavigationProperty] = field(default_factory=list)
    sap_label: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "entity_set_name": self.entity_set_name,
            "properties": [p.to_dict() for p in self.properties],
            "keys": list(self.keys),
            "navigation_properties": [n.to_dict() for n in self.navigation_properties],
            "sap_label": self.sap_label,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ODataEntityType":
        return cls(
            name=d.get("name", ""),
            entity_set_name=d.get("entity_set_name", ""),
            properties=[ODataProperty.from_dict(p) for p in d.get("properties", [])],
            keys=list(d.get("keys", [])),
            navigation_properties=[ODataNavigationProperty.from_dict(n) for n in d.get("navigation_properties", [])],
            sap_label=d.get("sap_label", ""),
        )

    def to_chunk_text(self, service_url: str, source_id: str) -> str:
        """Render this entity type as metadata-only prose for the RAG corpus."""
        lines: list[str] = [
            f"SAP OData EntitySet: {self.entity_set_name}",
            f"Service: {service_url}",
        ]
        if source_id:
            lines.append(f"Source: {source_id}")
        lines.append(f"EntityType: {self.name}")
        if self.sap_label:
            lines.append(f"sap:label: {self.sap_label}")
        if self.keys:
            lines.append(f"Keys: {', '.join(self.keys)}")
        lines.append("")
        lines.append("Properties:")
        for p in self.properties:
            base = f"- {p.name} ({p.type}, nullable={str(p.nullable).lower()}"
            if p.is_key:
                base += ", KEY"
            base += ")"
            if p.sap_label:
                base += f' — sap:label="{p.sap_label}"'
            if p.sap_unit:
                base += f", sap:unit={p.sap_unit}"
            if p.sap_semantics:
                base += f", sap:semantics={p.sap_semantics}"
            lines.append(base)
        if self.navigation_properties:
            lines.append("")
            lines.append("Navigation Properties:")
            for n in self.navigation_properties:
                head = f"- {n.name} -> {n.to_entity_type}"
                if n.referential_constraints:
                    joins = ", ".join(f"this.{a} = target.{b}" for a, b in n.referential_constraints)
                    head += f"  [join: {joins}]"
                lines.append(head)
        return "\n".join(lines)


@dataclass
class SourceSchema:
    service_url: str
    namespace: str = ""
    entity_types: list[ODataEntityType] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "service_url": self.service_url,
            "namespace": self.namespace,
            "entity_types": [et.to_dict() for et in self.entity_types],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SourceSchema":
        return cls(
            service_url=d.get("service_url", ""),
            namespace=d.get("namespace", ""),
            entity_types=[ODataEntityType.from_dict(e) for e in d.get("entity_types", [])],
        )

    def to_chunks(self, source_id: str = "") -> list["SchemaChunk"]:
        """One metadata-only chunk per EntityType for the ``source-schema`` RAG corpus.

        Metadata tags mirror the existing chunk conventions (``collection``,
        ``filename``, ...) so ``vector_store.index_documents`` produces stable IDs
        of the form ``source-schema_{source_id}_{i}`` (idempotent re-discovery).
        """
        chunks: list[SchemaChunk] = []
        for et in self.entity_types:
            chunks.append(SchemaChunk(
                content=et.to_chunk_text(self.service_url, source_id),
                metadata={
                    "collection": "source-schema",
                    "source_id": source_id,
                    "entity_set": et.entity_set_name,
                    "entity_type": et.name,
                    "filename": source_id or "metadata",
                    "description": "OData $metadata source schema (entity/property names, types, sap:label, keys, navigation properties — metadata only)",
                    "type": "odata-schema",
                },
            ))
        return chunks


@dataclass
class SchemaChunk:
    """Lightweight chunk object exposing ``.content`` and ``.metadata``.

    Compatible with ``vector_store.index_documents`` (which reads only those two
    attributes plus ``metadata['collection']``/``metadata['filename']``). Kept
    local to ``shared`` so this package does not depend on ``ai_agent``.
    """
    content: str
    metadata: dict[str, Any]