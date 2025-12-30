"""Fetch items from FoundryVTT via HTTP API (calls backend WebSocket internally)."""

import logging
import httpx
from typing import Dict, List, Optional
from string import ascii_lowercase

logger = logging.getLogger(__name__)

# Backend URL - can be overridden via environment variable
BACKEND_URL = "http://localhost:8000"


async def search_items_http(
    query: str,
    document_type: str = "Item",
    sub_type: Optional[str] = None,
    timeout: float = 30.0
) -> Dict:
    """
    Search for items via the backend HTTP API.

    Args:
        query: Search query string
        document_type: Document type (default: "Item")
        sub_type: Optional subtype filter (e.g., "spell")
        timeout: Request timeout in seconds

    Returns:
        Dict with success, count, results keys
    """
    params = {"query": query, "document_type": document_type}
    if sub_type:
        params["sub_type"] = sub_type

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BACKEND_URL}/api/foundry/search",
            params=params,
            timeout=timeout
        )
        response.raise_for_status()
        return response.json()


async def fetch_items_by_type_ws(
    item_subtype: str,
    use_two_letter_fallback: bool = True
) -> List[Dict]:
    """
    Fetch all items of a specific subtype from FoundryVTT via HTTP API.

    Uses alphabet strategy (a-z) to bypass 200-result search limit.

    Args:
        item_subtype: Item subtype to fetch (e.g., "spell", "weapon")
        use_two_letter_fallback: Use two-letter combos for queries that hit 200 limit

    Returns:
        List of item dicts with name, uuid, and other metadata
    """
    logger.info(f"Fetching all items of subtype '{item_subtype}' via HTTP API...")

    all_items = {}  # Deduplicate by UUID
    letters_at_limit = []

    # Query with each letter
    for letter in ascii_lowercase:
        try:
            result = await search_items_http(
                query=letter,
                document_type="Item",
                sub_type=item_subtype,
                timeout=30.0
            )

            if not result.get("success"):
                logger.error(f"Search failed for '{letter}'")
                continue

            # Deduplicate by UUID
            for item in result.get("results", []):
                all_items[item["uuid"]] = item

            result_count = result.get("count", 0)
            logger.debug(f"Letter '{letter}': {result_count} results (total unique: {len(all_items)})")

            # Track letters that hit the 200 limit
            if result_count == 200 and use_two_letter_fallback:
                letters_at_limit.append(letter)

        except Exception as e:
            logger.error(f"Search failed for '{letter}': {e}")
            continue

    # For letters that hit 200, query with two-letter combinations
    if letters_at_limit:
        logger.info(f"Letters at 200 limit: {', '.join(letters_at_limit)}")
        logger.info("Querying with two-letter combinations...")

        for letter in letters_at_limit:
            for second in ascii_lowercase:
                query = f"{letter}{second}"
                try:
                    result = await search_items_http(
                        query=query,
                        document_type="Item",
                        sub_type=item_subtype,
                        timeout=30.0
                    )

                    if result.get("success"):
                        for item in result.get("results", []):
                            all_items[item["uuid"]] = item
                except Exception:
                    continue

    # Also try empty query
    try:
        result = await search_items_http(
            query="",
            document_type="Item",
            sub_type=item_subtype,
            timeout=30.0
        )
        if result.get("success"):
            for item in result.get("results", []):
                all_items[item["uuid"]] = item
    except Exception:
        pass

    items_list = list(all_items.values())
    items_sorted = sorted(items_list, key=lambda i: i.get('name', ''))

    logger.info(f"Fetched {len(items_sorted)} unique items of subtype '{item_subtype}'")

    return items_sorted


async def fetch_all_spells_ws() -> List[Dict]:
    """Fetch all spells via HTTP API."""
    return await fetch_items_by_type_ws('spell')


def fetch_all_spells_ws_sync() -> List[Dict]:
    """Synchronous wrapper for fetch_all_spells_ws.

    Uses httpx sync client for simpler thread handling.
    """
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No event loop running, use asyncio.run()
        return asyncio.run(fetch_all_spells_ws())
    else:
        # Event loop already running, run in separate thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, fetch_all_spells_ws())
            return future.result(timeout=300)
