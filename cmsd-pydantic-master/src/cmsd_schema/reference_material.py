from __future__ import annotations
from pydantic import Field
from typing import Optional

from .identifiable_entity import IdentifiableEntity


# =============================================================================
# REFERENCE MATERIAL (from ReferenceMaterial.rng)
# =============================================================================

class ReferenceMaterial(IdentifiableEntity):
    """A reference to an external document, drawing, or other material"""
    uri: Optional[str] = Field(None, description="URI pointing to the material")
    media_type: Optional[str] = Field(None, description="MIME type of the material (e.g., application/pdf)")
