"""Actor creation tool using WebSocket-only (no relay server)."""
import sys
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from .base import BaseTool, ToolSchema, ToolResponse

# Add project paths for module imports
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))  # For "from src.xxx" imports
sys.path.insert(0, str(project_root / "src"))  # For "from xxx" imports

# Load environment variables from project root before imports
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Import actor creation pipeline components (without FoundryClient)
from actors.generate_actor_file import generate_actor_description  # noqa: E402
from actors.generate_actor_biography import generate_actor_biography  # noqa: E402
from actors.statblock_parser import parse_raw_text_to_statblock  # noqa: E402
from foundry.actors.parser import parse_stat_block_parallel  # noqa: E402
from foundry.actors.converter import convert_to_foundry  # noqa: E402
from foundry.actors.spell_cache import SpellCache  # noqa: E402
from foundry.icon_cache import IconCache  # noqa: E402
from app.websocket import push_actor  # noqa: E402

logger = logging.getLogger(__name__)


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
        """Execute actor creation via WebSocket (no relay server)."""
        try:
            model_name = "gemini-2.0-flash"

            # Step 1: Generate raw stat block text
            logger.info("Step 1/5: Generating stat block text with Gemini...")
            raw_text = await generate_actor_description(
                description=description,
                challenge_rating=challenge_rating,
                model_name=model_name
            )

            # Step 2: Parse to StatBlock model
            logger.info("Step 2/5: Parsing stat block to StatBlock model...")
            stat_block = await parse_raw_text_to_statblock(raw_text, model_name=model_name)

            # Step 3: Parse to detailed ParsedActorData
            logger.info("Step 3/5: Parsing to detailed ParsedActorData...")
            parsed_actor = await parse_stat_block_parallel(stat_block)

            # Step 4: Generate biography
            logger.info("Step 4/5: Generating actor biography...")
            biography = await generate_actor_biography(parsed_actor, model_name=model_name)
            parsed_actor = parsed_actor.model_copy(update={"biography": biography})

            # Step 5: Convert to FoundryVTT format
            logger.info("Step 5/5: Converting to FoundryVTT format...")
            spell_cache = SpellCache()
            spell_cache.load()

            icon_cache = IconCache()
            icon_cache.load()

            actor_json, spell_uuids = await convert_to_foundry(
                parsed_actor,
                spell_cache=spell_cache,
                icon_cache=icon_cache,
                use_ai_icons=True
            )

            # Get CR from parsed actor data
            actor_cr = parsed_actor.challenge_rating
            actor_name = parsed_actor.name

            # Push FULL actor data to connected Foundry clients via WebSocket
            # The Foundry module will call Actor.create(data)
            await push_actor({
                "actor": actor_json,
                "spell_uuids": spell_uuids,
                "name": actor_name,
                "cr": actor_cr
            })

            logger.info(f"Pushed actor '{actor_name}' (CR {actor_cr}) to Foundry via WebSocket")

            # Format text response
            cr_text = f"CR {actor_cr}"
            message = (
                f"Created **{actor_name}** ({cr_text})!\n\n"
                f"The actor data has been pushed to FoundryVTT via WebSocket.\n"
                f"Check your FoundryVTT Actors tab to find the new actor."
            )

            return ToolResponse(
                type="text",
                message=message,
                data=None
            )

        except Exception as e:
            logger.error(f"Actor creation failed: {e}")
            return ToolResponse(
                type="error",
                message=f"Failed to create actor: {str(e)}",
                data=None
            )
