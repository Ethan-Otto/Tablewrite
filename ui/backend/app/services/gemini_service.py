"""Gemini service for Module Assistant."""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

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

Available commands:
- /generate-scene [description] - Generate a new scene
- /list-scenes [chapter] - List scenes in a chapter
- /list-actors - List all actors/NPCs
- /help - Show help

"""

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
