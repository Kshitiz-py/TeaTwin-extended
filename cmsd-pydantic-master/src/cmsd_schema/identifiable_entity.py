from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from .basic_structures import Property

# =============================================================================
# IDENTIFIABLE ENTITY BASE
# =============================================================================

class IdentifiableEntity(BaseModel):
    """Base class for all identifiable CMSD entities"""
    model_config = ConfigDict(use_enum_values=True)

    identifier: str = Field(..., description="Unique identifier for this entity")
    name: Optional[str] = Field(None, description="Human-readable name")
    description: Optional[str] = Field(None, description="Human-readable description")
    # reference_materials is declared as List[str] here to avoid circular imports;
    # concrete subclasses that need typed ReferenceMaterialReference should override.
    reference_materials: List[str] = Field(
        default_factory=list,
        description="Identifiers of reference materials attached to this entity"
    )
    properties: List[Property] = Field(default_factory=list, description="Additional properties")
