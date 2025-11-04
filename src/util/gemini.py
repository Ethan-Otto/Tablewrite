"""
Gemini API utilities for D&D Module Converter.

Centralized module for all Google Generative AI (Gemini) interactions.
"""

import asyncio
import os
from typing import Optional, Any
from google import genai
from dotenv import load_dotenv
from pathlib import Path

# Default model name
DEFAULT_MODEL_NAME = "gemini-2.5-pro"


class GeminiAPI:
    """Wrapper for Gemini API operations."""

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME, api_key: Optional[str] = None):
        """
        Initialize Gemini API client.

        Args:
            model_name: Name of the Gemini model to use
            api_key: API key (if None, loads from environment)
        """
        self.model_name = model_name
        self._configured = False
        self.client = None

        if api_key:
            self._configure_with_key(api_key)
        else:
            self._configure_from_env()

    def _configure_from_env(self):
        """Load API key from .env file and configure Gemini."""
        # Try to find .env file (search up to project root)
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent
        dotenv_path = project_root / ".env"

        load_dotenv(dotenv_path=dotenv_path)

        api_key = os.getenv("GeminiImageAPI")
        if not api_key:
            raise ValueError(
                "Gemini API key not found. Set GeminiImageAPI in .env file or pass api_key parameter."
            )

        self.client = genai.Client(api_key=api_key)
        self._configured = True

    def _configure_with_key(self, api_key: str):
        """Configure Gemini with provided API key."""
        self.client = genai.Client(api_key=api_key)
        self._configured = True

    def create_model(self) -> Any:
        """
        Create a Gemini generative model instance.

        Returns:
            Client instance (for compatibility)
        """
        if not self._configured:
            raise RuntimeError("Gemini API not configured. Call configure() first.")

        return self.client

    def upload_file(self, file_path: str, display_name: Optional[str] = None) -> Any:
        """
        Upload a file to Gemini.

        Args:
            file_path: Path to file to upload
            display_name: Optional display name for the file

        Returns:
            Uploaded file object
        """
        if not self._configured:
            raise RuntimeError("Gemini API not configured.")

        return self.client.files.upload(file=file_path)

    def delete_file(self, file_name: str):
        """
        Delete a file from Gemini.

        Args:
            file_name: Name of the file to delete (from uploaded_file.name)
        """
        if not self._configured:
            raise RuntimeError("Gemini API not configured.")

        self.client.files.delete(name=file_name)

    def generate_content(self, prompt: str, file_obj: Optional[Any] = None) -> Any:
        """
        Generate content using Gemini.

        Args:
            prompt: Text prompt
            file_obj: Optional file object (from upload_file)

        Returns:
            Response object with .text attribute
        """
        if not self._configured:
            raise RuntimeError("Gemini API not configured.")

        if file_obj:
            contents = [file_obj, "\n\n", prompt]
        else:
            contents = [prompt]

        return self.client.models.generate_content(
            model=self.model_name,
            contents=contents
        )


class GeminiFileContext:
    """Context manager for uploading and auto-deleting Gemini files."""

    def __init__(self, api: GeminiAPI, file_path: str, display_name: Optional[str] = None):
        """
        Initialize file upload context.

        Args:
            api: GeminiAPI instance
            file_path: Path to file to upload
            display_name: Optional display name
        """
        self.api = api
        self.file_path = file_path
        self.display_name = display_name
        self.uploaded_file = None

    def __enter__(self):
        """Upload file on context entry."""
        self.uploaded_file = self.api.upload_file(self.file_path, self.display_name)
        return self.uploaded_file

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Delete file on context exit."""
        if self.uploaded_file:
            try:
                self.api.delete_file(self.uploaded_file.name)
            except Exception:
                # Silently fail deletion - file will expire anyway
                pass


# Convenience function for legacy code
def configure_gemini(api_key: Optional[str] = None) -> GeminiAPI:
    """
    Configure and return a Gemini API instance.

    Args:
        api_key: Optional API key (loads from .env if not provided)

    Returns:
        Configured GeminiAPI instance
    """
    return GeminiAPI(api_key=api_key)


async def generate_content_async(
    client: genai.Client,
    model: str,
    contents: Any,
    config: Optional[dict] = None
) -> Any:
    """
    Async wrapper for generate_content using asyncio.to_thread.

    The google.genai library only provides synchronous generate_content().
    This wrapper allows async code to call it without blocking the event loop.

    Args:
        client: genai.Client instance
        model: Model name (e.g., "gemini-2.5-pro")
        contents: Content to send to the model
        config: Optional generation config dict

    Returns:
        Response object with .text attribute

    Example:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = await generate_content_async(
            client=client,
            model="gemini-2.5-pro",
            contents="Hello",
            config={'temperature': 0.7}
        )
    """
    return await asyncio.to_thread(
        client.models.generate_content,
        model=model,
        contents=contents,
        config=config
    )
