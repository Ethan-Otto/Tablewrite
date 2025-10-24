"""Extract environmental context from chapter XML using Gemini."""

import logging
import json
import os
from dotenv import load_dotenv
import google.generativeai as genai

from .models import ChapterContext

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GeminiImageAPI")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

GEMINI_MODEL_NAME = "gemini-2.0-flash-exp"


def extract_chapter_context(xml_content: str) -> ChapterContext:
    """
    Use Gemini to analyze chapter XML and extract environmental context.

    Args:
        xml_content: Full chapter XML content

    Returns:
        ChapterContext with environment type, weather, atmosphere, etc.

    Raises:
        ValueError: If Gemini response is invalid or unparseable
        RuntimeError: If Gemini API call fails
    """
    logger.info("Extracting chapter environmental context with Gemini")

    prompt = f"""
Analyze this D&D module chapter XML and extract environmental context.

Return ONLY a JSON object with these fields (use null for unknown):
- environment_type: (e.g., "underground", "forest", "urban", "coastal", "dungeon")
- weather: (e.g., "rainy", "foggy", "clear", "stormy") or null if indoors/underground
- atmosphere: (e.g., "oppressive", "peaceful", "tense", "mysterious")
- lighting: (e.g., "dim torchlight", "bright sunlight", "darkness", "well-lit")
- terrain: (e.g., "rocky caverns", "dense forest", "cobblestone streets")
- additional_notes: Any other relevant environmental details

Focus on the PHYSICAL ENVIRONMENT only. Ignore NPCs, monsters, and plot.

XML:
{xml_content}

Return ONLY valid JSON, no markdown formatting:
"""

    try:
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        response = model.generate_content(prompt)

        logger.debug(f"Gemini response: {response.text}")

        # Parse JSON response
        response_text = response.text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            # Remove opening ```json or ``` and closing ```
            lines = response_text.split("\n")
            # Remove first line (``` or ```json)
            lines = lines[1:]
            # Remove last line (```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            # If first line is "json", remove it
            if lines and lines[0].strip() == "json":
                lines = lines[1:]
            response_text = "\n".join(lines).strip()

        try:
            context_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {response_text}")
            raise ValueError(f"Failed to parse Gemini response as JSON: {e}") from e

        # Create ChapterContext (Pydantic will validate)
        context = ChapterContext(**context_data)
        logger.info(f"Extracted context: {context.environment_type} environment")

        return context

    except ValueError:
        # Re-raise ValueError without wrapping
        raise
    except Exception as e:
        logger.error(f"Failed to extract chapter context: {e}")
        raise RuntimeError(f"Failed to extract chapter context: {e}") from e
