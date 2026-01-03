"""FoundryVTT API client via WebSocket backend."""

import os
import logging
import requests
from typing import Dict, Any, Optional, List

from .journals import JournalManager
from .items.manager import ItemManager
from .actors import ActorManager
from .scenes import SceneManager
from .icon_cache import IconCache
from .files import FileManager

logger = logging.getLogger(__name__)

# Default backend URL - the FastAPI server that handles WebSocket communication
DEFAULT_BACKEND_URL = "http://localhost:8000"


class FoundryClient:
    """Client for interacting with FoundryVTT via WebSocket backend.

    All operations go through the FastAPI backend which communicates with
    FoundryVTT via WebSocket. The relay server is no longer used.
    """

    def __init__(self, backend_url: Optional[str] = None):
        """
        Initialize FoundryVTT API client.

        Args:
            backend_url: URL of the FastAPI backend (default: http://localhost:8000)
                        Can also be set via BACKEND_URL environment variable.
        """
        self.backend_url = backend_url or os.getenv("BACKEND_URL", DEFAULT_BACKEND_URL)

        # Initialize managers - all use backend HTTP API
        self.journals = JournalManager(backend_url=self.backend_url)
        self.items = ItemManager(backend_url=self.backend_url)
        self.actors = ActorManager(backend_url=self.backend_url)
        self.scenes = SceneManager(backend_url=self.backend_url)
        self.files = FileManager(backend_url=self.backend_url)
        self.icons = IconCache()

        logger.info(f"Initialized FoundryClient with backend at {self.backend_url}")

    # Journal operations (delegated to JournalManager)

    def create_journal_entry(
        self,
        name: str,
        pages: list = None,
        content: str = None,
        folder: str = None
    ) -> Dict[str, Any]:
        """Create a new journal entry in FoundryVTT."""
        return self.journals.create_journal_entry(name, pages, content, folder)

    def get_all_journals_by_name(self, name: str) -> list[Dict[str, Any]]:
        """Get all journals matching the given name."""
        return self.journals.get_all_journals_by_name(name)

    def get_journal_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get first journal matching the given name."""
        return self.journals.get_journal_by_name(name)

    def get_journal(self, journal_uuid: str) -> Dict[str, Any]:
        """Get a journal by UUID."""
        return self.journals.get_journal(journal_uuid)

    def update_journal_entry(
        self,
        journal_uuid: str,
        pages: list = None,
        content: str = None,
        name: str = None
    ) -> Dict[str, Any]:
        """Update an existing journal entry."""
        return self.journals.update_journal_entry(journal_uuid, pages, content, name)

    def delete_journal_entry(self, journal_uuid: str) -> Dict[str, Any]:
        """Delete a journal entry."""
        return self.journals.delete_journal_entry(journal_uuid)

    def create_or_replace_journal(
        self,
        name: str,
        pages: list = None,
        content: str = None,
        folder: str = None
    ) -> Dict[str, Any]:
        """Create or replace a journal entry."""
        return self.journals.create_or_replace_journal(name, pages, content, folder)

    # Item operations (delegated to ItemManager)

    def get_all_items_by_name(self, name: str) -> list[Dict[str, Any]]:
        """Get all items matching the given name."""
        return self.items.get_all_items_by_name(name)

    def get_item_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get first item matching the given name."""
        return self.items.get_item_by_name(name)

    def get_item(self, item_uuid: str) -> Dict[str, Any]:
        """Get an item by UUID."""
        return self.items.get_item(item_uuid)

    # File operations (delegated to FileManager)

    def upload_file(self, local_path: str, destination: str = "uploaded-maps") -> Dict[str, Any]:
        """
        Upload a file to FoundryVTT world folder.

        Args:
            local_path: Path to local file
            destination: Subdirectory in world folder (default: "uploaded-maps")

        Returns:
            {"success": True, "path": "worlds/.../filename"} on success
            {"success": False, "error": "..."} on failure
        """
        from pathlib import Path
        return self.files.upload_file(Path(local_path), destination)

    def download_file(self, target_path: str, local_path: str) -> None:
        """
        Download a file from FoundryVTT.

        NOTE: This functionality requires a backend endpoint that is not yet implemented.

        Args:
            target_path: Full path to file in FoundryVTT
            local_path: Local path to save downloaded file

        Raises:
            NotImplementedError: Backend file download endpoint not yet implemented
        """
        raise NotImplementedError(
            "File download via WebSocket backend not yet implemented. "
            "Add GET /api/foundry/download endpoint to backend."
        )

    def is_connected(self) -> bool:
        """
        Check if the backend is connected to FoundryVTT via WebSocket.

        Returns:
            True if backend is running and connected to Foundry, False otherwise
        """
        endpoint = f"{self.backend_url}/api/foundry/status"

        try:
            response = requests.get(endpoint, timeout=5)
            response.raise_for_status()
            data = response.json()
            return data.get("connected_clients", 0) > 0
        except requests.exceptions.RequestException:
            return False

    def is_world_active(self) -> bool:
        """
        Check if FoundryVTT is active and connected.

        Uses the backend status endpoint to verify connection.

        Returns:
            True if backend is connected to Foundry, False otherwise
        """
        return self.is_connected()

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """
        Get currently active sessions.

        NOTE: This functionality is not available via WebSocket backend.

        Raises:
            NotImplementedError: Session management not available via WebSocket
        """
        raise NotImplementedError(
            "Session management not available via WebSocket backend."
        )

    # Actor operations (delegated to ActorManager)

    def search_actor(self, name: str) -> Optional[str]:
        """Search for actor by name in all compendiums."""
        return self.actors.search_all_compendiums(name)

    def create_creature_actor(self, stat_block) -> str:
        """Create creature actor from stat block."""
        return self.actors.create_creature_actor(stat_block)

    def create_npc_actor(self, npc, stat_block_uuid: Optional[str] = None) -> str:
        """Create NPC actor with optional stat block link."""
        return self.actors.create_npc_actor(npc, stat_block_uuid)
