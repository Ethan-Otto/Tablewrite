"""FoundryVTT Scene operations."""

import logging
import requests
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


def _is_running_in_tests() -> bool:
    """Check if running in pytest."""
    import sys
    return "pytest" in sys.modules


class SceneManager:
    """Manages scene operations for FoundryVTT."""

    def __init__(
        self,
        relay_url: str,
        foundry_url: str,
        api_key: str,
        client_id: str,
        folder_manager: Optional[Any] = None
    ):
        """
        Initialize scene manager.

        Args:
            relay_url: URL of the relay server
            foundry_url: URL of the FoundryVTT instance
            api_key: API key for authentication
            client_id: Client ID for the FoundryVTT instance
            folder_manager: Optional FolderManager instance for organizing scenes
        """
        self.relay_url = relay_url
        self.foundry_url = foundry_url
        self.api_key = api_key
        self.client_id = client_id
        self.folder_manager = folder_manager

    def create_scene(
        self,
        name: str,
        background_image: Optional[str] = None,
        width: int = 3000,
        height: int = 2000,
        grid_size: int = 100,
        folder: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a scene in FoundryVTT via the relay API.

        Args:
            name: Name of the scene
            background_image: URL or path to background image (optional)
            width: Scene width in pixels (default 3000)
            height: Scene height in pixels (default 2000)
            grid_size: Grid size in pixels (default 100)
            folder: Folder ID to assign to the scene

        Returns:
            Dict containing the created scene data with 'uuid' key

        Raises:
            RuntimeError: If the API request fails or returns a non-200 response
        """
        url = f"{self.relay_url}/create?clientId={self.client_id}"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        # Auto-organize test scenes into "tests" folder
        if not folder and _is_running_in_tests() and self.folder_manager:
            try:
                folder = self.folder_manager.get_or_create_folder("tests", "Scene")
                logger.debug("Adding scene to 'tests' folder (running in pytest)")
            except Exception as e:
                logger.warning(f"Failed to set test folder: {e}")

        # Build scene data - FoundryVTT Scene document structure
        scene_data = {
            "name": name,
            "width": width,
            "height": height,
            "grid": {
                "size": grid_size
            }
        }

        # Add background image if provided
        if background_image:
            scene_data["background"] = {
                "src": background_image
            }

        # Add folder if provided
        if folder:
            scene_data["folder"] = folder

        payload = {
            "entityType": "Scene",
            "data": scene_data
        }

        logger.debug(f"Creating scene: {name}")

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Failed to create scene: {response.status_code} - {response.text}")
                raise RuntimeError(
                    f"Failed to create scene: {response.status_code} - {response.text}"
                )

            result = response.json()
            uuid = result.get("uuid")
            logger.info(f"Created scene: {name} (UUID: {uuid})")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Scene creation request failed: {e}")
            raise RuntimeError(f"Failed to create scene: {e}") from e

    def get_scene(self, scene_uuid: str) -> Dict[str, Any]:
        """
        Retrieve a Scene by UUID.

        Args:
            scene_uuid: UUID of the scene to retrieve (format: Scene.{id})

        Returns:
            Complete scene data as dict

        Raises:
            RuntimeError: If retrieval fails
        """
        url = f"{self.relay_url}/get?clientId={self.client_id}&uuid={scene_uuid}"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        logger.debug(f"Retrieving scene: {scene_uuid}")

        try:
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Failed to retrieve scene: {response.status_code} - {response.text}")
                raise RuntimeError(
                    f"Failed to retrieve scene: {response.status_code} - {response.text}"
                )

            response_data = response.json()

            # Extract scene data from response envelope
            scene_data = response_data.get("data", response_data)

            scene_name = scene_data.get("name", "Unknown")
            logger.info(f"Retrieved scene: {scene_name} (UUID: {scene_uuid})")
            return scene_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Scene retrieval request failed: {e}")
            raise RuntimeError(f"Failed to retrieve scene: {e}") from e

    def delete_scene(self, scene_uuid: str) -> Dict[str, Any]:
        """
        Delete a scene.

        Args:
            scene_uuid: UUID of the scene to delete (format: Scene.{id})

        Returns:
            Response data from API

        Raises:
            RuntimeError: If deletion fails
        """
        url = f"{self.relay_url}/delete?clientId={self.client_id}&uuid={scene_uuid}"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        try:
            response = requests.delete(url, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Delete failed: {response.status_code} - {response.text}")
                raise RuntimeError(f"Failed to delete scene: {response.status_code} - {response.text}")

            result = response.json()
            logger.info(f"Deleted scene: {scene_uuid}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Delete request failed: {e}")
            raise RuntimeError(f"Failed to delete scene: {e}") from e

    def search_scenes(self, name: str) -> List[Dict[str, Any]]:
        """
        Search for scenes by name.

        Args:
            name: Name to search for

        Returns:
            List of matching scene dicts (empty list if none found)
        """
        url = f"{self.relay_url}/search"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        params = {
            "clientId": self.client_id,
            "filter": "Scene",
            "query": name
        }

        logger.debug(f"Searching for scene: {name}")

        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.warning(f"Search failed: {response.status_code}")
                return []

            results = response.json()

            # Handle empty results or error response
            if not results or (isinstance(results, dict) and results.get("error")):
                logger.debug(f"No scenes found with name: {name}")
                return []

            # Handle both list and dict response formats
            search_results = results if isinstance(results, list) else results.get("results", [])

            logger.debug(f"Found {len(search_results)} scene(s) matching: {name}")
            return search_results

        except requests.exceptions.RequestException as e:
            logger.warning(f"Search request failed: {e}")
            return []

    def get_scene_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get first scene matching the given name.

        Args:
            name: Name of the scene to find

        Returns:
            Scene dict if found, None otherwise
        """
        results = self.search_scenes(name)

        if not results:
            return None

        # Return first exact name match
        for scene in results:
            if scene.get("name") == name:
                return scene

        return None
