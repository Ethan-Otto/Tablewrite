"""Icon cache for resolving item types to FoundryVTT icon paths."""

import logging
import os
import requests
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
