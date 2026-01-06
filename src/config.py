"""Centralized configuration for the D&D module converter.

This module provides:
- PROJECT_ROOT and SRC_DIR paths
- Environment variable access with get_env()
- Automatic .env loading

Usage:
    from config import PROJECT_ROOT, get_env

    api_key = get_env("GeminiImageAPI")
    data_dir = PROJECT_ROOT / "data" / "pdfs"
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Calculate paths once at import time
SRC_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SRC_DIR.parent.resolve()

# Load .env from project root
_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    load_dotenv(_env_path)


def get_env(key: str, default: Optional[str] = None) -> str:
    """Get environment variable value.

    Args:
        key: Environment variable name
        default: Default value if not set. If None and key not found, raises KeyError.

    Returns:
        Environment variable value or default

    Raises:
        KeyError: If key not found and no default provided
    """
    value = os.environ.get(key)
    if value is not None:
        return value
    if default is not None:
        return default
    raise KeyError(f"Environment variable '{key}' not set and no default provided")


# Common configuration values
def get_gemini_api_key() -> str:
    """Get Gemini API key from environment."""
    return get_env("GeminiImageAPI")


def get_backend_url() -> str:
    """Get backend URL for API calls."""
    return get_env("BACKEND_URL", default="http://localhost:8000")


def get_foundry_url() -> str:
    """Get FoundryVTT URL."""
    return get_env("FOUNDRY_URL", default="http://localhost:30000")
