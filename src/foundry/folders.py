"""FoundryVTT Folder operations."""

import logging
import requests
import sys
from typing import Dict, Any, Optional, Literal

logger = logging.getLogger(__name__)


class FolderManager:
    """Manages folder operations for FoundryVTT."""

    def __init__(self, relay_url: str, foundry_url: str, api_key: str, client_id: str):
        """
        Initialize folder manager.

        Args:
            relay_url: URL of the relay server
            foundry_url: URL of the FoundryVTT instance
            api_key: API key for authentication
            client_id: Client ID for the FoundryVTT instance
        """
        self.relay_url = relay_url
        self.foundry_url = foundry_url
        self.api_key = api_key
        self.client_id = client_id
        self._folder_cache: Dict[tuple[str, str], str] = {}  # (type, name) -> folder_id

    def get_or_create_folder(
        self,
        name: str,
        folder_type: Literal["Actor", "JournalEntry", "Item", "Scene"]
    ) -> str:
        """
        Get existing folder by name or create it if it doesn't exist.

        Args:
            name: Folder name
            folder_type: Type of entities this folder will contain
                        ("Actor", "JournalEntry", "Item", "Scene")

        Returns:
            Folder ID

        Raises:
            RuntimeError: If folder operations fail
        """
        # Check cache first
        cache_key = (folder_type, name)
        if cache_key in self._folder_cache:
            logger.debug(f"Using cached folder ID for '{name}' ({folder_type})")
            return self._folder_cache[cache_key]

        # Search for existing folder
        folder_id = self.search_folder(name, folder_type)
        if folder_id:
            logger.info(f"Found existing folder: '{name}' ({folder_type}) - {folder_id}")
            self._folder_cache[cache_key] = folder_id
            return folder_id

        # Create new folder
        folder_id = self.create_folder(name, folder_type)
        logger.info(f"Created new folder: '{name}' ({folder_type}) - {folder_id}")
        self._folder_cache[cache_key] = folder_id
        return folder_id

    def search_folder(
        self,
        name: str,
        folder_type: Literal["Actor", "JournalEntry", "Item", "Scene"]
    ) -> Optional[str]:
        """
        Get a folder by name and type using the /get-folder endpoint.

        Args:
            name: Folder name to search for
            folder_type: Type of entities the folder contains

        Returns:
            Folder ID if found, None otherwise
        """
        url = f"{self.relay_url}/get-folder"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        params = {
            "clientId": self.client_id,
            "name": name
        }

        logger.debug(f"Getting folder: {name} ({folder_type})")

        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)

            if response.status_code == 404:
                logger.debug(f"Folder not found: {name}")
                return None

            if response.status_code != 200:
                logger.warning(f"Get folder failed: {response.status_code} - {response.text}")
                return None

            result = response.json()
            data = result.get("data", {})

            # Check if the folder type matches
            if data.get("type") == folder_type:
                folder_id = data.get("id")
                logger.debug(f"Found folder: {name} ({folder_type}) - {folder_id}")
                return folder_id
            else:
                logger.debug(f"Folder found but type mismatch: expected {folder_type}, got {data.get('type')}")
                return None

        except Exception as e:
            logger.warning(f"Get folder failed: {e}")
            return None

    def create_folder(
        self,
        name: str,
        folder_type: Literal["Actor", "JournalEntry", "Item", "Scene"]
    ) -> str:
        """
        Create a new folder using the /create-folder endpoint.

        Args:
            name: Folder name
            folder_type: Type of entities this folder will contain

        Returns:
            Folder ID

        Raises:
            RuntimeError: If creation fails
        """
        url = f"{self.relay_url}/create-folder"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "clientId": self.client_id,
            "name": name,
            "folderType": folder_type
        }

        logger.debug(f"Creating folder: {name} ({folder_type})")

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Folder creation failed: {response.status_code} - {response.text}")
                raise RuntimeError(
                    f"Failed to create folder: {response.status_code} - {response.text}"
                )

            result = response.json()
            folder_id = result.get("data", {}).get("id")

            if not folder_id:
                logger.error(f"No folder ID in response: {result}")
                raise RuntimeError("Failed to get folder ID from response")

            logger.info(f"Created folder: {name} ({folder_type}) - {folder_id}")
            return folder_id

        except requests.exceptions.RequestException as e:
            logger.error(f"Folder creation request failed: {e}")
            raise RuntimeError(f"Failed to create folder: {e}") from e


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
