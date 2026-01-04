"""Chat router for Module Assistant API."""

from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest, ChatResponse
from app.services.command_parser import CommandParser, CommandType
from app.services.gemini_service import GeminiService
from app.tools import registry

router = APIRouter(prefix="/api", tags=["chat"])

# Initialize services
command_parser = CommandParser()
gemini_service = GeminiService()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint.

    Handles both regular chat messages and slash commands.
    """
    try:
        # Parse command
        cmd = command_parser.parse(request.message)

        # Handle different command types
        if cmd.type == CommandType.HELP:
            return _handle_help_command()

        elif cmd.type == CommandType.GENERATE_SCENE:
            return await _handle_generate_scene(cmd.args, request.context)

        elif cmd.type == CommandType.LIST_SCENES:
            return _handle_list_scenes(cmd.args, request.context)

        elif cmd.type == CommandType.LIST_ACTORS:
            return _handle_list_actors(request.context)

        elif cmd.type == CommandType.UNKNOWN:
            return ChatResponse(
                message=f"Unknown command: {cmd.original_message}. Type /help for available commands.",
                type="error"
            )

        else:  # Regular chat
            # Convert conversation history to dict format
            history_dicts = [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in request.conversation_history
            ]

            # Get all available tool schemas
            tool_schemas = registry.get_schemas()
            print(f"[DEBUG] Available tools: {[t.name for t in tool_schemas]}")

            # Call Gemini with function calling enabled
            response = await gemini_service.generate_with_tools(
                message=request.message,
                conversation_history=history_dicts,
                tools=tool_schemas
            )
            print(f"[DEBUG] Gemini response type: {response.get('type')}")
            print(f"[DEBUG] Gemini response: {response}")

            # Check if Gemini wants to call a tool
            if response.get("type") == "tool_call":
                tool_name = response["tool_call"]["name"]
                tool_params = response["tool_call"]["parameters"]

                # Execute the tool
                tool_response = await registry.execute_tool(tool_name, **tool_params)

                # Return tool response
                return ChatResponse(
                    message=tool_response.message,
                    type=tool_response.type,
                    data=tool_response.data
                )

            # No tool call - return text response
            return ChatResponse(
                message=response["text"],
                type="text",
                data=None
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _handle_help_command() -> ChatResponse:
    """Handle /help command."""
    help_text = """**Available Commands:**

- `/generate-scene [description]` - Generate a new scene with AI
- `/list-scenes [chapter]` - List all scenes (optionally filtered by chapter)
- `/list-actors` - List all actors and NPCs
- `/help` - Show this help message

You can also chat naturally without using commands!"""

    return ChatResponse(message=help_text, type="text")


async def _handle_generate_scene(args: str, context: dict) -> ChatResponse:
    """Handle /generate-scene command."""
    if not args:
        return ChatResponse(
            message="Please provide a scene description. Example: `/generate-scene dark cave entrance`",
            type="error"
        )

    # Generate scene description
    description = gemini_service.generate_scene_description(args)

    # Generate scene image using the image generator tool
    image_tool = registry.tools.get("generate_images")
    if image_tool:
        # Create an enhanced prompt for D&D scene artwork
        image_prompt = f"Fantasy D&D scene illustration: {description}. Dramatic lighting, detailed environment, no text or words in the image."
        try:
            image_response = await image_tool.execute(prompt=image_prompt, count=1)

            if image_response.type == "image" and image_response.data:
                image_urls = image_response.data.get("image_urls", [])
                response_message = f"**Generated Scene**\n\n{description}"

                return ChatResponse(
                    message=response_message,
                    type="image",
                    data={
                        "description": description,
                        "request": args,
                        "image_urls": image_urls,
                        "prompt": image_prompt
                    }
                )
            else:
                # Log the failed response for debugging
                print(f"[DEBUG] Image generation returned non-image response: {image_response}")
        except Exception as e:
            print(f"[DEBUG] Image generation exception: {e}")

    # Fallback if image generation fails
    response_message = f"**Generated Scene**\n\n{description}\n\n_Image generation failed, showing description only._"

    return ChatResponse(
        message=response_message,
        type="scene",
        data={"description": description, "request": args}
    )


def _handle_list_scenes(chapter_filter: str, context: dict) -> ChatResponse:
    """Handle /list-scenes command."""
    # TODO: Integrate with actual scene database
    # For now, return placeholder

    message = f"**Scenes in {chapter_filter or 'All Chapters'}**\n\n"
    message += "1. Cragmaw Hideout Entrance\n"
    message += "2. Twin Pools Cave\n"
    message += "3. Goblin Den\n"
    message += "4. Klarg's Cave\n\n"
    message += "_Note: Scene database integration coming soon!_"

    return ChatResponse(message=message, type="list")


def _handle_list_actors(context: dict) -> ChatResponse:
    """Handle /list-actors command."""
    # TODO: Integrate with actual actor database
    # For now, return placeholder

    message = "**Available Actors**\n\n"
    message += "1. Klarg (Bugbear)\n"
    message += "2. Sildar Hallwinter (Human Fighter)\n"
    message += "3. Goblin\n"
    message += "4. Wolf\n\n"
    message += "_Note: Actor database integration coming soon!_"

    return ChatResponse(message=message, type="list")
