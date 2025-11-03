"""Parallel parser for converting StatBlock to ParsedActorData using Gemini."""

import asyncio
import json
import logging
from typing import Optional, Union
from pathlib import Path
import os

import google.generativeai as genai
from dotenv import load_dotenv

from actors.models import StatBlock
from foundry.actors.models import (
    ParsedActorData, Attack, Trait, Multiattack,
    InnateSpellcasting, InnateSpell, DamageFormula, AttackSave,
    SkillProficiency, DamageModification
)
from foundry.actors.spell_cache import SpellCache

# Load environment
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Configure Gemini
genai.configure(api_key=os.getenv("GeminiImageAPI"))

logger = logging.getLogger(__name__)

# Model configuration
DEFAULT_MODEL = "gemini-2.0-flash"
PARSE_TEMPERATURE = 0.0  # Deterministic parsing


def parse_senses(senses_str: Optional[str]) -> dict:
    """
    Parse senses string into structured fields.

    Example: "Darkvision 60 ft., Passive Perception 14"
    Returns: {"darkvision": 60, "passive_perception": 14}
    """
    import re

    if not senses_str:
        return {}

    result = {}

    # Parse darkvision (e.g., "Darkvision 60 ft.")
    darkvision_match = re.search(r'darkvision\s+(\d+)\s*ft', senses_str, re.IGNORECASE)
    if darkvision_match:
        result["darkvision"] = int(darkvision_match.group(1))

    # Parse blindsight
    blindsight_match = re.search(r'blindsight\s+(\d+)\s*ft', senses_str, re.IGNORECASE)
    if blindsight_match:
        result["blindsight"] = int(blindsight_match.group(1))

    # Parse tremorsense
    tremorsense_match = re.search(r'tremorsense\s+(\d+)\s*ft', senses_str, re.IGNORECASE)
    if tremorsense_match:
        result["tremorsense"] = int(tremorsense_match.group(1))

    # Parse truesight
    truesight_match = re.search(r'truesight\s+(\d+)\s*ft', senses_str, re.IGNORECASE)
    if truesight_match:
        result["truesight"] = int(truesight_match.group(1))

    # Parse passive perception
    passive_match = re.search(r'passive\s+perception\s+(\d+)', senses_str, re.IGNORECASE)
    if passive_match:
        result["passive_perception"] = int(passive_match.group(1))

    return result


