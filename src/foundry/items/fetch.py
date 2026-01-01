"""
Fetch items from FoundryVTT compendiums via WebSocket backend HTTP API.

Uses alphabet-based querying to work around the 200-result search limit.
"""

import os
import logging
from typing import Dict, List, Optional
from string import ascii_lowercase
import requests

logger = logging.getLogger(__name__)

DEFAULT_BACKEND_URL = "http://localhost:8000"


def fetch_items_by_type(
    item_subtype: str,
    backend_url: str = None,
    use_two_letter_fallback: bool = True
) -> List[Dict]:
    """
    Fetch all items of a specific subtype from FoundryVTT via backend.

    Uses alphabet strategy (a-z) to bypass 200-result search limit.
    For queries that hit the limit, optionally uses two-letter combinations.

    Args:
        item_subtype: Item subtype to fetch (e.g., "spell", "weapon", "equipment")
        backend_url: Backend server URL (defaults to BACKEND_URL env var or localhost:8000)
        use_two_letter_fallback: Use two-letter combos for queries that hit 200 limit

    Returns:
        List of item dicts with name, uuid, and other metadata

    Raises:
        RuntimeError: If API request fails
    """
    backend_url = backend_url or os.getenv("BACKEND_URL", DEFAULT_BACKEND_URL)

    logger.info(f"Fetching all items of subtype '{item_subtype}'...")

    all_items = {}  # Deduplicate by UUID
    letters_at_limit = []

    def search_query(query: str) -> List[Dict]:
        """Execute a search query and return results."""
        url = f"{backend_url}/api/foundry/search"
        params = {
            "query": query,
            "document_type": "Item",
            "subtype": item_subtype
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if not data.get("success"):
                logger.warning(f"Search failed: {data.get('error')}")
                return []

            return data.get('results', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to search for '{query}': {e}")
            raise RuntimeError(f"Failed to search: {e}") from e

    # Query with each letter
    for letter in ascii_lowercase:
        results = search_query(letter)

        # Deduplicate by UUID
        for item in results:
            uuid = item.get('uuid')
            if uuid:
                all_items[uuid] = item

        logger.debug(f"Letter '{letter}': {len(results)} results (total unique: {len(all_items)})")

        # Track letters that hit the 200 limit
        if len(results) == 200 and use_two_letter_fallback:
            letters_at_limit.append(letter)

    # For letters that hit 200, query with two-letter combinations
    if letters_at_limit:
        logger.info(f"Letters at 200 limit: {', '.join(letters_at_limit)}")
        logger.info("Querying with two-letter combinations...")

        for letter in letters_at_limit:
            for second in ascii_lowercase:
                query = f"{letter}{second}"
                results = search_query(query)

                for item in results:
                    uuid = item.get('uuid')
                    if uuid:
                        all_items[uuid] = item

                if results:
                    logger.debug(f"  '{query}': {len(results)} results (total unique: {len(all_items)})")

                # Warn if even two-letter combo hits 200
                if len(results) == 200:
                    logger.warning(f"'{query}' hit 200 limit - may need 3-letter combos!")

    # Also try empty query to catch items that don't match letters
    results = search_query("")
    for item in results:
        uuid = item.get('uuid')
        if uuid:
            all_items[uuid] = item

    logger.debug(f"Empty query: {len(results)} results (total unique: {len(all_items)})")

    items_list = list(all_items.values())
    items_sorted = sorted(items_list, key=lambda i: i.get('name', ''))

    logger.info(f"Fetched {len(items_sorted)} unique items of subtype '{item_subtype}'")

    return items_sorted


def fetch_all_spells(backend_url: str = None, **kwargs) -> List[Dict]:
    """
    Convenience function to fetch all spells.

    Args:
        backend_url: Backend server URL
        **kwargs: Passed to fetch_items_by_type()

    Returns:
        List of spell dicts
    """
    return fetch_items_by_type('spell', backend_url=backend_url, **kwargs)
