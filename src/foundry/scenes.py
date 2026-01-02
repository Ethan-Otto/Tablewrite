"""FoundryVTT Scene operations via WebSocket backend."""

import logging
import requests
from json import JSONDecodeError
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
                # Safe JSON parsing for error details
                try:
                    error_detail = response.json().get("detail", f"HTTP {response.status_code}")
                except (ValueError, JSONDecodeError):
                    error_detail = f"HTTP {response.status_code}: {response.text[:200]}"
                return {"success": False, "error": error_detail}

            # Parse and validate response
            try:
                data = response.json()
            except (ValueError, JSONDecodeError) as e:
                logger.error(f"Invalid JSON response: {e}")
                return {"success": False, "error": f"Invalid JSON response: {e}"}

            # Validate response has required fields
            if not isinstance(data, dict):
                return {"success": False, "error": f"Unexpected response type: {type(data).__name__}"}

            if "uuid" not in data:
                logger.warning(f"Response missing 'uuid' field: {data}")

            logger.info(f"Created scene: {data.get('uuid')}")
            # Return complete response with success flag
            return {"success": True, **data}

        except requests.exceptions.RequestException as e:
            logger.error(f"Create scene failed: {e}")
            return {"success": False, "error": str(e)}

    def get_scene(self, scene_uuid: str) -> Dict[str, Any]:
        """
        Retrieve a Scene by UUID.

        Args:
            scene_uuid: UUID of the scene to retrieve (e.g., "Scene.abc123")

        Returns:
            {"success": True, "entity": {...}} on success
            {"success": False, "error": "..."} on failure
        """
        endpoint = f"{self.backend_url}/api/foundry/scene/{scene_uuid}"

        logger.debug(f"Getting scene: {scene_uuid}")

        try:
            response = requests.get(endpoint, timeout=30)

            if response.status_code == 404:
                return {"success": False, "error": f"Scene not found: {scene_uuid}"}

            if response.status_code != 200:
                # Safe JSON parsing for error details
                try:
                    error_detail = response.json().get("detail", f"HTTP {response.status_code}")
                except (ValueError, JSONDecodeError):
                    error_detail = f"HTTP {response.status_code}: {response.text[:200]}"
                return {"success": False, "error": error_detail}

            # Parse and validate response
            try:
                data = response.json()
            except (ValueError, JSONDecodeError) as e:
                logger.error(f"Invalid JSON response: {e}")
                return {"success": False, "error": f"Invalid JSON response: {e}"}

            # Validate response has required fields
            if not isinstance(data, dict):
                return {"success": False, "error": f"Unexpected response type: {type(data).__name__}"}

            logger.info(f"Got scene: {scene_uuid}")
            return {"success": True, **data}

        except requests.exceptions.RequestException as e:
            logger.error(f"Get scene failed: {e}")
            return {"success": False, "error": str(e)}

    def delete_scene(self, scene_uuid: str) -> Dict[str, Any]:
        """
        Delete a scene.

        Args:
            scene_uuid: UUID of the scene to delete (e.g., "Scene.abc123")

        Returns:
            {"success": True, "uuid": "...", "name": "..."} on success
            {"success": False, "error": "..."} on failure
        """
        endpoint = f"{self.backend_url}/api/foundry/scene/{scene_uuid}"

        logger.debug(f"Deleting scene: {scene_uuid}")

        try:
            response = requests.delete(endpoint, timeout=30)

            if response.status_code == 404:
                return {"success": False, "error": f"Scene not found: {scene_uuid}"}

            if response.status_code != 200:
                # Safe JSON parsing for error details
                try:
                    error_detail = response.json().get("detail", f"HTTP {response.status_code}")
                except (ValueError, JSONDecodeError):
                    error_detail = f"HTTP {response.status_code}: {response.text[:200]}"
                return {"success": False, "error": error_detail}

            # Parse and validate response
            try:
                data = response.json()
            except (ValueError, JSONDecodeError) as e:
                logger.error(f"Invalid JSON response: {e}")
                return {"success": False, "error": f"Invalid JSON response: {e}"}

            # Validate response has required fields
            if not isinstance(data, dict):
                return {"success": False, "error": f"Unexpected response type: {type(data).__name__}"}

            logger.info(f"Deleted scene: {data.get('name')} ({scene_uuid})")
            return {"success": True, **data}

        except requests.exceptions.RequestException as e:
            logger.error(f"Delete scene failed: {e}")
            return {"success": False, "error": str(e)}

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

            # Safe JSON parsing
            try:
                data = response.json()
            except (ValueError, JSONDecodeError):
                logger.warning("Search returned invalid JSON")
                return []

            if not isinstance(data, dict) or not data.get("success"):
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
