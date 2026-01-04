"""Pytest configuration for UI backend tests."""
import sys
import pytest
from pathlib import Path

# Add backend root to path so imports work
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))


@pytest.fixture(autouse=True)
def disable_actor_image_generation():
    """Disable image generation for actor creation in all tests."""
    from app.tools.actor_creator import set_image_generation_enabled
    set_image_generation_enabled(False)
    yield
    set_image_generation_enabled(True)
