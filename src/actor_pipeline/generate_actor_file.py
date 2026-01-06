"""Generate D&D 5e actor text files from descriptions using Gemini.

This module uses Gemini to create complete stat blocks and bios from natural
language descriptions. The generated text files can then be processed through
the existing pipeline:
  1. Text file → parse_raw_text_to_statblock() → StatBlock
  2. StatBlock → parse_stat_block_parallel() → ParsedActorData
  3. ParsedActorData → convert_to_foundry() → FoundryVTT actor JSON
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from google import genai
from dotenv import load_dotenv

from util.gemini import generate_content_async

# Load environment
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)

# Model configuration
DEFAULT_MODEL = "gemini-2.5-pro"
GENERATION_TEMPERATURE = 0.7  # Creative but consistent


async def generate_actor_description(
    description: str,
    challenge_rating: Optional[float] = None,
    model_name: str = DEFAULT_MODEL
) -> str:
    """
    Generate a complete D&D 5e stat block from natural language description.

    This is a simpler version that returns the raw text directly (used by orchestrate.py).
    For a version that saves to file with more options, use generate_actor_from_description.

    Args:
        description: Natural language description of the actor
        challenge_rating: Optional CR (0.125-30). If None, Gemini determines it.
        model_name: Gemini model to use (default: gemini-2.5-pro)

    Returns:
        Generated stat block text in D&D 5e format

    Example:
        raw_text = await generate_actor_description(
            "A cunning goblin assassin with poisoned daggers",
            challenge_rating=2.0
        )
    """
    # Use the full version but don't save to file
    temp_output = Path("/tmp") / "temp_actor.txt"
    result_path = await generate_actor_from_description(
        description=description,
        challenge_rating=challenge_rating,
        output_path=temp_output,
        model_name=model_name
    )

    # Read the generated text and return it
    text = result_path.read_text(encoding="utf-8")

    # Clean up temp file
    try:
        result_path.unlink()
    except Exception:
        pass

    return text


async def generate_actor_from_description(
    description: str,
    challenge_rating: Optional[float] = None,
    name: Optional[str] = None,
    bio_context: Optional[str] = None,
    output_path: Optional[Path] = None,
    model_name: str = DEFAULT_MODEL
) -> Path:
    """
    Generate a complete D&D 5e actor file from a description using Gemini.

    Args:
        description: Natural language description of the creature/NPC
        challenge_rating: Optional CR (0.125, 0.25, 0.5, 1-30). If not provided, Gemini will determine appropriate CR.
        name: Optional custom name (Gemini will generate if not provided)
        bio_context: Optional additional context for biography
        output_path: Optional custom output path (defaults to data/actors/<name>.txt)
        model_name: Gemini model to use (default: gemini-2.5-pro)

    Returns:
        Path to generated file

    Example:
        >>> # With explicit CR
        >>> path = await generate_actor_from_description(
        ...     description="A mutated sea creature with acidic tentacles and telepathic abilities",
        ...     challenge_rating=5,
        ...     bio_context="Found in the ruins of an underwater temple"
        ... )
        >>> # Let Gemini determine CR
        >>> path = await generate_actor_from_description(
        ...     description="An ancient lich with reality-warping powers",
        ...     bio_context="Destroyed kingdoms millennia ago"
        ... )
    """
    # Build comprehensive prompt
    cr_examples = {
        0.125: "CR 1/8 (25 XP) - weak creatures like kobolds",
        0.25: "CR 1/4 (50 XP) - goblins, skeletons",
        0.5: "CR 1/2 (100 XP) - orcs, giant wasps",
        1: "CR 1 (200 XP) - dire wolves, animated armor",
        2: "CR 2 (450 XP) - ogres, griffons",
        5: "CR 5 (1,800 XP) - hill giants, troll",
        10: "CR 10 (5,900 XP) - stone golems, young dragons",
        20: "CR 20 (25,000 XP) - pit fiends, ancient dragons"
    }

    if challenge_rating is not None:
        cr_guidance = cr_examples.get(challenge_rating, f"CR {challenge_rating}")
        cr_instruction = f"""CHALLENGE RATING: {challenge_rating} ({cr_guidance})