async def parse_single_action_async(
    action_text: str,
    model_name: str = DEFAULT_MODEL
) -> Union[Attack, Multiattack, Trait]:
    """
    Parse a single action entry into Attack, Multiattack, or Trait.

    Actions can be:
    - Attacks (e.g., "Tentacles. Melee Weapon Attack: +5...")
    - Multiattack (e.g., "Multiattack. The creature makes...")
    - Special actions (e.g., "Ink Cloud. A 20-foot-radius cloud...")

    Args:
        action_text: Raw action text
        model_name: Gemini model to use

    Returns:
        Attack, Multiattack, or Trait object
    """
    # Detect if this is a multiattack
    is_multiattack = "multiattack" in action_text.lower()

    # Detect if this is an attack (supports both 2014 and 2024 D&D formats)
    # 2014: "Melee Weapon Attack:" or "Ranged Weapon Attack:"
    # 2024: "Melee Attack Roll:" or "Ranged Attack Roll:"
    is_attack = (
        "weapon attack:" in action_text.lower() or
        "spell attack:" in action_text.lower() or
        "attack roll:" in action_text.lower()
    )

    if is_multiattack:
        schema = {
            "name": "Multiattack",
            "description": "The pit fiend makes four attacks...",
            "num_attacks": 4
        }
        prompt = f"""
Parse this D&D 5e multiattack action into JSON.

ACTION TEXT:
{action_text}

OUTPUT JSON SCHEMA:
{{
  "name": "string (action name)",
  "description": "string (full description)",
  "num_attacks": integer (number of attacks, e.g., 'three attacks' → 3)
}}

Extract the number of attacks from phrases like "makes X attacks", "three attacks", etc.

OUTPUT ONLY VALID JSON. No explanations.
"""
    elif is_attack:
        schema = {
            "name": "Scimitar",
            "attack_type": "melee",
            "attack_bonus": 4,
            "reach": 5,
            "damage": [
                {"number": 1, "denomination": 6, "bonus": "+2", "type": "slashing"}
            ],
            "attack_save": {
                "ability": "con",
                "dc": 13,
                "damage": [{"number": 2, "denomination": 6, "bonus": "", "type": "poison"}],
                "on_save": "half"
            }
        }
        prompt = f"""
Parse this D&D 5e attack action into JSON.

ACTION TEXT:
{action_text}

OUTPUT JSON SCHEMA:
{{
  "name": "string (weapon name)",
  "attack_type": "string ('melee' or 'ranged')",
  "attack_bonus": integer (e.g., '+4 to hit' → 4),
  "reach": integer (for melee, in feet),
  "range": integer (for ranged, short range in feet),
  "range_long": integer (for ranged, long range in feet),
  "damage": [
    {{
      "number": integer (dice count, e.g., '2d6' → 2),
      "denomination": integer (die size, e.g., '2d6' → 6),
      "bonus": "string (modifier with sign, e.g., '+2' or '')",
      "type": "string (damage type: slashing, piercing, bludgeoning, fire, etc.)"
    }}
  ],
  "attack_save": {{  // OPTIONAL - only if attack requires a saving throw
    "ability": "string (con, dex, wis, etc.)",
    "dc": integer,
    "damage": [{{...}}],  // Damage on failed save
    "ongoing_damage": [{{...}}],  // OPTIONAL - damage each turn
    "duration_rounds": integer,  // OPTIONAL - duration of ongoing effect
    "on_save": "string ('half', 'none', 'negates')",
    "effect_description": "string"  // OPTIONAL
  }}
}}

PARSING RULES:
1. attack_type: "melee" for melee attacks, "ranged" for ranged attacks, "melee_ranged" for "Melee or Ranged"
2. attack_bonus: Extract from "+X to hit" or "Attack Roll: +X" (just the number)
3. reach: For melee, extract from "reach X ft"
4. range/range_long: For ranged, extract from "range X/Y ft" or "range X ft"
5. damage: Parse "XdY+Z damage_type" or "X (XdY + Z) damage_type" format. Can have multiple damage entries.
6. attack_save: Include ONLY if the attack description mentions a saving throw (DC X ability save)
7. ongoing_damage: Include ONLY if damage continues each turn/round

SUPPORTS BOTH 2014 AND 2024 D&D FORMATS:
- 2014: "Melee Weapon Attack: +5 to hit"
- 2024: "Melee Attack Roll: +12, reach 5 ft. Hit: 31 (4d12 + 5) Force damage"

OUTPUT ONLY VALID JSON. No explanations.
"""
    else:
        # Special action (not an attack) - parse as Trait with activation
        prompt = f"""
Parse this D&D 5e special action into JSON.

ACTION TEXT:
{action_text}

OUTPUT JSON SCHEMA:
{{
  "name": "string (action name)",
  "description": "string (full description)",
  "activation": "string ('action', 'bonus', 'reaction', 'legendary')"
}}

ACTIVATION TYPE RULES:
- "action": Requires an action to use (most common for special actions like Breath Weapon, Ink Cloud)
- "bonus": Requires a bonus action
- "reaction": Triggered reaction
- "legendary": Legendary action

Most special actions use "action" unless the description mentions bonus action, reaction, or legendary.

OUTPUT ONLY VALID JSON. No explanations.
"""

    # Call Gemini
    model = genai.GenerativeModel(model_name)
    response = await model.generate_content_async(
        prompt,
        generation_config=genai.GenerationConfig(
            temperature=PARSE_TEMPERATURE,
            response_mime_type="application/json"
        )
    )

    # Parse response
    parsed_json = json.loads(response.text)
    logger.debug(f"Gemini response type: {type(parsed_json)}, value: {parsed_json}")

    # Handle case where Gemini returns a list instead of dict
    if isinstance(parsed_json, list):
        if len(parsed_json) == 0:
            raise ValueError(f"Gemini returned empty list for action: {action_text[:100]}")
        parsed_json = parsed_json[0]  # Take first element
        logger.warning(f"Gemini returned list instead of dict, using first element")

    # Create appropriate object
    if is_multiattack:
        return Multiattack(**parsed_json)
    elif is_attack:
        # Convert damage formulas
        if "damage" in parsed_json:
            parsed_json["damage"] = [
                DamageFormula(**dmg) for dmg in parsed_json["damage"]
            ]

        # Convert attack save if present
        if "attack_save" in parsed_json and parsed_json["attack_save"]:
            save_data = parsed_json["attack_save"]
            if "damage" in save_data:
                save_data["damage"] = [DamageFormula(**dmg) for dmg in save_data["damage"]]
            if "ongoing_damage" in save_data:
                save_data["ongoing_damage"] = [DamageFormula(**dmg) for dmg in save_data["ongoing_damage"]]
            parsed_json["attack_save"] = AttackSave(**save_data)

        return Attack(**parsed_json)
    else:
        # Special action - return as Trait
        return Trait(**parsed_json)


