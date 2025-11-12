"""Parallel image generation utility using Gemini Imagen."""

import asyncio
import logging
from typing import List, Optional, Union
from io import BytesIO
from pathlib import Path
from datetime import datetime
import os
from PIL import Image
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


async def generate_images_parallel(
    prompts: List[str],
    max_concurrent: int = 15,
    save_dir: Optional[Path] = None,
    make_run: bool = False,
    reference_image: Optional[Union[str, Path, Image.Image]] = None,
    temperature: float = 1.0,
    model: str = "gemini-2.5-flash-image"
) -> List[Optional[bytes]]:
    """
    Generate multiple images in parallel from prompts.

    Args:
        prompts: List of image generation prompts
        max_concurrent: Maximum concurrent API calls (default 15)
        save_dir: Optional directory to save images (with auto-generated names)
        make_run: If True, create a timestamped subfolder inside save_dir (default False)
        reference_image: Optional reference image (file path, Path, or PIL Image) to condition generation
        temperature: Sampling temperature 0.0-2.0 (default 1.0). Higher = more creative/random
        model: Gemini model to use (default: gemini-2.5-flash-image)

    Returns:
        List of image bytes (PNG format), None for failed generations

    Example:
        # Basic usage
        images = await generate_images_parallel(prompts)

        # With reference image and low temperature (more consistent)
        images = await generate_images_parallel(
            prompts,
            reference_image="/path/to/reference.png",
            temperature=0.5
        )

        # High temperature for more creative variation
        images = await generate_images_parallel(
            prompts,
            temperature=1.5,
            save_dir=Path("output/images"),
            make_run=True
        )
    """
    if not prompts:
        return []

    # Store reference image info for thread-safe access
    # Each thread will load its own copy to avoid PIL threading issues
    ref_image_path = None
    if reference_image is not None:
        if isinstance(reference_image, Image.Image):
            # Save PIL Image to temp file and pass path
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            reference_image.save(temp_file.name, 'PNG')
            ref_image_path = temp_file.name
            logger.info(f"Saved reference PIL Image to temp file: {ref_image_path}")
        else:
            # Convert string or Path to string path
            ref_image_path = str(reference_image)
            logger.info(f"Using reference image: {ref_image_path}")

    # Create timestamped run directory if requested
    actual_save_dir = None
    if save_dir:
        if make_run:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            actual_save_dir = save_dir / timestamp
            logger.info(f"Creating timestamped run directory: {actual_save_dir}")
        else:
            actual_save_dir = save_dir

    semaphore = asyncio.Semaphore(max_concurrent)

    async def generate_one(prompt: str, index: int) -> Optional[bytes]:
        async with semaphore:
            try:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None,
                    _generate_image_sync,
                    prompt,
                    model,
                    actual_save_dir,
                    index if actual_save_dir else None,
                    ref_image_path,  # Pass path, not PIL Image object
                    temperature
                )
            except Exception as e:
                logger.error(f"Failed to generate image {index} ('{prompt[:50]}...'): {e}")
                return None

    logger.info(f"Generating {len(prompts)} images with max_concurrent={max_concurrent}")
    results = await asyncio.gather(*[generate_one(p, i) for i, p in enumerate(prompts)])

    success_count = sum(1 for r in results if r is not None)
    logger.info(f"Generated {success_count}/{len(prompts)} images successfully")
    if actual_save_dir:
        logger.info(f"Images saved to: {actual_save_dir}")

    return results


def _generate_image_sync(
    prompt: str,
    model: str,
    save_dir: Optional[Path] = None,
    index: Optional[int] = None,
    reference_image_path: Optional[str] = None,
    temperature: float = 1.0
) -> bytes:
    """
    Blocking image generation call.

    This runs in a thread pool executor to avoid blocking the event loop.

    Supports two API patterns:
    - imagen-4.0-* models: Use generate_images() API
    - gemini-*-image models: Use generate_content() with response_modalities=["IMAGE"]

    Args:
        reference_image_path: Path to reference image file (each thread loads its own copy)
        temperature: Sampling temperature 0.0-2.0
    """
    api_key = os.getenv("GeminiImageAPI")
    if not api_key:
        raise ValueError("GeminiImageAPI environment variable not set")

    client = genai.Client(api_key=api_key)

    # Detect which API to use based on model name
    use_generate_images_api = model.startswith("imagen-")

    if use_generate_images_api:
        # Use generate_images() API for imagen-4.0-* models
        # Note: generate_images() doesn't support reference images or temperature
        if reference_image_path is not None:
            logger.warning(f"Reference images not supported with {model}, ignoring reference_image")
        if temperature != 1.0:
            logger.warning(f"Temperature not supported with {model}, ignoring temperature={temperature}")

        response = client.models.generate_images(
            model=model,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
            )
        )

        if not response.generated_images:
            raise RuntimeError("No images generated")

        # Get PIL image and convert to bytes
        pil_image = response.generated_images[0].image._pil_image
        buffer = BytesIO()
        pil_image.save(buffer, format='PNG')
        generated_image_bytes = buffer.getvalue()

    else:
        # Use generate_content() API for gemini-*-image models
        # Build contents list: [prompt] or [prompt, image]
        contents = [prompt]
        if reference_image_path is not None:
            # Each thread loads its own copy of the image for thread safety
            ref_image = Image.open(reference_image_path)
            contents.append(ref_image)

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=temperature,
                response_modalities=["IMAGE"]
            )
        )

        # Extract image bytes from response
        generated_image_bytes = None
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                generated_image_bytes = part.inline_data.data
                break

        if generated_image_bytes is None:
            raise RuntimeError("No image data in response")

    # Optionally save to disk
    if save_dir and index is not None:
        save_dir.mkdir(parents=True, exist_ok=True)
        filepath = save_dir / f"image_{index:03d}.png"
        with open(filepath, 'wb') as f:
            f.write(generated_image_bytes)
        logger.debug(f"Saved image to {filepath}")

    return generated_image_bytes


async def generate_variations(
    prompt: str,
    count: int = 4,
    max_concurrent: int = 15,
    save_dir: Optional[Path] = None,
    make_run: bool = False,
    reference_image: Optional[Union[str, Path, Image.Image]] = None,
    temperature: float = 1.0,
    model: str = "gemini-2.5-flash-image"
) -> List[Optional[bytes]]:
    """
    Generate multiple variations of the same prompt.

    Args:
        prompt: Single prompt to generate variations of
        count: Number of variations to generate
        max_concurrent: Maximum concurrent API calls
        save_dir: Optional directory to save images
        make_run: If True, create a timestamped subfolder inside save_dir
        reference_image: Optional reference image to condition generation
        temperature: Sampling temperature 0.0-2.0 (default 1.0)
        model: Gemini model to use (default: gemini-2.5-flash-image)

    Returns:
        List of image bytes (PNG format)

    Example:
        # Just get bytes
        variations = await generate_variations("A goblin hideout", count=4)

        # With reference image and high temperature for more variety
        variations = await generate_variations(
            "A goblin hideout",
            count=4,
            reference_image="path/to/reference.png",
            temperature=1.5
        )

        # Low temperature for more consistency
        variations = await generate_variations(
            "A goblin hideout",
            count=4,
            temperature=0.3,
            save_dir=Path("output/variations"),
            make_run=True
        )
    """
    return await generate_images_parallel(
        [prompt] * count,
        max_concurrent=max_concurrent,
        save_dir=save_dir,
        make_run=make_run,
        reference_image=reference_image,
        temperature=temperature,
        model=model
    )
