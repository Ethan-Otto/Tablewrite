"""Data models for scene extraction."""

from typing import Optional
from pydantic import BaseModel, field_validator


class Scene(BaseModel):
    """Represents a physical location/scene from a D&D module."""

    section_path: str  # e.g., "Chapter 2 → The Cragmaw Hideout → Area 1"
    name: str
    description: str  # Physical environment description only (no NPCs/monsters)
    location_type: str  # e.g., "underground", "outdoor", "interior", "underwater"
    xml_section_id: Optional[str] = None  # Reference to XML section element

    @field_validator('name')
    @classmethod
    def validate_name_not_empty(cls, v: str) -> str:
        """Ensure name is not empty."""
        if not v or not v.strip():
            raise ValueError("Scene name cannot be empty")
        return v

    @field_validator('description')
    @classmethod
    def validate_description_not_empty(cls, v: str) -> str:
        """Ensure description is not empty."""
        if not v or not v.strip():
            raise ValueError("Scene description cannot be empty")
        return v


class ChapterContext(BaseModel):
    """Environmental context for a chapter (inferred by Gemini)."""

    environment_type: str  # e.g., "underground", "forest", "urban", "coastal"
    weather: Optional[str] = None  # e.g., "rainy", "foggy", "clear"
    atmosphere: Optional[str] = None  # e.g., "oppressive", "peaceful", "tense"
    lighting: Optional[str] = None  # e.g., "dim torchlight", "bright sunlight", "darkness"
    terrain: Optional[str] = None  # e.g., "rocky caverns", "dense forest", "cobblestone streets"
    additional_notes: Optional[str] = None  # Any other relevant context
