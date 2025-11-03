"""Icon cache for resolving item types to FoundryVTT icon paths."""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class IconCache:
    """
    Caches icon paths from FoundryVTT for intelligent icon selection.

    Usage:
        cache = IconCache()
        cache.load()  # Fetch all icons from FoundryVTT
        icon_path = cache.get_icon("Scimitar", category="weapon")
    """

    def __init__(self):
        """Initialize empty icon cache."""
        self._icons_by_category: Dict[str, List[str]] = {}  # Full paths: "weapons/swords" → [icons...]
        self._all_icons: List[str] = []
        self._loaded = False

    @property
    def loaded(self) -> bool:
        """Check if cache has been loaded."""
        return self._loaded

    @property
    def icon_count(self) -> int:
        """Get total number of icons in cache."""
        return len(self._all_icons)
