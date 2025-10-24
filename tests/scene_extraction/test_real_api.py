"""Real API integration test for scene extraction (requires API key)."""

import os
import pytest
from dotenv import load_dotenv
from src.scene_extraction import (
    extract_chapter_context,
    identify_scene_locations,
)

load_dotenv()


@pytest.fixture
def sample_xml():
    """Sample D&D module XML for testing."""
    return """
<chapter name="The Cragmaw Hideout">
    <section name="Overview">
        <p>The Cragmaw goblins have a hideout in a cave complex deep in the forest.
        The entrance is hidden among thick undergrowth.</p>
    </section>
    <section name="Area 1 - Cave Mouth">
        <p>A dark cave entrance opens in the hillside. The rough stone walls are
        damp and covered in moss. Torchlight flickers from deeper within.</p>
    </section>
</chapter>
"""


@pytest.mark.skipif(
    not os.getenv("GeminiImageAPI"),
    reason="Real API tests require GeminiImageAPI environment variable"
)
class TestRealAPIIntegration:
    """Tests that actually call the Gemini API (requires API key)."""

    def test_extract_context_real_api(self, sample_xml):
        """Test context extraction with real Gemini API call."""
        context = extract_chapter_context(sample_xml)

        # Verify we got valid context
        assert context.environment_type is not None
        assert len(context.environment_type) > 0

        print(f"✓ Context extracted: {context.environment_type}")
        print(f"  Lighting: {context.lighting}")
        print(f"  Terrain: {context.terrain}")

    def test_identify_scenes_real_api(self, sample_xml):
        """Test scene identification with real Gemini API call."""
        # First get context
        context = extract_chapter_context(sample_xml)

        # Then identify scenes
        scenes = identify_scene_locations(sample_xml, context)

        # Verify we got scenes
        assert len(scenes) > 0
        assert scenes[0].name is not None
        assert scenes[0].description is not None

        print(f"✓ Found {len(scenes)} scene(s)")
        for scene in scenes:
            print(f"  - {scene.name}: {scene.description[:50]}...")
