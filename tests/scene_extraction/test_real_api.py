"""Real API integration test for scene extraction (requires API key)."""

import os
import pytest
from pathlib import Path
from dotenv import load_dotenv
from src.scene_extraction import (
    extract_chapter_context,
    identify_scene_locations,
    generate_scene_image,
    save_scene_image,
    create_scene_gallery_html,
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

    @pytest.mark.skip(reason="Imagen-3.0 model not currently available via generativeai API")
    def test_generate_image_real_api(self, sample_xml, tmp_path):
        """Test image generation with real Gemini Imagen API."""
        # NOTE: This test is skipped because imagen-3.0-generate-001 is not available
        # through the current Gemini API. When Imagen becomes available, this test
        # will verify the image generation functionality.

        # Get context and scenes first
        context = extract_chapter_context(sample_xml)
        scenes = identify_scene_locations(sample_xml, context)

        # Generate image for first scene
        scene = scenes[0]
        image_bytes = generate_scene_image(scene, context)

        # Verify we got image data
        assert image_bytes is not None
        assert len(image_bytes) > 0
        assert isinstance(image_bytes, bytes)

        print(f"✓ Generated image: {len(image_bytes)} bytes")

        # Test saving the image
        image_path = tmp_path / "test_scene.png"
        save_scene_image(image_bytes, str(image_path))

        assert image_path.exists()
        assert image_path.read_bytes() == image_bytes

        print(f"✓ Saved image to: {image_path}")

    def test_create_gallery_html(self, sample_xml):
        """Test gallery HTML creation (no API call, but tests integration)."""
        # Get context and scenes
        context = extract_chapter_context(sample_xml)
        scenes = identify_scene_locations(sample_xml, context)

        # Create gallery HTML
        image_paths = {scene.name: f"images/{scene.name.lower().replace(' ', '_')}.png" for scene in scenes}
        html = create_scene_gallery_html(scenes, image_paths)

        # Verify HTML
        assert "Scene Gallery" in html
        assert scenes[0].name in html
        assert scenes[0].description in html

        print(f"✓ Generated gallery HTML: {len(html)} characters")

    def test_workflow_without_image_generation(self, sample_xml, tmp_path):
        """Test workflow without image generation (Imagen API not available)."""
        print("\n=== WORKFLOW TEST (without image generation) ===")

        # Step 1: Extract context
        print("Step 1: Extracting chapter context...")
        context = extract_chapter_context(sample_xml)
        assert context.environment_type is not None
        print(f"  ✓ Context: {context.environment_type}")

        # Step 2: Identify scenes
        print("Step 2: Identifying scenes...")
        scenes = identify_scene_locations(sample_xml, context)
        assert len(scenes) > 0
        print(f"  ✓ Found {len(scenes)} scene(s)")

        # Step 3: Create mock image paths (simulating saved images)
        print("Step 3: Creating gallery with mock image paths...")
        images_dir = tmp_path / "images"
        images_dir.mkdir()
        image_paths = {}

        for i, scene in enumerate(scenes, start=1):
            image_filename = f"scene_{i:03d}_{scene.name.lower().replace(' ', '_')}.png"
            image_path = images_dir / image_filename
            # Create placeholder file
            image_path.write_bytes(b"fake_image_data")
            image_paths[scene.name] = str(image_path)
            print(f"  ✓ Mock image: {image_filename}")

        # Step 4: Create gallery
        print("Step 4: Creating scene gallery HTML...")
        html = create_scene_gallery_html(scenes, image_paths)
        assert "Scene Gallery" in html
        assert scenes[0].name in html

        gallery_file = tmp_path / "scene_gallery.html"
        gallery_file.write_text(html)
        print(f"  ✓ Gallery saved: {gallery_file} ({len(html)} characters)")

        # Final verification
        print("\n=== WORKFLOW COMPLETE (without Imagen) ===")
        print(f"✓ Scenes extracted: {len(scenes)}")
        print(f"✓ Mock images created: {len(image_paths)}")
        print(f"✓ Gallery HTML created: {gallery_file.exists()}")
        print(f"✓ All files saved to: {tmp_path}")
        print(f"\nNOTE: Image generation skipped (Imagen API not available)")
        print(f"      Context extraction and scene identification tested with real API ✓")
