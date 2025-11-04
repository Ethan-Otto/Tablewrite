"""Foundry-specific actor models for detailed parsing."""

from typing import List, Optional, Literal, Dict
from pydantic import BaseModel, Field, ConfigDict


class DamageFormula(BaseModel):
    """Dice damage formula (FoundryVTT format)."""

    model_config = ConfigDict(frozen=True)

    number: int  # Dice count (e.g., 3 for 3d6)
    denomination: int  # Dice size (e.g., 6 for d6)
    bonus: str = ""  # Flat modifier (e.g., "+2")
    type: str  # Damage type: "piercing", "slashing", "fire", etc.


class SavingThrow(BaseModel):
    """Saving throw triggered by ability."""

    ability: Literal["str", "dex", "con", "int", "wis", "cha"]
    dc: Optional[int] = None  # Explicit DC if specified
    dc_ability: Optional[str] = None  # Ability for DC calculation (e.g., "cha")
    on_failure: str  # Effect description on failure
    on_success: Optional[str] = None  # Effect on success (if specified)


class Attack(BaseModel):
    """Parsed attack (weapon or spell attack)."""

    name: str
    attack_type: Literal["melee", "ranged", "melee_ranged"]
    attack_bonus: int  # To-hit bonus
    reach: Optional[int] = None  # Melee reach in feet (5, 10, 15, etc.)
    range_short: Optional[int] = None  # Ranged short range
    range_long: Optional[int] = None  # Ranged long range
    damage: List[DamageFormula]  # Primary + additional damage
    additional_effects: Optional[str] = None  # e.g., "target is grappled (escape DC 16)"

    # NEW: Optional attack save (e.g., Pit Fiend Bite poison save)
    attack_save: Optional['AttackSave'] = None

    @property
    def range(self) -> Optional[int]:
        """Alias for range_short for backwards compatibility."""
        return self.range_short


class Trait(BaseModel):
    """Parsed trait/feature."""

    name: str
    description: str
    activation: Literal["action", "bonus", "reaction", "passive", "legendary"] = "passive"
    uses: Optional[int] = None  # Limited uses per day/rest
    recharge: Optional[str] = None  # e.g., "5-6" for recharge on 5 or 6
    saving_throw: Optional[SavingThrow] = None


class Multiattack(BaseModel):
    """Multiattack action."""

    name: str = "Multiattack"
    description: str
    num_attacks: Optional[int] = None
    activation: Literal["action", "bonus", "reaction", "passive"] = "action"

    model_config = ConfigDict(frozen=True)


class Spell(BaseModel):
    """Parsed spell reference with compendium UUID."""

    name: str
    level: int  # 0-9
    uuid: Optional[str] = None  # Compendium UUID (resolved during parsing)
    school: Optional[str] = None  # "evo", "abj", etc.
    casting_time: Optional[str] = None


class InnateSpell(BaseModel):
    """An innate spell with usage frequency."""

    name: str
    frequency: str  # "at will", "3/day", "1/day", etc.
    uses: Optional[int] = None  # Max uses per day
    uuid: Optional[str] = None  # Compendium UUID (resolved during parsing)

    model_config = ConfigDict(frozen=True)


class InnateSpellcasting(BaseModel):
    """Innate spellcasting ability."""

    ability: str  # "charisma", "intelligence", etc.
    save_dc: Optional[int] = None
    attack_bonus: Optional[int] = None
    spells: List[InnateSpell] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)


class AttackSave(BaseModel):
    """A saving throw associated with an attack."""

    ability: Optional[str] = None  # "con", "dex", "wis", etc. (None for automatic effects)
    dc: Optional[int] = None       # Difficulty Class (None for automatic effects)

    # Damage on failed save
    damage: List[DamageFormula] = Field(default_factory=list)
    on_save: Literal["half", "none", "full", "negates"] = "none"  # Damage on successful save

    # For ongoing effects (e.g., poison damage each turn)
    ongoing_damage: Optional[List[DamageFormula]] = None
    duration_rounds: Optional[int] = None

    effect_description: Optional[str] = None  # e.g., "poisoned condition"

    model_config = ConfigDict(frozen=True)


class SkillProficiency(BaseModel):
    """Skill proficiency entry."""

    skill: str  # "Stealth", "Perception", etc.
    bonus: int  # Total bonus (ability mod + proficiency)
    proficiency_level: Literal[0, 1, 2] = 1  # 0=none, 1=proficient, 2=expertise


class DamageModification(BaseModel):
    """Damage resistance/immunity/vulnerability."""

    types: List[str]  # ["fire", "poison"]
    condition: Optional[str] = None  # "from nonmagical attacks"


class ParsedActorData(BaseModel):
    """Fully parsed stat block ready for FoundryVTT conversion."""

    # Reference to source (for debugging)
    source_statblock_name: str  # Just the name, not full object

    # Core stats (copied from StatBlock)
    name: str
    armor_class: int
    hit_points: int
    hit_dice: Optional[str] = None  # e.g., "27d10 + 189"
    challenge_rating: float

    # Biography/description
    biography: Optional[str] = None  # Full stat block text or generated description

    # Creature type
    size: Optional[str] = None  # "Small", "Medium", "Large", etc.
    creature_type: Optional[str] = None  # "humanoid", "fiend", etc.
    creature_subtype: Optional[str] = None  # "goblinoid", "devil", etc.
    alignment: Optional[str] = None

    # Abilities
    abilities: Dict[str, int]  # STR, DEX, CON, INT, WIS, CHA (required)
    saving_throw_proficiencies: List[str] = []  # ["dex", "wis"]

    # Skills
    skill_proficiencies: List[SkillProficiency] = []

    # Defenses
    damage_resistances: Optional[DamageModification] = None
    damage_immunities: Optional[DamageModification] = None
    damage_vulnerabilities: Optional[DamageModification] = None
    condition_immunities: List[str] = []  # ["poisoned", "charmed"]

    # Movement
    speed_walk: int = 30  # Default 30 ft
    speed_fly: Optional[int] = None
    speed_swim: Optional[int] = None
    speed_burrow: Optional[int] = None
    speed_climb: Optional[int] = None
    speed_hover: bool = False

    # Senses
    darkvision: Optional[int] = None  # Distance in feet
    blindsight: Optional[int] = None
    tremorsense: Optional[int] = None
    truesight: Optional[int] = None
    passive_perception: Optional[int] = None

    # Languages
    languages: List[str] = []  # ["Common", "Goblin"]
    telepathy: Optional[int] = None  # Range in feet

    # Abilities
    traits: List[Trait] = []
    attacks: List[Attack] = []
    reactions: List[Trait] = []  # Reactions use Trait model with activation="reaction"

    # Multiattack
    multiattack: Optional[Multiattack] = None

    # Spellcasting
    spells: List[Spell] = []  # Each spell has UUID pre-resolved
    spellcasting_ability: Optional[Literal["int", "wis", "cha"]] = None
    spell_save_dc: Optional[int] = None
    spell_attack_bonus: Optional[int] = None

    # Innate Spellcasting
    innate_spellcasting: Optional[InnateSpellcasting] = None
