"""Quick test script for imagen-4.0-generate-001 model."""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from google import genai
from google.genai import types
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_imagen4():
    """Test imagen-4.0-generate-001 with generate_images API."""

    # Initialize client
    api_key = os.getenv("GeminiImageAPI")
    if not api_key:
        raise ValueError("GeminiImageAPI not found in environment")

    client = genai.Client(api_key=api_key)

    # Test prompt - simple D&D scene
    prompt = """
A dark cave entrance with rough stone walls and moss-covered rocks.
Underground setting, dim lighting, rocky cavern terrain.
Fantasy illustration, D&D 5e art style, detailed environment, high quality.

IMPORTANT: Do NOT include any text, words, or letters in the image.
Focus on the physical environment only.
"""

    logger.info("Testing imagen-4.0-generate-001...")
    logger.info(f"Prompt: {prompt[:100]}...")

    try:
        response = client.models.generate_images(
            model='imagen-4.0-generate-001',
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
            )
        )

        if response.generated_images:
            logger.info(f"✓ Successfully generated {len(response.generated_images)} image(s)")

            # Get the PIL image
            pil_image = response.generated_images[0].image._pil_image

            # Save to test output
            output_dir = Path(__file__).parent.parent / "tests" / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / "imagen4_test.png"

            pil_image.save(output_path)
            logger.info(f"✓ Saved test image to: {output_path}")
            logger.info(f"✓ Image size: {pil_image.size}")

            return True
        else:
            logger.error("✗ No images generated")
            return False

    except Exception as e:
        logger.error(f"✗ Failed to generate image: {e}")
        raise

if __name__ == "__main__":
    try:
        success = test_imagen4()
        if success:
            print("\n✓ imagen-4.0-generate-001 works correctly!")
        else:
            print("\n✗ imagen-4.0-generate-001 test failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
