"""PyMuPDF-based image extraction."""
import logging
import fitz

logger = logging.getLogger(__name__)


def extract_image_with_pymupdf(page: fitz.Page, output_path: str) -> bool:
    """Extract large images from PDF page using PyMuPDF.

    Searches for images that occupy >25% of the page area. If found,
    extracts and saves the largest image to output_path.

    Args:
        page: PyMuPDF page object
        output_path: Path to save extracted image (PNG format)

    Returns:
        True if extraction succeeded, False if no large images found
    """
    try:
        images = page.get_images()
        if not images:
            logger.debug(f"No images found on page")
            return False

        # Calculate page area
        page_area = page.rect.width * page.rect.height
        threshold = page_area * 0.25

        # Find largest image above threshold
        doc = page.parent
        largest_image = None
        largest_area = 0

        for img_ref in images:
            xref = img_ref[0]
            try:
                img_info = doc.extract_image(xref)
                img_area = img_info['width'] * img_info['height']

                if img_area > threshold and img_area > largest_area:
                    largest_image = img_info
                    largest_area = img_area
            except Exception as e:
                logger.warning(f"Failed to extract image xref {xref}: {e}")
                continue

        if largest_image:
            # Save image as PNG
            with open(output_path, "wb") as f:
                f.write(largest_image['image'])
            logger.info(f"Extracted image: {largest_image['width']}x{largest_image['height']} -> {output_path}")
            return True
        else:
            logger.debug(f"No images above 25% page area threshold")
            return False

    except Exception as e:
        logger.error(f"Image extraction failed: {e}")
        return False
