"""FoundryVTT item utilities for fetching and managing compendium items."""

from .manager import ItemManager
from .fetch import fetch_items_by_type, fetch_all_spells
from .deduplicate import deduplicate_items, get_source_priority, get_source_stats

__all__ = [
    'ItemManager',
    'fetch_items_by_type',
    'fetch_all_spells',
    'deduplicate_items',
    'get_source_priority',
    'get_source_stats',
]
