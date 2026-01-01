"""FoundryVTT Item operations via WebSocket backend."""

import logging
import requests
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class ItemManager:
    """Manages item operations for FoundryVTT via WebSocket backend.

    All operations go through the FastAPI backend HTTP API, which internally
    uses WebSocket to communicate with FoundryVTT. The relay server is no longer used.
    """

    def __init__(self, backend_url: str):
        """
        Initialize item manager.

        Args:
            backend_url: URL of the FastAPI backend (e.g., http://localhost:8000)
        """
        self.backend_url = backend_url

    def get_all_items_by_name(self, name: str) -> List[Dict[str, Any]]:
        """
        Get all items matching the given name across all compendiums.

        Uses the backend search endpoint which queries via WebSocket.

        Args:
            name: Name of the item to search for

        Returns:
            List of matching item dicts (empty list if none found)

        Raises:
            RuntimeError: If API request fails
        """
        endpoint = f"{self.backend_url}/api/foundry/search"

        params = {
            "query": name,
            "document_type": "Item"
        }

        logger.debug(f"Searching for item: {name}")

        try:
            response = requests.get(endpoint, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            if not data.get("success"):
                logger.warning(f"Search failed: {data.get('error')}")
                return []

            results = data.get("results", [])
            logger.debug(f"Search returned {len(results)} results")
            return results

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to search for item '{name}': {e}")
            raise RuntimeError(f"Failed to search for item: {e}") from e

    def get_item_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get first item matching the given name.

        Args:
            name: Name of the item to find

        Returns:
            Item dict if found (with uuid, name, package, etc.), None otherwise

        Raises:
            RuntimeError: If API request fails
        """
        results = self.get_all_items_by_name(name)

        if not results:
            logger.debug(f"No item found with name: {name}")
            return None

        # Return first match
        item = results[0]
        logger.debug(f"Found item: {item.get('name', 'unknown')} (UUID: {item.get('uuid', 'unknown')})")
        return item

    def get_item(self, item_uuid: str) -> Dict[str, Any]:
        """
        Get an item by UUID.

        NOTE: This functionality requires a backend endpoint that is not yet implemented.

        Args:
            item_uuid: UUID of the item

        Returns:
            Item data dict

        Raises:
            NotImplementedError: Backend endpoint not yet implemented
        """
        raise NotImplementedError(
            "Get item by UUID via WebSocket backend not yet implemented. "
            "Add GET /api/foundry/item/{uuid} endpoint to backend."
        )
