from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Union
from decimal import Decimal

from .basic_types import (
    ResourceType, LayoutLengthUnit, TextAnchorLocation, BasicShapeType,
    CoordinateSystem, BaseLocation, ShapeDescriptionType,
    GraphicDescriptionType, SegmentType
)
from .basic_structures import (
    Property, Coordinate2D, Coordinate3D, BoundaryDefinition,
    ColorHighlight, ShapeLabelDefinition, ImageResolution, SpatialDimension
)
from .entity_reference_definition import (
    ResourceReference, LayoutElementReference, ReferenceMaterialReference
)


# =============================================================================
# TRANSFORMATION OPERATIONS
# =============================================================================

class Rotation(BaseModel):
    """Rotation transformation with degrees around X, Y, Z axes"""
    x_degree: Optional[Decimal] = Field(None, description="Rotation around X axis in degrees")
    y_degree: Optional[Decimal] = Field(None, description="Rotation around Y axis in degrees")
    z_degree: Optional[Decimal] = Field(None, description="Rotation around Z axis in degrees")
    origin: Coordinate3D = Field(..., description="Origin point for rotation")

    @model_validator(mode='after')
    def check_at_least_one_degree(self):
        if not any([self.x_degree is not None, self.y_degree is not None, self.z_degree is not None]):
            raise ValueError("At least one of x_degree, y_degree, or z_degree must be specified")
        return self


class Translation(BaseModel):
    """Translation transformation with offsets along X, Y, Z axes"""
    x_offset: Optional[Decimal] = Field(None, description="Offset along X axis")
    y_offset: Optional[Decimal] = Field(None, description="Offset along Y axis")
    z_offset: Optional[Decimal] = Field(None, description="Offset along Z axis")

    @model_validator(mode='after')
    def check_not_empty(self):
        if not any([self.x_offset is not None, self.y_offset is not None, self.z_offset is not None]):
            raise ValueError("Translation may not be empty - at least one offset must be specified")
        return self


class Scaling(BaseModel):
    """Scaling transformation with percentages along X, Y, Z axes"""
    x_percent: Optional[Decimal] = Field(None, description="Scaling percentage along X axis")
    y_percent: Optional[Decimal] = Field(None, description="Scaling percentage along Y axis")
    z_percent: Optional[Decimal] = Field(None, description="Scaling percentage along Z axis")

    @model_validator(mode='after')
    def check_not_empty(self):
        if not any([self.x_percent is not None, self.y_percent is not None, self.z_percent is not None]):
            raise ValueError("Scaling may not be empty - at least one percentage must be specified")
        return self


# Type alias for transformation operations
TransformationOperation = Union[Rotation, Translation, Scaling]


class TransformationList(BaseModel):
    """List of transformation operations"""
    transformations: List[TransformationOperation] = Field(
        ...,
        min_length=1,
        description="List of transformation operations (Rotation, Translation, Scaling)"
    )


# =============================================================================
# GRAPHIC DESCRIPTIONS
# =============================================================================

class GraphicDescription(BaseModel):
    """Base graphic description"""
    graphic_type: GraphicDescriptionType = Field(..., description="Type of graphic")
    file_name: str = Field(..., description="File name URI")
    file_type: str = Field(..., description="File type")
    transformations: Optional[TransformationList] = Field(None, description="Transformations to apply")
    properties: List[Property] = Field(default_factory=list, description="Additional properties")


class ModelGraphic(BaseModel):
    """3D model graphic description"""
    graphic_type: GraphicDescriptionType = Field(..., description="Type of graphic")
    file_name: str = Field(..., description="File name URI")
    file_type: str = Field(..., description="File type")
    transformations: Optional[TransformationList] = Field(None, description="Transformations to apply")
    properties: List[Property] = Field(default_factory=list, description="Additional properties")
    model_unit: LayoutLengthUnit = Field(..., description="Unit of measurement for the model")
    model_dimension: SpatialDimension = Field(..., description="Dimensions of the model")


class ImageGraphic(BaseModel):
    """2D image graphic description"""
    graphic_type: GraphicDescriptionType = Field(..., description="Type of graphic")
    file_name: str = Field(..., description="File name URI")
    file_type: str = Field(..., description="File type")
    transformations: Optional[TransformationList] = Field(None, description="Transformations to apply")
    properties: List[Property] = Field(default_factory=list, description="Additional properties")
    image_resolution: ImageResolution = Field(..., description="Image resolution")
    image_dimension: SpatialDimension = Field(..., description="Image dimensions")


# =============================================================================
# TEXTUAL ANNOTATION
# =============================================================================

class TextualAnnotation(BaseModel):
    """Textual annotation for layout"""
    attach_point: Optional[Coordinate3D] = Field(None, description="Point where text is attached")
    text: str = Field(..., description="The annotation text")
    text_anchor_location: Optional[TextAnchorLocation] = Field(None, description="Text anchor location")
    color: Optional[str] = Field(None, description="Text color (hex or name)")
    style: Optional[str] = Field(None, description="Text style")
    text_angle: Optional[Decimal] = Field(None, description="Text rotation angle in degrees")
    properties: List[Property] = Field(default_factory=list, description="Additional properties")


# =============================================================================
# BASIC SHAPES
# =============================================================================