Use this exact CR for the stat block."""
    else:
        cr_instruction = """CHALLENGE RATING: Not specified - you must determine the appropriate CR.

REASONING PROCESS:
1. Analyze the description for power indicators:
   - Magical abilities (spells, innate magic)
   - Physical capabilities (size, strength, special attacks)
   - Defensive abilities (resistances, immunities, regeneration)
   - Tactical complexity (legendary actions, lair actions)
   - Narrative role (minion, boss, world-ending threat)

2. Consider CR benchmarks:
   - CR 0-1/4: Weak creatures (kobolds, skeletons, commoners)
   - CR 1/2-2: Common threats (orcs, goblins, zombies)
   - CR 3-5: Dangerous foes (ogres, griffons, basic spellcasters)
   - CR 6-10: Serious threats (giants, young dragons, mages)
   - CR 11-15: Deadly encounters (adult dragons, powerful demons)
   - CR 16-20: Legendary threats (ancient dragons, pit fiends)
   - CR 21-30: World-ending entities (demon lords, gods)

3. Select the most appropriate CR based on your analysis.
4. State your reasoning briefly after the stat block (before the Bio section).

Format:
[Stat block]

CR Reasoning: [1-2 sentences explaining why you chose this CR]

Bio
[Biography]"""

    prompt = f"""Generate a complete D&D 5e stat block and biography for a creature.

DESCRIPTION:
{description}

{cr_instruction}
{f"NAME: {name}" if name else ""}
{f"BIO CONTEXT: {bio_context}" if bio_context else ""}

REQUIREMENTS:
1. Create a balanced D&D 5e stat block appropriate for the chosen CR
2. Use official D&D 5e stat block format (see example below)
3. Include appropriate abilities, traits, and actions for the CR
4. Make the creature interesting and mechanically sound
5. Add a 2-3 paragraph biography that fits the description

STAT BLOCK FORMAT (follow exactly):
```
Creature Name
Size Type, Alignment
Armor Class X (description)
Hit Points X (XdY + Z)
Speed X ft., [additional movement]
STR
XX (+X)
DEX
XX (+X)
CON
XX (+X)
INT
XX (+X)
WIS
XX (+X)
CHA
XX (+X)
[Saving Throws ...]
[Skills ...]
[Damage Resistances ...]
[Damage Immunities ...]
[Damage Vulnerabilities ...]
[Condition Immunities ...]
Senses ..., Passive Perception XX
Languages ...
Challenge {challenge_rating} (XP)
Proficiency Bonus +X
Traits

Trait Name. Trait description.

[More traits...]
Actions

Action Name. Action description with mechanics.

[More actions...]

[Reactions]

Reaction Name. Reaction description.

[Legendary Actions]

The [creature] can take 3 legendary actions...
```

STAT BLOCK GUIDELINES:
- HP should be appropriate for the CR (roughly 15-30 per CR level)
- Attack bonuses should be roughly CR/2 + 5 (minimum +3)
- Damage should scale with CR (roughly 7-15 damage per CR level)
- Save DCs should be roughly 8 + proficiency bonus + ability modifier
- Include 1-3 interesting traits
- Include 2-5 actions (including Multiattack if CR >= 3)
- Consider legendary actions if CR >= 10
- Ensure all numbers are mechanically balanced for the chosen CR

SPELLCASTING FORMAT (use when creature has spells):
For spellcasting creatures, include a "Spellcasting" trait in the Traits section:

Spellcasting. The [creature] is a Xth-level spellcaster. Its spellcasting ability is [Intelligence/Wisdom/Charisma] (spell save DC X, +X to hit with spell attacks). The [creature] has the following spells prepared:

Cantrips (at will): fire bolt, light, mage hand
1st level (4 slots): mage armor, magic missile, shield
2nd level (3 slots): misty step, suggestion
3rd level (3 slots): counterspell, fireball, fly
4th level (2 slots): greater invisibility
5th level (1 slot): cone of cold

For innate spellcasting (racial/creature abilities without slots):

Innate Spellcasting. The [creature]'s innate spellcasting ability is [ability] (spell save DC X). It can innately cast the following spells, requiring no material components:

