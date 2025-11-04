"""Generate D&D 5e actor descriptions from natural language using Gemini."""

import logging
import os
from typing import Optional
from google import genai
from dotenv import load_dotenv

# Load environment
load_dotenv()

logger = logging.getLogger(__name__)

# Configure Gemini (lazy initialization)
_client = None

def get_client():
    """Get or create the Gemini client."""
    global _client
    if _client is None:
        api_key = os.getenv("GeminiImageAPI") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key not set (GeminiImageAPI or GEMINI_API_KEY)")
        _client = genai.Client(api_key=api_key)
    return _client

# Model configuration
DEFAULT_MODEL = "gemini-2.0-flash"
GENERATION_TEMPERATURE = 0.7  # Creative but consistent


async def generate_actor_description(
    description: str,
    challenge_rating: Optional[float] = None,
    model_name: str = "gemini-2.0-flash"
) -> str:
    """
    Generate a complete D&D 5e stat block from natural language description.

    Args:
        description: Natural language description of the actor
                    Example: "A fierce red dragon wyrmling with fire breath"
        challenge_rating: Optional CR to target (0.125-30). If None, Gemini determines it.
        model_name: Gemini model to use (default: "gemini-2.0-flash")

    Returns:
        Generated stat block text in D&D 5e format

    Raises:
        RuntimeError: If Gemini API call fails
        ValueError: If response is invalid

    Example:
        raw_text = await generate_actor_description(
            "A cunning goblin assassin with poisoned daggers",
            challenge_rating=2.0
        )
    """
    logger.info(f"Generating stat block for: {description[:50]}...")

    # Build CR instruction
    if challenge_rating is not None:
        cr_instruction = f"Challenge Rating: MUST be exactly {challenge_rating}"
    else:
        cr_instruction = "Challenge Rating: Determine an appropriate CR based on the description"

    prompt = f"""Generate a complete D&D 5e stat block for the following creature.

DESCRIPTION:
{description}

REQUIREMENTS:
- {cr_instruction}
- Follow official D&D 5e stat block format exactly
- Include: Name, Size/Type/Alignment, AC, HP, Speed, Ability Scores (STR, DEX, CON, INT, WIS, CHA)
- Include: Saving Throws, Skills, Damage Resistances/Immunities/Vulnerabilities (if appropriate)
- Include: Condition Immunities (if appropriate)
- Include: Senses, Languages
- Include: Traits (special abilities)
- Include: Actions (attacks and special actions)
- Include: Reactions (if appropriate)
- Include: Legendary Actions (if CR is high enough and creature is legendary)

OUTPUT FORMAT (example):
```
Goblin Assassin
Small humanoid (goblinoid), neutral evil
Armor Class 15 (leather armor)
Hit Points 27 (6d6 + 6)
Speed 30 ft.

STR 8 (-1)
DEX 17 (+3)
CON 12 (+1)
INT 10 (+0)
WIS 11 (+0)
CHA 8 (-1)

Skills Stealth +7, Sleight of Hand +5
Senses darkvision 60 ft., passive Perception 10
Languages Common, Goblin
Challenge 2 (450 XP)

Traits
Nimble Escape. The goblin can take the Disengage or Hide action as a bonus action on each of its turns.

Assassinate. During its first turn, the goblin has advantage on attack rolls against any creature that hasn't taken a turn. Any hit the goblin scores against a surprised creature is a critical hit.

Sneak Attack (1/Turn). The goblin deals an extra 7 (2d6) damage when it hits a target with a weapon attack and has advantage on the attack roll.

Actions
Multiattack. The goblin makes two attacks with its poisoned dagger.

Poisoned Dagger. Melee or Ranged Weapon Attack: +5 to hit, reach 5 ft. or range 20/60 ft., one target. Hit: 5 (1d4 + 3) piercing damage, and the target must succeed on a DC 11 Constitution saving throw or take 7 (2d6) poison damage and become poisoned for 1 minute.
```

Generate ONLY the stat block text, no additional commentary.
"""

    try:
        response = await get_client().models.generate_content_async(
            model=model_name,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=GENERATION_TEMPERATURE
            )
        )

        raw_text = response.text.strip()

        # Remove markdown code blocks if present
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            # Remove first line (``` or ```markdown)
            lines = lines[1:]
            # Remove last line (```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw_text = "\n".join(lines).strip()

        logger.info(f"Generated stat block: {len(raw_text)} characters")
        logger.debug(f"Stat block preview: {raw_text[:200]}...")

        return raw_text

    except Exception as e:
        logger.error(f"Failed to generate actor description: {e}")
        raise RuntimeError(f"Failed to generate actor description: {e}") from e
