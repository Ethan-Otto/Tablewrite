"""Batch actor creation tool - create multiple actors from natural language."""
import sys
import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from .base import BaseTool, ToolSchema, ToolResponse
from .actor_creator import (
    load_caches,
    generate_actor_description,
    generate_actor_image,
    _image_generation_enabled,
)

# Add src to path for imports (backend tools run from ui/backend)
_src_dir = Path(__file__).parent.parent.parent.parent.parent / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

# Import config module for automatic .env loading (side effect)
import config  # noqa: E402, F401

from util.gemini import GeminiAPI  # noqa: E402
from actor_pipeline.orchestrate import create_actor_from_description  # noqa: E402
from app.websocket import push_actor, get_or_create_folder  # noqa: E402

logger = logging.getLogger(__name__)


async def parse_actor_requests(prompt: str) -> List[Dict[str, Any]]:
    """
    Parse natural language prompt into structured actor requests.

    Args:
        prompt: Natural language like "Create a goblin, two bugbears, and a hobgoblin"

    Returns:
        List of dicts with 'description' and 'count' keys
    """
    def _parse():
        api = GeminiAPI(model_name="gemini-2.0-flash")
        system_prompt = """You are a D&D creature parser. Extract creatures/actors from the user's request.

Return a JSON array where each element has:
- "description": brief creature description (e.g., "a goblin scout", "a bugbear brute")
- "count": number of this creature type requested (default 1)

Examples:
- "Create a goblin" -> [{"description": "a goblin", "count": 1}]
- "Make two bugbears and an orc" -> [{"description": "a bugbear", "count": 2}, {"description": "an orc", "count": 1}]
- "5 kobolds" -> [{"description": "a kobold", "count": 5}]

If no creatures are mentioned, return [].
Return ONLY the JSON array, no other text."""

        response = api.generate_content(f"{system_prompt}\n\nUser request: {prompt}")
        return response.text.strip()

    result_text = await asyncio.to_thread(_parse)

    # Parse JSON response
    try:
        # Handle potential markdown code blocks
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result = json.loads(result_text)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse actor requests: {result_text}")
        return []