At will: detect magic, levitate
3/day each: dispel magic, invisibility
1/day: plane shift

After the stat block, add:

Bio

[2-3 paragraph biography describing the creature's nature, habitat, behavior, and role in the world]

OUTPUT ONLY THE STAT BLOCK AND BIO. No additional commentary or explanations.
"""

    # Call Gemini
    if challenge_rating is not None:
        logger.info(f"Generating CR {challenge_rating} creature: {description[:100]}...")
    else:
        logger.info(f"Generating creature (auto CR): {description[:100]}...")

    # Initialize client (uses GEMINI_API_KEY or GeminiImageAPI env var)
    client = genai.Client(api_key=os.getenv("GeminiImageAPI") or os.getenv("GEMINI_API_KEY"))

    response = await generate_content_async(
        client=client,
        model=model_name,
        contents=prompt,
        config={'temperature': GENERATION_TEMPERATURE}
    )

    generated_text = response.text.strip()

    # Extract creature name from first line if not provided
    if name is None:
        first_line = generated_text.split('\n')[0].strip()
        name = first_line
        logger.info(f"Generated creature: {name}")

    # Determine output path
    if output_path is None:
        output_dir = PROJECT_ROOT / "data" / "actors"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename
        safe_name = name.lower().replace(" ", "_").replace("'", "")
        output_path = output_dir / f"{safe_name}.txt"

    # Write to file
    output_path.write_text(generated_text, encoding="utf-8")

    logger.info(f"Generated actor file: {output_path}")
    return output_path


async def generate_multiple_actors(
    descriptions: list[tuple[str, Optional[float]]],
    output_dir: Optional[Path] = None
) -> list[Path]:
    """
    Generate multiple actor files in parallel.

    Args:
        descriptions: List of (description, challenge_rating) tuples. CR can be None for auto-determination.
        output_dir: Optional output directory (defaults to data/actors/)

    Returns:
        List of paths to generated files

    Example:
        >>> paths = await generate_multiple_actors([
        ...     ("A fire-breathing dragon", 15),
        ...     ("A cunning thief", None),  # Auto CR
        ...     ("An ancient lich", 21)
        ... ])
    """
    tasks = [
        generate_actor_from_description(desc, cr, output_path=output_dir)
        for desc, cr in descriptions
    ]

    return await asyncio.gather(*tasks)


# Synchronous wrapper for convenience
def generate_actor_sync(
    description: str,
    challenge_rating: Optional[float] = None,
    name: Optional[str] = None,
    bio_context: Optional[str] = None,
    output_path: Optional[Path] = None,
    model_name: str = DEFAULT_MODEL
) -> Path:
    """
    Synchronous wrapper for generate_actor_from_description.

    See generate_actor_from_description for full documentation.
    """
    return asyncio.run(generate_actor_from_description(
        description, challenge_rating, name, bio_context, output_path, model_name
    ))


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    async def main():
        # Example 1: Explicit CR - crystalline spider
        path1 = await generate_actor_from_description(
            description="A crystalline spider that feeds on magical energy",
            challenge_rating=3,
            bio_context="Lives in the Underdark near wizard towers"
        )
        print(f"Generated: {path1}")

        # Example 2: Auto CR - let Gemini decide based on description
        path2 = await generate_actor_from_description(
            description="A half-orc warrior who was raised by elves and fights with grace",
            name="Grok Silverblade",
            bio_context="Leader of the Moonwood Rangers"
        )
        print(f"Generated (auto CR): {path2}")

        # Example 3: Auto CR - ancient lich (should be high CR)
        path3 = await generate_actor_from_description(
            description="An ancient lich with reality-warping powers who destroyed entire kingdoms",
            bio_context="Awakened after millennia of slumber beneath a cursed mountain"
        )
        print(f"Generated (auto CR): {path3}")

        # Example 4: Explicit high CR - elemental titan
        path4 = await generate_actor_from_description(
            description="An elemental titan made of living storm clouds",
            challenge_rating=18,
            bio_context="Created by an ancient god as punishment for hubris"
        )
        print(f"Generated: {path4}")

    asyncio.run(main())
