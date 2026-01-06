"""FoundryVTT actor operations - network layer only.

Models and converters have been moved to foundry_converters package.
This module provides network operations (ActorManager) and re-exports
common types from foundry_converters for backwards compatibility.

Note: SpellCache has moved to caches.SpellCache - import from there directly.
"""

from .manager import ActorManager

# Re-export models from foundry_converters for backwards compatibility
from foundry_converters.actors.models import (
    DamageFormula,
    SavingThrow,
    Attack,
    Trait,
    Spell,
    SkillProficiency,
    DamageModification,
    ParsedActorData,
)
from foundry_converters.actors.converter import convert_to_foundry

__all__ = [
    "ActorManager",
    # Re-exported from foundry_converters
    "DamageFormula",
    "SavingThrow",
    "Attack",
    "Trait",
    "Spell",
    "SkillProficiency",
    "DamageModification",
    "ParsedActorData",
    "convert_to_foundry",
]
