from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List

from .basic_types import ConnectionType
from .basic_structures import Length, MeasuredValue
from .entity_reference_definition import ResourceReference
from .identifiable_entity import IdentifiableEntity


# =============================================================================
# CONNECTION ENTITIES (from Connection.rng)
# =============================================================================

class PathSegment(BaseModel):
    """Physical properties of a transport route segment (maps Transportweg concept)"""
    length: Optional[Length] = Field(None, description="Length of the path segment")
    width: Optional[Length] = Field(None, description="Width of the path segment (Transportweg.breite_meter)")
    speed_limit: Optional[MeasuredValue] = Field(None, description="Speed limit on the segment (Transportweg.geschwindigkeitslimit_ms)")
    vehicle_capacity: Optional[int] = Field(None, description="Maximum vehicle capacity (Transportweg.kapazitaet)")
    is_bidirectional: Optional[bool] = Field(None, description="Whether the segment allows bidirectional travel")
    overtaking_allowed: Optional[bool] = Field(None, description="Whether overtaking is allowed (Transportweg.ueberholmoeglichkeit)")
    access_restrictions: List[str] = Field(default_factory=list, description="Access restrictions for the segment (Transportweg.befahrensrestriktion)")


class Connection(IdentifiableEntity):
    """A directed connection between two resources (e.g., conveyor link, path)"""
    connection_type: ConnectionType = Field(..., description="Whether this is an input or output connection")
    from_resource: Optional[ResourceReference] = Field(None, description="Origin resource of the connection")
    to_resource: Optional[ResourceReference] = Field(None, description="Destination resource of the connection")
    from_resource_frame: Optional[str] = Field(None, description="3D connection frame at the origin resource (Zhao 2024, Table 1)")
    to_resource_frame: Optional[str] = Field(None, description="3D connection frame at the destination resource (Zhao 2024, Table 1)")
    path_segment: Optional[PathSegment] = Field(None, description="Physical properties of the transport route segment")
