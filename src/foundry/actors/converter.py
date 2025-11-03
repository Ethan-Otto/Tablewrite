"""Convert ParsedActorData to FoundryVTT actor JSON format."""

import logging
import secrets
from typing import Dict, Any, Optional, TYPE_CHECKING
from .models import ParsedActorData, Attack, AttackSave

if TYPE_CHECKING:
    from .spell_cache import SpellCache

logger = logging.getLogger(__name__)


def _generate_activity_id() -> str:
    """Generate a unique 16-character ID for activities and items.

    FoundryVTT requires exactly 16 alphanumeric characters [a-zA-Z0-9].
    """
    import string
    alphabet = string.ascii_letters + string.digits  # a-zA-Z0-9
    return ''.join(secrets.choice(alphabet) for _ in range(16))


def _base_activity_structure() -> dict:
    """Common fields for all activities."""
    return {
        "activation": {
            "type": "action",
            "value": None,
            "override": False,
            "condition": ""
        },
        "consumption": {
            "scaling": {"allowed": False},
            "spellSlot": True,
            "targets": []
        },
        "description": {"chatFlavor": ""},
        "duration": {
            "units": "inst",
            "concentration": False,
            "override": False
        },
        "effects": [],
        "range": {"override": False, "units": "self"},
        "target": {
            "template": {"contiguous": False, "units": "ft", "type": ""},
            "affects": {"choice": False, "type": "creature", "count": "1", "special": ""},
            "override": False,
            "prompt": True
        },
        "uses": {"spent": 0, "recovery": [], "max": ""}
    }


def _create_attack_activity(attack: Attack, activity_id: str) -> dict:
    """Create an attack-type activity for a weapon."""
    base = _base_activity_structure()
    base.update({
        "type": "attack",
        "_id": activity_id,
        "sort": 0,
        "attack": {
            "bonus": str(attack.attack_bonus),
            "flat": True,
            "critical": {"threshold": None},
            "type": {"value": attack.attack_type, "classification": "weapon"},
            "ability": ""
        },
        "damage": {
            "includeBase": True,
            "parts": [],
            "critical": {"bonus": ""}
        },
        "name": ""
    })
    return base


def _create_save_activity(save: AttackSave, activity_id: str) -> dict:
    """Create a save-type activity."""
    base = _base_activity_structure()
    base.update({
        "type": "save",
        "_id": activity_id,
        "sort": 0,
        "save": {
            "ability": [save.ability],
            "dc": {"calculation": "", "formula": str(save.dc)}
        },
        "damage": {
            "parts": [
                {
                    "custom": {"enabled": False, "formula": ""},
                    "number": d.number,
                    "denomination": d.denomination,
                    "bonus": d.bonus,
                    "types": [d.type],
                    "scaling": {"number": 1}
                }
                for d in save.damage
            ],
            "onSave": save.on_save
        },
        "name": ""
    })
    return base


def _create_ongoing_damage_activity(save: AttackSave, activity_id: str) -> dict:
    """Create ongoing damage activity (e.g., poison each turn)."""
    base = _base_activity_structure()
    base["activation"]["type"] = "turnStart"
    base.update({
        "type": "damage",
        "_id": activity_id,
        "sort": 0,
        "damage": {
            "critical": {"allow": False},
            "parts": [
                {
                    "custom": {"enabled": False, "formula": ""},
                    "number": d.number,
                    "denomination": d.denomination,
                    "bonus": d.bonus,
                    "types": [d.type],
                    "scaling": {"number": 1}
                }
                for d in save.ongoing_damage
            ]
        },
        "name": f"Add'l {save.ongoing_damage[0].type.capitalize()} Damage" if save.ongoing_damage else ""
    })
    return base


