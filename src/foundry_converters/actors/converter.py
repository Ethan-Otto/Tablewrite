"""Convert ParsedActorData to FoundryVTT actor JSON format."""

import logging
import secrets
from typing import Dict, Any, Optional, List, Tuple
from .models import ParsedActorData, Attack, AttackSave

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


def _is_save_based_action(trait) -> bool:
    """Detect if a trait is a save-based action (e.g., breath weapon, gaze attack)."""
    import re

    # Must be an action or bonus action (not passive)
    if trait.activation not in ["action", "bonus"]:
        return False

    # Check description for saving throw pattern
    desc_lower = trait.description.lower()
    if re.search(r'dc \d+.*saving throw', desc_lower):
        return True

    return False


def _parse_save_action(trait) -> dict:
    """Parse save-based action description to extract save data."""
    import re

    desc = trait.description
    result = {
        "template_type": "cone",
        "template_size": "",
        "damage_parts": [],
        "on_save": "half",
        "save_ability": "dex",
        "save_dc": ""
    }

    # Extract template type and size (e.g., "60-foot cone", "30-foot line")
    template_match = re.search(r'(\d+)-foot (cone|line|cube|sphere|cylinder)', desc, re.IGNORECASE)
    if template_match:
        result["template_size"] = template_match.group(1)
        result["template_type"] = template_match.group(2).lower()

    # Extract damage (e.g., "63 (18d6) fire damage")
    damage_match = re.search(r'(\d+)\s*\((\d+)d(\d+)\)\s+(\w+)\s+damage', desc, re.IGNORECASE)
    if damage_match:
        num_dice = int(damage_match.group(2))
        die_size = int(damage_match.group(3))
        damage_type = damage_match.group(4).lower()

        result["damage_parts"] = [{
            "custom": {"enabled": False, "formula": ""},
            "number": num_dice,
            "denomination": die_size,
            "bonus": "",
            "types": [damage_type],
            "scaling": {"number": 1}
        }]

    # Extract save DC (e.g., "DC 21 Dexterity saving throw")
    save_match = re.search(r'DC (\d+)\s+(\w+)\s+saving throw', desc, re.IGNORECASE)
    if save_match:
        result["save_dc"] = save_match.group(1)
        ability = save_match.group(2).lower()[:3]  # "dex", "con", etc.
        result["save_ability"] = ability

    # Extract on-save behavior (e.g., "half as much damage on a successful one")
    if re.search(r'half.*damage.*success', desc, re.IGNORECASE):
        result["on_save"] = "half"
    elif re.search(r'no.*damage.*success', desc, re.IGNORECASE):
        result["on_save"] = "none"

    return result


