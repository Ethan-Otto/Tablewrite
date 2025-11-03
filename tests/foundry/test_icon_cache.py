"""Test suite for FoundryVTT icon cache."""

import pytest
from foundry.icon_cache import IconCache


def test_icon_cache_initialization():
    """Test IconCache initializes with empty state."""
    cache = IconCache()

    assert not cache.loaded
    assert cache.icon_count == 0
