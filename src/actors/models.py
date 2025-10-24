"""Pydantic models for D&D 5e stat blocks and NPCs."""

from typing import Optional, Dict
from pydantic import BaseModel, field_validator


class StatBlock(BaseModel):
    """D&D 5e stat block structure."""

    # Always preserve original text
    name: str
    raw_text: str

    # Required D&D 5e fields
    armor_class: int
    hit_points: int
    challenge_rating: float

    # Optional fields
    size: Optional[str] = None
    type: Optional[str] = None
    alignment: Optional[str] = None
    abilities: Optional[Dict[str, int]] = None  # STR, DEX, CON, INT, WIS, CHA
    speed: Optional[str] = None
    senses: Optional[str] = None
    languages: Optional[str] = None
    traits: Optional[str] = None  # Special traits/features
    actions: Optional[str] = None  # Actions section

    @field_validator('armor_class')
    @classmethod
    def validate_ac(cls, v: int) -> int:
        """Validate armor class is in valid range."""
        if not (1 <= v <= 30):
            raise ValueError(f"Armor class {v} out of range (1-30)")
        return v

    @field_validator('hit_points')
    @classmethod
    def validate_hp(cls, v: int) -> int:
        """Validate hit points are positive."""
        if v < 1:
            raise ValueError(f"Hit points must be positive, got {v}")
        return v

    @field_validator('challenge_rating')
    @classmethod
    def validate_cr(cls, v: float) -> float:
        """Validate challenge rating is valid."""
        valid_crs = [0, 0.125, 0.25, 0.5] + list(range(1, 31))
        if v not in valid_crs:
            raise ValueError(f"Invalid challenge rating: {v}")
        return v


class NPC(BaseModel):
    """Named NPC with plot context and stat block reference."""

    name: str
    creature_stat_block_name: str  # Name of creature stat block this NPC uses
    description: str
    plot_relevance: str
    location: Optional[str] = None
    first_appearance_section: Optional[str] = None  # Where NPC first appears in module
