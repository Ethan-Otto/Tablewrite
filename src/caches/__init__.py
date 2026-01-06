"""Centralized caching for external resource lookups.

This module provides caches for:
- SpellCache: Spell name -> compendium UUID
- IconCache: Icon path lookups

These caches are separated from foundry/ because they are data structures,
not network operations.
"""

from .spell_cache import SpellCache
from .icon_cache import IconCache

__all__ = ["SpellCache", "IconCache"]