async def parse_single_trait_async(
    trait_text: str,
    spell_cache: Optional[SpellCache] = None,
    model_name: str = DEFAULT_MODEL
) -> Union[Trait, InnateSpellcasting]:
    """
    Parse a single trait entry into Trait or InnateSpellcasting.

    Args:
        trait_text: Raw trait text
        spell_cache: Optional spell cache for UUID resolution
        model_name: Gemini model to use

    Returns:
        Trait or InnateSpellcasting object
    """
    # Detect if this is innate spellcasting
    is_spellcasting = "spellcasting" in trait_text.lower() and "innate" in trait_text.lower()

    if is_spellcasting:
        return await parse_innate_spellcasting_async(trait_text, spell_cache, model_name)
    else:
        prompt = f"""
Parse this D&D 5e trait/feature into JSON.

TRAIT TEXT:
{trait_text}

OUTPUT JSON SCHEMA:
{{
  "name": "string (trait name, e.g., 'Nimble Escape')",
  "description": "string (full description)",
  "activation": "string ('passive', 'action', 'bonus', 'reaction', 'legendary')"
}}

ACTIVATION TYPE RULES:
- "passive": Always active, no action required (e.g., Magic Resistance, Keen Senses)
- "action": Requires an action to use (e.g., Breath Weapon, Frightful Presence)
- "bonus": Requires a bonus action (e.g., Nimble Escape allows Disengage/Hide as bonus action)
- "reaction": Triggered reaction (e.g., Parry, Shield)
- "legendary": Legendary action

Most traits are "passive" unless the description mentions an action type.

OUTPUT ONLY VALID JSON. No explanations.
"""

        model = genai.GenerativeModel(model_name)
        response = await model.generate_content_async(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=PARSE_TEMPERATURE,
                response_mime_type="application/json"
            )
        )

        parsed_json = json.loads(response.text)
        logger.debug(f"Gemini trait response type: {type(parsed_json)}, value: {parsed_json}")

        # Handle case where Gemini returns a list instead of dict
        if isinstance(parsed_json, list):
            if len(parsed_json) == 0:
                raise ValueError(f"Gemini returned empty list for trait: {trait_text[:100]}")
            parsed_json = parsed_json[0]
            logger.warning(f"Gemini returned list instead of dict for trait, using first element")

        return Trait(**parsed_json)


