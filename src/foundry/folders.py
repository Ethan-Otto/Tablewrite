"""FoundryVTT Folder operations via WebSocket backend."""

import logging
import sys
from typing import Dict, Optional, Literal

logger = logging.getLogger(__name__)


class FolderManager:
    """Manages folder operations for FoundryVTT via WebSocket backend.

    NOTE: Folder operations via WebSocket backend are not yet implemented.
    All methods raise NotImplementedError until backend endpoints are added.
    """

    def __init__(self, backend_url: str):
        """
        Initialize folder manager.

        Args:
            backend_url: URL of the FastAPI backend (e.g., http://localhost:8000)
        """
        self.backend_url = backend_url
        self._folder_cache: Dict[tuple[str, str], str] = {}  # (type, name) -> folder_id

    def get_or_create_folder(
        self,
        name: str,
        folder_type: Literal["Actor", "JournalEntry", "Item", "Scene"]
    ) -> str:
        """
        Get existing folder by name or create it if it doesn't exist.

        NOTE: This functionality requires backend endpoints that are not yet implemented.

        Args:
            name: Folder name
            folder_type: Type of entities this folder will contain

        Raises:
            NotImplementedError: Backend endpoints not yet implemented
        """
        raise NotImplementedError(
            "Folder operations via WebSocket backend not yet implemented. "
            "Add /api/foundry/folder endpoints to backend."
        )

    def search_folder(
        self,
        name: str,
        folder_type: Literal["Actor", "JournalEntry", "Item", "Scene"]
    ) -> Optional[str]:
        """
        Get a folder by name and type.

        NOTE: This functionality requires a backend endpoint that is not yet implemented.

        Args:
            name: Folder name to search for
            folder_type: Type of entities the folder contains

        Raises:
            NotImplementedError: Backend endpoint not yet implemented
        """
        raise NotImplementedError(
            "Folder search via WebSocket backend not yet implemented. "
            "Add GET /api/foundry/folder endpoint to backend."
        )

    def create_folder(
        self,
        name: str,
        folder_type: Literal["Actor", "JournalEntry", "Item", "Scene"]
    ) -> str:
        """
        Create a new folder.

        NOTE: This functionality requires a backend endpoint that is not yet implemented.

        Args:
            name: Folder name
            folder_type: Type of entities this folder will contain

        Raises:
            NotImplementedError: Backend endpoint not yet implemented
        """
        raise NotImplementedError(
            "Folder creation via WebSocket backend not yet implemented. "
            "Add POST /api/foundry/folder endpoint to backend."
        )


def is_running_in_tests() -> bool:
    """
    Detect if code is running in pytest test environment.

    Returns:
        True if running in pytest, False otherwise
    """
    return "pytest" in sys.modules


def get_test_folder_name() -> str:
    """
    Get the name for the test folder.

    Returns:
        "tests" folder name
    """
    return "tests"
