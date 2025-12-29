"""FoundryVTT REST API client."""

import os
import logging
import requests
from typing import Dict, Any, Optional, List

from .journals import JournalManager
from .items.manager import ItemManager
from .actors import ActorManager
from .scenes import SceneManager
from .icon_cache import IconCache

logger = logging.getLogger(__name__)


class FoundryClient:
    """Client for interacting with FoundryVTT via REST API."""

    def __init__(self):
        """
        Initialize FoundryVTT API client.

        Raises:
            ValueError: If required environment variables are not set
        """
        self.relay_url = os.getenv("FOUNDRY_RELAY_URL")
        self.foundry_url = os.getenv("FOUNDRY_URL")
        self.api_key = os.getenv("FOUNDRY_API_KEY")
        self.client_id = os.getenv("FOUNDRY_CLIENT_ID")

        if not self.relay_url:
            raise ValueError("FOUNDRY_RELAY_URL not set in environment")
        if not self.foundry_url:
            raise ValueError("FOUNDRY_URL not set in environment")
        if not self.api_key:
            raise ValueError("FOUNDRY_API_KEY not set in environment")
        if not self.client_id:
            raise ValueError("FOUNDRY_CLIENT_ID not set in environment")

        # Initialize managers
        self.journals = JournalManager(
            relay_url=self.relay_url,
            foundry_url=self.foundry_url,
            api_key=self.api_key,
            client_id=self.client_id
        )

        self.items = ItemManager(
            relay_url=self.relay_url,
            foundry_url=self.foundry_url,
            api_key=self.api_key,
            client_id=self.client_id
        )

        self.actors = ActorManager(
            relay_url=self.relay_url,
            foundry_url=self.foundry_url,
            api_key=self.api_key,
            client_id=self.client_id
        )

        self.scenes = SceneManager(
            relay_url=self.relay_url,
            foundry_url=self.foundry_url,
            api_key=self.api_key,
            client_id=self.client_id
        )

        self.icons = IconCache()

        logger.info(f"Initialized FoundryClient at {self.foundry_url}")

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

    # File operations

    def upload_file(self, local_path: str, target_path: str, overwrite: bool = True) -> Dict[str, Any]:
        """
        Upload a file to FoundryVTT.

        Args:
            local_path: Path to local file
            target_path: Target path in FoundryVTT (e.g., "worlds/my-world/assets/image.png")
            overwrite: Whether to overwrite existing files (default: True)

        Returns:
            Upload response dict

        Raises:
            RuntimeError: If upload fails
        """
        from pathlib import Path
        import mimetypes

        endpoint = f"{self.relay_url}/upload"

        # Split target_path into directory path and filename
        path_obj = Path(target_path)
        directory = str(path_obj.parent)
        filename = path_obj.name

        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            mime_type = "application/octet-stream"

        # API expects x-api-key header, binary data in body, and separate path/filename parameters
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/octet-stream"
        }

        params = {
            "clientId": self.client_id,
            "path": directory,
            "filename": filename,
            "mimeType": mime_type,
            "overwrite": str(overwrite).lower()
        }

        logger.debug(f"Uploading {local_path} → {target_path}")

        # Read file as binary data for request body
        try:
            with open(local_path, 'rb') as f:
                file_data = f.read()
        except IOError as e:
            logger.error(f"Failed to read local file '{local_path}': {e}")
            raise RuntimeError(f"Failed to read file: {e}") from e

        try:
            response = requests.post(endpoint, headers=headers, params=params, data=file_data, timeout=60)
            response.raise_for_status()
            result = response.json()
            logger.debug(f"Upload successful: {filename}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to upload file '{filename}': {e}")
            raise RuntimeError(f"Failed to upload file: {e}") from e

    def download_file(self, target_path: str, local_path: str) -> None:
        """
        Download a file from FoundryVTT.

        Args:
            target_path: Full path to file in FoundryVTT (e.g., "worlds/my-world/assets/image.png")
            local_path: Local path to save downloaded file

        Raises:
            RuntimeError: If download fails
        """
        from pathlib import Path

        endpoint = f"{self.relay_url}/download"

        headers = {
            "x-api-key": self.api_key
        }

        # Download endpoint expects full file path in "path" parameter (no separate filename)
        params = {
            "clientId": self.client_id,
            "path": target_path
        }

        logger.debug(f"Downloading {target_path} → {local_path}")

        try:
            response = requests.get(endpoint, headers=headers, params=params, timeout=60)
            response.raise_for_status()

            # Write binary response to file
            with open(local_path, 'wb') as f:
                f.write(response.content)

            logger.debug(f"Download successful: {target_path}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download file '{target_path}': {e}")
            raise RuntimeError(f"Failed to download file: {e}") from e
        except IOError as e:
            logger.error(f"Failed to write to local file '{local_path}': {e}")
            raise RuntimeError(f"Failed to write file: {e}") from e

    def is_world_active(self) -> bool:
        """
        Check if any world is currently running in FoundryVTT.

        This works regardless of whether the world was launched via browser
        or headless API session. Makes a lightweight search API call to verify
        the server can respond.

        Returns:
            True if a world is active and responding, False otherwise
        """
        endpoint = f"{self.relay_url}/search"

        headers = {
            "x-api-key": self.api_key
        }

        params = {
            "clientId": self.client_id,
            "query": "",
            "filter": "Item"
        }

        try:
            response = requests.get(endpoint, headers=headers, params=params, timeout=5)
            response.raise_for_status()
            # If we get a successful response, a world is active
            return True
        except requests.exceptions.RequestException:
            # Any error means no world is active or server isn't responding
            return False

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """
        Get currently active headless FoundryVTT sessions.

        Note: This only returns headless API sessions, not browser sessions.
        Use is_world_active() to check if any world is running.

        Returns:
            List of active session dictionaries with keys:
                - id: Session ID
                - clientId: Client ID
                - lastActivity: Timestamp of last activity
                - idleMinutes: Minutes since last activity

        Raises:
            RuntimeError: If API call fails
        """
        endpoint = f"{self.relay_url}/session"

        headers = {
            "x-api-key": self.api_key
        }

        try:
            response = requests.get(endpoint, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('activeSessions', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get active sessions: {e}")
            raise RuntimeError(f"Failed to get active sessions: {e}") from e

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
