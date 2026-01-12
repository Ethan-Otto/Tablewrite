"""Chat router for Module Assistant API."""

import re
from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest, ChatResponse
from app.services.command_parser import CommandParser, CommandType
from app.services.gemini_service import GeminiService
from app.tools import registry
from app.tools.actor_creator import set_request_context
from app.websocket import fetch_actor, fetch_journal

router = APIRouter(prefix="/api", tags=["chat"])

# Regex to match mentions: @[Name](Type.uuid)
MENTION_PATTERN = re.compile(r'@\[([^\]]+)\]\(([^)]+)\)')


async def parse_and_resolve_mentions(message: str) -> tuple[str, list[dict]]:
    """
    Parse mentions in message and resolve them to entity context.

    Args:
        message: Raw message with mentions like @[Goblin](Actor.abc123)

    Returns:
        tuple: (cleaned_message, list of resolved entity contexts)
    """
    mentions = MENTION_PATTERN.findall(message)
    if not mentions:
        return message, []

    resolved_entities = []
    cleaned_message = message

    for name, uuid_str in mentions:
        # Parse the type from UUID (format: Type.id or just id)
        if '.' in uuid_str:
            entity_type = uuid_str.split('.')[0]
            entity_id = uuid_str.split('.', 1)[1]
        else:
            entity_type = "Unknown"
            entity_id = uuid_str

        entity_context = {
            "name": name,
            "type": entity_type,
            "uuid": uuid_str,
            "details": None
        }

        # Try to fetch entity details based on type
        try:
            if entity_type == "Actor":
                result = await fetch_actor(entity_id)
                if result.success and result.entity:
                    entity_context["details"] = _extract_actor_summary(result.entity)
            elif entity_type == "JournalEntry":
                result = await fetch_journal(entity_id)
                if result.success and result.entity:
                    entity_context["details"] = _extract_journal_summary(result.entity)
            # Items and Scenes could be added similarly
        except Exception as e:
            print(f"[DEBUG] Failed to fetch entity {uuid_str}: {e}")

        resolved_entities.append(entity_context)

        # Replace mention with cleaner reference in message
        original_mention = f"@[{name}]({uuid_str})"
        clean_ref = f"[{entity_type}: {name}]"
        cleaned_message = cleaned_message.replace(original_mention, clean_ref)

    return cleaned_message, resolved_entities


def _extract_actor_summary(actor: dict) -> str:
    """Extract a summary of actor details for context."""
    name = actor.get("name", "Unknown")
    system = actor.get("system", {})

    parts = [f"Name: {name}"]

    # HP
    hp = system.get("attributes", {}).get("hp", {})
    if hp.get("max"):
        parts.append(f"HP: {hp.get('value', hp.get('max'))}/{hp.get('max')}")

    # AC
    ac = system.get("attributes", {}).get("ac", {})
    if ac.get("value"):
        parts.append(f"AC: {ac.get('value')}")

    # CR
    cr = system.get("details", {}).get("cr")
    if cr is not None:
        parts.append(f"CR: {cr}")

    # Type
    creature_type = system.get("details", {}).get("type", {}).get("value")
    if creature_type:
        parts.append(f"Type: {creature_type}")

    return "; ".join(parts)


def _extract_journal_summary(journal: dict) -> str:
    """Extract a summary of journal details for context."""
    name = journal.get("name", "Unknown")
    pages = journal.get("pages", [])

    parts = [f"Name: {name}", f"Pages: {len(pages)}"]

    if pages:
        page_names = [p.get("name", "Untitled") for p in pages[:5]]
        parts.append(f"Page titles: {', '.join(page_names)}")

    return "; ".join(parts)

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
            # Parse and resolve any @mentions in the message
            cleaned_message, resolved_entities = await parse_and_resolve_mentions(request.message)

            # If we have resolved entities, add their context
            enhanced_context = dict(request.context) if request.context else {}
            if resolved_entities:
                enhanced_context["mentioned_entities"] = resolved_entities
                print(f"[DEBUG] Resolved {len(resolved_entities)} mentions: {[e['name'] for e in resolved_entities]}")

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
            if gemini_service.is_rules_question(cleaned_message):
                print("[DEBUG] Detected rules question, using thinking mode")
                print(f"[DEBUG] Rules question context: {enhanced_context.get('gameSystem', {})}")
                response_text = gemini_service.generate_with_thinking(
                    message=cleaned_message,
                    conversation_history=history_dicts,
                    context=enhanced_context
                )
                return ChatResponse(
                    message=response_text,
                    type="text",
                    data={"thinking_mode": True}
                )

            # Set request context for tool execution
            set_request_context(enhanced_context)

            # Get all available tool schemas
            tool_schemas = registry.get_schemas()
            print(f"[DEBUG] Available tools: {[t.name for t in tool_schemas]}")

            # Call Gemini with function calling enabled
            response = await gemini_service.generate_with_tools(
                message=cleaned_message,
                conversation_history=history_dicts,
                tools=tool_schemas,
                context=enhanced_context
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