async def expand_duplicates(requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Expand requests with count > 1 into individual actors with unique names.

    Args:
        requests: List of {"description": str, "count": int}

    Returns:
        Expanded list where each entry has count=1 and unique description
    """
    expanded = []

    for req in requests:
        count = req.get("count", 1)
        description = req.get("description", "")

        if count == 1:
            expanded.append({"description": description, "count": 1})
        else:
            # Generate unique names for duplicates
            unique_names = await _generate_unique_names(description, count)
            for name in unique_names:
                expanded.append({"description": name, "count": 1})

    return expanded


async def _generate_unique_names(base_description: str, count: int) -> List[str]:
    """Generate unique variant names for duplicate creatures."""
    def _generate():
        api = GeminiAPI(model_name="gemini-2.0-flash")
        prompt = f"""Generate {count} unique, distinct names/variants for this D&D creature:
"{base_description}"

Make each name descriptive and different (e.g., "Bugbear Brute", "Bugbear Tracker", "Bugbear Shaman").
Return ONLY a JSON array of strings, no other text.

Example: ["Bugbear Brute", "Bugbear Tracker"]"""

        response = api.generate_content(prompt)
        return response.text.strip()

    result_text = await asyncio.to_thread(_generate)

    try:
        # Handle potential markdown code blocks
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        names = json.loads(result_text)
        if isinstance(names, list) and len(names) >= count:
            return names[:count]
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse unique names: {result_text}")

    # Fallback: append numbers
    return [f"{base_description} #{i+1}" for i in range(count)]


async def create_single_actor(
    description: str,
    spell_cache,
    icon_cache,
    folder_id: str = None
) -> Dict[str, Any]:
    """
    Create a single actor with shared caches.

    Args:
        description: Natural language description of the actor
        spell_cache: Pre-loaded SpellCache instance
        icon_cache: Pre-loaded IconCache instance
        folder_id: Optional folder ID to place actor in

    Returns:
        Dict with 'uuid', 'name', 'cr', and optionally 'image_url'
    """
    # Generate image if enabled
    image_url = None
    foundry_image_path = None
    if _image_generation_enabled:
        try:
            visual_desc = await generate_actor_description(description)
            image_url, foundry_image_path = await generate_actor_image(visual_desc)
        except Exception as e:
            logger.warning(f"Image generation failed (non-fatal): {e}")

    # Actor upload function
    async def ws_actor_upload(actor_data: dict, spell_uuids: list) -> str:
        if folder_id:
            actor_data["folder"] = folder_id
        if foundry_image_path:
            actor_data["img"] = foundry_image_path

        result = await push_actor({
            "actor": actor_data,
            "spell_uuids": spell_uuids
        }, timeout=30.0)

        if result.success:
            return result.uuid
        raise RuntimeError(f"Failed to create actor: {result.error}")

    # Create the actor
    result = await create_actor_from_description(
        description=description,
        spell_cache=spell_cache,
        icon_cache=icon_cache,
        actor_upload_fn=ws_actor_upload,
    )

    return {
        "uuid": result.foundry_uuid,
        "name": result.stat_block.name if result.stat_block else "Unknown",
        "cr": result.challenge_rating,
        "image_url": image_url
    }


class BatchActorCreatorTool(BaseTool):
    """Tool for creating multiple D&D actors from a single prompt."""

    @property
    def name(self) -> str:
        return "create_actors"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="create_actors",
            description=(
                "Create multiple D&D actors/creatures from a natural language description. "
                "Use when user asks to create several actors at once, like 'create a goblin, "
                "two bugbears, and a hobgoblin captain'."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Natural language description of actors to create"
                    }
                },
                "required": ["prompt"]
            }
        )

    async def execute(self, prompt: str) -> ToolResponse:
        """Execute batch actor creation."""
        try:
            # Step 1: Parse prompt into actor requests
            requests = await parse_actor_requests(prompt)
            if not requests:
                return ToolResponse(
                    type="text",
                    message="I couldn't identify any actors to create. Could you be more specific?",
                    data=None
                )

            # Step 2: Expand duplicates into unique actors
            expanded = await expand_duplicates(requests)
            total = len(expanded)

            # Step 3: Load caches once (shared across all actors)
            spell_cache, icon_cache = await load_caches()

            # Step 4: Get or create Tablewrite folder
            folder_id = None
            try:
                folder_result = await get_or_create_folder("Tablewrite", "Actor")
                if folder_result.success:
                    folder_id = folder_result.folder_id
            except Exception as e:
                logger.warning(f"Failed to get Tablewrite folder: {e}")

            # Step 5: Create actors in parallel
            tasks = [
                create_single_actor(
                    req["description"],
                    spell_cache,
                    icon_cache,
                    folder_id
                )
                for req in expanded
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Step 6: Collect successes and failures
            successes = []
            failures = []
            image_urls = []

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failures.append({
                        "description": expanded[i]["description"],
                        "error": str(result)
                    })
                else:
                    successes.append(result)
                    if result.get("image_url"):
                        image_urls.append(result["image_url"])

            # Step 7: Build response message
            if successes:
                lines = [f"Created {len(successes)} of {total} actors:"]
                for s in successes:
                    link = f"@UUID[{s['uuid']}]{{{s['name']}}}"
                    lines.append(f"- {link} (CR {s['cr']})")

                if failures:
                    lines.append("\nFailed:")
                    for f in failures:
                        lines.append(f"- {f['description']} - {f['error']}")

                message = "\n".join(lines)
            else:
                message = f"Failed to create any actors:\n" + "\n".join(
                    f"- {f['description']} - {f['error']}" for f in failures
                )

            # Return with images if available
            response_data = {
                "created": [{"uuid": s["uuid"], "name": s["name"], "cr": s["cr"]} for s in successes],
                "failed": failures
            }

            if image_urls:
                return ToolResponse(
                    type="image",
                    message=message,
                    data={**response_data, "image_urls": image_urls}
                )

            return ToolResponse(
                type="text",
                message=message,
                data=response_data
            )

        except Exception as e:
            logger.error(f"Batch actor creation failed: {e}")
            return ToolResponse(
                type="error",
                message=f"Failed to create actors: {str(e)}",
                data=None
            )
