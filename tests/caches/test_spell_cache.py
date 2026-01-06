"""Tests for spell_cache module."""

import pytest


class TestSpellCacheImports:
    """Tests that SpellCache can be imported from caches."""

    def test_imports_from_caches(self):
        """Should import SpellCache from caches module."""
        from caches import SpellCache

        assert SpellCache is not None

    def test_spell_cache_has_get_method(self):
        """Should have get_spell_uuid method."""
        from caches import SpellCache

        cache = SpellCache()
        assert hasattr(cache, 'get_spell_uuid')