def convert_to_foundry(
    parsed_actor: ParsedActorData,
    spell_cache: Optional['SpellCache'] = None,
    include_spells_in_payload: bool = False
) -> tuple[Dict[str, Any], list[str]]:
    """
    Convert ParsedActorData to FoundryVTT actor JSON structure.

    This function transforms our parsed actor data into the complete JSON
    structure expected by FoundryVTT's D&D 5e system, including:
    - Actor system data (abilities, defenses, movement, senses)
    - Items array (attacks as weapon items, traits as feat items)
    - Spell UUIDs to be added via /give endpoint (returned separately)

    Args:
        parsed_actor: Fully parsed actor data with attacks, traits, spells
        spell_cache: Optional spell cache for UUID lookups
        include_spells_in_payload: If True, include spell stubs in CREATE payload
            (not recommended - spells will lack full compendium data)

    Returns:
        Tuple of (actor_json, spell_uuids):
            - actor_json: Dict containing FoundryVTT actor JSON structure
            - spell_uuids: List of compendium spell UUIDs to add via /give

    Example:
        >>> goblin_data = ParsedActorData(...)
        >>> actor_json, spell_uuids = convert_to_foundry(goblin_data, spell_cache)
        >>> actor_json['name']
        'Goblin'
        >>> spell_uuids
        ['Compendium.dnd5e.spells.ztgcdrWPshKRpFd0']
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
    spell_uuids = []  # Collect spell UUIDs to add via /give

    # Convert attacks to weapon items (NEW v10+ structure with activities)
    for attack in parsed_actor.attacks:
        activities = {}

        # 1. Always create attack activity
        attack_id = _generate_activity_id()
        activities[attack_id] = _create_attack_activity(attack, attack_id)

        # 2. Add save activity if present
        if attack.attack_save:
            save_id = _generate_activity_id()
            activities[save_id] = _create_save_activity(attack.attack_save, save_id)

            # 3. Add ongoing damage activity if present
            if attack.attack_save.ongoing_damage:
                dmg_id = _generate_activity_id()
                activities[dmg_id] = _create_ongoing_damage_activity(attack.attack_save, dmg_id)

        # Build weapon item (v10+ structure)
        item = {
            "_id": _generate_activity_id(),
            "name": attack.name,
            "type": "weapon",
            "img": "icons/weapons/swords/scimitar-guard-purple.webp",
            "system": {
                "description": {"value": attack.additional_effects or ""},
                "activities": activities,
                "damage": {
                    "base": {
                        "number": attack.damage[0].number,
                        "denomination": attack.damage[0].denomination,
                        "bonus": attack.damage[0].bonus.replace("+", ""),
                        "types": [attack.damage[0].type],
                        "custom": {"enabled": False, "formula": ""},
                        "scaling": {"mode": "", "number": None, "formula": ""}
                    },
                    "versatile": {
                        "number": None,
                        "denomination": None,
                        "types": [],
                        "custom": {"enabled": False},
                        "scaling": {"number": 1}
                    }
                },
                "range": {
                    "value": attack.range_short,
                    "long": attack.range_long,
                    "reach": attack.reach,
                    "units": "ft"
                },
                "type": {"value": "natural", "baseItem": ""},
                "properties": [],
                "uses": {"spent": 0, "recovery": [], "max": ""}
            }
        }
        items.append(item)

    # Convert traits to feat items
    for trait in parsed_actor.traits:
        item = {
            "_id": _generate_activity_id(),
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
            "_id": _generate_activity_id(),
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

    # Convert spells - collect UUIDs for /give endpoint
    for spell in parsed_actor.spells:
        # Get UUID from cache or spell object
        spell_uuid = None
        if spell_cache:
            spell_uuid = spell_cache.get_spell_uuid(spell.name)
        elif spell.uuid:
            spell_uuid = spell.uuid

        if spell_uuid:
            spell_uuids.append(spell_uuid)
        else:
            logger.warning(f"No UUID found for spell '{spell.name}', skipping")

        # Optionally include stub in payload (not recommended)
        if include_spells_in_payload:
            item = {
                "_id": _generate_activity_id(),
                "name": spell.name,
                "type": "spell",
                "img": "icons/magic/air/wind-tornado-wall-blue.webp",
                "system": {
                    "level": spell.level,
                    "school": spell.school or ""
                }
            }
            if spell_uuid:
                item["uuid"] = spell_uuid
            items.append(item)

    # Convert innate spellcasting to feat + spell items
    if parsed_actor.innate_spellcasting:
        innate = parsed_actor.innate_spellcasting

        # Build description from spell list
        spell_lines = []
        # Group by frequency
        by_frequency = {}
        for spell in innate.spells:
            if spell.frequency not in by_frequency:
                by_frequency[spell.frequency] = []
            by_frequency[spell.frequency].append(spell.name)

        for freq, spell_names in sorted(by_frequency.items()):
            spell_list = ", ".join(spell_names)
            spell_lines.append(f"{freq}: {spell_list}")

        description = (
            f"The {parsed_actor.name.lower()}'s spellcasting ability is "
            f"{innate.ability.capitalize()} (spell save DC {innate.save_dc or 10}). "
            f"It can innately cast the following spells, requiring no material components:\n\n"
            + "\n".join(spell_lines)
        )

        # Create Innate Spellcasting feat
        item = {
            "_id": _generate_activity_id(),
            "name": "Innate Spellcasting",
            "type": "feat",
            "img": "icons/magic/air/wind-tornado-wall-blue.webp",
            "system": {
                "description": {"value": description},
                "activation": {"type": "passive"},
                "uses": {}
            }
        }
        items.append(item)

        # Collect UUIDs for innate spells (to add via /give)
        for spell in innate.spells:
            # Look up UUID from spell cache
            spell_uuid = None
            if spell_cache:
                spell_uuid = spell_cache.get_spell_uuid(spell.name)

            if spell_uuid:
                spell_uuids.append(spell_uuid)
            else:
                logger.warning(f"No UUID found for innate spell '{spell.name}', skipping")

            # Optionally include stub in payload (not recommended)
            if include_spells_in_payload:
                spell_item = {
                    "_id": _generate_activity_id(),
                    "name": spell.name,
                    "type": "spell",
                    "img": "icons/magic/air/wind-tornado-wall-blue.webp",
                    "system": {
                        "level": 0,
                        "school": ""
                    }
                }

                if spell_uuid:
                    spell_item["uuid"] = spell_uuid

                # Get spell details from cache
                if spell_cache:
                    spell_data = spell_cache.get_spell_data(spell.name)
                    if spell_data:
                        system_data = spell_data.get("data", {}).get("system") or spell_data.get("system", {})
                        spell_item["system"]["level"] = system_data.get("level", 0)
                        spell_item["system"]["school"] = system_data.get("school", "")

                # Add uses if limited
                if spell.uses:
                    spell_item["system"]["uses"] = {
                        "value": spell.uses,
                        "max": spell.uses,
                        "per": "day"
                    }

                items.append(spell_item)

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

    logger.info(f"✓ Converted actor '{parsed_actor.name}' ({len(items)} items, {len(spell_uuids)} spells via /give)")
    return actor, spell_uuids
