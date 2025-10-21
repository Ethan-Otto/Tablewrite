"""FoundryVTT Item operations."""

import logging
import requests
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class ItemManager:
    """Manages item operations for FoundryVTT."""

    def __init__(self, relay_url: str, foundry_url: str, api_key: str, client_id: str):
        """
        Initialize item manager.

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

    def get_all_items_by_name(self, name: str) -> List[Dict[str, Any]]:
        """
        Get all items matching the given name across all compendiums.

        Uses the QuickInsert module via the /search endpoint with filter="Item".
        Limited to 200 results maximum (hardcoded in FoundryVTT module).

        Args:
            name: Name of the item to search for

        Returns:
            List of matching item dicts (empty list if none found, max 200 items)

        Raises:
            RuntimeError: If API request fails
        """
        url = f"{self.relay_url}/search"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        params = {
            "clientId": self.client_id,
            "filter": "Item",  # Filters to documentType:Item (via QuickInsert module)
            "query": name
        }

        logger.debug(f"Searching for item: {name}")

        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Search API returns a wrapper with 'results' array
            if isinstance(data, dict) and 'results' in data:
                results = data['results']
                logger.debug(f"Search returned {len(results)} results")
                return results
            # Fallback for unexpected response format
            elif isinstance(data, list):
                logger.debug(f"Search returned {len(data)} results (list format)")
                return data
            else:
                logger.warning(f"Unexpected search result format: {type(data)}")
                return []

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

        Args:
            item_uuid: UUID of the item (e.g., "Item.abc123" or "Compendium.dnd5e.items.Item.abc123")

        Returns:
            Item data dict

        Raises:
            RuntimeError: If API request fails
        """
        url = f"{self.relay_url}/get"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        params = {
            "clientId": self.client_id,
            "uuid": item_uuid
        }

        logger.debug(f"Getting item: {item_uuid}")

        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()

            item_data = response.json()
            logger.debug(f"Retrieved item: {item_data.get('name', 'unknown')}")
            return item_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get item '{item_uuid}': {e}")
            raise RuntimeError(f"Failed to get item: {e}") from e
