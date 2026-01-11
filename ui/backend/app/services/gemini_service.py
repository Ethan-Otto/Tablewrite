"""Gemini service for Module Assistant."""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add project src to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from util.gemini import GeminiAPI  # noqa: E402


class GeminiService:
    """Service for interacting with Gemini API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini service.

        Args:
            api_key: Optional API key (loads from .env if not provided)
        """
        self.api = GeminiAPI(model_name="gemini-2.0-flash", api_key=api_key)

    def _schema_to_gemini_tool(self, schema: 'ToolSchema') -> dict:
        """
        Convert ToolSchema to Gemini function calling format.

        Args:
            schema: Tool schema

        Returns:
            Gemini tool dict
        """
        return {
            "name": schema.name,
            "description": schema.description,
            "parameters": schema.parameters
        }

    async def generate_with_tools(
        self,
        message: str,
        conversation_history: List[Dict[str, str]],
        tools: List['ToolSchema'],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate response with tool calling support.

        Args:
            message: User message
            conversation_history: Previous messages
            tools: Available tool schemas
            context: Request context (game system, settings, etc.)

        Returns:
            Response dict with type and content
        """
        # Convert tool schemas to Gemini format
        gemini_functions = [self._schema_to_gemini_tool(t) for t in tools]

        # Build prompt with history and context
        prompt = self._build_chat_prompt(message, context or {}, conversation_history)

        # Generate with function calling
        if gemini_functions:
            response = self.api.client.models.generate_content(
                model=self.api.model_name,
                contents=prompt,
                config={
                    "tools": [{"function_declarations": gemini_functions}]
                }
            )
        else:
            # No tools available, regular generation
            response = self.api.generate_content(prompt)

        # Check if response contains function call
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate.content, 'parts') and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        return {
                            "type": "tool_call",
                            "tool_call": {
                                "name": part.function_call.name,
                                "parameters": dict(part.function_call.args)
                            },
                            "text": None
                        }

        # No tool call - return text response
        return {
            "type": "text",
            "text": response.text,
            "tool_call": None
        }

    def generate_chat_response(
        self,
        message: str,
        context: Dict[str, Any],
        conversation_history: Optional[list] = None
    ) -> str:
        """
        Generate a chat response using Gemini.

        Args:
            message: User message
            context: Conversation context
            conversation_history: List of previous messages

        Returns:
            Generated response text
        """
        # Build prompt with context and history
        prompt = self._build_chat_prompt(message, context, conversation_history)

        # Generate response
        response = self.api.generate_content(prompt)
        return response.text

    def is_rules_question(self, message: str) -> bool:
        """
        Detect if message is asking about D&D rules.

        Args:
            message: User message

        Returns:
            True if this appears to be a rules question
        """
        prompt = f"""Is this message a QUESTION asking about D&D 5e rules, mechanics, or how something works in the game?

Answer NO if the message is:
- A request to CREATE something (actor, scene, image, etc.)
- A command or action request
- A greeting or casual conversation

Answer YES only if the message is genuinely ASKING about rules/mechanics.

Message: "{message}"

Answer (YES or NO):"""

        try:
            response = self.api.generate_content(prompt)
            answer = response.text.strip().upper()
            return answer.startswith("YES")
        except Exception as e:
            print(f"[WARN] Rules detection failed: {e}, falling back to normal mode")
            return False

    def generate_with_thinking(
        self,
        message: str,
        conversation_history: Optional[list] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a response using extended thinking for thorough reasoning.

        Args:
            message: User message
            conversation_history: Previous messages
            context: Request context (game system, settings, etc.)

        Returns:
            Generated response with thorough reasoning
        """
        # Build prompt optimized for rules explanation
        game_system = (context or {}).get("gameSystem", {})
        system_title = game_system.get("title", "D&D 5e")
        rules_version = game_system.get("rulesVersion")

        # Determine which ruleset to use
        if rules_version == "modern":
            rules_info = "**Rules Version:** 2024 rules\nUse the 2024 Player's Handbook rules. Note key differences from 2014 rules where relevant."
        elif rules_version == "legacy":
            rules_info = "**Rules Version:** 2014 rules\nUse the 2014 Player's Handbook rules."
        elif rules_version:
            # Other systems might have their own version strings
            rules_info = f"**Rules Version:** {rules_version}"
        else:
            rules_info = ""

        prompt = f"""You are an expert {system_title} rules advisor. Answer the following question thoroughly and accurately.

{rules_info}

Include:
- The core rule mechanics for THIS specific rules version
- Relevant page references if known (PHB, DMG, etc.)
- Common edge cases or clarifications
- Practical examples when helpful

Think through this step by step before answering.

"""

        if conversation_history:
            prompt += "\n**Conversation History:**\n"
            for msg in conversation_history:
                role = msg.get("role", "").upper()
                content = msg.get("content", "")
                if role == "SYSTEM":
                    continue
                prompt += f"{role}: {content}\n"
            prompt += "\n"

        prompt += f"Question: {message}\n\nAnswer:"

        try:
            # Use thinking model configuration (gemini-2.5-flash supports thinking)
            response = self.api.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )

            return response.text
        except Exception as e:
            print(f"[WARN] Thinking mode failed: {e}, falling back to regular generation")
            # Fallback to regular chat response
            return self.generate_chat_response(message, {}, conversation_history)

    def generate_scene_description(self, scene_request: str) -> str:
        """
        Generate a detailed scene description.

        Args:
            scene_request: User's scene request

        Returns:
            Generated scene description
        """
        prompt = f"""You are a D&D Dungeon Master describing a scene.

User request: {scene_request}

Generate a vivid, atmospheric description of this scene/location. Include:
- Physical layout and dimensions
- Lighting and atmosphere
- Notable features and details
- Sounds, smells, or other sensory details

Keep it concise (2-3 sentences) and evocative."""

        response = self.api.generate_content(prompt)
        return response.text.strip()

    def _build_chat_prompt(
        self,
        message: str,
        context: Dict[str, Any],
        conversation_history: Optional[list] = None
    ) -> str:
        """Build prompt with context and conversation history."""
        prompt = """You are a helpful D&D Module Assistant. You help users work with D&D module content, generate scenes, and manage actors.

IMPORTANT: When the user asks you to generate, create, draw, or show an image, you MUST call the generate_images tool immediately. Do not ask clarifying questions about where to save the image or any other details - just call the tool with the user's description as the prompt. The tool handles all file management automatically.

Available commands:
- /generate-scene [description] - Generate a new scene
- /list-scenes [chapter] - List scenes in a chapter
- /list-actors - List all actors/NPCs
- /help - Show help

"""

        # Add game system context
        game_system = context.get("gameSystem", {})
        print(f"[DEBUG] Game system context: {game_system}")
        if game_system:
            system_id = game_system.get("id", "unknown")
            system_title = game_system.get("title", "Unknown System")
            rules_version = game_system.get("rulesVersion")

            prompt += f"\n**Game System:** {system_title} (system id: {system_id})"

            # Add rules version context
            if rules_version:
                if system_id == "dnd5e":
                    if rules_version == "legacy":
                        prompt += " - Using 2014 (Legacy) Rules"
                    elif rules_version == "modern":
                        prompt += " - Using 2024 Rules"
                else:
                    # Pass through any rules version for other systems
                    prompt += f" - Rules: {rules_version}"

            prompt += "\nTailor all content, rules references, and mechanics to this specific game system and rules version.\n\n"

        if context.get("module"):
            prompt += f"Current module: {context['module']}\n"
        if context.get("chapter"):
            prompt += f"Current chapter: {context['chapter']}\n"

        # Add conversation history if available
        if conversation_history:
            prompt += "\n**Conversation History:**\n"
            for msg in conversation_history:
                role = msg.get("role", "").upper()
                content = msg.get("content", "")
                if role == "SYSTEM":
                    continue  # Skip system messages
                prompt += f"{role}: {content}\n"
            prompt += "\n"

        prompt += f"User: {message}\n\nAssistant:"

        return prompt