async def parse_innate_spellcasting_async(
    trait_text: str,
    spell_cache: Optional[SpellCache] = None,
    model_name: str = DEFAULT_MODEL
) -> InnateSpellcasting:
    """
    Parse innate spellcasting trait with spell UUID resolution.

    Args:
        trait_text: Raw innate spellcasting trait text
        spell_cache: Optional spell cache for UUID resolution
        model_name: Gemini model to use

    Returns:
        InnateSpellcasting object with resolved spell UUIDs
    """
    prompt = f"""
Parse this D&D 5e innate spellcasting trait into JSON.

TRAIT TEXT:
{trait_text}

OUTPUT JSON SCHEMA:
{{
  "ability": "string (charisma, intelligence, wisdom)",
  "save_dc": integer,
  "spells": [
    {{
      "name": "string (spell name, lowercase)",
      "frequency": "string ('at will', '3/day', '1/day', etc.)",
      "uses": integer (OPTIONAL - only for limited use spells, e.g., '3/day' → 3)
    }}
  ]
}}

PARSING RULES:
1. ability: Extract from "(Charisma)" or similar in the trait name
2. save_dc: Extract from "spell save DC X"
3. spells: Parse spell list organized by frequency
   - "At will: detect magic, fireball" → frequency: "at will"
   - "3/day each: hold monster" → frequency: "3/day", uses: 3
   - "1/day: wish" → frequency: "1/day", uses: 1
4. Spell names should be lowercase and match official D&D 5e spell names

OUTPUT ONLY VALID JSON. No explanations.
"""

    model = genai.GenerativeModel(model_name)
    response = await model.generate_content_async(
        prompt,
        generation_config=genai.GenerationConfig(
            temperature=PARSE_TEMPERATURE,
            response_mime_type="application/json"
        )
    )

    parsed_json = json.loads(response.text)
    logger.debug(f"Gemini spellcasting response type: {type(parsed_json)}, value: {parsed_json}")

    # Handle case where Gemini returns a list instead of dict
    if isinstance(parsed_json, list):
        if len(parsed_json) == 0:
            raise ValueError(f"Gemini returned empty list for spellcasting: {trait_text[:100]}")
        parsed_json = parsed_json[0]
        logger.warning(f"Gemini returned list instead of dict for spellcasting, using first element")

    # Resolve spell UUIDs if spell_cache provided
    if spell_cache:
        for spell in parsed_json["spells"]:
            uuid = spell_cache.get_spell_uuid(spell["name"])
            if uuid:
                spell["uuid"] = uuid
            else:
                logger.warning(f"Spell '{spell['name']}' not found in cache")

    # Create InnateSpell objects
    parsed_json["spells"] = [InnateSpell(**spell) for spell in parsed_json["spells"]]

    return InnateSpellcasting(**parsed_json)


