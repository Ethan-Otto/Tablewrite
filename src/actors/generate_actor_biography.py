"""Generate flavorful biographies for D&D 5e creatures using Gemini."""

import asyncio
import logging
import os
from typing import Optional
import google.generativeai as genai

from foundry.actors.models import ParsedActorData

logger = logging.getLogger(__name__)

# Gemini client (lazy initialization)
_gemini_client = None


def _get_gemini_client():
    """Get or create Gemini client (lazy initialization)."""
    global _gemini_client
    if _gemini_client is None:
        api_key = os.getenv("GeminiImageAPI")
        if not api_key:
            raise ValueError("GeminiImageAPI environment variable not set")
        genai.configure(api_key=api_key)
        _gemini_client = genai
    return _gemini_client


async def generate_actor_biography(
    parsed_actor: ParsedActorData,
    model_name: str = "gemini-2.0-flash"
) -> str:
    """
    Generate a flavorful biography for a D&D 5e creature.

    Creates a descriptive paragraph about what the creature is like based on its
    stats, abilities, and special traits. This is NOT mechanical information, but
    rather flavor text describing the creature's nature, behavior, and appearance.

    Args:
        parsed_actor: The fully parsed actor data with stats, abilities, traits
        model_name: Gemini model to use (default: "gemini-2.0-flash")

    Returns:
        A 2-4 sentence biography/description of the creature

    Example:
        >>> bio = await generate_actor_biography(goblin_parsed_data)
        >>> print(bio)
        "Goblins are small, black-hearted, selfish humanoids that lair in caves,
         abandoned mines, despoiled dungeons, and other dismal settings. Individually
         weak, they gather in large numbers to torment other creatures."
    """
    logger.info(f"Generating biography for {parsed_actor.name}...")

    # Build a summary of the creature's key features
    summary_parts = []

    # Size and type
    if parsed_actor.size and parsed_actor.creature_type:
        summary_parts.append(f"Size: {parsed_actor.size}, Type: {parsed_actor.creature_type}")

    # Alignment
    if parsed_actor.alignment:
        summary_parts.append(f"Alignment: {parsed_actor.alignment}")

    # CR
    summary_parts.append(f"Challenge Rating: {parsed_actor.challenge_rating}")

    # Notable abilities
    ability_scores = []
    for ability, score in parsed_actor.abilities.items():
        modifier = (score - 10) // 2
        if modifier >= 3:  # Notable positive
            ability_scores.append(f"{ability.upper()} {score} (+{modifier})")
        elif modifier <= -2:  # Notable negative
            ability_scores.append(f"{ability.upper()} {score} ({modifier})")

    if ability_scores:
        summary_parts.append(f"Notable abilities: {', '.join(ability_scores)}")

    # Special traits (limit to 3)
    if parsed_actor.traits:
        trait_names = [t.name for t in parsed_actor.traits[:3]]
        summary_parts.append(f"Special traits: {', '.join(trait_names)}")

    # Attacks (limit to 3)
    if parsed_actor.attacks:
        attack_names = [a.name for a in parsed_actor.attacks[:3]]
        summary_parts.append(f"Attacks: {', '.join(attack_names)}")

    # Spellcasting
    if parsed_actor.spells:
        summary_parts.append(f"Spellcaster with {len(parsed_actor.spells)} spells")

    if parsed_actor.innate_spellcasting:
        summary_parts.append(f"Innate spellcasting ({parsed_actor.innate_spellcasting.ability})")

    # Build the prompt
    summary = "\n".join(f"- {part}" for part in summary_parts)

    prompt = f"""You are writing flavor text for a D&D 5e virtual tabletop.

Generate a SHORT biography (2-4 sentences) for the following creature. The biography should:
1. Describe what this creature IS (appearance, nature, behavior)
2. Be evocative and flavorful
3. NOT include mechanical stats or numbers
4. Sound like official D&D 5e monster manual descriptions

CREATURE NAME: {parsed_actor.name}

KEY FEATURES:
{summary}

Write ONLY the biography text (2-4 sentences), nothing else:"""

    try:
        # Use asyncio.to_thread since generate_content is synchronous
        response = await asyncio.to_thread(
            _get_gemini_client().GenerativeModel(model_name).generate_content,
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,  # Slightly creative
                max_output_tokens=200  # Keep it short
            )
        )

        biography = response.text.strip()
        logger.info(f"✓ Generated biography for {parsed_actor.name} ({len(biography)} chars)")
        return biography

    except Exception as e:
        logger.error(f"Failed to generate biography for {parsed_actor.name}: {e}")
        # Return a generic fallback
        return f"A {parsed_actor.size or ''} {parsed_actor.creature_type or 'creature'} of challenge rating {parsed_actor.challenge_rating}."
