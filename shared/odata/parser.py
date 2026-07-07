"""EDMX/CSDL parser for SAP OData v2 ``$metadata`` documents.

Produces a ``SourceSchema`` (METADATA ONLY — entity/property names, types,
``sap:label``, keys, navigation properties, and referential constraints). No row
data is ever read or produced here; ``$metadata`` is schema, not data.

SAP OData v2 namespace notes (handled by local-name matching plus a collected
namespace map, so exact URIs don't matter):
  * edmx: http://schemas.microsoft.com/ado/2007/06/edmx
  * edm : http://schemas.microsoft.com/ado/2008/09/edm  (also 2006/04/edm)
  * sap : http://www.sap.com/Protocols/SAPData
          (sap:label, sap:unit, sap:semantics, sap:creatable, ...)
"""
from __future__ import annotations

import io
import logging
import xml.etree.ElementTree as ET

from .source_schema import (
    SourceSchema,
    ODataEntityType,
    ODataProperty,
    ODataNavigationProperty,
)

logger = logging.getLogger("shared.odata.parser")

_KNOWN_SAP_URIS = (
    "http://www.sap.com/Protocols/SAPData",
    "http://www.sap.com/Protocols/DataDocumentation",
)


def _local(tag: str) -> str:
    """Strip the XML namespace prefix: ``{uri}local`` -> ``local``."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _children(elem, local: str):
    """Direct children of ``elem`` whose local name equals ``local``."""
    return [c for c in elem if _local(c.tag) == local]


def _find_child(elem, local: str):
    for c in elem:
        if _local(c.tag) == local:
            return c
    return None


def _collect_ns_map(xml_text: str) -> dict[str, str]:
    """prefix -> uri, from the document's xmlns declarations (iterparse start-ns)."""
    ns_map: dict[str, str] = {}
    try:
        for _event, val in ET.iterparse(io.BytesIO(xml_text.encode("utf-8")), events=["start-ns"]):
            prefix, uri = val  # type: ignore[misc]
            ns_map[prefix] = uri
    except Exception as e:  # pragma: no cover - defensive
        logger.warning(f"namespace collection failed: {e}")
    return ns_map


def _sap_attr(elem, ns_map: dict[str, str], local: str) -> str:
    """Read a ``sap:<local>`` attribute, tolerating either the declared ``sap``
    prefix uri or the known SAP URIs (in case namespace collection missed it)."""
    candidates = []
    uri = ns_map.get("sap")
    if uri:
        candidates.append(f"{{{uri}}}{local}")
    for u in _KNOWN_SAP_URIS:
        candidates.append(f"{{{u}}}{local}")
    for c in candidates:
        if c in elem.attrib:
            return elem.attrib[c]
    return ""


def _strip_namespace(qualified: str) -> str:
    """``N.EntityTypeName`` -> ``EntityTypeName``."""
    if not qualified:
        return qualified
    return qualified.rsplit(".", 1)[-1]


def _bool(val, default: bool) -> bool:
    if val is None:
        return default
    return str(val).strip().lower() == "true"


def _int_or_none(val):
    if val is None or val == "":
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


