"""Actor creation tool - thin wrapper around shared actor creation logic."""
import sys
import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from .base import BaseTool, ToolSchema, ToolResponse
from .image_styles import get_actor_style

# Add src to path for imports (backend tools run from ui/backend)
_src_dir = Path(__file__).parent.parent.parent.parent.parent / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

# Import config module for automatic .env loading (side effect)
import config  # noqa: E402, F401

from actor_pipeline.orchestrate import create_actor_from_description  # noqa: E402
from caches import SpellCache, IconCache  # noqa: E402
from app.websocket import push_actor, list_files, list_compendium_items, upload_file, get_or_create_folder  # noqa: E402
from util.gemini import GeminiAPI  # noqa: E402
from app.config import settings  # noqa: E402

logger = logging.getLogger(__name__)

# Flag to disable image generation (for tests)
_image_generation_enabled = True

# Context settings from frontend (set per-request)
_request_context: dict = {}


def set_request_context(context: dict):
    """Set the request context for the current request."""
    global _request_context
    _request_context = context or {}


def get_request_context() -> dict:
    """Get the current request context."""
    return _request_context


def set_image_generation_enabled(enabled: bool):
    """Enable or disable image generation for actor creation."""
    global _image_generation_enabled
    _image_generation_enabled = enabled


async def generate_actor_description(description: str) -> str:
    """
    Use Gemini to generate a visual description of the actor for image generation.

    Args:
        description: The user's actor description

    Returns:
        A detailed visual description suitable for image generation
    """
    def _generate():
        api = GeminiAPI(model_name="gemini-2.0-flash")
        prompt = f"""Based on this D&D creature/character description, generate a concise visual description
suitable for AI image generation. Focus on physical appearance, clothing/armor, weapons,
and distinctive visual features. Keep it to 2-3 sentences.

Description: {description}

Visual description for image generation:"""
        response = api.generate_content(prompt)
        return response.text.strip()

    return await asyncio.to_thread(_generate)


async def generate_actor_image(
    visual_description: str,
    upload_to_foundry: bool = True,
    style: str = "watercolor"
) -> tuple[Optional[str], Optional[str]]:
    """
    Generate an image of the actor using Imagen.

    Args:
        visual_description: Visual description of the actor
        upload_to_foundry: Whether to upload the image to Foundry
        style: Art style to use ("watercolor" or "oil")

    Returns:
        Tuple of (local_url, foundry_path):
        - local_url: URL path for serving via backend (e.g., "/api/images/actor_xxx.png")
        - foundry_path: Foundry-relative path for actor profile (e.g., "worlds/test/actor-portraits/actor_xxx.png")
    """
    import base64

    try:
        # Get style prompt based on setting
        style_prompt = get_actor_style(style)
        styled_prompt = f"{visual_description}, {style_prompt}"
        logger.info(f"[IMAGE PROMPT] style={style}, prompt={styled_prompt[:100]}...")

        # Generate image in thread pool to avoid blocking event loop
        def _generate_image():
            # Using Gemini for image generation (can switch back to imagen-4.0-fast-generate-001)
            api = GeminiAPI(model_name="gemini-2.5-flash-image")
            return api.client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=styled_prompt
            )

        response = await asyncio.to_thread(_generate_image)

        # Extract image from Gemini response
        image_data = None
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    image_data = part.inline_data.data
                    break

        if image_data:
            # Save image locally
            output_dir = settings.IMAGE_OUTPUT_DIR
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = uuid.uuid4().hex[:8]
            filename = f"actor_{timestamp}_{unique_id}.png"
            filepath = output_dir / filename

            with open(filepath, 'wb') as f:
                f.write(image_data)

            logger.info(f"Generated actor image: {filename}")
            local_url = f"/api/images/{filename}"

            # Upload to Foundry if requested
            foundry_path = None
            if upload_to_foundry:
                try:
                    # Base64 encode the image data
                    b64_content = base64.b64encode(image_data).decode('utf-8')

                    # Upload to Foundry's actor-portraits folder
                    upload_result = await upload_file(
                        filename=filename,
                        content=b64_content,
                        destination="actor-portraits"
                    )

                    if upload_result.success:
                        foundry_path = upload_result.path
                        logger.info(f"Uploaded actor image to Foundry: {foundry_path}")
                    else:
                        logger.warning(f"Failed to upload actor image to Foundry: {upload_result.error}")

                except Exception as e:
                    logger.warning(f"Foundry upload failed (non-fatal): {e}")

            return local_url, foundry_path

        return None, None

    except Exception as e:
        logger.warning(f"Actor image generation failed: {e}")
        return None, None