async def parse_stat_block_parallel(
    stat_block: StatBlock,
    spell_cache: Optional[SpellCache] = None,
    model_name: str = DEFAULT_MODEL
) -> ParsedActorData:
    """
    Parse StatBlock to ParsedActorData with maximum parallelization.

    Each action, trait, and reaction is parsed in parallel using async Gemini calls.

    Args:
        stat_block: StatBlock with pre-split lists
        spell_cache: Optional spell cache for spell UUID resolution
        model_name: Gemini model to use

    Returns:
        ParsedActorData with fully structured attacks, traits, spells
    """
    logger.info(f"Parsing {stat_block.name} with {len(stat_block.actions)} actions, {len(stat_block.traits)} traits")

    # Create parse tasks for all items in parallel
    action_tasks = [
        parse_single_action_async(action_text, model_name)
        for action_text in stat_block.actions
    ]

    trait_tasks = [
        parse_single_trait_async(trait_text, spell_cache, model_name)
        for trait_text in stat_block.traits
    ]

    reaction_tasks = [
        parse_single_trait_async(reaction_text, spell_cache, model_name)
        for reaction_text in stat_block.reactions
    ]

    legendary_action_tasks = [
        parse_single_trait_async(legendary_text, spell_cache, model_name)
        for legendary_text in stat_block.legendary_actions
    ]

    # Run all tasks in parallel
    logger.debug(f"Starting {len(action_tasks) + len(trait_tasks) + len(reaction_tasks) + len(legendary_action_tasks)} parallel Gemini calls")

    action_results, trait_results, reaction_results, legendary_results = await asyncio.gather(
        asyncio.gather(*action_tasks) if action_tasks else asyncio.sleep(0, result=[]),
        asyncio.gather(*trait_tasks) if trait_tasks else asyncio.sleep(0, result=[]),
        asyncio.gather(*reaction_tasks) if reaction_tasks else asyncio.sleep(0, result=[]),
        asyncio.gather(*legendary_action_tasks) if legendary_action_tasks else asyncio.sleep(0, result=[])
    )

    # Separate multiattack from regular attacks and special actions
    multiattack = None
    attacks = []
    traits = []
    for result in action_results:
        if isinstance(result, Multiattack):
            multiattack = result
        elif isinstance(result, Attack):
            attacks.append(result)
        elif isinstance(result, Trait):
            # Special actions (like Ink Cloud) parsed as Traits
            traits.append(result)

    # Separate innate spellcasting from regular traits
    innate_spellcasting = None
    for result in trait_results:
        if isinstance(result, InnateSpellcasting):
            innate_spellcasting = result
        elif isinstance(result, Trait):
            traits.append(result)

    # Reactions are just traits with reaction activation
    traits.extend([t for t in reaction_results if isinstance(t, Trait)])

    # Legendary actions are traits with legendary activation
    traits.extend([t for t in legendary_results if isinstance(t, Trait)])

    logger.info(f"Parsed {stat_block.name}: {len(attacks)} attacks, {len(traits)} traits, {multiattack is not None} multiattack, {innate_spellcasting is not None} spellcasting")

    # Convert saving throws to proficiency list
    saving_throw_proficiencies = []
    if stat_block.saving_throws:
        saving_throw_proficiencies = list(stat_block.saving_throws.keys())

    # Convert skills to SkillProficiency objects
    skill_proficiencies = []
    if stat_block.skills:
        for skill_name, bonus in stat_block.skills.items():
            skill_proficiencies.append(SkillProficiency(
                skill=skill_name.capitalize(),
                bonus=bonus,
                proficiency_level=1  # Assume proficient (not expertise)
            ))

    # Parse senses
    senses = parse_senses(stat_block.senses)

    # Parse damage modifiers into DamageModification objects
    damage_resistances = None
    if stat_block.damage_resistances:
        types = [r.strip().lower() for r in stat_block.damage_resistances.split(',')]
        damage_resistances = DamageModification(types=types)

    damage_immunities = None
    if stat_block.damage_immunities:
        types = [i.strip().lower() for i in stat_block.damage_immunities.split(',')]
        damage_immunities = DamageModification(types=types)

    damage_vulnerabilities = None
    if stat_block.damage_vulnerabilities:
        types = [v.strip().lower() for v in stat_block.damage_vulnerabilities.split(',')]
        damage_vulnerabilities = DamageModification(types=types)

    condition_immunities_list = []
    if stat_block.condition_immunities:
        condition_immunities_list = [c.strip().lower() for c in stat_block.condition_immunities.split(',')]

    # Build ParsedActorData
    return ParsedActorData(
        source_statblock_name=stat_block.name,
        name=stat_block.name,
        armor_class=stat_block.armor_class,
        hit_points=stat_block.hit_points,
        challenge_rating=stat_block.challenge_rating,
        abilities=stat_block.abilities or {},
        saving_throw_proficiencies=saving_throw_proficiencies,
        skill_proficiencies=skill_proficiencies,
        attacks=attacks,
        traits=traits,
        multiattack=multiattack,
        innate_spellcasting=innate_spellcasting,
        size=stat_block.size,
        creature_type=stat_block.type,
        alignment=stat_block.alignment,
        darkvision=senses.get("darkvision"),
        blindsight=senses.get("blindsight"),
        tremorsense=senses.get("tremorsense"),
        truesight=senses.get("truesight"),
        passive_perception=senses.get("passive_perception"),
        damage_resistances=damage_resistances,
        damage_immunities=damage_immunities,
        damage_vulnerabilities=damage_vulnerabilities,
        condition_immunities=condition_immunities_list
    )


# Convenience function for parsing multiple stat blocks
async def parse_multiple_stat_blocks(
    stat_blocks: list[StatBlock],
    spell_cache: Optional[SpellCache] = None,
    model_name: str = DEFAULT_MODEL
) -> list[ParsedActorData]:
    """
    Parse multiple stat blocks in parallel.

    Args:
        stat_blocks: List of StatBlock objects
        spell_cache: Optional spell cache
        model_name: Gemini model to use

    Returns:
        List of ParsedActorData objects
    """
    tasks = [
        parse_stat_block_parallel(sb, spell_cache, model_name)
        for sb in stat_blocks
    ]

    return await asyncio.gather(*tasks)