class EdmxParser:
    """Parse a SAP OData v2 ``$metadata`` EDMX document into a ``SourceSchema``."""

    def parse(self, xml_text: str, service_url: str = "") -> SourceSchema:
        ns_map = _collect_ns_map(xml_text)
        root = ET.fromstring(xml_text)

        entity_types: dict[str, ODataEntityType] = {}   # type_name -> EntityType
        associations: dict[str, dict] = {}              # assoc_name -> record
        namespace = ""

        for schema in self._iter_local(root, "Schema"):
            namespace = namespace or schema.attrib.get("Namespace", "")
            for et_elem in _children(schema, "EntityType"):
                et = self._parse_entity_type(et_elem, ns_map)
                if et.name:
                    entity_types[et.name] = et
            for assoc_elem in _children(schema, "Association"):
                rec = self._parse_association(assoc_elem)
                if rec["name"]:
                    associations[rec["name"]] = rec
            for container in _children(schema, "EntityContainer"):
                for es_elem in _children(container, "EntitySet"):
                    name = es_elem.attrib.get("Name", "")
                    etype = _strip_namespace(es_elem.attrib.get("EntityType", ""))
                    if name and etype in entity_types:
                        entity_types[etype].entity_set_name = name

        # Resolve navigation properties against associations (to_entity_type + join keys)
        for et in entity_types.values():
            for nav in et.navigation_properties:
                assoc_name = _strip_namespace(nav.relationship)
                rec = associations.get(assoc_name)
                if not rec:
                    continue
                for end in rec["ends"]:
                    if end["role"] == nav.to_role:
                        nav.to_entity_type = _strip_namespace(end["type"])
                        break
                nav.referential_constraints = self._orient_constraints(rec, nav.from_role, nav.to_role)

        return SourceSchema(
            service_url=service_url,
            namespace=namespace,
            entity_types=list(entity_types.values()),
        )

    def _iter_local(self, root, local: str):
        return [e for e in root.iter() if _local(e.tag) == local]

    def _parse_entity_type(self, et_elem, ns_map: dict[str, str]) -> ODataEntityType:
        name = et_elem.attrib.get("Name", "")
        keys: list[str] = []
        key_elem = _find_child(et_elem, "Key")
        if key_elem is not None:
            keys = [pr.attrib.get("Name", "") for pr in _children(key_elem, "PropertyRef")]
        props: list[ODataProperty] = []
        for p in _children(et_elem, "Property"):
            pname = p.attrib.get("Name", "")
            props.append(ODataProperty(
                name=pname,
                type=p.attrib.get("Type", ""),
                nullable=_bool(p.attrib.get("Nullable"), True),
                is_key=(pname in keys),
                sap_label=_sap_attr(p, ns_map, "label"),
                sap_unit=_sap_attr(p, ns_map, "unit"),
                sap_semantics=_sap_attr(p, ns_map, "semantics"),
                max_length=_int_or_none(p.attrib.get("MaxLength")),
            ))
        navs: list[ODataNavigationProperty] = []
        for n in _children(et_elem, "NavigationProperty"):
            navs.append(ODataNavigationProperty(
                name=n.attrib.get("Name", ""),
                from_role=n.attrib.get("FromRole", ""),
                to_role=n.attrib.get("ToRole", ""),
                relationship=n.attrib.get("Relationship", ""),
            ))
        return ODataEntityType(
            name=name,
            entity_set_name="",
            properties=props,
            keys=keys,
            navigation_properties=navs,
            sap_label=_sap_attr(et_elem, ns_map, "label"),
        )

    def _parse_association(self, assoc_elem) -> dict:
        ends = []
        for end in _children(assoc_elem, "End"):
            ends.append({
                "role": end.attrib.get("Role", ""),
                "type": end.attrib.get("Type", ""),
                "multiplicity": end.attrib.get("Multiplicity", ""),
            })
        principal_role, principal_props = "", []
        dependent_role, dependent_props = "", []
        rc = _find_child(assoc_elem, "ReferentialConstraint")
        if rc is not None:
            pr = _find_child(rc, "Principal")
            dp = _find_child(rc, "Dependent")
            if pr is not None:
                principal_role = pr.attrib.get("Role", "")
                principal_props = [x.attrib.get("Name", "") for x in _children(pr, "PropertyRef")]
            if dp is not None:
                dependent_role = dp.attrib.get("Role", "")
                dependent_props = [x.attrib.get("Name", "") for x in _children(dp, "PropertyRef")]
        return {
            "name": assoc_elem.attrib.get("Name", ""),
            "ends": ends,
            "principal_role": principal_role,
            "principal_props": principal_props,
            "dependent_role": dependent_role,
            "dependent_props": dependent_props,
        }

    def _orient_constraints(self, rec: dict, from_role: str, to_role: str) -> list[tuple[str, str]]:
        """Orient the association's (dependent_prop, principal_prop) pairs relative to
        the navigation property's *this* side (``from_role``) and *target* side
        (``to_role``). Returns a list of ``(this_side_prop, target_side_prop)`` join keys.
        """
        pairs = list(zip(rec["dependent_props"], rec["principal_props"]))
        result: list[tuple[str, str]] = []
        for dep_prop, prin_prop in pairs:
            if from_role == rec["dependent_role"] and to_role == rec["principal_role"]:
                result.append((dep_prop, prin_prop))      # this=dependent, target=principal
            elif from_role == rec["principal_role"] and to_role == rec["dependent_role"]:
                result.append((prin_prop, dep_prop))      # this=principal, target=dependent
            else:
                # roles don't line up cleanly — emit dependent-first as best effort
                result.append((dep_prop, prin_prop))
        return result