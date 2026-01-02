"""FoundryVTT Scene operations via WebSocket backend."""

import logging
import requests
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class SceneManager:
    """Manages scene operations for FoundryVTT via WebSocket backend.

    All operations go through the FastAPI backend HTTP API, which internally
    uses WebSocket to communicate with FoundryVTT. The relay server is no longer used.
    """

    def __init__(self, backend_url: str):
        """
        Initialize scene manager.

        Args:
            backend_url: URL of the FastAPI backend (e.g., http://localhost:8000)
        """
        self.backend_url = backend_url

    def create_scene(
        self,
        name: str,
        background_image: Optional[str] = None,
        width: int = 3000,
        height: int = 2000,
        grid_size: Optional[int] = 100,
        walls: Optional[List[Dict[str, Any]]] = None,
        folder: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a scene in FoundryVTT via the backend WebSocket.

        Args:
            name: Name of the scene
            background_image: Foundry-relative path to background image
            width: Scene width in pixels (default 3000)
            height: Scene height in pixels (default 2000)
            grid_size: Grid size in pixels (None for gridless)
            walls: Optional list of wall objects
            folder: Optional folder ID

        Returns:
            {"success": True, "uuid": "Scene.xxx", "name": "..."} on success
            {"success": False, "error": "..."} on failure
        """
        endpoint = f"{self.backend_url}/api/foundry/scene"

        scene_data: Dict[str, Any] = {
            "name": name,
            "width": width,
            "height": height,
        }

        if background_image:
            scene_data["background"] = {"src": background_image}

        if grid_size is not None:
            scene_data["grid"] = {"size": grid_size, "type": 1}

        if walls:
            scene_data["walls"] = walls

        if folder:
            scene_data["folder"] = folder

        payload = {"scene": scene_data}

        logger.debug(f"Creating scene: {name}")

        try:
            response = requests.post(endpoint, json=payload, timeout=60)

            if response.status_code != 200:
                error_msg = response.json().get("detail", f"HTTP {response.status_code}")
                return {"success": False, "error": error_msg}

            data = response.json()
            logger.info(f"Created scene: {data.get('uuid')}")
            return {"success": True, "uuid": data.get("uuid"), "name": data.get("name")}

        except requests.exceptions.RequestException as e:
            logger.error(f"Create scene failed: {e}")
            return {"success": False, "error": str(e)}

    def get_scene(self, scene_uuid: str) -> Dict[str, Any]:
        """
        Retrieve a Scene by UUID.

        NOTE: This functionality requires a backend endpoint that is not yet implemented.

        Args:
            scene_uuid: UUID of the scene to retrieve

        Raises:
            NotImplementedError: Backend endpoint not yet implemented
        """
        raise NotImplementedError(
            "Get scene via WebSocket backend not yet implemented. "
            "Add GET /api/foundry/scene/{uuid} endpoint to backend."
        )

    def delete_scene(self, scene_uuid: str) -> Dict[str, Any]:
        """
        Delete a scene.

        NOTE: This functionality requires a backend endpoint that is not yet implemented.

        Args:
            scene_uuid: UUID of the scene to delete

        Raises:
            NotImplementedError: Backend endpoint not yet implemented
        """
        raise NotImplementedError(
            "Delete scene via WebSocket backend not yet implemented. "
            "Add DELETE /api/foundry/scene/{uuid} endpoint to backend."
        )

    def search_scenes(self, name: str) -> List[Dict[str, Any]]:
        """
        Search for scenes by name.

        Args:
            name: Name to search for

        Returns:
            List of matching scene dicts (empty list if none found)
        """
        endpoint = f"{self.backend_url}/api/foundry/search"

        params = {
            "query": name,
            "document_type": "Scene"
        }

        logger.debug(f"Searching for scene: {name}")

        try:
            response = requests.get(endpoint, params=params, timeout=30)

            if response.status_code != 200:
                logger.warning(f"Search failed: {response.status_code}")
                return []

            data = response.json()

            if not data.get("success"):
                return []

            results = data.get("results", [])
            logger.debug(f"Found {len(results)} scene(s) matching: {name}")
            return results

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
