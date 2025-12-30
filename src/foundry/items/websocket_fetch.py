"""Fetch items from FoundryVTT via WebSocket."""

import asyncio
import logging
import sys
import os
from typing import Dict, List
from string import ascii_lowercase

# Add ui/backend to path for importing websocket module
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_ui_backend_path = os.path.join(_project_root, "ui", "backend")
if _ui_backend_path not in sys.path:
    sys.path.insert(0, _ui_backend_path)

logger = logging.getLogger(__name__)


async def fetch_items_by_type_ws(
    item_subtype: str,
    use_two_letter_fallback: bool = True
) -> List[Dict]:
    """
    Fetch all items of a specific subtype from FoundryVTT via WebSocket.

    Uses alphabet strategy (a-z) to bypass 200-result search limit.

    Args:
        item_subtype: Item subtype to fetch (e.g., "spell", "weapon")
        use_two_letter_fallback: Use two-letter combos for queries that hit 200 limit

    Returns:
        List of item dicts with name, uuid, and other metadata
    """
    # Import here to avoid circular imports
    from app.websocket import search_items

    logger.info(f"Fetching all items of subtype '{item_subtype}' via WebSocket...")

    all_items = {}  # Deduplicate by UUID
    letters_at_limit = []

    # Query with each letter
    for letter in ascii_lowercase:
        result = await search_items(
            query=letter,
            document_type="Item",
            sub_type=item_subtype,
            timeout=30.0
        )

        if not result.success:
            logger.error(f"Search failed for '{letter}': {result.error}")
            continue

        # Deduplicate by UUID
        for item in result.results or []:
            all_items[item.uuid] = {
                "uuid": item.uuid,
                "id": item.id,
                "name": item.name,
                "type": item.type,
                "img": item.img,
                "pack": item.pack
            }

        result_count = len(result.results or [])
        logger.debug(f"Letter '{letter}': {result_count} results (total unique: {len(all_items)})")

        # Track letters that hit the 200 limit
        if result_count == 200 and use_two_letter_fallback:
            letters_at_limit.append(letter)

    # For letters that hit 200, query with two-letter combinations
    if letters_at_limit:
        logger.info(f"Letters at 200 limit: {', '.join(letters_at_limit)}")
        logger.info("Querying with two-letter combinations...")

        for letter in letters_at_limit:
            for second in ascii_lowercase:
                query = f"{letter}{second}"
                result = await search_items(
                    query=query,
                    document_type="Item",
                    sub_type=item_subtype,
                    timeout=30.0
                )

                if result.success:
                    for item in result.results or []:
                        all_items[item.uuid] = {
                            "uuid": item.uuid,
                            "id": item.id,
                            "name": item.name,
                            "type": item.type,
                            "img": item.img,
                            "pack": item.pack
                        }

    # Also try empty query
    result = await search_items(
        query="",
        document_type="Item",
        sub_type=item_subtype,
        timeout=30.0
    )
    if result.success:
        for item in result.results or []:
            all_items[item.uuid] = {
                "uuid": item.uuid,
                "id": item.id,
                "name": item.name,
                "type": item.type,
                "img": item.img,
                "pack": item.pack
            }

    items_list = list(all_items.values())
    items_sorted = sorted(items_list, key=lambda i: i.get('name', ''))

    logger.info(f"Fetched {len(items_sorted)} unique items of subtype '{item_subtype}'")

    return items_sorted


async def fetch_all_spells_ws() -> List[Dict]:
    """Fetch all spells via WebSocket."""
    return await fetch_items_by_type_ws('spell')


def fetch_all_spells_ws_sync() -> List[Dict]:
    """Synchronous wrapper for fetch_all_spells_ws.

    Handles both cases:
    - No event loop running: uses asyncio.run()
    - Event loop already running (e.g., pytest-asyncio): uses run_until_complete()
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No event loop running, use asyncio.run()
        return asyncio.run(fetch_all_spells_ws())
    else:
        # Event loop already running, create a new task
        # This happens in pytest-asyncio or other async contexts
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, fetch_all_spells_ws())
            return future.result(timeout=300)
