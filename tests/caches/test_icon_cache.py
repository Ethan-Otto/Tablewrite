"""Tests for icon_cache module."""

import pytest


class TestIconCacheImports:
    """Tests that IconCache can be imported from caches."""

    def test_imports_from_caches(self):
        """Should import IconCache from caches module."""
        from caches import IconCache

        assert IconCache is not None

    def test_icon_cache_has_get_method(self):
        """Should have get_icon method."""
        from caches import IconCache

        cache = IconCache()
        assert hasattr(cache, 'get_icon')

    def test_icon_cache_has_load_method(self):
        """Should have load method."""
        from caches import IconCache

        cache = IconCache()
        assert hasattr(cache, 'load')
        assert hasattr(cache, 'load_from_data')
