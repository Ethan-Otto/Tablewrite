"""Gemini-powered parser for converting raw D&D 5e stat block text to StatBlock."""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional

from google import genai
from dotenv import load_dotenv

from actors.models import StatBlock

# Load environment
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Configure Gemini (lazy initialization)
_client = None

def get_client():
    """Get or create the Gemini client."""
    global _client
    if _client is None:
        api_key = os.getenv("GeminiImageAPI")
        if not api_key:
            raise ValueError("GeminiImageAPI environment variable not set")
        _client = genai.Client(api_key=api_key)
    return _client

logger = logging.getLogger(__name__)

# Model configuration
DEFAULT_MODEL = "gemini-2.0-flash"
PARSE_TEMPERATURE = 0.0  # Deterministic parsing


async def parse_raw_text_to_statblock(
    raw_text: str,
    model_name: str = DEFAULT_MODEL
) -> StatBlock:
    """
    Parse raw D&D 5e stat block text into StatBlock using Gemini.

    Args:
        raw_text: Complete stat block text
        model_name: Gemini model to use

    Returns:
        StatBlock with all fields extracted

    Example input:
        Giant Octopus
        Large Beast, Unaligned
        Armor Class 11
        Hit Points 52 (8d10 + 8)
        Speed 10 ft., swim 60 ft.
        STR 17 (+3)
        DEX 13 (+1)
        ...
        Skills Perception +4, Stealth +5
        ...
        Traits
        Hold Breath. While out of water...
        Actions
        Tentacles. Melee Weapon Attack: +5 to hit...
    """
    prompt = f"""Parse this D&D 5e stat block into JSON format.

STAT BLOCK TEXT:
{raw_text}

OUTPUT JSON SCHEMA:
{{
  "name": "string (creature name, e.g., 'Giant Octopus')",
  "armor_class": integer,
  "hit_points": integer,
  "challenge_rating": float (use 0.125 for CR 1/8, 0.25 for CR 1/4, 0.5 for CR 1/2),

  "size": "string (tiny, small, medium, large, huge, gargantuan) LOWERCASE",
  "type": "string (beast, humanoid, fiend, etc.) LOWERCASE",
  "alignment": "string (lawful evil, unaligned, etc.) LOWERCASE or null",

  "abilities": {{
    "STR": integer,
    "DEX": integer,
    "CON": integer,
    "INT": integer,
    "WIS": integer,
    "CHA": integer
  }},

  "speed": "string (e.g., '30 ft., fly 60 ft.') or null",
  "senses": "string (e.g., 'Darkvision 60 ft., Passive Perception 14') or null",
  "languages": "string (e.g., 'Infernal, Telepathy 120 ft.' or '--' for none) or null",

  "damage_resistances": "string (e.g., 'Fire, Cold; Bludgeoning from Nonmagical Attacks') or null",
  "damage_immunities": "string (e.g., 'Poison, Fire') or null",
  "damage_vulnerabilities": "string or null",
  "condition_immunities": "string (e.g., 'Poisoned, Charmed') or null",

  "saving_throws": {{
    "dex": integer,
    "con": integer,
    "wis": integer
  }} or null,

  "skills": {{
    "perception": integer,
    "stealth": integer,
    "intimidation": integer
  }} or null,

  "traits": [
    "string (complete trait entry from Traits section, e.g., 'Hold Breath. While out of water, the octopus can hold its breath for 1 hour.')"
  ],

  "actions": [
    "string (complete action entry from Actions section - includes both attacks AND special actions)",
    "string (e.g., 'Tentacles. Melee Weapon Attack: +5 to hit...' OR 'Ink Cloud (Recharges after a Short or Long Rest). A 20-foot-radius cloud...')"
  ],

  "reactions": [
    "string (complete reaction entry)"
  ],

  "legendary_actions": [
    "string (complete legendary action entry)"
  ]
}}

PARSING RULES:
1. Extract name from the first line
2. Extract size and type from line like "Large Beast, Unaligned"
3. Parse abilities from ability score block (STR, DEX, CON, INT, WIS, CHA)
4. For saving_throws: Extract from "Saving Throws DEX +8, CON +13" → {{"dex": 8, "con": 13}}
   - Use LOWERCASE ability names (dex, con, wis, str, int, cha)
   - Include ONLY abilities listed in saving throws line
5. For skills: Extract from "Skills Perception +4, Stealth +5" → {{"perception": 4, "stealth": 5}}
   - Use LOWERCASE skill names
   - Include ONLY skills explicitly listed
6. For traits/actions/reactions: Preserve the D&D 5e structure exactly as it appears:
   - traits: Everything listed under "Traits" section
   - actions: Everything listed under "Actions" section (both attacks AND special actions like Ink Cloud, Breath Weapon)
   - Each entry should start with the ability name followed by period and full description
   - Example: "Hold Breath. While out of water, the octopus can hold its breath for 1 hour."
7. If a section is missing (no Reactions, no Legendary Actions), use empty list []
8. If a field doesn't exist in the stat block, use null

OUTPUT ONLY VALID JSON. No explanations.
"""

    # Use asyncio.to_thread since generate_content is synchronous
    response = await asyncio.to_thread(
        get_client().models.generate_content,
        model=model_name,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=PARSE_TEMPERATURE,
            response_mime_type="application/json"
        )
    )

    # Parse response
    parsed_json = json.loads(response.text)
    logger.debug(f"Gemini parsed stat block: {parsed_json.get('name')}")

    # Handle case where Gemini returns a list instead of dict
    if isinstance(parsed_json, list):
        if len(parsed_json) == 0:
            raise ValueError(f"Gemini returned empty list for stat block")
        parsed_json = parsed_json[0]
        logger.warning(f"Gemini returned list instead of dict, using first element")

    # Add raw_text to the JSON
    parsed_json["raw_text"] = raw_text

    # Create StatBlock
    return StatBlock(**parsed_json)
