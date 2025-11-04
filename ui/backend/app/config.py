"""Configuration for chat backend."""
from pathlib import Path


class Settings:
    """Application settings."""

    # Tool settings
    MAX_IMAGES_PER_REQUEST = 4
    IMAGE_STORAGE_DAYS = 7
    IMAGE_OUTPUT_DIR = Path("app/output/chat_images")

    # Gemini settings
    GEMINI_MODEL = "gemini-2.0-flash"
    GEMINI_TIMEOUT = 60  # seconds

    # Image generation
    IMAGEN_CONCURRENT_LIMIT = 2  # Max parallel image generation


# Global settings instance
settings = Settings()
