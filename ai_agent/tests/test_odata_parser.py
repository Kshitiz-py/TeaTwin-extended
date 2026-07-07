"""Unit tests for the OData $metadata EDMX parser, SourceSchema, unit table, and client URL building.

No network access — uses a hand-crafted SAP OData v2 EDMX fixture that mirrors the
API_PRODUCTION_ROUTING structure (ProductionRoutingOperation + WorkCenter, a
navigation property, and a referential-constraint join key, plus sap:label and
sap:unit annotations).
"""

from shared.odata.parser import EdmxParser
from shared.odata.source_schema import SourceSchema
from shared.odata.units import convert_factor, unit_name_for
from shared.odata.client import ODataClient


EDMX_FIXTURE = """<?xml version="1.0" encoding="utf-8"?>
<edmx:Edmx xmlns:edmx="http://schemas.microsoft.com/ado/2007/06/edmx"
           xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata"
           xmlns:sap="http://www.sap.com/Protocols/SAPData"
           Version="1.0">
  <edmx:DataServices m:DataServiceVersion="2.0">
    <Schema xmlns="http://schemas.microsoft.com/ado/2008/09/edm" Namespace="API_PRODUCTION_ROUTING" xml:lang="en">
      <EntityType Name="ProductionRoutingOperationType" sap:label="Production Routing Operation">
        <Key>
          <PropertyRef Name="ProductionRoutingGroup"/>
          <PropertyRef Name="ProductionRouting"/>
          <PropertyRef Name="ProductionRoutingSequence"/>
          <PropertyRef Name="ProductionRoutingOpIntID"/>
          <PropertyRef Name="ProductionRoutingOpIntVersion"/>
        </Key>
        <Property Name="WorkCenter" Type="Edm.String" Nullable="true" MaxLength="8" sap:label="Work Center"/>
        <Property Name="WorkCenterInternalID" Type="Edm.String" Nullable="false" MaxLength="10" sap:label="Work Center Internal ID"/>
        <Property Name="Operation" Type="Edm.String" Nullable="false" MaxLength="4" sap:label="Operation"/>
        <Property Name="OperationText" Type="Edm.String" Nullable="true" MaxLength="40" sap:label="Operation Short Text"/>
        <Property Name="StandardWorkQuantity1" Type="Edm.Decimal" Nullable="true" Precision="9" Scale="3" sap:label="Standard Work Quantity 1" sap:unit="StandardWorkQuantityUnit1"/>
        <Property Name="StandardWorkQuantityUnit1" Type="Edm.String" Nullable="true" MaxLength="3" sap:label="Unit for Std Work Quantity 1"/>
        <NavigationProperty Name="WorkCenter_2" FromRole="ProductionRoutingOperation" ToRole="WorkCenter_2" Relationship="API_PRODUCTION_ROUTING.ProductionRoutingOperation_WorkCenter_2"/>
      </EntityType>
      <EntityType Name="WorkCenterType" sap:label="Work Center">
        <Key>
          <PropertyRef Name="WorkCenter"/>
        </Key>
        <Property Name="WorkCenter" Type="Edm.String" Nullable="false" MaxLength="8" sap:label="Work Center"/>
        <Property Name="WorkCenterInternalID" Type="Edm.String" Nullable="false" MaxLength="10" sap:label="Work Center Internal ID"/>
        <Property Name="WorkCenterTypeCode" Type="Edm.String" Nullable="true" sap:label="Work Center Category"/>
      </EntityType>
      <Association Name="ProductionRoutingOperation_WorkCenter_2">
        <End Role="ProductionRoutingOperation" Type="API_PRODUCTION_ROUTING.ProductionRoutingOperationType" Multiplicity="*"/>
        <End Role="WorkCenter_2" Type="API_PRODUCTION_ROUTING.WorkCenterType" Multiplicity="0..1"/>
        <ReferentialConstraint>
          <Principal Role="WorkCenter_2">
            <PropertyRef Name="WorkCenter"/>
          </Principal>
          <Dependent Role="ProductionRoutingOperation">
            <PropertyRef Name="WorkCenter"/>
          </Dependent>
        </ReferentialConstraint>
      </Association>
      <EntityContainer Name="API_PRODUCTION_ROUTING" m:IsDefaultEntityContainer="true">
        <EntitySet Name="ProductionRoutingOperation" EntityType="API_PRODUCTION_ROUTING.ProductionRoutingOperationType" sap:creatable="false" sap:updatable="false" sap:deletable="false"/>
        <EntitySet Name="WorkCenter" EntityType="API_PRODUCTION_ROUTING.WorkCenterType" sap:creatable="false"/>
      </EntityContainer>
    </Schema>
  </edmx:DataServices>
</edmx:Edmx>
"""

SVC_URL = "https://a33p.ucc.cloud/sap/opu/odata/sap/API_PRODUCTION_ROUTING"


def _schema():
    return EdmxParser().parse(EDMX_FIXTURE, service_url=SVC_URL)


