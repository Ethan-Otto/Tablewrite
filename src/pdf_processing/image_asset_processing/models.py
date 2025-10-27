"""Data models for image asset extraction."""
from pydantic import BaseModel
from typing import Optional


class MapDetectionResult(BaseModel):
    """Result from Gemini Vision map detection.

    Attributes:
        has_map: Whether the page contains a map
        type: Map type ("navigation_map" or "battle_map")
        name: Descriptive name (3 words max)
    """
    has_map: bool
    type: Optional[str] = None
    name: Optional[str] = None


class MapMetadata(BaseModel):
    """Metadata for extracted map asset.

    Attributes:
        name: Descriptive map name
        chapter: Chapter name (None if unknown)
        page_num: PDF page number (1-indexed)
        type: Map type ("navigation_map" or "battle_map")
        source: Extraction method ("extracted" or "segmented")
    """
    name: str
    chapter: Optional[str] = None
    page_num: int
    type: str
    source: str
