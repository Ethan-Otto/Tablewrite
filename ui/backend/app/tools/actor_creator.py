"""Actor creation tool - thin wrapper around shared actor creation logic."""
import sys
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv
from .base import BaseTool, ToolSchema, ToolResponse

# Add project paths for module imports
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Load environment variables from project root before imports
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)

from actors.orchestrate import create_actor_from_description  # noqa: E402
from foundry.actors.spell_cache import SpellCache  # noqa: E402
from foundry.icon_cache import IconCache  # noqa: E402
from app.websocket import push_actor, list_files, list_compendium_items  # noqa: E402

logger = logging.getLogger(__name__)


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
        """Execute actor creation using shared logic from actors.orchestrate."""
        try:
            # Pre-fetch spells and icons via WebSocket (avoids HTTP self-deadlock)
            # Uses retry logic to wait for WebSocket reconnection after hot reload
            # HARD FAIL: SpellCache MUST load successfully - spells won't work without it
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

            # WebSocket-based actor upload function with retry
            async def ws_actor_upload(actor_data: dict, spell_uuids: list) -> str:
                """Upload actor via WebSocket instead of relay."""
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

            message = (
                f"Created **{actor_name}** (CR {actor_cr})!\n\n"
                f"UUID: `{result.foundry_uuid}`\n"
                f"The actor has been created in FoundryVTT."
            )

            return ToolResponse(
                type="text",
                message=message,
                data={"uuid": result.foundry_uuid, "name": actor_name, "cr": actor_cr}
            )

        except Exception as e:
            logger.error(f"Actor creation failed: {e}")
            return ToolResponse(
                type="error",
                message=f"Failed to create actor: {str(e)}",
                data=None
            )
