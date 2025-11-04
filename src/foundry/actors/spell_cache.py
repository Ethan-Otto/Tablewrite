"""Spell cache for resolving spell names to FoundryVTT compendium UUIDs."""

import logging
import os
from typing import Optional, Dict
from ..items.fetch import fetch_all_spells
from ..items.manager import ItemManager

logger = logging.getLogger(__name__)


class SpellCache:
    """
    Caches spell data from FoundryVTT compendiums for fast UUID lookup.

    Usage:
        cache = SpellCache()
        cache.load()  # Fetch all spells from FoundryVTT
        uuid = cache.get_spell_uuid("Fireball")
    """

    def __init__(self):
        """Initialize empty spell cache."""
        self._spell_by_name: Dict[str, Dict] = {}
        self._full_data_cache: Dict[str, Dict] = {}  # Cache full spell data by UUID
        self._loaded = False
        self._item_manager: Optional[ItemManager] = None

    def load(
        self,
        relay_url: Optional[str] = None,
        api_key: Optional[str] = None,
        client_id: Optional[str] = None
    ) -> None:
        """
        Load all spells from FoundryVTT compendiums.

        Args:
            relay_url: Relay server URL (defaults to env var)
            api_key: API key (defaults to env var)
            client_id: Client ID (defaults to env var)

        Raises:
            ValueError: If required credentials are missing
            RuntimeError: If API request fails
        """
        logger.info("Loading spell cache from FoundryVTT...")

        # Store credentials for lazy fetching
        relay_url = relay_url or os.getenv("FOUNDRY_RELAY_URL")
        api_key = api_key or os.getenv("FOUNDRY_LOCAL_API_KEY")
        client_id = client_id or os.getenv("FOUNDRY_LOCAL_CLIENT_ID")
        foundry_url = os.getenv("FOUNDRY_LOCAL_URL")

        # Initialize ItemManager for lazy fetching full data
        self._item_manager = ItemManager(relay_url, foundry_url, api_key, client_id)

        # Fetch all spells (uses env vars if params not provided)
        kwargs = {}
        if relay_url:
            kwargs['relay_url'] = relay_url
        if api_key:
            kwargs['api_key'] = api_key
        if client_id:
            kwargs['client_id'] = client_id

        spells = fetch_all_spells(**kwargs)

        # Build lookup dict (case-insensitive)
        for spell in spells:
            name = spell.get('name', '').lower()
            if name:
                self._spell_by_name[name] = spell

        self._loaded = True
        logger.info(f"✓ Loaded {len(self._spell_by_name)} spells into cache")

    def get_spell_uuid(self, spell_name: str) -> Optional[str]:
        """
        Get FoundryVTT compendium UUID for a spell by name.

        Args:
            spell_name: Name of the spell (case-insensitive)

        Returns:
            UUID string if found, None otherwise

        Example:
            >>> cache.get_spell_uuid("Fireball")
            'Compendium.dnd5e.spells.Item.ztgcdrWPshKRpFd0'
        """
        if not self._loaded:
            logger.warning("SpellCache.get_spell_uuid() called before load()")
            return None

        # Case-insensitive lookup
        spell = self._spell_by_name.get(spell_name.lower())

        if spell:
            return spell.get('uuid')

        return None

    def get_spell_data(self, spell_name: str) -> Optional[Dict]:
        """
        Get full spell data by name (including system fields).

        This method lazily fetches full item data from FoundryVTT on first access
        and caches it for subsequent calls.

        Args:
            spell_name: Name of the spell (case-insensitive)

        Returns:
            Full spell dict with system data if found, None otherwise
        """
        if not self._loaded:
            logger.warning("SpellCache.get_spell_data() called before load()")
            return None

        # Get basic spell info from search results
        spell_info = self._spell_by_name.get(spell_name.lower())
        if not spell_info:
            return None

        # Get UUID
        uuid = spell_info.get('uuid')
        if not uuid:
            return None

        # Check if we already have full data cached
        if uuid in self._full_data_cache:
            return self._full_data_cache[uuid]

        # Lazily fetch full data from FoundryVTT
        if self._item_manager:
            try:
                full_data = self._item_manager.get_item(uuid)
                self._full_data_cache[uuid] = full_data
                return full_data
            except Exception as e:
                logger.warning(f"Failed to fetch full data for {spell_name}: {e}")
                return spell_info  # Return basic info as fallback
        else:
            return spell_info  # Return basic info if no ItemManager available

    @property
    def loaded(self) -> bool:
        """Check if cache has been loaded."""
        return self._loaded

    @property
    def spell_count(self) -> int:
        """Get number of spells in cache."""
        return len(self._spell_by_name)
