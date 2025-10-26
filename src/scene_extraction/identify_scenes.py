"""Identify physical location scenes from chapter XML using Gemini."""

import logging
import json
import os
from typing import List
from dotenv import load_dotenv
import google.generativeai as genai

from .models import Scene, ChapterContext

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GeminiImageAPI")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Use gemini-2.0-flash-exp instead of gemini-2.5-pro for this structured extraction task
# because it's faster and cheaper while still providing reliable JSON parsing for scene identification
GEMINI_MODEL_NAME = "gemini-2.0-flash-exp"


def identify_scene_locations(xml_content: str, chapter_context: ChapterContext) -> List[Scene]:
    """
    Use Gemini to analyze XML and identify physical location scenes.

    Args:
        xml_content: Full chapter XML content
        chapter_context: Environmental context for the chapter

    Returns:
        List of Scene objects (empty list if no scenes found)

    Raises:
        ValueError: If Gemini response is invalid
        RuntimeError: If Gemini API call fails
    """
    logger.info("Identifying scene locations with Gemini")

    context_summary = f"""
Environment: {chapter_context.environment_type}
Weather: {chapter_context.weather or 'N/A'}
Atmosphere: {chapter_context.atmosphere or 'N/A'}
Lighting: {chapter_context.lighting or 'N/A'}
Terrain: {chapter_context.terrain or 'N/A'}
"""

    prompt = f"""
Analyze this D&D module chapter XML and identify physical location scenes (rooms, areas, outdoor locations).

Chapter Environmental Context:
{context_summary}

For each physical location, extract:
- section_path: Full section hierarchy (e.g., "Chapter 2 → The Cragmaw Hideout → Area 1")
- name: Short descriptive name for the location
- description: Physical environment description ONLY (no NPCs, no monsters, no plot - just the physical space)
- location_type: Specific location type - must be one of: "underground" (caves, dungeons, tunnels), "outdoor" (forest, plains, mountains), "interior" (buildings, structures), "underwater", or "other"
- xml_section_id: The 'id' attribute from the XML section element (or null if not present)

Return ONLY a JSON array of scene objects. If no physical locations found, return [].

EXCLUDE from descriptions:
- Named NPCs or monsters
- Combat encounters
- Plot events
- Treasure or items

INCLUDE in descriptions:
- Physical layout and dimensions
- Architectural features
- Natural features (if outdoor)
- Lighting and atmosphere
- Furniture and fixtures
- Environmental hazards (physical only, like pits or traps)

XML:
{xml_content}

Return ONLY valid JSON array, no markdown formatting:
"""

    try:
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        response = model.generate_content(prompt)

        logger.debug(f"Gemini response: {response.text}")

        # Parse JSON response
        response_text = response.text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()

        try:
            scenes_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {response_text}")
            raise ValueError(f"Failed to parse Gemini response as JSON: {e}") from e

        # Create Scene objects (Pydantic will validate)
        scenes = [Scene(**scene_data) for scene_data in scenes_data]
        logger.info(f"Identified {len(scenes)} scene locations")

        return scenes

    except Exception as e:
        logger.error(f"Failed to identify scene locations: {e}")
        raise RuntimeError(f"Failed to identify scene locations: {e}") from e
