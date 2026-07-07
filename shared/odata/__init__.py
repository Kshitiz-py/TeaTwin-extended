"""OData / SAP integration package.

This package is the deterministic bridge to SAP OData services:

  * ``parser``    — EDMX/CSDL -> SourceSchema (metadata only)
  * ``source_schema`` — SourceSchema dataclasses + JSON (de)serialization + RAG chunks
  * ``client``    — OData v2 HTTP client (the only code that connects to SAP)
  * ``auth``      — normalized auth -> HTTP headers
  * ``units``     — SAP unit-code -> CMSD unit + conversion factor (runtime only)

The LLM never imports or calls into this package directly; it only consumes the
metadata-only RAG chunks produced from a ``SourceSchema``.
"""
from .source_schema import (
    SourceSchema,
    ODataEntityType,
    ODataProperty,
    ODataNavigationProperty,
    SchemaChunk,
)
from .parser import EdmxParser
from .client import ODataClient
from .auth import build_auth_headers
from .units import convert_factor, unit_name_for

__all__ = [
    "SourceSchema",
    "ODataEntityType",
    "ODataProperty",
    "ODataNavigationProperty",
    "SchemaChunk",
    "EdmxParser",
    "ODataClient",
    "build_auth_headers",
    "convert_factor",
    "unit_name_for",
]