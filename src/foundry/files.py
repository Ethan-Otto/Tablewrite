"""FoundryVTT file operations via WebSocket backend."""

import logging
import requests
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class FileManager:
    """Manages file operations for FoundryVTT via WebSocket backend.

    All operations go through the FastAPI backend HTTP API, which internally
    uses WebSocket to communicate with FoundryVTT.
    """

    def __init__(self, backend_url: str):
        """
        Initialize file manager.

        Args:
            backend_url: URL of the FastAPI backend (e.g., http://localhost:8000)
        """
        self.backend_url = backend_url

    def upload_file(
        self,
        local_path: Path,
        destination: str = "uploaded-maps"
    ) -> Dict[str, Any]:
        """
        Upload a file to FoundryVTT world folder.

        Args:
            local_path: Path to local file
            destination: Subdirectory in world folder (default: "uploaded-maps")

        Returns:
            {"success": True, "path": "worlds/.../filename"} on success
            {"success": False, "error": "..."} on failure
        """
        endpoint = f"{self.backend_url}/api/foundry/files/upload"

        # Ensure local_path is a Path object
        if not isinstance(local_path, Path):
            local_path = Path(local_path)

        if not local_path.exists():
            return {"success": False, "error": f"File not found: {local_path}"}

        try:
            with open(local_path, 'rb') as f:
                files = {'file': (local_path.name, f)}
                data = {'destination': destination}

                logger.debug(f"Uploading {local_path.name} to {destination}")
                response = requests.post(endpoint, files=files, data=data, timeout=120)

            if response.status_code != 200:
                logger.warning(f"Upload failed with status {response.status_code}")
                return {"success": False, "error": f"Upload failed: {response.status_code}"}

            result = response.json()
            logger.info(f"Uploaded {local_path.name} to {result.get('path', 'unknown')}")
            return result

        except requests.exceptions.Timeout as e:
            logger.error(f"Upload request timed out: {e}")
            return {"success": False, "error": f"Request timed out: {e}"}
        except requests.exceptions.RequestException as e:
            logger.error(f"Upload request failed: {e}")
            return {"success": False, "error": str(e)}

    def list_files(self, directory: str = "") -> Dict[str, Any]:
        """
        List files in a FoundryVTT directory.

        Args:
            directory: Directory path to list (relative to world folder)

        Returns:
            {"success": True, "files": [...]} on success
            {"success": False, "error": "..."} on failure
        """
        endpoint = f"{self.backend_url}/api/foundry/files"

        params = {}
        if directory:
            params['path'] = directory

        try:
            response = requests.get(endpoint, params=params, timeout=30)

            if response.status_code != 200:
                return {"success": False, "error": f"List files failed: {response.status_code}"}

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"List files request failed: {e}")
            return {"success": False, "error": str(e)}
