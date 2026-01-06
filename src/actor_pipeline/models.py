"""Pydantic models for D&D 5e stat blocks and NPCs."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List
from pydantic import BaseModel, field_validator


class StatBlock(BaseModel):
    """D&D 5e stat block structure with pre-split sections for parallel processing."""

    # Always preserve original text
    name: str
    raw_text: str

    # Required D&D 5e fields
    armor_class: int
    hit_points: int
    challenge_rating: float

    # Optional structured fields
    size: Optional[str] = None
    type: Optional[str] = None
    alignment: Optional[str] = None
    abilities: Optional[Dict[str, int]] = None  # STR, DEX, CON, INT, WIS, CHA
    speed: Optional[str] = None
    senses: Optional[str] = None
    languages: Optional[str] = None

    # Proficiencies (extracted from raw text)
    saving_throws: Optional[Dict[str, int]] = None  # {"dex": 8, "con": 13, "wis": 10}
    skills: Optional[Dict[str, int]] = None  # {"perception": 4, "stealth": 5}

    # Damage modifiers
    damage_resistances: Optional[str] = None  # e.g., "Fire, Cold; Bludgeoning from Nonmagical Attacks"
    damage_immunities: Optional[str] = None
    damage_vulnerabilities: Optional[str] = None
    condition_immunities: Optional[str] = None  # e.g., "Poisoned, Charmed"

    # Split into lists for parallel processing
    # Each item is a complete entry (e.g., "Scimitar. Melee Weapon Attack: +4 to hit...")
    traits: List[str] = []  # Special abilities (includes innate spellcasting if present)
    actions: List[str] = []  # Actions (includes multiattack if present)
    reactions: List[str] = []  # Reactions
    legendary_actions: List[str] = []  # Legendary actions

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


@dataclass
class ActorCreationResult:
    """Complete result from actor creation pipeline with all intermediate outputs."""

    # Input
    description: str
    challenge_rating: Optional[float]

    # Intermediate outputs
    raw_stat_block_text: str
    stat_block: StatBlock
    parsed_actor_data: 'ParsedActorData'  # Forward reference since ParsedActorData is in foundry/actors/models.py

    # Final output
    foundry_uuid: str

    # File paths (for debugging/inspection)
    output_dir: Path

    # Metadata
    timestamp: str  # ISO format timestamp
    model_used: str  # e.g., "gemini-2.0-flash"

    # Optional file paths
    raw_text_file: Optional[Path] = None
    stat_block_file: Optional[Path] = None
    parsed_data_file: Optional[Path] = None
    foundry_json_file: Optional[Path] = None