async def list_compendium_items_with_retry(
    document_type: str = "Item",
    sub_type: str = None,
    max_retries: int = 3,
    initial_delay: float = 1.0
):
    """
    Fetch compendium items with retry logic for WebSocket reconnection.

    After a hot reload, the Foundry WebSocket may not be reconnected yet.
    This retries with exponential backoff to wait for the connection.
    """
    delay = initial_delay
    last_result = None

    for attempt in range(max_retries):
        result = await list_compendium_items(
            document_type=document_type,
            sub_type=sub_type,
            timeout=15.0
        )
        last_result = result

        if result.success:
            return result

        # Check if it's a connection issue (worth retrying)
        logger.warning(f"Attempt {attempt + 1}/{max_retries}: error={result.error}")
        if result.error and "No Foundry client connected" in result.error:
            if attempt < max_retries - 1:
                logger.warning(f"WebSocket not connected, waiting {delay}s before retry {attempt + 2}/{max_retries}...")
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff
            continue

        # Non-connection error, don't retry
        break

    logger.warning(f"All {max_retries} attempts failed, returning last result")
    return last_result


async def list_files_with_retry(
    path: str,
    source: str = "public",
    recursive: bool = False,
    extensions: list = None,
    max_retries: int = 3,
    initial_delay: float = 1.0
):
    """
    List files with retry logic for WebSocket reconnection.
    """
    delay = initial_delay
    last_result = None

    for attempt in range(max_retries):
        result = await list_files(
            path=path,
            source=source,
            recursive=recursive,
            extensions=extensions,
            timeout=15.0
        )
        last_result = result

        if result.success:
            return result

        # Check if it's a connection issue (worth retrying)
        if result.error and "No Foundry client connected" in result.error:
            if attempt < max_retries - 1:
                logger.info(f"WebSocket not connected for files, waiting {delay}s before retry {attempt + 2}/{max_retries}...")
                await asyncio.sleep(delay)
                delay *= 2
            continue

        break

    return last_result


async def load_caches() -> tuple[SpellCache, IconCache]:
    """
    Load SpellCache and IconCache via WebSocket.

    Returns:
        Tuple of (SpellCache, IconCache)

    Raises:
        RuntimeError: If cache loading fails
    """
    # HARD FAIL: SpellCache MUST load successfully
    spell_cache = SpellCache()
    logger.info("Fetching spells from compendium via WebSocket (with retry)...")
    spells_result = await list_compendium_items_with_retry(
        document_type="Item",
        sub_type="spell",
        max_retries=3,
        initial_delay=1.0
    )

    if not spells_result.success:
        error_msg = f"❌ SpellCache FAILED to load: {spells_result.error}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    if not spells_result.results or len(spells_result.results) == 0:
        error_msg = "❌ SpellCache FAILED: No spells returned from compendium"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # Convert SearchResultItem objects to dicts for load_from_data
    spell_dicts = [
        {
            "name": r.name,
            "uuid": r.uuid,
            "type": r.type,
            "img": r.img,
            "pack": r.pack,
        }
        for r in spells_result.results
    ]
    spell_cache.load_from_data(spell_dicts)
    logger.info(f"✓ SpellCache loaded with {spell_cache.spell_count} spells")

    # Verify critical spells exist
    test_uuid = spell_cache.get_spell_uuid("Fire Bolt")
    if not test_uuid:
        error_msg = "❌ SpellCache FAILED: 'Fire Bolt' not found - cache may be incomplete"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    logger.info(f"✓ Test lookup 'Fire Bolt' -> {test_uuid}")

    # HARD FAIL: IconCache MUST load successfully
    icon_cache = IconCache()
    logger.info("Fetching icons via WebSocket (with retry)...")
    files_result = await list_files_with_retry(
        path="icons",
        source="public",
        recursive=True,
        extensions=[".webp", ".png", ".jpg", ".svg"],
        max_retries=3,
        initial_delay=1.0
    )

    if not files_result.success:
        error_msg = f"❌ IconCache FAILED to load: {files_result.error}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    icon_cache.load_from_data(files_result.files or [])
    logger.info(f"✓ IconCache loaded with {icon_cache.icon_count} icons")

    return spell_cache, icon_cache


