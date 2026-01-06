"""Spell cache for resolving spell names to FoundryVTT compendium UUIDs."""

import logging
from typing import Optional, Dict, List
from foundry.items.websocket_fetch import fetch_all_spells_ws_sync

logger = logging.getLogger(__name__)


class SpellCache:
    """
    Caches spell data from FoundryVTT compendiums for fast UUID lookup.

    Usage:
        cache = SpellCache()
        cache.load()  # Fetch all spells from FoundryVTT
        uuid = cache.get_spell_uuid("Fireball")

    Alternative (for FastAPI context - avoids self-deadlock):
        cache = SpellCache()
        cache.load_from_data(spells_list)  # Load from pre-fetched data
    """

    def __init__(self):
        """Initialize empty spell cache."""
        self._spell_by_name: Dict[str, Dict] = {}
        self._loaded = False

    def load(self) -> None:
        """
        Load all spells from FoundryVTT compendiums via WebSocket.

        Requires:
            - Backend running on localhost:8000
            - Foundry connected via WebSocket

        Raises:
            RuntimeError: If WebSocket fetch fails (no fallback to relay)
        """
        logger.info("Loading spell cache from FoundryVTT via WebSocket...")

        try:
            spells = fetch_all_spells_ws_sync()
        except Exception as e:
            # No relay fallback - fail fast and loud
            error_msg = f"SpellCache WebSocket fetch failed: {e}"
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from e

        self._populate_from_spells(spells)

    def load_from_data(self, spells: List[Dict]) -> None:
        """
        Load spells from pre-fetched data.

        Use this when running inside FastAPI to avoid self-deadlock
        (the server can't make HTTP requests to itself).

        Args:
            spells: List of spell dicts with 'name', 'uuid', etc.
        """
        logger.info(f"Loading spell cache from pre-fetched data ({len(spells)} spells)...")
        self._populate_from_spells(spells)

    def _populate_from_spells(self, spells: List[Dict]) -> None:
        """Build lookup dict from spell list (case-insensitive)."""
        self._spell_by_name.clear()
        for spell in spells:
            name = spell.get('name', '').lower()
            if name:
                self._spell_by_name[name] = spell

        self._loaded = True
        logger.info(f"Loaded {len(self._spell_by_name)} spells into cache")

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
        Get spell data by name.

        Args:
            spell_name: Name of the spell (case-insensitive)

        Returns:
            Spell dict with uuid, name, type, img, pack if found, None otherwise
        """
        if not self._loaded:
            logger.warning("SpellCache.get_spell_data() called before load()")
            return None

        return self._spell_by_name.get(spell_name.lower())

    @property
    def loaded(self) -> bool:
        """Check if cache has been loaded."""
        return self._loaded

    @property
    def spell_count(self) -> int:
        """Get number of spells in cache."""
        return len(self._spell_by_name)