async def convert_to_foundry(
    parsed_actor: ParsedActorData,
    spell_cache: Optional[Any] = None,
    icon_cache: Optional[Any] = None,
    include_spells_in_payload: bool = False,
    use_ai_icons: bool = True
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

    # Add senses
    senses = {}
    if parsed_actor.darkvision:
        senses["darkvision"] = parsed_actor.darkvision
    if parsed_actor.blindsight:
        senses["blindsight"] = parsed_actor.blindsight
    if parsed_actor.tremorsense:
        senses["tremorsense"] = parsed_actor.tremorsense
    if parsed_actor.truesight:
        senses["truesight"] = parsed_actor.truesight
    if senses:
        attributes["senses"] = senses

    # Add spellcasting info if present
    if parsed_actor.spellcasting_ability:
        attributes["spellcasting"] = parsed_actor.spellcasting_ability
        attributes["spelldc"] = parsed_actor.spell_save_dc or 10

    # Build skills
    # FoundryVTT skill abbreviation mapping
    skill_abbrev_map = {
        "acrobatics": "acr",
        "animal handling": "ani",
        "arcana": "arc",
        "athletics": "ath",
        "deception": "dec",
        "history": "his",
        "insight": "ins",
        "intimidation": "itm",
        "investigation": "inv",
        "medicine": "med",
        "nature": "nat",
        "perception": "prc",
        "performance": "prf",
        "persuasion": "per",
        "religion": "rel",
        "sleight of hand": "slt",
        "stealth": "ste",
        "survival": "sur"
    }

    skills = {}
    for skill_prof in parsed_actor.skill_proficiencies:
        skill_key = skill_abbrev_map.get(skill_prof.skill.lower())
        if skill_key:
            skills[skill_key] = {"value": skill_prof.proficiency_level}

    # Build details (simplified like create_creature_actor)
    details = {
        "cr": parsed_actor.challenge_rating,
        "type": {
            "value": parsed_actor.creature_type or "humanoid",
            "subtype": ""
        },
        "alignment": parsed_actor.alignment or "",
        "biography": {
            "value": parsed_actor.biography or "",
            "public": ""
        }
    }

    # Build traits (damage modifiers and condition immunities)
    traits_dict = {}
    if parsed_actor.damage_resistances:
        traits_dict["dr"] = {"value": parsed_actor.damage_resistances.types}
    if parsed_actor.damage_immunities:
        traits_dict["di"] = {"value": parsed_actor.damage_immunities.types}
    if parsed_actor.damage_vulnerabilities:
        traits_dict["dv"] = {"value": parsed_actor.damage_vulnerabilities.types}
    if parsed_actor.condition_immunities:
        traits_dict["ci"] = {"value": parsed_actor.condition_immunities}

    # Build system object (minimal like create_creature_actor)
    system = {
        "abilities": abilities,
        "attributes": attributes,
        "details": details,
        "skills": skills,
        "traits": traits_dict
    }

    # Pre-fetch icons using AI if enabled
    icon_map = {}  # Map from item name to icon path
    if use_ai_icons and icon_cache and icon_cache.loaded:
        logger.info(f"Using AI icon selection for {parsed_actor.name}...")

        # Collect all items that need icons
        items_for_icons: List[Tuple[str, Optional[List[str]]]] = []

        # Helper: check if attack is a natural weapon
        def is_natural_weapon(name: str) -> bool:
            """Detect natural weapons by name (bite, claw, etc.)."""
            natural_keywords = {
                "bite", "claw", "gore", "tail", "slam", "sting", "tentacle",
                "horn", "tusk", "talon", "wing", "fist", "pseudopod", "tendril"
            }
            name_lower = name.lower()
            return any(keyword in name_lower for keyword in natural_keywords)

        # Add attacks (natural weapons use creatures folder only, weapons use both)
        for attack in parsed_actor.attacks:
            if is_natural_weapon(attack.name):
                items_for_icons.append((attack.name, ["creatures"]))
            else:
                items_for_icons.append((attack.name, ["weapons", "creatures"]))

        # Add traits (search both magic and skills folders)
        for trait in parsed_actor.traits:
            items_for_icons.append((trait.name, ["magic", "skills"]))

        # Add multiattack if present (search both magic and skills folders)
        if parsed_actor.multiattack:
            items_for_icons.append((parsed_actor.multiattack.name, ["magic", "skills"]))

        # Batch fetch icons in parallel (perfect word match + Gemini)
        icon_results = await icon_cache.get_icons_batch(
            items_for_icons,
            model_name="gemini-2.0-flash"
        )

        # Build map for easy lookup
        for (item_name, _), icon_path in zip(items_for_icons, icon_results):
            if icon_path:
                icon_map[item_name] = icon_path

        logger.info(f"✓ Selected {len(icon_map)} icons using AI")

    # Build items array (attacks, traits, spells)
    items = []
    spell_uuids = []  # Collect spell UUIDs to add via /give

    # Collect spell names to filter from attacks/traits (case-insensitive)
    # Spells will be added via /give from compendium, so don't duplicate as feat/weapon
    spell_names = {spell.name.lower() for spell in parsed_actor.spells}
    if parsed_actor.innate_spellcasting:
        spell_names.update(spell.name.lower() for spell in parsed_actor.innate_spellcasting.spells)
    logger.debug(f"Spell names to filter from attacks/traits: {spell_names}")

    # Convert attacks to weapon items (NEW v10+ structure with activities)
    for attack in parsed_actor.attacks:
        # Skip attacks that are actually spells (they'll be added from compendium)
        if attack.name.lower() in spell_names:
            logger.info(f"Skipping attack '{attack.name}' - will be added as spell from compendium")
            continue
        activities = {}

        # Determine if this is a save-only attack (e.g., breath weapon)
        # Save-only attacks have attack_save but no attack roll (attack_bonus is None or 0)
        is_save_only = attack.attack_save is not None and (attack.attack_bonus is None or attack.attack_bonus == 0)

        # 1. Create attack activity (only for attacks with attack rolls)
        if not is_save_only:
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

        # Select appropriate icon
        # 1. Check for common hardcoded natural weapons first
        weapon_icon = None
        attack_name_lower = attack.name.lower()
        if "bite" in attack_name_lower:
            weapon_icon = "icons/creatures/abilities/mouth-teeth-long-red.webp"
        elif "claw" in attack_name_lower:
            weapon_icon = "icons/creatures/claws/claw-talons-glowing-orange.webp"
        # 2. Use AI-selected icon if available
        elif attack.name in icon_map:
            weapon_icon = icon_map[attack.name]
        # 3. Fallback to fuzzy match or default
        elif icon_cache and icon_cache.loaded:
            matched_icon = icon_cache.get_icon(attack.name, category="weapons")
            if matched_icon:
                weapon_icon = matched_icon

        # Final fallback
        if not weapon_icon:
            weapon_icon = "icons/weapons/swords/scimitar-guard-purple.webp"

        # Build weapon item (v10+ structure)
        item = {
            "_id": _generate_activity_id(),
            "name": attack.name,
            "type": "weapon",
            "img": weapon_icon,
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
        # Skip traits that are actually spells (they'll be added from compendium)
        if trait.name.lower() in spell_names:
            logger.info(f"Skipping trait '{trait.name}' - will be added as spell from compendium")
            continue

        # Create activity for non-passive traits
        activities = {}
        if trait.activation != "passive":
            activity_id = _generate_activity_id()
            activity = _base_activity_structure()

            # Check if this is a save-based action (breath weapon, gaze attack, etc.)
            is_save_action = _is_save_based_action(trait)

            if is_save_action:
                # Create save activity for save-based actions
                save_data = _parse_save_action(trait)
                activity.update({
                    "type": "save",
                    "_id": activity_id,
                    "sort": 0,
                    "name": "",
                    "activation": {
                        "type": trait.activation,
                        "value": None,
                        "override": False,
                        "condition": ""
                    },
                    "target": {
                        "template": {
                            "contiguous": False,
                            "units": "ft",
                            "type": save_data.get("template_type", "cone"),
                            "size": str(save_data.get("template_size", "")),
                            "count": "",
                            "width": "5"
                        },
                        "affects": {
                            "choice": False,
                            "count": "",
                            "type": "creature",
                            "special": ""
                        },
                        "override": False,
                        "prompt": True
                    },
                    "damage": {
                        "parts": save_data.get("damage_parts", []),
                        "onSave": save_data.get("on_save", "half")
                    },
                    "save": {
                        "ability": [save_data.get("save_ability", "dex")],
                        "dc": {
                            "calculation": "",
                            "formula": str(save_data.get("save_dc", ""))
                        }
                    }
                })
            else:
                # Regular utility activity
                activity.update({
                    "type": "utility",
                    "_id": activity_id,
                    "sort": 0,
                    "name": "",
                    "activation": {
                        "type": trait.activation,
                        "value": None,
                        "override": False,
                        "condition": ""
                    }
                })
            activities[activity_id] = activity

        # Select appropriate icon (from AI map if available, else fuzzy match)
        trait_icon = "icons/magic/movement/trail-streak-zigzag-yellow.webp"  # Default
        if trait.name in icon_map:
            trait_icon = icon_map[trait.name]
        elif icon_cache and icon_cache.loaded:
            # Try multiple keyword matches
            keywords = trait.name.lower().split()
            matched_icon = icon_cache.get_icon_by_keywords(keywords, category="magic")
            if matched_icon:
                trait_icon = matched_icon

        item = {
            "_id": _generate_activity_id(),
            "name": trait.name,
            "type": "feat",
            "img": trait_icon,
            "system": {
                "description": {"value": trait.description},
                "activation": {
                    "type": trait.activation,
                    "value": None,
                    "condition": ""
                },
                "activities": activities,
                "uses": {"value": trait.uses, "max": trait.uses} if trait.uses else {}
            }
        }
        items.append(item)

    # Convert multiattack to feat item
    if parsed_actor.multiattack:
        # Create activity for multiattack
        activity_id = _generate_activity_id()
        activity = _base_activity_structure()
        activity.update({
            "type": "utility",
            "_id": activity_id,
            "sort": 0,
            "name": "",
            "activation": {
                "type": parsed_actor.multiattack.activation,
                "value": None,
                "override": False,
                "condition": ""
            }
        })

        # Get icon from AI map, but override generic "Multiattack" with better hardcoded icon
        if parsed_actor.multiattack.name.lower() == "multiattack":
            # Always use combat icon for generic multiattack (don't trust AI for this common case)
            multiattack_icon = "icons/skills/melee/blade-tips-triple-steel.webp"
        else:
            # Other special multiattacks use AI suggestion or generic default
            multiattack_icon = icon_map.get(
                parsed_actor.multiattack.name,
                "icons/magic/movement/trail-streak-zigzag-yellow.webp"
            )

        item = {
            "_id": _generate_activity_id(),
            "name": parsed_actor.multiattack.name,
            "type": "feat",
            "img": multiattack_icon,
            "system": {
                "description": {"value": parsed_actor.multiattack.description},
                "activation": {
                    "type": parsed_actor.multiattack.activation,
                    "value": None,
                    "condition": ""
                },
                "activities": {activity_id: activity},
                "uses": {}
            }
        }
        items.append(item)

    # Convert spells - collect UUIDs for /give endpoint
    for spell in parsed_actor.spells:
        # Get UUID from cache or spell object (cache first, then fallback to spell.uuid)
        spell_uuid = None
        if spell_cache:
            spell_uuid = spell_cache.get_spell_uuid(spell.name)
        # Fallback to spell's uuid if cache miss or cache not available
        if not spell_uuid and spell.uuid:
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
            # Look up UUID from cache or spell object (cache first, then fallback)
            spell_uuid = None
            if spell_cache:
                spell_uuid = spell_cache.get_spell_uuid(spell.name)
            # Fallback to spell's uuid if cache miss or cache not available
            if not spell_uuid and hasattr(spell, 'uuid') and spell.uuid:
                spell_uuid = spell.uuid

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
