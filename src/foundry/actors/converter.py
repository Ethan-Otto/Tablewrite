"""Convert ParsedActorData to FoundryVTT actor JSON format."""

import logging
from typing import Dict, Any
from .models import ParsedActorData

logger = logging.getLogger(__name__)


def convert_to_foundry(parsed_actor: ParsedActorData) -> Dict[str, Any]:
    """
    Convert ParsedActorData to FoundryVTT actor JSON structure.

    This function transforms our parsed actor data into the complete JSON
    structure expected by FoundryVTT's D&D 5e system, including:
    - Actor system data (abilities, defenses, movement, senses)
    - Items array (attacks as weapon items, traits as feat items, spells)
    - Activities within items (attack rolls, damage, saves)

    Args:
        parsed_actor: Fully parsed actor data with attacks, traits, spells

    Returns:
        Dict containing FoundryVTT actor JSON structure

    Example:
        >>> goblin_data = ParsedActorData(...)
        >>> foundry_json = convert_to_foundry(goblin_data)
        >>> foundry_json['name']
        'Goblin'
        >>> foundry_json['system']['abilities']['dex']['value']
        14
    """
    logger.info(f"Converting actor '{parsed_actor.name}' to FoundryVTT format...")

    # Calculate ability modifiers
    def ability_mod(score: int) -> int:
        return (score - 10) // 2

    # Build abilities
    abilities = {}
    for ability in ["str", "dex", "con", "int", "wis", "cha"]:
        score = parsed_actor.abilities.get(ability.upper(), 10)
        abilities[ability] = {
            "value": score,
            "proficient": 1 if ability in parsed_actor.saving_throw_proficiencies else 0
        }

    # Build attributes
    attributes = {
        "ac": {"value": parsed_actor.armor_class},
        "hp": {
            "value": parsed_actor.hit_points,
            "max": parsed_actor.hit_points
        },
        "movement": {
            "walk": parsed_actor.speed_walk or 30
        }
    }

    # Add spellcasting info if present
    if parsed_actor.spellcasting_ability:
        attributes["spellcasting"] = parsed_actor.spellcasting_ability
        attributes["spelldc"] = parsed_actor.spell_save_dc or 10

    # Build details (simplified like create_creature_actor)
    details = {
        "cr": parsed_actor.challenge_rating,
        "type": {
            "value": parsed_actor.creature_type or "humanoid",
            "subtype": ""
        },
        "alignment": parsed_actor.alignment or ""
    }

    # Build system object (minimal like create_creature_actor)
    system = {
        "abilities": abilities,
        "attributes": attributes,
        "details": details,
        "traits": {}  # Empty traits dict for schema compatibility
    }

    # Build items array (attacks, traits, spells)
    items = []

    # Convert attacks to weapon items
    for attack in parsed_actor.attacks:
        item = {
            "name": attack.name,
            "type": "weapon",
            "img": "icons/weapons/swords/scimitar-guard-purple.webp",
            "system": {
                "description": {"value": attack.additional_effects or ""},
                "attackBonus": str(attack.attack_bonus),
                "damage": {
                    "parts": [[f"{dmg.number}d{dmg.denomination}{dmg.bonus}", dmg.type]
                             for dmg in attack.damage]
                },
                "range": {
                    "value": attack.range_short,
                    "long": attack.range_long,
                    "reach": attack.reach
                },
                "actionType": attack.attack_type
            }
        }
        items.append(item)

    # Convert traits to feat items
    for trait in parsed_actor.traits:
        item = {
            "name": trait.name,
            "type": "feat",
            "img": "icons/magic/movement/trail-streak-zigzag-yellow.webp",
            "system": {
                "description": {"value": trait.description},
                "activation": {"type": trait.activation},
                "uses": {"value": trait.uses, "max": trait.uses} if trait.uses else {}
            }
        }
        items.append(item)

    # Convert multiattack to feat item
    if parsed_actor.multiattack:
        item = {
            "name": parsed_actor.multiattack.name,
            "type": "feat",
            "img": "icons/magic/movement/trail-streak-zigzag-yellow.webp",
            "system": {
                "description": {"value": parsed_actor.multiattack.description},
                "activation": {"type": parsed_actor.multiattack.activation},
                "uses": {}
            }
        }
        items.append(item)

    # Convert spells to spell items (using UUIDs)
    for spell in parsed_actor.spells:
        item = {
            "name": spell.name,
            "type": "spell",
            "img": "icons/magic/air/wind-tornado-wall-blue.webp",
            "system": {
                "level": spell.level,
                "school": spell.school or ""
            }
        }
        if spell.uuid:
            item["uuid"] = spell.uuid
        items.append(item)

    # Build final actor structure
    actor = {
        "name": parsed_actor.name,
        "type": "npc",
        "img": "icons/svg/mystery-man.svg",
        "system": system,
        "items": items,
        "effects": [],
        "flags": {}
    }

    logger.info(f"✓ Converted actor '{parsed_actor.name}' ({len(items)} items)")
    return actor
