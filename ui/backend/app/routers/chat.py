"""Chat router for Module Assistant API."""

from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest, ChatResponse
from app.services.command_parser import CommandParser, CommandType
from app.services.gemini_service import GeminiService
from app.tools import registry
from app.tools.actor_creator import set_request_context

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
            return await _handle_help_command()

        elif cmd.type == CommandType.GENERATE_SCENE:
            return await _handle_generate_scene(cmd.args, request.context)

        elif cmd.type == CommandType.LIST_SCENES:
            return await _handle_list_scenes()

        elif cmd.type == CommandType.LIST_ACTORS:
            return await _handle_list_actors()

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

            # Check if this is a rules question
            if gemini_service.is_rules_question(request.message):
                print("[DEBUG] Detected rules question, using thinking mode")
                print(f"[DEBUG] Rules question context: {request.context.get('gameSystem', {})}")
                response_text = gemini_service.generate_with_thinking(
                    message=request.message,
                    conversation_history=history_dicts,
                    context=request.context
                )
                return ChatResponse(
                    message=response_text,
                    type="text",
                    data={"thinking_mode": True}
                )

            # Set request context for tool execution
            set_request_context(request.context)

            # Get all available tool schemas
            tool_schemas = registry.get_schemas()
            print(f"[DEBUG] Available tools: {[t.name for t in tool_schemas]}")

            # Call Gemini with function calling enabled
            response = await gemini_service.generate_with_tools(
                message=request.message,
                conversation_history=history_dicts,
                tools=tool_schemas,
                context=request.context
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


async def _handle_help_command() -> ChatResponse:
    """Handle /help command by calling the help tool."""
    tool_response = await registry.execute_tool("help")

    # Add slash command info to the tool response
    help_text = tool_response.message + "\n\n**Slash Commands:**\n"
    help_text += "- `/help` - Show this help\n"
    help_text += "- `/list-actors` - List all actors\n"
    help_text += "- `/list-scenes` - List all scenes\n"
    help_text += "- `/generate-scene [description]` - Generate scene artwork\n"
    help_text += "\nYou can also chat naturally without commands!"

    return ChatResponse(
        message=help_text,
        type=tool_response.type,
        data=tool_response.data
    )


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


async def _handle_list_scenes() -> ChatResponse:
    """Handle /list-scenes command by calling the list_scenes tool."""
    tool_response = await registry.execute_tool("list_scenes")
    return ChatResponse(
        message=tool_response.message,
        type=tool_response.type,
        data=tool_response.data
    )


async def _handle_list_actors() -> ChatResponse:
    """Handle /list-actors command by calling the list_actors tool."""
    tool_response = await registry.execute_tool("list_actors")
    return ChatResponse(
        message=tool_response.message,
        type=tool_response.type,
        data=tool_response.data
    )