class BasicShape(BaseModel):
    """Base class for basic shapes"""
    type: BasicShapeType = Field(..., description="Type of basic shape")
    height: Optional[Decimal] = Field(None, description="Height of the shape")
    color: Optional[ColorHighlight] = Field(None, description="Color highlighting")
    label: Optional[ShapeLabelDefinition] = Field(None, description="Label for the shape")


class Box(BasicShape):
    """Box/Rectangle shape"""
    width: Decimal = Field(..., description="Width of the box")
    depth: Decimal = Field(..., description="Depth of the box")


class Circle(BasicShape):
    """Circle shape"""
    center: Coordinate2D = Field(..., description="Center point of the circle")
    radius: Decimal = Field(..., description="Radius of the circle")
    angle: Optional[Decimal] = Field(None, description="Rotation angle in degrees")


class Polygon(BasicShape):
    """Polygon shape"""
    points: List[Coordinate2D] = Field(
        ...,
        min_length=3,
        description="Points defining the polygon (at least 3 required)"
    )


# =============================================================================
# SEGMENT SHAPES
# =============================================================================

class SegmentShape(BaseModel):
    """Base class for segment shapes"""
    type: SegmentType = Field(..., description="Type of segment")
    segment_number: Optional[str] = Field(None, description="Segment identifier")
    description: Optional[str] = Field(None, description="Segment description")
    base: BaseLocation = Field(..., description="Base location (floor or ceiling)")
    start: Coordinate2D = Field(..., description="Start point of the segment")
    width: Decimal = Field(..., description="Width of the segment")
    start_height: Optional[Decimal] = Field(None, description="Height at start of segment")
    end_height: Optional[Decimal] = Field(None, description="Height at end of segment")
    track_width: Optional[Decimal] = Field(None, description="Track width")
    color: Optional[ColorHighlight] = Field(None, description="Color highlighting")
    reference_materials: List[ReferenceMaterialReference] = Field(
        default_factory=list,
        description="Reference materials"
    )
    properties: List[Property] = Field(default_factory=list, description="Additional properties")


class StraightSegment(SegmentShape):
    """Straight line segment"""
    end: Coordinate2D = Field(..., description="End point of the segment")


class CurvedSegment(SegmentShape):
    """Curved segment"""
    rotation_point: Coordinate2D = Field(..., description="Point of rotation for the curve")
    rotation_angle: Decimal = Field(..., description="Rotation angle in degrees")


# =============================================================================
# SHAPE DESCRIPTION
# =============================================================================

class ShapeDescription(BaseModel):
    """Shape description that can be basic, graphic, segment, or text"""
    shape_type: ShapeDescriptionType = Field(..., description="Type of shape description")
    basic_shape: Optional[Union[Box, Circle, Polygon]] = Field(
        None,
        description="Basic shape (box, circle, or polygon)"
    )
    graphic: Optional[Union[ModelGraphic, ImageGraphic]] = Field(
        None,
        description="Graphic (model or image)"
    )
    segments: List[Union[StraightSegment, CurvedSegment]] = Field(
        default_factory=list,
        description="List of segments"
    )
    textual_annotation: Optional[TextualAnnotation] = Field(
        None,
        description="Textual annotation"
    )

    @model_validator(mode='after')
    def validate_shape_type_consistency(self):
        """Validate that shape_type matches the provided shape data"""
        if self.shape_type == ShapeDescriptionType.BASIC and not self.basic_shape:
            raise ValueError("basic_shape must be provided when shape_type is 'basic'")
        if self.shape_type == ShapeDescriptionType.GRAPHIC and not self.graphic:
            raise ValueError("graphic must be provided when shape_type is 'graphic'")
        if self.shape_type == ShapeDescriptionType.SEGMENT and not self.segments:
            raise ValueError("segments must be provided when shape_type is 'segment'")
        if self.shape_type == ShapeDescriptionType.TEXT and not self.textual_annotation:
            raise ValueError("textual_annotation must be provided when shape_type is 'text'")
        return self


# =============================================================================
# LAYOUT ELEMENTS
# =============================================================================

class LayoutElement(BaseModel):
    """Base layout element with common attributes"""
    identifier: str = Field(..., description="Unique identifier for the layout element")
    description: Optional[str] = Field(None, description="Description of the layout element")
    name: Optional[str] = Field(None, description="Name of the layout element")
    associated_resource: Optional[ResourceReference] = Field(
        None,
        description="Associated resource reference"
    )
    boundary: BoundaryDefinition = Field(..., description="Boundary definition")
    reference_materials: List[ReferenceMaterialReference] = Field(
        default_factory=list,
        description="Reference materials"
    )
    properties: List[Property] = Field(default_factory=list, description="Additional properties")


class LayoutObject(LayoutElement):
    """Layout object representing a physical object in the layout"""
    type: Optional[ResourceType] = Field(None, description="Type of resource")
    shape: Optional[ShapeDescription] = Field(None, description="Shape description")


class Placement(BaseModel):
    """Placement of a layout element at a specific location"""
    layout_element: LayoutElementReference = Field(..., description="Reference to the layout element")
    location: Coordinate3D = Field(..., description="Location of the placement")
    transformations: Optional[TransformationList] = Field(
        None,
        description="Transformations to apply"
    )


class Layout(LayoutElement):
    """Layout containing multiple placements"""
    placements: List[Placement] = Field(default_factory=list, description="Placements in the layout")
