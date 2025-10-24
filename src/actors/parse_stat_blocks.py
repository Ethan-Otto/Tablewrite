"""Parse D&D 5e stat blocks using Gemini."""

import logging
import json
from typing import Optional
from util.gemini import GeminiAPI
from .models import StatBlock

logger = logging.getLogger(__name__)


def parse_stat_block_with_gemini(raw_text: str, api: Optional[GeminiAPI] = None) -> StatBlock:
    """
    Parse a D&D 5e stat block using Gemini.

    Args:
        raw_text: Raw stat block text
        api: Optional GeminiAPI instance (creates new one if not provided)

    Returns:
        Parsed StatBlock object

    Raises:
        ValueError: If parsing fails or result is invalid
        RuntimeError: If Gemini API call fails
    """
    if api is None:
        api = GeminiAPI()

    logger.debug(f"Parsing stat block (length: {len(raw_text)} chars)")

    # Construct parsing prompt
    prompt = f"""Parse this D&D 5e stat block into structured JSON.

Extract the following fields:
- name (string): Creature name
- armor_class (integer): AC value only (not the parenthetical armor type)
- hit_points (integer): HP value only (not the dice formula)
- challenge_rating (float): CR as decimal (1/4 = 0.25, 1/2 = 0.5)
- size (string, optional): Creature size
- type (string, optional): Creature type
- alignment (string, optional): Alignment
- abilities (object, optional): {{STR: int, DEX: int, CON: int, INT: int, WIS: int, CHA: int}}
- speed (string, optional): Speed description
- senses (string, optional): Senses description
- languages (string, optional): Languages
- traits (string, optional): Special traits (everything between stats and ACTIONS)
- actions (string, optional): Actions section (everything after ACTIONS header)

Return ONLY valid JSON with these exact field names. Do not include any markdown formatting or explanation.

Stat block:
{raw_text}"""

    try:
        # Call Gemini
        response = api.generate_content(prompt)
        response_text = response.text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            # Remove first and last lines (``` markers)
            response_text = "\n".join(lines[1:-1])
            # Remove language identifier if present
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()

        # Parse JSON
        parsed_data = json.loads(response_text)

        # Add raw_text to parsed data
        parsed_data["raw_text"] = raw_text

        # Create and validate StatBlock
        stat_block = StatBlock(**parsed_data)

        logger.info(f"Successfully parsed stat block: {stat_block.name} (CR {stat_block.challenge_rating})")
        return stat_block

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response as JSON: {e}")
        logger.debug(f"Response text: {response_text}")
        raise ValueError(f"Invalid JSON from Gemini: {e}") from e

    except Exception as e:
        logger.error(f"Failed to parse stat block: {e}")
        raise RuntimeError(f"Stat block parsing failed: {e}") from e
