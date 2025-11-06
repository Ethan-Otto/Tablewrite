"""Icon cache for resolving item types to FoundryVTT icon paths."""

import asyncio
import logging
import os
import requests
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple, Union
from google import genai

from util.gemini import generate_content_async

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

            # Extract icon file paths (API returns 'results' not 'files')
            files = data.get('results', data.get('files', []))
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

    async def _select_icon_with_gemini(
        self,
        item_name: str,
        icon_paths: List[str],
        model_name: str = "gemini-2.0-flash"
    ) -> Optional[str]:
        """
        Use Gemini to select the most appropriate icon from a list.

        Args:
            item_name: Name of the item/attack/trait (e.g., "Flaming Sword")
            icon_paths: List of candidate icon file paths
            model_name: Gemini model to use

        Returns:
            Best matching icon path, or None if Gemini fails
        """
        if not icon_paths:
            return None

        # Extract category path + filename (includes folder context like "lightning", "fire", etc.)
        display_paths = []
        for path in icon_paths:
            # Remove "icons/" prefix and file extension, keep category folders
            # e.g., "icons/magic/lightning/bolt-blue.webp" → "magic/lightning/bolt-blue"
            clean_path = path.replace('icons/', '', 1).rsplit('.', 1)[0]
            display_paths.append(clean_path)

        prompt = f"""You are an icon selection assistant for a D&D 5e virtual tabletop.

Given an item/ability name, select the MOST APPROPRIATE icon from the list below.

ITEM NAME: {item_name}

AVAILABLE ICONS (numbered, showing category/subcategory/filename):
{chr(10).join(f"{i+1}. {name}" for i, name in enumerate(display_paths))}

INSTRUCTIONS:
1. Consider the item's theme, purpose, and visual style
2. Pay attention to folder names (e.g., "lightning", "fire", "acid") as they indicate icon theme
3. Match based on semantic meaning, not just literal words
4. Respond with ONLY the number of your choice (1-{len(display_paths)})
5. Choose the single best match

Your response (number only):"""

        try:
            # Initialize client and call Gemini
            client = genai.Client(api_key=os.getenv("GeminiImageAPI") or os.getenv("GEMINI_API_KEY"))
            response = await generate_content_async(
                client=client,
                model=model_name,
                contents=prompt,
                config={'temperature': 0.0}
            )

            # Parse response (should be just a number)
            choice_text = response.text.strip()
            choice_num = int(choice_text)

            if 1 <= choice_num <= len(icon_paths):
                selected = icon_paths[choice_num - 1]
                logger.info(f"Gemini selected icon for '{item_name}': {selected}")
                return selected
            else:
                logger.warning(f"Gemini returned invalid choice {choice_num} for '{item_name}'")
                return None

        except Exception as e:
            logger.error(f"Gemini icon selection failed for '{item_name}': {e}")
            return None

    async def get_icon_with_ai_fallback(
        self,
        search_term: str,
        category: Optional[Union[str, List[str]]] = None,
        model_name: str = "gemini-2.0-flash"
    ) -> Optional[str]:
        """
        Get icon using perfect word matching, falling back to Gemini if no perfect match.

        This method first attempts perfect word matching (search words must appear as
        complete words in icon filename). If no perfect match is found, it uses Gemini
        to intelligently select from the category's icons.

        Args:
            search_term: Item/attack/trait name to match
            category: Optional category or list of categories to narrow search
                     (e.g., "weapons", ["weapons", "creatures"])
            model_name: Gemini model to use for AI selection

        Returns:
            Best matching icon path, or None if all methods fail

        Example:
            >>> icon = await cache.get_icon_with_ai_fallback("Flame Sword", category="weapons")
            >>> # Perfect match: "sword" in "flame-sword-fire.webp"
            >>> # Or Gemini selects best from weapon icons

            >>> icon = await cache.get_icon_with_ai_fallback("Claw", category=["weapons", "creatures"])
            >>> # Searches both weapons and creatures folders
        """
        if not self._loaded:
            logger.warning("IconCache.get_icon_with_ai_fallback() called before load()")
            return None

        # Normalize search term and extract words
        search_words = set(search_term.lower().replace("-", " ").split())

        # Determine search pool (merge multiple categories if list provided)
        search_pool = []
        if category:
            categories = [category] if isinstance(category, str) else category
            seen_icons = set()  # Deduplicate icons that appear in multiple categories

            for cat in categories:
                if cat in self._icons_by_category:
                    for icon in self._icons_by_category[cat]:
                        if icon not in seen_icons:
                            search_pool.append(icon)
                            seen_icons.add(icon)
        else:
            search_pool = self._all_icons

        if not search_pool:
            return None

        # Try perfect word matching first
        for icon_path in search_pool:
            filename = icon_path.split('/')[-1].rsplit('.', 1)[0]
            icon_words = set(filename.lower().split('-'))

            # Check if ALL search words are in icon words (perfect match)
            if search_words <= icon_words:  # search_words is subset of icon_words
                logger.info(f"Perfect word match for '{search_term}' → '{icon_path}'")
                return icon_path

        # No perfect match found, use Gemini
        logger.info(f"No perfect match for '{search_term}', using Gemini...")

        # Get top 200 icons from category for Gemini to choose from
        # (limit to 200 to keep prompt manageable while providing good coverage)
        candidate_icons = search_pool[:200] if len(search_pool) > 200 else search_pool

        gemini_choice = await self._select_icon_with_gemini(
            search_term,
            candidate_icons,
            model_name=model_name
        )

        if gemini_choice:
            return gemini_choice

        # If Gemini fails, return first icon as last resort
        if search_pool:
            logger.warning(f"Gemini failed for '{search_term}', using first icon from category")
            return search_pool[0]

        return None

    async def get_icons_batch(
        self,
        items: List[Tuple[str, Optional[Union[str, List[str]]]]],
        model_name: str = "gemini-2.0-flash"
    ) -> List[Optional[str]]:
        """
        Get icons for multiple items in parallel using perfect word match + AI fallback.

        Args:
            items: List of (search_term, category) tuples where category can be:
                  - Single string: "weapons"
                  - List of strings: ["weapons", "creatures"]
                  - None: search all icons
            model_name: Gemini model to use for AI selection

        Returns:
            List of icon paths (same order as input), None for failed matches

        Example:
            >>> items = [
            ...     ("Shortsword", "weapons"),
            ...     ("Claw", ["weapons", "creatures"]),
            ...     ("Nimble Escape", ["magic", "skills"])
            ... ]
            >>> icons = await cache.get_icons_batch(items)
        """
        tasks = [
            self.get_icon_with_ai_fallback(
                search_term=term,
                category=cat,
                model_name=model_name
            )
            for term, cat in items
        ]

        return await asyncio.gather(*tasks, return_exceptions=False)
