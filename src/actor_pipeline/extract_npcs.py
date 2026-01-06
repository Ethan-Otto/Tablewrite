"""Extract named NPCs from generated XML using Gemini."""

import logging
import json
from typing import List, Optional
from util.gemini import GeminiAPI
from .models import NPC

logger = logging.getLogger(__name__)


def identify_npcs_with_gemini(
    xml_content: str,
    api: Optional[GeminiAPI] = None
) -> List[NPC]:
    """
    Identify named NPCs from XML content using Gemini.

    Analyzes the XML structure and narrative text to find named characters
    with plot relevance. Links NPCs to their creature stat blocks if available.

    Args:
        xml_content: XML content to analyze
        api: Optional GeminiAPI instance (creates new one if not provided)

    Returns:
        List of NPC objects

    Raises:
        RuntimeError: If Gemini API call fails
    """
    if api is None:
        api = GeminiAPI()

    logger.debug(f"Analyzing XML for NPCs (length: {len(xml_content)} chars)")

    # Construct NPC identification prompt
    prompt = f"""Analyze this D&D module XML and identify all named NPCs (non-player characters).

For each named NPC, extract:
- name (string): The NPC's name (e.g., "Klarg", "Sildar Hallwinter")
- creature_stat_block_name (string): The creature type/stat block this NPC uses (e.g., "Bugbear", "Human Fighter")
  - Look for nearby <stat_block> tags or descriptions like "Klarg, a bugbear" → "Bugbear"
  - Use the stat block name exactly as it appears in <stat_block name="...">
- description (string): Brief physical or personality description (1-2 sentences)
- plot_relevance (string): Why this NPC matters to the story (1-2 sentences)
- location (string, optional): Where the NPC is found (e.g., "Cragmaw Hideout", "Area 6")
- first_appearance_section (string, optional): Section where NPC first appears (e.g., "Chapter 1 → Goblin Ambush")

IMPORTANT:
- Only include NAMED characters (e.g., "Klarg", "Sildar"), NOT generic enemies ("goblins", "bandits")
- Link NPCs to stat blocks by finding nearby <stat_block name="..."> tags or creature type mentions
- If a stat block isn't found, infer the creature type from context (e.g., "human fighter" → "Human Fighter")

Return ONLY valid JSON array with these exact field names:
[
  {{
    "name": "Klarg",
    "creature_stat_block_name": "Bugbear",
    "description": "Leader of the Cragmaw goblins, wears a tattered cloak",
    "plot_relevance": "Guards stolen supplies, has taken Sildar prisoner",
    "location": "Cragmaw Hideout, Area 6",
    "first_appearance_section": "Chapter 1 → Cragmaw Hideout"
  }}
]

If no named NPCs found, return empty array: []

Do not include markdown formatting or explanation.

XML content:
{xml_content}"""

    try:
        # Call Gemini
        response = api.generate_content(prompt)
        response_text = response.text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()

        # Parse JSON
        parsed_data = json.loads(response_text)

        # Validate and create NPC objects
        npcs = []
        for npc_data in parsed_data:
            try:
                npc = NPC(**npc_data)
                npcs.append(npc)
            except Exception as e:
                logger.warning(f"Failed to validate NPC data: {e}")
                logger.debug(f"Invalid NPC data: {npc_data}")
                continue

        logger.info(f"Identified {len(npcs)} NPC(s) from XML")
        return npcs

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response as JSON: {e}")
        logger.debug(f"Response text: {response_text}")
        raise RuntimeError(f"Invalid JSON from Gemini: {e}") from e

    except Exception as e:
        logger.error(f"Failed to extract NPCs: {e}")
        raise RuntimeError(f"NPC extraction failed: {e}") from e
