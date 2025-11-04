"""Icon cache for resolving item types to FoundryVTT icon paths."""

import logging
import os
import requests
from difflib import SequenceMatcher
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

    def load(
        self,
        relay_url: Optional[str] = None,
        api_key: Optional[str] = None,
        client_id: Optional[str] = None,
        icon_extensions: Optional[List[str]] = None
    ) -> None:
        """
        Load all icon files from FoundryVTT file system.

        Args:
            relay_url: Relay server URL (defaults to env var)
            api_key: API key (defaults to env var)
            client_id: Client ID (defaults to env var)
            icon_extensions: List of file extensions to include (default: ['.webp', '.png', '.jpg', '.svg'])

        Raises:
            ValueError: If required credentials are missing
            RuntimeError: If API request fails
        """
        logger.info("Loading icon cache from FoundryVTT file system...")

        # Get credentials from env if not provided
        relay_url = relay_url or os.getenv("FOUNDRY_RELAY_URL")
        api_key = api_key or os.getenv("FOUNDRY_LOCAL_API_KEY")
        client_id = client_id or os.getenv("FOUNDRY_LOCAL_CLIENT_ID")

        if not all([relay_url, api_key, client_id]):
            raise ValueError("Missing required credentials: relay_url, api_key, client_id")

        icon_extensions = icon_extensions or ['.webp', '.png', '.jpg', '.svg']

        # Fetch file system recursively from icons/ directory
        endpoint = f"{relay_url}/file-system"
        headers = {"x-api-key": api_key}
        params = {
            "clientId": client_id,
            "path": "icons",
            "recursive": "true",
            "source": "public"  # Public source includes core icons + modules
        }

        try:
            response = requests.get(endpoint, headers=headers, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()

            # Extract icon file paths
            files = data.get('files', [])
            for file_info in files:
                path = file_info.get('path', '')
                # Filter by extension
                if any(path.endswith(ext) for ext in icon_extensions):
                    self._all_icons.append(path)

                    # Categorize by directory structure
                    self._categorize_icon(path)

            self._loaded = True
            logger.info(f"✓ Loaded {len(self._all_icons)} icons into cache")
            logger.info(f"  Categories: {list(self._icons_by_category.keys())}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to load icon cache: {e}")
            raise RuntimeError(f"Failed to load icon cache: {e}") from e

    def _categorize_icon(self, path: str) -> None:
        """
        Categorize icon by full directory hierarchy.

        Mirrors FoundryVTT's existing structure by preserving all category levels.

        Example: "icons/weapons/swords/sword-steel.webp" creates:
            - "weapons" → [path]
            - "weapons/swords" → [path]

        This allows matching at different specificity levels.
        """
        parts = path.split('/')
        if len(parts) >= 2 and parts[0] == 'icons':
            # Add to top-level category (e.g., "weapons")
            top_level = parts[1]
            if top_level not in self._icons_by_category:
                self._icons_by_category[top_level] = []
            self._icons_by_category[top_level].append(path)

            # Add to all subcategory levels (e.g., "weapons/swords")
            for i in range(2, len(parts) - 1):  # -1 to exclude filename
                category_path = '/'.join(parts[1:i+1])
                if category_path not in self._icons_by_category:
                    self._icons_by_category[category_path] = []
                self._icons_by_category[category_path].append(path)

    def get_icon(
        self,
        search_term: str,
        category: Optional[str] = None,
        threshold: float = 0.6
    ) -> Optional[str]:
        """
        Get best matching icon path using fuzzy string matching.

        Args:
            search_term: Item/attack/trait name to match (e.g., "Scimitar", "Fireball")
            category: Optional category to narrow search (e.g., "weapons", "magic", "equipment")
            threshold: Similarity threshold for matching (0.0-1.0, default 0.6)

        Returns:
            Best matching icon path if found, None otherwise

        Example:
            >>> cache.get_icon("scimitar", category="weapons")
            'icons/weapons/swords/scimitar-curved-blue.webp'
        """
        if not self._loaded:
            logger.warning("IconCache.get_icon() called before load()")
            return None

        # Normalize search term
        search_term = search_term.lower().replace(" ", "-")

        # Determine search pool
        if category and category in self._icons_by_category:
            search_pool = self._icons_by_category[category]
        else:
            search_pool = self._all_icons

        if not search_pool:
            return None

        # Find best match using fuzzy string matching
        best_match = None
        best_score = 0.0

        for icon_path in search_pool:
            # Extract filename without extension for matching
            filename = icon_path.split('/')[-1].rsplit('.', 1)[0]

            # Calculate similarity against full filename
            similarity = SequenceMatcher(None, search_term, filename).ratio()

            # Also check similarity against individual words in filename (separated by hyphens)
            words = filename.split('-')
            for word in words:
                word_similarity = SequenceMatcher(None, search_term, word).ratio()
                similarity = max(similarity, word_similarity)

            if similarity > best_score and similarity >= threshold:
                best_score = similarity
                best_match = icon_path

        if best_match:
            logger.debug(f"Matched '{search_term}' → '{best_match}' (score: {best_score:.2f})")

        return best_match

    def get_icon_by_keywords(
        self,
        keywords: List[str],
        category: Optional[str] = None
    ) -> Optional[str]:
        """
        Get icon matching any of the provided keywords.

        Args:
            keywords: List of keywords to match against (tries in order)
            category: Optional category to narrow search

        Returns:
            First matching icon path, or None if no match

        Example:
            >>> cache.get_icon_by_keywords(["sword", "blade", "weapon"], category="weapons")
            'icons/weapons/swords/sword-steel.webp'
        """
        for keyword in keywords:
            icon = self.get_icon(keyword, category=category)
            if icon:
                return icon

        return None
