from pydantic import BaseModel, Field, model_validator, ConfigDict
from typing import Optional, List
from decimal import Decimal

from .basic_types import TimeUnit, LengthUnit, WeightUnit, DistributionType


# =============================================================================
# BASIC STRUCTURES (from BasicStructures.rng)
# =============================================================================

class MeasuredValue(BaseModel):
    """Base class for measured values with units"""
    model_config = ConfigDict(use_enum_values=True)

    unit: Optional[str] = Field(None, description="Unit of measurement")
    value: Decimal = Field(..., description="Numeric value")


class ElapsedTime(BaseModel):
    """Elapsed time with unit"""
    unit: Optional[TimeUnit] = Field(None, description="Time unit")
    value: Decimal = Field(..., description="Time value")


class Length(BaseModel):
    """Length measurement with unit"""
    unit: Optional[LengthUnit] = Field(None, description="Length unit")
    value: Decimal = Field(..., description="Length value")


class Weight(BaseModel):
    """Weight measurement with unit"""
    unit: Optional[WeightUnit] = Field(None, description="Weight unit")
    value: Decimal = Field(..., description="Weight value")


class Currency(BaseModel):
    """Currency amount with optional unit (ISO 4217 code)"""
    unit: Optional[str] = Field(None, pattern="[A-Z]{3}", description="3-letter currency code (e.g., USD, EUR)")
    value: Decimal = Field(..., description="Amount")


class GrossDimensions(BaseModel):
    """Gross dimensions (width, depth, height)"""
    unit: Optional[LengthUnit] = Field(None, description="Unit for all dimensions")
    width: Optional[Decimal] = Field(None, description="Width")
    depth: Optional[Decimal] = Field(None, description="Depth")
    height: Optional[Decimal] = Field(None, description="Height")

    @model_validator(mode='after')
    def check_at_least_one_dimension(self):
        if not any([self.width, self.depth, self.height]):
            raise ValueError("At least one dimension (width, depth, or height) must be specified")
        return self


class DistributionParameter(BaseModel):
    """Parameter for a statistical distribution"""
    name: str = Field(..., description="Parameter name")
    description: Optional[str] = None
    value: Decimal = Field(..., description="Parameter value")


class Distribution(BaseModel):
    """Statistical distribution definition"""
    name: str = Field(..., description="Distribution name (e.g., normal, exponential)")
    description: Optional[str] = None
    distribution_type: Optional[DistributionType] = Field(
        None, description="Typed distribution kind; coexists with freeform name (Bergmann §5)"
    )
    distribution_parameters: List[DistributionParameter] = Field(
        ...,
        min_length=1,
        description="Distribution parameters"
    )


class Duration(BaseModel):
    """Duration that can be a fixed value, distribution, or reference"""
    unit: Optional[TimeUnit] = None
    value: Optional[Decimal] = Field(None, description="Fixed duration value")
    distribution: Optional[Distribution] = Field(None, description="Stochastic duration")
    distribution_reference: Optional[str] = Field(None, description="Reference to distribution definition")

    @model_validator(mode='after')
    def check_exactly_one_duration_type(self):
        defined_fields = sum([
            self.value is not None,
            self.distribution is not None,
            self.distribution_reference is not None
        ])
        if defined_fields != 1:
            raise ValueError("Exactly one of value, distribution, or distribution_reference must be specified")
        return self


class Property(BaseModel):
    """Generic property with name-value pair"""
    name: str = Field(..., description="Property name")
    description: Optional[str] = None
    unit: Optional[str] = Field(None, description="Unit of measurement for the property")
    value: Optional[str] = Field(None, description="Property value")
    distribution: Optional[Distribution] = Field(None, description="Stochastic property value")


class LotInformation(BaseModel):
    """Lot/batch information"""
    lot_number: str = Field(..., description="Lot identification number")
    parent_lot_number: Optional[str] = Field(None, description="Parent lot number if applicable")
    description: Optional[str] = None


class LocationDefinition(BaseModel):
    """Location definition within a facility"""
    facility_location: Optional[str] = Field(None, description="Facility identifier")
    within_facility_location: Optional[str] = Field(None, description="Location within facility")
    resource_location: Optional[str] = Field(None, description="Resource identifier for location")

    @model_validator(mode='after')
    def check_at_least_one_location(self):
        if not any([self.facility_location, self.within_facility_location, self.resource_location]):
            raise ValueError("At least one location field must be specified")
        return self


# =============================================================================
# LAYOUT-RELATED STRUCTURES
# =============================================================================

class Coordinate2D(BaseModel):
    """2D coordinate (X, Y)"""
    model_config = ConfigDict(populate_by_name=True)

    x: Decimal = Field(..., description="X coordinate", alias="X")
    y: Decimal = Field(..., description="Y coordinate", alias="Y")


class Coordinate3D(Coordinate2D):
    """3D coordinate (X, Y, Z)"""
    z: Optional[Decimal] = Field(None, description="Z coordinate", alias="Z")


class SpatialDimension(BaseModel):
    """Spatial dimensions (width, depth, optional height)"""
    width: Decimal = Field(..., description="Width")
    depth: Decimal = Field(..., description="Depth")
    height: Optional[Decimal] = Field(None, description="Height")


class BoundaryDefinition(BaseModel):
    """Boundary definition for layout elements"""
    width: Decimal = Field(..., description="Width")
    depth: Decimal = Field(..., description="Depth")
    height: Optional[Decimal] = Field(None, description="Height")
    unit: Optional[str] = Field(None, description="Layout length unit")
    coordinate_system: Optional[str] = Field(None, description="Coordinate system type")


class ColorHighlight(BaseModel):
    """Color highlighting with line color, fill color, and alpha value"""
    line_color: Optional[str] = Field(None, description="Line color (hex or name)")
    fill_color: Optional[str] = Field(None, description="Fill color (hex or name)")
    alpha_value: Optional[int] = Field(None, ge=0, description="Alpha transparency value")
    properties: List[Property] = Field(default_factory=list, description="Additional properties")

    @model_validator(mode='after')
    def check_at_least_one_color(self):
        if not any([self.line_color, self.fill_color, self.alpha_value is not None]):
            raise ValueError("At least one of line_color, fill_color, or alpha_value must be specified")
        return self


class ShapeLabelDefinition(BaseModel):
    """Label definition for shapes"""
    text: str = Field(..., description="Label text")
    color: Optional[str] = Field(None, description="Text color (hex or name)")
    properties: List[Property] = Field(default_factory=list, description="Additional properties")


class ImageResolution(BaseModel):
    """Image resolution definition"""
    pixels_per_unit: int = Field(..., ge=0, description="Pixels per unit")
    screen_unit: str = Field(..., description="Screen unit (layout length unit)")