class ActorCreatorTool(BaseTool):
    """Tool for creating D&D actors from descriptions via WebSocket."""

    @property
    def name(self) -> str:
        return "create_actor"

    def get_schema(self) -> ToolSchema:
        """Return tool schema for Gemini function calling."""
        return ToolSchema(
            name="create_actor",
            description=(
                "Create a D&D actor/creature in FoundryVTT from a natural "
                "language description. Use when user asks to create, make, "
                "or generate an actor, monster, NPC, or creature."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Detailed description of the creature"
                    },
                    "challenge_rating": {
                        "type": "number",
                        "description": "Optional CR (0.125 to 30). Omit to infer from description.",
                        "minimum": 0.125,
                        "maximum": 30
                    }
                },
                "required": ["description"]
            }
        )

    async def execute(self, description: str, challenge_rating: float = None) -> ToolResponse:
        """Execute actor creation using shared logic from actor_pipeline.orchestrate."""
        try:
            # Pre-fetch spells and icons via WebSocket (avoids HTTP self-deadlock)
            # Uses retry logic to wait for WebSocket reconnection after hot reload
            spell_cache, icon_cache = await load_caches()

            # Get settings from request context
            context = get_request_context()
            settings = context.get('settings', {})
            art_enabled = settings.get('tokenArtEnabled', True)
            art_style = settings.get('artStyle', 'watercolor')

            # Generate actor image BEFORE actor creation (if enabled)
            # This allows us to set the profile image on the actor
            image_url = None
            foundry_image_path = None
            if _image_generation_enabled and art_enabled:
                logger.info(f"Generating actor image (style={art_style}) for: {description[:50]}...")
                try:
                    visual_desc = await generate_actor_description(description)
                    logger.info(f"Generated visual description: {visual_desc[:100]}...")
                    image_url, foundry_image_path = await generate_actor_image(
                        visual_desc,
                        style=art_style
                    )
                    if image_url:
                        logger.info(f"Actor image generated: {image_url}")
                    if foundry_image_path:
                        logger.info(f"Actor image uploaded to Foundry: {foundry_image_path}")
                except Exception as e:
                    logger.warning(f"Image generation failed (non-fatal): {e}")

            # WebSocket-based actor upload function with retry
            async def ws_actor_upload(actor_data: dict, spell_uuids: list) -> str:
                """Upload actor via WebSocket instead of relay."""
                # Ensure Tablewrite folder exists and set it on the actor
                try:
                    folder_result = await get_or_create_folder("Tablewrite", "Actor")
                    if folder_result.success and folder_result.folder_id:
                        actor_data["folder"] = folder_result.folder_id
                        logger.info(f"Set actor folder to Tablewrite: {folder_result.folder_id}")
                except Exception as e:
                    logger.warning(f"Failed to get/create Tablewrite folder: {e}")
                    # Continue without folder - actor will be created at root

                # Set profile image if available
                if foundry_image_path:
                    actor_data["img"] = foundry_image_path
                    logger.info(f"Setting actor profile image: {foundry_image_path}")

                # Log spell_uuids being sent
                logger.info(f"📤 Uploading actor '{actor_data.get('name')}' with {len(spell_uuids)} spell UUIDs")
                if spell_uuids:
                    for uuid in spell_uuids:
                        logger.info(f"   - {uuid}")
                else:
                    logger.warning("⚠️ No spell_uuids to send!")

                # Wrap in expected format: {actor: {...}, spell_uuids: [...]}
                delay = 1.0
                last_error = None

                for attempt in range(3):
                    result = await push_actor({
                        "actor": actor_data,
                        "spell_uuids": spell_uuids
                    }, timeout=30.0)

                    if result.success:
                        return result.uuid

                    last_error = result.error

                    # Check if it's a connection issue (worth retrying)
                    if result.error and "No Foundry client connected" in result.error:
                        if attempt < 2:
                            logger.info(f"WebSocket not connected for actor upload, waiting {delay}s before retry {attempt + 2}/3...")
                            await asyncio.sleep(delay)
                            delay *= 2
                        continue

                    # Non-connection error, don't retry
                    break

                raise RuntimeError(f"Failed to create actor: {last_error}")

            # Use shared actor creation logic (same as /api/actors/create)
            result = await create_actor_from_description(
                description=description,
                challenge_rating=challenge_rating,
                spell_cache=spell_cache,
                icon_cache=icon_cache,
                actor_upload_fn=ws_actor_upload,
            )

            actor_name = result.stat_block.name if result.stat_block else "Unknown"
            actor_cr = result.challenge_rating

            logger.info(f"Created actor '{actor_name}' (CR {actor_cr}) with UUID {result.foundry_uuid}")

            # Create FoundryVTT content link format
            actor_link = f"@UUID[{result.foundry_uuid}]{{{actor_name}}}"

            message = (
                f"Created **{actor_name}** (CR {actor_cr})!\n\n"
                f"UUID: `{result.foundry_uuid}`\n"
                f"**Link:** `{actor_link}`\n"
                f"The actor has been created in FoundryVTT."
            )

            # Return with image if available
            response_data = {"uuid": result.foundry_uuid, "name": actor_name, "cr": actor_cr}
            if image_url:
                return ToolResponse(
                    type="image",
                    message=message,
                    data={**response_data, "image_urls": [image_url]}
                )

            return ToolResponse(
                type="text",
                message=message,
                data=response_data
            )

        except Exception as e:
            logger.error(f"Actor creation failed: {e}")
            return ToolResponse(
                type="error",
                message=f"Failed to create actor: {str(e)}",
                data=None
            )