def test_parse_entity_types_and_keys():
    schema = _schema()
    by_name = {et.name: et for et in schema.entity_types}
    assert {"ProductionRoutingOperationType", "WorkCenterType"} <= set(by_name)
    pr = by_name["ProductionRoutingOperationType"]
    assert pr.entity_set_name == "ProductionRoutingOperation"
    assert "ProductionRoutingGroup" in pr.keys
    assert len(pr.keys) == 5
    assert pr.sap_label == "Production Routing Operation"
    wc = by_name["WorkCenterType"]
    assert wc.entity_set_name == "WorkCenter"
    assert wc.keys == ["WorkCenter"]


def test_parse_properties_with_sap_annotations():
    pr = {et.name: et for et in _schema().entity_types}["ProductionRoutingOperationType"]
    by_prop = {p.name: p for p in pr.properties}
    swq = by_prop["StandardWorkQuantity1"]
    assert swq.type == "Edm.Decimal"
    assert swq.sap_unit == "StandardWorkQuantityUnit1"
    assert swq.sap_label == "Standard Work Quantity 1"
    assert swq.nullable is True
    wci = by_prop["WorkCenterInternalID"]
    assert wci.nullable is False
    assert wci.is_key is False  # not a key of ProductionRoutingOperationType
    wc = {et.name: et for et in _schema().entity_types}["WorkCenterType"]
    assert {p.name: p.is_key for p in wc.properties}["WorkCenter"] is True


def test_navigation_property_join_keys():
    pr = {et.name: et for et in _schema().entity_types}["ProductionRoutingOperationType"]
    nav = {n.name: n for n in pr.navigation_properties}["WorkCenter_2"]
    assert nav.to_entity_type == "WorkCenterType"
    # Oriented join key: this.WorkCenter = target.WorkCenter
    assert nav.referential_constraints == [("WorkCenter", "WorkCenter")]


def test_to_dict_roundtrip():
    schema = _schema()
    d = schema.to_dict()
    assert d["service_url"] == SVC_URL
    assert len(d["entity_types"]) == 2
    back = SourceSchema.from_dict(d)
    assert {et.name for et in back.entity_types} == {"ProductionRoutingOperationType", "WorkCenterType"}
    pr = {et.name: et for et in back.entity_types}["ProductionRoutingOperationType"]
    assert pr.entity_set_name == "ProductionRoutingOperation"
    nav = {n.name: n for n in pr.navigation_properties}["WorkCenter_2"]
    assert nav.referential_constraints == [("WorkCenter", "WorkCenter")]


def test_to_chunks_metadata_only():
    schema = _schema()
    chunks = schema.to_chunks(source_id="sap-a33p")
    assert len(chunks) == 2
    by_set = {c.metadata["entity_set"]: c for c in chunks}
    assert all(c.metadata["collection"] == "source-schema" for c in chunks)
    assert all(c.metadata["source_id"] == "sap-a33p" for c in chunks)
    assert all(c.metadata["filename"] == "sap-a33p" for c in chunks)
    pr_text = by_set["ProductionRoutingOperation"].content
    # Metadata is present
    assert "ProductionRoutingOperation" in pr_text
    assert "StandardWorkQuantity1" in pr_text
    assert "Edm.Decimal" in pr_text
    assert "sap:unit=StandardWorkQuantityUnit1" in pr_text
    assert "WorkCenter_2" in pr_text  # navigation property listed
    assert "join: this.WorkCenter = target.WorkCenter" in pr_text
    # Metadata only — no OData row-data markers
    assert "d.results" not in pr_text
    assert "__metadata" not in pr_text


def test_units_table():
    assert convert_factor("MIN", "second") == 60.0
    assert convert_factor("HUR", "second") == 3600.0
    assert convert_factor("SEC", "second") == 1.0
    assert convert_factor("DAY", "second") == 86400.0
    # Same-unit conversion
    assert convert_factor("MIN", "minute") == 1.0
    # Cross-target
    assert convert_factor("HUR", "minute") == 60.0
    # Unknown SAP unit -> None (coverage gap; runtime leaves value as-is)
    assert convert_factor("KG", "second") is None
    assert convert_factor("", "second") is None
    # Unknown target -> None
    assert convert_factor("MIN", "parsec") is None
    # Case-insensitive lookup
    assert convert_factor("min", "second") == 60.0
    assert unit_name_for("MIN") == "minute"
    assert unit_name_for("KG") is None


def test_client_url_and_headers():
    c = ODataClient(
        base_url="https://a33p.ucc.cloud/sap/opu/odata/sap/API_PRODUCTION_ROUTING/",
        auth={"type": "basic", "username": "u", "password": "p"},
        sap_client="200",
    )
    # $metadata URL (no $format)
    meta = c._build_url("$metadata")
    assert meta == "https://a33p.ucc.cloud/sap/opu/odata/sap/API_PRODUCTION_ROUTING/$metadata?sap-client=200"
    # Entity-set URL preserves "$" literally
    es = c._build_url("ProductionRoutingOperation", {"$format": "json", "$top": "5"})
    assert "$format=json" in es and "$top=5" in es and "sap-client=200" in es
    # Basic auth header
    h = c._request_headers("application/xml")
    assert h["Accept"] == "application/xml"
    assert h["Authorization"].startswith("Basic ")
    # Data version header on data calls
    h2 = c._request_headers("application/json", data_version=True)
    assert h2["DataServiceVersion"] == "2.0"